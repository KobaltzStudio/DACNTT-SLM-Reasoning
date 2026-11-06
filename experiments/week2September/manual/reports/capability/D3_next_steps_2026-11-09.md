# D3 Next Steps - 2026-11-09

## 1. Current Status

D3 Gold vFinal regression has been completed.

- Gold vFinal: 185 records.
- Project-team-confirmed adjudications: 22.
- Gold validation: PASS.
- Evaluation input: 185 records.
- Extractor predictions: 185 records.
- Extractor evidence: 185 records.
- Micro F1: 0.5160.
- Macro F1: 0.5799.
- Exact match: 8/185.
- Error records: 177.
- Priority error review records: 170.

## 2. Deferred Tasks

The following tasks are intentionally deferred to 2026-11-09.

### 2.1 Priority Error Review

Review all 170 records in:

reports/capability/d3_final_regression/priority_error_review_annotated.csv

Review fields:

- review_status
- error_classification
- gold_label_correct
- extractor_rule_issue
- proposed_action
- review_notes
- reviewer

Review categories:

- MISSING_RULE
- OVERLY_BROAD_RULE
- GOLD_LABEL_ERROR
- GUIDELINE_AMBIGUITY
- OTHER

### 2.2 Error Pattern Analysis

After reviewing the records:

- Aggregate error classifications.
- Identify recurring false-negative patterns.
- Identify recurring false-positive patterns.
- Prioritize addition, multiplication, and division.
- Distinguish annotation errors from extractor errors.

### 2.3 Extractor Rule Decision

Decide whether to:

- Retain capability_rules_v2.json as the baseline.
- Create a separate capability_rules_v3.json.
- Refine the annotation guideline.
- Correct Gold annotations through a separately validated process.

Do not modify capability_rules_v2.json.

### 2.4 D3 Report Update

Update D3_final_completion_report.md after the review.

Document:

- Review coverage.
- Error classification statistics.
- Main error patterns.
- Rule development decision.
- Remaining limitations.

## 3. Important Constraints

- Gold vFinal is frozen for the current D3 evaluation.
- Do not overwrite D2 baseline artifacts.
- Do not modify capability_rules_v2.json.
- Any rule v3 experiment must use the same Gold vFinal evaluation input.
- D2-D3 metric differences must not be described as extractor improvement.

## 4. Expected Deliverables

- Completed priority_error_review_annotated.csv.
- Error classification summary.
- Error pattern analysis.
- Documented rule v2/v3 decision.
- Updated D3 final completion report.
