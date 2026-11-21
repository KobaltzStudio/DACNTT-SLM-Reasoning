# Final CPU regression — Phase F

Interpreter `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe` 3.11.9. The suite used `CUDA_VISIBLE_DEVICES=-1`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `MPLBACKEND=Agg` and `-B`. GPU/model actions were not invoked. Programmatic dry-runs use a hard-fail subprocess guard. The additional model-free A S2 rehearsal was run from the audit directory, so the shipped suite count stays 103.

| Check | Exit | Evidence |
|---|---:|---|
| `python -B -m unittest discover -s tests -v` on original source | 0 | 103/103 in 28.448 s, unittest_source.log |
| Same command on sealed detached package | 0 | 103/103 in 28.443 s, unittest_package.log |
| `python -B -m unittest discover -s tests -p test_final_d_test.py -v` | 0 | 5/5 in 0.582 s, unittest_d_test.log |
| Release A S2 rehearsal with 75 CRLF + 425 LF synthetic rows | 0 | 1/1 and read-only plans on both roots, resume_rehearsal.log |
| Controller/hook/D_test CLI help, both-root D_test audit-only | 0 | CLI help outputs, d_test_source.json and d_test_package.json |
| `bash -n` on the five deployment command blocks | 0 | bash_syntax_verified.log |
| `git --no-optional-locks diff --check` | 0 | git_diff_check.txt |
| Post-regression SHA recheck of package and protected inputs | 0 | final_seal_check.json. 658 files including indices, 52/52 unchanged |
| Live checks using CIM, NVIDIA-SMI and lock inventory | 0 | live_preflight.txt and live_final.txt. No pipeline process or lock |

Git branch `codex/controller-dryrun-fix`, HEAD unchanged, code worktree status unchanged. Tracked diff remains the inherited 12 files, +686/−210. New audit files and recovery/guide updates are not a source change. No new release package needed.
