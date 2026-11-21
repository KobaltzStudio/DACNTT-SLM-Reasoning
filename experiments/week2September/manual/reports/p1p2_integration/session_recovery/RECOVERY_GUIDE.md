# NEXT_SESSION_START_HERE

- Working directory `C:/Users/PC - NGHI/Desktop/Pipeline/P2/experiments/week2September/manual`, branch `codex/controller-dryrun-fix`.
- Use the same sealed package at `C:/Users/PC - NGHI/Desktop/Pipeline/p1p2_unified/runpod_package_20261119_004529`. Its checksum index SHA is `bf0c50c301de9e2b78d9533a6a995733a431a6834d8ad019926e1c826af07798`. It was independently rehashed after the 103-test rerun.
- Evidence directory `C:/Users/PC - NGHI/Desktop/Pipeline/P2/experiments/week2September/manual/reports/p1p2_integration/final_validation/pre_runpod_release_20261119_011425`. Read RELEASE_INTEGRITY_MANIFEST.json for phase evidence, hashes and remaining gates. Read GPTGUIDE Part F and the five session recovery files, then check live Git, Python processes, GPU, locks and the 52 protected fingerprints.
- Source Windows cache has seven verified files for `Qwen/Qwen2.5-1.5B-Instruct` pinned revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. When explicitly approved, transfer those files separately and check MODEL_CACHE_SHA256SUMS.txt. Keep the sealed package and writable Linux work tree separate.
- Next safe authorized phase is Linux CPU acceptance from RUNPOD_DEPLOYMENT_COMMANDS.md. Expect A S1/B S1/A S2/B S2–S3 action counts 0/0/4/16. Verify wheel lock, filesystem and cache. Linux status PENDING. No upload authorization assumed.
- Preserve the two validated S1 checkpoints and the 75 A S2 prediction rows plus the existing A S2 adapter. After separate scope approvals, run bounded S2 first, validate, then consider S3. No blanket RunPod, GPU, D_test or cleanup authorization.
- D_test needs all G7 candidates, FINAL manifest and externally pinned SHA before separate approval. Original ZIP and bytecode cleanup is PENDING_APPROVAL.

Safe local commands include `git --no-optional-locks status --short --branch`, `Get-FileHash -Algorithm SHA256 -LiteralPath '<package>/manifests/SHA256SUMS.txt'`, and `python -B scripts/run_final_d_test.py --audit-only`. Rerun only checks affected by live changes, preserving verified artifacts.

## Persistent evidence

See CURRENT_STATE.json and the tracked audit evidence record. Phase checks are read-only except Temp-only synthetic fixtures and report generation. Recheck live state before continuing. No authorization is inherited from this snapshot.
