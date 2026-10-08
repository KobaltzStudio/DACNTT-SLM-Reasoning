# KLTN / DACNTT Manual Evaluation Pipeline — Proposal 1

## Task 1–3 README

**Project area:** `experiments/week2September/manual/`

**Current status:**

- **Task 1:** Complete
- **Task 2:** Complete
- **Task 3:** In preparation / audit required
- **Task 4:** Next — automatic capability extractor

##

## 0. OVERVIEW

====================================================================== The purpose of Tasks 1–3 is to build and validate the manual evaluation pipeline for Proposal 1 before moving capability extraction to the automatic evaluator. Overall pipeline: GSM8K source data | v

**Task 1:** Pilot annotation | v Validate annotation protocol | v

**Task 2:** Capability coverage supplement | v Expanded manual reference set | v

**Task 3:** Ambiguous-case audit | v Stable annotation guideline | v

**Task 4:** Automatic capability extractor/evaluator Current capability taxonomy:

- `addition`
- `subtraction`
- `multiplication`
- `division`
- `percentage`
- `fraction`
- `ratio` Difficulty taxonomy:

- `easy`
- `medium`
- `hard` The final goal of Tasks 1–3 is not merely to create annotation data. The goal is to create a sufficiently clear manual reference for building the automatic capability extractor and evaluating the extractor against an independent reference. This is consistent with the original research design: capabilities need clear definitions, the manual annotation protocol must be standardized, the reference/ground truth must be sufficiently reliable, and the automatic evaluator must subsequently produce output in the same format as the manual reference. ==============================================================================
##

##
1. DIRECTORY STRUCTURE

```text
experiments/week2September/manual/
├── config/
│   ├── guideline_v2.md
│   └── manual_annotation_schema.json
├── data/
│   ├── raw/
│   │   ├── gsm8k_train.jsonl
│   │   ├── supplement_candidates.jsonl
│   │   └── supplement_selected.jsonl
│   ├── pilot/
│   │   ├── pilot_30.jsonl
│   │   ├── pilot_30_annotations.jsonl
│   │   └── pilot_30_annotations_A2.jsonl
│   ├── batch_100/
│   │   └── batch_100_annotations.jsonl
│   └── supplement/
│       └── supplement_annotations.jsonl
├── scripts/
│   ├── create_a2_template.py
│   ├── validate_annotation.py
│   ├── check_annotation_alignment.py
│   ├── calculate_annotation_agreement.py
│   ├── download_gsm8k_train.py
│   ├── check_gsm8k_pilot_mapping.py
│   ├── create_supplement_candidates.py
│   ├── remove_existing_annotations.py
│   ├── create_supplement_annotation_template.py
│   ├── report_capability_coverage.py
│   └── [Task 3 audit scripts — TO BE FINALIZED]
└── reports/
├── agreement_report.json
└── [Task 3 audit report — TO BE CREATED]
```

##
2. TASK 1 — PILOT ANNOTATION AND INTER-ANNOTATOR AGREEMENT

======================================================================

**

**STATUS:**** COMPLETE

**

**Objective:**** Task 1 checks whether the manual annotation guideline is sufficiently clear and consistent to be used on a pilot dataset. Task 1 performs:
1. Select 30 GSM8K problems.
2. Use the existing A1 annotation.
3. Create annotation set A2 on the same 30 problems.
4. Validate A
1.
5. Validate A
2.
6. Check A1/A2 alignment.
7. Calculate Cohen's kappa for each capability.
8. Calculate agreement for difficulty.
9. Check disagreement. ----------------------------------------------------------------------
###

###
2. 1. DATASET

----------------------------------------------------------------------

**

**Pilot source:**** experiments/week2September/manual/data/pilot/pilot_30.jsonl

**

**Number of problems:**** 30 problems

**

**Problem IDs:**** gsm8k_train_00000 ... gsm8k_train_00029

**

**A1:**** experiments/week2September/manual/data/pilot/pilot_30_annotations.jsonl

**

**A2:**** experiments/week2September/manual/data/pilot/pilot_30_annotations_A2.jsonl ----------------------------------------------------------------------
###

