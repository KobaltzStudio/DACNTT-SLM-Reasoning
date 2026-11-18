# B4 Seed 13 — Provenance Record

- Created (UTC): 2026-11-16T16:37:43.878407+00:00
- Scope: B4, seed 13, S1-S3 only

## Config and split

- Working config SHA-256: `e27fcf0ae16ec9b391a85757e0cc8ffa5630e29129f805d9dca495e2fdd2c461`
- Working config declared split SHA-256: `8bac2c8d43eae6df53b63f97f353ed6006551f44d5562b74941455301fec09a3`
- P1 staging config SHA-256: `17cf4b837dc42ac5145aea762847ca5dfba4bae58d253560b3b0dd6a254b73c5`
- P1 staging config declared split SHA-256: `85f4559246542d197c427318afb3eefb8b8492573b69ac23e691fc19ce93bbda`
- Actual split SHA-256: `85f4559246542d197c427318afb3eefb8b8492573b69ac23e691fc19ce93bbda`
- Working config ↔ split: MISMATCH
- P1 staging config ↔ split: MATCH

## Checkpoint evidence

| Checkpoint | ZIP SHA-256 | Train-set SHA-256 | Parent | Config SHA in train log | Status |
|---|---|---|---|---|---|
| student_ckpt_001.zip | `851742c95cdc1dba0333112f35f2f32d7e8cfe2e4235ae2c5ddc535bc2955615` | `614816f15b980f9958dd1747a3c0773171d8112ad167e116b7a7651d9623a006` | `student_ckpt_000` | `17cf4b837dc42ac5145aea762847ca5dfba4bae58d253560b3b0dd6a254b73c5` | PASS |
| student_ckpt_002.zip | `8ae764306b33f9456ffd18b09b4824784a87b1e827d15178e8b26bdcbe307f6f` | `cb82cb58ed58a92a8fd0dd33b09322e99191ecd048daf63a36b5ea4182898e1a` | `C:\KLTN-SLM-Reasoning\experiments\week2September\manual\models\task7\B4\seed_13\student_ckpt_001` | `17cf4b837dc42ac5145aea762847ca5dfba4bae58d253560b3b0dd6a254b73c5` | PASS |
| student_ckpt_003.zip | `cb55d9d34244f24964882f71a5654744d3d7cac8ca2ed6d7ebe77deb36c968df` | `f16cb78cbdaf4ce5280d79c552adab5ec57f56ca26a3796b02995f0de2441e0e` | `C:\KLTN-SLM-Reasoning\experiments\week2September\manual\models\task7\B4\seed_13\student_ckpt_002` | `17cf4b837dc42ac5145aea762847ca5dfba4bae58d253560b3b0dd6a254b73c5` | PASS |

## Split creator

- Status: UNRESOLVED
- Expected creator SHA-256: `052635fa4891476e9ed284f33d372ccaf477fcb708ce5b2d2bf2abd6ac93f539`
- Located script SHA-256: `7f1c9bbe5d832fad4d62b2ca45f922dd207abe785ef1791ecc25ba7689db781e`
- The split was not regenerated.

## Conclusion and limitations

VERIFIED: B4 seed 13 checkpoints S1-S3 reference the P1 staging experiment config by SHA-256 in their train_log.json files. This conclusion is limited to these three checkpoints.

This record does not establish S0 weights, other methods, other seeds, or all P2 training runs.
The working config remains unchanged.
