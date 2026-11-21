# Task 7 implementation

Copy all `scripts/*.py` files into `manual/scripts/`. `selection_common.py` is required by all four selectors.

## Frozen implementation decisions
- Budget A: count `n_traj` under the pinned Student tokenizer, excluding `<|im_end|>`.
- `train_round.py` records `trajectory_tokens` (matching Budget A) separately from `cumulative_training_tokens` (includes end-of-turn token). Compare selector budget to `trajectory_tokens`.
- No config or split is changed.
- B4 always ranks using S0 learnability. B5 requires learnability scores from the checkpoint matching the round.
- Selectors recompute trajectory token lengths with the Student tokenizer. They do not trust Teacher `metadata.token_length`.

## Compile and tests
From `manual/`:
```powershell
python -m py_compile scripts\eval_metrics.py scripts\compute_learnability.py scripts\selection_common.py scripts\select_b2_random.py scripts\select_b3_heuristic.py scripts\select_b4_static.py scripts\select_b5_dynamic.py scripts\validate_train_set.py scripts\test_task7_selection.py
python -m py_compile scripts\eval_student.py
python scripts\test_task7_selection.py
python scripts\test_answer_utils.py
```

## Evaluation smoke test
```powershell
python scripts\eval_student.py --tag S0_test --out reports\task7\smoke\eval_S0_dev_10.jsonl --limit 10 --backend hf
```

## NLL and learnability
Small test only:
```powershell
python scripts\compute_nll.py --tag student_ckpt_000 --out reports\task7\smoke\nll_S0_20.jsonl --limit 20
```
Full pool for B4:
```powershell
python scripts\compute_nll.py --tag student_ckpt_000 --out reports\task7\nll_S0.jsonl
python scripts\compute_learnability.py --nll reports\task7\nll_S0.jsonl --out reports\task7\learnability_S0.jsonl --checkpoint student_ckpt_000
```
B4/B5 selectors require score coverage of the entire official pool. A 20-record smoke file is not sufficient.

## Selection smoke tests
Use a reduced budget only for testing:
```powershell
New-Item -ItemType Directory -Force reports\task7\smoke | Out-Null
python scripts\select_b2_random.py --round 0 --seed 13 --budget 5000 --out reports\task7\smoke\b2_r0_s13.json --log reports\task7\smoke\b2_s13.jsonl
python scripts\select_b3_heuristic.py --round 0 --seed 13 --budget 5000 --out reports\task7\smoke\b3_r0_s13.json --log reports\task7\smoke\b3_s13.jsonl
python scripts\select_b4_static.py --round 0 --seed 13 --budget 5000 --scores reports\task7\learnability_S0.jsonl --source-checkpoint student_ckpt_000 --out reports\task7\smoke\b4_r0_s13.json --log reports\task7\smoke\b4_s13.jsonl
python scripts\select_b5_dynamic.py --round 0 --seed 13 --budget 5000 --scores reports\task7\learnability_S0.jsonl --source-checkpoint student_ckpt_000 --out reports\task7\smoke\b5_r0_s13.json --log reports\task7\smoke\b5_s13.jsonl
```
B4/B5 commands require full-pool learnability output. Validate:
```powershell
python scripts\validate_train_set.py reports\task7\smoke\b2_r0_s13.json
python scripts\validate_train_set.py reports\task7\smoke\b3_r0_s13.json
python scripts\validate_train_set.py reports\task7\smoke\b4_r0_s13.json
python scripts\validate_train_set.py reports\task7\smoke\b5_r0_s13.json
python scripts\validate_selection_log.py reports\task7\smoke\b2_s13.jsonl
python scripts\validate_selection_log.py reports\task7\smoke\b3_s13.jsonl
python scripts\validate_selection_log.py reports\task7\smoke\b4_s13.jsonl
python scripts\validate_selection_log.py reports\task7\smoke\b5_s13.jsonl
```

## Multi-round operation
Keep one append-only log per method and training seed. For B3/B4, selected trajectory IDs in previous rounds are excluded; candidates skipped for budget remain eligible in later rounds. B2/B5 may reselect across rounds, but enforce one trajectory per problem within a round.
For B5 round t, first run `compute_nll.py` under S_t, then `compute_learnability.py`, then the selector. Never use S0 scores for B5 rounds 1 or 2.

## Important review gates before official runs
1. Run the offline tests and all validators.
2. Verify `trajectory_tokens` in each train set equals the validator's recomputed value and is <=45,426.
3. Run one small training round and check `train_log.json`: `trajectory_tokens` should match Budget A; `cumulative_training_tokens` will be slightly larger because it includes EOS.
4. This implementation is a first compatible implementation, not evidence that the full experiment is complete. The L_emp probe (b=7) remains a separate approval gate.
5. `compute_learnability.py` fails if IQR is zero rather than silently changing the frozen formula.
6. B3 uses the shortest verified trajectory per problem, then shuffles the problem list deterministically with the training seed.
