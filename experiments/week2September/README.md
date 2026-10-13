1. Overview

This repository contains the experimental pipeline for the KLTN/DACNTT project on reasoning knowledge distillation between two Small Language Models (SLMs):

Teacher: Qwen2.5-3B-Instruct
Student: Qwen2.5-1.5B-Instruct
Dataset: GSM8K
Teacher inference: LM Studio OpenAI-compatible API
Current experiment: Week 2, September 2026

The current work focuses on establishing the experimental foundation for the proposed reasoning-distillation research.

The following stages have been completed:

GSM8K
  ↓
Teacher / Student Baseline
  ↓
Difficulty Analysis
  ↓
Teacher Multi-Trajectory Generation
  ↓
Trajectory Re-evaluation
  ↓
Teacher-Correct / Student-Wrong Candidate Extraction
  ↓
Student Skill-Gap Analysis
  ↓
Multi-Trajectory Analysis
  ↓
Data Validation
  ↓
Backup

Automatic trace selection, automatic curriculum, and Student training are intentionally deferred until the method, evaluation criteria, and literature review are finalized.

2. Environment

The experiments were performed in a Python virtual environment:

.venv

Activate it from PowerShell:

.\.venv\Scripts\Activate.ps1

The project uses:

Python 3.11
PyTorch
Transformers
Datasets
PEFT
TRL
Accelerate
OpenAI Python client
LM Studio

Teacher and Student are both SLMs. The Teacher is the larger model (3B) and the Student is the smaller model (1.5B).

3. LM Studio Setup

LM Studio is used as the local inference server.

The OpenAI-compatible endpoint is:

http://localhost:1234/v1

The Teacher model used in the trajectory-generation script is:

qwen2.5-3b-instruct

The Python code connects using:

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio",
)

Before running Teacher-generation scripts, LM Studio must be running and the required model must be loaded.

4. Week 2 Data

The main Week 2 directory is:

experiments/
└── week2September/

Important directories:

experiments/week2September/
├── raw/
├── processed/
└── results/

The main input/output files currently used are:

experiments/week2September/processed/
├── baseline_with_difficulty_100.jsonl
├── teacher_trajectories_metadata_50x5.jsonl
├── teacher_trajectories_reevaluated_50x5.jsonl
├── teacher_correct_student_wrong_with_metadata.jsonl
└── student_skill_gap.json

experiments/week2September/raw/
└── teacher_trajectories_50x5.jsonl

experiments/week2September/results/
├── multi_trajectory_analysis.json
└── week2_experimental_snapshot.txt
5. Baseline Experiment

The baseline contains 100 GSM8K examples.

The baseline compares:

Teacher: Qwen2.5-3B-Instruct
Student: Qwen2.5-1.5B-Instruct

Current results:

Teacher accuracy: 87/100 = 87.00%
Student accuracy: 71/100 = 71.00%

Teacher-Student gap:
87.00% - 71.00% = 16.00 percentage points

The baseline also identifies examples where:

Teacher = correct
Student = wrong

Current result:

Teacher-correct / Student-wrong questions: 17

This subset is used as the basis for the candidate pool and Student skill-gap analysis.

6. Difficulty Analysis

Difficulty metadata was generated for the experiment data.

The 250 Teacher trajectories currently have the following distribution:

Easy:   180
Medium:  65
Hard:      5

Difficulty-score distribution:

Score 0: 55
Score 1: 60
Score 2: 65
Score 3: 50
Score 4: 15
Score 5:  5

The difficulty information is stored with the trajectory metadata.

7. Teacher Multi-Trajectory Generation

Script:

scripts/generate_teacher_trajectories.py

Run:

python scripts/generate_teacher_trajectories.py

The script reads:

experiments/week2September/processed/trajectory_questions_50.jsonl

and generates:

5 trajectories per question

Configuration:

NUM_TRAJECTORIES = 5
TEMPERATURE = 0.7
MAX_TOKENS = 512
MODEL = "qwen2.5-3b-instruct"

For 50 questions:

50 questions × 5 trajectories = 250 trajectories

Output:

experiments/week2September/raw/teacher_trajectories_50x5.jsonl

The script is resumable. It checks existing (question_id, trajectory_id) pairs and skips already-generated records.

8. Teacher Trajectory Re-Evaluation

Teacher trajectories were re-evaluated after generation.

Script:

scripts/re_evaluate_teacher_trajectories.py

Run:

python scripts/re_evaluate_teacher_trajectories.py

Output:

experiments/week2September/processed/teacher_trajectories_reevaluated_50x5.jsonl

Current result:

Total trajectories: 250
Correct:            161
Incorrect:           89
Null answer:         39

Therefore:

