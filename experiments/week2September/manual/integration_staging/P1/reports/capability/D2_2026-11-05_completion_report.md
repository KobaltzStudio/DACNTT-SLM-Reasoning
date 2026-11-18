# D2 Completion Report — 2026-11-05



## 1. Objective



The objectives of D2 were to:



- Review guideline v3 and capability rules v2.

- Verify the D1 half-of-N decision.

- Construct a capability regression test suite.

- Run regression tests against the actual rule-based extractor.

- Establish a problem-level extractor baseline using 185 Gold problems.



## 2. Guideline and Rules Review



Reviewed files:



- `config/guideline_v3.md`

- `config/capability_rules_v2.json`

- `scripts/extract_capabilities_rule_based.py`



The extractor implementation exposes:



- `compile_rules(rule_data)`

- `extract_capabilities(text, compiled_rules)`



The extraction function returns predicted capabilities, evidence, and fired rules.



Key annotation decisions:



- Half-of-N and one-third-of-N are classified as fraction.

- Fraction-of-N does not automatically imply division.

- Division requires a separate division requirement.

- Ratio is assigned when ratio or proportional reasoning is central to the problem.

- Gold annotations and baseline evaluation are problem-level.



The extractor is deterministic and rule-based. It detects patterns in the input text and does not perform full mathematical reasoning.



Review artifact:



`reports/capability/d2_regression/guideline_rules_review.md`



Review status: COMPLETED.



## 3. Regression Dataset



File:



`data/regression/capability_regression_cases_v1.jsonl`



| Category | Cases |

|---|---:|

| Fraction | 10 |

| Division | 10 |

| Ratio | 10 |

| Total | 30 |



Validation results:



- Records: 30

- Unique IDs: 30

- Schema validation: PASS

- Category validation: PASS



Artifact:



`data/regression/capability_regression_cases_v1.jsonl`



## 4. Regression Evaluation



The regression runner calls the actual extractor implementation using:



- Extractor: `scripts/extract_capabilities_rule_based.py`

- Rules: `config/capability_rules_v2.json`



Results:



| Metric | Result |

|---|---:|

| Total cases | 30 |

| Passed | 20 |

| Failed | 10 |

| Pass rate | 66.67% |



The failures were:



- F03: one-fourth expression.

- D02: equal-sharing expression.

- D03: group-counting expression.

- D04: group-counting expression.

- D05: unit-value expression.

- D07: inverse-operation expression.

- D09: part-to-whole percentage expression.

- D10: inverse-fraction expression.

- R08: ratio with scaling.

- R10: part-to-whole fraction expression.



These results indicate gaps between the manually specified capability expectations and the behavior of the current rule-based extractor.



The approved rules v2 were not modified during this evaluation.



Regression result:



`reports/capability/d2_regression/regression_test_results.json`



## 5. Existing Rules Tests



Capability rules v2:



- Total unit cases: 44

- Passed: 44

- Failed: 0



Result: PASS.



## 6. Problem-level Gold Baseline



Evaluation unit: Problem.



Dataset:



| Dataset | Problems |

|---|---:|

| batch_100 | 100 |

| supplement | 85 |

| Total | 185 |



Input records: 185.



Prediction records: 185.



Unique problem IDs: 185.



The extractor was applied to the original GSM8K question text. Gold labels were used only for evaluation.



### Per-capability Metrics



| Capability | Support | TP | FP | FN | Precision | Recall | F1 |

|---|---:|---:|---:|---:|---:|---:|---:|

| Addition | 78 | 12 | 4 | 66 | 0.7500 | 0.1538 | 0.2553 |

| Subtraction | 106 | 31 | 1 | 75 | 0.9688 | 0.2925 | 0.4493 |

| Multiplication | 155 | 27 | 3 | 128 | 0.9000 | 0.1742 | 0.2919 |

| Division | 89 | 7 | 11 | 82 | 0.3889 | 0.0787 | 0.1308 |

| Percentage | 41 | 41 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |

| Fraction | 49 | 49 | 2 | 0 | 0.9608 | 1.0000 | 0.9800 |

| Ratio | 30 | 24 | 0 | 6 | 1.0000 | 0.8000 | 0.8889 |



Overall metrics:



- Micro precision: 0.9009

- Micro recall: 0.3485

- Micro F1: 0.5026

- Macro F1: 0.5709

- Exact matches: 4/185

- Exact match rate: 0.0216



Artifacts:



