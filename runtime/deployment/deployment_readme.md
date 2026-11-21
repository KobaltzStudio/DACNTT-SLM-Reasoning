# RunPod deployment and execution handoff

**Windows staging verified. Linux verification PENDING. G9 NOT RUN / DELEGATED.** Commands below are for the operator after separate approval. The repository's current scope is CPU-only.

## Upload the sealed package

Use the directory handed off by the local report. Its layout is `P2/experiments/week2September/manual`, `P2/integration_staging`, `deployment`, and `manifests`. Keep these relative paths. Upload from a host with rsync/SSH, or a trusted file-transfer client that preserves bytes. The operator selects a fresh persistent-volume directory. Do not merge into an existing experiment or run a Git checkout over the package. Compare the checksum file's SHA with the trusted local handoff, independently of the upload.

```bash
# Set LOCAL_PACKAGE, RUNPOD_SSH and a fresh absolute REMOTE_PACKAGE first.
: "${LOCAL_PACKAGE:?local sealed package path required}"
: "${RUNPOD_SSH:?approved RunPod SSH host required}"
: "${REMOTE_PACKAGE:?fresh remote package directory required}"
rsync -rt --checksum --ignore-existing -- "$LOCAL_PACKAGE/" "$RUNPOD_SSH:$REMOTE_PACKAGE/"
```

## Linux CPU acceptance before any model command

Use Python 3.11 in an isolated environment with the packaged `P2/requirements-lock.txt`. Resolve Linux x86_64 wheels and approved image/driver availability before execution. The Windows reference is torch 2.13.0+cu126, transformers 5.15.0, peft 0.20.0, accelerate 1.14.0, safetensors 0.8.0, PyYAML 6.0.3 and matplotlib 3.11.2. Pin the lock and record Linux wheel versions. With an approved wheelhouse, prefer `python -m pip install --no-index --find-links "$WHEELHOUSE" -r P2/requirements-lock.txt`. Use the HF backend. vLLM is outside this handoff.

Stage the model cache independently. The pinned Student is `Qwen/Qwen2.5-1.5B-Instruct` revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, with tokenizer at the same revision. The previous approved model weight SHA-256 is `dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee`. Verify cache paths and symlinks/blobs and `model.safetensors` SHA at destination; cache and weights are deliberately outside this package. Use offline environment variables. Record writable storage, filesystem behavior (atomic publish, hard links, exclusive locks), driver and GPU memory after authorization. Prior Windows reference was about 7.52 GiB reserved at A S1, so reserve margin on a BF16-capable GPU.

```bash
set -euo pipefail
: "${PACKAGE:?absolute package root required}"
: "${SUMS_SHA:?trusted SHA256SUMS.txt digest from local handoff required}"
: "${HF_HOME:?verified HF cache path required}"
cd "$PACKAGE"
printf '%s  %s\n' "$SUMS_SHA" manifests/SHA256SUMS.txt | sha256sum -c -
sha256sum -c manifests/SHA256SUMS.txt
python --version
python -m pip check
export MANUAL_ROOT="$PACKAGE/P2/experiments/week2September/manual"
export LEGACY_WINDOWS_ROOT='C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual'
export HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
cd "$MANUAL_ROOT"
common=(--manual-root "$MANUAL_ROOT" --legacy-windows-root "$LEGACY_WINDOWS_ROOT" --seed 13
        --resume --backend hf --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1)
CUDA_VISIBLE_DEVICES='' python -B -m unittest discover -s tests -v
CUDA_VISIBLE_DEVICES='' python -B scripts/run_final_d_test.py --audit-only
CUDA_VISIBLE_DEVICES='' python -B scripts/run_p1_p2.py "${common[@]}" --method P1-DEFICIT --round 1 --dry-run
CUDA_VISIBLE_DEVICES='' python -B scripts/run_p1_p2.py "${common[@]}" --method P1P2 --round 1 --dry-run
CUDA_VISIBLE_DEVICES='' python -B scripts/run_p1_p2.py "${common[@]}" --method P1-DEFICIT --round 2 --dry-run
CUDA_VISIBLE_DEVICES='' python -B scripts/run_p1_p2.py "${common[@]}" --method P1P2 --from-checkpoint S1 --to-checkpoint S3 --dry-run
```

Expected actions in order: 0, 0, 4, 16. Windows-native archive fixture may skip on Linux. A S2 must recognize 75 rows and a completed adapter, then plan dev evaluation, checkpoint log, hook and state. B S2/S3 must use S1/S2 adapter lineage and fresh checkpoint-specific NLL. The final D_test audit is ID/SHA-only. Check Linux GPU only after authorization using `nvidia-smi` and `python -c 'import torch; assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()'`.

## Separately proposed live jobs

Keep a transcript of each command and its real exit code. Execute only the approved one-checkpoint block, and verify it before advancing. Re-run the matching dry-run immediately before each job. Do not use `--rounds all` for B.

