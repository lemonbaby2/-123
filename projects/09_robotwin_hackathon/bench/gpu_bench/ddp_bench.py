# -*- coding: utf-8 -*-
"""分布式可行性测试 —— 决定这两张卡能不能组队干活

测三件事：
  1) P2P 是否可用（能不能直接 GPU→GPU 拷贝，不绕 CPU）
  2) GPU 间真实拷贝带宽（这就是梯同步的通信上限）
  3) allreduce 吞吐 + 一个模拟训练的加速比（多卡 vs 单卡）

用法：
  python3 ddp_bench.py --p2p
  torchrun --nproc_per_node=2 ddp_bench.py --ddp

判据：
  两张消费卡之间是 SYS 拓扑（跨 NUMA 的 PCIe），没有 NVLink。
  所以通信一定走 CPU 中转 + PCIe，实测带宽通常只有 2~6 GB/s。
  而 PCIe 理论：Gen4 x4 ≈ 7.9 GB/s（单向）。这就是这台机的天花板。
"""
import os
import sys
import time
import json
import argparse

import torch


def human(bw):
    return f"{bw:8.2f} GB/s"


# ============================ 1) P2P 可用性 ============================
def cmd_p2p(args):
    print("=" * 74)
    print("  P2P（GPU 直连）可用性与 GPU 间拷贝带宽")
    print("=" * 74)
    n = torch.cuda.device_count()
    if n < 2:
        print("  只有一张卡，跳过")
        return {}
    print(f"\n  P2P 访问矩阵:  {n} 张卡")
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            try:
                ok = torch.cuda.can_device_access_peer(i, j)
            except Exception:
                ok = False
            print(f"    cuda:{i} -> cuda:{j} : {'✅ 可直连' if ok else '❌ 不可（需绕 CPU 内存）'}")

    print("\n" + "-" * 74)
    print("  GPU 间拷贝带宽（这才是分布式梯度同步的物理上限）")
    print("-" * 74)
    report = {}
    sizes_mb = [16, 64, 256, 1024, 2048]
    for src_dev in range(n):
        for dst_dev in range(n):
            if src_dev == dst_dev:
                continue
            print(f"\n  cuda:{src_dev} -> cuda:{dst_dev}")
            torch.cuda.set_device(src_dev)
            res = {}
            for mb in sizes_mb:
                nelem = mb * 1024 * 1024 // 4
                try:
                    src = torch.randn(nelem, dtype=torch.float32,
                                      device=f"cuda:{src_dev}")
                    # 预热
                    for _ in range(2):
                        dst = src.to(f"cuda:{dst_dev}")
                    torch.cuda.synchronize()
                    t0 = time.time()
                    for _ in range(5):
                        dst = src.to(f"cuda:{dst_dev}")
                    torch.cuda.synchronize()
                    dt = (time.time() - t0) / 5
                    bw = mb / 1024 / dt        # GB/s（单向）
                    res[mb] = round(bw, 2)
                    print(f"      {mb:5d} MiB   {human(bw)}")
                    del src, dst
                except RuntimeError as e:
                    print(f"      {mb:5d} MiB   失败: {str(e)[:50]}")
                    res[mb] = None
                torch.cuda.empty_cache()
            report[f"{src_dev}->{dst_dev}"] = res
    return report


