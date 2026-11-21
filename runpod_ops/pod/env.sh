# source /workspace/env.sh  — chạy lại mỗi lần SSH vào hoặc mở cửa sổ tmux mới.
# Biến lấy từ B4 của docs/RUNPOD_EXECUTION_GUIDE.md, volume cố định là /workspace.
export P1P2_VOLUME=/workspace
export SOURCE="$P1P2_VOLUME/intake/source"
export P1P2_PACKAGE="$P1P2_VOLUME/intake/runtime"
export WORK="$P1P2_VOLUME/intake/work"
export LOG_ROOT="$P1P2_VOLUME/intake/logs"
export MANUAL="$WORK/P2/experiments/week2September/manual"
export HF_HOME="$P1P2_VOLUME/intake/hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export HF_HUB_CACHE="$HF_HOME/hub"
export P1P2_PYTHON="$P1P2_VOLUME/intake/venv/bin/python"
export WHEELHOUSE="$P1P2_VOLUME/wheelhouse"
export RECEIPT="$LOG_ROOT/cpu-preflight/preflight.json"
export RETURN_ROOT="$P1P2_VOLUME/intake/returns"
export PATH="$HOME/.local/bin:$PATH"
