# P1 Extractor v3 — 14 Nov 2026

## Changes
- Added `config/capability_rules_v3.json`; v1/v2 remain unchanged.
- Added contextual division patterns for equal sharing, group counting, unit value, inverse unknown-factor equations, part-to-whole percentage, inverse fractions, and "what fraction of" questions.
- Added fraction vocabulary such as "one-fourth".
- Added multiplication suppressions for group-counting question forms to avoid interpreting "groups of" as multiplication when the question asks how many groups can be formed.

## Validation performed in this package
- Regression dataset structural validation: PASS, 30 records / 30 unique test IDs.
- Existing v1 extractor unit suite: PASS, 28/28.
- D2 regression with v3 rules: PASS, 30/30.
- Existing v2 unit test: NOT RUN successfully; its script imports `test_rules_v2_proposed.py`, which is not included in the source ZIP.
- D2 baseline v2: 20/30 when rerun from supplied source.
- No claim is made that v3 has been evaluated against all 170 approved review records or that it improves end-to-end Gold metrics. The 170 records are a development/error-analysis set and should not be used as an independent test set.

## Important semantic constraint
Follow Annotation Guideline v3, not the outdated division wording in `capability_config.json`: a simple fraction-of-quantity problem (e.g. "Find one-fourth of 40") is fraction-only, not division merely because a written solution could divide by four. Division is added for inverse-fraction questions and explicit part-to-whole questions when division is required by the task.

## Known limitation
The rules remain regex-based. A 30/30 score on this compact D2 suite is not evidence of general semantic correctness. Before adopting v3, rerun the extractor on the approved 170 development cases, inspect all changed predictions and false positives/negatives, and obtain human sign-off. Preserve v1/v2 and the original D2 artifacts.
