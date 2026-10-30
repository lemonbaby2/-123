"""LingBot-VLA 2.0 低内存流式加载（deploy 侧补丁模块）

背景
----
官方 `LingbotVlaV2Policy.__init__` 的加载顺序是:

    self.vla = self.load_vla(path)                  # ① CPU 建 fp32 模型 = 25.5GB RAM
    self.load_model_weights(path, strict=True)      # ② 一次性读全部分片到 dict = 又 25.5GB
    self.vla = self.vla.to(bfloat16).cuda()         # ③ 再转 bf16 上卡 = 12.76GB VRAM

峰值主机内存 ≈ 51GB。显存 16GB 的卡够用，但主机内存不足 56GB 的机器会 OOM，
且 Windows 上 `safe_open` 对 25GB 级 mmap 会撞页面文件上限（os error 1455）。

本模块做两件事，把峰值 RAM 压到约 13GB：

1. `enable_bf16_build()` —— 在 `load_vla` 之前把默认 dtype 设为 bf16，
   模型直接以 bf16 建在 CPU 上（12.76GB 而非 25.5GB）。
2. `stream_load_state_dict()` —— 逐分片读取 + 逐分片 copy_ 进模型，
   峰值只多出单分片大小（最大 419MB）。

结果：RAM ≈ 13GB，VRAM ≈ 12.8GB（激活另算 ~1.5GB），16GB 卡可跑。
精度与官方 `use_bf16=true` 完全等价（官方也是 fp32 载入后转 bf16）。

用法（在 deploy 脚本里）::

    import stream_load
    stream_load.enable_bf16_build()          # 必须在 load_vla 之前
    policy = LingbotVlaV2Policy(...)
    # 把 policy.load_model_weights = stream_load.make_stream_loader(policy)
"""
from __future__ import annotations

import glob
import json
import os
import struct
import time
from pathlib import Path
from typing import Dict, Iterable, Optional, Set, Tuple

import torch

# --------------------------------------------------------------------------
# 1) bf16 构建开关
# --------------------------------------------------------------------------


def enable_bf16_build() -> None:
    """在实例化模型前调用：让 nn.Parameter 直接以 bf16 分配，节省一半主机内存。"""
    torch.set_default_dtype(torch.bfloat16)
    print("[low-mem] default dtype = bfloat16（模型以 bf16 构建，主机内存省一半）")


def restore_fp32_build() -> None:
    torch.set_default_dtype(torch.float32)


# --------------------------------------------------------------------------
# 2) 分片流式加载
# --------------------------------------------------------------------------


def list_shards(model_dir: str) -> list[str]:
    """按 index.json 顺序返回分片绝对路径；无 index 时按文件名排序。"""
    d = Path(model_dir)
    idx = d / "model.safetensors.index.json"
    if idx.is_file():
        with open(idx) as f:
            wm = json.load(f).get("weight_map", {})
        shards = []
        for name in sorted(set(wm.values())):
            p = d / name
            if not p.is_file():
                raise FileNotFoundError(f"分片缺失: {p}")
            shards.append(str(p))
        return shards
    files = sorted(glob.glob(os.path.join(model_dir, "*.safetensors")))
    if not files:
        raise FileNotFoundError(f"{model_dir} 下没有 safetensors")
    return files


def _expected_keys(model_dir: str) -> Optional[Set[str]]:
    idx = Path(model_dir) / "model.safetensors.index.json"
    if not idx.is_file():
        return None
    with open(idx) as f:
        return set(json.load(f).get("weight_map", {}).keys())


def remap_fused_to_eager(key: str, tensor: torch.Tensor) -> Optional[list[Tuple[str, torch.Tensor]]]:
    """fused 专家权重 → eager 结构（sm_120 triton 不可用时的兜底）。

    fused: experts.gate_proj  [E, intermediate, hidden]
    eager: experts.{e}.gate_proj.weight  [intermediate, hidden]
    """
    for proj in ("gate_proj", "up_proj", "down_proj"):
        suffix = f".experts.{proj}"
        if key.endswith(suffix) and tensor.dim() == 3:
            prefix = key[: -len(suffix)]
            return [
                (f"{prefix}.experts.{e}.{proj}.weight", tensor[e].contiguous())
                for e in range(tensor.shape[0])
            ]
    return None


