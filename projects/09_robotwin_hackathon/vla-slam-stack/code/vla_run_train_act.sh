#!/bin/bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate lerobot
export CUDA_VISIBLE_DEVICES=0
export HF_ENDPOINT=https://hf-mirror.com
export TOKENIZERS_PARALLELISM=false
mkdir -p /root/vla_outputs
cd /root/vla_outputs
exec lerobot-train   --dataset.repo_id=lerobot/pusht   --policy.type=act   --policy.device=cuda   --policy.push_to_hub=false   --batch_size=16 --steps=20000 --log_freq=20 --save_freq=2000   --num_workers=4 --output_dir=/root/vla_outputs/act_pusht
