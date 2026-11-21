# Gold Review — Final Adjudication 2026-11-16

## Review scope

- Pending worklist records: **63**
- User-confirmed decisions: **22**
- Reviewed with no annotation change: **41**
- Total reviewed: **63**
- Capability-changed records: **17**
- Ambiguity-flagged records: **5**
- Difficulty changes: **0**
- Raw ground-truth changes: **0**
- Gold vFinal modifications: **0**

## Review status

- `REVIEWED_NO_CHANGE`: 41
- `REVIEWED_USER_DECISION`: 22

## Ambiguity status

- `DISJOINT_CATEGORY_ASSUMPTION_ACCEPTED`: 1
- `INTERPRETATION_A_ACCEPTED`: 1
- `NO_NEW_AMBIGUITY`: 17
- `NO_NEW_AMBIGUITY_IDENTIFIED`: 41
- `OVERLAP_DEFINED_AS_5_PERCENTAGE_POINTS_OF_TOTAL`: 1
- `SOURCE_VARIANT_AND_TAX_WORDING_CONFLICT`: 1
- `VACCINE_SCOPE_AND_MOSQUITO_OVERLAP_ASSUMPTIONS`: 1

## Explicitly retained assumptions and source caveats

- `gsm8k_train_00239`: 5% overlap is interpreted as 5 percentage points of the total germ population; answer 30%.
- `gsm8k_train_00713`: target answer 15% is retained under the assumptions that infected mosquito groups are disjoint and the vaccine reduction applies to both viruses, despite the malaria-vaccine wording.
- `gsm8k_train_00830`: the current raw dataset record has ground truth 25 for total meal cost. The separately supplied variant asks for the lassi price and derives $2.50. The two targets are not interchangeable.
- `gsm8k_train_01200`: interpretation A is accepted.
- `gsm8k_train_03048`: the three book categories are assumed mutually exclusive.

## Candidate

- Parent candidate directory: `C:\KLTN-SLM-Reasoning\experiments\week2September\manual\data\gold_vnext_candidate_2026-11-16`
- Release candidate directory: `C:\KLTN-SLM-Reasoning\experiments\week2September\manual\data\gold_vnext_candidate_2026-11-16_r1`
- Candidate version: `vNext-candidate-2026-11-16-r1`
- Candidate validation: **PASS**
- Freeze status: **NOT FROZEN**
- User approval required before release/freeze.

## Revision r1 — note consistency correction

- `gsm8k_train_00713`: replaced the contradictory legacy note. The 15% target remains accepted only under the two explicit assumptions; ambiguity remains flagged.
- `gsm8k_train_00830`: replaced the contradictory legacy note. Subtraction is included; raw ground truth 25 remains distinct from the alternate variant's $2.50 target.
- No capability, difficulty, or ground-truth values were changed by this revision.
- Revision candidate: `gold_vnext_candidate_2026-11-16_r1`.
- Freeze status: **NOT FROZEN**.