Trajectory correctness:
161 / 250 = 64.40%

Null answers are retained rather than silently removed.

9. Multi-Trajectory Analysis

Script:

scripts/analyze_multi_trajectory.py

Run:

python scripts/analyze_multi_trajectory.py

Current results:

Questions:       50
Trajectories:   250

Single-shot:     5/50 = 10.00%
Best-of-5:       9/50 = 18.00%
Majority:        9/50 = 18.00%

Output:

experiments/week2September/results/multi_trajectory_analysis.json

This analysis is descriptive only. It is not the final evaluation of the proposed distillation method.

10. Teacher-Correct / Student-Wrong Candidate Extraction

Script:

scripts/select_teacher_correct_student_wrong.py

Run:

python scripts/select_teacher_correct_student_wrong.py

The script uses:

experiments/week2September/processed/baseline_with_difficulty_100.jsonl

and:

experiments/week2September/raw/teacher_trajectories_50x5.jsonl

to identify questions satisfying:

teacher_correct == True
student_correct == False

Current baseline result:

Eligible questions: 17

However, only 12 of these questions have corresponding generated trajectories in the current 50-question trajectory set.

Therefore:

Eligible baseline questions: 17
Candidate questions represented by trajectories: 12
Candidate trajectories: 60

Because there are five trajectories per candidate question:

12 × 5 = 60

Current candidate trajectory statistics:

Correct trajectories:   28
Incorrect trajectories: 32
Null answers:           11

Output:

experiments/week2September/processed/teacher_correct_student_wrong_with_metadata.jsonl

Important distinction:

17 = Teacher-correct / Student-wrong baseline questions

12 = those questions currently represented in the trajectory dataset

60 = candidate trajectories

These quantities must not be treated as interchangeable.

11. Candidate Pool Validation

Script:

scripts/validate_week2_data.py

Run:

python scripts/validate_week2_data.py

Current validation:

Baseline:
100 records

Teacher correct:
87

Student correct:
71

Teacher-correct / Student-wrong:
17


Trajectories:
250

Unique questions:
50

Trajectories per question:
5

Duplicate trajectory keys:
0


Candidate pool:
60

Unique candidate questions:
12

Duplicate candidate keys:
0

Candidates outside eligible baseline:
0

Candidate difficulty:

Easy:    50
Medium:  10
Hard:     0

The validation also confirms:

Candidate IDs missing from baseline: 0
Trajectory question IDs missing from baseline: 0

This script should be run whenever the Week 2 data is regenerated or modified.

12. Student Skill-Gap Analysis

Script:

scripts/analyze_student_gaps.py

Run:

python scripts/analyze_student_gaps.py

Output:

experiments/week2September/processed/student_skill_gap.json

Current result:

Teacher-correct / Student-wrong questions: 17

Observed skill profile:

division
score = 10
normalized gap = 0.5882

addition
score = 7
normalized gap = 0.4118

multiplication
score = 4
normalized gap = 0.2353

percentage
score = 3
normalized gap = 0.1765

subtraction
score = 1
normalized gap = 0.0588

Current ranking:

1. division
2. addition
3. multiplication
4. percentage
5. subtraction

This is currently an exploratory Student skill-gap profile.

It should not yet be treated as a final validated skill model. The automatic selection algorithm will be designed after the manual selection protocol and evaluation criteria are finalized.

13. Candidate Pool Example

The candidate pool contains five trajectories for each represented Teacher-correct / Student-wrong question.

Example structure:

{
  "question_id": "gsm8k_train_00017",
  "trajectory_id": 0,
  "question": "...",
  "trajectory": "...",
  "predicted_answer": "...",
  "ground_truth": "...",
  "trajectory_correct": true,
  "teacher_baseline_correct": true,
  "student_baseline_correct": false,
  "difficulty": "easy",
  "difficulty_score": 2
}

The important experimental structure is:

Student failure
      ↓
Candidate question
      ↓
Multiple Teacher reasoning traces
      ↓
Trace-level inspection/selection

This is the foundation for the proposed trace-selection research.

14. Automatic Trace Selection

Status:

DEFERRED

It has intentionally not been finalized or implemented as a final experimental method yet.

Reason:

The selection method still requires:

1. Literature review
2. Final novelty positioning
3. Manual selection protocol
4. Explicit trace-quality criteria
5. Definition of the scoring function
6. Definition of evaluation metrics
7. Comparison between manual and automatic selection

The current 60-trajectory candidate pool is therefore treated as the input data for the future selection experiment.

Do not interpret the current candidate extraction as the proposed automatic selection algorithm.

15. Automatic Curriculum

Status:

DEFERRED

The previous curriculum script:

scripts/generate_curriculum.py

