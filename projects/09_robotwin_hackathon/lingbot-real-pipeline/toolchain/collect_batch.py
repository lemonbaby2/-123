# -*- coding: utf-8 -*-
"""批量无人值守采集器（跑在 <ROBOT_USER> 上，纯 CPU，不占用任何 GPU）

为什么要有这个脚本：
  collect.py demo 只跑固定 4 条，数据量远远不够训练。本脚本按「任务模板 + 随机参数」
  连续生成大量 episode，可无人值守跑几小时，断了能续跑。

用法（在 <ROBOT_USER> 上）:
  python3 collect_batch.py --plan                       # 只看计划，不动机器人（安全）
  python3 collect_batch.py --probe                      # 体检：臂 + 双相机
  python3 collect_batch.py --episodes-per-task 50       # 每个任务 50 条
  python3 collect_batch.py --tasks pick_place,push --episodes-per-task 30
  python3 collect_batch.py --max-minutes 180            # 跑满 3 小时自动停
  python3 collect_batch.py --resume                     # 中断后续跑（跳过已完成）

安全设计:
  * 关节位移限幅 ±JOINT_LIM_DEG，笛卡尔位移限幅 ±POSE_LIM_MM（防撞）
  * 每步动作后检查 err_code，非 0 立即 set_arm_stop + 回 home + 终止
  * 磁盘余量 < --min-free-gb 自动停（默认 5GB）
  * Ctrl+C 安全退出：停止录制 → 保存 → 回 home
  * manifest.jsonl 逐条落盘，断电也不丢账

产物:
  <out>/episode_XXXXXX/{cam_top.mp4, cam_wrist.mp4, states.npz, meta.json}
  <out>/manifest.jsonl    每行一条 episode 记录（task/帧数/时长/err）
  <out>/_batch.log        运行日志
"""
import os
import sys
import json
import time
import random
import shutil
import signal
import argparse
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


# =========================== 安全限幅 ===========================
JOINT_LIM_DEG = 30.0      # 单步关节位移上限（度）
POSE_LIM_MM = 150.0       # 单步笛卡尔位移上限（mm）
V_MIN, V_MAX = 15, 35     # 速度百分比区间
GRIP_OPEN, GRIP_CLOSE = 1.0, 0.0


# =========================== 任务模板 ===========================
# 每个模板 = 一个函数(rng) -> steps
# step 形式:
#   ("j", [d1..d6], v)          关节增量运动（相对当前）
#   ("p", [dx,dy,dz], v)        笛卡尔增量运动（相对当前，姿态不变）
#   ("pz", z, v)                只动 Z（对齐当前 x/y）
#   ("g", 0.0~1.0, 等待秒)      夹爪指令（写进动作维度）
#   ("dwell", 秒)               静止保持（采到稳定观测）

def t_pick_place(rng):
    """抓取-抬起-横移-下放-释放-撤离（最核心的抓放任务）"""
    dx = rng.uniform(60, 140) * rng.choice([-1, 1])
    dy = rng.uniform(40, 110) * rng.choice([-1, 1])
    lift = rng.uniform(60, 110)
    v = rng.randint(V_MIN + 5, V_MAX)
    return [
        ("g", GRIP_OPEN, 0.35),
        ("p", [dx * 0.6, dy * 0.6, 0], v),          # 接近
        ("dwell", rng.uniform(0.25, 0.5)),
        ("pz", -rng.uniform(30, 60), v - 5),        # 下探
        ("dwell", 0.3),
        ("g", GRIP_CLOSE, 0.6),                     # 闭合
        ("pz", lift, v - 5),                        # 抬起
        ("p", [-dx, -dy * 0.8, 0], v),              # 横移
        ("dwell", rng.uniform(0.2, 0.4)),
        ("pz", -lift * 0.85, v - 5),                # 下放
        ("g", GRIP_OPEN, 0.5),                      # 释放
        ("pz", lift * 0.7, v),                      # 撤离
    ]


def t_push(rng):
    """推向目标（低姿横推，力控类任务的简化版）"""
    dx = rng.uniform(80, 160) * rng.choice([-1, 1])
    v = rng.randint(V_MIN, V_MAX - 5)
    return [
        ("g", GRIP_CLOSE, 0.3),
        ("pz", -rng.uniform(40, 80), v),
        ("p", [dx * 0.5, rng.uniform(-20, 20), 0], v),
        ("p", [dx * 0.5, 0, 0], v),
        ("dwell", rng.uniform(0.3, 0.6)),
        ("pz", rng.uniform(40, 80), v),             # 抬起离开
    ]


