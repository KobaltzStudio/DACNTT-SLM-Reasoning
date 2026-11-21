#!/usr/bin/env bash
# Chạy P1-DEFICIT + P1P2 (S1→S3) cho các seed trong SEEDS bằng một lệnh. Mặc định SEEDS="42 2026".
#   bash /workspace/runpod_ops/65_launch_seeds.sh                      # nối tiếp
#   SEEDS=42 bash /workspace/runpod_ops/65_launch_seeds.sh             # chỉ seed 42
#   PARALLEL=1 bash /workspace/runpod_ops/65_launch_seeds.sh           # mỗi seed một session, chạy song song
# Khi được hỏi, gõ đúng danh sách seed nối bằng dấu phẩy, ví dụ 42,2026.
source /workspace/env.sh
set -euo pipefail
SEEDS=${SEEDS:-"42 2026"}
read -r -a list <<< "$SEEDS"
[ "${#list[@]}" -gt 0 ] || { echo "SEEDS rỗng"; exit 2; }
for s in "${list[@]}"; do case "$s" in 42|2026) ;; *) echo "Seed $s không hỗ trợ (chỉ 42, 2026)"; exit 2;; esac; done
token=$(IFS=,; echo "${list[*]}")
mkdir -p "$LOG_ROOT/seeds"
if [ "${PARALLEL:-0}" = 1 ]; then chains=(); for s in "${list[@]}"; do chains+=("seeds-$s"); done
else chains=("seeds-${token//,/-}"); fi
for c in "${chains[@]}" seeds-monitor; do
  ! tmux has-session -t "$c" 2>/dev/null || { echo "tmux session $c đã tồn tại"; exit 2; }
done
for c in "${chains[@]}"; do
  [ ! -e "$LOG_ROOT/seeds/$c.status" ] || { echo "Đã có $LOG_ROOT/seeds/$c.status — báo lại trước khi chạy lần nữa"; exit 2; }
done
echo "Sẽ chạy: P1-DEFICIT + P1P2, seed ${token}, S1→S3 ($([ "${PARALLEL:-0}" = 1 ] && echo song song || echo nối tiếp))"
read -r -p "Gõ $token để chạy: " ok
[ "$ok" = "$token" ] || { echo Hủy; exit 4; }
C=/workspace/runpod_ops/62_seeds_chain.sh
jobs_for(){ for s in "$@"; do printf 'P1-DEFICIT:%s P1P2:%s ' "$s" "$s"; done; }
if [ "${PARALLEL:-0}" = 1 ]; then
  for s in "${list[@]}"; do tmux new-session -d -s "seeds-$s" "bash $C seeds-$s $(jobs_for "$s"); exec bash"; done
else
  tmux new-session -d -s "${chains[0]}" "bash $C ${chains[0]} $(jobs_for "${list[@]}"); exec bash"
fi
tmux new-session -d -s seeds-monitor -e "SEEDS=$SEEDS" "bash /workspace/runpod_ops/66_seeds_monitor.sh; exec bash"
tmux ls
echo "Xem: tmux attach -t seeds-monitor  (thoát: Ctrl+b rồi d, KHÔNG Ctrl+C)"
