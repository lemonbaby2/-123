#!/usr/bin/env bash
set -euo pipefail
mkdir -p upstreams
clone(){ local url="$1" dir="$2"; shift 2; [ -d "upstreams/${dir}/.git" ] || git clone --depth 1 "$@" "$url" "upstreams/${dir}"; }
clone https://github.com/QwenLM/Qwen3-VL.git Qwen3-VL
clone https://github.com/IDEA-Research/Grounded-SAM-2.git Grounded-SAM-2
clone https://github.com/facebookresearch/sam2.git sam2
clone https://github.com/SpatialVLA/SpatialVLA.git SpatialVLA
clone https://github.com/SpatialVLA/SpatialVLA.git SpatialVLA-lerobot -b lerobot
clone https://github.com/starVLA/starVLA.git StarVLA-stable -b starVLA
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install numpy opencv-python pyyaml matplotlib
cat <<'EOF'
Core repos cloned. Install each large model using its own pinned environment/README.
Do not mix every VLA/VLM dependency into one Python environment in production.
EOF
