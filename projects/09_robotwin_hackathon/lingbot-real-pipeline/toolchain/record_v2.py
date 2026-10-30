"""同步采集 v2 —— 修正 v1 的「2 倍速视频」致命 bug

v1 的问题（实测确认）：
  主循环按 30Hz 节拍，每一拍都从相机取「最新帧」并写进 mp4。
  但两台相机实际只能出 15.5fps（USB2.0 总线对半分），
  于是每个真相位被写两次，mp4 以 30fps 播放 → 视频是真实速度的 2 倍。
  结果：动作与视觉观测在时间轴上错位一倍，VLA 训练直接学到 2 倍速动作。

v2 的做法：
  * 用帧序号 seq 判断「是否新帧」，只在真正拿到新帧时才写 mp4，绝不重复写。
  * mp4 的写入帧率用启动时实测的 effective_fps，不是写死的 30。
  * 视频尺寸从实际帧 shape 取（cams_v2 允许每路不同分辨率）。
  * meta.json 记录实测帧率 / 每路真实帧数 / 是否处于总线带宽共享状态，
    下游 build_dataset.py 按 fps 切 chunk 时用得上。

依赖：cams_v2.py（提供 get(name) -> (ts, frame, seq)）
"""
import os
import json
import time
import threading

import numpy as np
import cv2


