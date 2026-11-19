#!/usr/bin/env bash
# Trích nguyên văn từ docs/RUNPOD_EXECUTION_GUIDE.md (B11). Dùng: METHOD=P1-DEFICIT ROUND=2 ATTEMPT=$LOG_ROOT/a-s2-attempt1 bash 32_verify_scope.sh
source /workspace/env.sh
set -euo pipefail
: "${METHOD:?set P1-DEFICIT or P1P2}"
: "${ROUND:?set 2 or 3}"
: "${ATTEMPT:?set the successful attempt directory}"
case "$METHOD:$ROUND" in
  P1-DEFICIT:2) wrapper=run_a_s2.sh ;;
  P1-DEFICIT:3) wrapper=run_a_s3.sh ;;
  P1P2:2) wrapper=run_b_s2.sh ;;
  P1P2:3) wrapper=run_b_s3.sh ;;
  *) echo 'Invalid scope' >&2; exit 2 ;;
esac
test "$(cat "$ATTEMPT/exit_code.txt")" = 0
grep -F 'P1P2_CONTROLLER=PASS' "$ATTEMPT/execution.log"
preview=$(bash "$SOURCE/deployment/$wrapper" --package "$P1P2_PACKAGE" --work "$WORK")
printf '%s\n' "$preview"
printf '%s\n' "$preview" | grep -F '"actions": []'
"$P1P2_PYTHON" -B - "$WORK" "$MANUAL" "$P1P2_PACKAGE" "$ATTEMPT" "$METHOD" "$ROUND" <<'PY'
from pathlib import Path
import json, sys

work, root, package, attempt = [Path(x).resolve() for x in sys.argv[1:5]]
method, number = sys.argv[5], int(sys.argv[6])
sys.path.insert(0, str(root / "scripts"))
from p1p2_artifact_manager import hash_path

def read(path):
    return json.loads(path.read_bytes())

def rows(path):
    return [json.loads(line) for line in path.read_bytes().splitlines()]

group, label = f"{method}_seed13", f"S{number}"
tag = f"{group}_{label}"
runs = root / "runs/p1p2_integration" / group
models = root / "models/p1p2_integration" / group
reports = root / "reports/p1p2_integration"
adapter = models / f"student_ckpt_{number:03d}"
parent = models / f"student_ckpt_{number - 1:03d}"
selected = runs / f"round_{number:03d}"
pred = runs / label / "eval_dev.jsonl"
side = reports / "capability_sidecars" / tag
state = reports / "capability_state" / group / f"selection_round_{number + 1:03d}.json"
receipt = read(attempt / "execution.json")
assert (receipt["scope"], receipt["status"], receipt["exit_code"]) == (f"{method}:13:{label}", "PASS", 0)
assert Path(receipt["work"]).resolve() == work
dev = (root / "splits/d_dev_ids.txt").read_text(encoding="utf-8-sig").split()
prediction = rows(pred)
ids = {row["problem_id"] for row in prediction}
allowed = {"valid", "invalid_format", "invalid_answer"}
assert len(prediction) == len(ids) == len(set(dev)) == 500 and ids == set(dev)
assert all(r["checkpoint"] == tag and r["status"] in allowed for r in prediction)
correct = sum(r["status"] == "valid" for r in prediction)
summary = read(pred.with_suffix(".summary.json"))
assert (summary["checkpoint"], summary["split"], summary["n_problems"], summary["n_valid"]) == (tag, "dev", 500, correct)
assert summary["accuracy"] == correct / 500
assert pred.with_name("eval_dev.intent.json").is_file()
train_log = read(adapter / "train_log.json")
assert train_log["seed"] == 13 and train_log["checkpoint_parent_sha256"] == hash_path(parent)
matches = [r for r in rows(runs / "checkpoint_log.jsonl") if r["checkpoint"] == label]
assert len(matches) == 1
ckpt = matches[0]
assert (ckpt["method"], ckpt["training_seed"], ckpt["round"], ckpt["parent_checkpoint"]) == (method, 13, number, f"S{number - 1}")
assert ckpt["checkpoint_sha256"] == hash_path(adapter)
for key, path in (("train_set", selected / "train_set.json"), ("selection_log", selected / "selection_log.jsonl"), ("train_log", adapter / "train_log.json")):
    assert ckpt[f"{key}_sha256"] == hash_path(path), path
lineage = read(side / "checkpoint_lineage.json")
assert (lineage["method"], lineage["seed"], lineage["round"]) == (method, 13, number)
assert lineage["prediction_sha256"] == hash_path(pred) and lineage["checkpoint_sha256"] == hash_path(adapter)
coverage = read(side / "prediction_coverage_report.json")
assert coverage["prediction_unique_ids"] == 500 and coverage["gold_matched_prediction_ids"] == 85
assert len(rows(side / "capability_metrics.jsonl")) == 7 and state.is_file()
if method == "P1-DEFICIT" and number == 2:
    prefix = (package / pred.relative_to(work)).read_bytes()
    assert len(prefix.splitlines()) == 75 and pred.read_bytes().startswith(prefix)
    assert hash_path(package / adapter.relative_to(work)) == hash_path(adapter) and train_log["steps"] == 26
if method == "P1P2":
    nll = runs / f"S{number - 1}" / "nll.jsonl"
    nll_summary = read(nll.with_suffix(".summary.json"))
    assert (nll_summary["checkpoint"], nll_summary["adapter_sha256"]) == (f"S{number - 1}", hash_path(parent))
    assert read(selected / "train_set.json")["nll_sha256"] == hash_path(nll)
    print("NLL SHA-256", hash_path(nll))
print(f"{tag} strict D_dev = {correct}/500 = {correct / 500:.4%}")
for path in (adapter, pred, side, state):
    print(hash_path(path), path.relative_to(root))
PY
