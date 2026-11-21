# Student Evaluation Source Inspection

- Repository: `C:\KLTN-SLM-Reasoning`

## Frozen Gold JSONL
### `C:\KLTN-SLM-Reasoning\experiments\week2September\manual\data\gold_vnext_frozen_2026-11-16_r1\batch_100_annotations_vnext.jsonl`
- Exists: True
- Records: 100
- Unique IDs: 100
- Missing IDs: 0
- Duplicate IDs: []
- Keys: ['annotator_id', 'capabilities_manual', 'difficulty_manual', 'notes', 'problem_id', 'schema_version']
- SHA256: 5b655ab6705fa8d6178871d35f30712b90058354a29952b9e51e88e0108c8a9f

### `C:\KLTN-SLM-Reasoning\experiments\week2September\manual\data\gold_vnext_frozen_2026-11-16_r1\supplement_annotations_vnext.jsonl`
- Exists: True
- Records: 85
- Unique IDs: 85
- Missing IDs: 0
- Duplicate IDs: []
- Keys: ['annotator_id', 'capabilities_manual', 'difficulty_manual', 'notes', 'problem_id', 'schema_version']
- SHA256: 8c41bc4e5c237a289dfcda92fcc691bf84b0ff5552ea8c8249c3947d3725ae26

## Adjudication CSV
- Exists: True
- Records: 22
- Columns: ['problem_id', 'question', 'queue_reasons', 'semantic_issue_type', 'A1_original_labels', 'A1_reviewed_labels', 'A2_labels', 'A1_difficulty', 'A2_difficulty', 'capability_disagreements', 'A1_review_rationale', 'adjudication_status', 'final_labels', 'final_difficulty', 'adjudication_rationale', 'reviewer', 'ground_truth', 'reference_solution', 'decision_capabilities', 'decision_difficulty', 'decision_rationale', 'guideline_reference', 'raw_question', 'raw_ground_truth', 'source_index', 'question_matches_raw', 'final_capabilities', 'final_rationale', 'guideline_reference_final', 'human_review_status', 'human_confirmed_capabilities', 'human_confirmed_difficulty', 'human_reviewer', 'human_review_notes']
- Status counts: `{"A1_reviewed_labels": {"[\"fraction\", \"multiplication\", \"subtraction\"]": 3, "[\"fraction\", \"multiplication\"]": 1, "[\"multiplication\", \"percentage\", \"subtraction\"]": 1, "[\"addition\", \"fraction\", \"multiplication\"]": 1, "[\"division\", \"multiplication\", \"ratio\", \"subtraction\"]": 2, "[\"division\", \"multiplication\", \"ratio\"]": 2, "[\"division\", \"multiplication\", \"percentage\", \"subtraction\"]": 2, "[\"addition\", \"fraction\", \"multiplication\", \"subtraction\"]": 2, "[\"division\", \"multiplication\", \"percentage\"]": 1, "[\"addition\", \"multiplication\", \"percentage\"]": 1, "[\"addition\", \"division\", \"percentage\"]": 1, "[\"addition\", \"division\", \"fraction\", \"multiplication\"]": 1, "[\"addition\", \"division\", \"fraction\", \"multiplication\", \"ratio\"]": 1, "[\"addition\", \"multiplication\", \"percentage\", \"subtraction\"]": 2, "[\"addition\", \"fraction\", \"multiplication\", \"percentage\", \"subtraction\"]": 1}, "A1_review_rationale": {"Removed division: the requested quantity is cable length kept on hand; splitting into 25-foot sections is incidental and does not require calculating a section count.": 1, "Reviewed against the question and the project capability definitions; the original capability labels are retained. This decision concerns required reasoning capabilities, not independent verification of the supplied ground-truth answer.": 12, "The two joint-outcome probabilities are found by multiplication. The supplied ground truth (20) treats 'how much more likely' as a percentage-point difference, requiring subtraction. If interpreted as relative percentage increase, division would also be required and the answer would differ; this wording/target interpretation needs human confirmation.": 1, "Removed subtraction: the requested collected-container count is obtained by calculating the consumed soda cans, sparkling-water bottles, and juice bottles, then summing them; no remainder is requested.": 1, "Removed addition: group counts and the final girls' percentage can be derived through percentage multiplication, complements/subtraction, doubling, and division; no sum of quantities is required.": 1, "Added addition: Samuel's starting apple count must first be calculated as Bonnie's 8 plus 20 more. Fractional portions, multiplication, and subtraction are also required.": 1, "Removed addition: Boyd's girls count is obtained by doubling Julian's girls count; boys are the remainder, and the requested percentage uses division. No addition is required.": 1, "Revised operations: reversing the fixed $10 discount requires addition, then reversing the 50% discount requires division. Multiplication and subtraction are not needed for the requested inverse calculation.": 1, "Removed subtraction: the ratio partitions the total herd, fractions determine the animals sold, and multiplication plus addition determine total revenue. No subtraction is needed.": 1, "Removed subtraction: the stated difference of four corresponds directly to the two-part difference in the 3:5 ratio; division finds one part and multiplication finds the total.": 1, "Added addition: the 20% tax must be added to the $15 bill before subtracting the taxed total from $20 to obtain the tip.": 1}, "adjudication_status": {"AI_ADJUDICATED_PENDING_HUMAN_CONFIRMATION": 22}, "adjudication_rationale": {"": 22}, "reviewer": {"ChatGPT_AI": 22}, "decision_capabilities": {"": 22}, "decision_difficulty": {"": 22}, "decision_rationale": {"": 22}, "source_index": {"229": 1, "667": 1, "675": 1, "921": 1, "1192": 1, "1247": 1, "1516": 1, "2270": 1, "2690": 1, "2796": 1, "2858": 1, "2936": 1, "2955": 1, "3064": 1, "3079": 1, "3205": 1, "3334": 1, "4380": 1, "4573": 1, "4820": 1, "5157": 1, "5691": 1}, "human_review_status": {"CONFIRMED": 22}, "human_confirmed_capabilities": {"division;fraction;subtraction": 1, "division;fraction": 1, "multiplication;percentage;subtraction": 1, "addition;fraction": 1, "addition;fraction;subtraction": 3, "division;multiplication;ratio;subtraction": 2, "division;multiplication;ratio": 1, "division;multiplication;percentage;subtraction": 2, "fraction;subtraction": 1, "division;multiplication;percentage": 1, "addition;percentage": 1, "addition;division;percentage": 1, "addition;division;fraction": 1, "addition;division;fraction;multiplication;ratio": 1, "addition;division;multiplication;ratio": 1, "addition;multiplication;percentage;subtraction": 1, "addition;percentage;subtraction": 1, "addition;fraction;multiplication;percentage;subtraction": 1}, "human_confirmed_difficulty": {"medium": 17, "easy": 3, "hard": 2}, "human_reviewer": {"Project team (chat confirmation)": 22}, "human_review_notes": {"The project team explicitly confirmed the current AI adjudication in the conversation on 2026-11-06. No label or difficulty revision was requested.": 22}}`

## Student Prediction File
- Exists: True
- Records: 500
- Unique IDs: 500
- Missing IDs: 0
- Duplicate IDs: []
- Keys: ['checkpoint', 'correct', 'format_compliant', 'ground_truth', 'hit_max_new_tokens', 'lenient_correct', 'output_tokens', 'parsed_answer', 'problem_id', 'raw_output', 'verification_status']
- SHA256: 9bb9aeb1c356b7563fc3d8b1b45fe9553bc7c2ca7907e7672833fae448f9a26d

## Checkpoint
- Exists: True
- File count: 7

## Task 7 scripts
- `C:\KLTN-SLM-Reasoning\experiments\week2September\manual\scripts\test_task7_selection.py`

## Full details
- JSON: `C:\KLTN-SLM-Reasoning\experiments\week2September\manual\reports\capability\student_eval_2026-11-17\student_eval_source_inspection.json`
