#!/usr/bin/env bash
# B6-B9. Dùng:
#   bash 30_scope.sh a_s2            -> preview (không chạy gì)
#   bash 30_scope.sh a_s2 execute    -> chạy live (chỉ sau khi đã duyệt scope này)
# Scope: a_s2 a_s3 b_s2 b_s3. Live luôn chạy trong tmux.
source /workspace/env.sh
set -euo pipefail
scope=${1:?a_s2|a_s3|b_s2|b_s3}; mode=${2:-preview}
case "$scope" in
  a_s2) token='P1-DEFICIT:13:S2' ;; a_s3) token='P1-DEFICIT:13:S3' ;;
  b_s2) token='P1P2:13:S2' ;;       b_s3) token='P1P2:13:S3' ;;
  *) echo 'Invalid scope' >&2; exit 2 ;;
esac
wrapper="$SOURCE/deployment/run_${scope}.sh"
if [ "$scope" = a_s2 ]; then   # B6: so prefix 75 dòng với seal
  a_s2='runs/p1p2_integration/P1-DEFICIT_seed13/S2/eval_dev.jsonl'
  sealed_prefix="$P1P2_PACKAGE/P2/experiments/week2September/manual/$a_s2"
  test "$(wc -l < "$sealed_prefix")" -eq 75
  cmp -n "$(wc -c < "$sealed_prefix")" -- "$sealed_prefix" "$MANUAL/$a_s2"
  echo "A S2 prefix 75 dòng khớp seal"
fi
if [ "$mode" != execute ]; then
  bash "$wrapper" --package "$P1P2_PACKAGE" --work "$WORK"
  exit
fi
[ -n "${TMUX:-}" ] || { echo 'Hãy chạy live trong tmux' >&2; exit 3; }
n=1; while [ -e "$LOG_ROOT/${scope//_/-}-attempt$n" ]; do n=$((n+1)); done
out="$LOG_ROOT/${scope//_/-}-attempt$n"
echo "Scope $token, output $out"
read -r -p "Gõ đúng scope ($token) để xác nhận đã được duyệt: " ok
[ "$ok" = "$token" ] || { echo 'Hủy'; exit 4; }
bash "$wrapper" --package "$P1P2_PACKAGE" --work "$WORK" \
  --execute --approve "$token" --receipt "$RECEIPT" --output "$out"
echo "ATTEMPT=$out"
