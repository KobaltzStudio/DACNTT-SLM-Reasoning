#!/usr/bin/env bash
# Màn hình theo dõi, cập nhật mỗi 30 giây. Ctrl+c để thoát (không ảnh hưởng job).
source /workspace/env.sh
while true; do
  clear; date -u +%FT%TZ
  for f in chain_a chain_b chain_analysis; do printf '%-16s %s\n' "$f" "$(cat "$LOG_ROOT/$f.status" 2>/dev/null || echo '-')"; done
  echo; nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>/dev/null
  echo; for r in P1-DEFICIT_seed13/S3 P1P2_seed13/S2 P1P2_seed13/S3; do
    f="$MANUAL/runs/p1p2_integration/$r/eval_dev.jsonl"; [ -f "$f" ] && echo "$r: $(wc -l < "$f")/500"
  done
  echo; last=$(ls -td "$LOG_ROOT"/*-attempt* 2>/dev/null | head -1)
  [ -n "$last" ] && { echo "== $last"; tail -n 6 "$last/execution.log" 2>/dev/null; }
  echo; [ -f "$LOG_ROOT/RESULTS_SUMMARY.txt" ] && cat "$LOG_ROOT/RESULTS_SUMMARY.txt"
  sleep 30
done