def stream_load_state_dict(
    model: torch.nn.Module,
    model_dir: str,
    strict: bool = True,
    moe_layout: str = "fused",
    shard_dtype: Optional[torch.dtype] = None,
    verbose: bool = True,
    dry_run: bool = False,
) -> Dict[str, int]:
    """逐分片加载，避免一次性把 25.5GB 读进内存。

    shard_dtype: 读入后立即转换的目标 dtype（默认跟随首个参数的 dtype，
                 bf16 构建时即为 bf16，可再省一半分片暂存）。
    dry_run:     只做键名/shape 校验，不读取 tensor 数据（零内存占用）。
                 用于在 CPU/小内存机器上验证 ckpt 与模型结构是否对齐。
    """
    from safetensors import safe_open

    t0 = time.time()
    shards = list_shards(model_dir)

    # 目标 dtype 与已有键
    owned = model.state_dict()
    if shard_dtype is None:
        try:
            shard_dtype = next(iter(owned.values())).dtype
        except StopIteration:
            shard_dtype = torch.float32

    seen: Set[str] = set()
    copied = 0
    total_bytes = 0
    remapped = 0

    for i, shard in enumerate(shards, 1):
        if dry_run:
            # 只读 header（JSON），不 mmap 数据区
            hdr = read_safetensors_header(shard)
            for k, meta in hdr.items():
                pairs = [(k, tuple(meta["shape"]))]
                if moe_layout == "eager" and k.endswith(
                    (".experts.gate_proj", ".experts.up_proj", ".experts.down_proj")
                ):
                    proj = k.rsplit(".", 1)[-1]
                    prefix = k[: -len(f".experts.{proj}")]
                    e = tuple(meta["shape"])[0]
                    pairs = [
                        (f"{prefix}.experts.{e_}.{proj}.weight",
                         tuple(meta["shape"])[1:])
                        for e_ in range(e)
                    ]
                    remapped += 1
                for name, shape in pairs:
                    seen.add(name)
                    target = owned.get(name)
                    if target is None:
                        if strict:
                            raise KeyError(f"模型里没有这个参数: {name}（ckpt 中多出）")
                        continue
                    if tuple(target.shape) != tuple(shape):
                        raise RuntimeError(
                            f"shape 不匹配 {name}: 模型{tuple(target.shape)} vs ckpt{tuple(shape)}"
                        )
                    copied += 1
            total_bytes += os.path.getsize(shard)
            if verbose:
                print(f"[dry-run] shard {i}/{len(shards)} {os.path.basename(shard)} "
                      f"{len(hdr)} tensors  累计匹配 {copied}")
            continue

        with safe_open(shard, framework="pt", device="cpu") as f:
            keys = list(f.keys())
            # 逐 tensor 处理，避免整片驻留
            for k in keys:
                t = f.get_tensor(k)
                pairs: Iterable[Tuple[str, torch.Tensor]]
                if moe_layout == "eager":
                    r = remap_fused_to_eager(k, t)
                    pairs = r if r is not None else [(k, t)]
                    if r is not None:
                        remapped += 1
                else:
                    pairs = [(k, t)]

                for name, tensor in pairs:
                    seen.add(name)
                    target = owned.get(name)
                    if target is None:
                        if strict:
                            raise KeyError(
                                f"模型里没有这个参数: {name}（ckpt 中多出）。"
                                f"若 ckpt 是 fused 而模型是 eager，请设 moe_layout='eager'"
                            )
                        continue
                    if tuple(target.shape) != tuple(tensor.shape):
                        raise RuntimeError(
                            f"shape 不匹配 {name}: 模型{tuple(target.shape)} "
                            f"vs ckpt{tuple(tensor.shape)}"
                        )
                    with torch.no_grad():
                        target.copy_(tensor.to(dtype=target.dtype))
                    copied += 1
                del t
        total_bytes += os.path.getsize(shard)
        if verbose:
            print(f"[low-mem] shard {i}/{len(shards)} {os.path.basename(shard)} "
                  f"{os.path.getsize(shard)/1e9:.2f}GB  累计 {copied} tensors")

    # 完整性核对
    expected = _expected_keys(model_dir)
    missing = sorted(k for k in owned.keys() if k not in seen)
    # 模型里的非持久 buffer 不算缺
    if missing:
        real_missing = []
        for k in missing:
            # 允许模型中存在但 ckpt 未提供的 buffer（如 _cache 类，persistent=False 已不在 state_dict）
            real_missing.append(k)
        if strict and expected is not None:
            # 只有 ckpt 里应当存在的键才算致命缺失
            real_missing = [k for k in real_missing if k in expected]
            if real_missing:
                raise RuntimeError(f"缺失 {len(real_missing)} 个参数，例如 {real_missing[:5]}")
        elif real_missing and verbose:
            print(f"[low-mem] WARN: {len(real_missing)} 个模型键未从 ckpt 加载（多为 buffer）")

    dt = time.time() - t0
    stats = {
        "shards": len(shards),
        "tensors_copied": copied,
        "tensors_remapped": remapped,
        "bytes_read": total_bytes,
        "seconds": round(dt, 1),
    }
    if verbose:
        print(f"[low-mem] 完成: {copied} tensors / {total_bytes/1e9:.2f}GB / {dt:.1f}s "
              f"（remap={remapped}）")
    return stats


def make_stream_loader(policy, moe_layout: str = "fused"):
    """返回可直接替换 policy.load_model_weights 的函数。"""

    def _loader(path_to_pi_model, strict: bool = True):
        return stream_load_state_dict(
            policy.vla, path_to_pi_model, strict=strict, moe_layout=moe_layout
        )

    return _loader


# --------------------------------------------------------------------------
# 3) 只读权重头（不 mmap，绕开 Windows 页面文件限制）
# --------------------------------------------------------------------------


def read_safetensors_header(path: str) -> Dict[str, dict]:
    """手工解析 safetensors 头（8 字节长度 + JSON），不建立 mmap。"""
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(n))
    header.pop("__metadata__", None)
    return header


def verify_shards(model_dir: str) -> bool:
    """字节级校验每个分片是否完整（大小 == 8 + header_len + 最大 data_offset）。"""
    ok = True
    for shard in list_shards(model_dir):
        h = read_safetensors_header(shard)
        with open(shard, "rb") as f:
            n = struct.unpack("<Q", f.read(8))[0]
        exp = 8 + n + max(v["data_offsets"][1] for v in h.values())
        act = os.path.getsize(shard)
        good = exp == act
        ok &= good
        print(f"  {os.path.basename(shard)}: {len(h)} tensors "
              f"{act/1e9:.2f}GB {'OK' if good else f'MISMATCH exp={exp}'}")
    return ok


if __name__ == "__main__":
    import sys

    d = sys.argv[1] if len(sys.argv) > 1 else r"D:\lingbot_models\robotwin_ckpt\hf_ckpt\lingbot-vla-v2-6b-robotwin"
    print(f"校验 {d}")
    print("所有分片完好" if verify_shards(d) else "存在损坏分片")
