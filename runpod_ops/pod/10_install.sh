#!/usr/bin/env bash
# Bước cài môi trường trên pod (thay cho khối B4 dòng 82-109).
# Khác hướng dẫn gốc: source rsync từ github/ thay vì git clone; Python 3.11 cài bằng uv;
# wheelhouse và Student cache tải ngay trên pod rồi kiểm SHA.
source /workspace/env.sh
set -euo pipefail
REV=989aa7980e4cf806f80c7fef2b1adb7bc71aa306
test -f "$SOURCE/manifests/GITHUB_RELEASE_MANIFEST.json"
test -f "$P1P2_PACKAGE/manifests/SHA256SUMS.txt"
test ! -e "$WORK" && test ! -e "$P1P2_VOLUME/intake/venv"
echo "== Source: $(find "$SOURCE" -type f | wc -l) file (phải là 63)"
sha256sum "$SOURCE/manifests/GITHUB_RELEASE_MANIFEST.json" | tee "$LOG_ROOT/source_manifest_sha.txt"

echo "== tmux"
command -v tmux >/dev/null || { apt-get update -qq && apt-get install -y -qq tmux; }

echo "== uv + Python 3.11 venv"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.11
uv venv --seed --python 3.11 "$P1P2_VOLUME/intake/venv"
"$P1P2_PYTHON" --version

echo "== Wheelhouse (tải từ index trong requirements-lock.txt)"
mkdir -p "$WHEELHOUSE"
"$P1P2_PYTHON" -m pip download -q -d "$WHEELHOUSE" -r "$SOURCE/P2/requirements-lock.txt"

echo "== Cài offline từ wheelhouse (giống B4)"
"$P1P2_PYTHON" -m pip install --no-index --find-links "$WHEELHOUSE" \
  -r "$SOURCE/P2/requirements-lock.txt"
"$P1P2_PYTHON" -m pip check

echo "== Tải 7 file Student cache đúng revision"
files=$(cut -c67- "$SOURCE/manifests/MODEL_CACHE_SHA256SUMS.txt" | sed "s#^.*/snapshots/$REV/##")
HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 "$P1P2_VOLUME/intake/venv/bin/hf" download \
  Qwen/Qwen2.5-1.5B-Instruct --revision "$REV" $files
( cd "$HF_HUB_CACHE" && sha256sum -c "$SOURCE/manifests/MODEL_CACHE_SHA256SUMS.txt" )
echo "INSTALL DONE"
