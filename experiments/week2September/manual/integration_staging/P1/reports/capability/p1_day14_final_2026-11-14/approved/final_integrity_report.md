# Final integrity check — 14/11/2026

**Result: PASS WITH SCOPE LIMITATION**

## Verified

- 170 extractor-error rows; 170 unique problem IDs; 0 duplicates.
- All required review fields are populated.
- 85 Gold supplement rows; 85 unique problem IDs; 0 duplicates.
- All 85 Gold supplement rows have explicit user approval status.
- All uploaded ZIP archives pass ZIP CRC validation (`testzip` returns no corrupt member).
- SHA-256 hashes and file sizes are recorded in `final_integrity_report.json`.
- No source mutation was performed by the review workflow.

## Preserved artifacts

No changes were made to raw GSM8K, Gold vFinal source, Guideline v3, extractor rules, historical D3 regression outputs, training artifacts, or RunPod artifacts.

## Scope limitation

The local repository `C:\KLTN-SLM-Reasoning` was not mounted in this session. Therefore this check validates the uploaded archives and generated review outputs, but does not constitute a full hash comparison against every file on the user's local disk. Run the local PowerShell checks before considering repository-level integrity fully verified.

## User-provided clarification: gsm8k_train_00830

The user confirmed the Hilary prompt/solution trace and explicitly instructed not to replace it with the Janet scenario. The existing Gold labels are retained. The user-provided reasoning trace calculates $6 + $12 = $18, a 25% tip of $4.50, then $25 - $22.50 = $2.50. This source assumption is preserved as provided; the workflow does not independently resolve how tax is represented.
