#!/usr/bin/env bash
# Trích nguyên văn từ docs/RUNPOD_EXECUTION_GUIDE.md (B17, chỉ đọc trạng thái)
source /workspace/env.sh
ps -eo pid,ppid,lstart,args | grep -E '[r]un_p1_p2|[t]rain_round|[e]val_student|[c]ompute_nll'
find "$MANUAL/runs/p1p2_integration" -name .controller.lock -print
find "$LOG_ROOT" -maxdepth 2 \( -name intent.json -o -name execution.json -o -name exit_code.txt \) -print
