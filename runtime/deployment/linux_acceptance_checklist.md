# Linux acceptance checklist

Linux status PENDING. Complete this checklist on the approved persistent-volume host, record UTC timestamp, package digest, command transcripts, exit codes and operator.

- [ ] Verify out-of-band package checksum file SHA, then verify every payload file in its original relative location.
- [ ] Verify no name/case collision, symlink/reparse substitution or checkout newline normalization. Confirm writable runtime namespaces and working directory.
- [ ] Verify Python 3.11, lock/wheel compatibility, pinned HF cache revision with tokenizer and weights, offline variables, disk and append-only/no-overwrite behavior. Confirm atomic rename, exclusive lock and hard link support on the real volume.
- [ ] Run the CPU suite and D_test audit-only. Keep D_test execution NOT_RUN.
- [ ] Run the four Linux CPU dry-runs. Expect 0/0/4/16 planned actions, no D_test, preserved A S2 prefix, dynamic fresh NLL at B S1/S2 and matching lineage.
- [ ] Confirm approved CUDA/BF16 and recorded driver/model/memory before live jobs. Each live checkpoint needs scope approval. Verify S2 before S3.
- [ ] Validate after each checkpoint and collect all output fingerprints. Run analysis to a fresh output namespace.
- [ ] Complete and freeze G7 on D_dev_select and record its SHA and evaluator fingerprint before requesting D_test authorization.
- [ ] Verify return-to-local archive and transfer manifest in an isolated incoming directory. G9 remains delegated until actual verified runtime evidence is delivered.
