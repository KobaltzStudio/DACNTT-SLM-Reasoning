# Gold Review Preparation — 2026-11-15

## Source integrity

- Gold batch records: 100
- Gold supplement records: 85
- Gold unique IDs: 185
- Gold review queue records: 185
- Human-confirmed decisions: 22
- Priority extractor-error records: 170

## Gold review status

- Confirmed: 22
- Pending: 63
- Excluded: 100

## Worklist

- Pending D_dev records: 63
- Also in priority extractor queue: 61
- Not in priority extractor queue: 2
- Worklist: `data\gold\review_2026-11-15\adjudication_worklist_63_pending.csv`

## Important scope restrictions

- The 170-row priority queue is not a Gold adjudication queue.
- Only the 63 pending D_dev records enter this worklist.
- The 22 human-confirmed records are retained unchanged.
- The 100 D_pool records remain excluded from primary mastery evaluation.
- This script does not modify Gold vFinal, Gold vNext, split files, capability config, or extractor rules.
- This worklist is not a frozen Gold release.

## Source schema inspection

`reports\gold\review_2026-11-15\gold_source_schema_inspection.json`

The schema inspection contains source fields and sample records. Use it before writing a source-specific join or adjudication exporter.
