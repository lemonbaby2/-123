# -*- coding: utf-8 -*-
"""
LingBot-VLA 2.0 部署前验证（CPU 安全，无 GPU / 不加载完整权重）
  [A] config 链路: lingbotvla_cli.yaml -> LingbotVLAV2Config -> merge_qwen_config
  [B] meta 设备实例化模型结构（零内存），统计参数量与 state_dict 键
  [C] 权重键名比对: safetensors index vs meta state_dict（strict load 前置校验）
  [D] FeatureTransform(robot_config + norm_stats) 构造
用法: python lingbot_smoke_meta.py [--weights DIR]
"""
import os, sys, time, json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
import yaml

REPO = Path(r"E:\研究生学习\黑客松\tmp\lingbot-vla-v2")
sys.path.insert(0, str(REPO))
os.chdir(REPO)

CKPT_ROOT = Path(r"D:\lingbot_models\robotwin_ckpt")
CLI_YAML = CKPT_ROOT / "lingbotvla_cli.yaml"
QWEN_PATH = r"D:\lingbot_models\Qwen3-VL-4B-Instruct"
WEIGHTS_DIR = Path(r"D:\lingbot_models\robotwin_ckpt\hf_ckpt\lingbot-vla-v2-6b-robotwin")

from lingbotvla.models.vla.lingbot_vla.configuration_lingbot_vla import LingbotVLAV2Config
from lingbotvla.models.vla.lingbot_vla.modeling_lingbot_vla_v2 import LingbotVlaV2Policy
from lingbotvla.models.vla.lingbot_vla.qwen3vl_in_vla import apply_lingbot_qwen3_vl_patch
from lingbotvla.data.vla_data.utils import FeatureTransform
from lingbotvla.models import build_processor
from transformers import AutoConfig
from safetensors import safe_open

t0 = time.time()
print("=" * 64)

# ---------- [A] config ----------
print("[A] config chain")
training_config = yaml.safe_load(open(CLI_YAML))
training_config["model"]["tokenizer_path"] = QWEN_PATH
training_config["model"]["config_path"] = str(CKPT_ROOT / "hf_ckpt" / "lingbot-vla-v2-6b-robotwin")
training_config["model"]["model_path"] = training_config["model"]["config_path"]
training_config["train"]["init_device"] = "cpu"
# 注意: moe_implementation 保持官方 yaml 的 "fused"（与真机部署/权重存储格式一致）

model_cfg = dict(training_config["model"])
model_cfg.update(training_config["train"])
config = LingbotVLAV2Config(**model_cfg)
for key, value in model_cfg.items():
    if not hasattr(config, key):
        setattr(config, key, value)
config.attention_implementation = "eager"
config.use_cache = True

qwen_config = AutoConfig.from_pretrained(QWEN_PATH)
for key in ["hidden_size", "intermediate_size", "num_hidden_layers", "num_attention_heads",
            "num_key_value_heads", "rms_norm_eps", "rope_theta", "vocab_size",
            "max_position_embeddings", "hidden_act", "tie_word_embeddings"]:
    tc = getattr(qwen_config, "text_config", None)
    if tc is not None and hasattr(tc, key):
        setattr(config, key, getattr(tc, key))
if hasattr(qwen_config, "vision_config"):
    config.vision_config = qwen_config.vision_config
print(f"    LingbotVLAV2Config ok: action_dim={config.action_dim} chunk={config.chunk_size} "
      f"hidden={config.hidden_size} layers={config.num_hidden_layers} vocab={config.vocab_size}")

# ---------- [B] meta 实例化 ----------
print("[B] meta-device instantiation (zero memory)")
apply_lingbot_qwen3_vl_patch()
with torch.device("meta"):
    policy = LingbotVlaV2Policy(config)
n_params = sum(p.numel() for p in policy.parameters())
print(f"    params: {n_params/1e9:.2f}B  ({time.time()-t0:.0f}s)")