### 2.
2. GUIDELINE

----------------------------------------------------------------------

**

**File:**** experiments/week2September/manual/config/guideline_v2.md The guideline defines: addition subtraction multiplication division percentage fraction ratio and: easy medium hard Annotation principles: - Annotate only capabilities actually used in the reasoning. - Do not annotate merely because the problem contains a related keyword. - Fraction and division must be distinguished. - Percentage requires actual percentage reasoning. - Ratio should be annotated only when ratio/proportional reasoning is the main mathematical object. - A problem may have multiple capabilities. - Difficulty is based on reasoning complexity, not only the number of operations. - Ambiguity is handled separately. ----------------------------------------------------------------------
###

### 2.
3. create_a2_template.py

----------------------------------------------------------------------

**

**File:**** experiments/week2September/manual/scripts/create_a2_template.py

**

**Purpose:**** Create the annotation template for A2 from the pilot dataset. The main purpose is to ensure that A2 has: - the same problem set; - the same problem IDs; - the same annotation schema; but the annotation data is stored in a separate file.

**

**Output:**** experiments/week2September/manual/data/pilot/ pilot_30_annotations_A2.jsonl

**

**Methodological note:**** In the current experiment, A2 is model-assisted annotation and its results match A1 exactly. Therefore: kappa = 1.0 should currently be interpreted only as evidence of annotation consistency and pipeline consistency. It should not be interpreted as an independent human-human inter-annotator reliability study unless A2 is independently performed by a second human annotator. ----------------------------------------------------------------------
###

### 2.
4. validate_annotation.py

----------------------------------------------------------------------

**

**File:**** experiments/week2September/manual/scripts/validate_annotation.py

**

**Purpose:**** Check whether the annotation file conforms to the schema and vocabulary.

**

**Main checks:**** - JSONL format. - Required fields. - problem_id. - capabilities_manual. - difficulty_manual. - notes. - annotator_id. - schema_version. - capability enum. - difficulty enum. - malformed records.

**

**Commands:**** python experiments\week2September\manual\scripts\validate_annotation.py experiments\week2September\manual\data\pilot\pilot_30_annotations.jsonl python experiments\week2September\manual\scripts\validate_annotation.py experiments\week2September\manual\data\pilot\pilot_30_annotations_A2.jsonl

**

**Results:****

**

**A1:**** PASS

**

**A2:**** PASS ----------------------------------------------------------------------
###

### 2.
5. check_annotation_alignment.py

----------------------------------------------------------------------

**

**File:**** experiments/week2September/manual/scripts/check_annotation_alignment.py

**

**Purpose:**** Check that A1 and A2 actually annotate the same problem set. Checks: - record count; - duplicate problem IDs; - ID set equality; - required fields; - capability validity; - difficulty validity.

**

**Command:**** python experiments\week2September\manual\scripts\check_annotation_alignment.py experiments\week2September\manual\data\pilot\pilot_30_annotations.jsonl experiments\week2September\manual\data\pilot\pilot_30_annotations_A2.jsonl

**

**Results:**** A1 records: 30 A2 records: 30 ID sets: MATCH duplicate IDs: NONE alignment errors: NONE ----------------------------------------------------------------------
###

### 2.
6. calculate_annotation_agreement.py

----------------------------------------------------------------------

**

**File:**** experiments/week2September/manual/scripts/calculate_annotation_agreement.py

**

**Purpose:**** Calculate agreement between A1 and A
2. For each capability: capability present = 1 capability absent = 0 Then calculate: Cohen's kappa Difficulty is treated as a categorical variable: easy medium hard The script also handles the degenerate case. If a capability does not have sufficient variation to calculate kappa, the result is reported as: N/A

**

**Output:**** experiments/week2September/manual/reports/agreement_report.json

**

**Command:**** python experiments\week2September\manual\scripts\calculate_annotation_agreement.py --a1 experiments\week2September\manual\data\pilot\pilot_30_annotations.jsonl --a2 experiments\week2September\manual\data\pilot\pilot_30_annotations_A2.jsonl --output experiments\week2September\manual\reports\agreement_report.json ----------------------------------------------------------------------
###

