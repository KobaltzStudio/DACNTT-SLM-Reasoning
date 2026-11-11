# B4/B5 implementation package

This package overlays Task 7 scripts into `experiments/week2September/manual/scripts/`. It does not include or replace the verified trajectory pool, split files, model adapters, or frozen config. Keep the repository's existing `config/experiment_config.json`, `trajectory/pool/pool_v1_verified.jsonl`, and split artifacts unchanged.

## Group-approved protocol implemented

- B4: rank the full verified pool once by `L_proxy(S0)` descending; tie-break by `trajectory_id` ascending. Continue through this ranking over rounds; a selected trajectory is never selected again. A candidate skipped by `n_cap` or the remaining budget can be reconsidered in a later round.
- B5: rank the full verified pool by the current checkpoint's `L_proxy(S_t)` descending; tie-break by `trajectory_id` ascending. Re-selection across rounds is allowed. Within a round, `n_cap=1` still applies.
- B5 learnability reference set: all eligible trajectories not selected in earlier rounds for that seed. Scores are still produced for every trajectory in the verified pool.
- Fail-fast: missing/duplicate score IDs, wrong checkpoint, non-finite NLL/L_proxy, invalid sigma, empty or too-small reference set, and incomplete pool coverage stop the run.
- Budget A: count `n_traj` with the pinned Student tokenizer; exclude `<|im_end|>`. Candidate that does not fit the remaining budget is skipped and scanning continues (group-approved option A).
- Resume: complete train-set/log, NLL/summary, learnability/summary, adapter/train_log, and evaluation/summary artifacts are reused only after consistency checks. Partial or mismatched artifact pairs stop. Existing files are never overwritten.

## Files

Copy all files in `manual/scripts/` from this package into the repository's `experiments/week2September/manual/scripts/` (merge; do not delete existing scripts). Replacements include `selection_common.py`, `compute_learnability.py`, `compute_nll.py`, `validate_train_set.py`, and `train_round.py` to add Budget-A consistency and overwrite guards. New files include:

- `run_b4_b5.py`: one-round orchestration: NLL -> learnability -> selector -> validation -> training -> D_dev evaluation.
- `validate_b4_b5_artifacts.py`: protocol-specific train-set and selection-log validation.
- `test_b4_b5_protocol.py`: offline unit tests for ranking, tie-break, Budget A fill, n_cap, B4 no-repeat, B5 re-selection, and learnability fail-fast behavior.
- `build_b4_b5_figures.py`: generates paper-ready figures and CSV summaries from completed D_dev runs.

## Installation (PowerShell)

Run from the repository root:

```powershell
Copy-Item .\b4b5_package\manual\scripts\*.py .\experiments\week2September\manual\scripts\ -Force
```

If the package was extracted directly into another folder, adjust the source path. Review the changed files with `git diff` before committing.

## Offline checks

Run from `experiments/week2September/manual/`:

```powershell
python -m py_compile scripts\selection_common.py scripts\compute_learnability.py scripts\compute_nll.py scripts\select_b4_static.py scripts\select_b5_dynamic.py scripts\validate_train_set.py scripts\validate_b4_b5_artifacts.py scripts\run_b4_b5.py scripts\build_b4_b5_figures.py scripts\test_b4_b5_protocol.py
python scripts\test_b4_b5_protocol.py
python scripts\test_task7_selection.py
python scripts\test_answer_utils.py
python scripts\validate_experiment_config.py --frozen
python scripts\validate_splits.py
```

The last two commands require the existing project files and are not run by this standalone package.

## Official one-round execution

Official training must run on the approved Cloud GPU. Local runs are smoke tests only. The L_emp probe (`b=7`) remains a separate approval gate; this package does not claim that gate has passed.

Example B4 round 0, seed 13:

```powershell
python scripts\run_b4_b5.py --method B4 --seed 13 --round 0
```

Example B4 round 1:

```powershell
python scripts\run_b4_b5.py --method B4 --seed 13 --round 1
```

Example B5 round 0 and round 1:

```powershell
python scripts\run_b4_b5.py --method B5 --seed 13 --round 0
python scripts\run_b4_b5.py --method B5 --seed 13 --round 1
```

Repeat rounds in order `0 -> 1 -> 2` for each method and seed `13, 42, 2026`. B4 S0 learnability is shared across seeds. B5 NLL and learnability are seed/checkpoint-specific. Do not use S0 scores for B5 rounds 1 or 2.

Useful flags:

- `--micro-batch 4` (default); choose a divisor of effective batch size 8.
- `--eval-backend hf` (default) or `vllm` if the Cloud environment supports it.
- `--skip-eval` only when evaluation is intentionally deferred; run evaluation separately before figures.
- `--reports-dir` and `--models-dir` to change artifact roots. Keep these paths stable between resume attempts.

The orchestration refuses to continue if a prerequisite checkpoint, prior-round train set, or artifact pair is missing or inconsistent. For B5 round `t>0`, the source adapter `student_ckpt_t` must exist. For B4 round `t>0`, the previous-round adapter is required for training continuation, while selection remains based on S0.

## Figures

After D_dev summaries exist for the checkpoints of interest:

```powershell
python scripts\build_b4_b5_figures.py --reports-dir reports\task7 --out-dir reports\task7\figures
```

Outputs include strict accuracy across rounds, secondary metrics, Budget-A utilization, selected learnability, and CSV metric tables. Missing runs are reported and omitted; the script does not impute values.

## Important limitations / gates

1. This package does not generate the L_emp probe or approve its acceptance threshold. Complete and obtain approval for that separate gate before official main runs.
2. The current frozen config does not define B0, so this package implements B4/B5 only.
3. The orchestration is per-round by design. Do not launch round `t+1` before round `t` has a valid train set, adapter, and (for B5) score/reference artifacts.
4. `compute_nll.py` and `compute_learnability.py` are now fail-closed on existing output paths. To rerun a corrupted artifact, move it to a quarantine/backup directory after inspection; do not delete or overwrite it automatically.
5. The package expects the current repository's `student_common.py`, model-loading environment, pinned tokenizer/model revision, pool, split IDs, and capability labels to remain present.
