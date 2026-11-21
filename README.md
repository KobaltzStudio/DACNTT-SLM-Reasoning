# Dynamic Learnability-Aware CoT Distillation

Budget-matched reasoning distillation on GSM8K. A Qwen2.5-3B-Instruct Teacher generates chain-of-thought trajectories, and a Qwen2.5-1.5B-Instruct Student is fine-tuned with LoRA on a selected subset under a fixed token budget. The project compares selection policies that re-score the pool at every Student checkpoint (S1, S2, S3) against static and heuristic baselines.

| Method | Selection rule |
|---|---|
| B0 | Untuned Student |
| B2 | Random |
| B3 | Shortest correct trajectory per problem |
| B4 | Learnability proxy scored once at S0 |
| B5 | Learnability proxy re-scored at every checkpoint |
| P1-DEFICIT | Mean capability deficit of the Student at the current checkpoint |
| P1P2 | 0.5 × deficit + 0.5 × percentile rank of the current learnability proxy |

## Results

Strict accuracy on the 500-question development split (D_dev). The held-out test split is not evaluated for P1-DEFICIT and P1P2.

| Seed | Method | S1 | S2 | S3 |
|---|---|---|---|---|
| 13 | P1-DEFICIT | 416 | 418 | 413 |
| 13 | P1P2 | 406 | 417 | 411 |
| 42 | P1-DEFICIT | 406 | 426 | 422 |
| 42 | P1P2 | 411 | 416 | 401 |
| 2026 | P1-DEFICIT | 411 | 409 | 433 |
| 2026 | P1P2 | 413 | 403 | 405 |

The untuned Student (S0) scores 357/500. Result bundles with per-file SHA-256 sums are in [`experiments/runpod_run/`](experiments/runpod_run/).

## Repository layout

| Path | Contents |
|---|---|
| `runtime/P2/experiments/week2September/manual/` | Sealed pipeline: source, configs, splits, Gold labels, trajectory pool, accepted runs. Read only |
| `runtime/manifests/` | SHA-256 index of the sealed runtime |
| `github/` | Source-only tree (63 files) with `tools/preflight.py` and tests |
| `deployment/` | Verification and per-checkpoint run wrappers (`ops.py`) |
| `runpod_ops/` | Numbered scripts for running on a RunPod GPU pod |
| `experiments/runpod_run/` | Returned result bundles for seeds 13, 42 and 2026 |
| `analysis/` | Capability analysis, checkpoint selection and figures (G6, G7, G8) |
| `docs/` | Protocol, architecture, RunPod execution guide, handoff reports |
| `recovery/` | Recovery guide and workspace state |
| `future_research/` | Proposals for prerequisite graphs and transfer probes |
| `tests/` | Tests for `deployment/ops.py` |

## Requirements

- Linux x86_64 for training and evaluation (Windows can run the source checks only)
- Python 3.11
- NVIDIA GPU with BF16 support for training and evaluation (the runs used an NVIDIA L4)
- About 5 GB of free disk for one working copy, the Student cache and outputs

## Getting started

### 1. Clone

```bash
git clone git@github.com:KobaltzStudio/DACNTT-SLM-Reasoning.git
cd DACNTT-SLM-Reasoning
```

LoRA adapters and tokenizer copies under `experiments/runpod_run/*/.../models/` are not stored in git.

### 2. Create the environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r runtime/P2/requirements-lock.txt
python -m pip check
```

The lock file pins every package and pulls PyTorch from the CUDA 12.6 index.

### 3. Run the checks (CPU only)

```bash
# Tests for the deployment tooling
python -B -m unittest discover -s tests -v

# Source tree checks
cd github
python -B tools/preflight.py source
python -B tools/preflight.py tests
cd ..

# Verify the sealed runtime against its SHA-256 index
bash runpod_ops/local/00_check_local.sh

# Controller usage
python -B runtime/P2/experiments/week2September/manual/scripts/run_p1_p2.py --help
```

### 4. Download the Student model

The pipeline runs offline and expects the exact Student revision in a local Hugging Face cache.

```bash
export HF_HOME=$HOME/p1p2/hf
export HF_HUB_CACHE=$HF_HOME/hub
hf download Qwen/Qwen2.5-1.5B-Instruct --revision 989aa7980e4cf806f80c7fef2b1adb7bc71aa306
```

[`manifests/MODEL_CACHE_SHA256SUMS.txt`](manifests/MODEL_CACHE_SHA256SUMS.txt) lists the expected files and hashes.

## Running experiments

Never run inside `runtime/`. The setup step copies the verified pipeline into a fresh working directory.

### On a local Linux GPU

```bash
export HANDOFF=$PWD
export P1P2_PACKAGE=$HANDOFF/runtime
export P1P2_PYTHON=$HANDOFF/.venv/bin/python
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
WORK=$HOME/p1p2/work          # must not exist yet
LOG_ROOT=$HOME/p1p2/logs && mkdir -p "$LOG_ROOT"