### 2.
7. TASK 1 RESULT

---------------------------------------------------------------------- Agreement results: | Category | Cohen's kappa |
|---|---:|
| Addition | 1.0000 |
| Subtraction | 1.0000 |
| Multiplication | 1.0000 |
| Division | 1.0000 |
| Percentage | 1.0000 |
| Fraction | 1.0000 |
| Ratio | N/A |
| Difficulty | 1.0000 | Disagreement records: 0

**

**Interpretation:**** 6/7 capabilities have sufficient variation to calculate kappa and all have kappa = 1.0. Difficulty has kappa = 1.0. Ratio = N/A does not mean the ratio guideline has been proven perfect. Ratio = N/A means the pilot distribution does not have sufficient variation for Cohen's kappa to be meaningful. This is precisely the issue Task 2 was created to address. ----------------------------------------------------------------------
###

### 2.
8. TASK 1 ARTIFACTS

----------------------------------------------------------------------

**

**DATA:**** pilot_30.jsonl pilot_30_annotations.jsonl pilot_30_annotations_A2.jsonl

**

**CONFIG:**** guideline_v2.md manual_annotation_schema.json

**

**SCRIPTS:**** create_a2_template.py validate_annotation.py check_annotation_alignment.py calculate_annotation_agreement.py

**

**REPORT:**** agreement_report.json ----------------------------------------------------------------------
###

### 2.
9. TASK 1 PIPELINE

---------------------------------------------------------------------- Pilot GSM8K | v A1 annotation | v A2 annotation | v Validate A1 | v Validate A2 | v Check A1/A2 alignment | v Calculate Cohen's kappa | v Inspect disagreements | v agreement_report.json TASK 1

**

**STATUS:**** COMPLETE ==============================================================================
##

##
3. TASK 2 — CAPABILITY COVERAGE SUPPLEMENT

======================================================================

**

**STATUS:**** COMPLETE ----------------------------------------------------------------------
###

###
3. 1. MOTIVATION

---------------------------------------------------------------------- The initial Batch 100 capability distribution was: addition: 51 subtraction: 51 multiplication: 71 division: 47 percentage: 12 fraction: 18 ratio: 0 Problem: ratio does not appear. percentage and fraction have low counts. Therefore, Batch 100 alone cannot provide a manual reference with sufficient coverage for all capabilities. Task 2 supplements the dataset with examples from GSM8K train. Sampling targets: ratio >= 10 percentage >= 25 fraction >= 30 These targets are sampling/coverage targets. They are not statistical validity thresholds. ----------------------------------------------------------------------
###

###
3. 2. IMPORTANT METHODOLOGICAL CONSTRAINT

---------------------------------------------------------------------- Candidate filtering does not use manual ground-truth capability labels. Candidate filtering uses: - linguistic signals; - problem signals; - percentage/fraction/ratio cues. The candidate type is only: candidate signal not: ground-truth capability. Ground truth is determined only during manual annotation. ----------------------------------------------------------------------
###

### 3.
3. download_gsm8k_train.py

----------------------------------------------------------------------

**

**File:**** experiments/week2September/manual/scripts/download_gsm8k_train.py

**

**Purpose:**** - Load GSM8K train. - Normalize the dataset to the project format. - Preserve project problem IDs. - Record source_index. - Create the source dataset used for candidate search.

**

**Output:**** experiments/week2September/manual/data/raw/gsm8k_train.jsonl Role: This is the source dataset for Task
2. ----------------------------------------------------------------------
###

### 3.
4. check_gsm8k_pilot_mapping.py

----------------------------------------------------------------------

**

**File:**** experiments/week2September/manual/scripts/check_gsm8k_pilot_mapping.py

**

**Purpose:**** Check the mapping between the project pilot dataset and the GSM8K source. Method: exact-match question

**

**Results:**** 30/30 matched 0 missing 0 multiple matches

**

