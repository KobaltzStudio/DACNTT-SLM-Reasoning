# Linux environment contract — Phase C

**Contract documented and Bash syntax checked. Target host validation PENDING.** Use Python 3.11 x86_64 and the delivered `P2/requirements-lock.txt` with an approved wheelhouse/image. Verify target wheel availability and installation with `python -m pip check` before attempting runtime. The following runtime versions are verified in the Windows environment and pinned in the lock; Linux wheel and driver compatibility are unverified at this stage.

| Dependency | Required version / scope |
|---|---|
| Python | 3.11 series, Windows reference 3.11.9 |
| PyTorch | 2.13.0+cu126, wheel CUDA runtime 12.6 |
| Transformers / PEFT / Accelerate | 5.15.0 / 0.20.0 / 1.14.0 |
| Tokenizers / Hugging Face Hub / Safetensors | 0.22.2 / 1.27.0 / 0.8.0 |
| PyYAML / Matplotlib | 6.0.3 / 3.11.2 |
| Datasets / bitsandbytes | Lock pins 5.0.1 / 0.50.2. No direct dependency in the supported HF BF16 LoRA paths. bitsandbytes is absent from the Windows environment used for this audit. |
| CUDA runtime | cu126 PyTorch with a compatible Linux driver and BF16 GPU. Use the pinned platform-specific dependencies in the lock, not Windows wheels. |

Use `HF_HOME` on persistent storage, `HF_HUB_CACHE="$HF_HOME/hub"`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and mask GPU during CPU acceptance with `CUDA_VISIBLE_DEVICES=''`. The exact offline Student revision and all seven required files are in MODEL_CACHE_TRANSFER_MANIFEST.csv. Copy only those when approved and verify file bytes and offline resolver from the Linux cache root. No Teacher weights are required for the verified-pool workflow. Prefer Bash, GNU coreutils (`sha256sum`, `cmp`, `wc`, `cut`, `cp`, `df`), awk, rsync and SSH on the approved endpoint.

The sealed package plus one byte-preserving operational copy and the Student snapshot require about **4.25 GB** before wheelhouse, logs, NLL files, adapters and outputs. Measure free disk on the actual persistent volume and leave room for outputs. The prior Windows A S1 measurement was about 7.52 GiB reserved; keep margin (e.g., a 16 GiB BF16-capable device). This is a planning estimate. Record target GPU and driver after authorization. Test volume atomic rename, exclusive directory creation and hardlinks using Temp fixtures; restrict permissions to a writable working tree and keep a separately verifiable sealed source. Do not install or upgrade packages in the Windows audit.

Run syntax-checked commands in RUNPOD_DEPLOYMENT_COMMANDS.md. CPU acceptance precedes any GPU preflight or live checkpoint command.
