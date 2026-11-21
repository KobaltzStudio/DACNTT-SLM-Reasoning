# Test execution log

Generated UTC: 2026-11-18T03:01:29.409405+00:00.

Original interrupted baseline: `C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual\reports\p1p2_integration\final_validation\runtime_20261118_113346\baseline.log`.
Observed: compile=0, tests=1, 76 tests, one assertion failure and ten errors.
test_publish_pair_rolls_back_first_if_second_publish_fails, tests/test_p1p2_artifact_manager.py:111. Windows WinError 5 occurred on the first real hard link; expected OSError text simulated was never reached.
Unrestricted baseline: compile=0, tests=0, 76 tests.
A separate runtime run detected intermittent WinError 5 in the post-eval hook direct rename on S3. The hook now calls the evaluator's tested no-overwrite retry publisher. Later fixture runs passed.

| Check | Command | Exit | Result |
|---|---|---:|---|
| compile | `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe -m compileall -q scripts tests` | 0 | PASS |
| all_tests | `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe -B -m unittest discover -s tests -v` | 0 | Ran 88 tests in 14.103s; OK |
| runtime | `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_p1p2_runtime.py -v` | 0 | Ran 7 tests in 12.969s; OK |
| analysis_fixtures | `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_p1p2_analysis.py -v` | 0 | Ran 5 tests in 0.586s; OK |
| resume_fixtures | `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_p1p2_resume.py -v` | 0 | Ran 2 tests in 0.019s; OK |
| no_overwrite_fixtures | `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_p1p2_no_overwrite.py -v` | 0 | Ran 3 tests in 0.012s; OK |
| cli_and_hook_fixtures | `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_p1p2_controller.py -v` | 0 | Ran 8 tests in 0.030s; OK |
| dry_deficit | `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe -B scripts/run_p1_p2.py --method P1-DEFICIT --seed 13 --rounds all --dry-run` | 0 | DRY_RUN_REPORT=C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual\reports\p1p2_integration\integration_tests\dry_run_1794970647621778200.json |
| dry_combined_method | `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe -B scripts/run_p1_p2.py --method P1P2 --seed 13 --rounds all --dry-run` | 0 | DRY_RUN_REPORT=C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual\reports\p1p2_integration\integration_tests\dry_run_1794970648339461400.json |
| dry_combined | `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe -B scripts/run_p1_p2.py --methods P1-DEFICIT P1P2 --seeds 13 --rounds all --dry-run` | 0 | DRY_RUN_REPORT=C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual\reports\p1p2_integration\integration_tests\dry_run_1794970649235678000.json |
| G6 inventory | `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe -B scripts/build_capability_learning_dynamics.py --manual . --output C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual\reports\p1p2_integration\final_validation\runtime_20261118_024353_resume\verified_analysis --inventory-only` | 0 | 37 raw, 35 logical, 2 alternate provenance records |
| G7 real | `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe -B scripts/select_checkpoint_on_dev.py` | 1 | Missing P1-DEFICIT S1 sidecar after verified B4/B5 inputs |
| G8 real availability | `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe -B scripts/build_p1p2_analysis_figures.py --preflight` | 0 | Seven blocked, zero production figures |
| Bounded BF16 LoRA | See exact argv in lora_smoke_test_report.json | 0 | One step, finite loss, saved and reloaded adapter, inference succeeded |
| Git | `git diff --check` | 0 | PASS |
| Git | `git --no-optional-locks status --short --branch` | 0 | git_status.log |

No full training, D_test evaluation, RunPod, commit or push.
