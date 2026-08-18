#!/usr/bin/env bash
set -euo pipefail

ROOT="${HOME}/Desktop/VLA_VLM_Engineering_2026"
UPSTREAMS="${ROOT}/upstreams"
mkdir -p "${UPSTREAMS}"

echo "[1/4] Installing base tools (git/python venv only if apt exists)"
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y git python3 python3-venv python3-pip build-essential
fi

clone_if_missing() {
  local url="$1"; local dir="$2"; shift 2
  if [ -d "${UPSTREAMS}/${dir}/.git" ]; then
    echo "[skip] ${dir} already exists"
  else
    git clone --depth 1 "$@" "$url" "${UPSTREAMS}/${dir}"
  fi
}

cd "${UPSTREAMS}"
clone_if_missing https://github.com/lemonbaby2/-123.git lizipeng-embodied-ai-portfolio
clone_if_missing https://github.com/huggingface/lerobot.git lerobot
clone_if_missing https://github.com/SpatialVLA/SpatialVLA.git SpatialVLA
clone_if_missing https://github.com/SpatialVLA/SpatialVLA.git SpatialVLA-lerobot -b lerobot
clone_if_missing https://github.com/GigaAI-research/SwiftVLA.git SwiftVLA
clone_if_missing https://github.com/starVLA/starVLA.git StarVLA-stable -b starVLA
clone_if_missing https://github.com/QwenLM/Qwen3-VL.git Qwen3-VL
clone_if_missing https://github.com/IDEA-Research/Grounded-SAM-2.git Grounded-SAM-2
clone_if_missing https://github.com/facebookresearch/sam2.git sam2
clone_if_missing https://github.com/wzzheng/StreamVGGT.git StreamVGGT
clone_if_missing https://github.com/openvla/openvla.git openvla
clone_if_missing https://github.com/moojink/openvla-oft.git openvla-oft
clone_if_missing https://github.com/Physical-Intelligence/openpi.git openpi
clone_if_missing https://github.com/NVIDIA/Isaac-GR00T.git Isaac-GR00T

echo "[2/4] Creating a lightweight Python venv for local calibration demos"
python3 -m venv "${ROOT}/.venv"
"${ROOT}/.venv/bin/python" -m pip install --upgrade pip
"${ROOT}/.venv/bin/pip" install numpy opencv-python pyyaml matplotlib

echo "[3/4] Copying this engineering package next to upstreams"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "${SCRIPT_DIR}" != "${ROOT}/package" ]; then
  mkdir -p "${ROOT}/package"
  cp -a "${SCRIPT_DIR}/." "${ROOT}/package/"
fi

echo "[4/4] Done"
echo "Workspace: ${ROOT}"
echo "Activate: source ${ROOT}/.venv/bin/activate"
if command -v code >/dev/null 2>&1; then
  code "${ROOT}" || true
else
  echo "VSCode CLI 'code' not found; open ${ROOT} manually in VSCode."
fi
