#!/usr/bin/env bash
# Mở 4 tmux session và chạy toàn bộ phần còn lại một lượt.
#   APPROVED_SCOPES="P1-DEFICIT:13:S3 P1P2:13:S2 P1P2:13:S3" bash 55_launch_all.sh
#   Thêm PARALLEL=1 để chạy run A và run B cùng lúc trên một GPU (nhanh hơn, có rủi ro OOM).
source /workspace/env.sh
set -euo pipefail
: "${APPROVED_SCOPES:?đặt APPROVED_SCOPES gồm các scope đã được duyệt}"
for s in chain-a chain-b analysis monitor; do
  ! tmux has-session -t "$s" 2>/dev/null || { echo "tmux session $s đã tồn tại"; exit 2; }
done
for f in chain_a chain_b chain_analysis; do
  [ ! -e "$LOG_ROOT/$f.status" ] || { echo "Đã có $LOG_ROOT/$f.status — báo lại trước khi chạy lần nữa"; exit 2; }
done
E=(-e "APPROVED_SCOPES=$APPROVED_SCOPES" -e "PARALLEL=${PARALLEL:-0}")
tmux new-session -d -s chain-a  "${E[@]}" "bash /workspace/runpod_ops/50_chain.sh a; exec bash"
tmux new-session -d -s chain-b  "${E[@]}" "bash /workspace/runpod_ops/50_chain.sh b; exec bash"
tmux new-session -d -s analysis "bash /workspace/runpod_ops/51_analysis_chain.sh; exec bash"
tmux new-session -d -s monitor  "bash /workspace/runpod_ops/56_monitor.sh; exec bash"
tmux ls
echo "Đã khởi chạy. Xem: tmux attach -t monitor  (thoát: Ctrl+b rồi d)"
