# -*- coding: utf-8 -*-
"""GPU 体检 —— CuPy 版（体积只有 torch 的 1/20，用于快速取数据）

覆盖：显存坏块 / 显存带宽 / GEMM 算力 / 烤机功耗采样。
结果与 torch 版 gpu_bench.py 口径一致，可互相校准。

用法：
  python cupy_bench.py --info
  python cupy_bench.py --vram
  python cupy_bench.py --bandwidth
  python cupy_bench.py --compute
  python cupy_bench.py --stress 120
  python cupy_bench.py --all --stress 120
"""
import os
import json
import time
import argparse
import subprocess
import threading

import cupy as cp
import numpy as np


def sync():
    cp.cuda.Stream.null.synchronize()


# ============================ 设备信息 ============================
def cmd_info():
    print("=" * 76)
    print("  设备信息（CuPy）")
    print("=" * 76)
    n = cp.cuda.runtime.getDeviceCount()
    info = {}
    for i in range(n):
        d = cp.cuda.Device(i)
        attr = d.attributes
        mem_total = cp.cuda.runtime.memGetInfo()[1]
        print(f"\n  [{i}] {d.attributes['Name'] if 'Name' in attr else ''}")
        with d:
            cc = cp.cuda.runtime.getDeviceProperties(i)['generated_ptr'] if False else None
        # 用 cupy 自带接口拿能力集
        try:
            import cupy_backends
            comp = cp.cuda.get_compute_capability(i)
        except Exception:
            comp = "?"
        print(f"      计算能力      : {comp}")
        print(f"      SM 数量       : {attr.get('MultiprocessorCount', '?')}")
        print(f"      显存          : {mem_total/1024**3:.2f} GiB")
        print(f"      SM 时钟上限   : {attr.get('ClockRate', 0)/1000:.0f} MHz")
        print(f"      显存时钟      : {attr.get('MemoryClockRate', 0)/1000:.0f} MHz")
        print(f"      显存位宽      : {attr.get('GlobalMemoryBusWidth', '?')} bit")
        bw = 2 * attr.get('MemoryClockRate', 0) * 1000 * \
            attr.get('GlobalMemoryBusWidth', 0) / 8 / 1e9
        print(f"      理论带宽      : {bw:.1f} GB/s")
        free, total = cp.cuda.runtime.memGetInfo()
        print(f"      当前空闲显存  : {free/1024**3:.2f} GiB")
        info[i] = dict(name=str(attr.get('Name', i)), cc=str(comp),
                       sm=attr.get('MultiprocessorCount'),
                       mem_gib=round(mem_total / 1024**3, 2),
                       theory_bw_gbs=round(bw, 1))
    return info


# ============================ 显存坏块 ============================
PATTERNS = [("全 0", 0), ("全 1", -1), ("0xAAAA...", int("0xAAAAAAAA", 16)),
            ("0x5555...", int("0x55555555", 16)),
            ("0x0F0F...", int("0x0F0F0F0F", 16)),
            ("单 bit 低位", 1), ("单 bit 高位", 1 << 31)]


def cmd_vram(args):
    print("=" * 76)
    print("  显存健康检查（pattern 校验 / 逐 bit 走位）")
    print("=" * 76)
    report = {}
    n = cp.cuda.runtime.getDeviceCount()
    for i in range(n):
        d = cp.cuda.Device(i)
        with d:
            free, total = cp.cuda.runtime.memGetInfo()
            usable = int((total - 512 * 1024**2) * args.vram_frac)
            nelem = usable // 4
            print(f"\n  [{i}] 可测 {usable/1024**3:.2f} GiB "
                  f"({nelem:,} × int32)")
            res = {"checks": 0, "errors": [], "total_bad": 0}
            try:
                buf = cp.empty(nelem, dtype=cp.int32)
            except Exception as e:
                print(f"      ⚠️ 分配失败: {e}")
                res["fatal"] = str(e)
                report[i] = res
                continue
            t0 = time.time()
            total_bad = 0
            for tag, val in PATTERNS:
                buf[:] = np.int32(val)
                sync()
                bad = int(cp.sum(buf != np.int32(val)))
                res["checks"] += 1
                if bad:
                    idx = cp.nonzero(buf != np.int32(val))[0][:8]
                    total_bad += bad
                    res["errors"].append(dict(test=tag, bad=bad,
                                              indices=[int(x) for x in idx]))
                    print(f"      ❌ {tag:<12} 错误 {bad}")
                else:
                    print(f"      ✅ {tag:<12} 通过")

            # 逐 bit 走位（限前 64 MiB，避免太慢）
            walk_N = min(nelem, 64 * 256 * 1024)
            small = buf[:walk_N]
            print(f"\n      -- 逐 bit 走位（{walk_N*4/1024**2:.0f} MiB × 32）--")
            walk_bad = 0
            for bit in range(32):
                v = np.int32(1 << bit)
                small[:] = v
                sync()
                if bool(cp.any(small != v)):
                    b = int(cp.sum(small != v))
                    walk_bad += b
                    res["errors"].append(dict(test=f"walk bit {bit}", bad=b))
                    print(f"      ❌ bit {bit:2d} 错误 {b}")
            res["checks"] += 32
            print(f"      ✅ 逐 bit 走位完成")
            total_bad += walk_bad

            # 伪随机
            ref = cp.asarray(np.random.randint(-2**31, 2**31 - 1, walk_N)
                             .astype(np.int32))
            small[:] = ref
            sync()
            rb = int(cp.sum(small != ref))
            res["checks"] += 1
            if rb:
                total_bad += rb
                res["errors"].append(dict(test="random", bad=rb))
                print(f"      ❌ 伪随机 pattern 错误 {rb}")
            else:
                print(f"      ✅ 伪随机 pattern 通过")

            dt = time.time() - t0
            res["total_bad"] = total_bad
            res["elapsed_s"] = round(dt, 1)
            res["verdict"] = "PASS" if total_bad == 0 else "FAIL"
            print(f"\n  >>> [{i}] {res['verdict']}  "
                  f"({res['checks']} 项, 错误 {total_bad}, {dt:.1f}s)")
            del buf, ref
            cp.get_default_memory_pool().free_all_blocks()
            report[i] = res
    return report


