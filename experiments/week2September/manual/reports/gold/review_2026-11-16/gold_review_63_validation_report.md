# Gold vNext Candidate Validation — 2026-11-16

- Status: **PASS**
- Candidate status: **VALIDATED_PENDING_USER_APPROVAL**
- Freeze status: **NOT FROZEN**

## Counts

- batch: **100**
- supplement: **85**
- total: **185**
- reviewed_pending: **63**
- user_confirmed_decisions: **22**
- reviewed_no_change: **41**
- capability_changed_records: **17**
- ambiguity_flagged_records: **5**
- human_confirmed_preserved: **22**

## Checks

- **PASS** `batch_count`: 100
- **PASS** `supplement_count`: 85
- **PASS** `gold_total_unique_ids`: 185
- **PASS** `batch_supplement_disjoint`: []
- **PASS** `worklist_63_unique`: {'rows': 63, 'unique': 63}
- **PASS** `queue_185_unique`: {'rows': 185, 'unique': 185}
- **PASS** `human_confirmed_22_unique`: {'rows': 22, 'unique': 22}
- **PASS** `worklist_is_supplement_subset`: []
- **PASS** `pending_and_human_confirmed_disjoint`: []
- **PASS** `all_explicit_decisions_in_worklist`: []
- **PASS** `explicit_decision_count`: 22
- **PASS** `queue_status_distribution`: {'excluded': 100, 'pending': 63, 'confirmed': 22}
- **PASS** `queue_split_distribution`: {'D_pool': 100, 'D_dev': 85}
- **PASS** `batch_matches_D_pool`: {'missing_from_batch': [], 'extra_in_batch': []}
- **PASS** `supplement_matches_D_dev`: {'missing_from_supplement': [], 'extra_in_supplement': []}
- **PASS** `human_confirmed_matches_queue`: {'missing_in_human_file': [], 'extra_in_human_file': []}
- **PASS** `worklist_matches_pending_queue`: {'missing_in_worklist': [], 'extra_in_worklist': []}
- **PASS** `all_pending_ids_in_raw_sources`: []
- **PASS** `raw_question_consistency`: []
- **PASS** `raw_ground_truth_consistency`: []
- **PASS** `v1_annotation_schema`: []
- **PASS** `source_hashes_match_inspection`: []
- **PASS** `no_change_review_count`: 41
- **PASS** `ledger_covers_all_63`: {'rows': 63, 'ids': 63}
- **PASS** `candidate_supplement_count`: 85
- **PASS** `candidate_batch_count`: 100
- **PASS** `candidate_supplement_count`: 85
- **PASS** `candidate_total_unique`: 185
- **PASS** `candidate_batch_inventory_unchanged`: True
- **PASS** `candidate_supplement_inventory_unchanged`: True
- **PASS** `batch_byte_identical`: 5b655ab6705fa8d6178871d35f30712b90058354a29952b9e51e88e0108c8a9f
- **PASS** `only_explicit_decisions_changed`: []
- **PASS** `human_confirmed_22_unchanged`: []
- **PASS** `candidate_schema_and_labels`: []
- **PASS** `ledger_record_count`: 63
- **PASS** `review_decision_partition`: {'user_confirmed': 22, 'no_change': 41}
- **PASS** `candidate_directory_promoted`: C:\KLTN-SLM-Reasoning\experiments\week2September\manual\data\gold_vnext_candidate_2026-11-16
- **PASS** `candidate_files_exist`: batch, supplement, manifest
- **PASS** `source_hashes_unchanged_after_build`: {'batch': '5b655ab6705fa8d6178871d35f30712b90058354a29952b9e51e88e0108c8a9f', 'supplement': 'a8f78e516c0640c1d30e5f64f22241e5a4a79bfc36be168fdf61c54ed4338654', 'gold_manifest': '498707d205252109b7a6e97f848f6bc4204bda6bea64575547e8e012c13d2d04', 'raw_train': '771125f195aa72606ce2844ccbd9826e1f2cc3c0e6d4b882f7f2f5ec20fc1754', 'supplement_raw': '32f464e3db07fbad83928e87048cae73be18ffad1d115dca181dea6741629f0e', 'human_confirmed': 'f9a8d55f5079ec94ad31cb0c933a6a0d00409cce0815e47fbefd80c1354224ab'}

## Source protection

- Gold vFinal source files unchanged.
- Raw source files unchanged.
- Human-confirmed records unchanged.
- Batch 100 copied byte-for-byte.
- No ground-truth or difficulty field was modified.
