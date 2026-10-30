"""采集 CLI：交互/脚本两种模式
用法:
  python3 collect.py probe                      # 只读体检：相机+臂+UDP
  python3 collect.py demo                       # 演示采集（脚本动作，验证管线）
  python3 collect.py drag <task名> <条数>        # 拖动示教采集（需有人在现场拖动机械臂）
  python3 collect.py run <task名> <秒>          # 纯记录指定秒数
"""
import sys, os, json, time
import numpy as np

from arm import ArmClient
from cams import DualCameras
from record import Recorder

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "episodes")


def probe():
    print("[1] 连接机械臂 ...")
    arm = ArmClient()
    info = arm.software_info()
    print("    型号:", info.get("Product_version"), "| 软件:", info.get("ctrl_info", {}).get("version"))
    s = arm.state()
    print("    关节(deg):", [round(v, 2) for v in s["joint"]])
    print("    末端(mm):", [round(v, 1) for v in s["pose"]], "rpy(deg):", [round(v, 2) for v in s["euler"]])
    print("    错误码:", s["err"])
    t0, n = time.time(), 0
    while time.time() - t0 < 2:
        st, age = arm.udp_state()
        if st:
            n += 1
    print(f"    UDP 200Hz 推送实测: {n/2:.0f} Hz, 延迟 {age*1000:.1f} ms")
    arm.close()

    print("[2] 打开双相机 ...")
    cams = DualCameras()
    for line in cams.start():
        print("   ", line)
    time.sleep(1.5)
    for line in cams.stats():
        print("   ", line)
    (t_top, f_top), (t_wrist, f_wrist) = cams.get()
    if f_top is not None:
        print(f"    top 帧: {f_top.shape} 亮度 {f_top.mean():.1f}")
    if f_wrist is not None:
        print(f"    wrist 帧: {f_wrist.shape} 亮度 {f_wrist.mean():.1f}")
    cams.stop()
    return 0


def demo():
    """脚本化演示采集：真实臂部运动（movej 扫动 + movel 方形 + 拾放风格），验证 30Hz 同步管线。
    注意：当前真机未安装夹爪，夹爪指令仅作记录占位。"""
    arm = ArmClient()
    cams = DualCameras()
    for line in cams.start():
        print("  camera:", line)
    rec = Recorder(arm, cams, OUT, fps=30)
    time.sleep(0.5)

    s0 = arm.state()
    print("起始关节:", [round(v, 2) for v in s0["joint"]])
    print("起始位姿(mm):", [round(v, 1) for v in s0["pose"]])
    home_j = np.array(s0["joint"])
    home_p = np.array(s0["pose"])
    home_e = np.array(s0["euler"])

    def go_j(deltas, v=25, wait=1.2):
        tgt = home_j + np.array(deltas, dtype=float)
        r = arm.movej([x * 1000 for x in tgt], v=v)
        time.sleep(wait)
        return r.get("receive_state")

    def go_p(dp, v=20, wait=1.2):
        tgt = home_p + np.array(dp, dtype=float)
        r = arm.movel(list(tgt), list(home_e), v=v)
        time.sleep(wait)
        return r.get("receive_state")

    # ---- episode 0: 关节空间扫动（模拟任务中的大幅度调整）----
    print("\n=== episode 0: movej 关节扫动 ===")
    rec.start_episode(task="demo_movej_sweep")
    rec.set_gripper_cmd(0.0)
    time.sleep(0.3)
    for d in ([25, 0, 10, 0, 0, 0], [-25, 8, -10, 0, 0, 0], [10, -8, 15, 0, 0, 0], [0, 0, 0, 0, 0, 0]):
        print("   movej", d, "->", go_j(d))
    time.sleep(0.3)
    rec.stop_episode()
    print("   保存:", rec.ep_dir)

    # ---- episode 1: 笛卡尔方形轨迹（模拟平移任务）----
    print("\n=== episode 1: movel 方形轨迹 ===")
    rec.start_episode(task="demo_movel_square")
    time.sleep(0.3)
    for dp in ([100, 0, 0], [0, 100, 0], [-100, 0, 0], [0, -100, 0], [0, 0, 0]):
        print("   movel", dp, "->", go_p(dp))
    time.sleep(0.3)
    rec.stop_episode()
    print("   保存:", rec.ep_dir)

    # ---- episode 2: 拾放风格（接近-抬起-横移-下放）----
    print("\n=== episode 2: 拾放风格动作 ===")
    rec.start_episode(task="demo_pick_place_style")
    time.sleep(0.3)
    seq = [([60, 0, 0], "接近"), ([0, 0, 80], "抬起"),
           ([-120, 0, 0], "横移"), ([0, 60, 0], "对位"),
           ([0, 0, -80], "下放"), ([60, 0, 0], "撤离")]
    for dp, name in seq:
        print(f"   {name} {dp} ->", go_p(dp))
        home_p = home_p + np.array(dp, dtype=float)   # 累积位移
    time.sleep(0.3)
    rec.stop_episode()
    print("   保存:", rec.ep_dir)

    # ---- episode 3: 回 home + 关节复合运动 ----
    print("\n=== episode 3: 回 home + 复合关节 ===")
    rec.start_episode(task="demo_return_home")
    time.sleep(0.3)
    print("   movel 回位 ->", arm.movel(list(s0["pose"]), list(s0["euler"]), v=20).get("receive_state"))
    time.sleep(1.5)
    for d in ([15, 5, 0, 0, 0, 0], [-15, -5, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]):
        print("   movej", d, "->", go_j(d))
    time.sleep(0.3)
    rec.stop_episode()
    print("   保存:", rec.ep_dir)

    cams.stop()
    arm.close()
    print("\n完成，数据在:", OUT)
    return 0


def run(task, seconds):
    arm = ArmClient()
    cams = DualCameras()
    for line in cams.start():
        print("  camera:", line)
    rec = Recorder(arm, cams, OUT, fps=30)
    rec.start_episode(task=task)
    t0 = time.time()
    while time.time() - t0 < float(seconds):
        time.sleep(0.2)
    rec.stop_episode()
    cams.stop()
    arm.close()
    print("保存:", rec.ep_dir)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    mode = sys.argv[1]
    if mode == "probe":
        sys.exit(probe())
    elif mode == "demo":
        sys.exit(demo())
    elif mode == "run":
        sys.exit(run(sys.argv[2], sys.argv[3]))
    else:
        print(__doc__)
        sys.exit(1)
