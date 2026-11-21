# RunPod operator commands

Use these commands only in the approved handoff environment. The runtime under `runtime/` is the immutable input package. The seven base Student cache files are transferred separately. The code is under the canonical manual layout retained inside the release.

## Before any job

From the approved receiving host, set the following to existing verified paths except for WORK and output folders. Use a Linux Python 3.11 virtual environment and a dedicated writable volume. Keep disk margin for the copy, caches, logs and new adapters. Python package versions are checked; a mismatch or missing version blocks setup.

```bash
export HANDOFF=/path/to/unified-handoff
export P1P2_PACKAGE="$HANDOFF/runtime"
export P1P2_PYTHON=/path/to/venv/bin/python
export HF_HOME=/path/to/dedicated-student-cache
export HF_HUB_CACHE="$HF_HOME/hub"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
WORK=/path/to/fresh-operational-root
LOG_ROOT=/path/to/existing-log-root
bash "$HANDOFF/deployment/verify_package.sh"
bash "$HANDOFF/deployment/verify_model_cache.sh"
bash "$HANDOFF/deployment/setup_environment.sh" --work "$WORK"
bash "$HANDOFF/deployment/linux_cpu_preflight.sh" --work "$WORK" --output "$LOG_ROOT/cpu-preflight"
```

The setup command copies verified P2 files into a fresh work root. It does not install packages unless explicitly given `--install-offline WHEELHOUSE` on Linux in the approved Python 3.11 venv. Match the sealed dependency lock and run pip check. Work and evidence destinations must be separate from the sealed tree. Allow extra disk for outputs; `--min-free-bytes` defaults to 2 GiB on each relevant local filesystem. The full transferred package plus one work copy and base cache needs about 4.25 GB before wheelhouse and output. The CPU check hides GPU, runs 103 tests and checks action counts 0/0/4/16. Windows may rehearse only; an execution receipt must say Linux with the matching package, work root and interpreter. See [handoff](../docs/HANDOFF_FOR_RUNPOD_OPERATOR.md) for input policy, CUDA and transfer.

## One scope at a time

With just `--work "$WORK"`, any round wrapper prints a read-only plan. Each parent must already pass a zero-action dry-run. A S2 accepts eval/hook/state actions only; it cannot request retraining. B S2/S3 verify the NLL source checkpoint S1/S2. A completely verified round exits without starting a subprocess for the stage.

Each line below requires separate approval. Run **one line**, verify, then obtain approval for the next. Keep the Linux CPU receipt. The token passed to `--approve` is a local scope confirmation, not an authentication secret or a substitute for operator approval.

```bash
RECEIPT="$LOG_ROOT/cpu-preflight/preflight.json"
# A S2 only; uses existing S2 adapter and appends after the 75-row D_dev prefix.
bash "$HANDOFF/deployment/run_a_s2.sh" --work "$WORK" --execute --approve P1-DEFICIT:13:S2 --receipt "$RECEIPT" --output "$LOG_ROOT/a-s2-attempt1"
# A S3 only after A S2 PASS.
bash "$HANDOFF/deployment/run_a_s3.sh" --work "$WORK" --execute --approve P1-DEFICIT:13:S3 --receipt "$RECEIPT" --output "$LOG_ROOT/a-s3-attempt1"
# B S2 only; learnability from S1.
bash "$HANDOFF/deployment/run_b_s2.sh" --work "$WORK" --execute --approve P1P2:13:S2 --receipt "$RECEIPT" --output "$LOG_ROOT/b-s2-attempt1"
# B S3 only after B S2 PASS; learnability from S2.
bash "$HANDOFF/deployment/run_b_s3.sh" --work "$WORK" --execute --approve P1P2:13:S3 --receipt "$RECEIPT" --output "$LOG_ROOT/b-s3-attempt1"
```

Exec is Linux-only and checks offline cache, dependency versions, input checksums, the append-only baseline, free space, a controller lock, plan scope and the approved parent. It checks BF16 CUDA only after explicit execution authorization. The wrapper records intent, log, exit and changed-output SHA. It rechecks pinned inputs/prefix and zero pending work on success. D_dev is the only evaluation split.

## Interrupted jobs and return

Keep the working volume at the same root. Inspect the process tree, lock, intent, execution log and current outputs. Wait if the pipeline is alive. Preserve invalid output and an unexplained lock; investigate before attempting a bounded restart, and use a **new** evidence path. Do not edit a partial JSONL, adapter or lineage to pass a check. A power loss may leave intent/log without a final receipt.

A successful run manifest can be collected into a new return directory. The bundle contains verified stage outputs plus execution evidence. Pin the printed SHA independently and transfer explicitly to a new Windows directory before comparison.

```bash
bash "$HANDOFF/deployment/collect_results.sh" --receipt "$LOG_ROOT/a-s2-attempt1/execution.json" --output /path/to/fresh-return
bash "$HANDOFF/deployment/verify_results.sh" --results /path/to/incoming-return --expected-sha "$TRUSTED_RESULTS_SHA"
```

For multi-attempt resumes the successful execution receipt inventories the complete scoped output set, including changed files inherited from earlier attempts. Keep failure receipts separately. For collision, disk or lineage errors, stop rather than promoting outputs.
