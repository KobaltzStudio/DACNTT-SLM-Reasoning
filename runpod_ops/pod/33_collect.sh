#!/usr/bin/env bash
# Trích nguyên văn từ docs/RUNPOD_EXECUTION_GUIDE.md (B16 collect). Dùng: ATTEMPT=$LOG_ROOT/a-s2-attempt1 RETURN_LABEL=a-s2 bash 33_collect.sh
source /workspace/env.sh
export RETURN_ROOT="${RETURN_ROOT:-/workspace/intake/returns}"
set -euo pipefail
: "${ATTEMPT:?set PASS checkpoint attempt directory}"
: "${RETURN_ROOT:?set persistent transfer directory outside work and package}"
: "${RETURN_LABEL:?set a fresh label, e.g. a-s2}"
mkdir -p "$RETURN_ROOT"
bash "$SOURCE/deployment/collect_results.sh" --package "$P1P2_PACKAGE" \
  --receipt "$ATTEMPT/execution.json" --output "$RETURN_ROOT/$RETURN_LABEL"
sha256sum "$RETURN_ROOT/$RETURN_LABEL/RESULTS_SHA256SUMS.txt"
