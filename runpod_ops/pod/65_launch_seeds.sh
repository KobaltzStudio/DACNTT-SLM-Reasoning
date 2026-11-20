#!/usr/bin/env bash
# Một lệnh chạy cả seed 42 và 2026 (P1-DEFICIT + P1P2, S1→S3):
#   bash /workspace/runpod_ops/65_launch_seeds.sh             # nối tiếp, 1 GPU (~10 giờ)
#   PARALLEL=1 bash /workspace/runpod_ops/65_launch_seeds.sh  # 2 seed song song trên cùng GPU
source /workspace/env.sh
set -euo pipefail
mkdir -p "$LOG_ROOT/seeds"
for s in seeds seeds-42 seeds-2026 seeds-monitor; do
  ! tmux has-session -t "$s" 2>/dev/null || { echo "tmux session $s đã tồn tại"; exit 2; }
done
ls "$LOG_ROOT"/seeds/*.status >/dev/null 2>&1 && { echo "Đã có file .status trong $LOG_ROOT/seeds — báo lại trước khi chạy lần nữa"; exit 2; }
read -r -p "Gõ SEEDS:42,2026 để xác nhận Nghi đã duyệt: " ok
[ "$ok" = "SEEDS:42,2026" ] || { echo Hủy; exit 4; }
C=/workspace/runpod_ops/62_seeds_chain.sh
if [ "${PARALLEL:-0}" = 1 ]; then
  tmux new-session -d -s seeds-42   "bash $C seeds-42 P1-DEFICIT:42 P1P2:42; exec bash"
  tmux new-session -d -s seeds-2026 "bash $C seeds-2026 P1-DEFICIT:2026 P1P2:2026; exec bash"
else
  tmux new-session -d -s seeds "bash $C seeds P1-DEFICIT:42 P1P2:42 P1-DEFICIT:2026 P1P2:2026; exec bash"
fi
tmux new-session -d -s seeds-monitor "bash /workspace/runpod_ops/66_seeds_monitor.sh; exec bash"
tmux ls
echo "Xem: tmux attach -t seeds-monitor  (thoát: Ctrl+b rồi d, KHÔNG Ctrl+C)"