**Purpose:**** Confirm that the project ordering may differ from the current Hugging Face ordering while the problem content still matches. ----------------------------------------------------------------------
###

### 3.
5. create_supplement_candidates.py

----------------------------------------------------------------------

**

**File:**** experiments/week2September/manual/scripts/create_supplement_candidates.py

**

**Purpose:**** Scan GSM8K train and identify candidate problems with linguistic/ problem signals related to: percentage fraction ratio

**

**Output:**** experiments/week2September/manual/data/raw/ supplement_candidates.jsonl

**

**Important:**** This file is not ground truth. It is only a candidate pool. ----------------------------------------------------------------------
###

### 3.
6. remove_existing_annotations.py

----------------------------------------------------------------------

**

**File:**** experiments/week2September/manual/scripts/remove_existing_annotations.py

**

**Purpose:**** Remove candidates already present in batch_100.

**

**Purpose:**** batch_100 ∩ supplement = empty set This ensures that the supplement does not duplicate the baseline manual set. ----------------------------------------------------------------------
###

### 3.
7. create_supplement_annotation_template.py

----------------------------------------------------------------------

**

**File:**** experiments/week2September/manual/scripts/ create_supplement_annotation_template.py

**

**Purpose:**** Input: supplement_selected.jsonl and create an annotation template for: 85 examples The annotation includes: capabilities_manual difficulty_manual notes annotator_id schema_version Final output: supplement_annotations.jsonl ----------------------------------------------------------------------
###

### 3.
8. report_capability_coverage.py

----------------------------------------------------------------------

**

**File:**** experiments/week2September/manual/scripts/report_capability_coverage.py

**

**Purpose:**** Calculate coverage for: batch_100 supplement combined pool and compare it with the sampling targets. ----------------------------------------------------------------------
###

### 3.
9. validate_annotation.py

----------------------------------------------------------------------

**

**File:**** experiments/week2September/manual/scripts/validate_annotation.py In Task 2, this script is reused to validate: supplement_annotations.jsonl Validation includes: - schema; - required fields; - capability enum; - difficulty enum; - annotation structure. ----------------------------------------------------------------------
###

### 3.
10. TASK 2 DATA

----------------------------------------------------------------------

**

**Raw GSM8K:**** experiments/week2September/manual/data/raw/gsm8k_train.jsonl

**

**Candidate pool:**** experiments/week2September/manual/data/raw/supplement_candidates.jsonl

**

**Selected candidate pool:**** experiments/week2September/manual/data/raw/supplement_selected.jsonl

**

**Baseline annotation:**** experiments/week2September/manual/data/batch_100/ batch_100_annotations.jsonl

**

**Supplement annotation:**** experiments/week2September/manual/data/supplement/ supplement_annotations.jsonl ----------------------------------------------------------------------
###

### 3.1
1. TASK 2 RESULT

----------------------------------------------------------------------

**

**Batch 100:**** addition: 51 subtraction: 51 multiplication: 71 division: 47 percentage: 12 fraction: 18 ratio: 0

**

**Supplement:**** total records: 85 addition: 27 subtraction: 55 multiplication: 84 division: 48 percentage: 29 fraction: 31 ratio: 30

**

**Combined:**** total records: 185

**

**Final coverage:**** addition: 51 + 27 = 78 subtraction: 51 + 55 = 106 multiplication: 71 + 84 = 155 division: 47 + 48 = 95 percentage: 12 + 29 = 41 target = 25 status = PASS fraction: 18 + 31 = 49 target = 30 status = PASS ratio: 0 + 30 = 30 target = 10 status = PASS ----------------------------------------------------------------------
###

### 3.1
2. TASK 2 VALIDATION

----------------------------------------------------------------------

**

**Supplement records:**** 85

**

**Unique problem IDs:**** 85

**

**Duplicate IDs:**** NONE

**

**Batch/supplement overlap:**** NONE

**

**Schema validation:**** PASS

**

**Capability coverage:**** percentage >= target fraction >= target ratio >= target Task 2 therefore satisfies its operational objective. ----------------------------------------------------------------------
###

### 3.1
3. IMPORTANT PROVENANCE RULE

