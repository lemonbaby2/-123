# -*- coding: utf-8 -*-
"""模型容量实测 —— 回答「这两张卡到底能跑什么模型」

不下载任何模型，用真实显存分配 + 真实 GEMM 来量化：
  1) 每张卡最大可用显存（真正做到"能装下多大"）
  2) Transformer 层的实际吞吐（tokens/s 估算）
  3) 不同精度（FP16 / BF16 / INT8）的推理速度
  4) 据此推算能跑哪些规模的模型

用法:
  python model_capacity.py            # 全测
  python model_capacity.py --quick    # 只测显存 + 一次吞吐
"""
import os
import time
import json
import argparse

import torch


def max_alloc(dev):
    """逐次倍增探测最大可分配显存"""
    torch.cuda.set_device(dev)
    torch.cuda.empty_cache()
    info = torch.cuda.get_device_properties(dev)
    print(f"\n  [{dev}] {info.name}  总显存 {info.total_memory/1024**3:.2f} GiB")
    blocks = []
    step = 256 * 1024 * 1024          # 每次申请 256 MiB
    mb_total = 0
    try:
        while True:
            blocks.append(torch.empty(step // 4, dtype=torch.float32,
                                      device=f"cuda:{dev}"))
            mb_total += step
            if mb_total > info.total_memory * 1.2:
                break
    except torch.OutOfMemoryError:
        pass
    except RuntimeError:
        pass
    got = sum(b.numel() * 4 for b in blocks) / 1024**3
    print(f"      实际可分配   : {got:.2f} GiB "
          f"(占标称 {got/(info.total_memory/1024**3)*100:.0f}%)")
    del blocks
    torch.cuda.empty_cache()
    return got


def transformer_layer_bench(dev, hidden=4096, batch=1, seq=512,
                            dtype=torch.float16, layers=1, iters=30):
    """模拟一层 Transformer 的 QKV+O+FFN 投影，测 tokens/s"""
    torch.cuda.set_device(dev)
    torch.cuda.empty_cache()
    try:
        # 一层: qkv(3h×h) + o(h×h) + ffn(2 × 4h×h) ≈ 12 h² 参数
        w1 = torch.randn(hidden, hidden * 3, device=f"cuda:{dev}", dtype=dtype)
        w2 = torch.randn(hidden, hidden, device=f"cuda:{dev}", dtype=dtype)
        w3 = torch.randn(hidden, hidden * 4, device=f"cuda:{dev}", dtype=dtype)
        w4 = torch.randn(hidden * 4, hidden, device=f"cuda:{dev}", dtype=dtype)
        x = torch.randn(batch * seq, hidden, device=f"cuda:{dev}", dtype=dtype)
    except torch.OutOfMemoryError:
        return None
    for _ in range(3):
        h = x @ w1
        h = h[:, :hidden] @ w2
        h = h @ w3
        _ = h @ w4
    torch.cuda.synchronize()
    t0 = time.time()
    for _ in range(iters):
        h = x @ w1
        h = h[:, :hidden] @ w2
        h = h @ w3
        _ = h @ w4
    torch.cuda.synchronize()
    dt = (time.time() - t0) / iters
    # 一层大约 12 h² FLOPs/token
    flops = 12 * hidden * hidden * batch * seq * 2
    tflops = flops / dt / 1e12
    tokens_s = batch * seq / dt
    del w1, w2, w3, w4, x
    torch.cuda.empty_cache()
    return dict(ms=round(dt * 1000, 2), tflops=round(tflops, 2),
                tokens_s=round(tokens_s, 1))


def int8_bench(dev, hidden=4096, iters=30):
    """INT8 GEMM —— Blackwell 第 5 代 Tensor Core 的强项"""
    torch.cuda.set_device(dev)
    torch.cuda.empty_cache()
    try:
        a = torch.randint(-127, 127, (hidden, hidden),
                          device=f"cuda:{dev}", dtype=torch.int8)
        b = torch.randint(-127, 127, (hidden, hidden),
                          device=f"cuda:{dev}", dtype=torch.int8)
        c = torch.mm(a, b)
    except Exception as e:
        return f"INT8 matmul 不支持: {str(e)[:60]}"
    torch.cuda.synchronize()
    t0 = time.time()
    for _ in range(iters):
        c = torch.mm(a, b)
    torch.cuda.synchronize()
    dt = (time.time() - t0) / iters
    tops = 2 * hidden ** 3 / dt / 1e12
    del a, b, c
    torch.cuda.empty_cache()
    return dict(ms=round(dt * 1000, 3), tops=round(tops, 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "result_capacity.json"))
    a = ap.parse_args()

    n = torch.cuda.device_count()
    rep = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "devices": {}}

    print("=" * 78)
    print("  1) 最大可用显存（能装下多大的模型）")
    print("=" * 78)
    for i in range(n):
        got = max_alloc(i)
        rep["devices"][i] = {"name": torch.cuda.get_device_name(i),
                             "max_alloc_gib": round(got, 2)}

    print("\n" + "=" * 78)
    print("  2) Transformer 单层吞吐（hidden=4096, seq=512, batch=1）")
    print("=" * 78)
    for i in range(n):
        print(f"\n  [{i}] {torch.cuda.get_device_name(i)}")
        for dt_name, dt in (("FP16", torch.float16), ("BF16", torch.bfloat16)):
            r = transformer_layer_bench(i, dtype=dt)
            if r:
                print(f"      {dt_name}: 每层 {r['ms']:7.2f} ms  "
                      f"{r['tflops']:6.2f} TFLOPS  {r['tokens_s']:8.1f} tokens/s")
                rep["devices"][i][f"layer_{dt_name}"] = r
        if not a.quick:
            r8 = int8_bench(i)
            print(f"      INT8: {r8}")
            rep["devices"][i]["int8"] = r8

    print("\n" + "=" * 78)
    print("  3) 推理速度推算（以 7B 模型 32 层为例）")
    print("=" * 78)
    for i in range(n):
        d = rep["devices"][i]
        r = d.get("layer_FP16")
        if not r:
            continue
        # 7B / 32 层 → 每层约 218M 参数；用实测单层耗时外推
        per_layer = r["ms"]
        total = per_layer * 32
        print(f"\n  [{i}] {d['name']}")
        print(f"      7B FP16 单层 {per_layer:.1f} ms → 32 层 {total:.0f} ms/forward")
        print(f"      ≈ {1000/total:.1f} forward/s（不含 KV cache / attention）")
        print(f"      可用显存 {d['max_alloc_gib']:.2f} GiB")

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)
    print(f"\n结果: {a.out}")


if __name__ == "__main__":
    main()
