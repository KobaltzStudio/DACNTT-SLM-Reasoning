# D3 Final Completion Report

Report generated: 2026-11-06

## 1. Objective

D3 evaluates the rule-based capability extractor against the project-team-confirmed Gold vFinal annotations. The evaluation unit is the individual problem.

## 2. Gold vFinal

- Gold version: vFinal
- Batch records: 100
- Supplement records: 85
- Total records: 185
- Unique problem IDs: 185
- Confirmed adjudications: 22
- Validation status: PASS
- Guideline: v3

The 22 AI-adjudicated decisions were explicitly confirmed by the project team. The labels in Gold vFinal remain identical to Gold vNext; the version change records the confirmation status and provenance.

## 3. Experimental Configuration

- Extractor: `scripts/extract_capabilities_rule_based.py`
- Rules: `config/capability_rules_v2.json`
- Evaluation unit: problem-level
- Gold: Gold vFinal
- Reference baseline: D2 Gold v2
- Extractor and rule implementation are unchanged.

## 4. D3 vFinal Evaluation Results

| Metric | Result |
|---|---:|
| Gold records | 185 |
| Prediction records | 185 |
| Exact matches | 8 |
| Exact match rate | 0.0432 |
| Micro Precision | 0.9104 |
| Micro Recall | 0.3601 |
| Micro F1 | 0.5160 |
| Macro F1 | 0.5799 |

### 4.1 Per-capability metrics

| Capability | Support | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| addition | 81 | 13 | 3 | 68 | 0.8125 | 0.1605 | 0.2680 |
| subtraction | 102 | 31 | 1 | 71 | 0.9688 | 0.3039 | 0.4627 |
| multiplication | 144 | 27 | 3 | 117 | 0.9000 | 0.1875 | 0.3103 |
| division | 89 | 8 | 10 | 81 | 0.4444 | 0.0899 | 0.1495 |
| percentage | 41 | 41 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| fraction | 49 | 49 | 2 | 0 | 0.9608 | 1.0000 | 0.9800 |
| ratio | 30 | 24 | 0 | 6 | 1.0000 | 0.8000 | 0.8889 |

## 5. D2 and D3 vFinal Comparison

| Level | Metric | Capability | D2 | D3 vFinal | Delta |
|---|---|---|---:|---:|---:|
| aggregate | micro_precision |  | 0.9009433962264151 | 0.910377358490566 | 0.009433962264150941 |
| aggregate | micro_recall |  | 0.34854014598540145 | 0.36007462686567165 | 0.011534480880270204 |
| aggregate | micro_f1 |  | 0.5026315789473684 | 0.5160427807486632 | 0.013411201801294736 |
| aggregate | macro_f1 |  | 0.570888059075874 | 0.579927747290436 | 0.009039688214561914 |
| aggregate | exact_match_rate |  | 0.021621621621621623 | 0.043243243243243246 | 0.021621621621621623 |
| capability | support | addition | 78 | 81 | 3 |
| capability | TP | addition | 12 | 13 | 1 |
| capability | FP | addition | 4 | 3 | -1 |
| capability | FN | addition | 66 | 68 | 2 |
| capability | precision | addition | 0.75 | 0.8125 | 0.0625 |
| capability | recall | addition | 0.15384615384615385 | 0.16049382716049382 | 0.0066476733143399636 |
| capability | f1 | addition | 0.25531914893617025 | 0.26804123711340205 | 0.012722088177231805 |
| capability | support | subtraction | 106 | 102 | -4 |
| capability | TP | subtraction | 31 | 31 | 0 |
| capability | FP | subtraction | 1 | 1 | 0 |
| capability | FN | subtraction | 75 | 71 | -4 |
| capability | precision | subtraction | 0.96875 | 0.96875 | 0.0 |
| capability | recall | subtraction | 0.29245283018867924 | 0.30392156862745096 | 0.01146873843877172 |
| capability | f1 | subtraction | 0.4492753623188405 | 0.462686567164179 | 0.013411204845338476 |
| capability | support | multiplication | 155 | 144 | -11 |
| capability | TP | multiplication | 27 | 27 | 0 |
| capability | FP | multiplication | 3 | 3 | 0 |
| capability | FN | multiplication | 128 | 117 | -11 |
| capability | precision | multiplication | 0.9 | 0.9 | 0.0 |
| capability | recall | multiplication | 0.17419354838709677 | 0.1875 | 0.013306451612903225 |
| capability | f1 | multiplication | 0.29189189189189185 | 0.31034482758620696 | 0.01845293569431511 |
| capability | support | division | 89 | 89 | 0 |
| capability | TP | division | 7 | 8 | 1 |
| capability | FP | division | 11 | 10 | -1 |
| capability | FN | division | 82 | 81 | -1 |
| capability | precision | division | 0.3888888888888889 | 0.4444444444444444 | 0.055555555555555525 |
| capability | recall | division | 0.07865168539325842 | 0.0898876404494382 | 0.011235955056179775 |
| capability | f1 | division | 0.1308411214953271 | 0.14953271028037382 | 0.01869158878504673 |
| capability | support | percentage | 41 | 41 | 0 |
| capability | TP | percentage | 41 | 41 | 0 |
| capability | FP | percentage | 0 | 0 | 0 |
| capability | FN | percentage | 0 | 0 | 0 |
| capability | precision | percentage | 1.0 | 1.0 | 0.0 |
| capability | recall | percentage | 1.0 | 1.0 | 0.0 |
| capability | f1 | percentage | 1.0 | 1.0 | 0.0 |
| capability | support | fraction | 49 | 49 | 0 |
| capability | TP | fraction | 49 | 49 | 0 |
| capability | FP | fraction | 2 | 2 | 0 |
| capability | FN | fraction | 0 | 0 | 0 |
| capability | precision | fraction | 0.9607843137254902 | 0.9607843137254902 | 0.0 |
| capability | recall | fraction | 1.0 | 1.0 | 0.0 |
| capability | f1 | fraction | 0.98 | 0.98 | 0.0 |
| capability | support | ratio | 30 | 30 | 0 |
| capability | TP | ratio | 24 | 24 | 0 |
| capability | FP | ratio | 0 | 0 | 0 |
| capability | FN | ratio | 6 | 6 | 0 |
| capability | precision | ratio | 1.0 | 1.0 | 0.0 |
| capability | recall | ratio | 0.8 | 0.8 | 0.0 |
| capability | f1 | ratio | 0.888888888888889 | 0.888888888888889 | 0.0 |

