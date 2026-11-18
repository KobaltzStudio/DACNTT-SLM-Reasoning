from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from itertools import permutations
from pathlib import Path

CAPABILITIES = [
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
]

EXPECTED_ARTIFACTS = {
    "capability_learning_curves.csv",
    "capability_learning_curves.png",
    "capability_graph.json",
    "graph_evidence_ledger.csv",
    "student_learning_dynamics.md",
}

REQUIRED_REPORT_HEADINGS = [
    "## 1. Experimental Setting",
    "## 2. Checkpoint Identity and Round Normalization",
    "## 3. Metric Definitions",
    "## 4. Capability-Level Results",
    "## 5. Transition-Level Dynamics",
    "## 6. Observations",
    "## 7. Graph Interpretation",
    "## 8. Limitations",
    "## 9. Conclusion and Next Research Steps",
]


class Validation:
    def __init__(self):
        self.errors = []
        self.passes = []

    def check(self, condition, message):
        if condition:
            self.passes.append(message)
        else:
            self.errors.append(message)

    def finish(self):
        for item in self.passes:
            print(f"PASS: {item}")

        for item in self.errors:
            print(f"FAIL: {item}")

        if self.errors:
            print(f"FINAL VALIDATION: FAIL ({len(self.errors)} errors)")
            return 1

        print(f"CHECKS PASSED: {len(self.passes)}")
        print("FINAL VALIDATION: PASS")
        return 0


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def safe_float(value):
    try:
        number = float(value)
        if not math.isfinite(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def validate(manual: Path, output_dir: Path):
    result = Validation()

    expected_paths = {
        name: output_dir / name
        for name in EXPECTED_ARTIFACTS
    }
    expected_paths["artifact_manifest.json"] = (
        output_dir / "artifact_manifest.json"
    )

    for name, path in expected_paths.items():
        result.check(
            path.is_file() and path.stat().st_size > 0,
            f"Artifact exists and is non-empty: {name}",
        )

    if result.errors:
        return result.finish()

    csv_path = output_dir / "capability_learning_curves.csv"
    graph_path = output_dir / "capability_graph.json"
    ledger_path = output_dir / "graph_evidence_ledger.csv"
    report_path = output_dir / "student_learning_dynamics.md"
    manifest_path = output_dir / "artifact_manifest.json"

    rows = read_csv(csv_path)

    result.check(len(rows) == 21, "Learning Curves contains 21 records")

    required_columns = {
        "method",
        "seed",
        "round",
        "checkpoint",
        "capability",
        "n_support",
        "n_correct",
        "n_incorrect",
        "mastery",
        "deficit",
        "ci95_low",
        "ci95_high",
        "delta_vs_previous",
        "delta_classification",
        "total_change_round0_to_round2",
        "trend_label",
    }

    columns = set(rows[0]) if rows else set()

    result.check(
        required_columns.issubset(columns),
        "Learning Curves contains all required columns",
    )

    if rows:
        result.check(
            {row["capability"] for row in rows} == set(CAPABILITIES),
            "Learning Curves contains exactly 7 capabilities",
        )

        result.check(
            {int(row["round"]) for row in rows} == {0, 1, 2},
            "Learning Curves contains rounds 0, 1, 2",
        )

        keys = [
            (row["round"], row["capability"])
            for row in rows
        ]

        result.check(
            len(keys) == len(set(keys)),
            "No duplicate round/capability records",
        )

        result.check(
            all(row["method"] == "B4" for row in rows),
            "All Learning Curves records use method B4",
        )

        result.check(
            all(row["seed"] == "13" for row in rows),
            "All Learning Curves records use seed 13",
        )

        metric_errors = []

        for row in rows:
            support = int(row["n_support"])
            correct = int(row["n_correct"])
            incorrect = int(row["n_incorrect"])

            mastery = safe_float(row["mastery"])
            deficit = safe_float(row["deficit"])
            low = safe_float(row["ci95_low"])
            high = safe_float(row["ci95_high"])

            if support <= 0 or correct < 0 or incorrect < 0:
                metric_errors.append(
                    f"{row['capability']}/round{row['round']}: invalid counts"
                )
                continue

            if correct + incorrect != support:
                metric_errors.append(
                    f"{row['capability']}/round{row['round']}: count mismatch"
                )

            expected_mastery = correct / support

            # Compare against the precision actually stored in the CSV.
            # Example: 7/12 = 0.583333... is stored as 0.5833.
            mastery_precision = len(row["mastery"].partition(".")[2])
            expected_mastery_rounded = round(expected_mastery, mastery_precision)

            if (
                mastery is None
                or abs(mastery - expected_mastery_rounded) > 1e-9
            ):
                metric_errors.append(
                    f"{row['capability']}/round{row['round']}: mastery mismatch"
                )

            if deficit is None or mastery is None:
                metric_errors.append(
                    f"{row['capability']}/round{row['round']}: invalid mastery/deficit"
                )
            elif not (
                0 <= mastery <= 1
                and 0 <= deficit <= 1
                and abs(mastery + deficit - 1) <= 1e-9
            ):
                metric_errors.append(
                    f"{row['capability']}/round{row['round']}: invalid deficit"
                )

            if (
                low is None
                or high is None
                or not (0 <= low <= high <= 1)
            ):
                metric_errors.append(
                    f"{row['capability']}/round{row['round']}: invalid CI"
                )

            delta = safe_float(row["delta_vs_previous"])

            if int(row["round"]) == 0:
                if delta is not None:
                    metric_errors.append(
                        f"{row['capability']}/round0: delta must be empty"
                    )
            elif delta is None:
                metric_errors.append(
                    f"{row['capability']}/round{row['round']}: missing delta"
                )

        result.check(
            not metric_errors,
            "Mastery, deficit, counts, CI and delta are valid"
            if not metric_errors
            else "Metric errors: " + "; ".join(metric_errors[:10]),
        )

    graph = read_json(graph_path)
    graph_schema = read_json(
        manual / "schemas" / "capability_graph_schema.json"
    )

    graph_required = graph_schema["required"]

    result.check(
        all(key in graph for key in graph_required),
        "Graph contains all schema-required top-level fields",
    )

    result.check(
        len(graph.get("nodes", [])) == 7,
        "Capability Graph contains 7 nodes",
    )

    result.check(
        len(graph.get("edges", [])) == 0,
        "Capability Graph contains 0 edges",
    )

    result.check(
        [node.get("capability") for node in graph.get("nodes", [])]
        == CAPABILITIES,
        "Graph node taxonomy and order match frozen taxonomy",
    )

    result.check(
        graph.get("status") == "empirical",
        "Graph status is empirical",
    )

    result.check(
        graph.get("student_checkpoint") == "B4_seed13_ckpt003",
        "Graph checkpoint identity matches final observed checkpoint",
    )

    ledger = read_csv(ledger_path)

    result.check(
        len(ledger) == 84,
        "Evidence Ledger contains 84 records",
    )

    expected_pairs = set(permutations(CAPABILITIES, 2))
    actual_pairs = {
        (row["source_capability"], row["target_capability"])
        for row in ledger
    }

    result.check(
        actual_pairs == expected_pairs,
        "Evidence Ledger covers exactly 42 directed non-self pairs",
    )

    result.check(
        all(
            row["relationship_type"] in {"prerequisite", "transfer"}
            for row in ledger
        ),
        "Evidence Ledger contains only prerequisite and transfer types",
    )

    result.check(
        all(row["status"] == "not_established" for row in ledger),
        "No unverified relationship is marked established",
    )

    result.check(
        all(row["evidence_available"].lower() == "false" for row in ledger),
        "All unverified relationships have evidence_available=false",
    )

    result.check(
        all(
            row["source_capability"] != row["target_capability"]
            for row in ledger
        ),
        "Evidence Ledger contains no self-pairs",
    )

    result.check(
        all(
            row["evidence_source"] == ""
            for row in ledger
        ),
        "No unsupported evidence source is claimed",
    )

    report = report_path.read_text(encoding="utf-8")

    missing_headings = [
        heading
        for heading in REQUIRED_REPORT_HEADINGS
        if heading not in report
    ]

    result.check(
        not missing_headings,
        "Report contains all required sections"
        if not missing_headings
        else f"Report missing headings: {missing_headings}",
    )

    result.check(
        "round_unknown" in report and "Round 0" in report,
        "Report documents Round 0 normalization",
    )

    result.check(
        "controlled intervention" in report.lower(),
        "Report documents controlled-intervention limitation",
    )

    result.check(
        "one method" in report.lower() or "one seed" in report.lower(),
        "Report documents single-seed limitation",
    )

    manifest = read_json(manifest_path)

    result.check(
        manifest.get("method") == "B4" and manifest.get("seed") == 13,
        "Manifest identifies B4 seed 13",
    )

    artifact_records = manifest.get("artifacts", [])
    input_records = manifest.get("inputs", [])

    artifact_names = {
        Path(item["path"]).name
        for item in artifact_records
    }

    result.check(
        artifact_names == EXPECTED_ARTIFACTS,
        "Manifest lists exactly the 5 generated artifacts",
    )

    integrity_errors = []

    for item in artifact_records + input_records:
        path = manual / Path(item["path"])

        if not path.is_file():
            integrity_errors.append(f"Missing file: {item['path']}")
            continue

        actual = sha256(path)

        if actual.lower() != item["sha256"].lower():
            integrity_errors.append(f"SHA256 mismatch: {item['path']}")

    result.check(
        not integrity_errors,
        "All artifact and input SHA256 hashes match"
        if not integrity_errors
        else "; ".join(integrity_errors[:10]),
    )

    checkpoint_records = manifest.get("checkpoint_provenance", [])

    result.check(
        len(checkpoint_records) == 3,
        "Manifest contains 3 checkpoint provenance records",
    )

    if len(checkpoint_records) == 3:
        expected_rounds = [0, 1, 2]

        result.check(
            [item["round"] for item in checkpoint_records] == expected_rounds,
            "Manifest checkpoint rounds are ordered 0, 1, 2",
        )

        result.check(
            all(
                item["train_set_sha256"]
                for item in checkpoint_records
            ),
            "Manifest records train-set SHA256 for all checkpoints",
        )

        result.check(
            all(
                item["train_set_source_checkpoint"] == "student_ckpt_000"
                for item in checkpoint_records
            ),
            "Original train-set source_checkpoint metadata is preserved",
        )

        result.check(
            all(
                item["pool_sha256_train_log"]
                == item["pool_sha256_train_set"]
                for item in checkpoint_records
            ),
            "Train-log and train-set pool hashes agree",
        )

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manual = Path(args.manual).resolve()
    output_dir = Path(args.output).resolve()

    result = validate(manual, output_dir)
    return result.finish()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"FINAL VALIDATION: FAIL: {exc}", file=sys.stderr)
        sys.exit(1)

