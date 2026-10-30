#!/usr/bin/env python
"""LingBot-VLA 2.0 GPU 就绪探测（在 GPU 机器上运行，纯只读，不改环境）

用法:
    python gpu_check.py
    python gpu_check.py --weights /data/.../lingbot-vla-v2-6b-robotwin

输出四段判定:
    [1] GPU 硬件      型号 / 显存 / 计算能力
    [2] torch 兼容    版本 + 是否含该 arch 的 kernel（sm_120 需 cu128+）
    [3] 显存预算      能否装下 6.38B bf16
    [4] 运行环境     triton / flash-attn / 关键依赖版本
最后打印 GO / NO-GO 结论。
"""
from __future__ import annotations

import argparse
import importlib
import os
import platform
import sys

# 6.38B 参数（实测 state_dict 1708 键）
N_PARAMS = 6.38e9
GB = 1e9


def hr(title: str) -> None:
    print("\n" + "=" * 62)
    print(title)
    print("=" * 62)


def sec1_gpu() -> dict:
    hr("[1] GPU 硬件")
    info = {"count": 0, "name": "", "vram": 0.0, "sm": (0, 0), "ok": False}
    try:
        import torch
    except ImportError:
        print("  !! torch 未安装，先装 torch 再跑本脚本")
        return info

    if not torch.cuda.is_available():
        print("  !! torch.cuda.is_available() = False")
        print("     可能原因：装了 CPU 版 torch / 驱动未装 / CUDA 版本与 arch 不匹配")
        print(f"     torch={torch.__version__}  cuda_built={torch.version.cuda}")
        return info

    info["count"] = torch.cuda.device_count()
    print(f"  设备数: {info['count']}")
    for i in range(info["count"]):
        p = torch.cuda.get_device_properties(i)
        sm = f"sm_{p.major}{p.minor}"
        print(f"  GPU{i}: {p.name}")
        print(f"        显存 {p.total_memory / GB:.2f} GB   计算能力 {sm}   "
              f"MP={p.multi_processor_count}")
        if i == 0:
            info.update(name=p.name, vram=p.total_memory / GB, sm=(p.major, p.minor))
    info["ok"] = info["count"] > 0
    return info


def sec2_torch(gpu: dict) -> dict:
    hr("[2] torch / arch 兼容性")
    import torch

    out = {"ok": False, "cuda_built": torch.version.cuda or "cpu", "arch_ok": None}
    print(f"  torch      : {torch.__version__}")
    print(f"  cuda_built : {torch.version.cuda or 'CPU-only build'}")

    if gpu["sm"] == (0, 0):
        print("  跳过（无 GPU）")
        return out

    major, minor = gpu["sm"]
    arch_str = f"sm_{major}{minor}"
    try:
        arch_list = torch.cuda.get_arch_list()
    except Exception:
        arch_list = []
    print(f"  torch arch : {', '.join(arch_list) if arch_list else '(无法读取)'}")

    sm_tag = f"sm_{major}{minor}"
    # torch 的 arch list 里 Blackwell 常以 sm_120 / sm_100 出现
    arch_ok = any(sm_tag in a for a in arch_list) if arch_list else None
    out["arch_ok"] = arch_ok

    if arch_ok is False:
        print(f"  !! torch 未编译 {arch_str} kernel → 运行会报 "
              f"'no kernel image is available for execution on the device'")
        if major >= 12:
            print(f"     修复: pip install --force-reinstall torch torchvision "
                  f"--index-url https://download.pytorch.org/whl/cu128")
            print(f"     (Blackwell {arch_str} 必须 cu128 及以上 wheel)")
    elif arch_ok:
        print(f"  OK: torch 含 {arch_str} kernel")
        out["ok"] = True

    # 实机小算子冒烟：比 arch list 更硬
    try:
        a = torch.randn(64, 64, device="cuda", dtype=torch.bfloat16)
        b = (a @ a).float().sum().item()
        print(f"  bf16 矩阵乘实测: OK (sum={b:.1f})")
        out["bf16_ok"] = True
    except Exception as e:
        print(f"  !! bf16 CUDA 算子失败: {type(e).__name__}: {e}")
        out["bf16_ok"] = False
    return out


def sec3_budget(gpu: dict) -> dict:
    hr("[3] 显存预算（6.38B 参数）")
    out = {"fits_bf16": False, "fits_fp32": False}
    if gpu["vram"] <= 0:
        print("  跳过（无 GPU）")
        return out

    need_bf16 = N_PARAMS * 2 / GB
    need_fp32 = N_PARAMS * 4 / GB
    overhead = 1.5  # CUDA context + 激活 + KV cache（2 图短 prompt，no_grad）
    need_bf16_total = need_bf16 + overhead

    print(f"  权重 bf16      : {need_bf16:6.2f} GB")
    print(f"  权重 fp32      : {need_fp32:6.2f} GB")
    print(f"  运行时开销约   : {overhead:6.2f} GB (context+激活+KV)")
    print(f"  ----")
    print(f"  bf16 合计需要  : {need_bf16_total:6.2f} GB")
    print(f"  本机可用       : {gpu['vram']:6.2f} GB")

    try:
        import torch
        free, total = torch.cuda.mem_get_info()
        print(f"  当前空闲       : {free / GB:6.2f} GB (总 {total / GB:.2f} GB)")
    except Exception:
        free = gpu["vram"] * GB

    margin = gpu["vram"] - need_bf16_total
    out["fits_fp32"] = gpu["vram"] >= need_fp32 + overhead
    out["fits_bf16"] = gpu["vram"] >= need_bf16_total

    if out["fits_bf16"] and margin >= 2.0:
        print(f"  ✅ GO: bf16 可跑，余量 {margin:.1f} GB")
    elif out["fits_bf16"]:
        print(f"  🟡 能跑但很紧，余量仅 {margin:.1f} GB")
        print(f"     建议: use_length=25、sdpa 注意力、关 compile、"
              f"必要时降图像分辨率")
    else:
        print(f"  ❌ NO-GO: 差 {abs(margin):.1f} GB")
        print(f"     选项: ① 换 ≥16GB 卡  ② 多卡 device_map 切分（未验证）"
              f"  ③ CPU offload（单步几十秒，做不了闭环）")
    return out


