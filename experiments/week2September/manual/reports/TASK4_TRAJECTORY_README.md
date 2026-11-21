# Task 4: actual Teacher trajectory generation and extractor evaluation

The current `batch_100` problem and annotation files are already the canonical inputs. No new manual annotation is needed.

From the repository root:

```text
python experiments\week2September\manual\scripts\generate_teacher_trajectories_batch.py ^
  experiments\week2September\manual\data\batch_100\batch_100.jsonl ^
  experiments\week2September\manual\trajectory\pool\batch_100_teacher_raw.jsonl
```

Then run the complete extractor/evaluation pipeline:

```text
python experiments\week2September\manual\scripts\run_task4_extractor_batch100.py ^
  --repo experiments\week2September\manual
```

Expected generation target:

- 100 problems
- 5 trajectories/problem
- 500 raw trajectories

The pipeline does not change the existing manual annotations. It creates new trajectory artifacts and the two requested reports.

Important: do not use the old `teacher_trajectories_50x5.jsonl` as the canonical Task-4 batch unless its generation provenance is independently confirmed. It is retained as historical data.
