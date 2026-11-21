import json
from pathlib import Path

files = [
    Path("data/batch_100/batch_100_annotations_v2.jsonl"),
    Path("data/supplement/supplement_annotations_v2.jsonl"),
]

all_records = []
for path in files:
    if not path.exists():
        raise FileNotFoundError(path)

    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]

    ids = [row["problem_id"] for row in rows]

    print(path)
    print("  records:", len(rows))
    print("  unique IDs:", len(set(ids)))

    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate IDs in {path}")

    all_records.extend(rows)

all_ids = [row["problem_id"] for row in all_records]

print("\nTOTAL RECORDS:", len(all_records))
print("TOTAL UNIQUE IDs:", len(set(all_ids)))

if len(all_records) != 185 or len(set(all_ids)) != 185:
    raise SystemExit("GOLD V2 VALIDATION: FAIL")

print("GOLD V2 VALIDATION: PASS")
