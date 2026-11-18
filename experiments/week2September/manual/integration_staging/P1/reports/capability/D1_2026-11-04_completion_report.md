# D1 Completion Report — 2026-11-04
## Dynamic Learnability-aware CoT Knowledge Distillation

**Task:** D1 — Capability Artifact Audit and Split Integrity Verification  
**Date:** 04 November 2026  
**Project:** Dynamic Learnability-aware CoT Knowledge Distillation

---

## 1. Objective

The objective of D1 was to audit the finalized Gold v2 capability annotation artifacts, verify their integrity and consistency, confirm the assignment of Gold problems to the frozen dataset splits, and produce a reproducible audit report.

The audit focused on:

1. Validating the structure and quality of Gold v2 annotations.
2. Checking problem ID uniqueness across annotation sources.
3. Verifying Gold-to-split assignments against the frozen split manifest.
4. Validating source and split file integrity using SHA256.
5. Re-running relevant annotation, capability extraction, capability rules, and manual adjudication tests.
6. Consolidating the results into a completion report.

## 2. Gold v2 Artifact Inventory

Two finalized Gold v2 annotation files were audited:

| Source | File | Records |
|---|---|---:|
| Batch 100 | `data/batch_100/batch_100_annotations_v2.jsonl` | 100 |
| Supplement | `data/supplement/supplement_annotations_v2.jsonl` | 85 |
| **Total** | | **185** |

### 2.1. Data Quality Validation

The audit identified:

| Quality check | Result |
|---|---:|
| Total Gold records | 185 |
| Unique Gold problem IDs | 185 |
| Cross-source duplicate IDs | 0 |
| Missing problem IDs | 0 |
| Missing capability labels | 0 |
| Invalid capability labels | 0 |
| Duplicate capability labels | 0 |

**Result:** All 185 Gold records passed the artifact quality checks.

### 2.2. Capability Support

The following table reports the number of Gold problems associated with each capability. A problem may have multiple capability labels; therefore, these counts are not mutually exclusive.

| Capability | Batch 100 | Supplement | Combined |
|---|---:|---:|---:|
| addition | 51 | 27 | 78 |
| subtraction | 51 | 55 | 106 |
| multiplication | 71 | 84 | 155 |
| division | 42 | 47 | 89 |
| percentage | 12 | 29 | 41 |
| fraction | 18 | 31 | 49 |
| ratio | 0 | 30 | 30 |

The capability support statistics were generated in:

- `reports/capability/d1_audit_v2/source_capability_support.csv`

## 3. Gold-to-Split Assignment Verification

The Gold v2 problem IDs were compared against the frozen split files and the split design recorded in `splits/split_manifest.json`.

### 3.1. Gold-to-Split Mapping

| Gold source | Target split | Gold records | Overlap | Gold IDs outside target split |
|---|---|---:|---:|---:|
| batch_100 | D_pool | 100 | 100 | 0 |
| batch_100 | D_dev | 100 | 0 | 100 |
| batch_100 | D_test | 100 | 0 | 100 |
| supplement | D_pool | 85 | 0 | 85 |
| supplement | D_dev | 85 | 85 | 0 |
| supplement | D_test | 85 | 0 | 85 |

The mapping is consistent with the frozen split design:

- All 100 `batch_100` Gold problems belong to `D_pool`.
- All 85 supplement Gold problems belong to `D_dev`.
- No Gold problem belongs to `D_test`.

### 3.2. Split Coverage

| Split | Total problems | Gold overlap | Gold coverage |
|---|---:|---:|---:|
| D_pool | 6,968 | 100 | 1.44% |
| D_dev | 500 | 85 | 17.00% |
| D_test | 1,319 | 0 | 0.00% |

The 17% Gold coverage in D_dev is consistent with the current dataset construction: 85 supplement problems are annotated, while the remaining 415 D_dev problems are randomly selected training problems.

The absence of Gold annotations in D_test is intentional and preserves the separation between annotated development data and the official test set.

**Result:** Gold-to-split assignments match the frozen split manifest.

## 4. Split Integrity Verification

### 4.1. SHA256 Cross-platform Normalization

The initial execution of `scripts/validate_splits.py` reported eight SHA256 mismatches across source and split files.

Investigation identified the cause as line-ending differences between Windows CRLF files and the LF-normalized content represented by the hashes in `split_manifest.json`.

The `sha256_file()` function in `scripts/create_splits.py` was updated to normalize CRLF and CR line endings to LF before computing SHA256.

This change ensures consistent hash verification across Windows and Unix-like environments.

The original split files, problem assignments, random seed, and split manifest were preserved. No split regeneration was performed.

After the update, all eight hash checks passed.

### 4.2. Split Validation Results

The final execution of `scripts/validate_splits.py` passed all 30 checks.

| Validation category | Checks | Result |
|---|---:|---|
| Source SHA256 | 4 | PASS |
| Split SHA256 | 4 | PASS |
| ID sorting, uniqueness, and empty-line checks | 9 | PASS |
| Pairwise split disjointness | 3 | PASS |
| Source membership and test-set consistency | 2 | PASS |
| Near-duplicate exclusion and train partition | 2 | PASS |
| batch_100 and supplement membership | 2 | PASS |
| Expected split counts | 4 | PASS |
| **Total** | **30** | **30/30 PASS** |

