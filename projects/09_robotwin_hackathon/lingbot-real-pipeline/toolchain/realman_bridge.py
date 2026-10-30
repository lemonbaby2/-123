"""RealMan GEN65-BI 机械臂 × LingBot-VLA 2.0 部署桥接客户端。

运行位置：机器人本机（<ROBOT_USER>），因为机械臂 <ARM_HOST> 与相机只在机器人内网可达。
策略服务器（GPU 机）运行：python -m deploy.lingbot_vla_v2_policy --model_path ... --port 8006

用法：
  python3 realman_bridge.py --host <GPU机IP> --port 8006 \
      --task "pick up the block and put it in the bowl" \
      --robo-name realman_gen65bi --period 0.15 --duration 30

数据流：
  观测: observation.images.cam_high(top RGB) + observation.images.cam_wrist(wrist RGB)
        + observation.state(7D: 6关节弧度 + 夹爪0~1) + task(指令)
  动作: action.arm.position(chunk,6 弧度) + action.effector.position(chunk,1) -> movej/夹爪

安全：关节限位钳制、单步最大增量、速度上限、错误码急停。
"""
import argparse, json, sys, time
import numpy as np

sys.path.insert(0, "/home/<ROBOT_USER>/lingbot_real")
from arm import ArmClient
from cams import DualCameras

# ---------- 策略客户端（websocket + msgpack）----------
import websockets.sync.client
from msgpack_numpy import Packer, unpackb


class PolicyClient:
    def __init__(self, host, port, api_key=None):
        self._uri = f"ws://{host}:{port}"
        self._packer = Packer()
        self._ws, self.meta = self._wait_for_server()

    def _wait_for_server(self):
        print(f"[bridge] 连接策略服务器 {self._uri} ...")
        while True:
            try:
                conn = websockets.sync.client.connect(
                    self._uri, compression=None, max_size=None)
                meta = unpackb(conn.recv())
                print("[bridge] 服务器已连接, metadata:", meta)
                return conn, meta
            except Exception as e:
                print(f"[bridge] 重试中 ({e}) ...")
                time.sleep(3)

    def infer(self, obs):
        self._ws.send(self._packer.pack(obs))
        resp = self._ws.recv()
        if isinstance(resp, str):
            raise RuntimeError(f"推理服务器错误:\n{resp}")
        return unpackb(resp)

    def reset(self, robo_name):
        return self.infer(dict(reset=True, robo_name=robo_name))

    def close(self):
        try:
            self._ws.close()
        except Exception:
            pass


# ---------- 安全限制 ----------
JOINT_LIMIT_DEG = 160.0        # RealMan GEN65 各轴限位（保守）
MAX_STEP_DEG = 6.0             # 单控制步最大关节增量（度）
MAX_SPEED_V = 40               # movej 速度百分比上限


