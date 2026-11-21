
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_no}: invalid JSON: {exc}"
                ) from exc

            if not isinstance(obj, dict):
                raise ValueError(
                    f"{path}:{line_no}: record must be a JSON object"
                )

            records.append(obj)

    return records


def read_ids(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev-ids", required=True)
    parser.add_argument(
        "--annotations",
        nargs="+",
        required=True,
        help="One or more annotation JSONL files",
    )
    parser.add_argument("--out-dir", required=True)

    parser.add_argument("--id-field", default="problem_id")
    parser.add_argument("--capability-field", default="capabilities")
    parser.add_argument(
        "--status-field",
        default="adjudication_status",
    )

    parser.add_argument(
        "--gold-status",
        default="adjudicated",
    )

    args = parser.parse_args()

    dev_path = Path(args.dev_ids)
    annotation_paths = [Path(p) for p in args.annotations]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dev_ids_list = read_ids(dev_path)
    dev_ids = set(dev_ids_list)

    if len(dev_ids) != len(dev_ids_list):
        raise ValueError("D_dev contains duplicate IDs")

    # Keep source provenance for every record.
    records = []
    for path in annotation_paths:
        for row in read_jsonl(path):
            row["_source_file"] = str(path)
            records.append(row)

    id_counts = Counter()
    invalid_capabilities = []
    missing_id = []
    missing_capabilities = []
    unknown_ids = []
    status_counts = Counter()

    # Preserve records grouped by problem ID.
    by_problem = {}

    for row in records:
        problem_id = row.get(args.id_field)

        if not problem_id:
            missing_id.append(row)
            continue

        id_counts[problem_id] += 1

        if problem_id not in dev_ids:
            unknown_ids.append(problem_id)

        status = row.get(args.status_field, "missing")
        status_counts[str(status)] += 1

        caps = row.get(args.capability_field)

        if not isinstance(caps, list) or not caps:
            missing_capabilities.append(problem_id)
            caps = []

        invalid = [
            cap for cap in caps
            if cap not in CAPABILITIES
        ]

        if invalid:
            invalid_capabilities.append({
                "problem_id": problem_id,
                "invalid_capabilities": invalid,
                "source_file": row["_source_file"],
            })

        by_problem.setdefault(problem_id, []).append(row)

    duplicate_ids = {
        problem_id: count
        for problem_id, count in id_counts.items()
        if count > 1
    }

    # A problem is gold only if it has exactly one adjudicated,
    # non-empty record with valid capability labels.
    gold_by_problem = {}
    gold_conflicts = []

    for problem_id, rows in by_problem.items():
        gold_rows = [
            row for row in rows
            if row.get(args.status_field) == args.gold_status
            and isinstance(row.get(args.capability_field), list)
            and len(row[args.capability_field]) > 0
            and all(
                cap in CAPABILITIES
                for cap in row[args.capability_field]
            )
        ]

        if len(gold_rows) == 1:
            gold_by_problem[problem_id] = gold_rows[0]
        elif len(gold_rows) > 1:
            gold_conflicts.append(problem_id)

    gold_ids = set(gold_by_problem) & dev_ids
    missing_gold_ids = sorted(dev_ids - gold_ids)

    capability_support = Counter()

    for problem_id in gold_ids:
        caps = set(
            gold_by_problem[problem_id][args.capability_field]
        )
        for cap in caps:
            capability_support[cap] += 1

    coverage = (
        len(gold_ids) / len(dev_ids)
        if dev_ids else 0.0
    )

    report = {
        "d_dev_count": len(dev_ids),
        "annotation_records": len(records),
        "unique_annotated_problem_ids": len(id_counts),
        "gold_labeled_d_dev": len(gold_ids),
        "gold_coverage": coverage,
        "gold_coverage_percent": round(coverage * 100, 2),
        "missing_gold_count": len(missing_gold_ids),
        "missing_gold_ids": missing_gold_ids,
        "status_counts": dict(status_counts),
        "capability_support": {
            cap: capability_support.get(cap, 0)
            for cap in sorted(CAPABILITIES)
        },
        "duplicate_problem_ids": duplicate_ids,
        "gold_conflicts": gold_conflicts,
        "missing_id_records": len(missing_id),
        "missing_capability_records": len(missing_capabilities),
        "invalid_capability_records": invalid_capabilities,
        "ids_outside_d_dev": sorted(set(unknown_ids)),
        "annotation_files": [str(p) for p in annotation_paths],
    }

    (out_dir / "capability_gap_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Capability Gap Audit",
        "",
        f"- D_dev count: {len(dev_ids)}",
        f"- Annotation records: {len(records)}",
        f"- Gold-labeled D_dev: {len(gold_ids)}",
        f"- Gold coverage: {coverage:.2%}",
        f"- Missing gold labels: {len(missing_gold_ids)}",
        "",
        "## Capability support",
        "",
        "| Capability | Gold support |",
        "|---|---:|",
    ]

    for cap in sorted(CAPABILITIES):
        lines.append(
            f"| {cap} | {capability_support.get(cap, 0)} |"
        )

    lines += [
        "",
        "## Data quality checks",
        "",
        f"- Duplicate problem IDs: {len(duplicate_ids)}",
        f"- Gold conflicts: {len(gold_conflicts)}",
        f"- Missing ID records: {len(missing_id)}",
        f"- Missing capability records: {len(missing_capabilities)}",
        f"- Invalid capability records: {len(invalid_capabilities)}",
        f"- IDs outside D_dev: {len(set(unknown_ids))}",
        "",
        "## Interpretation",
        "",
        "Only adjudicated records with non-empty valid capability labels "
        "are counted as gold coverage.",
        "Pending annotations and extractor predictions are not counted.",
        "Review all conflicts and out-of-split IDs before using these "
        "labels for evaluation.",
    ]

    (out_dir / "capability_gap_audit.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
