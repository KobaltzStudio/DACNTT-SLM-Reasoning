# Windows CPU acceptance

| Check | Result |
|---|---|
| Original workspace `python -B -m unittest discover -s tests -v` | 103/103, exit 0, 25.140 s |
| Detached package, same suite | 103/103, exit 0, 25.958 s |
| D_test-only synthetic suite | 5/5, exit 0 |
| Controller plans on source and detached tree | 0 / 0 / 4 / 16 actions, all exit 0 |
| In-memory compile | 202 files, exit 0 |
| `git --no-optional-locks diff --check` | exit 0; only existing Git newline warnings |
| Sealed package rehash and Git Bash `sha256sum -c manifests/SHA256SUMS.txt` | exit 0, 655 payload members |
| Read-only protection recheck | 52/52 equal |
| Operator instructions | 6 Bash blocks checked by `bash -n`, exit 0 each |

Python `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe`, version 3.11.9. Suite ran with CUDA hidden and both Hugging Face/Transformers flags set to offline. Tests use synthetic artifacts and stubs. See `unittest_source.log`, `unittest_package.log`, `git_diff_check_final.txt`, `final_integrity.json`, `handoff_syntax.log` and `bash_sha256check.log`. Current results are five tests above the sealed 98-test baseline. D_test real inference and GPU jobs NOT_RUN.
