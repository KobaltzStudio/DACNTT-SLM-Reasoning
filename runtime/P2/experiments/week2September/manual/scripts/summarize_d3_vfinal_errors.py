import csv
import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
D3_DIR = BASE / "reports" / "capability" / "d3_final_regression"

INPUT = D3_DIR / "error_analysis.csv"
SUMMARY_CSV = D3_DIR / "error_analysis_by_capability.csv"
PRIORITY_CSV = D3_DIR / "priority_error_review.csv"
ANNOTATED_CSV = D3_DIR / "priority_error_review_annotated.csv"

CAPABILITIES = [
    "addition", "subtraction", "multiplication",
    "division", "percentage", "fraction", "ratio",
]

PRIORITY_CAPABILITIES = {
    "addition", "multiplication", "division",
}

REVIEW_FIELDS = [
    "review_status",
    "error_classification",
    "gold_label_correct",
    "extractor_rule_issue",
    "proposed_action",
    "review_notes",
    "reviewer",
]


def parse_list(value, field, problem_id):
    try:
        result = json.loads(value or "[]")
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {field} for {problem_id}"
        ) from exc

    if not isinstance(result, list):
        raise ValueError(
            f"{field} must be a list for {problem_id}"
        )

    return result


def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    fn_counts = Counter()
    fp_counts = Counter()
    priority_rows = []

    for row in rows:
        problem_id = row["problem_id"]

        fn = parse_list(
            row.get("false_negatives", ""),
            "false_negatives",
            problem_id,
        )
        fp = parse_list(
            row.get("false_positives", ""),
            "false_positives",
            problem_id,
        )

        fn_counts.update(fn)
        fp_counts.update(fp)

        priority_fn = sorted(set(fn) & PRIORITY_CAPABILITIES)

        if priority_fn:
            new_row = dict(row)
            new_row["priority_false_negatives"] = json.dumps(
                priority_fn, ensure_ascii=False
            )
            priority_rows.append(new_row)

    summary_rows = [
        {
            "capability": cap,
            "FN": fn_counts[cap],
            "FP": fp_counts[cap],
        }
        for cap in CAPABILITIES
    ]

    with SUMMARY_CSV.open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=["capability", "FN", "FP"]
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    priority_fields = list(priority_rows[0].keys()) if priority_rows else [
        "problem_id", "priority_false_negatives",
    ]

    with PRIORITY_CSV.open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=priority_fields
        )
        writer.writeheader()
        writer.writerows(priority_rows)

    annotated_rows = []

    for row in priority_rows:
        new_row = dict(row)
        for field in REVIEW_FIELDS:
            new_row[field] = ""
        annotated_rows.append(new_row)

    annotated_fields = priority_fields + [
        field for field in REVIEW_FIELDS
        if field not in priority_fields
    ]

    with ANNOTATED_CSV.open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=annotated_fields
        )
        writer.writeheader()
        writer.writerows(annotated_rows)

    print("D3 VFINAL ERROR ANALYSIS SUMMARY")
    print(f"Error records: {len(rows)}")
    print(f"Priority records: {len(priority_rows)}")
    print("\nCapability FN/FP:")
    for row in summary_rows:
        print(
            f"{row['capability']:<16} "
            f"FN={row['FN']:<4} FP={row['FP']}"
        )

    print(f"Summary CSV: {SUMMARY_CSV}")
    print(f"Priority CSV: {PRIORITY_CSV}")
    print(f"Annotated review CSV: {ANNOTATED_CSV}")
    print("[PASS]")


if __name__ == "__main__":
    main()