Verified split counts:

| Dataset component | Count |
|---|---:|
| D_pool | 6,968 |
| D_dev | 500 |
| D_test | 1,319 |
| Near-duplicates removed | 5 |
| batch_100 in D_pool | 100 |
| Supplement in D_dev | 85 |

The validator also confirmed that no D_pool question shares a lowercase word 13-gram with any D_dev or D_test question.

**Result:** All split integrity checks passed.

## 5. Regression Tests

The following regression tests were executed successfully.

| Test | Result |
|---|---|
| Validate `batch_100_annotations_v2.jsonl` | 100 records — PASS |
| Validate `supplement_annotations_v2.jsonl` | 85 records — PASS |
| Capability extractor unit tests | 28 cases — PASS |
| Capability rules v2 unit tests | 44 cases — PASS |
| Manual adjudication validation | 34 rows — PASS |

### 5.1. Manual Adjudication Summary

The manual adjudication dataset contains 34 reviewed rows.

| Category | Count |
|---|---:|
| FALSE_LEXICAL_TRIGGER | 31 |
| DEFINITION_AMBIGUITY | 3 |
| PROPOSE_RULE_CHANGE | 27 |
| KEEP_GOLD | 7 |

The validation confirmed the expected row count, review status, adjudication categories, and decisions.

**Result:** All relevant regression tests passed.

## 6. Ambiguous Case Audit Reference

The existing Task 3 ambiguous case audit was checked as supporting evidence for the finalized annotation decisions.

Source file:

`reports/ambiguous_case_audit_report.json`

Audit results:

| Metric | Result |
|---|---:|
| Total cases | 5 |
| Resolved cases | 5 |
| Open cases | 0 |
| Ground-truth inconsistencies | 1 |
| Annotation revisions | 0 |
| Annotations retained | 5 |
| Guideline revisions required | 0 |
| Status | PASS |

The five audited problems were:

- `gsm8k_train_00023`
- `gsm8k_train_00029`
- `gsm8k_train_00056`
- `gsm8k_train_00073`
- `gsm8k_train_00082`

All five annotations were retained.

Problem `gsm8k_train_00056` was flagged for ground-truth inconsistency. The original annotation was retained rather than automatically changing the label or excluding the problem.

No unresolved ambiguous cases remained in this audit.

## 7. Remaining Limitation: A2 Annotation Independence

The independence of annotator A2 has not yet been confirmed.

The existing 30-problem A1/A2 pilot agreement report indicates:

- Cohen's kappa is 1.0 for the six non-ratio capabilities.
- Ratio kappa is null because both annotators have zero positive examples for this capability.

However, the independence of A2's annotation process remains unresolved. Therefore, the current agreement statistics should not be treated as reliable evidence of inter-annotator reliability until annotation independence is confirmed.

Required follow-up:

1. Confirm whether A2 annotated the pilot problems independently and without access to A1's labels.
2. If independence cannot be established, arrange for another annotator to perform blind re-annotation of the 30 pilot problems.
3. Recalculate agreement statistics after obtaining valid independent annotations.

This limitation is separate from the completed Gold artifact and split integrity audit.

## 8. Generated and Updated Artifacts

### 8.1. Updated Script

- `scripts/create_splits.py`
  - Updated `sha256_file()` to normalize line endings before computing SHA256.

### 8.2. Audit Script

- `scripts/audit_capability_artifacts_v2.py`
  - Audits Gold v2 records, capability labels, problem IDs, and Gold-to-split intersections.

### 8.3. Audit Outputs

Directory: `reports/capability/d1_audit_v2/`

- `capability_artifact_audit.json`
- `capability_artifact_audit.md`
- `gold_record_inventory.csv`
- `source_capability_support.csv`
- `split_capability_support.csv`
- `gold_source_split_intersections.csv`

### 8.4. Supporting Existing Artifacts

- `reports/ambiguous_case_audit_report.json`
- `config/guideline_v3.md`
- `config/capability_rules_v2.json`
- `reports/error_analysis/manual_adjudication.csv`
- `splits/split_manifest.json`

The supporting artifacts were retained as evidence for the audit and its decisions.

## 9. Final Conclusion

The D1 capability artifact audit and split integrity verification have been completed successfully.

The audit validated 185 unique Gold v2 records without schema quality issues or cross-source duplicate IDs. Gold-to-split assignments were verified against the frozen split manifest: all 100 `batch_100` problems belong to `D_pool`, all 85 supplement problems belong to `D_dev`, and no Gold problem belongs to `D_test`.

The split integrity validator passed all 30 checks after implementing cross-platform line-ending normalization for SHA256 computation. Annotation validation, capability extractor tests, capability rules v2 tests, and manual adjudication validation also passed.

The existing ambiguous case audit contains five resolved cases and no open cases. One ground-truth inconsistency was explicitly flagged without forcing an annotation change.

**D1 status: COMPLETED — capability artifact audit, Gold-to-split verification, and technical validation.**

**Outstanding limitation: A2 annotation independence remains unresolved and requires separate follow-up.**