---------------------------------------------------------------------- Do not physically merge the supplement into: batch_100_annotations.jsonl The supplement must remain at: data/supplement/supplement_annotations.jsonl Reason: - provenance; - auditability; - reproducibility; - distinguish the baseline and coverage supplement. The combined pool can be created when needed by a script or evaluator, but the source annotations must remain separate. TASK 2

**

**STATUS:**** COMPLETE ==============================================================================
##

##
4. TASK 3 — AMBIGUOUS-CASE AUDIT

======================================================================

**

**STATUS:**** IN PREPARATION NOT YET COMPLETE ----------------------------------------------------------------------
###

###
4. 1. PURPOSE

---------------------------------------------------------------------- Task 3 is not intended to create another large dataset. The goal of Task 3 is to identify and resolve annotation cases that may be inconsistent between annotators or between manual annotation and the future automatic extractor. This is an important step before Task
4. Task 1 answers: "Do the current two annotations agree?" Task 2 answers: "Does the manual dataset have sufficient capability coverage?" Task 3 must answer: "Is the guideline sufficiently clear to handle borderline/ambiguous cases?" Without Task 3, high kappa on the pilot is not sufficient to demonstrate that the guideline is stable, especially because the current A2 is model-assisted. ----------------------------------------------------------------------
###

###
4. 2. CASES TO AUDIT

---------------------------------------------------------------------- Task 3 should focus on the following boundary cases:
1. Fraction vs Division
2. Ratio vs Multiplication
3. Percentage vs Multiplication
4. Percentage vs Fraction
5. Addition vs Subtraction in wording such as: "more", "less", "remaining", "difference"
6. Multiplication in wording such as: "times", "twice", "three times"
7. Problems using multiple capabilities at the same time
8. Problems where a capability appears in the statement but is not actually used in the reasoning
9. Problems where a capability is used in intermediate reasoning but is not the final operation
10. Problems with multiple valid solutions where each has a different capability decomposition 1
1. Difficulty borderline: easy vs medium medium vs hard 1
2. Ambiguous wording without enough evidence to determine the capability with certainty. ----------------------------------------------------------------------
###

###
4. 3. PRINCIPLE OF TASK 3

---------------------------------------------------------------------- Do not change annotations merely to increase agreement. Correct process: ambiguous case | v inspect problem | v inspect reasoning | v apply guideline | v identify missing/ambiguous rule | v update guideline if needed | v re-annotate case | v record decision Task 3 should prioritize fixing the guideline when it is unclear, rather than forcing a new annotator to match an existing annotation. ----------------------------------------------------------------------
###

### 4.
4. PROPOSED TASK 3 DATA ARTIFACT

----------------------------------------------------------------------

**

**Proposed file:**** experiments/week2September/manual/data/audit/ ambiguous_cases.jsonl

**

**Each record should contain:**** problem_id source problem current_capabilities current_difficulty ambiguity_type ambiguity_description evidence decision revised_capabilities revised_difficulty guideline_action annotator_id audit_version

**

**Example:**** { "problem_id": "gsm8k_train_xxxxx", "source": "supplement", "current_capabilities": ["division"], "current_difficulty": "medium", "ambiguity_type": "fraction_vs_division", "ambiguity_description": "...", "evidence": "...", "decision": "fraction", "revised_capabilities": ["fraction"], "revised_difficulty": "medium", "guideline_action": "clarify_fraction_definition", "annotator_id": "A1", "audit_version": "v1" } ----------------------------------------------------------------------
###

### 4.
5. PROPOSED TASK 3 SCRIPTS

---------------------------------------------------------------------- Task 3 currently needs the following scripts to be added. A. detect_ambiguous_cases.py

**

**Path:**** experiments/week2September/manual/scripts/ detect_ambiguous_cases.py

**

**Purpose:**** Create a list of candidate cases that may be ambiguous. Possible signals include: - multiple capability cues; - conflicting capability cues; - fraction/division overlap; - ratio/multiplication overlap; - percentage/multiplication overlap; - notes containing ambiguity; - rare or unusual capability combinations.

