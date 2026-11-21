# D2 Error Analysis Summary — 2026-11-05



## 1. Scope and Evaluation Context



D2 evaluates the current rule-based capability extractor at the problem level.



Two evaluation sources were used:



- A targeted regression suite containing 30 cases.

- A Gold evaluation set containing 185 problems.



The regression suite evaluates whether the current rules recognize selected capability patterns. The Gold evaluation measures agreement between extractor predictions and manual capability labels.



These results are problem-level measurements. They must not be mixed with the trajectory-level metrics reported in D1.



The approved `capability_rules_v2.json` and the existing Gold labels were preserved during this baseline evaluation.



## 2. Regression Failure Analysis



The regression suite contains 30 cases:



- Passed: 20.

- Failed: 10.

- Pass rate: 66.67%.



The ten failures were classified using the available expected labels, predicted labels, failure descriptions, and the current capability definitions.



| ID | Expected | Predicted | Classification | Preliminary analysis |

|---|---|---|---|---|

| F03 | fraction | none | PATTERN_GAP | The extractor does not recognize the `one-fourth` expression. |

| D02 | division | none | PATTERN_GAP | The equal-sharing pattern is not detected. |

| D03 | division | multiplication | PATTERN_GAP | The group-counting pattern is not recognized as a division requirement; multiplication is predicted instead. |

| D04 | division | none | PATTERN_GAP | The group-counting pattern is not detected. |

| D05 | division | none | PATTERN_GAP | The unit-value pattern is not detected. |

| D07 | division | none | PATTERN_GAP | The inverse-operation pattern is not detected. |

| D09 | division + percentage | percentage | GUIDELINE_AMBIGUITY | Whether division is independently required in this part-to-whole percentage case needs clarification. |

| D10 | division + fraction | fraction | GUIDELINE_AMBIGUITY | Finding the original from one-third of a number may involve inverse multiplication; division should not be assigned automatically without a separate division requirement. |

| R08 | multiplication + ratio | ratio | GUIDELINE_AMBIGUITY | The guideline should clarify whether ratio scaling necessarily requires multiplication as a separately annotated capability. |

| R10 | division + fraction | fraction | GUIDELINE_AMBIGUITY | A part-to-whole fraction relationship does not automatically establish a separate division requirement. |



### 2.1. Classification Summary



- `PATTERN_GAP`: 6 cases.

- `RULE_OVERGENERALIZATION`: 0 cases identified from the available failure descriptions.

- `GUIDELINE_AMBIGUITY`: 4 cases.

- `EXPECTED_LABEL_REVIEW`: 0 cases conclusively identified.



The classifications are preliminary diagnostic judgments. They do not constitute a formal adjudication of the Gold labels.



### 2.2. Main Findings



The regression failures indicate that the current extractor has incomplete coverage of several mathematical relationships:



- Fraction expressions such as `one-fourth`.

- Equal-sharing and group-counting questions.

- Unit-value questions.

- Inverse-operation questions.



The failures involving D09, D10, R08, and R10 are not treated as simple regex coverage problems. They expose boundary questions in the capability definitions, particularly the distinction between a capability explicitly required by a problem and an arithmetic operation that may appear during one possible solution.



No expected labels or approved rules were changed to improve the regression pass rate.



## 3. Problem-level Baseline Results



The extractor was evaluated on 185 Gold problems.



- Exact matches: 4/185.

- Problems with at least one mismatch: 181/185.

- Micro precision: 0.9009.

- Micro recall: 0.3485.

- Micro F1: 0.5026.

- Macro F1: 0.5709.



The baseline contains 357 false negatives and 21 false positives.



### 3.1. Division



- Support: 89.

- TP: 7.

- FP: 11.

- FN: 82.

- Precision: 0.3889.

- Recall: 0.0787.

- F1: 0.1308.



Division is the weakest capability in the current baseline. The extractor misses many problems involving equal sharing, unit values, rates, group counting, and inverse operations.



The low recall suggests that lexical matching does not adequately capture division requirements expressed through natural-language relationships rather than explicit division terminology.



### 3.2. Multiplication



- Support: 155.

- TP: 27.

- FP: 3.

- FN: 128.

- Precision: 0.9000.

- Recall: 0.1742.

- F1: 0.2919.



The extractor misses many multiplication problems involving repeated groups, quantities per unit, rates, and repeated quantities.



These relationships are not always expressed through explicit words such as `twice`, `times`, or `double`.



