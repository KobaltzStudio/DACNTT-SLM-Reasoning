#!/usr/bin/env bash
# Dry-run (CPU, không train/eval) cho P1-DEFICIT và P1P2 ở các seed trong SEEDS (mặc định "42 2026").
#   bash /workspace/runpod_ops/60_seeds_dryrun.sh
source /workspace/env.sh
set -euo pipefail
SEEDS=${SEEDS:-"42 2026"}
LEGACY=$("$P1P2_PYTHON" -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["windows_manual_root"])' \
  "$P1P2_PACKAGE/manifests/path_mapping_manifest.json")
out="$LOG_ROOT/seeds/dryrun-$(date -u +%Y%m%dT%H%M%SZ).log"; mkdir -p "$LOG_ROOT/seeds"
cd "$MANUAL"
# shellcheck disable=SC2086
CUDA_VISIBLE_DEVICES='' "$P1P2_PYTHON" -B scripts/run_p1_p2.py --manual-root "$MANUAL" \
  --legacy-windows-root "$LEGACY" --methods P1-DEFICIT P1P2 --seeds $SEEDS --rounds all \
  --resume --dry-run --backend hf --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1 2>&1 | tee "$out"
echo "DRYRUN LOG: $out"
