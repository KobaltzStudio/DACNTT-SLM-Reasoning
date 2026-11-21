#!/usr/bin/env bash
# Chạy nối tiếp các job (method:seed) truyền vào; dừng ở lỗi đầu tiên.
#   bash 62_seeds_chain.sh <tên-chain> P1-DEFICIT:42 P1P2:42 ...
source /workspace/env.sh
set -uo pipefail
name=$1; shift
st="$LOG_ROOT/seeds/$name.status"; log="$LOG_ROOT/seeds/$name.log"
echo RUNNING > "$st"
for job in "$@"; do
  if ! bash /workspace/runpod_ops/61_seed_job.sh "${job%%:*}" "${job##*:}" 2>&1 | tee -a "$log"; then
    echo "FAILED at $job" > "$st"; exit 1
  fi
done
echo PASS > "$st"
