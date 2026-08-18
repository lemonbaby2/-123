#!/usr/bin/env bash
set -euo pipefail
mkdir -p upstreams
if [ ! -d upstreams/lerobot/.git ]; then git clone --depth 1 https://github.com/huggingface/lerobot.git upstreams/lerobot; fi
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e 'upstreams/lerobot[smolvla,feetech]'
pip install numpy opencv-python pyyaml matplotlib
cat <<'EOF'
Installed LeRobot + SmolVLA dependencies.
Before real robot use: identify ports, configure motor IDs/baudrates, run lerobot-calibrate, verify E-stop and joint limits.
EOF