```bash
# Approved A S2 only: use the saved adapter, continue D_dev from 75/500.
python -B scripts/run_p1_p2.py "${common[@]}" --method P1-DEFICIT --round 2

# Only after A S2 audit and S3 approval.
python -B scripts/run_p1_p2.py "${common[@]}" --method P1-DEFICIT --round 3

# Approved B S2 only: compute NLL at S1 and train from S1.
python -B scripts/run_p1_p2.py "${common[@]}" --method P1P2 --round 2

# Only after B S2 audit and S3 approval; compute NLL at S2.
python -B scripts/run_p1_p2.py "${common[@]}" --method P1P2 --round 3
```

After each checkpoint, verify selection log/train set, adapter config/weights/train log, round/checkpoint log with parent SHA, eval intent and 500 distinct dev IDs with strict summary, hook sidecar for 85 Gold IDs and seven capabilities, and capability state. Scores for G7 use D_dev_select only. Record output artifacts, environment and telemetry. On failure retain logs, .controller.lock/provenance and staged partial bytes; inspect process ownership. Never delete or truncate output or automatically clear stale locks. Resume only with the same checkpoint-bounded command after identifying a safe validated stage, with the relevant approval. A valid S2 adapter should not be trained twice.

```bash
# Read-only recovery inspection; choose the exact approved method/round in the preceding block.
ps -eo pid,ppid,lstart,args | grep -E 'run_p1_p2|eval_student|train_round|compute_nll'
find runs/p1p2_integration -name .controller.lock -print
wc -l runs/p1p2_integration/P1-DEFICIT_seed13/S2/eval_dev.jsonl
sha256sum runs/p1p2_integration/P1-DEFICIT_seed13/S2/eval_dev.intent.json
```

## Final analysis and guarded D_test

After all required P1/P2 candidates are complete and validated, generate G6/G7/G8 in a new analysis namespace. Verify G7 JSON contains FINAL with all candidates. Have the reviewer record its SHA, policy and winners out of band before any test access. D_test can never be used for checkpoint selection or tuning.

```bash
: "${ANALYSIS_DIR:?new analysis directory required}"
python -B scripts/build_capability_learning_dynamics.py --manual "$MANUAL_ROOT" --legacy-windows-root "$LEGACY_WINDOWS_ROOT" --output "$ANALYSIS_DIR/g6"
python -B scripts/select_checkpoint_on_dev.py --manual-root "$MANUAL_ROOT" --output "$ANALYSIS_DIR/g7"
python -B scripts/build_p1p2_analysis_figures.py --manual-root "$MANUAL_ROOT" --output "$ANALYSIS_DIR/g8"
sha256sum "$ANALYSIS_DIR/g7/checkpoint_selection_seed13.json"
```

The final-test evaluator fingerprint is in `manifests/d_test_input_audit.json`. The wrapper re-derives G7 from D_dev_select, verifies the external pins and checkpoint SHA, checks the held-out split and refuses collisions. Separate authorization is required for each final test method. The wrapper accepts P1-DEFICIT and P1P2. Historical B4/B5 selection evidence is preserved; B4/B5 final test would require its own approved physical adapter provenance flow.

```bash
# Documentation only. Run after separate approval and out-of-band recording of G7 SHA.
: "${G7_FROZEN_SHA:?reviewer-pinned FINAL G7 manifest SHA required}"
: "${EVALUATOR_SHA:?approved evaluator fingerprint from package audit required}"
: "${FINAL_METHOD:?P1-DEFICIT or P1P2 as approved}"
python -B scripts/run_final_d_test.py --execute --method "$FINAL_METHOD" \
  --selection "$ANALYSIS_DIR/g7/checkpoint_selection_seed13.json" \
  --selection-sha256 "$G7_FROZEN_SHA" --evaluator-sha256 "$EVALUATOR_SHA"
```

Outputs are under `reports/p1p2_integration/final_d_test/<method>_seed13_<checkpoint>/`. Expect `predictions.jsonl`, `summary.json` and `provenance.json` with strict accuracy, Wilson 95% interval, counts, settings and input/output digests. A failed run may retain a sibling .pending directory. Preserve it for review. D_TEST_EXECUTION=NOT_RUN for local readiness.

## Return to Windows

Prepare an explicit transfer list of newly completed checkpoints, prediction/summary/intent, sidecars/states, NLL provenance, analysis, logs and a SHA manifest rooted at the package. Return to a fresh `reports/p1p2_integration/incoming_runpod/<timestamp>` staging directory, verify each SHA and parent fingerprint, and preserve original bytes and manifests. Compare Run A S2's initial 75 rows byte-for-byte with the original prefix; stop if the preserved prefix bytes differ. Promote only after review and separate approval, leaving the original partial prediction and protected artifacts available. Keep the Linux manual root stable for outputs containing Linux absolute locators; cross-host uses of new Linux artifacts require an explicit import mapping and verification.
