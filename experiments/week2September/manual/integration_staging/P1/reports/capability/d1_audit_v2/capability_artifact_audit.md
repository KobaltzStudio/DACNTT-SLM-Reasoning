# D1 Gold v2 Capability Artifact Audit

## Gold sources

| Source | Records | SHA-256 |
|---|---:|---|
| batch_100 | 100 | `76f1f08193a36282df2dce6fb44554f77d2778d362fee6f4e1606aa02a760181` |
| supplement | 85 | `f7a2f11d8a4f8f2721e659b58363068bd8a932f1292b55d3f20907bfb34caefc` |

- Total Gold records: **185**
- Unique Gold problem IDs: **185**
- Cross-source duplicate IDs: **0**

## Capability support

| Capability | Batch 100 | Supplement | Combined unique Gold |
|---|---:|---:|---:|
| addition | 51 | 27 | 78 |
| subtraction | 51 | 55 | 106 |
| multiplication | 71 | 84 | 155 |
| division | 42 | 47 | 89 |
| percentage | 12 | 29 | 41 |
| fraction | 18 | 31 | 49 |
| ratio | 0 | 30 | 30 |

## Gold overlap with splits

| Split | Split IDs | Gold overlap | Gold coverage | Split IDs without Gold |
|---|---:|---:|---:|---:|
| D_pool | 6968 | 100 | 1.44% | 6868 |
| D_dev | 500 | 85 | 17.00% | 415 |
| D_test | 1319 | 0 | 0.00% | 1319 |

## Data quality checks

- Missing problem IDs: 0
- Missing capability lists: 0
- Invalid capability labels: 0
- Duplicate labels within a record: 0
- Duplicate IDs within batch_100: 0
- Duplicate IDs within supplement: 0
- Cross-source duplicate IDs: 0

## Split integrity

- D_pool: 6968 rows, 6968 unique IDs, 0 duplicates.
- D_dev: 500 rows, 500 unique IDs, 0 duplicates.
- D_test: 1319 rows, 1319 unique IDs, 0 duplicates.
- D_pool__D_dev: 0 overlapping IDs.
- D_pool__D_test: 0 overlapping IDs.
- D_dev__D_test: 0 overlapping IDs.

## Interpretation and limitations

- Split coverage is descriptive, not automatically a pass/fail criterion.
- The expected Gold-to-split relationship must be checked against the split protocol.
- Capability support counts problem-level labels, not trajectory-level predictions.
- This report does not replace the Task 4 extractor evaluation.
- Cross-source duplicate IDs must be reviewed before treating combined support as final.

## Generated files

- `capability_artifact_audit.json`
- `gold_record_inventory.csv`
- `source_capability_support.csv`
- `split_capability_support.csv`
