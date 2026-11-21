#!/usr/bin/env bash
if [[ ${BASH_SOURCE[0]} != "$0" ]]; then
  return 0
fi
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec "${P1P2_PYTHON:-python}" -B "$here/ops.py" preflight "$@"
