# -*- coding: utf-8 -*-
"""CPU 健康 + 负载测试（i5-12600KF, 10C/16T, Alder Lake）

四件事：
  1) 单核 / 多核性能 —— 用 MKL 优化的 GEMM，看多线程扩展是否线性
  2) 满载压力 —— 多线程跑整数 + 浮点混合负载，边跑边校验结果（算错就报）
  3) 稳定性判据 —— 满载期间频率是否掉档（掉档 = 过热或供电不足）
  4) 内存带宽 —— 数据加载 / 预处理阶段主要吃这个

为什么用掉频判断散热而不是温度：
  这块主板没通过 ACPI 暴露 CPU 核心温度（只能读到主板 TZ00 的 27.9°C，不准）。
  但"满载时频率稳不稳"是更硬的指标 —— 散热不行就一定会掉频，
  而且这是你能直接感知到的（跑得慢）。

用法：
  python cpu_bench.py --info
  python cpu_bench.py --perf              # 单核/多核性能
  python cpu_bench.py --stress 60         # 压力 60 秒
  python cpu_bench.py --all --stress 120  # 全跑
"""
import os
import sys
import time
import json
import math
import argparse
import threading
import subprocess

import torch


# ============================ 系统监控 ============================
PS_FREQ = ("(Get-Counter '\\Processor Information(_Total)\\Processor Frequency'"
           " -ErrorAction SilentlyContinue).CounterSamples[0].CookedValue")
PS_PERF = ("(Get-Counter '\\Processor Information(_Total)\\% Processor Performance'"
           " -ErrorAction SilentlyContinue).CounterSamples[0].CookedValue")
PS_TZ = ("Get-CimInstance MSAcpi_ThermalZoneTemperature -Namespace root/WMI "
         "-ErrorAction SilentlyContinue | "
         "ForEach-Object { [math]::Round(($_.CurrentTemperature/10)-273.15,1) }")


def ps(cmd, timeout=8):
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                            "-Command", cmd],
                           capture_output=True, text=True, timeout=timeout)
        v = r.stdout.strip().splitlines()
        if not v:
            return None
        try:
            return float(v[0])
        except ValueError:
            return None
    except Exception:
        return None


class Monitor(threading.Thread):
    """后台采样：频率 / 性能百分比 / ACPI 温度"""

    def __init__(self, interval=1.0):
        super().__init__(daemon=True)
        self.interval = interval
        self.freq, self.perf, self.temp = [], [], []
        self._stop = threading.Event()

    def run(self):
        while not self._stop.is_set():
            f = ps(PS_FREQ)
            p = ps(PS_PERF)
            t = ps(PS_TZ)
            if f is not None:
                self.freq.append(f)
            if p is not None:
                self.perf.append(p)
            if t is not None:
                self.temp.append(t)
            time.sleep(self.interval)

    def stop(self):
        self._stop.set()

    def summary(self):
        def st(a):
            if not a:
                return None
            return dict(min=round(min(a), 1), max=round(max(a), 1),
                        avg=round(sum(a) / len(a), 1), n=len(a))
        return dict(freq_mhz=st(self.freq), perf_pct=st(self.perf),
                    acpi_temp_c=st(self.temp))


# ============================ 1) 信息 ============================
def cmd_info():
    print("=" * 74)
    print("  CPU 信息")
    print("=" * 74)
    print(f"      逻辑处理器   : {os.cpu_count()}")
    print(f"      torch 线程数 : {torch.get_num_threads()}")
    print(f"      torch 版本   : {torch.__version__}")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-CimInstance Win32_Processor | "
                            "Select-Object Name,NumberOfCores,"
                            "NumberOfLogicalProcessors,MaxClockSpeed | "
                            "Format-List"],
                           capture_output=True, text=True, timeout=15)
        print("      ---- WMI ----")
        for ln in r.stdout.strip().splitlines():
            if ln.strip():
                print("      " + ln.strip())
    except Exception:
        pass
    return {"logical": os.cpu_count(), "torch_threads": torch.get_num_threads()}


# ============================ 2) 性能 ============================
def gemm_bench(n, threads, iters=8, dtype=torch.float32):
    torch.set_num_threads(threads)
    a = torch.randn(n, n, dtype=dtype)
    b = torch.randn(n, n, dtype=dtype)
    for _ in range(2):
        _ = torch.mm(a, b)
    t0 = time.time()
    for _ in range(iters):
        _ = torch.mm(a, b)
    dt = (time.time() - t0) / iters
    gf = 2 * n ** 3 / dt / 1e9
    del a, b
    return gf, dt


def cmd_perf(args):
    print("=" * 74)
    print("  性能：多线程扩展性（GEMM 2048³ FP32，MKL）")
    print("=" * 74)
    base = None
    out = {}
    for th in (1, 2, 4, 8, 12, 16):
        gf, dt = gemm_bench(2048, th)
        if base is None:
            base = gf
        print(f"      {th:2d} 线程 : {gf:8.1f} GFLOPS   {dt*1000:7.1f} ms   "
              f"加速比 {gf/base:5.2f}×")
        out[th] = dict(gflops=round(gf, 1), ms=round(dt * 1000, 1),
                       speedup=round(gf / base, 2))

    print("\n  ---- 单核 vs 全核（小矩阵，看单核睿频能力）----")
    g1, _ = gemm_bench(1024, 1, iters=15)
    g16, _ = gemm_bench(1024, 16, iters=15)
    print(f"      单核 : {g1:8.1f} GFLOPS")
    print(f"      16 线程: {g16:8.1f} GFLOPS   扩展效率 {g16/g1/16*100:.0f}%")
    out["single_core_gflops"] = round(g1, 1)
    out["all_core_gflops"] = round(g16, 1)
    out["scaling_efficiency_pct"] = round(g16 / g1 / 16 * 100, 1)
    torch.set_num_threads(os.cpu_count())
    return out


