#!/usr/bin/env bash
# Chạy liền một run: preview -> live -> B11 verify -> B16 collect cho từng checkpoint.
#   bash 50_chain.sh a   -> A S3
#   bash 50_chain.sh b   -> B S2 rồi B S3
# Cần APPROVED_SCOPES chứa đúng token của mọi scope trong chain. Dừng ngay ở lỗi đầu tiên, không tự retry.
source /workspace/env.sh
set -euo pipefail
run=${1:?a|b}
STATUS="$LOG_ROOT/chain_$run.status"
exec > >(tee -a "$LOG_ROOT/chain_$run.log") 2>&1
trap 'echo FAILED > "$STATUS"; echo "!!! CHAIN $run FAILED — xem $LOG_ROOT/chain_$run.log, không tự chạy lại"' ERR
[ -n "${TMUX:-}" ] || { echo 'Hãy chạy trong tmux'; exit 3; }
case "$run" in a) scopes="a_s3" ;; b) scopes="b_s2 b_s3" ;; *) exit 2 ;; esac
tok(){ case $1 in a_s3) echo P1-DEFICIT:13:S3;; b_s2) echo P1P2:13:S2;; b_s3) echo P1P2:13:S3;; esac; }
for s in $scopes; do
  case " ${APPROVED_SCOPES:-} " in *" $(tok $s) "*) ;; *) echo "Chưa duyệt $(tok $s) trong APPROVED_SCOPES"; false;; esac
done
if [ "$run" = b ] && [ "${PARALLEL:-0}" != 1 ]; then
  echo "Chờ chain A xong (PARALLEL=0)..."
  until [ "$(cat "$LOG_ROOT/chain_a.status" 2>/dev/null)" = PASS ]; do
    [ "$(cat "$LOG_ROOT/chain_a.status" 2>/dev/null)" = FAILED ] && { echo "Chain A FAILED, không chạy B"; false; }
    sleep 60
  done
fi
echo RUNNING > "$STATUS"
for s in $scopes; do
  token=$(tok $s); method=${token%%:*}; round=${token##*S}; label=${s//_/-}
  echo "===== $(date -u +%FT%TZ) $token PREVIEW"
  bash "$SOURCE/deployment/run_$s.sh" --package "$P1P2_PACKAGE" --work "$WORK" | tee "$LOG_ROOT/preview_$label.json"
  if grep -qF '"actions": []' "$LOG_ROOT/preview_$label.json"; then
    # Checkpoint đã hoàn tất: wrapper không tạo receipt mới -> dùng lại attempt PASS mới nhất của scope này.
    att=$(for d in $(ls -d "$LOG_ROOT/$label"-attempt* 2>/dev/null | sort -V -r); do
            "$P1P2_PYTHON" -B -c 'import json,sys; r=json.load(open(sys.argv[1])); sys.exit(not (r.get("scope")==sys.argv[2] and r.get("status")=="PASS" and r.get("exit_code")==0))' \
              "$d/execution.json" "$token" 2>/dev/null && { echo "$d"; break; }
          done)
    [ -n "$att" ] || { echo "Preview 0 action nhưng không có attempt PASS cho $token"; false; }
    echo "===== $token đã hoàn tất trước đó, dùng lại $att (không chạy lại)"
  else
    n=1; while [ -e "$LOG_ROOT/$label-attempt$n" ]; do n=$((n+1)); done
    att="$LOG_ROOT/$label-attempt$n"
    echo "===== $(date -u +%FT%TZ) $token EXECUTE -> $att"
    bash "$SOURCE/deployment/run_$s.sh" --package "$P1P2_PACKAGE" --work "$WORK" \
      --execute --approve "$token" --receipt "$RECEIPT" --output "$att"
  fi
  echo "===== $(date -u +%FT%TZ) $token VERIFY (B11)"
  METHOD=$method ROUND=$round ATTEMPT=$att bash /workspace/runpod_ops/32_verify_scope.sh | tee "$LOG_ROOT/verify_$label.txt"
  echo "===== $(date -u +%FT%TZ) $token COLLECT (B16)"
  if [ -e "$RETURN_ROOT/$label/RESULTS_SHA256SUMS.txt" ]; then
    echo "===== $label đã collect trước đó, giữ nguyên"
    sha256sum "$RETURN_ROOT/$label/RESULTS_SHA256SUMS.txt" | tee "$LOG_ROOT/collect_$label.txt"
  else
    ATTEMPT=$att RETURN_LABEL=$label bash /workspace/runpod_ops/33_collect.sh | tee "$LOG_ROOT/collect_$label.txt"
  fi
  sha=$(tail -n1 "$LOG_ROOT/collect_$label.txt" | cut -c1-64)
  acc=$(grep -F 'strict D_dev' "$LOG_ROOT/verify_$label.txt")
  echo "$label $RETURN_ROOT/$label $sha | $acc" >> "$LOG_ROOT/RESULTS_SUMMARY.txt"
done
echo PASS > "$STATUS"
echo "===== CHAIN $run PASS"
