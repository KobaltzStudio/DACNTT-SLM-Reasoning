import csv
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

D3_DIR = BASE / "reports" / "capability" / "d3_regression"

INPUT = D3_DIR / "priority_error_review.csv"
OUTPUT = D3_DIR / "priority_error_review_annotated.csv"

REVIEW_FIELDS = [
    "review_status",
    "error_classification",
    "gold_label_correct",
    "extractor_rule_issue",
    "proposed_action",
    "review_notes",
    "reviewer",
]

VALID_CLASSIFICATIONS = {
    "MISSING_RULE",
    "OVERLY_BROAD_RULE",
    "GOLD_LABEL_ERROR",
    "GUIDELINE_AMBIGUITY",
    "SOLUTION_DEPENDENT",
    "OTHER",
}


def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if len(rows) != 170:
        raise ValueError(
            f"Expected 170 priority rows, found {len(rows)}"
        )

    ids = [row["problem_id"] for row in rows]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate problem_id in priority review")

    for row in rows:
        for field in REVIEW_FIELDS:
            row[field] = ""

    fields = list(rows[0].keys()) + [
        field for field in REVIEW_FIELDS
        if field not in rows[0]
    ]

    with OUTPUT.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    print("PRIORITY ERROR REVIEW WORKSHEET")
    print(f"Input records: {len(rows)}")
    print(f"Unique IDs: {len(set(ids))}")
    print(f"Output: {OUTPUT}")
    print("[PASS]")


if __name__ == "__main__":
    main()
