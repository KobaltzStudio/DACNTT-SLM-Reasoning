# Historical G5.9 Reconciliation

- Status: **PASS**
- Contexts reconciled: 33/33
- PASS or recovered: 33
- Failed: 0
- Batch manifest SHA-256: `2434edc223c7c0e5188e803f873cc40f41c01f0d024caba076dbc9eda5d29622`
- Historical batch manifest modified: **No**
- Alias policy: B4/B5 S1 represented once by canonical B5 sidecars.

## Checks

| Scope | Check | Status | Detail |
|---|---|---|---|
| batch | schema | PASS | p1p2.historical_g59_batch.v2 |
| batch | expected_context_count | PASS | observed=33 expected=33 |
| batch | expected_alias_count | PASS | observed=3 expected=3 |
| alias | B4_seed13_S1 | PASS | canonical=B5_seed13_S1; status=EXACT_ALIAS_CONFIRMED |
| alias | B4_seed42_S1 | PASS | canonical=B5_seed42_S1; status=EXACT_ALIAS_CONFIRMED |
| alias | B4_seed2026_S1 | PASS | canonical=B5_seed2026_S1; status=EXACT_ALIAS_CONFIRMED |
| context | B2_seed13_S1 | PASS | PASS |
| context | B2_seed13_S2 | PASS | PASS |
| context | B2_seed13_S3 | PASS | PASS |
| context | B2_seed2026_S1 | PASS | PASS |
| context | B2_seed2026_S2 | PASS | PASS |
| context | B2_seed2026_S3 | PASS | PASS |
| context | B2_seed42_S1 | PASS | PASS |
| context | B2_seed42_S2 | PASS | PASS |
| context | B2_seed42_S3 | PASS | PASS |
| context | B3_seed13_S1 | PASS | PASS |
| context | B3_seed13_S2 | PASS | PASS |
| context | B3_seed13_S3 | PASS | PASS |
| context | B3_seed2026_S1 | PASS | PASS |
| context | B3_seed2026_S2 | PASS | PASS |
| context | B3_seed2026_S3 | PASS | PASS |
| context | B3_seed42_S1 | PASS | PASS |
| context | B3_seed42_S2 | PASS | PASS |
| context | B3_seed42_S3 | PASS | PASS |
| context | B4_seed13_S2 | PASS | PASS |
| context | B4_seed13_S3 | PASS | PASS |
| context | B4_seed2026_S2 | PASS | PASS |
| context | B4_seed2026_S3 | PASS | PASS |
| context | B4_seed42_S2 | PASS | PASS |
| context | B4_seed42_S3 | PASS | RECOVERED_AFTER_BATCH_FAILURE |
| context | B5_seed13_S1 | PASS | PASS |
| context | B5_seed13_S2 | PASS | PASS |
| context | B5_seed13_S3 | PASS | PASS |
| context | B5_seed2026_S1 | PASS | PASS |
| context | B5_seed2026_S2 | PASS | PASS |
| context | B5_seed2026_S3 | PASS | PASS |
| context | B5_seed42_S1 | PASS | PASS |
| context | B5_seed42_S2 | PASS | PASS |
| context | B5_seed42_S3 | PASS | PASS |
| inventory | sidecar_directory_set | PASS | observed=33 expected=33 unexpected=[] missing=[] |

## Errors

No reconciliation errors.
