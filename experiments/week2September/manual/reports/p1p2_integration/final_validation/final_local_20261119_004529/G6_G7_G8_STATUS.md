# Phase 2 — G6, G7, G8 status

| Gate | Status | Reproduction evidence |
|---|---|---|
| G6 learning dynamics | PARTIAL | 39 valid sidecars, 37 logical groups, 2 alternate provenance records preserved. 63 rows in seed 13 dynamics (nine groups × seven capabilities), shared S0; 85 approved Gold IDs, strict correctness and Wilson 95% intervals. `g6/` contains JSON, CSV, Markdown and the sidecar inventory. Exit 4 denotes incomplete checkpoint coverage. |
| G7 selection | PARTIAL | Nine observations on the pinned 415 D_dev_select IDs. A S1 347/415, B S1 340/415. Shared S0 once, earliest checkpoint for ties in the final policy. Published partial manifest, no winner. Exit 0. |
| G8 figures | PARTIAL | Seven named figures with PNG, CSV and manifest. All 14 output SHA values match the earlier validated set. Missing scopes are recorded. Exit 4 denotes incomplete checkpoint coverage. |

Scope is seed 13. A S2, A S3, B S2 and B S3 are not fully observed. There are no inferred graph edges or D_test metrics. See `analysis_verification.json`, `analysis_exit_codes.json` and each gate log.