**

**Important:**** This script only creates audit candidates. It does not automatically change ground truth. B. create_ambiguity_audit_template.py

**

**Path:**** experiments/week2September/manual/scripts/ create_ambiguity_audit_template.py

**

**Purpose:**** Create a template for human audit from candidate cases. C. validate_ambiguity_audit.py

**

**Path:**** experiments/week2September/manual/scripts/ validate_ambiguity_audit.py

**

**Purpose:**** Validate: - problem_id; - ambiguity_type; - decision; - revised capability; - revised difficulty; - evidence; - annotator metadata. D. summarize_ambiguity_audit.py

**

**Path:**** experiments/week2September/manual/scripts/ summarize_ambiguity_audit.py

**

**Purpose:**** Create a report: - number of ambiguous cases; - ambiguity type distribution; - cases changed; - cases unchanged; - capability changes; - difficulty changes; - guideline changes. ----------------------------------------------------------------------
###

### 4.
6. TASK 3 REPORT

----------------------------------------------------------------------

**

**Proposed output:**** experiments/week2September/manual/reports/ ambiguity_audit_report.json The following may also be created: experiments/week2September/manual/reports/ ambiguity_audit_report.csv

**

**The report must contain at minimum:**** total_audit_cases resolved_cases unresolved_cases changed_annotations unchanged_annotations ambiguity_by_type capability_changes difficulty_changes guideline_changes unresolved_cases ----------------------------------------------------------------------
###

### 4.
7. TASK 3 COMPLETION CRITERIA

---------------------------------------------------------------------- Task 3 should be marked COMPLETE only when:
- - [ ] Candidate ambiguous cases have been created.
- - [ ] Human/manual audit has been performed.
- - [ ] Each ambiguous case has evidence.
- - [ ] Each case has an explicit decision.
- - [ ] Important guideline ambiguities have been recorded.
- - [ ] New rules or clarifications have been added to guideline_v2.md or a newer version.
- - [ ] Audit data has been validated.
- - [ ] No unresolved high-impact ambiguity remains that Task 4 would not know how to handle.
- - [ ] The audit report has been created.
- - [ ] The final guideline version has been identified. ----------------------------------------------------------------------
###

### 4.
8. TASK 3 EXPECTED RESULT

---------------------------------------------------------------------- The most important result of Task 3 is not: "0 ambiguity" It is instead: "Every important ambiguity has a clear handling rule."

**

**Example:**** Fraction: annotate fraction only when fractional reasoning is an actual mathematical operation/concept used in the reasoning. Division: annotate division when the reasoning performs partitioning, quotient reasoning, or a division operation. Ratio: annotate ratio only when the proportional/ratio relationship is the main mathematical object. Percentage: annotate percentage when the reasoning actually uses a percentage relationship, not merely because a percentage appears. Task 3 must turn these principles into sufficiently clear decision rules so that Task 4 can implement them as an automatic extractor. ==============================================================================
##

##
5. FINAL MANUAL REFERENCE DATASET

====================================================================== After Tasks 1–3, the manual reference conceptually consists of: Pilot: 30 records

**

**Batch 100:**** 100 records

**

**Supplement:**** 85 records Combined coverage pool: 185 records for the batch + supplement Pilot A1/A2 are kept separate for agreement validation. Batch 100 is kept separate because it is the baseline manual set. The supplement is kept separate because it is the coverage supplement. All data should not be flattened into a single file if doing so would lose provenance. ==============================================================================
##

##
6. CURRENT CAPABILITY COVERAGE

====================================================================== Current combined batch + supplement: | Capability | Combined count |
|---|---:|
| Addition | 78 |
| Subtraction | 106 |
| Multiplication | 155 |
| Division | 95 |
| Percentage | 41 |
| Fraction | 49 |
| Ratio | 30 | This is the coverage of the manually annotated pool. It is not the natural capability distribution of GSM8K. The supplement was intentionally created to increase coverage of underrepresented capabilities. ==============================================================================
##

##
7. COMMANDS — TASK 1

====================================================================== Validate

