import json
import csv
from pathlib import Path

FILES = [
    Path("data/raw/gsm8k_train.jsonl"),
    Path("data/supplement/supplement_annotations_v2.jsonl"),
    Path("reports/capability/d3_audit/adjudication_working.csv"),
]

def inspect_jsonl(path):
    print(f"\n========== {path} ==========")

    if not path.exists():
        print("NOT FOUND")
        return

    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            if not line.strip():
                continue

            record = json.loads(line)

            print("Fields:", list(record.keys()))
            print("Sample:", json.dumps(
                record,
                ensure_ascii=False,
                indent=2
            )[:2500])
            break

def inspect_csv(path):
    print(f"\n========== {path} ==========")

    if not path.exists():
        print("NOT FOUND")
        return

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        reader = csv.DictReader(f)

        print("Columns:", reader.fieldnames)

        for index, row in enumerate(reader):
            if index >= 2:
                break

            print(json.dumps(
                row,
                ensure_ascii=False,
                indent=2
            )[:3000])

for path in FILES:
    if path.suffix == ".jsonl":
        inspect_jsonl(path)
    elif path.suffix == ".csv":
        inspect_csv(path)