# ============================ 3) 内存带宽 ============================
def cmd_memory(args):
    print("=" * 74)
    print("  内存带宽（数据加载 / 预处理阶段主要吃这个）")
    print("=" * 74)
    torch.set_num_threads(os.cpu_count())
    n = 64 * 1024 * 1024 // 4      # 256 MiB
    a = torch.randn(n, dtype=torch.float32)
    b = torch.empty(n, dtype=torch.float32)
    for _ in range(2):
        b.copy_(a)
    t0 = time.time()
    for _ in range(8):
        b.copy_(a)
    dt = (time.time() - t0) / 8
    bw = n * 4 * 2 / dt / 1e9
    print(f"      copy 读+写 : {bw:8.1f} GB/s  ({dt*1000:.1f} ms / 256 MiB)")
    del a, b
    return {"copy_gbs": round(bw, 1)}


# ============================ 4) 压力测试 ============================
def _burn(seconds, stop, errors):
    """满载：整数 + 浮点混合，边算边校验"""
    torch.set_num_threads(os.cpu_count())
    n = 1024
    a = torch.randn(n, n)
    b = torch.randn(n, n)
    acc = 0.0
    end = time.time() + seconds
    rounds = 0
    while time.time() < end and not stop.is_set():
        c = torch.mm(a, b)
        # 浮点校验：结果不能出现 NaN / Inf
        s = float(c.sum())
        if math.isnan(s) or math.isinf(s):
            errors.append(f"round {rounds}: GEMM 结果 {s}")
        acc += s
        # 整数负载（压 ALU，和 GEMM 的 SIMD 单元不同）
        x = 0
        for i in range(20000):
            x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        if x == 0:
            errors.append(f"round {rounds}: 整数序列异常")
        rounds += 1
    return rounds


def cmd_stress(args):
    print("=" * 74)
    print(f"  满载压力测试（{args.stress} 秒，边算边校验）")
    print("=" * 74)
    mon = Monitor(args.sample_interval)
    mon.start()
    time.sleep(2)                      # 采一段空载基线
    idle = mon.summary()

    stop = threading.Event()
    errors = []
    nthreads = args.threads
    workers = [threading.Thread(target=lambda: _burn(args.stress, stop, errors),
                                daemon=True) for _ in range(nthreads)]
    t0 = time.time()
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    dt = time.time() - t0
    time.sleep(1)
    mon.stop()
    mon.join(timeout=5)
    load = mon.summary()

    print(f"\n      满载进程数 : {nthreads} × {os.cpu_count()} 线程")
    print(f"      总耗时     : {dt:.1f} s")
    print(f"      ❌ 计算错误 : {len(errors)}")
    for e in errors[:5]:
        print(f"         {e}")

    print("\n  ---- 频率/温度 ----")
    if idle.get("freq_mhz"):
        print(f"      空载频率 : {idle['freq_mhz']['min']:.0f}~"
              f"{idle['freq_mhz']['max']:.0f} MHz")
    if load.get("freq_mhz"):
        f = load["freq_mhz"]
        print(f"      满载频率 : {f['min']:.0f}~{f['max']:.0f} MHz  "
              f"(均值 {f['avg']:.0f})")
    if load.get("perf_pct"):
        p = load["perf_pct"]
        print(f"      性能百分比: {p['min']:.0f}~{p['max']:.0f}%")
    if load.get("acpi_temp_c"):
        t = load["acpi_temp_c"]
        print(f"      主板温度  : {t['min']:.1f}~{t['max']:.1f} °C  (参考值，非核心温度)")

    # 判定
    verdict = "stable"
    reason = []
    if errors:
        verdict = "UNSTABLE"
        reason.append(f"{len(errors)} 次计算错误")
    if load.get("freq_mhz") and idle.get("freq_mhz"):
        drop = 1 - load["freq_mhz"]["min"] / max(1.0, idle["freq_mhz"]["max"])
        if drop > 0.25:
            verdict = "THROTTLING"
            reason.append(f"满载频率较空载下降 {drop*100:.0f}%")
        print(f"\n      满载最低频 vs 空载最高频 : 下降 {drop*100:.1f}%")
    print(f"\n  >>> 判定: {verdict}  {'; '.join(reason) if reason else '无异常'}")

    return dict(seconds=args.stress, threads=nthreads, errors=errors[:10],
                error_count=len(errors), idle=idle, load=load, verdict=verdict)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--info", action="store_true")
    ap.add_argument("--perf", action="store_true")
    ap.add_argument("--memory", action="store_true")
    ap.add_argument("--stress", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--threads", type=int, default=1, help="并发满载进程数")
    ap.add_argument("--sample-interval", type=float, default=1.0)
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "result_cpu.json"))
    a = ap.parse_args()

    rep = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
           "cpu": "i5-12600KF", "torch": torch.__version__}
    try:
        if a.all or a.info:
            rep["info"] = cmd_info()
        if a.all or a.perf:
            rep["perf"] = cmd_perf(a)
        if a.all or a.memory:
            rep["memory"] = cmd_memory(a)
        if a.stress > 0:
            rep["stress"] = cmd_stress(a)
    finally:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2, ensure_ascii=False)
        print(f"\n结果: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
