import csv
import json
from pathlib import Path

MANUAL = Path("experiments/week2September/manual")

APPROVED = (
    MANUAL
    / "reports/capability/p1_day14_final_2026-11-14/approved/"
    / "priority_error_review_170_approved.csv"
)

CHANGES = (
    MANUAL
    / "reports/capability/p1_extractor_v3_1_2026-11-14/"
    / "candidate_analysis/candidate_changes_170.csv"
)

TARGET_ID = "gsm8k_train_00011"


def parse_json(value):
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def main():
    for path in (APPROVED, CHANGES):
        if not path.exists():
            raise FileNotFoundError(path)

    with APPROVED.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        approved_rows = list(csv.DictReader(f))

    with CHANGES.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        change_rows = list(csv.DictReader(f))

    approved = [
        row for row in approved_rows
        if row["problem_id"] == TARGET_ID
    ]

    changes = [
        row for row in change_rows
        if row["problem_id"] == TARGET_ID
    ]

    if len(approved) != 1:
        raise ValueError(
            f"Expected one approved row, found {len(approved)}"
        )

    if len(changes) != 1:
        raise ValueError(
            f"Expected one candidate change row, found {len(changes)}"
        )

    row = approved[0]
    change = changes[0]

    print("=" * 100)
    print("FALSE POSITIVE INSPECTION")
    print("=" * 100)

    print("\nPROBLEM ID:")
    print(TARGET_ID)

    print("\nQUESTION:")
    print(row["question"])

    print("\nGOLD CAPABILITIES:")
    print(row["gold_capabilities"])

    print("\nCANDIDATE PREDICTIONS:")
    print(change["candidate_predictions"])

    print("\nNEW FALSE POSITIVE:")
    print(change["new_false_positive"])

    print("\nFIXED FALSE NEGATIVE:")
    print(change["fixed_false_negative"])

    print("\nANNOTATION METADATA:")
    for key in (
        "solution_trace_available",
        "gold_label_correct",
        "human_approval",
    ):
        if key in row:
            print(f"{key}: {row[key]}")

    print("\nOTHER AVAILABLE COLUMNS:")
    print(", ".join(row.keys()))

    print("\nInspection completed. No files modified.")


if __name__ == "__main__":
    main()
