# Dependency closure — Phase A

**Windows dependency audit PASS.** Validated all 658 regular package files (655 payload and three indices), 575,403,394 bytes. JSON, CSV and SHA indices agree, every payload SHA and size matches its source or generated source report, and the two trusted manifest hashes match. No traversal, duplicate paths, case collisions, symlink or reparse points. Ten groups contain identical bytes at different expected paths. They represent distinct logical inputs or evidence roles and were retained.

| Dependency | Classification | Evidence / deployment |
|---|---|---|
| Unified runner, selector, train, evaluator, NLL, hook, G6–G8 and final D_test source/tests | INCLUDED_IN_PACKAGE | AST closure in integrity_observation.json and plan/test logs. |
| Experiment and registry config, frozen pool/token counts, Gold, split and historical lineage | INCLUDED_IN_PACKAGE | Verified by SHA, source equivalence and mapped CPU plans. |
| A S1, A S2, B S1 adapters/configs and train logs; A S2 partial prefix | INCLUDED_IN_PACKAGE | Verified adapter lineage and source/target hashes. B future S2/S3 are outputs. |
| Shared S0 and checkpoint-specific NLL | INCLUDED_IN_PACKAGE / future outputs | S0 reference, archived S0 NLL and summary included. B S2/S3 require fresh NLL on respective parent adapters. |
| Base Student model revision, config, generation config, tokenizer/config, merges, vocab and weights | SEPARATE_TRANSFER_REQUIRED | Seven pinned cache files, 3,098,955,668 bytes and individual SHA. Weights SHA matches the trusted previous audit. Transfer these files only. |
| HF hub cache path, Python, torch CUDA build, Transformers, PEFT, Accelerate, Tokenizers, Safetensors, YAML, Matplotlib | PROVIDED_BY_LINUX_ENVIRONMENT | Version contract and offline verification commands in LINUX_ENVIRONMENT_CONTRACT.md. |
| Teacher model/cache | OPTIONAL | The frozen Teacher trajectory pool is included; the Teacher generator source is used to verify the prompt template. No Teacher model is loaded in the supported Run A/B workflow. |
| vLLM, datasets and bitsandbytes | OPTIONAL for this execution scope | Supported deployment uses HF BF16/LoRA; preserve the dependency lock. This audit does not qualify optional backends or quantized paths. |
| Unresolved local runtime dependencies | No MISSING_BLOCKER observed | Linux package availability, transfer and live environment validation remain pending. |

Verified 226 recorded locator occurrences, including 26 runtime references. All runtime and analysis targets are present in the package. 132 locator occurrences refer to local archived provenance objects intentionally outside the release, including old G5.9 train-set lineage. They still exist at source and are not executable dependencies of the unified workflow. Historical runners and archived paths remain historical scope.

Pinned snapshot root is recorded in MODEL_CACHE_TRANSFER_MANIFEST.csv. The Windows HF cache resolver found each expected file at the exact revision. The safetensors header has 338 entries and expected data extent. Only bytes, metadata and SHA were inspected; no model was loaded, downloaded, copied or uploaded. SHA of MODEL_CACHE_SHA256SUMS.txt is `97b5db3ae70d9a73a0961c2c56424eff49cb8da9324d455356c8c049adb31630`.
