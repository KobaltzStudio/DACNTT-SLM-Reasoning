# B4 Seed 13 — Learning Curve

## 1. Scope

This report contains three local B4 checkpoints trained with seed 13.

- S1: student_ckpt_001
- S2: student_ckpt_002
- S3: student_ckpt_003

This is one training lineage. It is not a multi-seed aggregate.

## 2. Training lineage

| Checkpoint | Parent | Effective batch | Micro-batch | Grad accumulation |
|---|---|---:|---:|---:|
| student_ckpt_001 | student_ckpt_000 | 8 | 4 | 2 |
| student_ckpt_002 | student_ckpt_001 | 8 | 4 | 2 |
| student_ckpt_003 | student_ckpt_002 | 8 | 1 | 8 |

## 3. Evaluation protocol

- Evaluation split: D_dev
- Prediction count: 500 per checkpoint
- Gold source: Gold vNext
- Confirmed Gold D_dev IDs: 22
- Join key: problem_id
- Primary capability correctness: strict `correct`
- Missing predictions are not imputed.
- Capability labels are multi-label.

## 4. Required artifacts

- B4_seed13_learning_curve.csv
- B4_seed13_learning_curve_manifest.json
- B4_seed13_training_config.csv
- B4_seed13_checkpoint_inventory.csv

## 5. Interpretation

Capability support is capability-specific. A single problem may contribute to multiple capability rows.

Capability mastery must be interpreted together with support and Wilson 95% confidence intervals.

The three checkpoints use the same seed, but their micro-batch configurations are not identical. Report this difference explicitly.

## 6. RunPod comparison

Do not merge local and RunPod results until pool hash, train-set hash, base model revision, parent lineage, training configuration, evaluation backend, decoding configuration, and Gold source hashes have been compared.

Local HF evaluation and RunPod vLLM evaluation must remain distinguishable in the experiment records.