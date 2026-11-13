# 17/11 — Checkpoint and Multi-seed Pipeline Status

## 1. B4 seed 13 — checkpoint inventory

Three trained and evaluated checkpoints are available.

| Checkpoint | Round | Seed | Effective batch | Micro-batch | Grad accumulation |
|---|---:|---:|---:|---:|---:|
| student_ckpt_001 | 0 | 13 | 8 | 4 | 2 |
| student_ckpt_002 | 1 | 13 | 8 | 4 | 2 |
| student_ckpt_003 | 2 | 13 | 8 | 1 | 8 |

Each checkpoint has:
- 500 prediction records.
- 500 unique prediction IDs.
- Hugging Face evaluation backend.
- Greedy decoding.
- Prompt version v1.

## 2. Gold vNext evaluation integrity

All three checkpoints passed inventory audit v2.

- Confirmed Gold D_dev records: 22.
- Matched confirmed Gold predictions: 22/22.
- Missing predictions: 0.
- Coverage rate: 1.0.
- No prediction IDs outside D_dev.
- Frozen Gold batch, supplement and adjudication CSV hashes match.
- Evaluator SHA is identical across checkpoints.
- Pool SHA is identical across checkpoints.
- Prediction SHA differs across checkpoints.

Audit result: INVENTORY_AUDIT_V2 PASS.

## 3. Source validation

All five core scripts passed py_compile:

- run_b4_b5.py
- train_round.py
- eval_student.py
- select_b4_static.py
- select_b5_dynamic.py

Both selector --help commands passed.

Source inspection confirms:
- Supported seeds: 13, 42, 2026.
- Supported rounds: 0, 1, 2.
- Training outputs separated by method and seed.
- B4 uses static S0 learnability scores.
- B5 uses the checkpoint corresponding to the current round.
- Selection is deterministic for identical pool and score inputs.
- Training seed is passed to train_round.py.
- Resume checks validate train-set and checkpoint lineage.

## 4. Multi-seed selector smoke tests

All outputs are isolated under:
reports/learning_curve/2026-11-17/selector_smoke/

B4:
- [x] Seed 42, round 0.
- [x] Seed 42, round 1.
- [x] Seed 42, round 2.
- [x] Seed 2026, round 0.
- [x] Seed 2026, round 1.
- [x] Seed 2026, round 2.

B5:
- [x] Seed 42, round 0.
- [x] Seed 2026, round 0.

All eight selector invocations completed successfully.
All eight train sets were created using the verified pool and S0 learnability score file.
The smoke selection used a 45,426 Budget-A token budget.

Selector smoke audit:
- 100 checks passed.
- Method, seed, round and source checkpoint metadata verified.
- Selection logs cover the exact verified pool.
- Train-set trajectory IDs match selected IDs in the logs.
- No duplicate trajectory IDs within each train set.

## 5. Source SHA256

- run_b4_b5.py:
  EF80F2676C245257E8E0E0802EDC74AB2D3DB05A47F4316E78D72E92320C90C8

- train_round.py:
  193A363440A9372D0E6624BDED30BEA1BB4D5160EE824818A916013519EE550B

- eval_student.py:
  52A653F64D8EC720BF340F3F258B6C779BAFEA63B9E1A333539675DFEC31A5F8

- selection_common.py:
  4FE28656EBCA94D179AFC6255716E47353744D03B1FAB6CF5C26EE8066DAA835

- select_b4_static.py:
  E43C55F75DD94327C324892164C6264639CDB4C0368AF98D03D6A75C804AD0C2

- select_b5_dynamic.py:
  88B7FBB113C8159E583C121BC2B04770622EB225A80C98C934750C81FC1376CF

- audit_checkpoint_inventory_v2.py:
  8751642BE79535664F7ECC68CF17ECCBB6EEBC080D856F4B0BAF1C87E0960FD4

- build_checkpoint_inventory.py:
  1B09287C884DCB591DC9D03F8DB5C7E9A3F2D2E9C85814FD3C6CF18B213444D4

- test_b4_b5_lineage.py:
  2EEFF717F2948CED5DE2AE73D0447B0C14760E772DDAAF4CD396C8589FDC0826

## 6. Runtime validation still pending

Selector smoke tests do not constitute full training/evaluation runtime validation.