### 3.3. Addition and Subtraction



| Capability | Support | TP | FP | FN | Precision | Recall | F1 |

|---|---:|---:|---:|---:|---:|---:|---:|

| Addition | 78 | 12 | 4 | 66 | 0.7500 | 0.1538 | 0.2553 |

| Subtraction | 106 | 31 | 1 | 75 | 0.9688 | 0.2925 | 0.4493 |



The extractor frequently detects only part of the operations associated with a problem.



For example, `gsm8k_train_00001` contains Gold addition and subtraction labels, while the extractor predicts subtraction only. This illustrates the difficulty of detecting multiple capabilities in a single problem.



### 3.4. Fraction and Ratio



| Capability | Support | TP | FP | FN | Precision | Recall | F1 |

|---|---:|---:|---:|---:|---:|---:|---:|

| Fraction | 49 | 49 | 2 | 0 | 0.9608 | 1.0000 | 0.9800 |

| Ratio | 30 | 24 | 0 | 6 | 1.0000 | 0.8000 | 0.8889 |



Fraction and ratio have stronger results than the basic arithmetic capabilities in this evaluation.



However, these results are specific to the current 185-problem dataset. They do not establish generalization to other datasets or distributions.



### 3.5. Percentage



- Support: 41.

- TP: 41.

- FP: 0.

- FN: 0.

- Precision: 1.0000.

- Recall: 1.0000.

- F1: 1.0000.



Percentage achieves perfect scores on the 41 Gold examples in this evaluation. This should not be interpreted as proof of perfect percentage recognition in general.



## 4. Error Categories and Interpretation



The observed baseline mismatches can be interpreted through five diagnostic categories:



1. **Missing lexical pattern:** the problem expresses a capability using wording not covered by the current rules.

2. **Implicit operation:** the required arithmetic relationship is not stated through an explicit operation keyword.

3. **False lexical trigger:** a word or symbol appears in the problem but does not establish that the corresponding capability is required.

4. **Multi-capability omission:** the extractor identifies one capability but misses other capabilities associated with the same problem.

5. **Annotation/guideline ambiguity:** the boundary between capabilities is not sufficiently clear to determine whether a label should be assigned.



Representative false positives illustrate the limitations of lexical matching:



- `gsm8k_train_00007`: fraction notation triggers a division prediction even though the Gold labels do not include division.

- `gsm8k_train_00020`: the word `divided` triggers division although the Gold labels are multiplication and subtraction.

- `gsm8k_train_00051`: `sub-divided` triggers division without sufficient evidence of a division requirement.

- `gsm8k_train_00059`: fractional notation triggers division although the Gold labels include fraction and subtraction only.



These cases show that the presence of a mathematical word or symbol is not, by itself, sufficient evidence that a capability is required.



The aggregate counts and representative examples support a preliminary diagnosis. They do not establish that every one of the 181 mismatching problems has been individually adjudicated.



## 5. Implications for Future Extractor Improvements



The current rules v2 provide a reproducible baseline, but performance is uneven across capabilities.



Future improvements should prioritize:



1. Increasing division recall for equal sharing, group counting, unit value, rates, and inverse-operation patterns.

2. Increasing multiplication recall for repeated groups, per-unit quantities, and rate-based relationships.

3. Improving multi-capability detection so that identifying one operation does not suppress other required capabilities.

4. Reducing false positives caused by lexical triggers such as `divided`, `sub-divided`, and fraction notation.

5. Clarifying capability boundaries for inverse fractions, part-to-whole relationships, percentage calculations, and ratio scaling.



These are recommendations for a subsequent improvement stage. They were not implemented as part of the D2 baseline.



## 6. D2 Decision



- Preserve the approved capability rules v2.

- Preserve the 30 regression cases and their current expected labels.

- Preserve the 185 Gold labels.

- Preserve the generated predictions, evidence, and baseline metrics.

- Document regression failures and baseline mismatches as diagnostic evidence.

- Keep problem-level evaluation separate from D1 trajectory-level evaluation.

- Retain A2 annotation independence as an unresolved limitation.



**Conclusion:** D2 establishes a reproducible problem-level baseline for the rule-based capability extractor and documents its principal limitations. The most significant weaknesses are low recall for division and multiplication, incomplete multi-capability detection, and false positives caused by lexical triggers. The regression suite and error analysis provide a concrete basis for subsequent extractor improvements without modifying the approved rules v2 during baseline establishment.

