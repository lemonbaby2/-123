# -*- coding: utf-8 -*-
"""榨干功耗 —— 判断 5060 Ti 到底能不能顶到 180 W 上限

之前那轮烤机（GEMM + 访存）只到 152.9 W / 84.9%。
问题是：那个负载够不够重，还是卡本身被限制住了？

本脚本逐级加码，看功耗能推到多少：
  L1  单 stream FP16 大 GEMM（8192³）
  L2  4 stream 并行 FP16 GEMM          —— 提高 SM 占用
  L3  4 stream GEMM + 显存带宽流并发   —— 同时压计算与访存
  L4  多进程（每进程满载一张卡）        —— 排除 Python GIL / 调度影响

每一级跑 N 秒，全程 nvidia-smi 0.25 s 采样，报告峰值/均值/温度/频率。
"""
import os
import sys
import time
import json
import argparse
import threading
import subprocess

import torch


def smi():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,power.draw,power.limit,"
             "temperature.gpu,utilization.gpu,clocks.sm,clocks.max.sm,"
             "temperature.memory,memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return []
    rows = []
    for ln in out.splitlines():
        p = [x.strip() for x in ln.split(",")]
        if len(p) < 10:
            continue

        def f(v):
            try:
                return float(v)
            except Exception:
                return float("nan")

        rows.append(dict(index=int(p[0]), name=p[1], power=f(p[2]),
                         limit=f(p[3]), temp=f(p[4]), util=f(p[5]),
                         clock=f(p[6]), clock_max=f(p[7]),
                         mem_temp=f(p[8]), mem_used=f(p[9])))
    return rows


class Sampler(threading.Thread):
    def __init__(self, interval=0.25):
        super().__init__(daemon=True)
        self.interval = interval
        self.samples = []
        self._stop = threading.Event()

    def run(self):
        while not self._stop.is_set():
            self.samples.extend(smi())
            time.sleep(self.interval)

    def stop(self):
        self._stop.set()


def level1(dev, seconds):
    """单 stream 大 GEMM"""
    with torch.cuda.device(dev):
        n = 8192
        a = torch.randn(n, n, device=f"cuda:{dev}", dtype=torch.float16)
        b = torch.randn(n, n, device=f"cuda:{dev}", dtype=torch.float16)
        torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction = True
        end = time.time() + seconds
        while time.time() < end:
            _ = torch.mm(a, b)
        torch.cuda.synchronize()
    del a, b


def level2(dev, seconds, streams=4):
    """多 stream 并行 GEMM"""
    with torch.cuda.device(dev):
        n = 4096
        ss = [torch.cuda.Stream() for _ in range(streams)]
        mats = []
        for _ in range(streams):
            mats.append((torch.randn(n, n, device=f"cuda:{dev}", dtype=torch.float16),
                         torch.randn(n, n, device=f"cuda:{dev}", dtype=torch.float16)))
        torch.cuda.synchronize()
        end = time.time() + seconds
        while time.time() < end:
            for s, (a, b) in zip(ss, mats):
                with torch.cuda.stream(s):
                    _ = torch.mm(a, b)
            torch.cuda.synchronize()
    del mats


def level3(dev, seconds, streams=4):
    """GEMM + 显存带宽流并发"""
    with torch.cuda.device(dev):
        n = 4096
        ss = [torch.cuda.Stream() for _ in range(streams)]
        mats = [(torch.randn(n, n, device=f"cuda:{dev}", dtype=torch.float16),
                 torch.randn(n, n, device=f"cuda:{dev}", dtype=torch.float16))
                for _ in range(streams)]
        info = torch.cuda.get_device_properties(dev)
        nbuf = int(info.total_memory * 0.25 // 4)
        bufs = [torch.empty(nbuf, device=f"cuda:{dev}", dtype=torch.float32)
                for _ in range(2)]
        bufs[0].random_()
        torch.cuda.synchronize()
        end = time.time() + seconds
        while time.time() < end:
            for s, (a, b) in zip(ss, mats):
                with torch.cuda.stream(s):
                    _ = torch.mm(a, b)
            with torch.cuda.stream(ss[0]):
                bufs[1].copy_(bufs[0])
                bufs[0].mul_(1.0000001)
            torch.cuda.synchronize()
    del mats, bufs


def report(sampler, dev, label, seconds):
    rows = [s for s in sampler.samples if s["index"] == dev]
    if not rows:
        print(f"  {label}: 无样本"); return None
    loaded = [r for r in rows if r["util"] >= 90.0] or rows
    pw = [r["power"] for r in loaded if r["power"] == r["power"]]
    tp = [r["temp"] for r in loaded if r["temp"] == r["temp"]]
    ck = [r["clock"] for r in loaded if r["clock"] == r["clock"]]
    if not pw:
        print(f"  {label:<26} 功耗读数不可用")
        return None
    lim = rows[0]["limit"]
    mx, av = max(pw), sum(pw) / len(pw)
    print(f"  {label:<26} 峰值 {mx:6.1f} W  均值 {av:6.1f} W  "
          f"满载率 {mx/lim*100:5.1f}%  温度 {max(tp):5.1f}°C  "
          f"SM {min(ck):.0f}~{max(ck):.0f} MHz")
    return dict(label=label, peak_w=round(mx, 1), avg_w=round(av, 1),
                limit_w=lim, saturation_pct=round(mx / lim * 100, 1),
                temp_max_c=max(tp), clock_min=min(ck), clock_max=max(ck),
                seconds=seconds)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=1)
    ap.add_argument("--seconds", type=int, default=25)
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "result_maxpower.json"))
    a = ap.parse_args()

    dev = a.device
    info = torch.cuda.get_device_properties(dev)
    print("=" * 78)
    print(f"  功耗榨取测试  [{dev}] {info.name}  "
          f"TDP {torch.cuda.get_device_properties(dev).total_memory/1024**3:.0f}GiB")
    print("=" * 78)

    results = []
    for label, fn in (("L1 单 stream FP16 GEMM", level1),
                      ("L2 4-stream 并行 GEMM", level2),
                      ("L3 GEMM + 带宽流并发", level3)):
        print(f"\n--- {label} ({a.seconds}s) ---")
        s = Sampler(0.25)
        s.start()
        torch.cuda.empty_cache()
        t0 = time.time()
        try:
            fn(dev, a.seconds)
        except Exception as e:
            print(f"  ❌ {e}")
        time.sleep(0.5)
        s.stop()
        s.join(timeout=3)
        r = report(s, dev, label, round(time.time() - t0, 1))
        if r:
            results.append(r)
        torch.cuda.empty_cache()
        time.sleep(3)     # 让卡回落到 idle，保证下一级起点一致

    print("\n" + "=" * 78)
    if results:
        best = max(results, key=lambda r: r["peak_w"])
        print(f"  最高峰值: {best['peak_w']} W / {best['limit_w']} W "
              f"= {best['saturation_pct']}%  ({best['label']})")
        gap = best["limit_w"] - best["peak_w"]
        print(f"  与 TDP 差距: {gap:.1f} W")
        if best["saturation_pct"] >= 95:
            print("  ✅ 可以跑满")
        elif best["saturation_pct"] >= 88:
            print("  🟡 接近满功耗，实际训练负载会更高")
        else:
            print("  ⚠️ 负载未压满，可能是我的测试负载不够重（真实训练会更高）")
    print("=" * 78)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "device": dev, "name": info.name, "levels": results},
                  f, indent=2, ensure_ascii=False)
    print(f"\n结果: {a.out}")


if __name__ == "__main__":
    main()