class ArmBridge:
    def __init__(self, arm, period=0.15, state_unit="rad", gripper_invert=False):
        self.arm = arm
        self.period = period
        self.state_unit = state_unit        # 模型 state 单位: rad / deg
        self.gripper_invert = gripper_invert
        self.last_target = None

    def get_state(self):
        """7D: 6关节(rad) + 夹爪(0~1)"""
        s = self.arm.state()
        joint_deg = np.asarray(s["joint"], dtype=np.float64)
        if self.state_unit == "rad":
            joint = np.deg2rad(joint_deg)
        else:
            joint = joint_deg
        try:
            g = self.arm.cmd({"command": "get_gripper_state"}, timeout=2)
            grip = float(g.get("actpos", 0)) / 1000.0
        except Exception:
            grip = 0.0
        return np.concatenate([joint, [grip]]).astype(np.float32)

    def execute_chunk(self, chunk_arm_rad, chunk_eff, log=print):
        """按控制周期执行一个动作块。chunk_arm_rad: (T,6) 弧度; chunk_eff: (T,) 0~1"""
        T = len(chunk_arm_rad)
        for t in range(T):
            t0 = time.time()
            # 1) 安全钳制
            tgt_rad = np.asarray(chunk_arm_rad[t], dtype=np.float64)
            tgt_deg = np.rad2deg(tgt_rad)
            cur_deg = np.asarray(self.arm.state()["joint"], dtype=np.float64)
            if self.last_target is not None:
                delta = tgt_deg - self.last_target
                over = np.abs(delta) > MAX_STEP_DEG
                if over.any():
                    tgt_deg = self.last_target + np.clip(delta, -MAX_STEP_DEG, MAX_STEP_DEG)
                    log(f"    [安全] 步 {t} 增量超限已钳制: {np.round(delta[over], 1)}")
            self.last_target = tgt_deg.copy()
            tgt_deg = np.clip(tgt_deg, -JOINT_LIMIT_DEG, JOINT_LIMIT_DEG)

            # 2) 错误码检查
            st, age = self.arm.udp_state()
            if st is not None and any(int(c) != 0 for c in (st.get("err_code") or [])):
                log(f"    [急停] 关节错误码: {st['err_code']}")
                self.arm.stop()
                return False

            # 3) 下发 movej
            self.arm.movej([x * 1000 for x in tgt_deg], v=MAX_SPEED_V)

            # 4) 夹爪（若安装）
            eff = float(chunk_eff[t])
            pos = int(round((1.0 - eff if self.gripper_invert else eff) * 999 + 1))
            try:
                self.arm.cmd({"command": "set_gripper_position", "position": pos, "block": False}, timeout=2)
            except Exception:
                pass

            # 5) 控制周期
            dt = time.time() - t0
            if dt < self.period:
                time.sleep(self.period - dt)
        return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="策略服务器 IP")
    ap.add_argument("--port", type=int, default=8006)
    ap.add_argument("--task", required=True, help="语言指令")
    ap.add_argument("--robo-name", default="realman_gen65bi")
    ap.add_argument("--period", type=float, default=0.15, help="控制周期秒")
    ap.add_argument("--duration", type=float, default=30.0, help="总运行秒数")
    ap.add_argument("--use-length", type=int, default=25, help="每次推理执行的步数")
    ap.add_argument("--state-unit", default="rad", choices=["rad", "deg"])
    ap.add_argument("--gripper-invert", action="store_true")
    ap.add_argument("--record", default=None, help="可选：录制输出目录（同 collect.py 格式）")
    args = ap.parse_args()

    import cv2
    arm = ArmClient()
    cams = DualCameras()
    for line in cams.start():
        print("[bridge]", line)
    time.sleep(1.0)

    policy = PolicyClient(args.host, args.port)
    bridge = ArmBridge(arm, period=args.period, state_unit=args.state_unit,
                       gripper_invert=args.gripper_invert)

    # 复位：加载机器人配置
    r = policy.reset(args.robo_name)
    print("[bridge] reset ->", {k: v for k, v in r.items() if k != "server_timing"})

    s0 = arm.state()
    print("[bridge] 起始关节(deg):", [round(v, 2) for v in s0["joint"]])

    t_start = time.time()
    step = 0
    n_infer = 0
    ok = True
    while time.time() - t_start < args.duration:
        # ---- 观测 ----
        (t_top, f_top), (t_wrist, f_wrist) = cams.get()
        if f_top is None or f_wrist is None:
            time.sleep(0.05)
            continue
        obs = {
            "observation.images.cam_high": cv2.cvtColor(f_top, cv2.COLOR_BGR2RGB),
            "observation.images.cam_wrist": cv2.cvtColor(f_wrist, cv2.COLOR_BGR2RGB),
            "observation.state": bridge.get_state(),
            "task": args.task,
        }
        # ---- 推理 ----
        t_inf = time.time()
        try:
            act = policy.infer(obs)
        except Exception as e:
            print(f"[bridge] 推理失败: {e}")
            break
        n_infer += 1
        # 真实 server 输出原始键 action(chunk,7: 6关节rad+夹爪)；兼容旧拆分键
        if "action" in act:
            full = np.asarray(act["action"], dtype=np.float64)
            arm_act = full[..., :6]
            eff_act = full[..., 6:7]
        else:
            arm_act = np.asarray(act["action.arm.position"], dtype=np.float64)
            eff_act = np.asarray(act["action.effector.position"], dtype=np.float64).reshape(-1)
        infer_ms = (time.time() - t_inf) * 1000
        print(f"[bridge] 推理#{n_infer} chunk={arm_act.shape} 耗时{infer_ms:.0f}ms "
              f"首步目标(deg)={np.round(np.rad2deg(arm_act[0]), 1)}")

        # ---- 执行 ----
        ok = bridge.execute_chunk(arm_act, eff_act)
        if not ok:
            break
        step += len(arm_act)

    print(f"[bridge] 结束: 推理 {n_infer} 次, 执行 {step} 步, "
          f"总耗时 {time.time()-t_start:.1f}s")
    try:
        cams.stop()
        arm.close()
        policy.close()
    except Exception as e:
        print(f"[bridge] 清理时警告: {e}")
    time.sleep(0.5)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
