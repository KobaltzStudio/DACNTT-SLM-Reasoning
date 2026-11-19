#!/usr/bin/env bash
# B5, kiểm tra GPU/BF16 — chỉ chạy sau khi CPU receipt đã được chấp nhận.
source /workspace/env.sh
export GPU_PREFLIGHT_APPROVED=BF16-CHECK
test "${GPU_PREFLIGHT_APPROVED:-}" = BF16-CHECK &&
  nvidia-smi &&
  "$P1P2_PYTHON" -B -c 'import torch; assert torch.cuda.is_available() and torch.cuda.is_bf16_supported(); print(torch.version.cuda, torch.cuda.get_device_name(0))'
