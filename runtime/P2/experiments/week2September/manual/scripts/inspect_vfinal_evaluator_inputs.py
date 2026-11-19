import json
from pathlib import Path

ROOT = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual"
)

GOLD_ROOT = ROOT / "data" / "gold_releases" / "vFinal_2026-11-16"
SPLIT_ROOT = ROOT / "splits" / "p1p2_vfinal_2026-11-16"

def read_jsonl(path):
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"Non-object JSON: {path}:{line_no}")
                rows.append(row)
    return rows

print("=== GOLD RELEASE JSONL FILES ===")

for path in sorted(GOLD_ROOT.glob("*.jsonl")):
    rows = read_jsonl(path)
    ids = [
        str(row.get("problem_id", "")).strip()
        for row in rows
    ]
    labels_present = sum(
        isinstance(row.get("capabilities_manual"), list)
        and bool(row["capabilities_manual"])
        for row in rows
    )

    print("\nFILE:", path)
    print("RECORDS:", len(rows))
    print("UNIQUE_IDS:", len(set(ids)))
    print("EMPTY_IDS:", sum(not value for value in ids))
    print("DUPLICATE_IDS:", len(ids) - len(set(ids)))
    print("ROWS_WITH_CAPABILITIES_MANUAL:", labels_present)

    if rows:
        print("FIRST_ROW_KEYS:", sorted(rows[0].keys()))
        print("FIRST_ROW_SAMPLE:", json.dumps(
            rows[0], ensure_ascii=False
        )[:1200])

print("\n=== SPLIT FILES ===")

for name in ["d_dev_graph_ids.txt", "d_dev_select_ids.txt"]:
    path = SPLIT_ROOT / name
    values = [
        x.strip()
        for x in path.read_text(encoding="utf-8-sig").splitlines()
        if x.strip()
    ]
    print("\nFILE:", path)
    print("COUNT:", len(values))
    print("UNIQUE:", len(set(values)))
    print("DUPLICATES:", len(values) - len(set(values)))

manifest_path = SPLIT_ROOT / "split_manifest.json"
print("\n=== SPLIT MANIFEST ===")
print(manifest_path.read_text(encoding="utf-8-sig"))

print("\n=== APPROVAL SUMMARY ===")
approval_path = GOLD_ROOT / "adjudication_human_confirmed.csv"

import csv
with approval_path.open(
    "r", encoding="utf-8-sig", newline=""
) as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    print("COLUMNS:", reader.fieldnames)
    print("RECORDS:", len(rows))
    print("REVIEW_STATUS_COUNTS:", end=" ")
    from collections import Counter
    print(dict(Counter(
        str(r.get("review_status", "")).strip()
        for r in rows
    )))
    print("HUMAN_APPROVAL_COUNTS:", dict(Counter(
        str(r.get("human_approval", "")).strip()
        for r in rows
    )))
