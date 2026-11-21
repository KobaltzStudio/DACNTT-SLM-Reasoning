# G7 historical lineage forensics

## B4 seed 13 S1

- Main historical prediction: `C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual\runs\main\B4_seed13\S1\eval_dev.jsonl`.
- Main SHA-256: `0788f385d387178383184450ab9b0897f1ed38a861e06ad088a1135da70b0351`.
- Sidecar: `C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual\reports\capability_g4_validation\B4_seed13_S1`. Manifest SHA-256: `0c0f51e6514863d0868a7c5ef0b8d6ae431fe23fed35fab741b227dab9d696fa`.
- Expected prediction SHA-256 in lineage: `f9262326c8207a45665b67c521a1f74a1eabe4f4dfed2e7f49a9d6d17760a4d4`.
- Existing derived prediction: `C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual\reports\p1p2_integration\derived_predictions\B4_seed13\eval_student_ckpt_001_dev_status.jsonl`. SHA-256: `f9262326c8207a45665b67c521a1f74a1eabe4f4dfed2e7f49a9d6d17760a4d4`.
- Main IDs: 500. Derived IDs: 500. Shared IDs: 500. Different strict status on shared IDs: 75. Different full row objects: 500.
- Provenance manifest: `C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual\reports\p1p2_integration\derived_predictions\B4_seed13\adapter_manifest.json`. SHA-256: `741bcd7a5ed19d7a3b685355910ffc59d4ff155347466a65691a02e1e794448e`.
- Existing derivation script copies verification_status to status after checking strict correctness against the original correctness flag.
- Upstream SHA-256: `9bb9aeb1c356b7563fc3d8b1b45fe9553bc7c2ca7907e7672833fae448f9a26d`. Adding status from verification_status reproduces derived row objects exactly: True.

The derived prediction is the canonical input for this evaluated lineage. No historical input or digest was rewritten. Prediction equivalence alone does not authenticate B4/B5 adapter identity.

## Remaining blockers

Seed-13 integrated P1-DEFICIT and P1P2 S1?S3 predictions and sidecars are absent. G7 requires all four method series before publication.