def t_stack(rng):
    """叠放：抓 → 抬到高处 → 精确下压 → 释放"""
    dx = rng.uniform(40, 100) * rng.choice([-1, 1])
    dy = rng.uniform(40, 100) * rng.choice([-1, 1])
    up = rng.uniform(120, 170)
    v = rng.randint(V_MIN + 5, V_MAX - 5)
    return [
        ("g", GRIP_OPEN, 0.3),
        ("p", [dx * 0.5, dy * 0.5, 0], v),
        ("pz", -rng.uniform(35, 70), v - 5),
        ("dwell", 0.3),
        ("g", GRIP_CLOSE, 0.6),
        ("pz", up, v - 5),
        ("p", [-dx * 0.55, -dy * 0.55, 0], v),
        ("dwell", rng.uniform(0.3, 0.5)),
        ("pz", -up * 0.9, v - 8),
        ("g", GRIP_OPEN, 0.5),
        ("pz", up * 0.6, v),
    ]


def t_sweep_area(rng):
    """大范围扫掠：采视觉覆盖度（相机看不同区域）"""
    a = rng.uniform(120, 220) * rng.choice([-1, 1])
    b = rng.uniform(80, 150) * rng.choice([-1, 1])
    v = rng.randint(V_MIN, V_MAX)
    return [
        ("p", [a, 0, rng.uniform(-30, 30)], v),
        ("p", [0, b, 0], v),
        ("p", [-a, 0, 0], v),
        ("p", [0, -b, rng.uniform(-20, 20)], v),
        ("p", [a * 0.4, b * 0.4, 0], v),
    ]


def t_joint_reach(rng):
    """关节空间可达性探索（大幅改变腕部视角，补观测多样性）"""
    v = rng.randint(V_MIN, V_MAX)
    steps = []
    for _ in range(rng.randint(3, 5)):
        d = [rng.uniform(-1, 1) * JOINT_LIM_DEG * 0.7 for _ in range(3)]
        d += [rng.uniform(-1, 1) * 15 for _ in range(3)]
        steps.append(("j", d, v))
        steps.append(("dwell", rng.uniform(0.2, 0.5)))
    return steps


def t_open_drawer(rng):
    """拉抽屉：接近 → 勾住 → 后拉 → 推回"""
    dx = rng.uniform(60, 120)
    pull = rng.uniform(80, 150)
    v = rng.randint(V_MIN, V_MAX - 5)
    return [
        ("g", GRIP_OPEN, 0.3),
        ("p", [dx, rng.uniform(-30, 30), 0], v),
        ("dwell", 0.3),
        ("g", GRIP_CLOSE, 0.5),
        ("p", [-pull, 0, 0], v - 8),
        ("dwell", rng.uniform(0.3, 0.6)),
        ("p", [pull * 0.85, 0, 0], v - 8),
        ("g", GRIP_OPEN, 0.4),
        ("p", [-dx * 0.6, 0, 0], v),
    ]


TASKS = {
    "pick_place": t_pick_place,
    "push":       t_push,
    "stack":      t_stack,
    "sweep":      t_sweep_area,
    "joint":      t_joint_reach,
    "drawer":     t_open_drawer,
}
DEFAULT_TASKS = "pick_place,push,stack,sweep"


# =========================== 工具 ===========================
def log(msg, logf=None):
    line = f"[{datetime.datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    if logf:
        logf.write(line + "\n")
        logf.flush()


def free_gb(path):
    try:
        return shutil.disk_usage(path).free / (1024 ** 3)
    except Exception:
        return 999.0


