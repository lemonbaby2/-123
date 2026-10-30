#!/bin/bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate lerobot
export CUDA_VISIBLE_DEVICES=1
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_XET=1
export TOKENIZERS_PARALLELISM=false
mkdir -p /root/vla_outputs
cd /root/vla_outputs
exec python -u /root/vla_train_lora.py --dataset.repo_id=lerobot/pusht --policy.type=smolvla --policy.pretrained_path=/root/vla_models/smolvla_base --policy.load_vlm_weights=true --policy.device=cuda --policy.push_to_hub=false --peft.method_type=LORA --peft.r=16 --batch_size=8 --steps=20000 --log_freq=20 --save_freq=2000 --num_workers=4 --output_dir=/root/vla_outputs/smolvla_pusht_lora