bash deployment/verify_package.sh
bash deployment/verify_model_cache.sh
bash deployment/setup_environment.sh --work "$WORK"
bash deployment/linux_cpu_preflight.sh --work "$WORK" --output "$LOG_ROOT/cpu-preflight"
```

Then run one method and seed for all three rounds (selection, LoRA training, NLL scoring and D_dev evaluation):

```bash
MANUAL=$WORK/P2/experiments/week2September/manual
LEGACY=$("$P1P2_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["windows_manual_root"])' \
  "$P1P2_PACKAGE/manifests/path_mapping_manifest.json")
cd "$MANUAL"
"$P1P2_PYTHON" -B scripts/run_p1_p2.py --manual-root "$MANUAL" --legacy-windows-root "$LEGACY" \
  --method P1P2 --seed 42 --rounds all --resume --backend hf --dtype bf16 \
  --micro-batch 1 --nll-batch 1 --eval-batch 1
```

Add `--dry-run` first to print the plan without training. `--method` accepts `B2`, `B3`, `B4`, `B5`, `P1-DEFICIT` and `P1P2`. One method and seed takes about 2 to 2.5 hours on an L4, most of it in evaluation.

### On RunPod

Scripts in `runpod_ops/` wrap the same steps. `local/` runs on your machine and `pod/` runs on the pod after `source /workspace/env.sh`.

| Step | Where | Script |
|---|---|---|
| Check the runtime seal | local | `runpod_ops/local/00_check_local.sh` |
| Configure SSH to the pod | local | `runpod_ops/local/01_ssh.sh <IP> <PORT>` |
| Upload runtime, source and scripts | local | `runpod_ops/local/02_push.sh` |
| Install Python 3.11, packages and the Student cache | pod | `10_install.sh` (after a pod restart: `11_restore_env.sh`) |
| CPU preflight, then GPU check | pod | `20_preflight_cpu.sh`, `21_gpu_check.sh` |
| Dry-run seeds 42 and 2026 | pod | `60_seeds_dryrun.sh` |
| Launch both seeds in tmux | pod | `65_launch_seeds.sh` (add `PARALLEL=1` to run them side by side) |
| Monitor | pod | `66_seeds_monitor.sh` |
| Download and verify bundles | local | `runpod_ops/local/05_pull_seeds.sh` |

Stop the pod after the bundles are downloaded. See [`docs/RUNPOD_EXECUTION_GUIDE.md`](docs/RUNPOD_EXECUTION_GUIDE.md) and [`deployment/README_RUNPOD.md`](deployment/README_RUNPOD.md) for the full procedure.

### Verifying results

```bash
bash deployment/verify_results.sh --results <bundle-dir> --expected-sha <sha of RESULTS_SHA256SUMS.txt>
```

Verification needs the complete bundle, including the `models/` folder that git does not store.

## Project rules

- `runtime/` and its SHA indices are immutable.
- The controller evaluates D_dev only. Running on D_test needs a final checkpoint selection (G7 FINAL) and separate approval.
- When a job is interrupted, keep logs, partial predictions, locks and lineage files, and follow [`recovery/RECOVERY_GUIDE.md`](recovery/RECOVERY_GUIDE.md).

The full rules are in [`AGENTS.md`](AGENTS.md). The earlier operator notes for this workspace are in [`HANDOFF.md`](HANDOFF.md).

## Documentation

- [`docs/SCIENTIFIC_PROTOCOL.md`](docs/SCIENTIFIC_PROTOCOL.md): protocol and analysis plan
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): controller and pipeline structure
- [`docs/ARTIFACT_PROVENANCE.md`](docs/ARTIFACT_PROVENANCE.md): where each artifact comes from
- [`docs/FINAL_HANDOFF_REPORT.md`](docs/FINAL_HANDOFF_REPORT.md): handoff report
- [`future_research/README.md`](future_research/README.md): follow-up research directions

## Authors

Dinh Hong Vu (advisor), Nguyen Ngoc Trinh Nghi and Ngo Chi Thuan, Faculty of Information Technology, Ton Duc Thang University.