- [ ] B4 seed 42 training/evaluation through checkpoint 003.
- [ ] B4 seed 2026 training/evaluation through checkpoint 003.
- [ ] B5 seed 13 training/evaluation through checkpoint 003.
- [ ] B5 seed 42 training/evaluation through checkpoint 003.
- [ ] B5 seed 2026 training/evaluation through checkpoint 003.
- [ ] Verify B5 round 1/2 scores originate from the matching seed checkpoint.
- [ ] Verify RunPod artifacts against the local artifact contract.

These tasks depend on actual training runs and their outputs. Do not mark them complete based on selector smoke tests.

## 7. Learning curve readiness

Current empirical learning-curve source:
- B4 seed 13.
- Checkpoints 001, 002, 003.
- 500 predictions per checkpoint.
- 22 confirmed Gold D_dev records matched per checkpoint.
- Identical frozen Gold source and evaluator.

This is sufficient to construct a preliminary, single-seed learning curve on 18/11.

Additional seeds and B5 results can be incorporated when their checkpoints and predictions are available and pass the same evaluation audit.

## 8. Work scheduled for 18/11

- [ ] Generate capability_learning_curves.csv.
- [ ] Generate capability_learning_curves.png.
- [ ] Classify capability dynamics as improving, regressing or plateauing.
- [ ] Generate capability_graph.json.
- [ ] Generate graph_evidence_ledger.csv.
- [ ] Write student_learning_dynamics.md.
- [ ] Separate empirical evidence from hypotheses.
- [ ] Preserve support counts and confidence intervals.

## 9. Official selector validation and consistency audit

### 9.1 Official validators

Both official validators passed for all eight smoke-test train sets:

| Method | Seed | Round | validate_train_set.py | validate_b4_b5_artifacts.py |
|---|---:|---:|---|---|
| B4 | 42 | 0 | PASS | PASS |
| B4 | 42 | 1 | PASS | PASS |
| B4 | 42 | 2 | PASS | PASS |
| B4 | 2026 | 0 | PASS | PASS |
| B4 | 2026 | 1 | PASS | PASS |
| B4 | 2026 | 2 | PASS | PASS |
| B5 | 42 | 0 | PASS | PASS |
| B5 | 2026 | 0 | PASS | PASS |

Validation confirmed:
- Train sets conform to the verified pool and experiment configuration.
- Budget-A token counts are within the configured 45,426-token budget.
- Pool, leakage and n_cap checks passed.
- Selection log coverage and protocol checks passed.

Terminal result: ALL_SELECTOR_PROTOCOL_VALIDATORS PASS.

### 9.2 Cross-seed and cross-round consistency

The independent consistency audit passed all 14 checks:

- B4 rounds 0, 1 and 2: seed 42 and seed 2026 have identical selected trajectory IDs.
- B4 rounds 0, 1 and 2: token usage is identical across the two seeds.
- B4 seed 42: selections across rounds 0, 1 and 2 are pairwise disjoint.
- B4 seed 2026: selections across rounds 0, 1 and 2 are pairwise disjoint.
- B5 round 0: seed 42 and seed 2026 have identical selected trajectory IDs.
- B4 and B5 round 0: selected trajectory IDs are identical because both use the same S0 score source and ranking.

Terminal result: SEED_AND_ROUND_CONSISTENCY PASS (14 checks).

### 9.3 Scope and limitations of the validation

These results validate selector outputs, train-set structure, selection-log consistency and deterministic selection behavior. They do not validate full model training or evaluation for the remaining seeds.

B5 seed 42 and seed 2026 have only been smoke-tested for round 0. B5 rounds 1 and 2 remain untested in this local smoke-test stage.

No full B4/B5 training run for the remaining seeds is marked complete by this report. Those runs, their evaluation outputs and subsequent artifact integration are deferred to the later RunPod work schedule.

## 10. 17/11 closure

The planned local checkpoint inventory, Gold integrity audit, source audit, selector smoke tests, official train-set/artifact validators and cross-seed/cross-round consistency checks are complete.

The 17/11 local pipeline-readiness tasks are therefore complete.

The following work remains outside today's completed scope:
- Full B4/B5 training and evaluation for the remaining seeds.
- B5 round 1/2 runtime validation on the remaining seeds.
- RunPod artifact collection, merge and integration validation.

The next scheduled research work is the 18/11 learning-dynamics and capability-graph work, using only checkpoints with actual predictions and the frozen confirmed Gold D_dev subset. Do not interpolate results for checkpoints that have not been trained and evaluated.
