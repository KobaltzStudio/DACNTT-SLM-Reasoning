# v3.1 Experiment Audit

- Generated at: `2026-11-12T16:26:46+09:00`
- Experiment: `Dynamic Learnability-aware CoT Knowledge Distillation`
- Component: Rule-based capability extraction
- Rules version: `v3.1`
- Evaluation set: Approved 170
- Audit status: **PASS WITH DOCUMENTED LIMITATIONS**

> Scope note: Approved 170 is an approved/review set, not an independent test set. The extractor uses question text and does not inspect Teacher solution traces. Gold annotation uncertainty must be considered separately.

## 1. Objective and scope

This audit consolidates the v3.1 rule-based capability extractor results, the approved-170 evaluation, the inverse-percentage multiplication exception, and the available regression checks. It verifies artifact consistency and records unresolved limitations. It does not claim generalization to an independent test set.

## 2. Configuration and change

- Official config: `experiments/week2September/manual/config/capability_rules_v3.1.json`
- Pre-exception backup: `experiments/week2September/manual/config/backups/capability_rules_v3.1_before_inverse_percentage_exception_20261112_155233.json`
- The candidate inverse-percentage negative pattern is present in the official v3.1 config and absent from the pre-exception backup.
- The candidate analysis reports one changed problem: `gsm8k_train_00011`.
- For this question, multiplication was removed while percentage was retained. The gold annotation is `division` and `percentage`; division remains a false negative. The exception therefore removes the multiplication false positive but does not solve the missing division prediction.

## 3. Approved 170 evaluation

### 3.1 Overall metrics

| Metric | v3 | v3.1 |
| --- | --- | --- |
| Samples | 170 | 170 |
| Exact match | 1/170 (0.59%) | 8/170 (4.71%) |
| Micro TP | 177 | 194 |
| Micro FP | 19 | 17 |
| Micro FN | 326 | 309 |
| Micro precision | 0.9031 | 0.9194 |
| Micro recall | 0.3519 | 0.3857 |
| Micro F1 | 0.5064 | 0.5434 |

### 3.2 v3.1 per-capability metrics

| Capability | TP | FP | FN | TN | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| addition | 8 | 3 | 68 | 91 | 0.7273 | 0.1053 | 0.1839 |
| subtraction | 28 | 1 | 63 | 78 | 0.9655 | 0.3077 | 0.4667 |
| multiplication | 38 | 3 | 102 | 27 | 0.9268 | 0.2714 | 0.4199 |
| division | 18 | 8 | 70 | 74 | 0.6923 | 0.2045 | 0.3158 |
| percentage | 38 | 0 | 0 | 132 | 1.0000 | 1.0000 | 1.0000 |
| fraction | 40 | 2 | 0 | 128 | 0.9524 | 1.0000 | 0.9756 |
| ratio | 24 | 0 | 6 | 140 | 1.0000 | 0.8000 | 0.8889 |

### 3.3 Prediction changes and error counts

- Prediction changes between v3 and final v3.1: **15**.
- False negatives: **162**.
- False positives: **17**.
- The official prediction-changes CSV contains 15 records. The earlier count of 16 belongs to the pre-exception state; after the exception changed `gsm8k_train_00011`, that problem no longer contributes a v3-to-final-v3.1 prediction difference.

## 4. Inverse-percentage exception candidate

- Candidate changed rows: **1**.
- Changed problem IDs: `gsm8k_train_00011`.

| Metric | Candidate baseline | Candidate final / official v3.1 |
| --- | --- | --- |
| TP | 194 | 194 |
| FP | 18 | 17 |
| FN | 309 | 309 |
| Precision | 0.9151 | 0.9194 |
| Recall | 0.3857 | 0.3857 |
| F1 | 0.5427 | 0.5434 |

The exception reduces FP from 18 to 17 while TP and FN remain unchanged. It improves precision and F1 slightly; it does not improve recall. This is a narrow correction supported by one changed sample, not evidence of broad multiplication capability improvement.

## 5. Regression results

### 5.1 Strict negative division regression

- Cases: 2.
- Passed: 2/2.
- Both cases retain their expected multiplication, percentage, and subtraction predictions while suppressing division.

| Test | Source problem | Predicted capabilities | Division detected | PASS |
| --- | --- | --- | --- | --- |
| N01 | gsm8k_train_03439 | multiplication, percentage, subtraction | False | True |
| N02 | gsm8k_train_07117 | multiplication, percentage, subtraction | False | True |

