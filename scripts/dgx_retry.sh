#!/bin/bash
# 重试：MotrixLab（跳过 triton）+ 09 jump 资产（429 退避）
set -x
export PATH=/home/nvidia/.local/bin:$PATH
export HF_ENDPOINT=https://hf-mirror.com
UV=/home/nvidia/.local/bin/uv
CR=/home/nvidia/microduck-course-run

echo "=== MotrixLab sync (no triton) ==="
cd "$CR/topic/02-可运行代码/MotrixLab" || exit 1
$UV sync --all-packages --extra cuda --no-install-package triton 2>&1 | tail -4
$CR/topic/02-可运行代码/MotrixLab/.venv/bin/python -c "import torch; print('MOTRIX_TORCH_OK', torch.__version__, torch.cuda.is_available())" 2>&1 | tail -2

echo "=== wait 120s for hf-mirror 429 cooldown ==="
sleep 120

echo "=== jump prep retry ==="
$CR/envs/lightnav/bin/python /home/nvidia/jump_prep.py 2>&1 | tail -6
echo "RETRY_DONE"
