# P1/P2 Unified

KLTN/DACNTT studies adaptive reasoning distillation. Proposal 1 selects trajectories based on Student capability deficits. Proposal 2 ranks data using learnability from the current Student checkpoint. The integrated controller selects data, trains LoRA, evaluates strict D_dev and runs the capability/lineage hook.

| Term | Meaning |
|---|---|
| **P1-DEFICIT (Run A)** | Deficit-only selection, without NLL-based ranking. |
| **P1P2 (Run B)** | Deficits plus checkpoint-specific learnability percentile, with frozen alpha 0.5. S2/S3 use NLL from verified S1/S2 parents. |
| **B2/B3/B4/B5** | P2 baseline selectors. CLI and source are present. Full B2–B5 runtime is not established by this release. |
| **S0, S1–S3** | Shared base Student and three successive LoRA checkpoints. Integrated rounds are one-based; the P2 selector uses a zero-based mapping. |
| **D_dev / D_dev_select / D_test** | D_dev is the 500-ID strict evaluation scope for each checkpoint. D_dev_select contains the 415 IDs used by G7 to choose a checkpoint. D_test is held until G7 FINAL, an independent manifest SHA, and separate approval. |

The preserved seed-13 results are A S1 416/500, B S1 406/500, and a trained A S2 adapter with 75/500 D_dev predictions. A S3 and B S2/S3 are pending. G6 capability analysis, G7 checkpoint selection and G8 figures are partial. Prerequisite direction, transfer and graph-guided selection are future research hypotheses. No graph training or D_test result is claimed here.

## Install and check

Use a Python 3.11 virtual environment. On the approved platform, install from `P2/requirements-lock.txt` using the matching wheelhouse or approved package indexes, then run `pip check`. Use the Hugging Face backend for the released workflow; vLLM is optional. The source tree keeps `P2/experiments/week2September/manual`.

```bash
python -m venv .venv
# Activate the new venv for your platform, then install the approved lock:
python -m pip install -r P2/requirements-lock.txt
python -m pip check
python -B tools/preflight.py source
python -B tools/preflight.py tests
python -B -m unittest discover -s tests -v
python -B P2/experiments/week2September/manual/scripts/run_p1_p2.py --help
```

The source-only commands run the controller and deployment fixtures. Two test modules check the frozen registry and experiment configs and require the private runtime. For a CPU dry-run on actual sealed artifacts, run `python -B tools/preflight.py bundle --bundle "$P1P2_PACKAGE"`. The bundle preflight is read-only and blocks model subprocesses. When the bundle is absent it reports how to obtain it. Obtain the exact runtime and separate Student cache from an authorized operator. The manifests specify their paths and hashes.

See the [GitHub-to-RunPod workflow](docs/GITHUB_TO_RUNPOD_WORKFLOW.md), [reproducibility instructions](REPRODUCIBILITY.md), [pre-push audit](docs/PRE_PUSH_AUDIT.md) and [data policy](SECURITY_AND_DATA_POLICY.md). Linux CPU and execution on RunPod still require validation and scope approval.
