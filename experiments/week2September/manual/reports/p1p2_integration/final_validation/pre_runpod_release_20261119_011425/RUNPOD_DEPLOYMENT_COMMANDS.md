# RunPod commands — approval-gated handoff

All commands below are instructions for the approved operator. There was no upload, transfer, RunPod connection, Linux execution or GPU job in this audit. Use a fresh Linux release and a distinct writable work tree. Record a transcript and exit status for every accepted phase.

## 1. Transfer after approval

Set LOCAL_PACKAGE to the sealed local package, CACHE_SOURCE_HUB to the transfer host's mount of the verified Windows HF hub cache, and AUDIT_DIR to this audit directory. Set RUNPOD_SSH, REMOTE_PACKAGE, REMOTE_AUDIT_DIR and REMOTE_HF_HOME for the separately approved endpoint and persistent volume. Create fresh target directories first. Transfer the audit instructions and cache checksum list separately from the sealed release.

```bash
set -euo pipefail
: "${LOCAL_PACKAGE:?local package required}"
: "${CACHE_SOURCE_HUB:?mounted verified HF hub directory required}"
: "${AUDIT_DIR:?release audit directory required}"
: "${RUNPOD_SSH:?approved SSH endpoint required}"
: "${REMOTE_PACKAGE:?fresh Linux package path required}"
: "${REMOTE_AUDIT_DIR:?separate Linux audit path required}"
: "${REMOTE_HF_HOME:?fresh dedicated Linux HF cache path required}"
rsync -rt --checksum --ignore-existing -- "$LOCAL_PACKAGE/" "$RUNPOD_SSH:$REMOTE_PACKAGE/"
rsync -rt --checksum --ignore-existing -- "$AUDIT_DIR/MODEL_CACHE_SHA256SUMS.txt" "$RUNPOD_SSH:$REMOTE_AUDIT_DIR/"
cut -c67- "$AUDIT_DIR/MODEL_CACHE_SHA256SUMS.txt" |
  rsync -rt --copy-links --checksum --ignore-existing --files-from=- -- "$CACHE_SOURCE_HUB/" "$RUNPOD_SSH:$REMOTE_HF_HOME/hub/"
```

## 2. Verify Linux CPU inputs

Set PACKAGE to the transferred sealed tree, CACHE_SUMS to the separately transferred checksum list, HF_HOME to the verified transfer destination, and WORK_ROOT to a fresh absolute path for execution. Use a preapproved Linux Python 3.11 virtual environment; if installation is needed, use its approved wheelhouse with the package lock. Keep the execution cwd on the work copy.

```bash
set -euo pipefail
: "${PACKAGE:?sealed Linux package path required}"
: "${CACHE_SUMS:?absolute path to separate cache checksum list required}"
: "${HF_HOME:?dedicated Linux HF cache required}"
: "${WORK_ROOT:?fresh operational copy path required}"
cd "$PACKAGE"
printf '%s  %s\n' 'bf0c50c301de9e2b78d9533a6a995733a431a6834d8ad019926e1c826af07798' manifests/SHA256SUMS.txt |
  sha256sum -c -
printf '%s  %s\n' 'dbe0d5bb0b2b80df5d0b4f41ff57b3318a543c264e2d5b20c5c7f818e0424f62' manifests/RUNPOD_PACKAGE_MANIFEST.json |
  sha256sum -c -
sha256sum -c manifests/SHA256SUMS.txt
printf '%s  %s\n' '97b5db3ae70d9a73a0961c2c56424eff49cb8da9324d455356c8c049adb31630' "$CACHE_SUMS" |
  sha256sum -c -
export HF_HOME HF_HUB_CACHE="$HF_HOME/hub" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
(cd "$HF_HUB_CACHE"; sha256sum -c "$CACHE_SUMS")
python --version
# If needed in the approved venv, use the approved wheelhouse:
# python -m pip install --no-index --find-links "$WHEELHOUSE" -r P2/requirements-lock.txt
python -m pip check
CUDA_VISIBLE_DEVICES='' python -B -c 'import torch, transformers, peft, accelerate, tokenizers, safetensors, yaml, matplotlib; print(torch.__version__, torch.version.cuda)'
CUDA_VISIBLE_DEVICES='' python -B - <<'PY'
from pathlib import Path
from huggingface_hub import try_to_load_from_cache
names = ("config.json", "generation_config.json", "merges.txt", "model.safetensors",
         "tokenizer.json", "tokenizer_config.json", "vocab.json")
for name in names:
    path = try_to_load_from_cache("Qwen/Qwen2.5-1.5B-Instruct", name,
                                 revision="989aa7980e4cf806f80c7fef2b1adb7bc71aa306")
    if not isinstance(path, str) or not Path(path).is_file():
        raise SystemExit(f"Missing offline Student file: {name}")
PY
if [ -e "$WORK_ROOT" ] || [ -L "$WORK_ROOT" ]; then
  printf '%s\n' "Refusing existing work path" >&2
  exit 1
fi
mkdir -- "$WORK_ROOT"
cp -a -- "$PACKAGE/P2" "$WORK_ROOT/"
(cd "$WORK_ROOT"; awk 'substr($0,67,3)=="P2/"' "$PACKAGE/manifests/SHA256SUMS.txt" | sha256sum -c -)
df -Pk -- "$WORK_ROOT" "$HF_HUB_CACHE"
export MANUAL_ROOT="$WORK_ROOT/P2/experiments/week2September/manual"
export LEGACY_WINDOWS_ROOT='C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual'
cd "$MANUAL_ROOT"
test -w "$MANUAL_ROOT/runs/p1p2_integration"
test -w "$MANUAL_ROOT/models/p1p2_integration"
test -w "$MANUAL_ROOT/reports/p1p2_integration"
common=(--manual-root "$MANUAL_ROOT" --legacy-windows-root "$LEGACY_WINDOWS_ROOT" --seed 13
        --resume --backend hf --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1)
CUDA_VISIBLE_DEVICES='' python -B -m unittest discover -s tests -v
CUDA_VISIBLE_DEVICES='' python -B scripts/run_final_d_test.py --audit-only
CUDA_VISIBLE_DEVICES='' python -B scripts/run_p1_p2.py "${common[@]}" --method P1-DEFICIT --round 1 --dry-run
CUDA_VISIBLE_DEVICES='' python -B scripts/run_p1_p2.py "${common[@]}" --method P1P2 --round 1 --dry-run
CUDA_VISIBLE_DEVICES='' python -B scripts/run_p1_p2.py "${common[@]}" --method P1-DEFICIT --round 2 --dry-run
CUDA_VISIBLE_DEVICES='' python -B scripts/run_p1_p2.py "${common[@]}" --method P1P2 --from-checkpoint S1 --to-checkpoint S3 --dry-run
```

