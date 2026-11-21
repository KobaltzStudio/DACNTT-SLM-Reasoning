import json
import sys
from pathlib import Path
from collections import Counter

path = Path(sys.argv[1])

rows = []
with path.open("r", encoding="utf-8-sig") as f:
    for line_no, line in enumerate(f, 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"Non-object JSON at line {line_no}")
        rows.append(row)

ids = [str(x.get("problem_id", "")).strip() for x in rows]
statuses = [x.get("status") for x in rows]

print("FILE:", path)
print("ROWS:", len(rows))
print("UNIQUE_IDS:", len(set(ids)))
print("EMPTY_IDS:", sum(not x for x in ids))
print("STATUS_COUNTS:", dict(Counter(statuses)))
print("INVALID_STATUS:", sorted(set(statuses) - {
    "valid", "invalid_answer", "invalid_format"
}))

if len(rows) != 500:
    raise SystemExit("FAIL: expected exactly 500 rows")

if len(set(ids)) != 500 or any(not x for x in ids):
    raise SystemExit("FAIL: problem_id invalid or duplicated")

if set(statuses) - {"valid", "invalid_answer", "invalid_format"}:
    raise SystemExit("FAIL: unknown status")

print("PREDICTION_SCHEMA_AUDIT: PASS")
