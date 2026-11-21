#!/usr/bin/env bash
source /workspace/env.sh
R="$MANUAL/runs/p1p2_integration"
while true; do
  clear; date -u +%FT%TZ
  for f in "$LOG_ROOT"/seeds/*.status; do [ -e "$f" ] && printf '%-14s %s\n' "$(basename "$f" .status)" "$(cat "$f")"; done
  echo; nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>/dev/null; echo
  for m in P1-DEFICIT P1P2; do for s in ${SEEDS:-42 2026}; do for k in 1 2 3; do
    p="$R/${m}_seed$s/S$k/eval_dev.jsonl"; [ -f "$p" ] && echo "${m}_seed$s/S$k: $(wc -l < "$p")/500"
  done; done; done
  last=$(ls -td "$LOG_ROOT"/seeds/*/attempt* 2>/dev/null | head -1)
  [ -n "$last" ] && { echo; echo "== $last"; tail -n 6 "$last/execution.log" 2>/dev/null; }
  echo; cat "$LOG_ROOT/seeds/RESULTS_SUMMARY.txt" 2>/dev/null
  sleep 30
done
