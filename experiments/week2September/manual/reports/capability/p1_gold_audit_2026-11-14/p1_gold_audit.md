# Proposal 1 — Gold audit (2026-11-14)

## Executive result

- Gold vFinal: 100 batch + 85 supplement = 185 records.
- Unique Gold problem IDs: 185.
- Human-confirmed adjudication decisions: 22 (D_dev=22).
- Supplement semantic review completed: False.
- Priority extractor-error review queue: 170 records / 170 unique IDs.
- Gold review queue: 185 rows (one row per Gold vFinal ID).

## Gold vFinal split coverage

| Source | D_pool | D_dev | D_test |
|---|---:|---:|---:|
| Batch 100 | 100 | 0 | 0 |
| Supplement 85 | 0 | 85 | 0 |
| Total | 100 | 85 | 0 |

## Gold review status

| Status | Records |
|---|---:|
| confirmed (explicit human-confirmed adjudication) | 22 |
| pending (D_dev but not in human-confirmed adjudication file) | 63 |
| excluded from primary mastery evaluation (not D_dev) | 100 |
| unresolved (split/ID issue) | 0 |

## Priority error review split coverage

| Split | Records |
|---|---:|
| D_pool | 91 |
| D_dev | 79 |
| D_test | 0 |
| UNKNOWN | 0 |
| SPLIT_OVERLAP | 0 |

## Critical interpretation

The 170-row file is `priority_error_review_annotated.csv`: an extractor-error review queue. It is not 170 Gold labels awaiting adjudication. The queue contains records already present in Gold vFinal. A record may have a human-confirmed Gold adjudication and still require extractor-error analysis.

Do not edit Gold vFinal labels, split files, capability rules, or extractor code during this audit. If a genuine Gold-label defect is discovered, record the evidence and create a separately reviewed proposal; do not patch the frozen Gold release in place.

## Integrity findings

- Blank Gold IDs: 0
- Duplicate IDs in batch: 0
- Duplicate IDs in supplement: 0
- IDs duplicated across batch/supplement: 0
- Gold IDs outside all splits: 0
- Priority queue IDs not in Gold vFinal: 0
- Duplicate priority queue IDs: 0

Full ID lists, hashes, source inventory, support counts, and per-file counts are in `gold_inventory.json`.
The row-level review queue is in `gold_review_queue.csv`.

## Capability support (multi-label assignments)

| Capability | Support |
|---|---:|
| addition | 81 |
| division | 89 |
| fraction | 49 |
| multiplication | 144 |
| percentage | 41 |
| ratio | 30 |
| subtraction | 102 |

## Source file hashes

- `data/gold_vfinal/batch_100_annotations_vfinal.jsonl` — SHA-256 `76f1f08193a36282df2dce6fb44554f77d2778d362fee6f4e1606aa02a760181`
- `data/gold_vfinal/supplement_annotations_vfinal.jsonl` — SHA-256 `0f9733007f0fe7e53a2a22faeb3c0c55670e872378ae74f2062677143d98be44`
- `data/gold_vfinal/gold_vfinal_manifest.json` — SHA-256 `498707d205252109b7a6e97f848f6bc4204bda6bea64575547e8e012c13d2d04`
- `data/gold_vnext/gold_vnext_manifest.json` — SHA-256 `bba75f1400c4a2903fc792078d84e39ce85addefc819d6487ccb220bd19aeea6`
- `reports/capability/d3_final_regression/priority_error_review_annotated.csv` — SHA-256 `92554e8061cbb7a6dc55875b471f4b4ae4571bf959583fc4abb923dd263ff8a2`
- `reports/capability/d3_audit/adjudication_human_confirmed.csv` — SHA-256 `f9a8d55f5079ec94ad31cb0c933a6a0d00409cce0815e47fbefd80c1354224ab`
