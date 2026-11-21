import csv
from pathlib import Path

SOURCE = Path(
    "experiments/week2September/manual/reports/capability/"
    "p1_day14_final_2026-11-14/approved/"
    "priority_error_review_170_approved.csv"
)

OUTPUT = Path(
    "experiments/week2September/manual/data/regression/"
    "division_retention_13_approved_2026-11-14.csv"
)

RETENTION_IDS = {
    "gsm8k_train_00014",
    "gsm8k_train_00025",
    "gsm8k_train_00040",
    "gsm8k_train_00068",
    "gsm8k_train_02059",
    "gsm8k_train_02342",
    "gsm8k_train_02486",
    "gsm8k_train_02858",
    "gsm8k_train_03016",
    "gsm8k_train_03048",
    "gsm8k_train_03439",
    "gsm8k_train_05451",
    "gsm8k_train_07117",
}

def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    with SOURCE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    required = {
        "problem_id",
        "question",
        "gold_capabilities",
        "solution_trace_available",
        "gold_label_correct",
        "human_approval",
    }

    missing = required - set(fieldnames or [])
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    selected = [
        row for row in rows
        if row.get("problem_id") in RETENTION_IDS
    ]

    found_ids = {row["problem_id"] for row in selected}
    missing_ids = RETENTION_IDS - found_ids
    duplicate_ids = [
        problem_id
        for problem_id in RETENTION_IDS
        if sum(r["problem_id"] == problem_id for r in selected) > 1
    ]

    if missing_ids:
        raise ValueError(f"Missing retention IDs: {sorted(missing_ids)}")
    if duplicate_ids:
        raise ValueError(f"Duplicate retention IDs: {duplicate_ids}")
    if len(selected) != 13:
        raise ValueError(f"Expected 13 records, found {len(selected)}")

    selected.sort(key=lambda row: row["problem_id"])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected)

    print("Source:", SOURCE)
    print("Output:", OUTPUT)
    print("Rows:", len(selected))
    print("Unique IDs:", len(found_ids))
    print("Missing IDs:", len(missing_ids))
    print("Duplicate IDs:", len(duplicate_ids))
    print("\nTrace availability:")
    for row in selected:
        print(
            row["problem_id"],
            "| trace =", row["solution_trace_available"],
            "| gold_label_correct =", row["gold_label_correct"],
            "| human_approval =", row["human_approval"],
        )

if __name__ == "__main__":
    main()
