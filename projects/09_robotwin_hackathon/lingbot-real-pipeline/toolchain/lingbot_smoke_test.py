# -*- coding: utf-8 -*-
"""
LingBot-VLA 2.0 CPU 冒烟测试（不依赖 GPU / 不加载权重）
复刻 deploy/lingbot_vla_v2_policy.py load_vla 的真实代码路径：
  1. lingbotvla_cli.yaml -> LingbotVLAV2Config
  2. AutoConfig.from_pretrained(Qwen3-VL 本地) + merge_qwen_config
  3. build_processor
  4. LingBotVlaV2InferencePolicy(config, eval=True)  # CPU fp32
  5. FeatureTransform(robot_config + norm_stats)
  6. 假观测前向（sample_actions）验证 shape
"""
import os, sys, time, json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
import yaml

torch.set_default_dtype(torch.bfloat16)  # CPU 冒烟：fp32 全模型 >30G OOM，bf16 减半

REPO = Path(r"E:\研究生学习\黑客松\tmp\lingbot-vla-v2")
sys.path.insert(0, str(REPO))
os.chdir(REPO)  # robot_config 相对路径 configs/robot_configs/...

CKPT_ROOT = Path(r"D:\lingbot_models\robotwin_ckpt")
CLI_YAML = CKPT_ROOT / "lingbotvla_cli.yaml"
QWEN_PATH = r"D:\lingbot_models\Qwen3-VL-4B-Instruct"

from lingbotvla.models.vla.lingbot_vla.configuration_lingbot_vla import LingbotVLAV2Config
from lingbotvla.models.vla.lingbot_vla.modeling_lingbot_vla_v2 import LingbotVlaV2Policy
from lingbotvla.models.vla.lingbot_vla.qwen3vl_in_vla import apply_lingbot_qwen3_vl_patch
from lingbotvla.data.vla_data.utils import FeatureTransform
from lingbotvla.models import build_processor

t0 = time.time()
print("=" * 60)
print("[1/6] load training config")
training_config = yaml.safe_load(open(CLI_YAML))
training_config["model"]["tokenizer_path"] = QWEN_PATH
training_config["model"]["config_path"] = str(CKPT_ROOT / "hf_ckpt" / "lingbot-vla-v2-6b-robotwin")
training_config["model"]["model_path"] = training_config["model"]["config_path"]
training_config["train"]["init_device"] = "cpu"
training_config["train"]["moe_implementation"] = "eager"  # 避开 triton fused kernel（CPU 无 triton）

model_cfg = dict(training_config["model"])
model_cfg.update(training_config["train"])
config = LingbotVLAV2Config(**model_cfg)
for key, value in model_cfg.items():
    if not hasattr(config, key):
        setattr(config, key, value)
config.attention_implementation = "eager"  # 与 load_vla 一致
config.use_cache = True
print(f"    config ok: action_dim={config.action_dim} chunk_size={config.chunk_size} "
      f"img_size={training_config['data']['img_size']}")

print("[2/6] merge qwen config")
from transformers import AutoConfig
qwen_config = AutoConfig.from_pretrained(QWEN_PATH)
print(f"    qwen: {type(qwen_config).__name__} text_hidden={getattr(qwen_config, 'text_config', qwen_config).hidden_size}")

# merge_qwen_config 是 server 类的方法，取出核心逻辑
import re, inspect
src = inspect.getsource(apply_lingbot_qwen3_vl_patch)
print(f"    qwen3vl patch fn: {len(src)} chars (will apply)")

print("[3/6] build_processor (Qwen3-VL local)")
processor = build_processor(QWEN_PATH)
tok = processor.tokenizer
print(f"    tokenizer ok: vocab={tok.vocab_size} pad={tok.pad_token}")

print("[4/6] instantiate LingbotVlaV2Policy on CPU (fp32)")
apply_lingbot_qwen3_vl_patch()
policy = LingbotVlaV2Policy(config)
policy = policy.cpu().eval()
n_params = sum(p.numel() for p in policy.parameters())
print(f"    params: {n_params/1e9:.2f}B  ({time.time()-t0:.0f}s)")

print("[5/6] FeatureTransform (robot_config + norm_stats)")
robot_name = "realman_gen65bi"
data_config = SimpleNamespace(**training_config["data"])
ft = FeatureTransform(
    f"configs/robot_configs/{robot_name}.yaml",
    data_config, config, processor,
    chunk_size=config.chunk_size,
    norm_stats_path=None,  # -> robot_config 内 norm_stats 字段
)
print(f"    states={ft.states}")
print(f"    actions={ft.actions}")
print(f"    images={ft.images}")
print(f"    normalizer={type(ft.normalizer).__name__}")

print("[6/6] fake observation forward (CPU)")
H = W = training_config["data"]["img_size"]
fake_obs = {
    "observation.images.cam_high": np.random.randint(0, 255, (H, W, 3), dtype=np.uint8),
    "observation.images.cam_wrist": np.random.randint(0, 255, (H, W, 3), dtype=np.uint8),
    "observation.state": np.zeros(7, dtype=np.float32),   # 6 joints(rad) + gripper
    "task": "pick up the object",
}
# 走 FeatureTransform.apply 得到模型输入
item = ft.apply(fake_obs, policy_eval=True)
print(f"    apply keys: {sorted(item.keys())}")
for k, v in item.items():
    if isinstance(v, torch.Tensor):
        print(f"      {k}: {tuple(v.shape)} {v.dtype}")
    elif isinstance(v, np.ndarray):
        print(f"      {k}: {v.shape} {v.dtype}")

obs = {
    "images": torch.as_tensor(item["images"]).float(),
    "img_masks": torch.as_tensor(item["img_masks"]).bool(),
    "lang_tokens": torch.as_tensor(item["lang_tokens"]).long(),
    "lang_masks": torch.as_tensor(item["lang_masks"]).bool(),
    "state": torch.as_tensor(item["states"]).float(),
}
if "image_grid_thw" in item:
    obs["image_grid_thw"] = torch.as_tensor(item["image_grid_thw"]).long()

with torch.no_grad():
    t1 = time.time()
    actions = policy.model.sample_actions(
        obs["images"].unsqueeze(0).to(torch.bfloat16),
        obs["img_masks"].unsqueeze(0),
        obs["lang_tokens"].unsqueeze(0),
        obs["lang_masks"].unsqueeze(0),
        obs["state"].unsqueeze(0).to(torch.bfloat16),
        image_grid_thw=obs.get("image_grid_thw"),
    )
print(f"    sample_actions: {tuple(actions.shape)} dtype={actions.dtype} ({time.time()-t1:.1f}s)")
assert actions.shape[-1] >= 7, f"action dim too small: {actions.shape}"
print("=" * 60)
print(f"SMOKE OK  total {time.time()-t0:.0f}s")
