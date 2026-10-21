#!/bin/bash
# DGX 环境构建：09 long-jump / 05 MotrixLab / 06 desk-climb
set -x
export PATH=/home/nvidia/.local/bin:$PATH
export HF_ENDPOINT=https://hf-mirror.com
UV=/home/nvidia/.local/bin/uv
CR=/home/nvidia/microduck-course-run
CODE=$CR/topic/02-可运行代码
PV=$CR/envs/lightnav/bin/python

echo "=== A: long-jump assets + env (default home) ==="
JUMP_HOME=/home/nvidia/projects/robotics_shared/downloads/microduck-long-jump
mkdir -p "$JUMP_HOME"
cd "$CODE/long-jump-learning" || exit 1
$PV -c "
import sys, os
sys.path.insert(0, '.')
from jump_lesson import prepare_assets, prepare_environment
home = '$JUMP_HOME'
source, model = prepare_assets(home)
print('ASSETS_OK', source, model)
python, result = prepare_environment(source, home)
print('ENV_OK', python)
" 2>&1 | tail -6
echo "JUMP_RC=$?"

echo "=== B: MotrixLab env (Python 3.10 + cuda extra) ==="
cd "$CODE/MotrixLab" || exit 1
$UV python install 3.10 2>&1 | tail -1
$UV sync --all-packages --extra cuda 2>&1 | tail -6
echo "MOTRIX_RC=$?"

echo "=== C: desk-climb env + models ==="
cd "$CODE/microduck-playground-official/experiments/desk-climb/source" || exit 1
$UV sync --frozen 2>&1 | tail -4
$UV run ../training/download_models.py 2>&1 | tail -4
echo "DESKCLIMB_RC=$?"

echo "=== ENV_BUILD_DONE ==="
