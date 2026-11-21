#!/usr/bin/env bash
# Run the main experiment for one training seed on a pod: S_0 first, then each method in order.
#
# Usage (on the pod, inside tmux, from anywhere):
#   bash scripts/run_all.sh 13                  # S_0, then B5 B4 B2 B3 for seed 13
#   bash scripts/run_all.sh 42 B5 B4            # only some methods, in this order
#
# Environment variables (all optional):
#   RUNS_DIR=runs/main     output directory (keep the pilot apart: RUNS_DIR=runs/pilot is NOT a pilot run)
#   EXTRA_ARGS="..."       passed to every run_experiment.py call, e.g. "--backend hf --eval-batch 32" or "--dry-run"
#   B2_NLL=1               score S_1, S_2 for B2 too (T7-7 sensitivity analysis)
#   RETRIES=1              how many times a failed method is re-run before stopping (finished steps are skipped)
#   SKIP_SETUP=1           do not source setup_pod.sh (local dry run only)
#   NOTIFY=0               do not e-mail at the end (by default a mail is sent when .env exists; see .env.example)
#
# E-mail: when the script ends (finished, failed or stopped with Ctrl+C), scripts/notify_email.py sends the result
# and the last log lines to MAIL_TO from .env. A pod that is killed or loses power cannot send anything.
#
# B5 runs before B4 so that B4 reuses S_1 (task7_decisions.md). Every call is resumable: after an interruption,
# run the same command again. S_0 is computed once per RUNS_DIR; a lock file keeps two processes that share the
# same volume from computing it at the same time. With one volume per pod, either let each pod compute S_0
# or copy runs/main/S0/ from the first pod before starting (all methods must use the same S_0).
# Output: one log per seed in $RUNS_DIR/log_seed<SEED>.txt, step durations in $RUNS_DIR/timing.jsonl.

MANUAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$MANUAL_DIR" || exit 1

SEED="${1:-}"
if [ -z "$SEED" ]; then
    echo "usage: bash scripts/run_all.sh SEED [METHOD ...]" >&2
    exit 2
fi
shift
if [ "$#" -gt 0 ]; then METHODS=("$@"); else METHODS=(B5 B4 B2 B3); fi

# setup_pod.sh activates the venv; source it before 'set -u' (activate scripts read unset variables).
if [ "${SKIP_SETUP:-0}" != "1" ]; then
    # shellcheck disable=SC1091
    source scripts/setup_pod.sh || { echo "setup_pod.sh failed" >&2; exit 1; }
fi
set -uo pipefail

RUNS_DIR="${RUNS_DIR:-runs/main}"
RETRIES="${RETRIES:-1}"
read -r -a EXTRA <<< "${EXTRA_ARGS:-}"
PY="${PYTHON:-python}"
mkdir -p "$RUNS_DIR"
LOG="$RUNS_DIR/log_seed$SEED.txt"
exec > >(tee -a "$LOG") 2>&1

STATUS="STOPPED"   # becomes FINISHED or FAILED below; stays STOPPED on Ctrl+C or an unexpected exit
START_TS=$(date +%s)

summary_lines() {
    for m in "${METHODS[@]}"; do
        f="$RUNS_DIR/${m}_seed${SEED}/S3/eval_test.jsonl"
        if [ -s "$f" ]; then echo "  $m: S3 eval_test present ($(wc -l < "$f") rows)"; else echo "  $m: not finished"; fi
    done
}

notify() {
    [ "${NOTIFY:-1}" = "1" ] && [ -f .env ] || return 0
    local hours body
    hours=$(awk "BEGIN {printf \"%.1f\", ($(date +%s) - $START_TS) / 3600}")
    body="run_all.sh seed $SEED ($RUNS_DIR): $STATUS after $hours h
methods: ${METHODS[*]}
$(summary_lines)"
    "$PY" scripts/notify_email.py --subject "[DACNTT] seed $SEED $STATUS ($hours h)" --body "$body" \
        --log "$LOG" --log-lines 40 || echo "!!! e-mail not sent (see message above)"
}
trap notify EXIT

echo "=== run_all.sh seed $SEED methods ${METHODS[*]} | $(date -Is) | host $(uname -n)"
echo "config sha256 $(sha256sum config/experiment_config.json | cut -d' ' -f1)"
command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

run_method() {  # method -> 0 when finished
    local m="$1" attempt=0 extra=()
    [ "$m" = "B2" ] && [ "${B2_NLL:-0}" = "1" ] && extra=(--b2-nll)
    while :; do
        echo "--- $m seed $SEED (attempt $((attempt + 1))) $(date -Is)"
        if "$PY" scripts/run_experiment.py --method "$m" --seed "$SEED" --runs-dir "$RUNS_DIR" \
                "${extra[@]}" "${EXTRA[@]}"; then
            return 0
        fi
        attempt=$((attempt + 1))
        if [ "$attempt" -gt "$RETRIES" ]; then
            return 1
        fi
        echo "!!! $m failed, retrying (finished steps are skipped)"
        sleep 30
    done
}

# S_0 once per RUNS_DIR (B0 = evaluation and NLL of the base Student only).
echo "--- S_0 $(date -Is)"
if ! flock "$RUNS_DIR/.s0.lock" "$PY" scripts/run_experiment.py --method B0 --seed "$SEED" \
        --runs-dir "$RUNS_DIR" "${EXTRA[@]}"; then
    echo "!!! S_0 failed: stop. Send the last lines of $LOG."
    STATUS="FAILED"
    exit 1
fi

FAILED=()
for m in "${METHODS[@]}"; do
    if ! run_method "$m"; then
        FAILED+=("$m")
        echo "!!! $m failed after $((RETRIES + 1)) attempts: stop here (later methods not started)."
        break
    fi
done

echo "=== summary seed $SEED | $(date -Is)"
summary_lines
if [ "${#FAILED[@]}" -eq 0 ]; then STATUS="FINISHED"; else STATUS="FAILED (${FAILED[*]})"; exit 1; fi
