import csv
from pathlib import Path

REPO = Path(r"C:\KLTN-SLM-Reasoning")

SOURCE = (
    REPO
    / "experiments/week2September/manual/data/gold/review_2026-11-15"
    / "adjudication_worklist_63_pending.csv"
)

LEDGER = (
    REPO
    / "experiments/week2September/manual/reports/gold/review_2026-11-16"
    / "user_adjudication_2026-11-16.csv"
)

OUTPUT = (
    REPO
    / "experiments/week2September/manual/data/gold/review_2026-11-16"
    / "remaining_54_review_queue.csv"
)


def load_csv(path):
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    source_rows = load_csv(SOURCE)
    ledger_rows = load_csv(LEDGER)

    source_ids = [r["problem_id"] for r in source_rows]
    decision_ids = [r["problem_id"] for r in ledger_rows]

    if len(source_ids) != 63 or len(set(source_ids)) != 63:
        raise ValueError("Source worklist must contain 63 unique IDs.")

    if len(decision_ids) != 9 or len(set(decision_ids)) != 9:
        raise ValueError("Adjudication ledger must contain 9 unique IDs.")

    missing = set(decision_ids) - set(source_ids)
    if missing:
        raise ValueError(f"Ledger IDs not found in source: {sorted(missing)}")

    reviewed = set(decision_ids)
    remaining = [
        row for row in source_rows
        if row["problem_id"] not in reviewed
    ]

    if len(remaining) != 54:
        raise ValueError(
            f"Expected 54 remaining rows, got {len(remaining)}."
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(source_rows[0].keys())
        )
        writer.writeheader()
        writer.writerows(remaining)

    print("PASS: remaining worklist exported")
    print(f"Original pending rows: {len(source_rows)}")
    print(f"Rows in adjudication ledger: {len(ledger_rows)}")
    print(f"Remaining rows: {len(remaining)}")
    print(f"Output: {OUTPUT}")
    print("Original 63-row worklist: unchanged")


if __name__ == "__main__":
    main()
