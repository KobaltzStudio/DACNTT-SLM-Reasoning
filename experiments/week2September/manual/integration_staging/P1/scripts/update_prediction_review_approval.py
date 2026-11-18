import csv
import sys
from pathlib import Path

APPROVED_STATUS = "APPROVED_BY_USER_2026-11-12"

TARGET_IDS = {
    "gsm8k_train_02342",
    "gsm8k_train_02858",
    "gsm8k_train_03016",
}

def main():
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: python update_prediction_review_approval.py "
            "<input.csv> <output.csv>"
        )

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        raise FileNotFoundError(input_path)

    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    required = {
        "problem_id",
        "review_status",
        "review_notes",
        "human_approval",
    }

    missing = required - set(fieldnames or [])
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    if len(rows) != 13:
        raise ValueError(
            f"Expected 13 review records, found {len(rows)}. "
            "Check the input file before updating."
        )

    ids = [row["problem_id"] for row in rows]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate problem_id found.")

    found_targets = set(ids) & TARGET_IDS

    if found_targets != TARGET_IDS:
        raise ValueError(
            f"Target ID mismatch. Found: {sorted(found_targets)}"
        )

    for row in rows:
        row["review_status"] = APPROVED_STATUS
        row["human_approval"] = APPROVED_STATUS

        if row["problem_id"] in TARGET_IDS:
            row["review_notes"] = (
                "User reviewed and approved on 2026-11-12."
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Input records: {len(rows)}")
    print(f"Updated approval status: {APPROVED_STATUS}")
    print(f"Updated D3 notes: {len(TARGET_IDS)}")
    print(f"Output: {output_path}")

    print("\nVerification:")
    for row in rows:
        print(
            row["problem_id"],
            "|",
            row["review_status"],
            "|",
            row["human_approval"],
        )

if __name__ == "__main__":
    main()
