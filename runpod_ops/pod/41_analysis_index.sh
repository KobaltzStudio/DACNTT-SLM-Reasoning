#!/usr/bin/env bash
# Trích nguyên văn từ docs/RUNPOD_EXECUTION_GUIDE.md (B16, index SHA cho thư mục phân tích). Dùng: ANALYSIS=<dir> bash 41_analysis_index.sh
source /workspace/env.sh
: "${ANALYSIS:?set ANALYSIS from LAST_ANALYSIS_DIR.txt}"
(
  set -euo pipefail
  set -o noclobber
  cd "$ANALYSIS"
  LC_ALL=C find g6-inventory g6 g7 figures g8-preflight.json -type f -print0 |
    LC_ALL=C sort -z | xargs -0 -r sha256sum > FINAL_ANALYSIS_SHA256SUMS.txt
  sha256sum -c FINAL_ANALYSIS_SHA256SUMS.txt
  sha256sum FINAL_ANALYSIS_SHA256SUMS.txt
)
