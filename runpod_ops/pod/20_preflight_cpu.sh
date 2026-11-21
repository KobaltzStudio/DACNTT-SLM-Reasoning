#!/usr/bin/env bash
# Trích nguyên văn từ docs/RUNPOD_EXECUTION_GUIDE.md (B5, khối CPU preflight)
source /workspace/env.sh
set -euo pipefail
test -d "$LOG_ROOT" && test -w "$LOG_ROOT"
test -d "$HF_HUB_CACHE" && test -r "$HF_HUB_CACHE"
df -h "$P1P2_PACKAGE" "$HF_HUB_CACHE" "$LOG_ROOT"
(
  cd "$P1P2_PACKAGE"
  printf '%s  %s\n' \
    bf0c50c301de9e2b78d9533a6a995733a431a6834d8ad019926e1c826af07798 manifests/SHA256SUMS.txt \
    dbe0d5bb0b2b80df5d0b4f41ff57b3318a543c264e2d5b20c5c7f818e0424f62 manifests/RUNPOD_PACKAGE_MANIFEST.json |
    sha256sum -c -
  sha256sum -c manifests/SHA256SUMS.txt
)
bash "$SOURCE/deployment/verify_package.sh" --package "$P1P2_PACKAGE"
bash "$SOURCE/deployment/verify_model_cache.sh" --package "$P1P2_PACKAGE"
(
  export CUDA_VISIBLE_DEVICES=''
  cd "$SOURCE"
  "$P1P2_PYTHON" -B -c 'import torch, transformers, peft, accelerate, tokenizers, safetensors, yaml, matplotlib; print(torch.__version__, torch.version.cuda, transformers.__version__, peft.__version__)'
  "$P1P2_PYTHON" -B tools/preflight.py source
  "$P1P2_PYTHON" -B tools/preflight.py tests
  "$P1P2_PYTHON" -B -m unittest discover -s tests -v
  "$P1P2_PYTHON" -B tools/preflight.py bundle --bundle "$P1P2_PACKAGE"
)
bash "$SOURCE/deployment/setup_environment.sh" --package "$P1P2_PACKAGE" --work "$WORK"
test -w "$MANUAL" && test -w "$MANUAL/runs/p1p2_integration"
test -z "$(find "$MANUAL/runs/p1p2_integration" -name .controller.lock -print)"
bash "$SOURCE/deployment/linux_cpu_preflight.sh" --package "$P1P2_PACKAGE" \
  --work "$WORK" --output "$LOG_ROOT/cpu-preflight"
export RECEIPT="$LOG_ROOT/cpu-preflight/preflight.json"
"$P1P2_PYTHON" -B - "$RECEIPT" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_bytes())
assert (r["status"], r["platform"], r["actions"]) == ("PASS", "linux", [0, 0, 4, 16]), r
print("Linux CPU receipt OK:", r["actions"])
PY
