# Task 7 Decisions â€” Official Experiment Protocol v2

**Project:** Dynamic Learnability-aware CoT Knowledge Distillation  
**Decision date:** 2026-11-10  
**Status:** Draft for project-team confirmation  
**Scope:** Record the decisions required before official B0â€“B5 experiments.

> This document records the four choices explicitly confirmed by the project owner and consolidates protocol values already present in `config/experiment_config.json`. It does not claim that unconfirmed technical details have received group approval. Items marked **VERIFY** must be checked against the full protocol or implementation before official runs.

## A. Confirmed decisions

| Item | Decision | Status |
|---|---|---|
| Token budget | Keep 45,426 supervised response tokens per round; 136,278 total | Confirmed |
| Official environment | Cloud GPU | Confirmed |
| L_emp probe | Run probe to validate provisional `b = 7` | Confirmed |
| Methods | Run all required methods: B0, B2, B3, B4, B5 | Confirmed |
| Training seeds | 13, 42, 2026 | Retain config value |
| Rounds | 3 | Retain config value |
| Primary comparison | B5 vs B4 | Retain config value |

The local RTX 4060 laptop is for development and smoke tests, not official training under this protocol.

### B. Data splits and provenance

The current split files pass `scripts/validate_splits.py`.

- `D_pool`: 6,968 problems
- `D_dev`: 500 problems
- `D_test`: 1,319 problems
- Near-duplicate exclusions: 5
- Split seed: 363636
- `D_test` equals the official GSM8K test set.
- Pool, development and test IDs are disjoint.
- Source and split-file hashes match the validation manifest.

The current `splits/split_manifest.json` SHA-256 is:

`85f4559246542d197c427318afb3eefb8b8492573b69ac23e691fc19ce93bbda`

The current `config/experiment_config.json` declares the same SHA-256.

**Validation status:** `scripts/validate_splits.py` and `scripts/validate_experiment_config.py --frozen` both pass.

The current split manifest hash is consistent with the frozen experiment configuration. No split regeneration or hash update is required.

## C. Token budget

Keep the existing budget:

- `n_round = 200`
- `beta_round_tokens = 45,426`
- `rounds_M = 3`
- `beta_total_tokens = 136,278`

The unit is **supervised (loss-bearing) response tokens under the Student tokenizer**. Prompt tokens are masked from the loss and logged separately.

The config records `45,426 = 200 Ã— 227.13`. The value 227.13 came from 480 verified trajectories in the preliminary pool, as recorded in `reports/task5/pool_token_stats.json`. The official pool's metadata-based mean token length was separately measured at approximately 246.76. These measurements must not be treated as interchangeable: the latter has not yet been demonstrated to use the same Student-tokenizer counting procedure as the budget estimate.

**Decision:** retain 45,426 for comparability with the frozen protocol. Do not silently recalculate it from official-pool metadata. During pipeline validation, verify that selector and trainer count supervised response tokens using the Student tokenizer and enforce the 45,426-token round budget. Report actual selected trajectory counts and actual supervised token totals for every method, seed and round.

If implementation reveals that the budget cannot be enforced as specified, stop and document the discrepancy. Do not silently change the budget.

## D. Methods and selection schedules

Run all required methods: **B0, B2, B3, B4 and B5**. The descriptions below consolidate the current config; implementation details marked **VERIFY** must be checked against the complete protocol.

### D.1 B0 â€” baseline

**VERIFY:** inspect the full protocol and existing scripts to establish whether B0 means training only on the original supervised training set, no additional CoT trajectories, or another precisely specified baseline. Do not infer its definition from the method name alone.

### D.2 B2 â€” random selection

Use the random-selection baseline. Per-round random generator seed:

`random.Random(training_seed * 100 + round)`

Apply the per-round supervised response-token budget and `n_cap = 1` as specified by the implementation protocol. Record exact selected trajectory IDs and token totals.

### D.3 B3 â€” shortest correct trajectory

For each problem, retain its shortest correct verified trajectory, measured with the Student tokenizer. Break equal-length ties by ascending `trajectory_id`.

Shuffle the problem order once using the training seed. Walk through this fixed order across rounds, continuing from the previous round and filling each round up to the token budget. Do not repeat a trajectory across rounds. A problem may contribute at most one trajectory in a round (`n_cap = 1`).

### D.4 B4 â€” static learnability selection

