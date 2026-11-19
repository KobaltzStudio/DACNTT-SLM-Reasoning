#!/usr/bin/env bash
# Trích nguyên văn từ docs/RUNPOD_EXECUTION_GUIDE.md (B15 --audit-only, không suy luận D_test)
source /workspace/env.sh
set -euo pipefail
CUDA_VISIBLE_DEVICES='' "$P1P2_PYTHON" -B "$MANUAL/scripts/run_final_d_test.py" \
  --audit-only > "$LOG_ROOT/d-test-readiness.json"
"$P1P2_PYTHON" -B - "$LOG_ROOT/d-test-readiness.json" "$P1P2_PACKAGE/manifests/d_test_input_audit.json" <<'PY'
import json, sys
from pathlib import Path
a, b = (json.loads(Path(x).read_bytes()) for x in sys.argv[1:])
assert a["D_TEST_EXECUTION"] == "NOT_RUN" and a["n_test"] == 1319
assert a == b
PY
