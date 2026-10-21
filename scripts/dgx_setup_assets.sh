#!/bin/bash
# DGX 资产总装：克隆仓库 + hf-mirror 下载模型（mirror 绕行 + HF 镜像）
set -x
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
export HF_ENDPOINT=https://hf-mirror.com
export HOME=/home/nvidia
export PATH=/home/nvidia/.local/bin:$PATH
UV=/home/nvidia/.local/bin/uv
CR=/home/nvidia/microduck-course-run
CODE=$CR/topic/02-可运行代码
LOG=$CR/setup_assets.log

echo "=== [1/5] clone Vottivott/microduck-playground (official) ==="
cd "$CODE" || exit 1
rm -rf microduck-playground-official
git clone --depth 1 https://github.com/Vottivott/microduck-playground.git microduck-playground-official 2>&1 | tail -2
echo "OFFICIAL_CLONE_RC=$?"

echo "=== [2/5] clone Motphys/MotrixLab (ball_balance, shallow no-lfs) ==="
cd "$CODE" || exit 1
rm -rf MotrixLab
GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 https://github.com/Motphys/MotrixLab.git MotrixLab 2>&1 | tail -2
echo "MOTRIX_CLONE_RC=$?"

echo "=== [3/5] clone lightorigins/LightNav-0 + pollen-robotics/microduck_rl ==="
mkdir -p /home/nvidia/projects /home/nvidia/workspaces
cd /home/nvidia/projects || exit 1
rm -rf LightNav-0
git clone --depth 1 https://github.com/lightorigins/LightNav-0.git LightNav-0 2>&1 | tail -2
echo "LIGHTNAV_CLONE_RC=$?"
cd /home/nvidia/workspaces || exit 1
rm -rf microduck_rl
git clone --depth 1 https://github.com/pollen-robotics/microduck_rl.git microduck_rl 2>&1 | tail -2
echo "MICRODUCK_RL_CLONE_RC=$?"

echo "=== [4/5] HF downloads via hf-mirror ==="
mkdir -p "$CR/artifacts" "$CR/checkpoints"
# 4a. basketball pack (checkpoint.pt + policy.onnx)
$UV pip install --python /home/nvidia/microduck-course-run/envs/lightnav/bin/python huggingface_hub 2>&1 | tail -1
PV=/home/nvidia/microduck-course-run/envs/lightnav/bin/python
HF_ENDPOINT=https://hf-mirror.com $PV -c "
from huggingface_hub import snapshot_download
p = snapshot_download('HannesVonEssen/microduck-basketball', local_dir='$CR/artifacts/basketball')
print('BASKETBALL_OK', p)
" 2>&1 | tail -3
# 4b. LightNav-0 (9.6GB)
HF_ENDPOINT=https://hf-mirror.com $PV -c "
from huggingface_hub import snapshot_download
p = snapshot_download('LightOriginsHQ/LightNav-0', local_dir='$CR/checkpoints/LightNav-0')
print('LIGHTNAV_MODEL_OK', p)
" 2>&1 | tail -3
# 4c. alpha_walking.onnx from microduck-policies
mkdir -p "$CR/checkpoints/microduck-navigation"
curl -fsSL -m 300 -o "$CR/checkpoints/microduck-navigation/alpha_walking.onnx" \
  "https://hf-mirror.com/pollen-robotics/microduck-policies/resolve/main/alpha_walking.onnx" 2>&1 | tail -1
ls -la "$CR/checkpoints/microduck-navigation/" 2>&1

echo "=== [5/5] verify ==="
ls -d "$CODE/microduck-playground-official" "$CODE/MotrixLab" /home/nvidia/projects/LightNav-0 /home/nvidia/workspaces/microduck_rl 2>&1
ls "$CR/artifacts/basketball/" 2>&1
ls "$CR/checkpoints/LightNav-0/" 2>&1 | head -10
echo "=== SETUP_DONE ==="
