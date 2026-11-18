# G5.9 post-evaluation publication patch

## Included files
- `scripts/run_p1p2_post_eval.py`: bounded Windows publication retry; no-overwrite
  collision checks; preserves staging on failure and reports its recovery path.
- `scripts/capability_eval.py`: applies the same publication contract to its standalone
  CLI, keeping the evaluator and wrapper behavior consistent.
- `tests/test_g59_publication.py`: four hook publication tests.
- `tests/test_capability_eval_publication.py`: four evaluator publication tests.

## Safety properties
- Uses `os.rename`, not `os.replace`.
- Never deletes the staging directory after build/publication failure.
- Retries `PermissionError` five times with bounded backoff.
- Checks destination before every attempt and rejects collisions.
- A staging directory is not a final sidecar and cannot be counted as PASS.

## Apply in the project
1. Extract this ZIP to a temporary review folder, not directly over the project.
2. Back up both current source files.
3. Copy the two files under `scripts/` to the project's `scripts/` directory.
4. Copy the two test files under `tests/` to the project's `tests/` directory.
5. Do not change historical predictions, train sets, logs, checkpoints, config or splits.

## Validate from project root
```powershell
python -m py_compile scripts\run_p1p2_post_eval.py scripts\capability_eval.py tests\test_g59_publication.py tests\test_capability_eval_publication.py
python -m unittest discover -s tests -p "test_g59_publication.py" -v
python -m unittest discover -s tests -p "test_capability_eval_publication.py" -v
python scripts\run_p1p2_post_eval.py --help
```

The included eight publication tests passed in the build environment. This does not yet
prove the patch works on the user's Windows machine or that historical G5.9 is complete.

## Retry policy
After the above validation passes, invoke the hook directly for only `B4_seed42_S3`
using the existing six input files from:
`reports\p1p2_integration\historical_g59_inputs\run_20261117_073550_117070\`

Do not run `run_historical_g59_batch.py` without a single-context retry mode; its current
implementation loops over all 33 contexts.
