#!/bin/bash
# 08 LightNav 环境构建：模型服务环境（vllm）+ notebook 内核依赖
set -x
export PATH=/home/nvidia/.local/bin:$PATH
UV=/home/nvidia/.local/bin/uv
CR=/home/nvidia/microduck-course-run
L=/home/nvidia/LightNav-0

echo "=== [1/3] lightnav-0 model env (py3.11 + vllm) ==="
$UV venv --python 3.11 "$CR/envs/lightnav-0" 2>&1 | tail -2
$UV pip install --python "$CR/envs/lightnav-0/bin/python" -e "$L[vllm,video]" 2>&1 | tail -4
echo "MODEL_ENV_RC=$?"

echo "=== [2/3] notebook venv: vln-mujoco + media deps ==="
$UV pip install --python "$CR/envs/notebook/bin/python" \
  -e "$L/mujoco_demo[microduck]" \
  imageio imageio-ffmpeg websocket-client aiohttp 2>&1 | tail -4
echo "NOTEBOOK_ENV_RC=$?"

echo "=== [3/3] verify imports ==="
"$CR/envs/notebook/bin/python" -c "
import vln_mujoco, mujoco, numpy, imageio
from vln_mujoco.robots import microduck
print('VLN_IMPORTS_OK', vln_mujoco.__file__)
" 2>&1 | tail -3
echo "=== LIGHTNAV_ENV_DONE ==="
