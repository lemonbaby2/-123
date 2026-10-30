# -*- coding: utf-8 -*-
"""GPU 体检套件 —— 双卡 GeForce 混合阵容实测

覆盖四件事：
  1) 显存健康（坏块 / stuck bit）—— 多种 pattern + 逐 bit walk
  2) 显存带宽 —— 顺序读写 GB/s
  3) 算力 —— FP32 / TF32 / FP16 / BF16 GEMM TFLOPS
  4) 烤机稳定性 + 功耗是否跑满 —— 满载期间采样 功耗/温度/SM频率

为什么自己写而不是直接用 FurMark：
  GeForce 卡没有 ECC，显存错误只会静默表现为脏数据，
  图形烤机软件测不出来。这套是直接对着显存做 pattern 校验，
  并且能在 WSL 里同时驱动两张不同架构的卡。

用法：
  python3 gpu_bench.py --info
  python3 gpu_bench.py --vram                # 显存全检（慢，几分钟）
  python3 gpu_bench.py --bandwidth
  python3 gpu_bench.py --compute
  python3 gpu_bench.py --stress 180          # 烤机 180 秒并采样功耗
  python3 gpu_bench.py --all --stress 120    # 全跑
"""
import os
import sys
import json
import time
import argparse
import subprocess
import threading

import torch

GPU_NAME_CACHE = {}


def smi_query():
    """一次性拿所有卡的功耗/温度/频率，返回 list[dict]"""
    try:
        out = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=index,name,power.draw,power.limit,temperature.gpu,"
             "utilization.gpu,utilization.memory,clocks.sm,clocks.max.sm,"
             "memory.used,memory.total,fan.speed",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception as e:
        return []
    rows = []
    for line in out.splitlines():
        p = [x.strip() for x in line.split(",")]
        if len(p) < 12:
            continue

        def f(v, d=float("nan")):
            try:
                return float(v)
            except (ValueError, TypeError):
                return d

        # WDDM 模式下部分消费卡的功耗读数返回 N/A，不能因为一个字段丢了整行
        try:
            rows.append(dict(
                index=int(p[0]), name=p[1],
                power_w=f(p[2]), power_limit_w=f(p[3]),
                temp_c=f(p[4]), util_gpu=f(p[5]), util_mem=f(p[6]),
                clock_sm=f(p[7]), clock_sm_max=f(p[8]),
                mem_used=f(p[9]), mem_total=f(p[10]),
                fan=f(p[11], 0.0),
            ))
        except (ValueError, IndexError):
            continue
    return rows


# ============================== 1) 设备信息 ==============================
def cmd_info(args):
    print("=" * 78)
    print("  设备信息")
    print("=" * 78)
    for i in range(torch.cuda.device_count()):
        p = torch.cuda.get_device_properties(i)
        print(f"\n  [{i}] {p.name}")
        print(f"      计算能力      : sm_{p.major}{p.minor}  ({arch_name(p.major, p.minor)})")
        print(f"      SM 数量       : {p.multi_processor_count}")
        print(f"      显存          : {p.total_memory / 1024**3:.2f} GiB")
        print(f"      SM 时钟上限   : {p.clock_rate/1000:.0f} MHz")
        print(f"      显存时钟      : {p.memory_clock_rate/1000:.0f} MHz")
        print(f"      显存位宽      : {p.memory_bus_width} bit")
        bw = 2 * p.memory_clock_rate * 1000 * p.memory_bus_width / 8 / 1e9
        print(f"      理论带宽      : {bw:.1f} GB/s")
        print(f"      L2 缓存       : {p.L2_cache_size / 1024:.0f} KiB")
        print(f"      Tensor Core   : {'是' if p.major >= 7 else '否'}")
        # 张量核心 dtype 支持探测
        sup = []
        for dtype in (torch.float16, torch.bfloat16, torch.float32):
            try:
                a = torch.zeros(16, 16, device=f"cuda:{i}", dtype=dtype)
                _ = a @ a
                sup.append(str(dtype).replace("torch.", ""))
            except Exception:
                pass
        print(f"      GEMM 支持     : {', '.join(sup)}")
        try:
            print(f"      flash/其他    : 当前 torch={torch.__version__} cuda={torch.version.cuda}")
        except Exception:
            pass
    return {}


def arch_name(major, minor):
    m = {(8, 9): "Ada Lovelace", (12, 0): "Blackwell", (8, 6): "Ampere",
         (7, 5): "Turing", (8, 0): "Ampere A100", (9, 0): "Hopper"}
    return m.get((major, minor), f"unknown_{major}{minor}")


# ============================== 2) 显存坏块检测 ==============================
def _as_int32(v):
    """torch.int32 是有符号的，0xFFFFFFFF 这类无符号写法会溢出，转成补码"""
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v > 0x7FFFFFFF else v