- `reports/capability/d2_regression/gold_evaluation_input.jsonl`

- `reports/capability/d2_regression/extractor_predictions.jsonl`

- `reports/capability/d2_regression/extractor_evidence.jsonl`

- `reports/capability/d2_regression/capability_metrics.csv`

- `reports/capability/d2_regression/extractor_baseline.json`



## 7. Preliminary Findings



### Fraction



- Recall: 1.0000.

- Precision: 0.9608.

- F1: 0.9800.

- Two false positives were observed.



### Division



- Recall: 0.0787.

- Precision: 0.3889.

- F1: 0.1308.

- Division has the weakest baseline performance.



### Ratio



- Recall: 0.8000.

- Precision: 1.0000.

- F1: 0.8889.

- Six Gold ratio problems were not detected.



### Addition and Multiplication



- Addition recall: 0.1538.

- Multiplication recall: 0.1742.

- Both capabilities have substantial false-negative counts.



### Percentage



- Precision, recall, and F1 are all 1.0000 on the evaluated Gold set.



These results are specific to the 185-problem dataset and must not be interpreted as general performance guarantees.



Detailed FP/FN causes remain subject to the error analysis artifact.



## 8. Limitations



- The extractor is rule-based and does not perform full mathematical reasoning.

- Problem statements may not explicitly express every capability required by their solutions.

- Regression failures indicate limitations in the current rules v2 behavior.

- A2 annotation independence remains unresolved.

- The baseline uses the approved rules v2 without modification.

- The baseline is problem-level and must not be mixed with Task 4 trajectory-level metrics.



## 9. Conclusion



D2 status: COMPLETED — BASELINE AND MODEL-ASSISTED ERROR ANALYSIS DOCUMENTED.



Completed:



- Guideline v3 and capability rules v2 review.

- Regression dataset construction and validation.

- Existing rules v2 unit tests (44/44 PASS).

- Regression evaluation (20/30 PASS).

- Regression failure classification and diagnostic analysis.

- Gold input construction for 185 problems.

- Rule-based extraction on all 185 problems.

- Problem-level baseline evaluation.

- False-positive and false-negative analysis.

- Consolidated error analysis documentation.



The current rules v2, regression expected labels, and Gold labels were preserved during baseline evaluation.



The baseline establishes a reproducible reference point for subsequent extractor improvements.



Known limitations:



- Low recall for division, multiplication, addition, and subtraction.

- Rule-based extraction cannot perform full mathematical reasoning.

- Problem statements may not explicitly express every capability required by their solutions.

- Some capability boundaries require further clarification, particularly inverse-fraction, part-to-whole, percentage, and ratio-scaling cases.

- The regression failure classifications are preliminary diagnostic judgments, not formal human adjudication.

- A2 annotation independence remains unresolved.

- Results are specific to the current 185-problem dataset.

- Problem-level metrics must remain separate from D1 trajectory-level metrics.



## 10. Generated Artifacts



### Configuration and Guidelines



- `config/guideline_v3.md`

- `config/capability_rules_v2.json`



### Regression Dataset



- `data/regression/capability_regression_cases_v1.jsonl`



### Scripts



- `scripts/validate_regression_cases.py`

- `scripts/test_capability_regression_d2.py`

- `scripts/test_capability_rules_v2.py`

- `scripts/build_gold_regression_input.py`

- `scripts/run_extractor_on_gold.py`

- `scripts/evaluate_extractor_baseline.py`

- `scripts/analyze_d2_regression.py`

- `scripts/analyze_d2_baseline_errors.py`



### Evaluation Outputs



- `reports/capability/d2_regression/gold_evaluation_input.jsonl`

- `reports/capability/d2_regression/extractor_predictions.jsonl`

- `reports/capability/d2_regression/extractor_evidence.jsonl`

- `reports/capability/d2_regression/regression_test_results.json`

- `reports/capability/d2_regression/capability_metrics.csv`

- `reports/capability/d2_regression/extractor_baseline.json`



### Error Analysis



- `reports/capability/d2_regression/guideline_rules_review.md`

- `reports/capability/d2_regression/regression_failure_analysis.md`

- `reports/capability/d2_regression/baseline_error_analysis.jsonl`

- `reports/capability/d2_regression/baseline_error_analysis.md`

- `reports/capability/d2_regression/d2_error_analysis_summary.md`



### Completion Report



- `reports/capability/D2_2026-11-05_completion_report.md`

