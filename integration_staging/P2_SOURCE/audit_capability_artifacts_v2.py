from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

CAPABILITIES = [
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
]

GOLD_FILES = {
    "batch_100": Path("data/batch_100/batch_100_annotations_v2.jsonl"),
    "supplement": Path("data/supplement/supplement_annotations_v2.jsonl"),
}

SPLIT_FILES = {
    "D_pool": Path("splits/d_pool_ids.txt"),
    "D_dev": Path("splits/d_dev_ids.txt"),
    "D_test": Path("splits/d_test_ids.txt"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_no}: invalid JSON: {exc}"
                ) from exc

            if not isinstance(row, dict):
                raise ValueError(
                    f"{path}:{line_no}: each record must be a JSON object"
                )

            row["_line_no"] = line_no
            records.append(row)

    return records


def read_ids(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit Gold v2 capability annotation artifacts and split coverage."
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Path to experiments/week2September/manual",
    )
    parser.add_argument(
        "--out-dir",
        default="reports/capability/d1_audit_v2",
        help="Output directory relative to --root",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = (root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # 1. Load Gold v2 source files and preserve provenance.
    # ---------------------------------------------------------
    source_records: dict[str, list[dict[str, Any]]] = {}
    source_info = {}
    all_records = []

    for source_name, relative_path in GOLD_FILES.items():
        path = root / relative_path
        if not path.exists():
            raise FileNotFoundError(f"Gold source not found: {path}")

        rows = read_jsonl(path)
        source_records[source_name] = rows

        source_info[source_name] = {
            "path": str(relative_path).replace("\\", "/"),
            "record_count": len(rows),
            "sha256": sha256_file(path),
        }

        for row in rows:
            copied = dict(row)
            copied["_source"] = source_name
            copied["_source_file"] = str(relative_path).replace("\\", "/")
            all_records.append(copied)

    # ---------------------------------------------------------
    # 2. Validate annotation schema and labels.
    # ---------------------------------------------------------
    missing_ids = []
    missing_capabilities = []
    invalid_capabilities = []
    duplicate_capabilities = []
    duplicate_ids_by_source = {}
    source_capability_counts = {}

    records_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for source_name, rows in source_records.items():
        source_ids = []
        cap_counter = Counter()

        for row in rows:
            problem_id = row.get("problem_id")
            caps = row.get("capabilities_manual")

            if not isinstance(problem_id, str) or not problem_id.strip():
                missing_ids.append({
                    "source": source_name,
                    "line": row.get("_line_no"),
                })
                continue

            problem_id = problem_id.strip()
            source_ids.append(problem_id)

            if not isinstance(caps, list) or len(caps) == 0:
                missing_capabilities.append({
                    "problem_id": problem_id,
                    "source": source_name,
                    "line": row.get("_line_no"),
                })
                caps = []

            invalid = [
                cap for cap in caps
                if not isinstance(cap, str) or cap not in CAPABILITIES
            ]
            if invalid:
                invalid_capabilities.append({
                    "problem_id": problem_id,
                    "source": source_name,
                    "invalid_capabilities": invalid,
                })

            repeated = [
                cap for cap, count in Counter(caps).items()
                if count > 1
            ]
            if repeated:
                duplicate_capabilities.append({
                    "problem_id": problem_id,
                    "source": source_name,
                    "duplicate_capabilities": repeated,
                })

            for cap in set(caps):
                if cap in CAPABILITIES:
                    cap_counter[cap] += 1

            records_by_id[problem_id].append({
                **row,
                "_source": source_name,
            })

        counts = Counter(source_ids)
        duplicate_ids_by_source[source_name] = {
            problem_id: count
            for problem_id, count in sorted(counts.items())
            if count > 1
        }

        source_capability_counts[source_name] = {
            cap: cap_counter.get(cap, 0)
            for cap in CAPABILITIES
        }

    cross_source_duplicates = {
        problem_id: sorted({
            row["_source"] for row in rows
        })
        for problem_id, rows in records_by_id.items()
        if len({row["_source"] for row in rows}) > 1
    }

    all_gold_ids = set(records_by_id)
    all_gold_record_count = len(all_records)

    # A cross-source duplicate is not silently resolved.
    # It is reported as a data-quality issue.
    gold_conflicts = {
        problem_id: len(rows)
        for problem_id, rows in records_by_id.items()
        if len(rows) > 1
    }

    combined_capability_counts = Counter()
    for problem_id, rows in records_by_id.items():
        if len(rows) != 1:
            continue
        caps = rows[0].get("capabilities_manual", [])
        if isinstance(caps, list):
            for cap in set(caps):
                if cap in CAPABILITIES:
                    combined_capability_counts[cap] += 1

    combined_capability_counts = {
        cap: combined_capability_counts.get(cap, 0)
        for cap in CAPABILITIES
    }

    # ---------------------------------------------------------
    # 3. Load split IDs and calculate intersections.
    # ---------------------------------------------------------
    split_data = {}
    split_duplicate_ids = {}
    split_ids_by_name = {}

    for split_name, relative_path in SPLIT_FILES.items():
        path = root / relative_path
        if not path.exists():
            raise FileNotFoundError(f"Split file not found: {path}")

        ids = read_ids(path)
        counts = Counter(ids)
        unique_ids = set(ids)

        split_data[split_name] = {
            "path": str(relative_path).replace("\\", "/"),
            "record_count": len(ids),
            "unique_count": len(unique_ids),
            "duplicate_count": len(ids) - len(unique_ids),
        }

        split_duplicate_ids[split_name] = {
            problem_id: count
            for problem_id, count in sorted(counts.items())
            if count > 1
        }
        split_ids_by_name[split_name] = unique_ids

    split_intersections = {}
    split_capability_rows = []

    for split_name, split_ids in split_ids_by_name.items():
        overlap = all_gold_ids & split_ids
        missing_gold = split_ids - all_gold_ids
        gold_outside_split = all_gold_ids - split_ids

        coverage = len(overlap) / len(split_ids) if split_ids else 0.0

        split_intersections[split_name] = {
            "split_count": len(split_ids),
            "gold_overlap_count": len(overlap),
            "gold_coverage": coverage,
            "gold_coverage_percent": round(coverage * 100, 2),
            "split_ids_without_gold_count": len(missing_gold),
            "gold_ids_outside_split_count": len(gold_outside_split),
            "gold_ids_outside_split": sorted(gold_outside_split),
        }

        for cap in CAPABILITIES:
            support = 0
            for problem_id in overlap:
                rows = records_by_id.get(problem_id, [])
                if len(rows) != 1:
                    continue
                caps = rows[0].get("capabilities_manual", [])
                if isinstance(caps, list) and cap in caps:
                    support += 1

            split_capability_rows.append({
                "split": split_name,
                "split_count": len(split_ids),
                "gold_overlap_count": len(overlap),
                "capability": cap,
                "capability_support_in_overlap": support,
            })

    # Check whether split sets overlap with each other.
    split_pairwise_overlap = {}
    split_names = list(split_ids_by_name)
    for i, left in enumerate(split_names):
        for right in split_names[i + 1:]:
            overlap = split_ids_by_name[left] & split_ids_by_name[right]
            split_pairwise_overlap[f"{left}__{right}"] = {
                "overlap_count": len(overlap),
                "overlap_ids": sorted(overlap),
            }

    # ---------------------------------------------------------
    # 4. Create record-level inventory.
    # ---------------------------------------------------------
    inventory_rows = []
    for source_name, rows in source_records.items():
        for row in rows:
            caps = row.get("capabilities_manual", [])
            if not isinstance(caps, list):
                caps = []

            inventory_rows.append({
                "problem_id": row.get("problem_id", ""),
                "source": source_name,
                "capabilities_manual": "|".join(
                    str(cap) for cap in caps
                ),
                "difficulty_manual": row.get("difficulty_manual", ""),
                "annotator_id": row.get("annotator_id", ""),
                "schema_version": row.get("schema_version", ""),
            })

    # ---------------------------------------------------------
    # 5. Build machine-readable report.
    # ---------------------------------------------------------
    report = {
        "audit_name": "D1 Gold v2 Capability Artifact Audit",
        "audit_version": "2.0",
        "gold_definition": (
            "Gold is sourced from the two v2 annotation JSONL files. "
            "The capability field is capabilities_manual. "
            "No adjudication_status field is required in these JSONL records."
        ),
        "capability_taxonomy": CAPABILITIES,
        "sources": source_info,
        "gold_record_count": all_gold_record_count,
        "gold_unique_problem_count": len(all_gold_ids),
        "gold_cross_source_duplicate_count": len(cross_source_duplicates),
        "gold_cross_source_duplicates": cross_source_duplicates,
        "gold_duplicate_problem_ids": gold_conflicts,
        "source_capability_support": source_capability_counts,
        "combined_capability_support_unique_records_only": combined_capability_counts,
        "split_summary": split_data,
        "split_intersections": split_intersections,
        "split_pairwise_overlap": split_pairwise_overlap,
        "split_duplicate_ids": split_duplicate_ids,
        "quality_checks": {
            "missing_id_records": missing_ids,
            "missing_capability_records": missing_capabilities,
            "invalid_capability_records": invalid_capabilities,
            "duplicate_capabilities": duplicate_capabilities,
            "duplicate_ids_by_source": duplicate_ids_by_source,
        },
        "interpretation_notes": [
            "Split coverage is descriptive. It is not automatically a pass/fail criterion.",
            "Whether Gold is expected in D_pool, D_dev, or D_test must be determined from the split protocol and project design.",
            "Cross-source duplicate IDs are reported and are not silently merged.",
            "Capability support counts problems, not trajectories.",
            "This audit does not replace trajectory-level extractor evaluation.",
        ],
    }

    json_path = out_dir / "capability_artifact_audit.json"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # ---------------------------------------------------------
    # 6. Export CSV reports.
    # ---------------------------------------------------------
    write_csv(
        out_dir / "gold_record_inventory.csv",
        [
            "problem_id",
            "source",
            "capabilities_manual",
            "difficulty_manual",
            "annotator_id",
            "schema_version",
        ],
        inventory_rows,
    )

    write_csv(
        out_dir / "split_capability_support.csv",
        [
            "split",
            "split_count",
            "gold_overlap_count",
            "capability",
            "capability_support_in_overlap",
        ],
        split_capability_rows,
    )

    source_support_rows = []
    for source_name, counts in source_capability_counts.items():
        for cap in CAPABILITIES:
            source_support_rows.append({
                "source": source_name,
                "record_count": source_info[source_name]["record_count"],
                "capability": cap,
                "problem_support": counts[cap],
            })

    for cap in CAPABILITIES:
        source_support_rows.append({
            "source": "combined_unique_records",
            "record_count": len(all_gold_ids),
            "capability": cap,
            "problem_support": combined_capability_counts[cap],
        })

    write_csv(
        out_dir / "source_capability_support.csv",
        [
            "source",
            "record_count",
            "capability",
            "problem_support",
        ],
        source_support_rows,
    )

    # ---------------------------------------------------------
    # 7. Human-readable Markdown report.
    # ---------------------------------------------------------
    lines = [
        "# D1 Gold v2 Capability Artifact Audit",
        "",
        "## Gold sources",
        "",
        "| Source | Records | SHA-256 |",
        "|---|---:|---|",
    ]

    for source_name, info in source_info.items():
        lines.append(
            f"| {source_name} | {info['record_count']} | `{info['sha256']}` |"
        )

    lines += [
        "",
        f"- Total Gold records: **{all_gold_record_count}**",
        f"- Unique Gold problem IDs: **{len(all_gold_ids)}**",
        f"- Cross-source duplicate IDs: **{len(cross_source_duplicates)}**",
        "",
        "## Capability support",
        "",
        "| Capability | Batch 100 | Supplement | Combined unique Gold |",
        "|---|---:|---:|---:|",
    ]

    for cap in CAPABILITIES:
        lines.append(
            f"| {cap} "
            f"| {source_capability_counts['batch_100'][cap]} "
            f"| {source_capability_counts['supplement'][cap]} "
            f"| {combined_capability_counts[cap]} |"
        )

    lines += [
        "",
        "## Gold overlap with splits",
        "",
        "| Split | Split IDs | Gold overlap | Gold coverage | Split IDs without Gold |",
        "|---|---:|---:|---:|---:|",
    ]

    for split_name, info in split_intersections.items():
        lines.append(
            f"| {split_name} | {info['split_count']} "
            f"| {info['gold_overlap_count']} "
            f"| {info['gold_coverage_percent']:.2f}% "
            f"| {info['split_ids_without_gold_count']} |"
        )

    lines += [
        "",
        "## Data quality checks",
        "",
        f"- Missing problem IDs: {len(missing_ids)}",
        f"- Missing capability lists: {len(missing_capabilities)}",
        f"- Invalid capability labels: {len(invalid_capabilities)}",
        f"- Duplicate labels within a record: {len(duplicate_capabilities)}",
        f"- Duplicate IDs within batch_100: {len(duplicate_ids_by_source['batch_100'])}",
        f"- Duplicate IDs within supplement: {len(duplicate_ids_by_source['supplement'])}",
        f"- Cross-source duplicate IDs: {len(cross_source_duplicates)}",
        "",
        "## Split integrity",
        "",
    ]

    for split_name, info in split_data.items():
        lines.append(
            f"- {split_name}: {info['record_count']} rows, "
            f"{info['unique_count']} unique IDs, "
            f"{info['duplicate_count']} duplicates."
        )

    for pair, info in split_pairwise_overlap.items():
        lines.append(
            f"- {pair}: {info['overlap_count']} overlapping IDs."
        )

    lines += [
        "",
        "## Interpretation and limitations",
        "",
        "- Split coverage is descriptive, not automatically a pass/fail criterion.",
        "- The expected Gold-to-split relationship must be checked against the split protocol.",
        "- Capability support counts problem-level labels, not trajectory-level predictions.",
        "- This report does not replace the Task 4 extractor evaluation.",
        "- Cross-source duplicate IDs must be reviewed before treating combined support as final.",
        "",
        "## Generated files",
        "",
        "- `capability_artifact_audit.json`",
        "- `gold_record_inventory.csv`",
        "- `source_capability_support.csv`",
        "- `split_capability_support.csv`",
    ]

    md_path = out_dir / "capability_artifact_audit.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---------------------------------------------------------
    # 8. Print concise execution summary.
    # ---------------------------------------------------------
    print("D1 CAPABILITY ARTIFACT AUDIT: COMPLETED")
    print(f"Output directory: {out_dir}")
    print(f"Gold records: {all_gold_record_count}")
    print(f"Unique Gold IDs: {len(all_gold_ids)}")
    print(f"Cross-source duplicate IDs: {len(cross_source_duplicates)}")
    print(
        "Quality issues: "
        f"missing_id={len(missing_ids)}, "
        f"missing_capabilities={len(missing_capabilities)}, "
        f"invalid_capabilities={len(invalid_capabilities)}, "
        f"duplicate_labels={len(duplicate_capabilities)}"
    )
    print("Split intersections:")
    for split_name, info in split_intersections.items():
        print(
            f"  {split_name}: overlap={info['gold_overlap_count']}/"
            f"{info['split_count']} "
            f"({info['gold_coverage_percent']:.2f}%)"
        )
    print("Generated:")
    print(f"  {json_path.name}")
    print(f"  {md_path.name}")
    print("  gold_record_inventory.csv")
    print("  source_capability_support.csv")
    print("  split_capability_support.csv")


if __name__ == "__main__":
    main()
