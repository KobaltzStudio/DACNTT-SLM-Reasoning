# Security and data policy

Review the exact candidate tree and `manifests/public_files.txt` on each publication. All frozen datasets, Gold/splits, checkpoints, NLL, predictions, evaluation/selection logs, capability sidecars, analysis data, external model weights and private provenance remain in the authorized private transfer channel. Small JSON/CSV needs the same permission check as a large file. Only redacted checksum and path metadata are in this candidate. Use a new review if those paths are subject to confidentiality restrictions.

Keep keys, access tokens, secret env files, personal local paths and cache auth outside repository paths. An automated pattern scan reduces accidental disclosure but does not prove that every secret or permission issue is absent. Obtain owner approval and third-party rights attestations before first publication. Use a fresh destination and verify independently pinned hashes before importing returned results.
