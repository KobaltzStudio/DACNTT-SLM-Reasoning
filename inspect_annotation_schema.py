
import json
from pathlib import Path
from collections import Counter, defaultdict

FILE = Path(
    "experiments/week2September/manual/data/batch_100/"
    "batch_100_annotations.jsonl"
)

rows = []

with FILE.open("r", encoding="utf-8") as f:
    for line_no, line in enumerate(f, start=1):
        if not line.strip():
            continue

        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            print(f"Invalid JSON at line {line_no}: {exc}")

print("Total records:", len(rows))

field_types = defaultdict(Counter)

for row in rows:
    if not isinstance(row, dict):
        continue

    for key, value in row.items():
        field_types[key][type(value).__name__] += 1

print("\n=== FIELD PROFILE ===")

for field, types in sorted(field_types.items()):
    print(field, dict(types))

print("\n=== FIRST TWO RECORDS ===")
print(json.dumps(rows[:2], ensure_ascii=False, indent=2))

print("\n=== POSSIBLE STATUS FIELDS ===")

for field in field_types:
    if any(word in field.lower()
           for word in ["status", "adjud", "review", "state"]):
        values = Counter(
            str(row.get(field))
            for row in rows
        )
        print(field, dict(values))

print("\n=== POSSIBLE CAPABILITY FIELDS ===")

for field in field_types:
    if any(word in field.lower()
           for word in ["capability", "skill", "label"]):
        values = Counter()

        for row in rows:
            value = row.get(field)

            if isinstance(value, list):
                values.update(str(x) for x in value)
            elif value is not None:
                values.update([str(value)])

        print(field, dict(values))
