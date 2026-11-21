#!/usr/bin/env bash
# Kéo các bundle seed 42/2026 về ~/p1p2-incoming/seed<seed>-<method>, kiểm SHA từng file và SHA bảng sums.
set -euo pipefail
sum=$(ssh runpod-p1p2 cat /workspace/intake/logs/seeds/RESULTS_SUMMARY.txt)
echo "$sum"
echo "$sum" | awk '{print $1" "$3" "$4}' | sort -u | while read -r label dir sha; do
  dest="$HOME/p1p2-incoming/$label"
  [ ! -e "$dest" ] || { echo "skip $label (đã có)"; continue; }
  rsync -rt -- "runpod-p1p2:${dir%/}/" "$dest/"
  (cd "$dest" && sha256sum --quiet -c RESULTS_SHA256SUMS.txt)
  got=$(sha256sum "$dest/RESULTS_SHA256SUMS.txt" | cut -c1-64)
  [ "$got" = "$sha" ] || { echo "SHA lệch ở $label: $got"; exit 1; }
  echo "VERIFIED $label ($(wc -l < "$dest/RESULTS_SHA256SUMS.txt") files) -> $dest"
done
