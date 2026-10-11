# Teacher trajectory pool

This directory stores Teacher-generated trajectories used by the manual Task-4 capability extractor and later reasoning-distillation experiments.

## Task 4 canonical batch

`batch_100_teacher_raw.jsonl` is generated from:

`data/batch_100/batch_100.jsonl`

using:

- Teacher: `Qwen/Qwen2.5-3B-Instruct`
- K: 5 trajectories/problem
- temperature: 0.7
- max_new_tokens: 512
- checkpoint: `ckpt_000`
- fixed prompt in `scripts/generate_teacher_trajectories_batch.py`

For 100 problems, the expected raw count is 500 trajectories.

The Teacher is not asked to provide capability labels. Capability labels are assigned only by the rule-based extractor.

## Existing 50x5 data

The project already contains an older file named `teacher_trajectories_50x5.jsonl` in `raw.zip`. It is real Teacher-generated data for 50 of the 100 batch problems, but it uses an older schema (`question_id`, `trajectory`, `predicted_answer`, etc.) and does not preserve the generation prompt/seed. Therefore it is retained as historical trajectory-pool evidence, not silently promoted to the canonical Task-4 batch.

## Task-4 flow

1. Generate `batch_100_teacher_raw.jsonl`.
2. Filter verified trajectories to `batch_100_teacher_verified.jsonl`.
3. Run `extract_capabilities_rule_based.py`.
4. Run `evaluate_capability_extractor.py` against `data/batch_100/batch_100_annotations.jsonl`.
5. The final reports are:
   - `reports/capability_extractor_batch100_report.json`
   - `reports/capability_extractor_batch100_report.csv`

The manual annotations remain the problem-level gold and are never modified by this pipeline.