PATTERNS32 = [
    ("全 0",        0x00000000),
    ("全 1",        0xFFFFFFFF),
    ("交替 1010",   0xAAAAAAAA),
    ("交替 0101",   0x55555555),
    ("低半 ff",     0x0000FFFF),
    ("高半 ff",     0xFFFF0000),
    ("单 bit 低位", 0x00000001),
    ("单 bit 高位", 0x80000000),
]


def _check(buf, expect_val, tag, result, chunk_elems=32 * 1024 * 1024):
    """分块比对 —— 不能整块比，(buf != v) 会再吃一份同等大小的显存"""
    bad = 0
    first_idx = []
    n = buf.numel()
    for start in range(0, n, chunk_elems):
        seg = buf[start:start + chunk_elems]
        diff = (seg != expect_val)
        cnt = int(diff.sum().item())
        if cnt:
            bad += cnt
            if not first_idx:
                first_idx = (start + diff.nonzero(as_tuple=True)[0][:8]).tolist()
    if bad:
        result["errors"].append(dict(test=tag, bad_count=bad,
                                     first_bad_indices=first_idx))
        print(f"      ❌ {tag:<20} 错误 {bad} 个  (首错偏移 {first_idx})")
    else:
        print(f"      ✅ {tag:<20} 通过")
    result["checks"] += 1
    return bad


def cmd_vram(args):
    print("=" * 78)
    print("  显存健康检查（pattern 校验 / stuck bit）")
    print("=" * 78)
    report = {}
    for i in range(torch.cuda.device_count()):
        torch.cuda.set_device(i)
        p = torch.cuda.get_device_properties(i)
        # 按真实空闲显存分配，避免和桌面/其他进程抢导致 OOM
        frac = args.vram_frac
        free_bytes, total_bytes = torch.cuda.mem_get_info()
        nbytes = int(free_bytes * frac)
        nbytes -= nbytes % 4
        nelem = nbytes // 4
        gib = nbytes / 1024**3
        print(f"\n  [{i}] {p.name}   总 {(total_bytes/1024**3):.2f} GiB / "
              f"空闲 {(free_bytes/1024**3):.2f} GiB   测试 {gib:.2f} GiB "
              f"({frac*100:.0f}% 空闲, {nelem:,} × int32)")
        res = {"device": i, "name": p.name, "bytes": nbytes,
               "errors": [], "checks": 0}
        try:
            buf = torch.empty(nelem, dtype=torch.int32, device=f"cuda:{i}")
        except RuntimeError as e:
            print(f"      ⚠️ 分配失败: {e}")
            res["fatal"] = str(e)
            report[i] = res
            continue
        t0 = time.time()
        total_bad = 0
        for tag, val in PATTERNS32:
            buf.fill_(_as_int32(val))
            torch.cuda.synchronize()
            total_bad += _check(buf, _as_int32(val), f"pattern {tag}", res)

        # 逐 bit 走位 —— 抓 stuck bit（只对前 64 MiB 做，避免太慢）
        walk_elems = min(nelem, 64 * 1024 * 256)
        small = buf[:walk_elems]
        print(f"\n      -- 逐 bit 走位（{walk_elems*4/1024**2:.0f} MiB, 32 轮）--")
        for bit in range(32):
            val = 1 << bit
            small.fill_(_as_int32(val))
            torch.cuda.synchronize()
            if small.ne(_as_int32(val)).any().item():
                bad = small.ne(_as_int32(val)).sum().item()
                total_bad += bad
                res["errors"].append(dict(test=f"walk bit {bit}", bad_count=int(bad)))
                print(f"      ❌ bit {bit:2d} 错误 {int(bad)} 个")
        res["checks"] += 32
        print(f"      ✅ 逐 bit 走位完成")

        # 伪随机校验 —— 抓地址译码/耦合错误
        print(f"\n      -- 伪随机 pattern --")
        ref = torch.randint(-2**31, 2**31 - 1, (walk_elems,),
                            dtype=torch.int32, device=f"cuda:{i}")
        small.copy_(ref)
        torch.cuda.synchronize()
        bad = small.ne(ref).sum().item()
        res["checks"] += 1
        if bad:
            total_bad += bad
            res["errors"].append(dict(test="random", bad_count=int(bad)))
            print(f"      ❌ 随机 pattern 错误 {int(bad)} 个")
        else:
            print(f"      ✅ 随机 pattern 通过")

        dt = time.time() - t0
        res["elapsed_s"] = round(dt, 1)
        res["total_bad"] = int(total_bad)
        res["verdict"] = "PASS" if total_bad == 0 else "FAIL"
        print(f"\n  >>> [{i}] {p.name}: {res['verdict']}  "
              f"({res['checks']} 项检查, 错误 {int(total_bad)}, 耗时 {dt:.1f}s)")

        del buf, ref
        torch.cuda.empty_cache()
        report[i] = res
    return report


