#!/usr/bin/env bash
# Chạy live S1→S3 cho một method + seed rồi đóng gói kết quả kèm SHA.
#   bash 61_seed_job.sh P1-DEFICIT 42
# Không xóa lock, không retry. Chạy lại cùng lệnh sẽ resume (--resume) sau khi đã xem log.
source /workspace/env.sh
set -euo pipefail
method=$1; seed=$2
case "$method" in P1-DEFICIT|P1P2) ;; *) echo "method sai"; exit 2;; esac
case "$seed" in 42|2026) ;; *) echo "seed chỉ nhận 42 hoặc 2026"; exit 2;; esac
label="$method-seed$seed"
base="$LOG_ROOT/seeds/$label"; mkdir -p "$base"
n=1; while [ -e "$base/attempt$n" ]; do n=$((n+1)); done
out="$base/attempt$n"; mkdir "$out"
lock="$MANUAL/runs/p1p2_integration/${method}_seed$seed/.controller.lock"
[ ! -e "$lock" ] || { echo "Lock tồn tại: $lock — không tự xóa, xem lại log trước"; exit 3; }
LEGACY=$("$P1P2_PYTHON" -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["windows_manual_root"])' \
  "$P1P2_PACKAGE/manifests/path_mapping_manifest.json")
echo "$(date -u +%FT%TZ) START $label -> $out"
cd "$MANUAL"
"$P1P2_PYTHON" -B -c 'import torch; assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()'
set +e
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 \
"$P1P2_PYTHON" -B scripts/run_p1_p2.py --manual-root "$MANUAL" --legacy-windows-root "$LEGACY" \
  --method "$method" --seed "$seed" --rounds all --resume --backend hf --dtype bf16 \
  --micro-batch 1 --nll-batch 1 --eval-batch 1 > "$out/execution.log" 2>&1
rc=$?; set -e
echo "$rc" > "$out/exit_code.txt"
tail -n 3 "$out/execution.log"
[ "$rc" = 0 ] && grep -q '^P1P2_CONTROLLER=PASS' "$out/execution.log" || { echo "$(date -u +%FT%TZ) FAIL $label rc=$rc"; exit 1; }

# Đóng gói: giữ nguyên đường dẫn tương đối như bundle seed 13, bỏ .controller.lock
dest="$RETURN_ROOT/seed$seed-$method"
[ ! -e "$dest" ] || { echo "Đã có $dest — không ghi đè"; exit 4; }
mkdir -p "$dest"
M=P2/experiments/week2September/manual
(cd "$WORK" && find "$M/runs/p1p2_integration/${method}_seed$seed" \
    "$M/models/p1p2_integration/${method}_seed$seed" \
    "$M/reports/p1p2_integration/capability_state/${method}_seed$seed" \
    "$M"/reports/p1p2_integration/capability_sidecars/"${method}_seed${seed}"_S* \
    -type f ! -name .controller.lock -print0 | rsync -a --from0 --files-from=- ./ "$dest/")
cp -a "$out" "$dest/operator"
(cd "$dest" && find . -type f ! -name RESULTS_SHA256SUMS.txt -printf '%P\n' | sort | xargs -d '\n' sha256sum > RESULTS_SHA256SUMS.txt)
sha=$(sha256sum "$dest/RESULTS_SHA256SUMS.txt" | cut -c1-64)
for k in 1 2 3; do
  s="$dest/$M/runs/p1p2_integration/${method}_seed$seed/S$k/eval_dev.summary.json"
  acc=$("$P1P2_PYTHON" -B -c 'import json,sys; d=json.load(open(sys.argv[1])); print("%d/%d = %.1f%%" % (d["n_valid"], d["n_problems"], d["accuracy"]*100))' "$s")
  echo "seed$seed-$method S$k $dest $sha | strict D_dev = $acc" | tee -a "$LOG_ROOT/seeds/RESULTS_SUMMARY.txt"
done
echo "$(date -u +%FT%TZ) DONE $label"
