# Phase 4 — Detached package validation

PASS on Windows. `staging_sha256_final.csv` has one source and staged SHA match per runtime file. 651 regular files were copied and verified at an independent root; the original research tree was not used as a write destination. The package retains canonical P2 relative paths and does not create junctions or symlinks.

Running the staged controller with a hard subprocess block produced A S1/B S1 0/0, A S2 4 and B S2–S3 16. Stage names and arguments match the source plans. A S2 reuses the existing adapter and predicts only the remaining D_dev rows when eventually approved. Staged G6 validated 39 sidecars, G7 surfaced nine candidates in partial mode, and G8 preflight returned 0. Staged D_test input/evaluator digests matched the source audit and counted exactly 1,319 IDs. No model commands ran.

The first staging dry-run showed that the earlier manifest copied `S0_nll.jsonl` without its required `S0_nll.summary.json`. Published the existing summary into the new copy only, then rechecked all 651 digests. The attempts and diagnosis are preserved in `package_cpu_validation*.log`. Final deployment documentation and checksum indices are added and sealed in phase 5.
