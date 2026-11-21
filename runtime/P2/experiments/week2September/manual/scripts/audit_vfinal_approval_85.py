import csv
import json
from pathlib import Path
from collections import Counter

root = Path(".")
gold_root = root / "data/gold_releases/vFinal_2026-11-16"

approval_path = gold_root / "gold_supplement_85_approved_review.csv"
labels_path = gold_root / "supplement_annotations_vfinal.jsonl"
graph_ids_path = root / "splits/p1p2_vfinal_2026-11-16/d_dev_graph_ids.txt"
manifest_path = gold_root / "gold_vfinal_manifest.json"

def read_ids(path):
    return [x.strip() for x in path.read_text(encoding="utf-8-sig").splitlines() if x.strip()]

with approval_path.open("r", encoding="utf-8-sig", newline="") as f:
    approval = list(csv.DictReader(f))
    approval_columns = list(csv.DictReader.__init__.__annotations__) if False else None

with approval_path.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    approval_columns = reader.fieldnames or []
    approval = list(reader)

with labels_path.open("r", encoding="utf-8") as f:
    labels = [json.loads(line) for line in f if line.strip()]

approval_ids = [r.get("problem_id", "").strip() for r in approval]
gold_ids = [r.get("problem_id", "").strip() for r in labels]
graph_ids = read_ids(graph_ids_path)

required_columns = {"problem_id", "review_status", "human_approval"}
missing_columns = sorted(required_columns - set(approval_columns))

review_counts = Counter((r.get("review_status") or "").strip() for r in approval)
human_counts = Counter((r.get("human_approval") or "").strip() for r in approval)

approved_statuses = {
    "APPROVED_NO_LABEL_CHANGE",
    "APPROVED_WITH_SOURCE_CLARIFICATION",
}
bad_status_rows = [
    (r.get("problem_id"), r.get("review_status"))
    for r in approval
    if (r.get("review_status") or "").strip() not in approved_statuses
]
bad_human_rows = [
    (r.get("problem_id"), r.get("human_approval"))
    for r in approval
    if not (r.get("human_approval") or "").strip().startswith("APPROVED_BY_USER_")
]

print("APPROVAL_FILE:", approval_path.resolve())
print("APPROVAL_ROWS:", len(approval))
print("APPROVAL_UNIQUE_IDS:", len(set(approval_ids)))
print("APPROVAL_COLUMNS:", approval_columns)
print("MISSING_REQUIRED_COLUMNS:", missing_columns)
print("REVIEW_STATUS_COUNTS:", dict(review_counts))
print("HUMAN_APPROVAL_COUNTS:", dict(human_counts))
print("INVALID_REVIEW_STATUS_ROWS:", bad_status_rows[:10])
print("INVALID_HUMAN_APPROVAL_ROWS:", bad_human_rows[:10])

print("GOLD_LABEL_ROWS:", len(labels))
print("GOLD_LABEL_UNIQUE_IDS:", len(set(gold_ids)))
print("D_DEV_GRAPH_COUNT:", len(graph_ids))
print("APPROVAL_EQUALS_GOLD_IDS:", set(approval_ids) == set(gold_ids))
print("GOLD_EQUALS_GRAPH_IDS:", set(gold_ids) == set(graph_ids))
print("APPROVAL_DUPLICATE_IDS:", len(approval_ids) - len(set(approval_ids)))

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
print("MANIFEST_GOLD_VERSION:", manifest.get("gold_version"))
print("MANIFEST_SUPPLEMENT_COUNT:", manifest.get("supplement_count"))

passed = (
    len(approval) == 85
    and len(set(approval_ids)) == 85
    and not missing_columns
    and not bad_status_rows
    and not bad_human_rows
    and set(approval_ids) == set(gold_ids) == set(graph_ids)
    and len(labels) == 85
    and manifest.get("gold_version") == "vFinal"
    and manifest.get("supplement_count") == 85
)
print("APPROVAL_AUDIT:", "PASS" if passed else "FAIL")
if not passed:
    raise SystemExit(1)
