#!/usr/bin/env bash
# Trích nguyên văn từ docs/RUNPOD_EXECUTION_GUIDE.md (B12 G6 + B13 G7 + B14 G8)
source /workspace/env.sh
set -euo pipefail
export ANALYSIS="$LOG_ROOT/analysis-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$ANALYSIS"
export LEGACY_WINDOWS_ROOT
LEGACY_WINDOWS_ROOT=$("$P1P2_PYTHON" -B -c \
  'import json,sys; from pathlib import Path; print(json.loads(Path(sys.argv[1]).read_bytes())["windows_manual_root"])' \
  "$P1P2_PACKAGE/manifests/path_mapping_manifest.json")
export CUDA_VISIBLE_DEVICES='' MPLBACKEND=Agg
"$P1P2_PYTHON" -B "$MANUAL/scripts/build_capability_learning_dynamics.py" \
  --manual "$MANUAL" --legacy-windows-root "$LEGACY_WINDOWS_ROOT" \
  --seed 13 --inventory-only --output "$ANALYSIS/g6-inventory"
"$P1P2_PYTHON" -B - "$ANALYSIS/g6-inventory/g6_pretraining_inventory.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_bytes())
assert r["status"] == "PASS" and not r["missing_method_checkpoint_pairs"], r["missing_method_checkpoint_pairs"]
assert r["accepted_sidecars"] == r["raw_sidecars"]
PY
"$P1P2_PYTHON" -B "$MANUAL/scripts/build_capability_learning_dynamics.py" \
  --manual "$MANUAL" --legacy-windows-root "$LEGACY_WINDOWS_ROOT" \
  --seed 13 --output "$ANALYSIS/g6"
"$P1P2_PYTHON" -B - "$ANALYSIS/g6/capability_learning_dynamics_seed13.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_bytes())
assert r["g6_status"] == "PASS" and r["seed"] == 13 and not r["missing_method_checkpoint_pairs"]
assert len(r["capabilities"]) == 7 and r["shared_S0_included_once"]
assert all(x["n_gold_records"] == 85 for x in r["rows"])
assert r["correctness_policy"] == "status == valid" and r["confidence_interval"] == "Wilson 95%"
PY
CUDA_VISIBLE_DEVICES='' "$P1P2_PYTHON" -B "$MANUAL/scripts/select_checkpoint_on_dev.py" \
  --manual-root "$MANUAL" --output "$ANALYSIS/g7"
"$P1P2_PYTHON" -B - "$ANALYSIS/g7/checkpoint_selection_seed13.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_bytes())
assert r["status"] == "FINAL" and not r["missing_checkpoints"]
rows = r["rows"]
assert len(rows) == 16 and {(x["method"], x["checkpoint"]) for x in rows} == {
    (m, f"S{i}") for m in ("B4", "B5", "P1-DEFICIT", "P1P2") for i in range(4)
}
assert all(x["denominator"] == 415 and x["missing"] == 0 and x["tie_break"] == "earliest checkpoint" for x in rows)
assert len({x["prediction_sha256"] for x in rows if x["checkpoint"] == "S0"}) == 1
for m in ("B4", "B5", "P1-DEFICIT", "P1P2"):
    candidates = [x for x in rows if x["method"] == m]
    best = min(candidates, key=lambda x: (-x["correct"], int(x["checkpoint"][1:])))["checkpoint"]
    assert all(x["selected_checkpoint"] == best for x in candidates)
    print(m, best)
PY
(
  cd "$ANALYSIS/g7"
  sha256sum checkpoint_selection_seed13.json checkpoint_selection_seed13.csv
)
export CUDA_VISIBLE_DEVICES='' MPLBACKEND=Agg
"$P1P2_PYTHON" -B "$MANUAL/scripts/build_p1p2_analysis_figures.py" \
  --manual-root "$MANUAL" --preflight > "$ANALYSIS/g8-preflight.json"
"$P1P2_PYTHON" -B - "$ANALYSIS/g8-preflight.json" <<'PY'
import json, sys
from pathlib import Path
figures = json.loads(Path(sys.argv[1]).read_bytes())["figures"]
assert len(figures) == 7
for name, item in figures.items():
    assert item["status"] == "AVAILABLE" and not item["partial"] and item["observations"] > 0, (name, item)
PY
"$P1P2_PYTHON" -B "$MANUAL/scripts/build_p1p2_analysis_figures.py" \
  --manual-root "$MANUAL" --output "$ANALYSIS/figures"
"$P1P2_PYTHON" -B - "$ANALYSIS/figures" "$MANUAL/scripts/build_p1p2_analysis_figures.py" <<'PY'
import hashlib, json, sys
from pathlib import Path

out, script = map(Path, sys.argv[1:])
def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

r = json.loads((out / "figure_manifest.json").read_bytes())
assert r["script_sha256"] == sha(script)
assert len(r["figures"]) == 7 and "single seed 13" in r["scope"]
for name, fig in r["figures"].items():
    assert fig["status"] == "GENERATED" and not fig["partial"] and not fig["missing"]
    assert fig["observations"] > 0 and set(fig["outputs"]) == {name + ".png", name + ".csv"}
    for path, digest in fig["inputs"].items():
        assert sha(Path(path)) == digest, path
    for filename, digest in fig["outputs"].items():
        assert sha(out / filename) == digest, filename
    print(name, fig["observations"])
PY
echo "ANALYSIS=$ANALYSIS" | tee "$LOG_ROOT/LAST_ANALYSIS_DIR.txt"