Expect 0/0/4/16 actions. Windows-native fixture may skip on Linux. Stop if an unexpected subprocess is planned, A S2 plans train or S3, B plan uses NLL S0 for S2/S3, or a path, split or fingerprint is inconsistent. Linux acceptance requires actual Linux evidence.

## 3. Bounded actions after Linux acceptance and separate job approval

These are four separately approved commands. Run the matching dry-run immediately before each one-checkpoint job. Stop at each point and validate the completed checkpoint. Request authorization for GPU preflight as well as the jobs.

```bash
# GPU preflight, only after approval.
nvidia-smi
python -B -c 'import torch; print(torch.__version__, torch.version.cuda); assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()'
# A S2 only, reuse adapter and evaluate the remaining 425 D_dev IDs.
python -B scripts/run_p1_p2.py "${common[@]}" --method P1-DEFICIT --round 2
# A S3 only after A S2 PASS and separate approval.
python -B scripts/run_p1_p2.py "${common[@]}" --method P1-DEFICIT --round 3
# B S2 only, fresh S1 NLL and S1 adapter parent.
python -B scripts/run_p1_p2.py "${common[@]}" --method P1P2 --round 2
# B S3 only after B S2 PASS and separate approval, fresh S2 NLL.
python -B scripts/run_p1_p2.py "${common[@]}" --method P1P2 --round 3
```

For each completed stage expect 500 unique D_dev predictions, summary, selection pair, NLL where applicable, train log, adapter, checkpoint log, sidecar and valid capability state. Rerun its bounded command with --dry-run and require zero planned actions. Check the original 75 A S2 rows on the sealed package as a byte-for-byte prefix of the final file.

```bash
prefix='runs/p1p2_integration/P1-DEFICIT_seed13/S2/eval_dev.jsonl'
reference="$PACKAGE/P2/experiments/week2September/manual/$prefix"
cmp -n "$(wc -c < "$reference")" -- "$reference" "$MANUAL_ROOT/$prefix"
test "$(wc -l < "$MANUAL_ROOT/$prefix")" -eq 500
```

On interruption, preserve logs, intent, lock and partial outputs. Verify PID ownership, SHA, newline boundary, unique IDs and checkpoint tags before a bounded resume. Escalate a stale lock, partial checkpoint or fingerprint conflict for review. Use a new staging directory for any corrective transfer.

## 4. Analysis and return to Windows

After all required checkpoints, generate G6/G7/G8 at a new analysis path, using the existing commands from the sealed deployment guide. Freeze G7 FINAL and have a reviewer pin its SHA in an independent record. The separate D_test command in the deployment guide requires that pin, evaluator fingerprint and approval; the unified controller never calls it.

Give the operator an explicit RELEASE_RESULTS allowlist of generated regular paths relative to WORK_ROOT, including provenance, commands/output logs and SHA manifest. Verify the returned files before import or comparison on Windows. The original P2 manual root, adapters and partial predictions stay in place throughout. Use a fresh destination and do not use rsync --delete.

```bash
# On the approved operator host with the WORK_ROOT available, generate a transfer checksum file.
: "${RELEASE_RESULTS:?vetted relative-path allowlist required}"
: "${RETURN_SUMS:?absolute new results checksum path required}"
(set -o noclobber; cd "$WORK_ROOT"; while IFS= read -r path; do sha256sum -- "$path"; done < "$RELEASE_RESULTS" > "$RETURN_SUMS")
sha256sum -- "$RETURN_SUMS"
# From the receiving host or its mounted transfer environment:
: "${INCOMING:?fresh Windows incoming directory required}"
: "${RETURN_SUMS_SHA:?trusted remote result manifest SHA required}"
mkdir -- "$INCOMING"
rsync -rt --checksum --ignore-existing --files-from="$RELEASE_RESULTS" -- "$RUNPOD_SSH:$WORK_ROOT/" "$INCOMING/"
rsync -rt --checksum --ignore-existing -- "$RUNPOD_SSH:$RETURN_SUMS" "$INCOMING/.results-sha256.txt"
(cd "$INCOMING"; printf '%s  %s\n' "$RETURN_SUMS_SHA" .results-sha256.txt | sha256sum -c -; sha256sum -c .results-sha256.txt)
```

Verify new Linux outputs under the same operational root for bounded resume. Importing new absolute Linux locators back to Windows requires explicit review; never rewrite old signed outputs or silently promote a returned checkpoint.
