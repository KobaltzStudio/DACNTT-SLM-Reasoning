#!/usr/bin/env bash
# Kéo mọi kết quả có trong RESULTS_SUMMARY.txt trên pod về ~/p1p2-incoming (bỏ qua nhãn đã có).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
ssh runpod-p1p2 'cat /workspace/intake/logs/RESULTS_SUMMARY.txt' | tee /dev/stderr |
while read -r label dir sha _; do
  [ -e "$HOME/p1p2-incoming/$label" ] && { echo "skip $label (đã có)"; continue; }
  [ "$label" = analysis ] && label="analysis-seed13"
  [ -e "$HOME/p1p2-incoming/$label" ] && { echo "skip $label (đã có)"; continue; }
  bash "$here/03_pull.sh" "$dir" "$label" "$sha" </dev/null
done
