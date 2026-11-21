# Pre-push audit

This Git repository lives at the handoff's `github/` root. The initial index on branch `main` has 63 files from `manifests/public_files.txt`. The branch is unborn and has no configured remote. The parent handoff's 800-entry SHA index describes the previous handoff snapshot. The dedicated GitHub release manifest records the updated candidate.

| Check | Status | Evidence |
| --- | --- | --- |
| Source completeness | PASS for the release scope | Static closure of 22 Python modules. The 22 core modules, 13 runtime test files and two requirement files match the runtime byte for byte. CLI and P2 selector source cover B2/B3/B4/B5, P1-DEFICIT and P1P2. Deployment validation covers Run A and Run B. |
| Security and privacy | PASS for the static candidate audit | Stage-only file, binary, secret-pattern, local-personal-path and public-link checks. Frozen configs, datasets, weights, NLL values and private outputs remain in the separate transfer. The checksum inventory still requires approval for publication. |
| License and publication | PENDING | No license grant established for this release. Owner approval and review of third-party code, data/model terms, figures and redacted metadata are required. No license added. |
| Clean checkout | PASS on Windows | Exported the Git index and verified each blob. 77 source-only runtime tests and 7 deployment tests passed. The 26 frozen-config tests passed separately against the private runtime, giving 103 runtime tests in total. The 11 CLI help checks and 10 deployment Bash syntax checks passed. |
| RunPod compatibility | PASS for Windows read-only compatibility | All 658 sealed files verified. Plans for A S1, B S1, A S2 and B S2 through S3 had 0/0/4/16 actions. A S2 scheduled evaluation and the hook without retraining. B scheduled NLL at S1/S2 from the adapters used as S2/S3 training parents. Real Linux CPU validation remains pending. |
| Protected fingerprints | PASS | All 52 original hashes, three sealed indices and all 743 handoff index entries outside `github/` matched. A S1 has 416/500 strict D_dev; B S1 has 406/500; A S2 has 75 unique saved predictions. |

The first clean export revealed that two test modules import through the `scripts` namespace. The source-only runner now adds the manual root to its test import path. Git whitespace checks accept preserved Windows CRLF from the sealed source. Bash wrappers retain LF.

## Commands and outcomes

Run these from the GitHub source root. Each verification command listed here returned 0.

```text
git --literal-pathspecs add --pathspec-from-file=manifests/public_files.txt
git status --short
git diff --cached --check
git diff --cached --stat
git ls-files --cached
git checkout-index --all --prefix=<fresh-temp-checkout>/
python -B tools/preflight.py source
python -B tools/preflight.py tests
python -B -m unittest discover -s tests -v
python -B tools/preflight.py bundle --bundle <verified-sealed-runtime>
```

The final four commands above ran from the exported checkout. The expected negative command `python -B tools/preflight.py bundle --bundle <missing-path>` returned 2 with `BUNDLE_REQUIRED`. The two config suites ran from the sealed manual root with `python -B -m unittest discover -s tests -p test_p1p2_method_registry.py -v` and the same command using `test_p1p2_unified_config.py`. They returned 0 with 11 and 15 tests.

The required private inputs include the frozen registry, unified run config, experiment config, pool and token table, dev IDs and Gold labels, predictions and sidecars, adapters and the separate seven-file Student snapshot. See [bundle workflow](GITHUB_TO_RUNPOD_WORKFLOW.md) and [publication checklist](GITHUB_RELEASE_CHECKLIST.md). SHA-256 values for all staged files except the release manifest itself are in [the release manifest](../manifests/GITHUB_RELEASE_MANIFEST.json).

Research status remains A S1 PASS, A S2 PARTIAL, A S3 NOT RUN, B S1 PASS and B S2/S3 NOT RUN. G6/G7/G8 are PARTIAL. G9, live RunPod execution and D_test are NOT RUN. Publication, commit, remote setup and push await approval.
