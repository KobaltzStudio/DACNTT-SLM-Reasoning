#!/usr/bin/env bash
# Chờ chain A và B PASS rồi chạy G6/G7/G8, index SHA và D_test audit (B12-B16).
source /workspace/env.sh
set -euo pipefail
exec > >(tee -a "$LOG_ROOT/chain_analysis.log") 2>&1
trap 'echo FAILED > "$LOG_ROOT/chain_analysis.status"; echo "!!! ANALYSIS FAILED — xem $LOG_ROOT/chain_analysis.log"' ERR
st(){ cat "$LOG_ROOT/chain_$1.status" 2>/dev/null || true; }
echo "Chờ chain A và B..."
until [ "$(st a)" = PASS ] && [ "$(st b)" = PASS ]; do
  if [ "$(st a)" = FAILED ] || [ "$(st b)" = FAILED ]; then echo "Có chain FAILED, không chạy phân tích"; false; fi
  sleep 60
done
echo "===== $(date -u +%FT%TZ) verify sealed package"
bash "$SOURCE/deployment/verify_package.sh" --package "$P1P2_PACKAGE"
echo "===== $(date -u +%FT%TZ) G6/G7/G8"
bash /workspace/runpod_ops/40_analysis.sh
export ANALYSIS=$(sed -n 's/^ANALYSIS=//p' "$LOG_ROOT/LAST_ANALYSIS_DIR.txt")
echo "===== $(date -u +%FT%TZ) analysis index"
bash /workspace/runpod_ops/41_analysis_index.sh | tee "$LOG_ROOT/analysis_index.txt"
echo "===== $(date -u +%FT%TZ) D_test audit-only"
bash /workspace/runpod_ops/42_d_test_audit.sh
echo "G7 JSON SHA: $(sha256sum "$ANALYSIS/g7/checkpoint_selection_seed13.json" | cut -c1-64)"
echo "analysis $ANALYSIS $(tail -n1 "$LOG_ROOT/analysis_index.txt" | cut -c1-64) | G7 $(sha256sum "$ANALYSIS/g7/checkpoint_selection_seed13.json" | cut -c1-64)" >> "$LOG_ROOT/RESULTS_SUMMARY.txt"
echo PASS > "$LOG_ROOT/chain_analysis.status"
echo "===== ANALYSIS PASS"; cat "$LOG_ROOT/RESULTS_SUMMARY.txt"