currently has a schema mismatch.

The script constructs records using:

difficulty

but its final statistics access:

difficulty_category

which causes:

KeyError: 'difficulty_category'

This is not currently blocking the Week 2 experimental foundation because automatic curriculum has been intentionally deferred.

Do not spend time fixing this script unless the curriculum experiment is resumed.

When resumed, the final schema should be decided first.

The intended conceptual structure is:

difficulty
    ↓
sorting
    ↓
easy
    ↓
medium
    ↓
hard

with metadata preserved for each question and its trajectories.

16. Student SFT / LoRA Training

Status:

DEFERRED

No full Student training experiment has been performed as part of this Week 2 foundation.

A future smoke test may use:

Qwen2.5-1.5B-Instruct
LoRA / PEFT
TRL SFT
Accelerate

but this should only be implemented after the training dataset and selection methodology are finalized.

The current Week 2 results should therefore not be interpreted as evidence that the proposed selected trajectories improve Student performance.

17. Important Experimental Interpretation

The current results establish the following:

Teacher is stronger than Student
        ↓
87% vs 71%
        ↓
16 percentage-point performance gap
        ↓
17 questions where Teacher succeeds and Student fails
        ↓
12 of these currently have 5 generated Teacher trajectories
        ↓
60 candidate trajectories
        ↓
Student skill-gap profile can be estimated
        ↓
Candidate reasoning traces can be inspected

The current results do NOT establish:

Automatic selection is better
Curriculum is better
Selected CoT improves Student
LoRA improves reasoning
The proposed method beats existing methods

Those require the next experimental phase.

18. Backup

A backup was created:

experiments/week2September_backup_2026-09-16

This backup contains the Week 2 experimental data before continuing with future modifications.

Do not overwrite the backup.

19. Current Experimental Snapshot

The current snapshot is stored at:

experiments/week2September/results/week2_experimental_snapshot.txt

Current key numbers:

Teacher:
87/100 = 87.00%

Student:
71/100 = 71.00%

Teacher-Student gap:
16.00 percentage points

Teacher-correct / Student-wrong:
17 questions

Teacher trajectories:
50 questions × 5 = 250

Teacher trajectory correctness:
161/250 = 64.40%

Best-of-5:
9/50 = 18.00%

Majority:
9/50 = 18.00%

Candidate questions:
12

Candidate trajectories:
60

Candidate trajectory correctness:
28 correct
32 incorrect
11 null

Student skill-gap ranking:
division
addition
multiplication
percentage
subtraction
20. Recommended Reproduction Order

If the repository needs to be reproduced from the current Week 2 state, use the following order.

First activate the environment:

.\.venv\Scripts\Activate.ps1

Make sure LM Studio is running with the Teacher model loaded.

Then verify the existing trajectory data:

python scripts/validate_week2_data.py

Run multi-trajectory analysis:

python scripts/analyze_multi_trajectory.py

Run candidate extraction:

python scripts/select_teacher_correct_student_wrong.py

Run Student skill-gap analysis:

python scripts/analyze_student_gaps.py

Validate the resulting data again:

python scripts/validate_week2_data.py

For a complete regeneration of Teacher trajectories, use:

python scripts/generate_teacher_trajectories.py

followed by:

python scripts/re_evaluate_teacher_trajectories.py

and then repeat the analysis steps.

Because Teacher generation uses local inference and temperature 0.7, regenerated trajectories may not be identical to the existing trajectories.

21. Current Status

Completed:

[✓] Python virtual environment
[✓] PyTorch / CUDA environment
[✓] LM Studio inference setup
[✓] Teacher baseline
[✓] Student baseline
[✓] Teacher-Student comparison
[✓] Difficulty metadata
[✓] Teacher multi-trajectory generation
[✓] Multi-trajectory re-evaluation
[✓] Multi-trajectory analysis
[✓] Teacher-correct / Student-wrong extraction
[✓] Student skill-gap analysis
[✓] Candidate-pool validation
[✓] Experimental data backup
[✓] Week 2 experimental snapshot

Deferred:

[ ] Manual trace-selection protocol
[ ] Automatic trace selection
[ ] Automatic curriculum
[ ] Final trace-ranking function
[ ] Final evaluation function
[ ] Student SFT dataset
[ ] LoRA training
[ ] Full Student training
[ ] Ablation experiments
[ ] Graph generation
[ ] Final experiment summary

The repository is currently at the stage:

Experimental Foundation
        ↓
Candidate Trace Pool
        ↓
Student Skill-Gap Characterization
        ↓
READY FOR METHOD FINALIZATION

The next phase should begin only after the research direction, literature review, manual selection criteria, and evaluation protocol have been finalized.