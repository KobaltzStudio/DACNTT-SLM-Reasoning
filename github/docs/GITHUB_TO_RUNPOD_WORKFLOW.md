# GitHub source and RunPod inputs

Clone the approved source separately from the private artifact intake. Obtain the exact sealed runtime and the seven separately checksummed Student cache entries from the operator. Use `manifests/runtime_payload.csv` for all 658 paths and SHA values. Preserve byte-for-byte files and the canonical P2 relative layout. The GitHub checkout contains no frozen research configs, datasets or trained weights.

```bash
python -B tools/preflight.py source
python -B tools/preflight.py tests
python -B tools/preflight.py bundle --bundle "$P1P2_PACKAGE"
bash deployment/verify_package.sh --package "$P1P2_PACKAGE"
```

The bundle check verifies the sealed SHA indices, 37 matching source/test/lock files and the three frozen configs, then runs plans with model subprocesses blocked. If the bundle is missing it exits with BUNDLE_REQUIRED. If you change the checkout's source, rebuild and re-test a separate compatible package before deploying it. The sealed package is the source of truth for frozen files. Windows paths recorded by that package are mapped through its metadata; use a separate writable Linux tree with the same relative P2 layout.

The operator provisions an approved Python 3.11 environment from the lock and an offline, checksum-validated HF cache. Verify the package and cache at the destination, then create a fresh operational copy and run the CPU preflight:

```bash
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
bash deployment/verify_model_cache.sh
bash deployment/setup_environment.sh --package "$P1P2_PACKAGE" --work "$WORK"
bash deployment/linux_cpu_preflight.sh --package "$P1P2_PACKAGE" --work "$WORK" --output "$LOG_ROOT/preflight"
```

The Linux CPU receipt should record 0/0/4/16 actions for A S1, B S1, A S2 and B S2–S3. A S2 reuses its adapter and 75 D_dev rows. B S2/S3 use S1/S2 NLL and their exact parent checkpoints. The wrappers require a zero-action parent plan, exact approval scope and a matching real Linux receipt for live execution. Preview with `bash deployment/run_a_s2.sh --package "$P1P2_PACKAGE" --work "$WORK"`. After approval, the four supported wrapper/scope pairs are A S2 `run_a_s2.sh` / `P1-DEFICIT:13:S2`, A S3 `run_a_s3.sh` / `P1-DEFICIT:13:S3`, B S2 `run_b_s2.sh` / `P1P2:13:S2`, and B S3 `run_b_s3.sh` / `P1P2:13:S3`. Each uses `--execute --approve <scope> --receipt "$LOG_ROOT/preflight/preflight.json" --output <fresh-log-dir>`. Validate S2 before S3.

Keep interrupted outputs, logs, locks and adapter lineage. Return a separately checksummed result bundle to a fresh incoming path using the collection and verification scripts. The unified controller evaluates D_dev only. A final D_test evaluation requires locked G7 FINAL, independent manifest SHA, matching evaluator/checkpoint SHA and separate approval. Linux CPU and live RunPod execution remain outside this Windows audit.
