# -*- coding: utf-8 -*-
"""
LingBot-VLA 2.0 真实权重 CPU 端到端验证（流式加载，bf16，零 GPU）
- 用官方 roboant/lingbot-vla-v2-6b-robotwin 权重（fp32 25.5GB, 6 shards）
- 分片流式 load_state_dict（每片转 bf16 后立即释放），峰值内存 ~18GB
- 假观测走完整 FeatureTransform -> sample_actions -> unapply 链路
用法: python cpu_infer_test.py
"""
import os, sys, time, json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
import yaml
from safetensors.torch import load_file

REPO = Path(r"E:\研究生学习\黑客松\tmp\lingbot-vla-v2")
sys.path.insert(0, str(REPO))
os.chdir(REPO)

CKPT_ROOT = Path(r"D:\lingbot_models\robotwin_ckpt")
CLI_YAML = CKPT_ROOT / "lingbotvla_cli.yaml"
QWEN_PATH = r"D:\lingbot_models\Qwen3-VL-4B-Instruct"
WEIGHTS_DIR = CKPT_ROOT / "hf_ckpt" / "lingbot-vla-v2-6b-robotwin"

torch.set_default_dtype(torch.bfloat16)
torch.set_num_threads(os.cpu_count() or 8)

from lingbotvla.models.vla.lingbot_vla.configuration_lingbot_vla import LingbotVLAV2Config
from lingbotvla.models.vla.lingbot_vla.modeling_lingbot_vla_v2 import LingbotVlaV2Policy
from lingbotvla.models.vla.lingbot_vla.qwen3vl_in_vla import apply_lingbot_qwen3_vl_patch
from lingbotvla.data.vla_data.utils import FeatureTransform
from lingbotvla.models import build_processor
from transformers import AutoConfig

t0 = time.time()
print("=" * 66, flush=True)

# ---------- config ----------
training_config = yaml.safe_load(open(CLI_YAML))
training_config["model"]["tokenizer_path"] = QWEN_PATH
training_config["model"]["config_path"] = str(WEIGHTS_DIR)
training_config["model"]["model_path"] = str(WEIGHTS_DIR)
training_config["train"]["init_device"] = "cpu"

model_cfg = dict(training_config["model"]); model_cfg.update(training_config["train"])
config = LingbotVLAV2Config(**model_cfg)
for k, v in model_cfg.items():
    if not hasattr(config, k):
        setattr(config, k, v)
config.attention_implementation = "eager"
config.use_cache = True
print(f"[1] config ok  action_dim={config.action_dim} chunk={config.chunk_size}", flush=True)

qwen_config = AutoConfig.from_pretrained(QWEN_PATH)
for k in ["hidden_size", "intermediate_size", "num_hidden_layers", "num_attention_heads",
          "num_key_value_heads", "rms_norm_eps", "rope_theta", "vocab_size",
          "max_position_embeddings", "hidden_act", "tie_word_embeddings"]:
    tc = getattr(qwen_config, "text_config", None)
    if tc is not None and hasattr(tc, k):
        setattr(config, k, getattr(tc, k))
if hasattr(qwen_config, "vision_config"):
    config.vision_config = qwen_config.vision_config

processor = build_processor(QWEN_PATH)
print(f"[2] processor ok  vocab={processor.tokenizer.vocab_size}", flush=True)

# ---------- 模型（bf16）----------
apply_lingbot_qwen3_vl_patch()
print("[3] building model in bf16 (ram ~12.8GB)...", flush=True)
policy = LingbotVlaV2Policy(config)
policy = policy.eval()
n_params = sum(p.numel() for p in policy.parameters())
print(f"    params {n_params/1e9:.2f}B  ({time.time()-t0:.0f}s)", flush=True)

# ---------- 流式加载权重 ----------
print("[4] streaming load (per-shard -> bf16 -> release)...", flush=True)
idx = json.loads((WEIGHTS_DIR / "model.safetensors.index.json").read_text())
shards = sorted(set(idx["weight_map"].values()))
missing_all, unexpected_all = [], []
for i, shard in enumerate(shards, 1):
    t_s = time.time()
    sd = load_file(str(WEIGHTS_DIR / shard))
    sd = {k: (v.to(torch.bfloat16) if v.is_floating_point() else v) for k, v in sd.items()}
    r = policy.load_state_dict(sd, strict=False)
    missing_all += list(r.missing_keys)
    unexpected_all += list(r.unexpected_keys)
    print(f"    [{i}/{len(shards)}] {shard}: {len(sd)} tensors in {time.time()-t_s:.1f}s "
          f"(missing so far {len(missing_all)}, unexpected {len(unexpected_all)})", flush=True)
    del sd
    import gc; gc.collect()

print(f"    load done: missing={len(missing_all)} unexpected={len(unexpected_all)}", flush=True)
if missing_all[:5]:
    print("    missing sample:", missing_all[:5], flush=True)
if unexpected_all[:5]:
    print("    unexpected sample:", unexpected_all[:5], flush=True)
assert not missing_all and not unexpected_all, "权重未完全匹配！"

# ---------- FeatureTransform ----------
data_config = SimpleNamespace(**training_config["data"])
ft = FeatureTransform(
    "configs/robot_configs/realman_gen65bi.yaml",
    data_config, config, processor,
    chunk_size=config.chunk_size, norm_stats_path=None,
)
policy.feature_transform = ft
print(f"[5] FeatureTransform ok  actions={ft.actions}", flush=True)

# ---------- 假观测端到端推理 ----------
print("[6] end-to-end inference (fake obs)...", flush=True)
H = W = training_config["data"]["img_size"]
obs = {
    "observation.images.camera_top": np.random.randint(0, 255, (H, W, 3), dtype=np.uint8),
    "observation.images.camera_wrist_left": np.random.randint(0, 255, (H, W, 3), dtype=np.uint8),
    "observation.state": np.zeros(7, dtype=np.float32),
    "task": "pick up the block and place it into the box",
}
t_inf = time.time()
with torch.no_grad():
    item = ft.apply(obs, policy_eval=True)
    print("    applied keys:", sorted(item.keys()), flush=True)
    for k, v in item.items():
        if isinstance(v, torch.Tensor):
            print(f"      {k}: {tuple(v.shape)} {v.dtype}", flush=True)
    actions = policy.model.sample_actions(
        item["images"].unsqueeze(0).to(torch.bfloat16),
        item["img_masks"].unsqueeze(0),
        item["lang_tokens"].unsqueeze(0),
        item["lang_masks"].unsqueeze(0),
        item["state"].unsqueeze(0).to(torch.bfloat16),
        image_grid_thw=item.get("image_grid_thw").unsqueeze(0) if item.get("image_grid_thw") is not None else None,
    )
print(f"    sample_actions -> {tuple(actions.shape)} {actions.dtype}  "
      f"({time.time()-t_inf:.1f}s)", flush=True)

# 反归一化
with torch.no_grad():
    single = dict(item)
    single["actions"] = actions[0].float()
    data = ft.unapply(single)
arm = np.asarray(data["action"]) if "action" in data else None
print(f"[7] unapply keys={list(data.keys())}", flush=True)
if arm is not None:
    print(f"    action shape {arm.shape}", flush=True)
    print(f"    first step: {np.round(arm[0], 4)}", flush=True)
    print(f"    arm joints(deg) first step: {np.round(np.rad2deg(arm[0][:6]), 1)}", flush=True)
    print(f"    effector first step: {arm[0][6]:.4f}", flush=True)

print("=" * 66, flush=True)
print(f"CPU END2END OK  total {time.time()-t0:.0f}s", flush=True)
