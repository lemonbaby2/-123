"""RealMan GEN65-BI 机械臂客户端（<ROBOT_USER> 真机）
协议依据：睿尔曼官方 JSON 协议 v3.x（develop.realman-robotics.com/robot/json/）
- TCP JSON API: <ARM_HOST>:8080（\n 分隔，持久连接）
- UDP 实时推送: <ARM_UDP_HOST>:8089, 200Hz

单位约定（与官方一致）：
- 关节角: 0.001° (int)
- 末端位置: 0.001mm (int)
- 末端姿态: 0.001rad (int, 欧拉角 rx/ry/rz)
- 速度 v: 0~100 百分比
"""
import socket, json, threading, time, math

ARM_IP = "<ARM_HOST>"
ARM_PORT = 8080
UDP_IP = "<ARM_UDP_HOST>"   # 本机 enp2s0
UDP_PORT = 8089


class ArmClient:
    def __init__(self, ip=ARM_IP, port=ARM_PORT, udp=True):
        self.ip, self.port = ip, port
        self.sock = None
        self.f = None
        self._lock = threading.Lock()
        self.udp_latest = None
        self.udp_ts = 0.0
        self.udp_count = 0
        self._udp_stop = threading.Event()
        self._udp_thread = None
        self.last_async = None
        self.connect()
        if udp:
            self.start_udp()

    # ---------- 连接 ----------
    def connect(self):
        self.sock = socket.create_connection((self.ip, self.port), timeout=5)
        self.sock.settimeout(5)
        self.f = self.sock.makefile("rwb")

    def close(self):
        self.stop_udp()
        try:
            self.sock.close()
        except Exception:
            pass

    def cmd(self, c, timeout=5):
        """发送一条 JSON 指令，返回解析后的 dict。
        运动中服务器会异步推送 current_trajectory_state 等消息，需跳过。"""
        with self._lock:
            self.sock.settimeout(timeout)
            self.f.write((json.dumps(c) + "\n").encode())
            self.f.flush()
            deadline = time.time() + timeout
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise IOError("arm cmd timeout: " + json.dumps(c, ensure_ascii=False)[:80])
                self.sock.settimeout(remaining)
                line = self.f.readline()
                if not line:
                    raise IOError("arm connection closed")
                try:
                    r = json.loads(line.decode(errors="replace"))
                except Exception:
                    continue
                # 异步推送（无 command 字段的 state 通知）: current_trajectory_state / Force_Position_State
                # 注意: get_current_arm_state 的响应是 {"arm_state":..,"state":"current_arm_state"}，不能跳
                if isinstance(r, dict) and "command" not in r and \
                        r.get("state") in ("current_trajectory_state", "Force_Position_State"):
                    self.last_async = r
                    continue
                return r

    # ---------- 状态 ----------
    def state(self):
        """TCP 查询 -> dict(joint_deg[6], pose_mm[3], euler_rad[3], err)"""
        r = self.cmd({"command": "get_current_arm_state"})
        a = r["arm_state"]
        return dict(
            joint=[v / 1000.0 for v in a["joint"]],          # 0.001deg -> deg
            pose=[v / 1000.0 for v in a["pose"][:3]],        # 0.001mm -> mm
            euler=[v / 1000.0 for v in a["pose"][3:]],       # 0.001rad -> rad
            err=a.get("err", []),
            raw=a,
        )

    def start_udp(self):
        def worker():
            u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            u.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                u.bind((UDP_IP, UDP_PORT))
            except OSError:
                return   # 端口被占则退化为 TCP 轮询
            u.settimeout(0.5)
            while not self._udp_stop.is_set():
                try:
                    d, _ = u.recvfrom(4096)
                except socket.timeout:
                    continue
                except OSError:
                    break
                try:
                    obj = json.loads(d.decode(errors="replace"))
                    js = obj.get("joint_status", {})
                    wp = obj.get("waypoint", {})
                    self.udp_latest = dict(
                        joint=[v / 1000.0 for v in js.get("joint_position", [])],
                        en_flag=js.get("joint_en_flag", []),
                        err_code=js.get("joint_err_code", []),
                        joint_current=js.get("joint_current", []),
                        joint_temperature=js.get("joint_temperature", []),
                        pose=[v / 1000.0 for v in wp.get("position", [])],
                        euler=[v / 1000.0 for v in wp.get("euler", [])],
                        quat=[v / 1000.0 for v in wp.get("quat", [])],
                        err=obj.get("err", []),
                        raw=obj,
                    )
                    self.udp_ts = time.time()
                    self.udp_count += 1
                except Exception:
                    continue
            u.close()
        self._udp_thread = threading.Thread(target=worker, daemon=True)
        self._udp_thread.start()

    def stop_udp(self):
        self._udp_stop.set()

    def udp_state(self):
        """-> (state_dict, age_sec)；无数据返回 (None, inf)"""
        if self.udp_latest is None:
            return None, float("inf")
        return self.udp_latest, time.time() - self.udp_ts

    # ---------- 运动（官方协议：joint=0.001°, pose=0.001mm/0.001rad, v=0~100）----------
    def movej(self, joint_mdeg, v=30, r=0, tc=0, block=True):
        """关节空间运动。joint_mdeg: 6 关节角，单位 0.001°"""
        return self.cmd({"command": "movej",
                         "joint": [int(round(x)) for x in joint_mdeg],
                         "v": int(v), "r": int(r), "trajectory_connect": int(tc)})

    def movej_deg(self, joint_deg, v=30, **kw):
        """关节空间运动，输入角度(度)"""
        return self.movej([x * 1000.0 for x in joint_deg], v=v, **kw)

    def movel(self, pose_mm, euler_rad, v=30, r=0, tc=0):
        """直线运动。pose_mm: [x,y,z](mm)；euler_rad: [rx,ry,rz](rad)"""
        pose = [int(round(x * 1000.0)) for x in pose_mm] + [int(round(x * 1000.0)) for x in euler_rad]
        return self.cmd({"command": "movel",
                         "pose": pose, "v": int(v), "r": int(r), "trajectory_connect": int(tc)})

    def movej_p(self, pose_mm, euler_rad, v=30, r=0, tc=0):
        """关节空间规划到目标位姿"""
        pose = [int(round(x * 1000.0)) for x in pose_mm] + [int(round(x * 1000.0)) for x in euler_rad]
        return self.cmd({"command": "movej_p",
                         "pose": pose, "v": int(v), "r": int(r), "trajectory_connect": int(tc)})

    def movec(self, via_mm, via_rad, to_mm, to_rad, v=30, r=0, loop=0, tc=0):
        """圆弧运动"""
        pv = [int(round(x * 1000.0)) for x in via_mm] + [int(round(x * 1000.0)) for x in via_rad]
        pt = [int(round(x * 1000.0)) for x in to_mm] + [int(round(x * 1000.0)) for x in to_rad]
        return self.cmd({"command": "movec",
                         "pose": {"pose_via": pv, "pose_to": pt},
                         "v": int(v), "r": int(r), "loop": int(loop), "trajectory_connect": int(tc)})

    # ---------- 夹爪 ----------
    def gripper(self, position, block=False):
        """夹爪到位置，position 1~1000"""
        return self.cmd({"command": "set_gripper_position",
                         "position": int(position), "block": bool(block)})

    def gripper_release(self, speed=500, block=False):
        return self.cmd({"command": "set_gripper_release",
                         "speed": int(speed), "block": bool(block)})

    # ---------- 拖动示教 ----------
    def drag_teach(self, on=True, record=True):
        """单/多关节拖动示教（start_drag_teach，无需六维力）。
        record=True 时记录轨迹，可 run_drag_trajectory 复现。"""
        if on:
            return self.cmd({"command": "start_drag_teach",
                             "trajectory_record": 1 if record else 0})
        return self.cmd({"command": "stop_drag_teach"})

    def multi_drag_teach(self, on=True, free_axes=None, frame=0):
        """复合模式拖动示教（六维力版本专用）。
        free_axes: [x,y,z,rx,ry,rz] 0/1"""
        if free_axes is None:
            free_axes = [1, 1, 1, 0, 0, 0]
        if on:
            return self.cmd({"command": "start_multi_drag_teach",
                             "free_axes": [int(x) for x in free_axes],
                             "frame": int(frame), "singular_wall": 0})
        return self.cmd({"command": "stop_drag_teach"})

    def run_drag_trajectory(self):
        return self.cmd({"command": "run_drag_trajectory"})

    # ---------- 其他 ----------
    def stop(self):
        return self.cmd({"command": "set_arm_stop"})

    def pause(self):
        return self.cmd({"command": "set_arm_pause"})

    def resume(self):
        return self.cmd({"command": "set_arm_continue"})

    def joint_enable(self, state):
        return self.cmd({"command": "set_joint_en_state", "joint_en_state": int(state)})

    def current_trajectory(self):
        return self.cmd({"command": "get_arm_current_trajectory"})

    def software_info(self):
        return self.cmd({"command": "get_arm_software_info"})


if __name__ == "__main__":
    arm = ArmClient()
    info = arm.software_info()
    print("software:", json.dumps(info.get("ctrl_info", {})))
    s = arm.state()
    print("joint(deg):", [round(v, 3) for v in s["joint"]])
    print("pose(mm):", [round(v, 2) for v in s["pose"]], "euler(rad):", [round(v, 4) for v in s["euler"]])
    print("err:", s["err"])
    t0, n = time.time(), 0
    while time.time() - t0 < 2:
        st, age = arm.udp_state()
        if st:
            n += 1
    print(f"UDP push: {n/2:.0f} Hz, last age={age*1000:.1f} ms")
    arm.close()