def sec4_env(gpu: dict) -> dict:
    hr("[4] 运行环境")
    out = {}

    # triton —— MoE fused 路径依赖
    try:
        import triton
        ver = getattr(triton, "__version__", "?")
        # 判断是否我们装的 stub（stub 里 KernelInterface.run 会抛 RuntimeError）
        is_stub = False
        try:
            from triton.backends.compiler import AttrsDescriptor  # noqa: F401
        except Exception:
            is_stub = True
        out["triton"] = ver
        tag = "  ← 这是我们为 Windows CPU 装的 stub，GPU 上必须换成真 triton！" if is_stub else ""
        print(f"  triton     : {ver}{tag}")
        if is_stub:
            print(f"    修复: pip install --force-reinstall 'triton>=3.3'")
    except ImportError:
        print("  triton     : 未安装（GPU 上 MoE fused 路径会失败）")
        out["triton"] = None

    # flash-attn —— 可选
    try:
        import flash_attn
        print(f"  flash-attn : {flash_attn.__version__}")
        out["flash_attn"] = flash_attn.__version__
    except ImportError:
        print("  flash-attn : 未安装 → 自动回退 sdpa/eager（不影响正确性）")
        out["flash_attn"] = None

    # 关键依赖版本矩阵
    print("  ----")
    want = {
        "transformers": "4.57.3",
        "tokenizers": "0.22.2",
        "huggingface_hub": "0.34.4",
        "datasets": "3.6.0",
        "lerobot": "*",
        "av": "15.x",
        "websockets": "<14",
    }
    pkgs = {
        "transformers": "transformers",
        "tokenizers": "tokenizers",
        "huggingface_hub": "huggingface_hub",
        "datasets": "datasets",
        "lerobot": "lerobot",
        "av": "av",
        "websockets": "websockets",
    }
    hub_ver = None
    for name, mod in pkgs.items():
        try:
            m = importlib.import_module(mod)
            v = getattr(m, "__version__", "?")
        except ImportError:
            v = "MISSING"
        if name == "huggingface_hub":
            hub_ver = v
        flag = ""
        if v == "MISSING":
            flag = "  ← 缺失"
        elif name == "huggingface_hub" and v != "0.34.4":
            flag = "  ← 必须是 0.34.4（transformers 4.57.3 要求 hub<1.0）"
        elif name == "av" and not str(v).startswith("15."):
            flag = "  ← 必须 15.x（19.x 无 av.option，lerobot 会崩）"
        elif name == "websockets" and str(v).split(".")[0] not in ("13", "12"):
            flag = "  ← 建议 <14（13.x API 差异，补丁已兼容）"
        print(f"  {name:18s}: {v:10s} (期望 {want[name]}){flag}")

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="", help="模型目录，用于额外校验（可选）")
    args = ap.parse_args()

    print("LingBot-VLA 2.0 GPU 就绪探测")
    print(f"host={platform.node()}  os={platform.platform()}  py={sys.version.split()[0]}")

    gpu = sec1_gpu()
    torch_ok = sec2_torch(gpu)
    budget = sec3_budget(gpu)
    env = sec4_env(gpu)

    if args.weights:
        hr("[5] 权重目录")
        import glob
        import json
        w = os.path.abspath(args.weights)
        idx = os.path.join(w, "model.safetensors.index.json")
        print(f"  目录: {w}")
        if os.path.isfile(idx):
            with open(idx) as f:
                wm = json.load(f).get("weight_map", {})
            shards = sorted(set(wm.values()))
            print(f"  index: {len(wm)} tensors / {len(shards)} shards")
            for s in shards:
                p = os.path.join(w, s)
                print(f"    {s}: {'OK' if os.path.exists(p) else 'MISSING'}")
        else:
            print("  !! 缺 model.safetensors.index.json")
        cli = os.path.join(os.path.dirname(os.path.dirname(w)), "lingbotvla_cli.yaml")
        print(f"  cli yaml（须在上两级）: {cli} -> "
              f"{'OK' if os.path.exists(cli) else 'MISSING'}")

    hr("结论")
    verdict = []
    if not gpu["ok"]:
        verdict.append("❌ 无可用 GPU")
    if torch_ok.get("arch_ok") is False:
        verdict.append("❌ torch 缺该 arch 的 kernel，必须换 cu128+ wheel")
    if gpu["ok"] and budget["fits_bf16"]:
        verdict.append("✅ 显存够跑 bf16")
    elif gpu["ok"]:
        verdict.append("❌ 显存不够 6.38B bf16")
    if env.get("triton") and gpu["ok"]:
        pass

    for v in verdict:
        print("  " + v)

    go = (
        gpu["ok"]
        and torch_ok.get("arch_ok") is not False
        and budget["fits_bf16"]
    )
    print()
    if go:
        print("  → GO：下一步跑 deploy/apply_patches.py，再 bash deploy/serve_gpu.sh")
        return 0
    print("  → NO-GO：按上面 ⚠ 提示处理后再跑本脚本")
    return 1


if __name__ == "__main__":
    sys.exit(main())