### 5.2 Division retention regression

- Total records: 13.
- Division prediction matched gold: 13/13.
- Trace-verified records: 0.
- Provisional no-trace records: 13.
**Interpretation:** the 13/13 result is provisional. All records have `solution_trace_available = NO`; therefore this result verifies agreement with the current provisional annotations only. It must not be described as trace-verified retention.

## 6. Remaining errors and limitations

- The approved-170 evaluation still contains 162 false-negative records.
- It still contains 17 false-positive records.
- Recall remains limited. The v3.1 micro recall is 0.3857, so the extractor misses a substantial number of gold capability labels.
- The 170-sample set is an approved/review set, not an independent test set.
- The extractor is question-text based and does not use Teacher solution traces.
- Some gold labels and retention examples remain provisional and require trace-based or otherwise documented human verification.
- The inverse-percentage exception addresses one observed multiplication false positive. It does not resolve the division false negative on `gsm8k_train_00011`.

## 7. Artifact inventory

| Artifact | Path | Recommendation |
| --- | --- | --- |
| Official rules | experiments/week2September/manual/config/capability_rules_v3.1.json | KEEP |
| Pre-exception rules backup | experiments/week2September/manual/config/backups/capability_rules_v3.1_before_inverse_percentage_exception_20261112_155233.json | KEEP |
| Approved 170 metrics | experiments/week2September/manual/reports/capability/p1_extractor_v3_1_2026-11-14/approved170_evaluation/metrics_v3_1_approved170.json | KEEP |
| Approved 170 predictions | experiments/week2September/manual/reports/capability/p1_extractor_v3_1_2026-11-14/approved170_evaluation/predictions_v3_1_all170.csv | KEEP |
| Prediction changes | experiments/week2September/manual/reports/capability/p1_extractor_v3_1_2026-11-14/approved170_evaluation/prediction_changes_v3_vs_v3_1.csv | KEEP |
| False negatives | experiments/week2September/manual/reports/capability/p1_extractor_v3_1_2026-11-14/approved170_evaluation/false_negatives_v3_1.csv | KEEP |
| False positives | experiments/week2September/manual/reports/capability/p1_extractor_v3_1_2026-11-14/approved170_evaluation/false_positives_v3_1.csv | KEEP |
| Candidate metrics | experiments/week2September/manual/reports/capability/p1_extractor_v3_1_2026-11-14/candidate_analysis/multiplication_exception_candidate/candidate_metrics.json | KEEP |
| Candidate changed rows | experiments/week2September/manual/reports/capability/p1_extractor_v3_1_2026-11-14/candidate_analysis/multiplication_exception_candidate/candidate_changes.csv | KEEP |
| Negative regression | experiments/week2September/manual/reports/capability/p1_extractor_v3_1_2026-11-14/regression/division_v3_1_negative_results.csv | KEEP |
| Division retention regression | experiments/week2September/manual/reports/capability/p1_extractor_v3_1_2026-11-14/regression/division_retention_13_results.csv | KEEP |

## 8. Validation summary

The audit script validates the approved-170 counts, final metrics, prediction-change count, candidate changed row, regression outcomes, retention annotation status, and the presence of the promoted exception in the official config.

**All mandatory artifact consistency checks passed.** The documented annotation and evaluation limitations remain open.

## 9. Recommended next actions

1. Preserve the current v3.1 config and all evaluation artifacts.
2. Do not promote additional rules based only on the Approved 170 set.
3. Prioritize review of high-impact false negatives and false positives.
4. Obtain solution traces or documented human adjudication for provisional labels.
5. Re-evaluate future rule changes on a separately defined validation/test protocol.

## 10. Historical metadata clarification

The `interpretation` field in `approved170_evaluation/metrics_v3_1_approved170.json` contains an interim statement that the N01/N02 strict negative division regression remains unresolved. This statement reflects the status at the time the metrics artifact was generated and is outdated relative to the latest regression results.

The latest regression artifact, `regression/division_v3_1_negative_results.csv`, confirms that both N01 and N02 pass (2/2 PASS). Therefore, the current strict negative regression status is PASS.

The original metrics JSON is intentionally retained unchanged for provenance. This audit report uses the latest regression artifact as the source of truth for the current regression status.