# ============================== 3) 显存带宽 ==============================
def cmd_bandwidth(args):
    print("=" * 78)
    print("  显存带宽")
    print("=" * 78)
    report = {}
    for i in range(torch.cuda.device_count()):
        torch.cuda.set_device(i)
        p = torch.cuda.get_device_properties(i)
        n = int(min(p.total_memory * 0.5, 2 * 1024**3)) // 4
        print(f"\n  [{i}] {p.name}")
        src = torch.empty(n, dtype=torch.float32, device=f"cuda:{i}")
        dst = torch.empty(n, dtype=torch.float32, device=f"cuda:{i}")
        src.random_()
        results = {}
        for label, op in (("写 (fill)", lambda: dst.fill_(1.0)),
                          ("读 + 写 (copy)", lambda: dst.copy_(src))):
            for _ in range(2):
                op()
            torch.cuda.synchronize()
            t0 = time.time()
            for _ in range(args.iters):
                op()
            torch.cuda.synchronize()
            dt = (time.time() - t0) / args.iters
            gb = n * 4 / 1e9
            bw = (gb if label.startswith("写") else gb * 2) / dt
            results[label] = round(bw, 1)
            print(f"      {label:<16} {bw:8.1f} GB/s")
        theory = 2 * p.memory_clock_rate * 1000 * p.memory_bus_width / 8 / 1e9
        eff = results["读 + 写 (copy)"] / theory * 100
        print(f"      理论带宽        {theory:8.1f} GB/s   实测效率 {eff:.0f}%")
        report[i] = dict(name=p.name, **results, theory_gbs=round(theory, 1),
                         efficiency_pct=round(eff, 1))
        del src, dst
        torch.cuda.empty_cache()
    return report


# ============================== 4) 算力 ==============================
def cmd_compute(args):
    print("=" * 78)
    print("  算力（GEMM TFLOPS）")
    print("=" * 78)
    report = {}
    for i in range(torch.cuda.device_count()):
        torch.cuda.set_device(i)
        p = torch.cuda.get_device_properties(i)
        print(f"\n  [{i}] {p.name}  (sm_{p.major}{p.minor})")
        res = {"name": p.name}
        cases = [(torch.float32, False, "FP32"), (torch.float32, True, "TF32"),
                 (torch.float16, False, "FP16"), (torch.bfloat16, False, "BF16")]
        m = k = n = 4096
        for dtype, tf32, label in cases:
            try:
                torch.backends.cuda.matmul.allow_tf32 = tf32
                a = torch.randn(m, k, device=f"cuda:{i}", dtype=dtype)
                b = torch.randn(k, n, device=f"cuda:{i}", dtype=dtype)
                for _ in range(3):
                    c = a @ b
                torch.cuda.synchronize()
                t0 = time.time()
                iters = 20
                for _ in range(iters):
                    c = a @ b
                torch.cuda.synchronize()
                dt = (time.time() - t0) / iters
                tflops = 2 * m * k * n / dt / 1e12
                res[label] = round(tflops, 2)
                print(f"      {label:<6} {tflops:8.2f} TFLOPS")
                del a, b, c
            except RuntimeError as e:
                res[label] = None
                print(f"      {label:<6} 不支持: {str(e)[:60]}")
            torch.cuda.empty_cache()
        torch.backends.cuda.matmul.allow_tf32 = False
        report[i] = res
    return report


