#!/usr/bin/env bash
# Sau khi Stop/Start pod: cài lại tmux + uv + đúng bản Python của venv (venv và cache vẫn ở /workspace).
#   bash /workspace/runpod_ops/11_restore_env.sh
source /workspace/env.sh
set -euo pipefail
command -v tmux >/dev/null || { apt-get update -qq && apt-get install -y -qq tmux; }
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
cfg="$P1P2_VOLUME/intake/venv/pyvenv.cfg"
ver=$(awk -F' = ' '/^version_info|^version /{print $2; exit}' "$cfg"); ver=${ver%.final*}
echo "venv cần Python $ver"
"$P1P2_PYTHON" -V 2>/dev/null || uv python install "$ver"
"$P1P2_PYTHON" -V
"$P1P2_PYTHON" -m pip check
"$P1P2_PYTHON" -B -c 'import torch, transformers, peft; print(torch.__version__, transformers.__version__, peft.__version__, torch.cuda.is_available())'
(cd "$HF_HUB_CACHE" && ls) && echo "ENV RESTORE PASS"
