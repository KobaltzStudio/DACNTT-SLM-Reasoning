import ast
import csv
import hashlib
import json
from pathlib import Path

MANUAL = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual")
AUDIT = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\integration_staging\G4_CHECKPOINT_AUDIT")

GOLD_JSONL = MANUAL / "data/gold_vfinal/supplement_annotations_vfinal.jsonl"
APPROVAL_CSV = MANUAL / "data/gold_releases/vFinal_2026-11-16/gold_supplement_85_approved_review.csv"
MANIFEST = MANUAL / "data/gold_releases/vFinal_2026-11-16/gold_vfinal_manifest.json"
PROVENANCE = MANUAL / "data/gold_releases/vFinal_2026-11-16/gold_release_provenance.json"
DEV_ALL = MANUAL / "splits/d_dev_ids.txt"
DEV_GRAPH = MANUAL / "splits/p1p2_vfinal_2026-11-16/d_dev_graph_ids.txt"
EVALUATOR = MANUAL / "scripts/capability_eval.py"

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_ids(path):
    return {
        x.strip()
        for x in path.read_text(encoding="utf-8-sig").splitlines()
        if x.strip()
    }

def load_jsonl(path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception as exc:
                    raise ValueError(f"JSONL parse error {path}:{line_no}: {exc}")
    return rows

def read_constants(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    wanted = {"CAPABILITIES", "EXPECTED_SUPPORT"}
    found = {}

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in wanted:
                    found[target.id] = ast.literal_eval(node.value)

    missing = wanted - set(found)
    if missing:
        raise ValueError(f"Could not read evaluator constants: {sorted(missing)}")
    return found

required = [
    GOLD_JSONL, APPROVAL_CSV, MANIFEST, PROVENANCE,
    DEV_ALL, DEV_GRAPH, EVALUATOR,
]
for p in required:
    if not p.is_file():
        raise FileNotFoundError(p)

gold_rows = load_jsonl(GOLD_JSONL)
with APPROVAL_CSV.open("r", encoding="utf-8-sig", newline="") as f:
    approval_rows = list(csv.DictReader(f))

gold_ids_list = [str(r.get("problem_id", "")).strip() for r in gold_rows]
approval_ids_list = [str(r.get("problem_id", "")).strip() for r in approval_rows]

if any(not x for x in gold_ids_list):
    raise ValueError("Gold JSONL contains empty problem_id")
if any(not x for x in approval_ids_list):
    raise ValueError("Approval CSV contains empty problem_id")

gold_ids = set(gold_ids_list)
approval_ids = set(approval_ids_list)
dev_ids = read_ids(DEV_ALL)
graph_ids = read_ids(DEV_GRAPH)

constants = read_constants(EVALUATOR)
capabilities = constants["CAPABILITIES"]
expected_support = constants["EXPECTED_SUPPORT"]

support = {cap: 0 for cap in capabilities}
label_errors = []

for row in gold_rows:
    labels = row.get("capabilities_manual")
    if not isinstance(labels, list) or not labels:
        label_errors.append({
            "problem_id": row.get("problem_id"),
            "error": "missing_or_invalid_capabilities_manual"
        })
        continue

    unknown = sorted(set(labels) - set(capabilities))
    if unknown:
        label_errors.append({
            "problem_id": row.get("problem_id"),
            "error": "unknown_capabilities",
            "unknown": unknown
        })
        continue

    for cap in set(labels):
        support[cap] += 1

approved_statuses = {
    "APPROVED_NO_LABEL_CHANGE",
    "APPROVED_WITH_SOURCE_CLARIFICATION",
}
bad_approvals = []
for row in approval_rows:
    pid = str(row.get("problem_id", "")).strip()
    status = str(row.get("review_status", "")).strip()
    approval = str(row.get("human_approval", "")).strip()

    if status not in approved_statuses or not approval.startswith("APPROVED_BY_USER_"):
        bad_approvals.append({
            "problem_id": pid,
            "review_status": status,
            "human_approval": approval,
        })

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))

checks = {
    "gold_rows_85": len(gold_rows) == 85,
    "gold_unique_ids_85": len(gold_ids) == 85,
    "approval_rows_85": len(approval_rows) == 85,
    "approval_unique_ids_85": len(approval_ids) == 85,
    "approval_ids_equal_gold_ids": approval_ids == gold_ids,
    "gold_subset_of_dev_500": gold_ids.issubset(dev_ids),
    "gold_equals_dev_graph_85": gold_ids == graph_ids,
    "dev_ids_500": len(dev_ids) == 500,
    "graph_ids_85": len(graph_ids) == 85,
    "no_label_errors": not label_errors,
    "all_approval_rows_approved": not bad_approvals,
    "support_matches_evaluator": support == expected_support,
    "manifest_supplement_count_85": manifest.get("supplement_count") == 85,
    "manifest_total_count_185": manifest.get("total_count") == 185,
    "provenance_approval_row_count_85": provenance.get("approval_row_count") == 85,
}

report = {
    "gold_labels": str(GOLD_JSONL),
    "gold_labels_sha256": sha256(GOLD_JSONL),
    "approval_csv": str(APPROVAL_CSV),
    "approval_csv_sha256": sha256(APPROVAL_CSV),
    "dev_ids_sha256": sha256(DEV_ALL),
    "dev_graph_ids_sha256": sha256(DEV_GRAPH),
    "gold_rows": len(gold_rows),
    "gold_unique_ids": len(gold_ids),
    "approval_rows": len(approval_rows),
    "approval_unique_ids": len(approval_ids),
    "gold_ids_equal_approval_ids": gold_ids == approval_ids,
    "gold_ids_equal_dev_graph_ids": gold_ids == graph_ids,
    "gold_ids_outside_dev": sorted(gold_ids - dev_ids),
    "gold_ids_missing_from_graph": sorted(graph_ids - gold_ids),
    "gold_ids_extra_vs_graph": sorted(gold_ids - graph_ids),
    "capabilities": capabilities,
    "observed_support": support,
    "expected_support": expected_support,
    "label_errors": label_errors,
    "bad_approval_rows": bad_approvals,
    "checks": checks,
    "all_checks_pass": all(checks.values()),
}

out_json = AUDIT / "gold_85_contract_audit.json"
out_txt = AUDIT / "gold_85_contract_audit.txt"

out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
lines = [
    "GOLD 85 CONTRACT AUDIT",
    f"ALL_CHECKS_PASS={report['all_checks_pass']}",
    "",
]
for name, passed in checks.items():
    lines.append(f"{'PASS' if passed else 'FAIL'}: {name}")
lines += [
    "",
    f"GOLD_ROWS={len(gold_rows)}",
    f"GOLD_UNIQUE_IDS={len(gold_ids)}",
    f"APPROVAL_ROWS={len(approval_rows)}",
    f"APPROVAL_UNIQUE_IDS={len(approval_ids)}",
    f"GOLD_EQUALS_DEV_GRAPH={gold_ids == graph_ids}",
    "",
    "OBSERVED_SUPPORT:",
    json.dumps(support, ensure_ascii=False, sort_keys=True),
    "EXPECTED_SUPPORT:",
    json.dumps(expected_support, ensure_ascii=False, sort_keys=True),
    "",
    f"GOLD_SHA256={sha256(GOLD_JSONL)}",
    f"APPROVAL_SHA256={sha256(APPROVAL_CSV)}",
]
out_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

print("\n".join(lines))
print(f"\nJSON_REPORT={out_json}")
print(f"TEXT_REPORT={out_txt}")

