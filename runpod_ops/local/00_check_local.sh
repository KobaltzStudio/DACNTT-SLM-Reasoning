#!/usr/bin/env bash
# Kiểm tra handoff trên máy bạn trước khi gửi lên pod.
set -euo pipefail
HANDOFF=$(cd "$(dirname "$0")/../.." && pwd)
cd "$HANDOFF/runtime"
printf '%s  %s\n' \
  bf0c50c301de9e2b78d9533a6a995733a431a6834d8ad019926e1c826af07798 manifests/SHA256SUMS.txt \
  dbe0d5bb0b2b80df5d0b4f41ff57b3318a543c264e2d5b20c5c7f818e0424f62 manifests/RUNPOD_PACKAGE_MANIFEST.json |
  sha256sum -c -
CRLF="P2/experiments/week2September/manual/scripts/run_all.sh P2/experiments/week2September/manual/scripts/setup_pod.sh"
grep -vF -e "${CRLF%% *}" -e "${CRLF##* }" manifests/SHA256SUMS.txt | sha256sum --quiet -c - && echo "runtime: 653 file khớp seal"
for f in $CRLF; do  # git đổi 2 file này sang LF; bản CRLF phải khớp seal
  want=$(grep -F "  $f" manifests/SHA256SUMS.txt | cut -c1-64)
  got=$(sed 's/$/\r/' "$f" | sha256sum | cut -c1-64)
  [ "$want" = "$got" ] && echo "CRLF OK: $f" || { echo "SAI: $f"; exit 1; }
done
echo "source github/: $(find "$HANDOFF/github" -type f | wc -l) file (phải là 63)"
sha256sum "$HANDOFF/github/manifests/GITHUB_RELEASE_MANIFEST.json"
