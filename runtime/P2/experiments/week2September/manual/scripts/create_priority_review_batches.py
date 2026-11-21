import csv
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

INPUT = (
    BASE / "reports" / "capability" / "d3_final_regression"
    / "priority_error_review_annotated.csv"
)

OUTPUT_DIR = (
    BASE / "reports" / "capability" / "d3_final_regression"
    / "review_batches"
)

BATCH_SIZE = 25

def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    with INPUT.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames

    if not rows:
        raise ValueError("Priority review file is empty.")

    if not fields:
        raise ValueError("CSV header is missing.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total = len(rows)
    batch_count = (total + BATCH_SIZE - 1) // BATCH_SIZE

    print("PRIORITY ERROR REVIEW BATCH BUILDER")
    print(f"Total problems: {total}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Batch count: {batch_count}")

    for batch_index in range(batch_count):
        start = batch_index * BATCH_SIZE
        end = min(start + BATCH_SIZE, total)

        batch_rows = rows[start:end]
        output = OUTPUT_DIR / (
            f"priority_review_batch_{batch_index + 1:02d}.csv"
        )

        with output.open(
            "w", encoding="utf-8-sig", newline=""
        ) as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(batch_rows)

        print(
            f"[OK] Batch {batch_index + 1:02d}: "
            f"{len(batch_rows)} rows -> {output}"
        )

    print("[PASS] All review batches created.")

if __name__ == "__main__":
    main()