sd_keys = set()
sd_shapes = {}
sd = policy.state_dict()  # 含 persistent buffers（如 e_score_correction_bias）
for name in sd:
    sd_keys.add(name)
    sd_shapes[name] = tuple(sd[name].shape)
print(f"    state_dict keys (incl. buffers): {len(sd_keys)}")

# ---------- [C] 权重键名比对 ----------
print("[C] checkpoint key matching (index.json only, no mmap)")
idx_file = WEIGHTS_DIR / "model.safetensors.index.json"
ckpt_keys = {}
if idx_file.exists():
    idx = json.loads(idx_file.read_text())
    weight_map = idx.get("weight_map", {})
    ckpt_keys = dict(weight_map)
    print(f"    index: {len(ckpt_keys)} tensors across {len(set(weight_map.values()))} shards")
else:
    import struct
    for p in sorted(WEIGHTS_DIR.glob("*.safetensors")):
        with open(p, "rb") as f:
            n = struct.unpack("<Q", f.read(8))[0]
            header = json.loads(f.read(n))
        for k in header:
            if k != "__metadata__":
                ckpt_keys[k] = p.name
    print(f"    (no index; read headers) {len(ckpt_keys)} tensors")
missing_in_model = sorted(k for k in ckpt_keys if k not in sd_keys)
missing_in_ckpt = sorted(k for k in sd_keys if k not in ckpt_keys)
if missing_in_model:
    print(f"    !! in ckpt but NOT in model ({len(missing_in_model)}):")
    for k in missing_in_model[:15]:
        print(f"       - {k}")
if missing_in_ckpt:
    print(f"    !! in model but NOT in ckpt ({len(missing_in_ckpt)}):")
    for k in missing_in_ckpt[:15]:
        print(f"       - {k}")
if not missing_in_model and not missing_in_ckpt:
    print("    PERFECT MATCH: strict load will succeed")

# shape 逐键校验（从 safetensors 头部读 shape，零内存，比键名更严格）
print("[C2] shape verification")
import struct
ckpt_shapes = {}
for shard in sorted(set(ckpt_keys.values())):
    p = WEIGHTS_DIR / shard
    with open(p, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        h = json.loads(f.read(n))
    for k, v in h.items():
        if k == "__metadata__":
            continue
        ckpt_shapes[k] = (tuple(v["shape"]), v["dtype"])

shape_mismatch = []
for k, (cshape, cdtype) in ckpt_shapes.items():
    if k in sd_shapes and tuple(sd_shapes[k]) != cshape:
        shape_mismatch.append((k, cshape, tuple(sd_shapes[k])))
if shape_mismatch:
    print(f"    !! shape mismatch ({len(shape_mismatch)}):")
    for k, c, m in shape_mismatch[:10]:
        print(f"       {k}: ckpt{c} vs model{m}")
else:
    print(f"    all {len(ckpt_shapes)} tensor shapes MATCH")

# 抽查 dtype 分布
from collections import Counter
dt = Counter(v[1] for v in ckpt_shapes.values())
print(f"    ckpt dtypes: {dict(dt)}")

# ---------- [D] FeatureTransform ----------
print("[D] FeatureTransform")
robot_name = "realman_gen65bi"
data_config = SimpleNamespace(**training_config["data"])
ft = FeatureTransform(
    f"configs/robot_configs/{robot_name}.yaml",
    data_config, config, None,  # processor=None -> tokenizer=None（CPU 无 Qwen processor 内存压力时可用）
    chunk_size=config.chunk_size,
    norm_stats_path=None,
)
print(f"    states={ft.states}")
print(f"    actions={ft.actions}")
print(f"    images={ft.images}")
print(f"    normalizer={type(ft.normalizer).__name__}")

print("=" * 64)
ok = not missing_in_model and not missing_in_ckpt and not shape_mismatch
print(f"META SMOKE {'OK' if ok else 'DONE (diff above)'}  total {time.time()-t0:.0f}s")