Compute `L_proxy(tau | S_0)` once, rank all eligible verified trajectories in descending order, and break ties by ascending `trajectory_id`.

Walk the fixed ranking across rounds, continuing with remaining candidates and filling each round up to the token budget. If a candidate is skipped because of `n_cap` in a round, it remains eligible for a later round. Do not repeat a trajectory across rounds. The B4 ranking and selected-data schedule should be identical across training seeds, subject to deterministic implementation.

### D.5 B5 â€” dynamic learnability selection

Recompute trajectory learnability at the current Student checkpoint for each round, then select using the current scores under the protocol's dynamic selection rule.

The config allows reselection across rounds for B5. Enforce `n_cap = 1` within each round and record any cross-round reselection. **VERIFY:** take the exact B5 ranking, candidate filtering, budget-filling and tie-breaking procedure from the full protocol/implementation decision. Do not substitute B4's fixed ranking for B5.

### D.6 Common selection requirements

- Only verified trajectories are eligible.
- `n_cap = 1`.
- Tie-break by ascending `trajectory_id`.
- Enforce 45,426 supervised response tokens per round.
- Preserve exact selected IDs, scores, token counts, skipped candidates and reasons.
- B3 and B4 do not repeat trajectories across rounds.
- B2 and B5 may reselect across rounds as permitted by config.
- Record deviations per method, seed and round.

## E. Learnability proxy

The protocol uses length-normalized negative log-likelihood:

`ell(tau | S_t) = NLL(tau | S_t) / response_token_length(tau)`

`L_proxy(tau | S_t) = exp(-(ell(tau | S_t) - ell_star_t)^2 / (2 * sigma_t^2))`

where:

- `ell_star_t` is the median `ell` over the reference set at checkpoint `S_t`.
- `sigma_t` is `IQR(ell) / 1.349` over that reference set.
- The reference set consists of eligible trajectories not yet trained in that run.
- `L_proxy` is computed for every eligible verified trajectory, even though the reference set used to estimate the median and scale excludes already-trained trajectories.

Before official runs, verify:

1. NLL is summed over loss-bearing response tokens and normalized by the exact Student-tokenizer response length.
2. Prompt tokens are excluded from both NLL and denominator.
3. Deterministic handling is defined for zero/non-finite `sigma_t`, empty reference sets and invalid NLL rows.
4. Raw NLL, normalized `ell`, reference-set membership, `ell_star_t`, `sigma_t` and `L_proxy` are saved for every checkpoint.
5. D_test labels/results do not influence selection or tuning.

Zero-scale and invalid-row handling are not specified in the available config. Agree and implement these rules before selector execution; do not silently invent a fallback.

## F. L_emp probe and provisional probe budget

The project owner decided to **run the L_emp probe to validate `b = 7`**. This value remains provisional until the probe is completed and reviewed.

Current config specifies:

- Probe checkpoint: `student_ckpt_000` (`S_0`)
- Five token-length quintile groups over the eligible pool
- 50 trajectories sampled per group
- Sampling seed: 363636
- Provisional probe budget: `b = 7` steps
- Recorded rationale: one epoch over 50 trajectories at effective batch size 8, `ceil(50/8) = 7` steps

The probe report must include:

- Five quintile boundaries and group sizes.
- Sampled trajectory IDs and sampling seed.
- Student-tokenizer prompt and response lengths.
- Actual optimizer/training steps under the probe setup.
- Effective batch size, micro-batch size and gradient accumulation.
- Whether measured training exposure supports using seven steps as the intended budget unit.
- Deviations, failures or memory-related changes.

**Acceptance decision:** the current project materials do not define a numerical pass/fail threshold for the L_emp probe. The team must review the report and explicitly record whether `b = 7` is accepted, revised or remains inconclusive. Until then, do not describe `b = 7` as empirically validated.

## G. Training and evaluation

Retain current config values unless the cloud smoke test demonstrates an implementation incompatibility requiring a documented decision:

- Student: `Qwen/Qwen2.5-1.5B-Instruct`
- Student revision: `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`
- Teacher: `Qwen/Qwen2.5-3B-Instruct`
- Teacher revision: `aa8e72537993ba99e69dfaafa59ed015b17504d1`
- LoRA rank: 16
- LoRA alpha: 32
- LoRA dropout: 0.1
- Learning rate: 0.0002
- Optimizer: `adamw_torch`
- Effective batch size: 8
- One epoch per round
- Maximum sequence length: 1024
- Precision: BF16
- Constant learning-rate schedule
- Warmup steps: 0
- Maximum gradient norm: 0.3
- Continue the same LoRA adapter across rounds; reinitialize optimizer state each round
- Three rounds, producing `S_1`, `S_2`, `S_3`

