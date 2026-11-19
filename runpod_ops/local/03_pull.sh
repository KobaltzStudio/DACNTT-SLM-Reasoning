#!/usr/bin/env bash
# Dùng: bash 03_pull.sh <đường dẫn trên pod> <nhãn mới> [SHA của RESULTS_SHA256SUMS.txt]
#   ví dụ: bash 03_pull.sh /workspace/intake/returns/a-s2 a-s2 <sha>
# Kéo về ~/p1p2-incoming/<nhãn>, không ghi đè thư mục đã có.
set -euo pipefail
HANDOFF=$(cd "$(dirname "$0")/../.." && pwd)
src=${1:?remote dir}; label=${2:?label}; expected=${3:-}
[[ "$label" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ ]] || { echo 'Nhãn không hợp lệ'; exit 2; }
dest="$HOME/p1p2-incoming/$label"
[ ! -e "$dest" ] || { echo "Đã tồn tại: $dest — dùng nhãn khác"; exit 2; }
mkdir -p "$HOME/p1p2-incoming"
rsync -rt -- "runpod-p1p2:${src%/}/" "$dest/"
if [ -n "$expected" ] && [ ! -f "$dest/FINAL_ANALYSIS_SHA256SUMS.txt" ]; then
  python3 -B "$HANDOFF/github/deployment/ops.py" verify-results --package "$HANDOFF/runtime" --results "$dest" --expected-sha "$expected"
fi
if [ -f "$dest/FINAL_ANALYSIS_SHA256SUMS.txt" ]; then
  (cd "$dest" && sha256sum --quiet -c FINAL_ANALYSIS_SHA256SUMS.txt)
  got=$(sha256sum "$dest/FINAL_ANALYSIS_SHA256SUMS.txt" | cut -c1-64)
  [ -z "$expected" ] || [ "$got" = "$expected" ] || { echo "Analysis index SHA lệch: $got"; exit 1; }
  echo "Analysis index OK: $got"
fi
echo "PULL DONE -> $dest"
