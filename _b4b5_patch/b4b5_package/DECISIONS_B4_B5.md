# B4/B5 — group-approved implementation contract

Approval received: 2026-11-11.

| Item | Approved behavior | Implementation point |
|---|---|---|
| B5 ranking | Descending `L_proxy`; tie-break `trajectory_id` ascending | `selection_common.rank_by_learnability` |
| B5 cross-round re-selection | Allowed; n_cap=1 still applies within each round | B5 passes an empty cross-round exclusion set; `used_problems` is rebuilt per round |
| Learnability failures | Fail-fast for missing/duplicate/invalid NLL, non-finite values, invalid sigma, or too-small/empty reference set | `compute_learnability.py`, `selection_common.py`, `run_b4_b5.py` |
| Budget filling | Option A: candidate that does not fit is skipped; scan continues | `selection_common.fill_budget` |
| Resume/overwrite | Reuse only complete, provenance-consistent artifacts; incomplete or mismatched artifacts stop; no overwrite | selector, NLL/learnability scripts, trainer, orchestrator |

## Fixed protocol details inherited from Task 7

- B4 uses S0 learnability for all rounds; trajectory IDs selected in earlier rounds are excluded. Candidate order is preserved across rounds by reapplying the same deterministic ranking and filtering prior selections.
- B5 computes scores under the current checkpoint S_t. The reference set for estimating `ell_star` and `sigma` excludes trajectories selected in earlier rounds for the same training seed, but the output score file still contains scores for every candidate in the verified pool.
- Budget A is the number of Student-tokenized trajectory response tokens and excludes `<|im_end|>`. Training logs separately record `trajectory_tokens` and `cumulative_training_tokens` (the latter includes the end-of-turn token).
- Token lengths are recomputed with the pinned Student tokenizer; Teacher metadata token lengths are not used.
- The verified pool, split manifest, config v2, model revision, and training hyperparameters are not changed.

## Deliberate scope boundary

This implementation does not certify the separate L_emp probe (`b=7`) gate, does not define B0, and does not claim official training has completed. Official runs should begin only after the remaining Task 7 approval gates are cleared.
