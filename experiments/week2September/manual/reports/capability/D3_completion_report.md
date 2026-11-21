# D3 Completion Report

Report generated: 2026-11-06

## 1. Objective

D3 evaluates the rule-based capability extractor against Gold vNext. The purpose is to measure extractor behavior under the updated problem-level annotations produced through the D3 adjudication process.

## 2. Gold vNext

- Total Gold records: 185
- Unique problem IDs: 185
- Guideline version: v3
- Gold status: AI_adjudicated_pending_human_confirmation
- Gold vNext contains AI-adjudicated cases pending human confirmation.

## 3. Experimental Configuration

- Extractor: `scripts/extract_capabilities_rule_based.py`
- Rules: `config/capability_rules_v2.json`
- Evaluation unit: problem-level
- D3 Gold: Gold vNext
- D2 reference Gold: Gold v2
- Extractor implementation and rules are unchanged between D2 and D3.

## 4. D3 Evaluation Results

| Metric | D3 result |
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

## 5. D2 and D3 Comparison

| Level | Metric | Capability | D2 | D3 | Delta (D3-D2) |
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

D2 uses Gold v2, whereas D3 uses Gold vNext. The extractor implementation and rule configuration are held constant. Therefore, differences in measured metrics indicate sensitivity to the updated Gold annotations; they must not be interpreted as an improvement or degradation of the extractor itself.

## 6. Error Analysis

- Number of problem records with at least one capability error: 177
- Error analysis file: `d3_regression/error_analysis.csv`

The error analysis records false positives, false negatives, the original question, matched evidence, and fired rules for each problem with an incorrect prediction.

## 7. Output Artifacts

| Artifact | Path |
|---|---|
| D3 evaluation input | `d3_regression/gold_evaluation_input.jsonl` |
| D3 predictions | `d3_regression/extractor_predictions.jsonl` |
| D3 evidence | `d3_regression/extractor_evidence.jsonl` |
| D3 metrics JSON | `d3_regression/extractor_vnext_metrics.json` |
| D3 capability metrics | `d3_regression/capability_metrics.csv` |
| D2-D3 comparison CSV | `d3_regression/d2_d3_comparison.csv` |
| D2-D3 comparison JSON | `d3_regression/d2_d3_comparison.json` |
| D3 error analysis | `d3_regression/error_analysis.csv` |

## 8. Limitations

1. Gold vNext includes AI-adjudicated labels that are pending human confirmation.
2. The evaluation measures a rule-based extractor against problem-level labels; it does not establish that every matched lexical pattern represents a mathematically necessary capability.
3. D2-D3 metric differences are affected by the change in Gold annotations.
4. Error analysis identifies prediction mismatches but does not automatically establish whether the Gold label or extractor rule is responsible.

## 9. Completion Status

- [x] Gold vNext evaluation input generated.
- [x] Extractor predictions and evidence generated.
- [x] D3 metrics calculated.
- [x] D2-D3 comparison generated.
- [x] D3 error analysis generated.
- [x] Completion report generated.

Human confirmation of the AI-adjudicated cases remains a separate validation activity and is not claimed as completed by this report.
