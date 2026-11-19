# Handoff for the RunPod operator

KLTN/DACNTT compares capability-deficit selection (Proposal 1) and Student NLL-based learnability (Proposal 2) for dynamic chain-of-thought distillation. Run A uses P1 only; Run B combines P1/P2. A S1 is PASS 416/500 and B S1 is PASS 406/500. A S2 has a completed 26-step adapter and 75/500 D_dev predictions. A S3 and B S2/S3 are pending. See [protocol](SCIENTIFIC_PROTOCOL.md) and [remaining work](REMAINING_WORK.md).

## Locate and transfer

- Source and tests are under the sealed runtime manual `scripts/` and `tests/`. Config is under manual `config/`. Frozen inputs under `data/`, `splits/`, `trajectory/` use the existing manifest. A/B predictions, NLL and training lineage are under manual `runs/`, `models/`, and `reports/`.
- The base Student is Qwen/Qwen2.5-1.5B-Instruct at `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. Obtain the seven exact files from the approved offline HF cache. The private CSV names source files, sizes, revision and SHA; use the paired SHA file below. Approval covers the host, dataset/privacy scope and transfer window.
- At the transfer host, set HANDOFF to this workspace; set RUNPOD_SSH, REMOTE_HANDOFF, CACHE_SOURCE_HUB and REMOTE_HF_HOME to operator-approved values. Create fresh target paths on persistent storage. The checksum manifest and runtime copy retain original bytes. These commands have not been executed.

```bash
rsync -rt --checksum --ignore-existing --files-from="$HANDOFF/manifests/runpod_files.txt" -- "$HANDOFF/" "$RUNPOD_SSH:$REMOTE_HANDOFF/"
cut -c67- "$HANDOFF/manifests/MODEL_CACHE_SHA256SUMS.txt" |
  rsync -rt --copy-links --checksum --ignore-existing --files-from=- -- "$CACHE_SOURCE_HUB/" "$RUNPOD_SSH:$REMOTE_HF_HOME/hub/"
```

## Verify, execute and return

At the Linux host, use approved Python 3.11, dependency lock and compatible CUDA 12.6 wheel / driver. BF16 HF LoRA is the frozen path. Verify real free space and target filesystem semantics. The existing Windows A S1 run reached around 7.52 GiB reserved; allow GPU margin. Follow [RunPod commands](../deployment/README_RUNPOD.md) for the package and cache pin checks, optional offline wheelhouse setup, writable copy, and CPU receipt. Linux CPU acceptance is still PENDING.

Use `run_a_s2.sh` to resume D_dev with the existing S2 adapter; use `run_a_s3.sh` after its verified completion and approval. Use `run_b_s2.sh` for B with S1 NLL and `run_b_s3.sh` after B S2 completes. Every real job has a separate approval scope. Preserve logs and intent, check no pending actions and validate lineage. On interruption, retain locks and partial outputs until ownership and provenance can be examined; keep the same working root. The results wrappers collect recorded outputs and produce a SHA list. Transfer the bundle back to a fresh Windows incoming directory, verify its independent pin and review before any promotion. Keep original artifacts in place.

Do not run at the sealed root, rerun completed S1, replace the 75-row prefix, select from D_test, copy across GitHub/private boundaries, launch a sequence of all rounds, widen scope, infer graph edges, or clear an unknown lock. GPU and D_test each need separate authorization; G7 FINAL and SHA gate D_test.
