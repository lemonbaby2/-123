"""30Hz 同步采集：双相机图像 + 机械臂状态 + 夹爪指令
每个 episode 输出:
  episode_XXXXXX/
    cam_top.mp4      # 顶部相机 640x480@30
    cam_wrist.mp4    # 腕部相机 640x480@30
    states.npz       # timestamps, joint(deg), pose(mm), euler(deg), en_flag, err_code, gripper_cmd
    meta.json        # task / fps / 帧数 / 时长
"""
import os, json, time, threading
import numpy as np
import cv2

from cams import DualCameras


class Recorder:
    def __init__(self, arm, cams, out_dir, fps=30):
        self.arm = arm
        self.cams = cams
        self.out_dir = out_dir
        self.fps = fps
        self.recording = False
        self._thread = None
        self._stop_evt = threading.Event()
        self.rows = []
        self.writers = None
        self.ep_dir = None
        self.gripper_cmd = 0.0     # 最近一次夹爪指令（0~1 归一化）
        self._gripper_lock = threading.Lock()
        self.episode_index = 0
        # 夹爪实际位置后台轮询（无夹爪时 actpos 恒 0，不影响录制）
        self._grip_pos = 0.0
        self._grip_stop = threading.Event()
        self._grip_thread = threading.Thread(target=self._gripper_poll, daemon=True)
        self._grip_thread.start()

    def _gripper_poll(self):
        """10Hz 轮询夹爪实际位置（TCP 查询与录制主循环分离，避免阻塞）"""
        while not self._grip_stop.is_set():
            try:
                r = self.arm.cmd({"command": "get_gripper_state"}, timeout=2)
                with self._gripper_lock:
                    self._grip_pos = float(r.get("actpos", 0)) / 1000.0
            except Exception:
                pass
            self._grip_stop.wait(0.1)

    # ----------  episode 控制 ----------
    def start_episode(self, task="pick_place"):
        os.makedirs(self.out_dir, exist_ok=True)
        self.ep_dir = os.path.join(self.out_dir, f"episode_{self.episode_index:06d}")
        os.makedirs(self.ep_dir, exist_ok=True)
        self.rows = []
        self.current_task = task
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writers = {
            "cam_top.mp4": cv2.VideoWriter(os.path.join(self.ep_dir, "cam_top.mp4"), fourcc, self.fps, (640, 480)),
            "cam_wrist.mp4": cv2.VideoWriter(os.path.join(self.ep_dir, "cam_wrist.mp4"), fourcc, self.fps, (640, 480)),
        }
        self._stop_evt.clear()
        self.recording = True
        self._thread = threading.Thread(target=self._loop, args=(task,), daemon=True)
        self._thread.start()
        return self.ep_dir

    def stop_episode(self):
        self.recording = False
        self._stop_evt.set()
        if self._thread:
            self._thread.join(timeout=5)
        for w in self.writers.values():
            w.release()
        self.writers = None
        self._save()

    # ----------  夹爪指令记录 ----------
    def set_gripper_cmd(self, pos_0_1):
        with self._gripper_lock:
            self.gripper_cmd = float(pos_0_1)

    def _get_gripper_cmd(self):
        with self._gripper_lock:
            return self.gripper_cmd

    def _get_gripper_pos(self):
        with self._gripper_lock:
            return self._grip_pos

    # ----------  主循环 30Hz ----------
    def _loop(self, task):
        period = 1.0 / self.fps
        n_written = 0
        t_start = time.time()
        next_t = t_start
        while not self._stop_evt.is_set():
            now = time.time()
            if now < next_t:
                time.sleep(min(0.002, next_t - now))
                continue
            # 1) 臂状态（UDP 200Hz 缓存，取最新）
            st, age = self.arm.udp_state()
            if st is None:
                st = self.arm.state()
            # 2) 双相机最新帧
            (t_top, f_top), (t_wrist, f_wrist) = self.cams.get()
            ts = time.time()
            if f_top is None or f_wrist is None:
                next_t += period
                continue
            # 3) 写视频
            self.writers["cam_top.mp4"].write(f_top)
            self.writers["cam_wrist.mp4"].write(f_wrist)
            # 4) 记录状态
            self.rows.append(dict(
                timestamp=ts - t_start,
                frame_index=n_written,
                joint=np.asarray(st["joint"], dtype=np.float32),          # 6, 度
                pose=np.asarray(st["pose"], dtype=np.float32),            # 3, mm
                euler=np.asarray(st["euler"], dtype=np.float32),          # 3, rad
                en_flag=np.asarray(st["en_flag"], dtype=np.int32),        # 6
                err_code=np.asarray(st["err_code"], dtype=np.int32),      # 6
                gripper_cmd=np.float32(self._get_gripper_cmd()),          # 1, 0~1
                gripper_pos=np.float32(self._get_gripper_pos()),          # 1, 0~1 实际
            ))
            n_written += 1
            next_t += period
            if next_t < time.time() - period:
                next_t = time.time()   # 落后太多则重置节拍

    # ----------  保存 ----------
    def _save(self):
        n = len(self.rows)
        if n == 0:
            return None
        arr_ts = np.array([r["timestamp"] for r in self.rows], dtype=np.float64)
        joint = np.stack([r["joint"] for r in self.rows])
        pose = np.stack([r["pose"] for r in self.rows])
        euler = np.stack([r["euler"] for r in self.rows])
        en = np.stack([r["en_flag"] for r in self.rows])
        err = np.stack([r["err_code"] for r in self.rows])
        grip = np.array([r["gripper_cmd"] for r in self.rows], dtype=np.float32)
        gpos = np.array([r["gripper_pos"] for r in self.rows], dtype=np.float32)
        np.savez(os.path.join(self.ep_dir, "states.npz"),
                 timestamps=arr_ts, joint=joint, pose=pose, euler=euler,
                 en_flag=en, err_code=err, gripper_cmd=grip, gripper_pos=gpos)
        meta = dict(
            episode_index=self.episode_index,
            task=getattr(self, "current_task", "unknown"),
            fps=self.fps,
            frames=n,
            duration=float(arr_ts[-1] - arr_ts[0]) if n > 1 else 0.0,
            created=time.strftime("%Y-%m-%d %H:%M:%S"),
            arm_ip=self.arm.ip,
            arm_type="GEN65-BI",
            cameras=["cam_top.mp4", "cam_wrist.mp4"],
            state_names=["joint(6,deg)", "pose(3,mm)", "euler(3,rad)",
                         "en_flag(6)", "err_code(6)", "gripper_cmd(1)", "gripper_pos(1)"],
        )
        with open(os.path.join(self.ep_dir, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        self.episode_index += 1
        return meta
