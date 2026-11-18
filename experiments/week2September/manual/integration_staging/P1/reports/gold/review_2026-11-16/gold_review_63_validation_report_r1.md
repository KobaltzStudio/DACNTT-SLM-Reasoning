# Gold vNext Candidate Revision r1 Validation

- Status: **PASS**
- Candidate status: **VALIDATED_PENDING_USER_APPROVAL**
- Freeze status: **NOT FROZEN**
- Batch records: **100**
- Supplement records: **85**
- Total records: **185**
- Revised notes: **2**
- Ledger rows: **63**

## Revised records

- `gsm8k_train_00713`: replaced contradictory note; retained 15% with explicit vaccine-scope and disjoint-group assumptions.
- `gsm8k_train_00830`: replaced contradictory note; added subtraction and retained raw ground truth 25 separately from the alternate variant's $2.50 target.

## Checks

- **PASS** `batch_count_100`: 100
- **PASS** `supplement_count_85`: 85
- **PASS** `total_unique_185`: 185
- **PASS** `batch_byte_identical_to_parent`: 5b655ab6705fa8d6178871d35f30712b90058354a29952b9e51e88e0108c8a9f
- **PASS** `only_two_notes_changed`: ['gsm8k_train_00713', 'gsm8k_train_00830']
- **PASS** `target_notes_replaced`: ['gsm8k_train_00713', 'gsm8k_train_00830']
- **PASS** `ledger_63_rows`: 63
- **PASS** `ledger_notes_match_candidate`: ['gsm8k_train_00713', 'gsm8k_train_00830']
- **PASS** `source_candidate_unchanged`: Original candidate files were read and not written.

## Source protection

- Parent candidate retained unchanged.
- Gold vFinal not modified.
- Raw ground truth not modified.
- Batch copied byte-for-byte from parent candidate.
- Only the two specified supplement notes were revised.
- Freeze status remains NOT FROZEN.