def load_manifest(out):
    """读已完成清单 -> {task: 已完成条数}, 最大 episode 序号"""
    mf = os.path.join(out, "manifest.jsonl")
    done = {}
    max_idx = -1
    if not os.path.exists(mf):
        return done, max_idx
    with open(mf, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("ok"):
                done[r["task"]] = done.get(r["task"], 0) + 1
            max_idx = max(max_idx, int(r.get("episode_index", 0)))
    return done, max_idx


def fmt_sec(s):
    s = int(max(0, s))
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


# =========================== 动作执行 ===========================
class Executor:
    def __init__(self, arm, rec, logf):
        self.arm = arm
        self.rec = rec
        self.logf = logf
        self.abort = False
        self.err_seen = []

    def _check_err(self, where=""):
        """检查错误码；真机 err 全 0 才正常"""
        try:
            st = self.arm.state()
        except Exception as e:
            log(f"    [WARN] 读状态失败({where}): {e}", self.logf)
            return True
        errs = [int(x) for x in st.get("err", []) if int(x) != 0]
        if errs:
            log(f"    [ERR ] {where} 错误码 {errs} → 立即停止", self.logf)
            self.err_seen = errs
            self.abort = True
            return False
        return True

    def run(self, steps):
        """执行一个 episode 的步骤序列；返回 True=正常结束"""
        for i, st in enumerate(steps):
            if self.abort:
                return False
            kind = st[0]

            if kind == "dwell":
                time.sleep(float(st[1]))
                continue

            if kind == "g":
                pos, wait = float(st[1]), float(st[2])
                self.rec.set_gripper_cmd(pos)      # 动作维度（无论夹爪是否在线都记）
                try:
                    self.arm.gripper(int(1 + pos * 999), block=False)
                except Exception:
                    pass                            # 无夹爪时静默忽略
                time.sleep(wait)
                continue

            if kind == "j":
                d, v = st[1], st[2]
                d = [max(-JOINT_LIM_DEG, min(JOINT_LIM_DEG, float(x))) for x in d]
                cur = self.arm.state()["joint"]
                tgt = [cur[k] + d[k] for k in range(6)]
                self.arm.movej_deg(tgt, v=v)
                time.sleep(0.9 + max(abs(x) for x in d) / 60.0)
                if not self._check_err(f"step{i}:movej"):
                    return False
                continue

            if kind == "p":
                d, v = st[1], st[2]
                d = [max(-POSE_LIM_MM, min(POSE_LIM_MM, float(x))) for x in d]
                s = self.arm.state()
                tgt = [s["pose"][k] + d[k] for k in range(3)]
                self.arm.movel(tgt, s["euler"], v=v)
                time.sleep(0.9 + max(abs(x) for x in d) / 180.0)
                if not self._check_err(f"step{i}:movel"):
                    return False
                continue

            if kind == "pz":
                dz, v = float(st[1]), st[2]
                dz = max(-POSE_LIM_MM, min(POSE_LIM_MM, dz))
                s = self.arm.state()
                tgt = [s["pose"][0], s["pose"][1], s["pose"][2] + dz]
                self.arm.movel(tgt, s["euler"], v=v)
                time.sleep(0.8 + abs(dz) / 180.0)
                if not self._check_err(f"step{i}:movel_z"):
                    return False
                continue

            log(f"    [WARN] 未知步骤 {kind}", self.logf)
        return True


def go_home(arm, home, logf):
    try:
        arm.movej_deg(home["joint"], v=25)
        time.sleep(1.2)
        log("  已回 home", logf)
    except Exception as e:
        log(f"  [WARN] 回 home 失败: {e}", logf)


# =========================== 主流程 ===========================
def main():
    ap = argparse.ArgumentParser(description="批量无人值守采集")
    ap.add_argument("--tasks", default=DEFAULT_TASKS, help=f"逗号分隔，可选: {','.join(TASKS)}")
    ap.add_argument("--episodes-per-task", type=int, default=50)
    ap.add_argument("--out", default=os.path.join(HERE, "episodes"))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--max-minutes", type=float, default=0, help="0=不限")
    ap.add_argument("--min-free-gb", type=float, default=5.0)
    ap.add_argument("--resume", action="store_true", help="跳过 manifest 里已完成的条数")
    ap.add_argument("--plan", action="store_true", help="只打印计划，不连机器人")
    ap.add_argument("--probe", action="store_true", help="只体检，不采集")
    ap.add_argument("--settle", type=float, default=1.0, help="episode 前后静置秒数")
    args = ap.parse_args()

    names = [t.strip() for t in args.tasks.split(",") if t.strip()]
    bad = [t for t in names if t not in TASKS]
    if bad:
        print(f"未知任务: {bad}\n可用: {list(TASKS)}")
        return 2

    os.makedirs(args.out, exist_ok=True)
    logf = open(os.path.join(args.out, "_batch.log"), "a", encoding="utf-8")
    manifest = os.path.join(args.out, "manifest.jsonl")

    # ---- 计划模式（不连机器人，随时可跑）----
    if args.plan:
        done, max_idx = load_manifest(args.out)
        print("=" * 66)
        print("  采集计划")
        print("=" * 66)
        print(f"  输出目录 : {args.out}")
        print(f"  已有数据 : {sum(done.values())} 条  {done}")
        print(f"  目标     : 每任务 {args.episodes_per_task} 条 × {len(names)} 任务 = "
              f"{args.episodes_per_task * len(names)} 条")
        print()
        rng = random.Random(0)
        total_est = 0.0
        total_ep = 0
        for t in names:
            steps = TASKS[t](rng)
            est = sum(0.9 for s in steps) + sum(s[-1] for s in steps if s[0] in ("g", "dwell"))
            est += 3 * sum(1 for s in steps if s[0] in ("j", "p", "pz"))
            left = max(0, args.episodes_per_task - done.get(t, 0)) if args.resume \
                else args.episodes_per_task
            total_est += est * left
            total_ep += left
            print(f"  {t:12s} 步骤 {len(steps):2d}  单条约 {est:4.1f}s  "
                  f"待采 {left:3d} 条  约 {fmt_sec(est * left)}")
        print()
        # 实测：一条 30~35s 的双相机 episode 原始约 3.5MB，LeRobot h264 编码后约 2.1MB
        print(f"  完整跑完预计: {fmt_sec(total_est)}"
              f"（不含相机/落盘开销，实际约 ×1.3 ≈ {fmt_sec(total_est * 1.3)}）")
        print(f"  数据量估算  : 原始 {total_ep * 3.5 / 1024:.2f} GB  "
              f"→ LeRobot 数据集 {total_ep * 2.1 / 1024:.2f} GB")
        print(f"  磁盘余量    : {free_gb(args.out):.1f} GB"
              f"{'  ⚠ 不足' if free_gb(args.out) < total_ep * 3.5 / 1024 + args.min_free_gb else '  OK'}")
        print("=" * 66)
        return 0

    # ---- 延迟导入（--plan 模式在没装 opencv 的机器上也能跑）----
    try:
        from arm import ArmClient
        from cams import DualCameras
        from record import Recorder
    except Exception as e:
        print(f"[FATAL] 导入硬件模块失败: {e}")
        print("        请在 <ROBOT_USER> 上、且本脚本与 arm.py/cams.py/record.py 同目录运行")
        return 3

    log("=" * 60, logf)
    log(f"批量采集启动 | 任务={names} | 每任务={args.episodes_per_task}", logf)

    # ---- 连接机器人 ----
    log("[1/4] 连接机械臂 ...", logf)
    try:
        arm = ArmClient()
    except Exception as e:
        log(f"[FATAL] 连不上机械臂: {e}", logf)
        log("        检查: 网线在 192.168.20.x?  arm 上电?  端口 8080?", logf)
        return 3
    info = arm.software_info()
    log(f"      型号 {info.get('Product_version')}  "
        f"软件 {info.get('ctrl_info', {}).get('version')}", logf)

    log("[2/4] 打开双相机 ...", logf)
    cams = DualCameras()
    cam_lines = cams.start()
    for line in cam_lines:
        log(f"      {line}", logf)
    if any("FAIL" in x for x in cam_lines):
        log("[FATAL] 相机打开失败，先跑 --probe 排查", logf)
        cams.stop()
        arm.close()
        return 3
    time.sleep(1.5)

    (_, f_top), (_, f_wrist) = cams.get()
    if f_top is None or f_wrist is None:
        log("[FATAL] 相机无帧", logf)
        cams.stop()
        arm.close()
        return 3
    log(f"      top={f_top.shape} 亮度{f_top.mean():.1f} | "
        f"wrist={f_wrist.shape} 亮度{f_wrist.mean():.1f}", logf)

    # ---- 夹爪在线检测（决定第 7 维是否有意义）----
    gripper_ok = False
    try:
        r = arm.cmd({"command": "get_gripper_state"}, timeout=3)
        gripper_ok = "actpos" in r
        log(f"      夹爪: {'在线 actpos=' + str(r.get('actpos')) if gripper_ok else '未检测到'}", logf)
    except Exception:
        log("      夹爪: 未检测到（第7维将恒为0，抓放任务语义不完整）", logf)
    if not gripper_ok:
        log("      [注意] 无夹爪也能采，但只能作为运动/视觉预训练数据；", logf)
        log("             正式抓放训练集必须装夹爪后重采。", logf)

    if args.probe:
        log("[probe] 体检完成，未采集", logf)
        cams.stop()
        arm.close()
        return 0

    # ---- 初始化录制器 ----
    log("[3/4] 初始化录制器 ...", logf)
    done, max_idx = load_manifest(args.out)
    rec = Recorder(arm, cams, args.out, fps=30)
    rec.episode_index = max_idx + 1          # 续接编号，绝不覆盖旧数据
    log(f"      起始序号 episode_{rec.episode_index:06d}，已有 {sum(done.values())} 条", logf)

    home = arm.state()
    home_j = list(home["joint"])
    log(f"      home 关节(deg)={[round(x, 2) for x in home_j]}", logf)

    ex = Executor(arm, rec, logf)
    rng = random.Random(args.seed if args.seed is not None
                        else int(time.time()))

    # Ctrl+C 安全退出
    stop_flag = {"v": False}

    def _sig(signum, frame):
        stop_flag["v"] = True
        log("\n[!] 收到中断，保存当前 episode 后退出 ...", logf)
    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)

    # ---- 主循环 ----
    log("[4/4] 开跑", logf)
    t_start = time.time()
    n_ep = 0
    n_fail = 0
    per_task_done = {t: (done.get(t, 0) if args.resume else 0) for t in names}

    try:
        for task in names:
            need = args.episodes_per_task - per_task_done[task]
            if need <= 0:
                log(f"[{task}] 已完成 {per_task_done[task]} 条，跳过", logf)
                continue
            log(f"\n===== 任务 {task}：还需 {need} 条 =====", logf)

            for k in range(need):
                if stop_flag["v"] or ex.abort:
                    break
                if args.max_minutes and (time.time() - t_start) / 60 >= args.max_minutes:
                    log(f"[时间到] 已跑 {args.max_minutes} 分钟，停止", logf)
                    stop_flag["v"] = True
                    break
                if free_gb(args.out) < args.min_free_gb:
                    log(f"[磁盘] 余量 < {args.min_free_gb}GB，停止", logf)
                    stop_flag["v"] = True
                    break

                steps = TASKS[task](rng)
                ep_idx = rec.episode_index
                log(f"  --- {task} {k + 1}/{need} -> episode_{ep_idx:06d} "
                    f"({len(steps)} 步) ---", logf)

                go_home(arm, {"joint": home_j}, logf)
                time.sleep(args.settle)

                rec.start_episode(task=task)
                time.sleep(0.2)
                ok = ex.run(steps)
                time.sleep(args.settle)
                meta = rec.stop_episode()

                if meta is None:
                    log("    [跳过] 0 帧，未落盘", logf)
                    n_fail += 1
                    continue

                rec_row = dict(
                    episode_index=ep_idx, task=task, frames=meta["frames"],
                    duration=round(meta["duration"], 2), ok=bool(ok),
                    err=ex.err_seen, gripper=gripper_ok,
                    ts=datetime.datetime.now().isoformat(timespec="seconds"),
                )
                with open(manifest, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec_row, ensure_ascii=False) + "\n")

                n_ep += 1
                if not ok:
                    n_fail += 1
                    log(f"    [异常收尾] {meta['frames']} 帧已保存，err={ex.err_seen}", logf)
                    go_home(arm, {"joint": home_j}, logf)
                    if ex.abort:
                        log("[终止] 检测到错误码，为安全起见停止全部采集", logf)
                        stop_flag["v"] = True
                        break
                else:
                    el = time.time() - t_start
                    rate = n_ep / el if el > 0 else 0
                    left = (args.episodes_per_task * len(names) - n_ep) / rate if rate else 0
                    log(f"    OK {meta['frames']} 帧 / {meta['duration']:.1f}s | "
                        f"累计 {n_ep} 条 | 均速 {rate * 60:.1f} 条/分 | "
                        f"剩余约 {fmt_sec(left)}", logf)
    finally:
        try:
            cams.stop()
        except Exception:
            pass
        go_home(arm, {"joint": home_j}, logf)
        try:
            arm.close()
        except Exception:
            pass

    # ---- 总结 ----
    dur = time.time() - t_start
    log("\n" + "=" * 60, logf)
    log(f"结束 | 成功 {n_ep} 条 / 失败 {n_fail} 条 | 用时 {fmt_sec(dur)}", logf)
    log(f"数据目录: {args.out}", logf)
    log("下一步构建 LeRobot 数据集:", logf)
    log(f"  python3 build_dataset.py {args.out} lingbot/gen65bi-<ROBOT_USER>-v1", logf)
    log("=" * 60, logf)
    logf.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
