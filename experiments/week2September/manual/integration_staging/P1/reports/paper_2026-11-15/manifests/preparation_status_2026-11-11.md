# Experiment Preparation Status

Date: 2026-11-11
Project: Dynamic Learnability-aware CoT Knowledge Distillation

## Environment
- Python: 3.11.9
- PyTorch: 2.13.0+cu126
- CUDA: 12.6
- Local GPU: NVIDIA GeForce RTX 4060 Laptop GPU
- BF16: Supported
- Transformers: 5.15.0
- PEFT: 0.20.0
- Official training environment: Cloud GPU
- Cloud environment: Not yet verified

## Dataset
- Verified trajectories: 4353
- D_pool: 6968
- D_dev: 500
- D_test: 1319
- Split validation: PASS

## Frozen configuration
- Config validation: PASS
- Config SHA256: 17CF4B837DC42AC5145AEA762847CA5DFBA4BAE58D253560B3B0DD6A254B73C5
- Split manifest SHA256: 85F4559246542D197C427318AFB3EEFB8B8492573B69AC23E691FC19CE93BBDA
- Verified pool SHA256: 95F34CFF848BFBD16305E5F0ECC2656525DC1E319CA2B1A404F9B75C8029CD04

## Preparation completed
- Experiment directories created.
- Required scripts found.
- CLI reference captured.
- Frozen config validation passed.
- Split validation passed.
- Local environment recorded.

## Pending
- Verify B0 implementation and definition.
- Verify B2/B3/B4/B5 implementations against protocol.
- Verify B5 full-pool scoring schedule.
- Resolve L_proxy edge cases.
- Verify supervised-token accounting.
- Implement and run L_emp probe (b=7).
- Verify Cloud GPU environment.
- Obtain project-team protocol confirmation.

## Authorization
Official training: NOT AUTHORIZED.
Reason: Protocol review and Cloud GPU verification are incomplete.