# ============================ 2) 分布式 allreduce ============================
def cmd_ddp(args):
    import torch.distributed as dist
    import torch.nn as nn
    import torch.optim as optim

    rank = int(os.environ.get("RANK", 0))
    world = int(os.environ.get("WORLD_SIZE", 1))
    local = int(os.environ.get("LOCAL_RANK", 0))
    torch.cuda.set_device(local)
    dist.init_process_group("nccl", rank=rank, world_size=world)
    dev = f"cuda:{local}"
    name = torch.cuda.get_device_name(local)
    print(f"[rank {rank}/{world}] {name}  ok", flush=True)

    sizes_mb = [16, 64, 256, 1024]
    report = {"world_size": world, "rank": rank, "allreduce": {}}
    if rank == 0:
        print("\n" + "-" * 74)
        print("  NCCL allReduce 吞吐（bus bandwidth）")
        print("-" * 74)
    for mb in sizes_mb:
        nelem = mb * 1024 * 1024 // 4
        t = torch.randn(nelem, dtype=torch.float32, device=dev)
        for _ in range(3):
            dist.all_reduce(t)
        torch.cuda.synchronize()
        iters = 20
        torch.cuda.synchronize()
        dist.barrier()
        t0 = time.time()
        for _ in range(iters):
            dist.all_reduce(t)
        torch.cuda.synchronize()
        dt = (time.time() - t0) / iters
        # NCCL bus bandwidth 口径
        busbw = (mb / 1024) * 2 * (world - 1) / world / dt
        report["allreduce"][mb] = round(busbw, 2)
        if rank == 0:
            print(f"      {mb:5d} MiB   busbw {human(busbw)}   "
                  f"(单次 {dt*1000:.2f} ms)")

    # ---- 模拟 DDP 训练步：ResNet-18 风格 ----
    if rank == 0:
        print("\n" + "-" * 74)
        print("  模拟 DDP 训练步（ResNet-18 / batch 32 / 224x224）")
        print("-" * 74)
    try:
        model = torch.hub.load("pytorch/vision:v0.10.0", "resnet18",
                               weights=None, verbose=False)
    except Exception:
        class ConvNet(nn.Module):
            def __init__(self):
                super().__init__()
                self.body = nn.Sequential(*[nn.Conv2d(64, 64, 3, padding=1)
                                            for _ in range(8)])
                self.head = nn.Linear(64 * 56 * 56, 1000)

            def forward(self, x):
                return self.head(self.body(x).flatten(1))
        model = ConvNet()
    model = model.to(dev)
    ddp_model = torch.nn.parallel.DistributedDataParallel(
        model, device_ids=[local])
    opt = optim.SGD(ddp_model.parameters(), lr=0.01)
    loss_fn = nn.CrossEntropyLoss()
    x = torch.randn(32, 3, 224, 224, device=dev)
    y = torch.randint(0, 1000, (32,), device=dev)

    for step in range(3):                      # 预热
        opt.zero_grad()
        loss = loss_fn(ddp_model(x), y)
        loss.backward()
        opt.step()
    torch.cuda.synchronize()
    dist.barrier()
    steps = 15
    t0 = time.time()
    for _ in range(steps):
        opt.zero_grad()
        loss = loss_fn(ddp_model(x), y)
        loss.backward()
        opt.step()
    torch.cuda.synchronize()
    dt = (time.time() - t0) / steps
    thr = 32 / dt
    report["ddp_step_ms"] = round(dt * 1000, 2)
    report["ddp_samples_per_s"] = round(thr, 1)
    if rank == 0:
        print(f"      {world} 卡: {dt*1000:7.2f} ms/step   {thr:7.1f} samples/s")

    # 单卡基准（每张卡各自跑一次，不含通信）
    for _ in range(2):
        opt.zero_grad()
        loss = loss_fn(model(x), y)
        loss.backward()
        opt.step()
    torch.cuda.synchronize()
    t0 = time.time()
    for _ in range(steps):
        opt.zero_grad()
        loss = loss_fn(model(x), y)
        loss.backward()
        opt.step()
    torch.cuda.synchronize()
    dt1 = (time.time() - t0) / steps
    report["single_step_ms"] = round(dt1 * 1000, 2)
    report["speedup"] = round(dt1 / dt, 2)
    if rank == 0:
        print(f"      单卡({name}): {dt1*1000:7.2f} ms/step   {32/dt1:7.1f} samples/s")
        print(f"\n  >>> {world} 卡加速比: {dt1/dt:.2f}x  "
              f"({'✅ 有收益' if dt1/dt > 1.3 else '⚠️ 通信吃掉收益' if dt1/dt > 0.9 else '❌ 不如单卡'})")
    dist.destroy_process_group()

    if rank == 0:
        outdir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, "ddp_result.json"),
                  "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--p2p", action="store_true")
    ap.add_argument("--ddp", action="store_true")
    a = ap.parse_args()
    if a.ddp:
        cmd_ddp(a)
    else:
        cmd_p2p(a)