Official runs must be performed on cloud GPU. Local execution is limited to smoke tests.

Evaluation:

- Greedy decoding
- `max_new_tokens = 512`
- Evaluate D_dev at all checkpoints
- Evaluate D_test at `S_0`, `S_1`, `S_2`, `S_3`
- Use D_dev only for decisions and tuning
- Report strict accuracy, lenient accuracy and format compliance together
- Invalid format counts as incorrect for the primary strict metric

## H. Statistical analysis and primary claims

Primary metric: exact-match/strict accuracy on D_test.

Primary comparison: **B5 vs B4**.

Within each seed, use paired per-problem correctness for McNemar's test.

Across seeds, report the mean paired difference and a 95% confidence interval. Report all three seeds; do not select or omit seeds based on outcomes.

For the learnability-dynamics hypothesis, retain the config's definitions:

- Compare `S_0 -> S_1` and `S_1 -> S_2`.
- Run the analysis on B4 for each training seed.
- Compute `rho_change` and `rho_noise` on the specified eligible, untrained trajectory set `U`.
- `Delta^a = rho_noise^a - rho_change^a`.
- Use cluster bootstrap over `problem_id`, 10,000 resamples, seed 363636.
- Configured support rule: one-sided 95% lower confidence bound above zero and `Delta^a >= 0.05` for every seed.

Also report the configured selection-noise check: Jaccard similarity of round-2 B5 selections between seeds, compared with the approximate chance level 0.02.

Do not claim the hypothesis is supported unless the registered criteria are met. Otherwise report it as unsupported or inconclusive, as appropriate.

## I. Required artifacts

Before training:

- Confirmed `task7_decisions.md`
- Updated and validated `config/experiment_config.json`
- Validated split manifest and split files
- Environment/dependency record
- L_emp probe plan and output schema
- Evaluator smoke-test report
- NLL smoke-test report
- Selector unit-test report

For every method, seed and round:

- Selection manifest with exact trajectory IDs
- Selection scores and candidate/reference-set details where applicable
- Supervised response-token total and prompt-token total
- Train-set JSON accepted by `train_round.py`
- Training log and checkpoint
- D_dev evaluation predictions and metrics

For final evaluation:

- D_test predictions at S0â€“S3
- Strict, lenient and format metrics
- Paired per-problem correctness files
- McNemar results
- Across-seed paired differences and 95% confidence intervals
- Learnability-dynamics bootstrap results
- Selection Jaccard results
- Reproducibility manifest with config hash, split hash, pool hash, model revisions, code version/identifier where available, environment and run timestamps

## J. Open items that must not be silently assumed

1. **Manifest identity:** confirm the current manifest is the intended official split before updating the config hash.
2. **B0 exact definition:** verify against the full protocol and existing implementation.
3. **B5 exact schedule:** verify candidate filtering, dynamic ranking and budget-filling rules against the full protocol.
4. **L_emp acceptance threshold:** no numerical threshold is specified in the available config; team review is required.
5. **Learnability edge cases:** define behavior for zero `sigma`, empty reference set and invalid NLL.
6. **Missing provenance files:** the working copy lacks `config/experiment_config_v1.json`; do not claim its contents or provenance by assumption.

## K. Task 7 completion checklist

- [ ] Project team reviews and confirms Sections Aâ€“J.
- [ ] Confirm current split manifest is the official split.
- [ ] Update `splits.manifest_sha256` in `experiment_config.json` only after confirmation.
- [ ] Ensure `sources.decisions_v2` points to this file.
- [ ] Ensure config status accurately states whether v2 is frozen or pending final confirmation.
- [ ] Resolve B0 and B5 implementation definitions.
- [ ] Agree on learnability edge-case handling.
- [ ] Run L_emp probe and record decision on `b = 7`.
- [ ] Run config and split validators successfully.
- [ ] Only then authorize official B0â€“B5 cloud runs.

**Task 7 is complete only when protocol-affecting checklist items have been resolved and the project team has confirmed the resulting config. Creating this document alone does not constitute empirical validation or group approval.**

