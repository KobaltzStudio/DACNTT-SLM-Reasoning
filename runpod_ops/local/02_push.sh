#!/usr/bin/env bash
# Tạo intake mới trên pod và chuyển runtime + source + script (B4).
set -euo pipefail
HANDOFF=$(cd "$(dirname "$0")/../.." && pwd)
OPS="$HANDOFF/runpod_ops"
ssh runpod-p1p2 'set -e; test -d /workspace && test -w /workspace; df -h /workspace
  umask 077
  mkdir /workspace/intake
  mkdir /workspace/intake/runtime /workspace/intake/source /workspace/intake/hf
  mkdir /workspace/intake/hf/hub /workspace/intake/logs /workspace/runpod_ops'
# 2 file .sh bị git đổi CRLF -> LF; seal cần bản CRLF. Gửi bản CRLF (SHA khớp seal) riêng.
CRLF=(P2/experiments/week2September/manual/scripts/run_all.sh P2/experiments/week2September/manual/scripts/setup_pod.sh)
rsync -rt --checksum --ignore-existing ${CRLF[@]/#/--exclude=/} -- "$HANDOFF/runtime/" runpod-p1p2:/workspace/intake/runtime/
for f in "${CRLF[@]}"; do
  sed 's/$/\r/' "$HANDOFF/runtime/$f" | ssh runpod-p1p2 "cat > '/workspace/intake/runtime/$f'"
done
ssh runpod-p1p2 'cd /workspace/intake/runtime && sha256sum --quiet -c manifests/SHA256SUMS.txt && echo "Pod runtime: toàn bộ SHA256SUMS OK"'
rsync -rt --checksum --ignore-existing -- "$HANDOFF/github/"  runpod-p1p2:/workspace/intake/source/
rsync -rt -- "$OPS/pod/" runpod-p1p2:/workspace/runpod_ops/
ssh runpod-p1p2 'cp /workspace/runpod_ops/env.sh /workspace/env.sh && chmod +x /workspace/runpod_ops/*.sh && ls /workspace/intake /workspace/runpod_ops'
echo "PUSH DONE"