# ============================== 5) 烤机 + 功耗监控 ==============================
def cmd_stress(args):
    print("=" * 78)
    print(f"  烤机稳定性 + 功耗监测（{args.stress} 秒）")
    print("=" * 78)
    devices = list(range(torch.cuda.device_count()))
    stop = threading.Event()
    samples = []

    def sampler():
        while not stop.is_set():
            for r in smi_query():
                r["t"] = time.time()
                samples.append(r)
            time.sleep(args.sample_interval)

    th = threading.Thread(target=sampler, daemon=True)
    th.start()

    workers = []
    for i in devices:
        workers.append(threading.Thread(target=_burn, args=(i, args.stress, stop),
                                        daemon=True))
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    stop.set()
    th.join(timeout=5)

    print("\n" + "-" * 78)
    print("  结果")
    print("-" * 78)
    report = {}
    for i in devices:
        rows = [s for s in samples if s["index"] == i]
        if not rows:
            continue
        loaded = [r for r in rows if r["util_gpu"] >= 90.0] or rows
        ok = lambda v: v == v          # 过滤 NaN（功耗读数 N/A 时会是 NaN）
        pw = [r["power_w"] for r in loaded if ok(r["power_w"])]
        tp = [r["temp_c"] for r in loaded if ok(r["temp_c"])]
        ck = [r["clock_sm"] for r in loaded if ok(r["clock_sm"])]
        ug = [r["util_gpu"] for r in loaded if ok(r["util_gpu"])]
        limit = rows[0]["power_limit_w"]
        pk = rows[0]["clock_sm_max"]
        tk = max(tp) if tp else float("nan")
        ckm, ckx = (min(ck), max(ck)) if ck else (float("nan"),) * 2
        if pw:
            avg_p, max_p = sum(pw) / len(pw), max(pw)
        print(f"\n  [{i}] {rows[0]['name']}")
        if pw:
            print(f"      功耗       峰值 {max_p:6.1f} W   均值 {avg_p:6.1f} W   "
                  f"上限 {limit:6.1f} W   满载率 {max_p/limit*100:5.1f}%")
        else:
            print(f"      功耗       ⚠️ 读数不可用（WDDM 限制，该卡不回报功耗），"
                  f"上限 {limit:.0f} W")
        print(f"      温度       最高 {tk:6.1f} °C  (目标墙 83°C，"
              f"{' 逼近' if tk >= 78 else ' 正常'})")
        print(f"      SM 频率    最低 {ckm:6.0f} MHz  最高 {ckx:6.0f} MHz   "
              f"理论峰值 {pk:.0f} MHz")
        drop = (1 - ckm / ckx) * 100 if ckx > 0 else 0
        print(f"      降频幅度   {drop:5.1f}%   {'⚠️ 明显降频' if drop > 8 else '✅ 稳定'}")
        print(f"      GPU 占用   均值 {sum(ug)/len(ug):5.1f}%")
        report[i] = dict(
            name=rows[0]["name"], power_limit_w=limit,
            power_avg_w=round(avg_p, 1) if pw else None,
            power_max_w=round(max_p, 1) if pw else None,
            power_readable=bool(pw),
            power_saturation_pct=round(max_p / limit * 100, 1) if pw else None,
            temp_max_c=tk, clock_min_mhz=ckm, clock_max_mhz=ckx,
            clock_peak_mhz=pk, throttle_pct=round(drop, 1),
            util_avg_pct=round(sum(ug) / len(ug), 1) if ug else 0.0,
            samples=len(rows), loaded_samples=len(loaded),
            verdict="stable" if drop <= 8 and tk < 85 else "throttling",
        )
    return report


def _burn(dev, seconds, stop):
    """单卡满载：交替打 GEMM 与显存带宽，避免只压一个单元"""
    torch.cuda.set_device(dev)
    p = torch.cuda.get_device_properties(dev)
    size = min(int(p.total_memory * 0.35) // 4, 300 * 1024 * 1024 // 4)
    k = 4096
    try:
        a = torch.randn(k, k, device=f"cuda:{dev}", dtype=torch.float16)
        b = torch.randn(k, k, device=f"cuda:{dev}", dtype=torch.float16)
        buf = torch.empty(size, dtype=torch.float32, device=f"cuda:{dev}")
    except RuntimeError:
        stop.set()
        return
    t_end = time.time() + seconds
    err = None
    n = 0
    while time.time() < t_end and not stop.is_set():
        try:
            _ = a @ b
            buf.mul_(1.0000001)
            buf.add_(0.0000001)
            n += 1
        except RuntimeError as e:
            err = str(e)
            break
    if err:
        print(f"  ❌ [{dev}] 烤机中断: {err}")
    else:
        print(f"  ✅ [{dev}] 烤机完成 {seconds}s，{n} 轮")
    del a, b, buf
    torch.cuda.empty_cache()


# ============================== main ==============================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--info", action="store_true")
    ap.add_argument("--vram", action="store_true")
    ap.add_argument("--bandwidth", action="store_true")
    ap.add_argument("--compute", action="store_true")
    ap.add_argument("--stress", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only", type=int, default=-1, help="只测某一张卡")
    ap.add_argument("--vram-frac", type=float, default=0.85)
    ap.add_argument("--iters", type=int, default=10)
    ap.add_argument("--sample-interval", type=float, default=0.5)
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "result.json"))
    args = ap.parse_args()

    if not torch.cuda.is_available():
        print("❌ CUDA 不可用")
        return 2
    print(f"torch={torch.__version__}  cuda={torch.version.cuda}  "
          f"devices={torch.cuda.device_count()}\n")

    report = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
              "torch": torch.__version__, "cuda": torch.version.cuda}
    try:
        if args.all or args.info:
            report["info"] = cmd_info(args)
        if args.all or args.vram:
            report["vram"] = cmd_vram(args)
        if args.all or args.bandwidth:
            report["bandwidth"] = cmd_bandwidth(args)
        if args.all or args.compute:
            report["compute"] = cmd_compute(args)
        if args.stress > 0:
            report["stress"] = cmd_stress(args)
    finally:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n结果已写入: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
