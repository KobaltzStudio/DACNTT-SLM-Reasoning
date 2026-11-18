\# Day 10 Completion Report

\## Dynamic Learnability-aware CoT Knowledge Distillation



\### 1. Learnability Estimation

\- Completed NLL computation for 4,353 verified trajectories at S0.

\- Generated `learnability\_S0.jsonl`.

\- Computed L\_proxy using the configured median and IQR-based scale.

\- Validated all 4,353 records.

\- All L\_proxy values are within \[0, 1].



\### 2. Selector Validation

\- B4 static selector smoke test passed.

\- B5 dynamic selector smoke test passed.

\- Each selector generated a valid selection log containing 4,353 candidate records.

\- Train-set validation passed for both methods.

\- Pool membership, data leakage and n\_cap checks passed.

\- B4 cross-round no-repeat was tested using a shared selection log.



\### 3. Token Accounting

\- Identified the discrepancy between selector/validator token counting and training token counting.

\- Updated selector and validator to count `n\_supervised`, including the end-of-turn token.

\- Re-ran B4 and B5 selector smoke tests.

\- Confirmed that selector and trainer supervised-token totals match for both methods.



\### 4. Training Pipeline

\- B4 round-0 training smoke test passed.

\- B5 round-0 training smoke test passed.

\- Both LoRA adapters were saved successfully.

\- B4 adapter continuation from round 0 to round 1 passed.

\- B5 adapter continuation from round 0 to round 1 passed.

\- Local GPU execution was used only for smoke testing.



\### 5. Remaining Protocol Requirements

The following items must be resolved before official experiments:

\- Confirm the exact B0 baseline definition.

\- Confirm the complete B5 dynamic selection schedule.

\- Define handling of zero or invalid learnability scale and empty reference sets.

\- Run and review the L\_emp probe to assess the provisional b = 7.

\- Obtain project-team confirmation of the experiment protocol.

\- Confirm the official split manifest and configuration provenance.



\### 6. Conclusion

The S0 learnability estimation, B4/B5 selector smoke tests, train-set validation and LoRA training pipeline have passed their current technical checks.



The implementation is ready for the next stage of experimental preparation. Official B0-B5 runs remain conditional on resolving the outstanding protocol decisions and completing the required pre-training validations.

