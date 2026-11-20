#!/usr/bin/env bash
# 在远端 DGX（Linux）上复现 Metatron 方案的可复现部分：
#   Coding Agent 写 skill 代码 -> MuJoCo 仿真 -> 打分 -> 反馈迭代
# 不依赖 NVIDIA 未公开的 base policy 权重。
#
# 前提：本机脚本目录已同步到 DGX（或把 metatron_trial.py 单独拷过去），
#       且 Ollama 服务在 127.0.0.1:11434 可达（或改 --coder-base）。
#
# 用法：bash run_on_dgx.sh --rounds 5 --task hurdle
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${HERE}/.venv-dgx"
CODER_BASE="${CODER_BASE:-http://127.0.0.1:11434/v1}"
CODER_MODEL="${CODER_MODEL:-qwen2.5-coder:7b}"

echo "[1/4] 环境: $(hostname) | $(python3 --version)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "  (无 NVIDIA GPU，MuJoCo 走 CPU 亦可)"

if [ ! -x "${VENV}/bin/python" ]; then
  echo "[2/4] 建 venv"
  python3 -m venv "${VENV}"
fi
echo "[3/4] 装依赖"
"${VENV}/bin/pip" install -q --disable-pip-version-check mujoco numpy

echo "[4/4] 跑迭代"
"${VENV}/bin/python" "${HERE}/metatron_trial.py" \
  --task hurdle --episodes 3 --tag dgx \
  --coder-base="${CODER_BASE}" --coder-model="${CODER_MODEL}" \
  --coder-key=ollama "$@"

echo "完成。结果: ${HERE}/results_dgx.json"