# ============================ 带宽 ============================
def cmd_bandwidth(args):
    print("=" * 76)
    print("  显存带宽")
    print("=" * 76)
    report = {}
    n = cp.cuda.runtime.getDeviceCount()
    for i in range(n):
        with cp.cuda.Device(i):
            free, total = cp.cuda.runtime.memGetInfo()
            N = int(min(total * 0.4, 2 * 1024**3) // 4)
            print(f"\n  [{i}] {N*4/1024**3:.2f} GiB 缓冲")
            a = cp.random.random(N, dtype=cp.float32)
            b = cp.empty(N, dtype=cp.float32)
            out = {}
            for tag, fn, mult in (("写 (fill)", lambda: b.__setitem__(slice(None), 1.0), 1),
                                  ("读+写 (copy)", lambda: b.__setitem__(slice(None), a), 2)):
                for _ in range(2):
                    fn()
                sync()
                t0 = time.time()
                for _ in range(args.iters):
                    fn()
                sync()
                dt = (time.time() - t0) / args.iters
                bw = N * 4 * mult / dt / 1e9
                out[tag] = round(bw, 1)
                print(f"      {tag:<14} {bw:8.1f} GB/s")
            del a, b
            cp.get_default_memory_pool().free_all_blocks()
            report[i] = out
    return report


# ============================ 算力 ============================
def cmd_compute(args):
    print("=" * 76)
    print("  GEMM 算力（TFLOPS）")
    print("=" * 76)
    report = {}
    n = cp.cuda.runtime.getDeviceCount()
    for i in range(n):
        with cp.cuda.Device(i):
            print(f"\n  [{i}]")
            res = {}
            for dtype, label in ((cp.float32, "FP32"), (cp.float16, "FP16")):
                try:
                    m = k = nn = 4096
                    a = cp.random.random((m, k), dtype=dtype)
                    b = cp.random.random((k, nn), dtype=dtype)
                    for _ in range(3):
                        c = cp.matmul(a, b)
                    sync()
                    iters = 20
                    t0 = time.time()
                    for _ in range(iters):
                        c = cp.matmul(a, b)
                    sync()
                    dt = (time.time() - t0) / iters
                    tf = 2 * m * k * nn / dt / 1e12
                    res[label] = round(tf, 2)
                    print(f"      {label:<6} {tf:8.2f} TFLOPS")
                    del a, b, c
                except Exception as e:
                    res[label] = None
                    print(f"      {label:<6} 失败: {str(e)[:50]}")
                cp.get_default_memory_pool().free_all_blocks()
            report[i] = res
    return report


# ============================ 烤机 ============================
def _smi():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,power.draw,power.limit,"
             "temperature.gpu,utilization.gpu,clocks.sm,clocks.max.sm",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return []
    rows = []
    for ln in out.splitlines():
        p = [x.strip() for x in ln.split(",")]
        if len(p) < 8:
            continue
        try:
            rows.append(dict(index=int(p[0]), name=p[1], power=float(p[2]),
                             limit=float(p[3]), temp=float(p[4]),
                             util=float(p[5]), clock=float(p[6]),
                             clock_max=float(p[7])))
        except ValueError:
            pass
    return rows


def cmd_stress(args):
    print("=" * 76)
    print(f"  烤机 + 功耗监测（{args.stress}s）")
    print("=" * 76)
    n = cp.cuda.runtime.getDeviceCount()
    stop = threading.Event()
    samples = []

    def sampler():
        while not stop.is_set():
            samples.extend(_smi())
            time.sleep(args.sample_interval)

    def burn(dev, seconds):
        with cp.cuda.Device(dev):
            try:
                a = cp.random.random((4096, 4096), dtype=cp.float16)
                b = cp.random.random((4096, 4096), dtype=cp.float16)
                free, total = cp.cuda.runtime.memGetInfo()
                nfloat = int(total * 0.25 // 4)
                buf = cp.empty(nfloat, dtype=cp.float32)
            except Exception as e:
                print(f"  ❌ [{dev}] 初始化失败: {e}")
                stop.set()
                return
            t_end = time.time() + seconds
            cnt = 0
            try:
                while time.time() < t_end and not stop.is_set():
                    _ = cp.matmul(a, b)
                    buf *= cp.float32(1.0000001)
                    buf += cp.float32(0.0000001)
                    cnt += 1
            except Exception as e:
                print(f"  ❌ [{dev}] 中断: {e}")
                return
            sync()
            print(f"  ✅ [{dev}] 完成 {seconds}s / {cnt} 轮")
            del a, b, buf
            cp.get_default_memory_pool().free_all_blocks()

    th = threading.Thread(target=sampler, daemon=True)
    th.start()
    workers = [threading.Thread(target=burn, args=(i, args.stress), daemon=True)
               for i in range(n)]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    stop.set()
    th.join(timeout=5)

    print("\n" + "-" * 76)
    report = {}
    for i in range(n):
        rows = [s for s in samples if s["index"] == i]
        if not rows:
            continue
        pw = [r["power"] for r in rows]
        tp = [r["temp"] for r in rows]
        ck = [r["clock"] for r in rows]
        ug = [r["util"] for r in rows]
        lim = rows[0]["limit"]
        maxp, avgp = max(pw), sum(pw) / len(pw)
        cmin, cmax, cpk = min(ck), max(ck), rows[0]["clock_max"]
        print(f"\n  [{i}] {rows[0]['name']}")
        print(f"      功耗        峰值 {maxp:6.1f} W   均值 {avgp:6.1f} W   "
              f"上限 {lim:6.1f} W   满载率 {maxp/lim*100:5.1f}%")
        print(f"      温度        最高 {max(tp):6.1f} °C")
        print(f"      SM 频率     最低 {cmin:6.0f}  最高 {cmax:6.0f}  "
              f"峰值 {cpk:.0f} MHz")
        drop = (1 - cmin / cmax) * 100 if cmax > 0 else 0
        print(f"      降频        {drop:5.1f}%  "
              f"{'⚠️ 明显' if drop > 8 else '✅ 稳定'}")
        print(f"      占用        均值 {sum(ug)/len(ug):5.1f}%")
        report[i] = dict(name=rows[0]["name"], power_limit_w=lim,
                         power_max_w=round(maxp, 1), power_avg_w=round(avgp, 1),
                         saturation_pct=round(maxp / lim * 100, 1),
                         temp_max_c=max(tp), clock_min_mhz=cmin,
                         clock_max_mhz=cmax, throttle_pct=round(drop, 1),
                         util_avg=round(sum(ug) / len(ug), 1),
                         verdict="stable" if drop <= 8 and max(tp) < 85 else "throttling")
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--info", action="store_true")
    ap.add_argument("--vram", action="store_true")
    ap.add_argument("--bandwidth", action="store_true")
    ap.add_argument("--compute", action="store_true")
    ap.add_argument("--stress", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--vram-frac", type=float, default=0.85)
    ap.add_argument("--iters", type=int, default=10)
    ap.add_argument("--sample-interval", type=float, default=0.5)
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "result_cupy.json"))
    a = ap.parse_args()

    print(f"cupy={cp.__version__}  cuda_runtime={cp.cuda.runtime.runtimeGetVersion()}\n")
    rep = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "cupy": cp.__version__}
    try:
        if a.all or a.info:
            rep["info"] = cmd_info()
        if a.all or a.vram:
            rep["vram"] = cmd_vram(a)
        if a.all or a.bandwidth:
            rep["bandwidth"] = cmd_bandwidth(a)
        if a.all or a.compute:
            rep["compute"] = cmd_compute(a)
        if a.stress > 0:
            rep["stress"] = cmd_stress(a)
    finally:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2, ensure_ascii=False)
        print(f"\n结果: {a.out}")


if __name__ == "__main__":
    main()