**

**A1:**** python experiments\week2September\manual\scripts\validate_annotation.py experiments\week2September\manual\data\pilot\pilot_30_annotations.jsonl Validate

**

**A2:**** python experiments\week2September\manual\scripts\validate_annotation.py experiments\week2September\manual\data\pilot\pilot_30_annotations_A2.jsonl Check alignment: python experiments\week2September\manual\scripts\check_annotation_alignment.py experiments\week2September\manual\data\pilot\pilot_30_annotations.jsonl experiments\week2September\manual\data\pilot\pilot_30_annotations_A2.jsonl Calculate agreement: python experiments\week2September\manual\scripts\calculate_annotation_agreement.py --a1 experiments\week2September\manual\data\pilot\pilot_30_annotations.jsonl --a2 experiments\week2September\manual\data\pilot\pilot_30_annotations_A2.jsonl --output experiments\week2September\manual\reports\agreement_report.json Expected: validation A1 = PASS validation A2 = PASS alignment = PASS disagreements = 0 kappa = 1.0 for capabilities with sufficient variation difficulty kappa = 1.0 ratio = N/A because of degenerate pilot distribution ==============================================================================
##

##
8. COMMANDS — TASK 2

====================================================================== Load GSM8K: python experiments\week2September\manual\scripts\download_gsm8k_train.py Check pilot mapping: python experiments\week2September\manual\scripts\check_gsm8k_pilot_mapping.py Create candidate pool: python experiments\week2September\manual\scripts\create_supplement_candidates.py Remove existing batch annotations: python experiments\week2September\manual\scripts\remove_existing_annotations.py Create supplement annotation template: python experiments\week2September\manual\scripts\create_supplement_annotation_template.py Validate supplement: python experiments\week2September\manual\scripts\validate_annotation.py experiments\week2September\manual\data\supplement\supplement_annotations.jsonl Report coverage: python experiments\week2September\manual\scripts\report_capability_coverage.py Expected final result: supplement = 85 records unique IDs = 85 overlap with batch_100 = 0 percentage >= 25 fraction >= 30 ratio >= 10 ==============================================================================
##

##
9. RELATION TO AUTOMATIC EXTRACTOR

====================================================================== Tasks 1–3 are preparation for Task
4. Task 1 provides initial consistency evidence. Task 2 provides capability coverage. Task 3 provides ambiguity resolution and decision rules. Task 4 then implements: Teacher trajectory | v capability extractor | v automatic capability prediction | v compare against manual reference | v Precision / Recall / F1 | v error analysis The automatic extractor must not simply reproduce the manual labels. It must infer capabilities from trajectory/problem evidence and then be evaluated against the manual reference. This distinction is critical. Manual annotation: ground truth/reference Automatic extractor: prediction Evaluator: prediction vs reference ==============================================================================
##

##
10. WHAT TASK 4 WILL CONSUME

====================================================================== Task 4 should consume: guideline_v2.md manual_annotation_schema.json final manual reference Task 3 ambiguity rules The extractor should output at least: problem_id trajectory_id capabilities For debugging/audit, it should additionally retain: evidence rules_fired confidence/status

**

**Example:**** { "problem_id": "gsm8k_train_00000", "trajectory_id": "gsm8k_train_00000_traj_001", "capabilities": [ "multiplication", "division" ], "evidence": { "multiplication": ["6 x 8 = 48"], "division": ["48 / 4 = 12"] } } The evidence field is not necessarily required in the final training data, but is strongly recommended for extractor debugging and scientific auditability. ==============================================================================
##

## 1
1. VALIDATION LOGIC FOR TASK 4

====================================================================== Automatic extractor validation should not rely only on unit tests. It should have three levels. LEVEL 1 — UNIT TEST Known examples: multiplication division percentage fraction ratio ambiguous boundary cases negative cases

**

**Purpose:**** verify implementation of extraction rules. LEVEL 2 — MANUAL REFERENCE EVALUATION For every capability: TP FP FN TN Then: Precision Recall F1

**

