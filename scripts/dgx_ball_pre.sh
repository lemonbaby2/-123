#!/bin/bash
# 等待 MotrixLab 环境就绪后跑 05 预训练（scratch smoke + ONNX 导出 + 落位 converted/）
set -x
CR=/home/nvidia/microduck-course-run
MP=$CR/topic/02-可运行代码/MotrixLab/.venv/bin/python
for i in $(seq 1 60); do
  if [ -x "$MP" ] && "$MP" -c "import torch" 2>/dev/null; then
    echo "MOTRIX_ENV_READY"
    break
  fi
  echo "waiting for motrix env ($i)..."
  sleep 30
done
"$MP" -c "import torch" 2>/dev/null || { echo "MOTRIX_ENV_TIMEOUT"; exit 1; }
MUJOCO_GL=egl OMP_NUM_THREADS=4 "$MP" /home/nvidia/ball_pre.py
