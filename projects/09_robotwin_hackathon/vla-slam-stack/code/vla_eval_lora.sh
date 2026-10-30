#!/bin/bash
# usage: vla_eval_lora.sh <policy_path> <gpu_id> <output_dir> <n_episodes>
source /root/miniconda3/etc/profile.d/conda.sh
conda activate lerobot
export CUDA_VISIBLE_DEVICES="$2"
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_XET=1
export MUJOCO_GL=egl
cd /root/vla_outputs
exec python -u /root/vla_eval_patched.py --policy.path="$1" --env.type=pusht --eval.n_episodes="$4" --eval.batch_size="$4" --eval.use_async_envs=false --output_dir="$3" --seed=1000