### Interpretation

D2 and D3 vFinal use different Gold annotation versions. The extractor implementation and rule configuration are held constant. Therefore, metric differences must be interpreted as sensitivity to annotation changes, not as evidence of extractor improvement.

## 6. Error Analysis

- Problems with at least one mismatch: 177

| Capability | FN | FP |
|---|---:|---:|
| addition | 68 | 3 |
| subtraction | 71 | 1 |
| multiplication | 117 | 3 |
| division | 81 | 10 |
| percentage | 0 | 0 |
| fraction | 0 | 2 |
| ratio | 6 | 0 |

The error analysis contains the original question, Gold labels, predicted labels, false negatives, false positives, evidence and fired rules. A mismatch alone does not establish whether the Gold annotation or extractor rule is incorrect.

## 7. Limitations

1. The evaluation covers 185 GSM8K problems and does not by itself establish generalization to other datasets.
2. The 22 adjudication decisions were AI-proposed and then explicitly confirmed by the project team; this should not be described as independent inter-human annotation agreement.
3. The rule-based extractor may miss semantically required capabilities when their wording is not covered by its patterns.
4. D2-D3 metric differences are affected by the Gold annotation version and are not extractor improvements.
5. Error classification requires reviewing both the mathematical requirements and the fired rules.

## 8. Output Artifacts

| Artifact | Path |
|---|---|
| Gold vFinal manifest | `data/gold_vfinal/gold_vfinal_manifest.json` |
| Gold vFinal validation | `reports/capability/d3_audit/gold_vfinal_validation.json` |
| Evaluation input | `d3_final_regression/gold_evaluation_input.jsonl` |
| Predictions | `d3_final_regression/extractor_predictions.jsonl` |
| Evidence | `d3_final_regression/extractor_evidence.jsonl` |
| Metrics JSON | `d3_final_regression/extractor_vfinal_metrics.json` |
| Capability metrics | `d3_final_regression/capability_metrics.csv` |
| D2-vFinal comparison | `d3_final_regression/d2_vfinal_comparison.csv` |
| Error analysis | `d3_final_regression/error_analysis.csv` |
| Error summary | `d3_final_regression/error_analysis_by_capability.csv` |
| Priority review | `d3_final_regression/priority_error_review_annotated.csv` |

## 9. Completion Status

- [x] Gold vFinal created and validated.
- [x] 22 adjudication decisions confirmed by the project team.
- [x] Evaluation input generated.
- [x] Extractor predictions and evidence generated.
- [x] D3 vFinal metrics calculated.
- [x] D2-D3 vFinal comparison generated.
- [x] Error analysis generated.
- [ ] Priority error review completed.
- [ ] Decision on extractor rule v3 documented.
