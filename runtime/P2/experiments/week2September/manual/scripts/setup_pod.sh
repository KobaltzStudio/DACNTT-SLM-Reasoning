#!/usr/bin/env bash
# Prepare a RunPod GPU pod for Task 6 generation (Instruction_task6.md).
# Source it, do not execute it, so the venv and variables stay in the current shell:
#   source scripts/setup_pod.sh
#
# Everything that must survive a pod stop lives on the network volume (/workspace):
#   /workspace/venv   Python venv with vLLM (created once, reused)
#   /workspace/hf     Hugging Face cache (models downloaded once)
#   /workspace/manual project files (rsync from the local repo)
# VLLM_VERSION pins the vLLM release installed into a new venv. 0.32.0 is the version installed on
# 2026-10-21 (torch 2.13.0+cu130, transformers 5.19.0); keep it for every run of the pool (T6-5:
# vLLM reproducibility holds only on the same hardware and vLLM version).

VENV=/workspace/venv
VLLM_VERSION="${VLLM_VERSION:-0.32.0}"

if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv --system-site-packages "$VENV"
    "$VENV/bin/pip" install --upgrade pip
    "$VENV/bin/pip" install "vllm${VLLM_VERSION:+==$VLLM_VERSION}"
fi
source "$VENV/bin/activate"

# Task 7 also trains on the pod (train_round.py) and validates selection logs. An existing venv from Task 6
# may lack these. PEFT_VERSION is the version the local pilot ran with (2026-11-01).
PEFT_VERSION="${PEFT_VERSION:-0.20.0}"
python -c "import peft" 2>/dev/null || pip install "peft==$PEFT_VERSION"
python -c "import jsonschema" 2>/dev/null || pip install jsonschema

export HF_HOME=/workspace/hf
export VLLM_ENABLE_V1_MULTIPROCESSING=0   # deterministic scheduling (vLLM docs, Reproducibility)

python - <<'EOF'
import torch, transformers, vllm
from vllm import LLM, SamplingParams  # lazy import: catches packages missing from the image (e.g. sniffio)
gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
bf16 = bool(gpu) and torch.cuda.is_bf16_supported()
print(f"gpu {gpu} | bf16 {bf16} | vllm {vllm.__version__} | torch {torch.__version__} | transformers {transformers.__version__}")
if not bf16:
    print("STOP: this GPU has no bf16; T6-5 requires L4/A100-class GPUs for vLLM")
EOF
