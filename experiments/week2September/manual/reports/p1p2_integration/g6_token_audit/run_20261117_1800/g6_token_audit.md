# G6 token-table audit

- Status: **PASS**
- Pool records: 4353; unique IDs: 4353
- Token records: 4353; unique IDs: 4353
- Common IDs: 4353
- Missing token rows: 0
- Extra token rows: 0
- Problem ID mismatches: 0
- Invalid response_tokens: 0

## Input fingerprints
- Verified pool SHA-256: `95f34cff848bfbd16305e5f0ecc2656525dc1e319ca2b1a404f9b75c8029cd04`
- Token table SHA-256: `5d3dbf340e64832384e8fdbc5166913ccf88c22d68e27078ed98b903b4c62933`

## Checks
- [x] pool_jsonl_parse
- [x] token_jsonl_parse
- [x] pool_trajectory_id_present
- [x] token_trajectory_id_present
- [x] pool_trajectory_id_unique
- [x] token_trajectory_id_unique
- [x] token_table_covers_pool
- [x] token_table_has_no_extra_ids
- [x] problem_ids_match
- [x] response_tokens_positive_integer

## Interpretation
A PASS means the token table is structurally aligned with the verified pool by trajectory_id and problem_id. It does not by itself prove historical tokenization provenance or equality with historical train-log pool hashes.