**Purpose:**** measure agreement with the manual reference. LEVEL 3 — ERROR ANALYSIS Inspect: false positives false negatives ambiguous cases capability overlap cases

**

**Purpose:**** determine whether extractor rules or the guideline need revision. ==============================================================================
##

## 1
2. RESEARCH LIMITATIONS

====================================================================== Limitation 1: A2 in Task 1 is currently model-assisted. Therefore: kappa = 1.0 not independent human-human reliability evidence. Limitation 2: The 30-problem pilot does not have sufficient variation for ratio. Therefore: ratio kappa = N/A Limitation 3: Task 2 sampling intentionally increases coverage. Therefore: combined 185-record distribution cannot be considered the natural GSM8K capability distribution. Limitation 4: Capability annotation is problem/reasoning dependent. Keyword occurrence does not imply capability usage. Limitation 5: The automatic extractor will operate at the trajectory level, while current manual labels are primarily determined at the problem level. Therefore, Task 4 evaluation must explicitly state this limitation. ==============================================================================
##

## 1
3. CURRENT STATUS

====================================================================== TASK 1 — COMPLETE
- - [x] Pilot dataset
- - [x] A1 annotations
- - [x] A2 annotations
- - [x] Annotation validation
- - [x] Alignment check
- - [x] Cohen's kappa
- - [x] Difficulty agreement
- - [x] Disagreement inspection
- - [x] Agreement report TASK 2 — COMPLETE
- - [x] GSM8K train source
- - [x] Pilot/source mapping
- - [x] Candidate generation
- - [x] Existing annotation filtering
- - [x] 85 selected supplement examples
- - [x] Manual annotation
- - [x] Schema validation
- - [x] Duplicate check
- - [x] Overlap check
- - [x] Capability coverage report TASK 3 — IN PREPARATION
- - [ ] Define ambiguity candidate detector
- - [ ] Generate ambiguous-case candidate set
- - [ ] Perform manual audit
- - [ ] Record evidence and decisions
- - [ ] Clarify guideline rules
- - [ ] Validate audit records
- - [ ] Generate ambiguity audit report
- - [ ] Freeze final guideline version TASK 4 — NEXT
- - [ ] Implement capability extractor
- - [ ] Implement extractor unit tests
- - [ ] Run extractor on Teacher trajectories
- - [ ] Create capability prediction JSONL
- - [ ] Evaluate against manual reference
- - [ ] Calculate Precision / Recall / F1
- - [ ] Perform FP/FN analysis
- - [ ] Produce capability extractor report ==============================================================================
##

## 1
4. TRANSITION TO TASK 4

====================================================================== Large-scale automatic extraction should not begin before Task 3 is complete enough to decide the important boundary cases.

**

**Transition condition:**** Task 1 + Task 2 + Task 3 | v Frozen guideline | v Capability extraction rules | v Unit tests | v Batch-100 / reference evaluation | v Automatic extractor Task 4 does not create new ground truth. Task 4 uses the manual reference built and audited in Tasks 1–3 to evaluate automatic capability extraction. ==============================================================================
##

## 1
5. OVERALL CONCLUSION

====================================================================== Task 1 has completed pilot consistency validation. Task 2 has completed capability coverage supplementation and produced 85 supplement annotations, increasing the combined manual pool to 185 records. Current combined capability coverage: | Capability | Combined count |
|---|---:|
| Addition | 78 |
| Subtraction | 106 |
| Multiplication | 155 |
| Division | 95 |
| Percentage | 41 |
| Fraction | 49 |
| Ratio | 30 | Task 3 is the remaining step before moving to automatic capability extraction. Task 3 needs to audit borderline cases and turn manual decisions into explicit rules in the guideline. After Task 3, the manual annotation pipeline will be considered sufficiently specified for Task
4. Task 4 will then build the automatic capability extractor and evaluate it against the manual reference using unit tests, Precision/Recall/F1, and error analysis.

**

**FINAL CURRENT STATE:**** TASK 1 = COMPLETE TASK 2 = COMPLETE TASK 3 = IN PREPARATION TASK 4 = NOT STARTED / NEXT STEP