class Recorder:
    def __init__(self, arm, cams, out_dir, fps=None, cam_names=("top", "wrist")):
        self.arm = arm
        self.cams = cams
        self.out_dir = out_dir
        self.requested_fps = fps           # None = 用实测帧率
        self.cam_names = list(cam_names)
        self.recording = False
        self._thread = None
        self._stop_evt = threading.Event()
        self.rows = []
        self.writers = {}
        self.ep_dir = None
        self.write_fps = 0.0
        self.per_cam_frames = {n: 0 for n in self.cam_names}
        self.dup_dropped = 0               # 被丢弃的重复帧计数（自检用）

        self.gripper_cmd = 0.0
        self._gripper_lock = threading.Lock()
        self.episode_index = 0
        self._grip_pos = 0.0
        self._grip_stop = threading.Event()
        self._grip_thread = threading.Thread(target=self._gripper_poll, daemon=True)
        self._grip_thread.start()

    # ---------------- 夹爪轮询（与主循环解耦，10Hz）----------------
    def _gripper_poll(self):
        while not self._grip_stop.is_set():
            try:
                r = self.arm.cmd({"command": "get_gripper_state"}, timeout=2)
                with self._gripper_lock:
                    self._grip_pos = float(r.get("actpos", 0)) / 1000.0
            except Exception:
                pass
            self._grip_stop.wait(0.1)

    def set_gripper_cmd(self, pos_0_1):
        with self._gripper_lock:
            self.gripper_cmd = float(pos_0_1)

    def _get_gripper_cmd(self):
        with self._gripper_lock:
            return self.gripper_cmd

    def _get_gripper_pos(self):
        with self._gripper_lock:
            return self._grip_pos

    # ---------------- episode 控制 ----------------
    def start_episode(self, task="pick_place"):
        os.makedirs(self.out_dir, exist_ok=True)
        self.ep_dir = os.path.join(self.out_dir, f"episode_{self.episode_index:06d}")
        os.makedirs(self.ep_dir, exist_ok=True)
        self.rows = []
        self.current_task = task
        self.dup_dropped = 0

        # 用实测帧率决定 mp4 写入帧率（关键：不能写死 30）
        meas = self.cams.effective_fps()
        self.write_fps = float(self.requested_fps or (meas if meas > 1 else 15.0))
        self.write_fps = round(self.write_fps, 2)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writers = {}
        for n in self.cam_names:
            ts, fr, _ = self.cams.get(n)
            if fr is None:
                raise RuntimeError(f"相机 {n} 无帧，无法开始录制")
            h, w = fr.shape[:2]
            self.writers[n] = cv2.VideoWriter(
                os.path.join(self.ep_dir, f"cam_{n}.mp4"), fourcc, self.write_fps, (w, h))
            self.per_cam_frames[n] = 0

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
        self.writers = {}
        return self._save()

    # ---------------- 主循环：事件驱动，新帧才写 ----------------
    def _loop(self, task):
        last_seq = {n: -1 for n in self.cam_names}
        t_start = time.time()
        n_written = 0
        pair_timeout = 0.25          # 等不齐一对新帧时的最长等待
        min_interval = 1.0 / max(1.0, self.write_fps * 1.5)   # 防止超频写入

        while not self._stop_evt.is_set():
            frames = {}
            fresh = 0
            deadline = time.time() + pair_timeout
            # 等到每一路都出现新帧（或超时）
            while time.time() < deadline and not self._stop_evt.is_set():
                fresh = 0
                for n in self.cam_names:
                    ts, fr, seq = self.cams.get(n)
                    if fr is None:
                        continue
                    if seq != last_seq[n]:
                        frames[n] = (ts, fr, seq)
                        fresh += 1
                if fresh == len(self.cam_names):
                    break
                time.sleep(0.002)

            if fresh == 0:
                self.dup_dropped += 1
                time.sleep(min_interval)
                continue

            # 只用全部到齐的那一批；缺帧就用上一次的（标记为 hold）
            now = time.time()
            st, age = self.arm.udp_state()
            if st is None:
                st = self.arm.state()

            for n in self.cam_names:
                if n in frames:
                    ts, fr, seq = frames[n]
                    self.writers[n].write(fr)
                    last_seq[n] = seq
                    self.per_cam_frames[n] += 1

            self.rows.append(dict(
                timestamp=now - t_start,
                frame_index=n_written,
                joint=np.asarray(st["joint"], dtype=np.float32),
                pose=np.asarray(st["pose"], dtype=np.float32),
                euler=np.asarray(st["euler"], dtype=np.float32),
                en_flag=np.asarray(st["en_flag"], dtype=np.int32),
                err_code=np.asarray(st["err_code"], dtype=np.int32),
                gripper_cmd=np.float32(self._get_gripper_cmd()),
                gripper_pos=np.float32(self._get_gripper_pos()),
            ))
            n_written += 1

    # ---------------- 保存 ----------------
    def _save(self):
        n = len(self.rows)
        if n == 0:
            return None
        arr_ts = np.array([r["timestamp"] for r in self.rows], dtype=np.float64)
        np.savez(
            os.path.join(self.ep_dir, "states.npz"),
            timestamps=arr_ts,
            joint=np.stack([r["joint"] for r in self.rows]),
            pose=np.stack([r["pose"] for r in self.rows]),
            euler=np.stack([r["euler"] for r in self.rows]),
            en_flag=np.stack([r["en_flag"] for r in self.rows]),
            err_code=np.stack([r["err_code"] for r in self.rows]),
            gripper_cmd=np.array([r["gripper_cmd"] for r in self.rows], dtype=np.float32),
            gripper_pos=np.array([r["gripper_pos"] for r in self.rows], dtype=np.float32),
        )

        # 实测帧率：用时间戳算，而不是用标称值
        dur = float(arr_ts[-1] - arr_ts[0]) if n > 1 else 0.0
        real_fps = (n - 1) / dur if dur > 0 else 0.0
        cam_stats = {}
        for name, cnt in self.per_cam_frames.items():
            cam_stats[name] = dict(frames=cnt,
                                   fps=round(cnt / dur, 2) if dur > 0 else 0.0)

        meta = dict(
            episode_index=self.episode_index,
            task=getattr(self, "current_task", "unknown"),
            fps=round(real_fps, 2),                  # 实测，不是标称
            fps_write=self.write_fps,                # mp4 容器帧率
            fps_requested_effective=self.cams.effective_fps(),
            frames=n,
            duration=round(dur, 3),
            created=time.strftime("%Y-%m-%d %H:%M:%S"),
            arm_ip=self.arm.ip,
            arm_type="GEN65-BI",
            cameras=[f"cam_{n}.mp4" for n in self.cam_names],
            camera_stats=cam_stats,
            fabric=dict(bandwidth_share=bool(getattr(self.cams, "bandwidth_share", False)),
                        note="bus_sharing=True 表示多路共用 USB2.0 带宽，帧率约减半"),
            state_names=["joint(6,deg)", "pose(3,mm)", "euler(3,rad)",
                         "en_flag(6)", "err_code(6)", "gripper_cmd(1)", "gripper_pos(1)"],
        )
        with open(os.path.join(self.ep_dir, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        self.episode_index += 1
        return meta
