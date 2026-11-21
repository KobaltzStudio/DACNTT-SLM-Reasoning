#!/usr/bin/env bash
set -euo pipefail

ROOT="${MANUAL_ROOT:?Set MANUAL_ROOT to the staged P2 manual directory}"
PYTHON="${PYTHON:-python}"
cd "$ROOT"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
flags=(--resume --backend hf --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1)

case "${1:-preflight}" in
  preflight)
    "$PYTHON" -B -c 'import torch, transformers, peft; print(torch.__version__, transformers.__version__, peft.__version__); assert torch.cuda.is_available() and torch.cuda.is_bf16_supported(); print(torch.cuda.get_device_name(), torch.cuda.mem_get_info())'
    "$PYTHON" -B scripts/run_p1_p2.py --help
    "$PYTHON" -B scripts/run_p1p2_post_eval.py --help
    ;;
  a-dry|a-s2|a-range) mode="$1"; method=P1-DEFICIT; scope=(--from-checkpoint S1 --to-checkpoint S3) ;;
  b-dry|b-s1|b-all|b-range) mode="$1"; method=P1P2; scope=(--rounds all) ;;
  *) printf '%s\n' 'Use preflight, a-dry, a-s2, a-range, b-dry, b-s1, b-all or b-range.' >&2; exit 2 ;;
esac

if [[ -v mode ]]; then
  case "$mode" in
    a-s2) scope=(--round 2) ;;
    b-s1) scope=(--round 1) ;;
    b-range) scope=(--from-checkpoint S1 --to-checkpoint S3) ;;
  esac
  cmd=("$PYTHON" -B scripts/run_p1_p2.py --method "$method" --seed 13 "${scope[@]}" "${flags[@]}")
  "${cmd[@]}" --dry-run
  if [[ "$mode" != *-dry ]]; then
    if [[ "${P1P2_SEPARATE_AUTHORIZATION:-}" != "$mode" ]]; then
      printf '%s\n' 'Training gate closed. Obtain separate authorization for this exact scope.' >&2
      exit 3
    fi
    "${cmd[@]}"
  fi
fi
