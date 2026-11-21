# G6 Input Audit

- G5.9 reconciliation: PASS
- Sidecar manifests under capability root: 34
- Unique run IDs: 34
- S0 candidates: 1

## S0 candidates

- `SHARED_seed0_S0` method=SHARED seed=0 round=0 checkpoint=S0 manifest=`C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual\reports\capability\g5_9_real_data_s0\SHARED_seed0_S0\student_capability_evaluation_manifest.json`

## Capability CSV schemas

- `C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual\reports\capability\g5_9_historical_20261117\B2_seed13_S1\capability_metrics.csv`
  - rows=7; columns=['run_id', 'method', 'seed', 'checkpoint', 'checkpoint_id', 'capability', 'n_support', 'n_correct', 'n_incorrect', 'mastery', 'deficit', 'ci95_low', 'ci95_high', 'ci_method', 'strict_metric', 'gold_policy']
  - sha256=0cf7002d55e8607097793ea6d375bd499765e54a0d389efc02c700927da94212

## State API

- `sha256_file(path)` at line 32
- `read_json(path)` at line 40
- `stable_state(value)` at line 47
- `main()` at line 56

## Errors

- None
