$Repo = "C:\KLTN-SLM-Reasoning"
$Manual = Join-Path $Repo "experiments\week2September\manual"
$AuditDir = Join-Path $Manual "reports\capability\p1_gold_audit_2026-11-14"
Set-Location $Repo

# Confirm source artifacts still exist
$Required = @(
  (Join-Path $Manual "data\gold_vfinal\batch_100_annotations_vfinal.jsonl"),
  (Join-Path $Manual "data\gold_vfinal\supplement_annotations_vfinal.jsonl"),
  (Join-Path $Manual "data\gold_vfinal\gold_vfinal_manifest.json"),
  (Join-Path $Manual "data\gold_vnext\gold_vnext_manifest.json"),
  (Join-Path $Manual "config\guideline_v3.md"),
  (Join-Path $Manual "priority_error_review.csv"),
  (Join-Path $Manual "priority_error_review_annotated.csv")
)
$Required | ForEach-Object {
  [PSCustomObject]@{ Path = $_; Exists = Test-Path $_ }
} | Format-Table -AutoSize

# Verify the already-generated Gold audit output
Get-FileHash (Join-Path $AuditDir "gold_inventory.json") -Algorithm SHA256
Get-FileHash (Join-Path $AuditDir "gold_review_queue.csv") -Algorithm SHA256
Get-FileHash (Join-Path $AuditDir "p1_gold_audit.md") -Algorithm SHA256

# Check original Gold source row counts and unique IDs without modifying files
@'
import json
from pathlib import Path
for name in ["batch_100_annotations_vfinal.jsonl","supplement_annotations_vfinal.jsonl"]:
    p=Path(r"C:\KLTN-SLM-Reasoning\experiments\week2September\manual\data\gold_vfinal")/name
    rows=[json.loads(x) for x in p.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
    ids=[x["problem_id"] for x in rows]
    print(name, "rows=",len(rows), "unique=",len(set(ids)), "duplicates=",len(ids)-len(set(ids)))
'@ | python -
