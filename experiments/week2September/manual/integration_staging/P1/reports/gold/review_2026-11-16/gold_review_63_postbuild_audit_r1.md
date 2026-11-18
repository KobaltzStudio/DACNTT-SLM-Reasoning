# Gold vNext r1 Post-build Independent Audit

- Audit status: **PASS**
- Freeze status: **NOT FROZEN**
- Freeze authorized by this audit: **NO**
- Batch: **100**
- Supplement: **85**
- Unique total: **185**
- Ledger rows: **63**

## Checks

- **PASS** `parent_batch_100` — 100
- **PASS** `parent_supplement_85` — 85
- **PASS** `r1_batch_100` — 100
- **PASS** `r1_supplement_85` — 85
- **PASS** `batch_supplement_disjoint` — []
- **PASS** `r1_total_unique_185` — 185
- **PASS** `batch_byte_identical_to_parent` — {"parent": "5b655ab6705fa8d6178871d35f30712b90058354a29952b9e51e88e0108c8a9f", "r1": "5b655ab6705fa8d6178871d35f30712b90058354a29952b9e51e88e0108c8a9f"}
- **PASS** `parent_batch_matches_parent_manifest` — {"manifest_hash": "5b655ab6705fa8d6178871d35f30712b90058354a29952b9e51e88e0108c8a9f", "actual_hash": "5b655ab6705fa8d6178871d35f30712b90058354a29952b9e51e88e0108c8a9f"}
- **PASS** `parent_supplement_matches_parent_manifest` — {"manifest_hash": "970c5d63c2f0f822a73805c0dd03a727a542d08077dcc3fbdffeb043e7f29257", "actual_hash": "970c5d63c2f0f822a73805c0dd03a727a542d08077dcc3fbdffeb043e7f29257"}
- **PASS** `only_two_supplement_notes_changed` — ["gsm8k_train_00713", "gsm8k_train_00830"]
- **PASS** `gsm8k_train_00713_note_exact_match` — "Exact expected note comparison"
- **PASS** `gsm8k_train_00830_note_exact_match` — "Exact expected note comparison"
- **PASS** `00713_old_contradiction_absent` — "Old contradictory phrase must be absent"
- **PASS** `00830_old_contradiction_absent` — "Old contradictory phrase must be absent"
- **PASS** `00830_subtraction_label_present` — "Note explicitly explains subtraction"
- **PASS** `ledger_has_63_rows` — 63
- **PASS** `ledger_notes_match_r1` — ["gsm8k_train_00713", "gsm8k_train_00830"]
- **PASS** `r1_manifest_version` — "vNext-candidate-2026-11-16-r1"
- **PASS** `r1_manifest_not_frozen` — "NOT_FROZEN"
- **PASS** `r1_manifest_validation_pass` — "PASS"
- **PASS** `r1_batch_matches_manifest` — {"manifest_hash": "5b655ab6705fa8d6178871d35f30712b90058354a29952b9e51e88e0108c8a9f", "actual_hash": "5b655ab6705fa8d6178871d35f30712b90058354a29952b9e51e88e0108c8a9f"}
- **PASS** `r1_supplement_matches_manifest` — {"manifest_hash": "8c41bc4e5c237a289dfcda92fcc691bf84b0ff5552ea8c8249c3947d3725ae26", "actual_hash": "8c41bc4e5c237a289dfcda92fcc691bf84b0ff5552ea8c8249c3947d3725ae26"}
- **PASS** `final_adjudication_report_has_r1_section` — "Revision r1 section presence"

## Limitation

This audit verifies parent batch and supplement against hashes stored in the parent manifest. It cannot independently prove the parent manifest file itself is unchanged because no pre-build hash of that manifest was recorded.

The revision remains pending user approval. This audit does not freeze or release Gold.
