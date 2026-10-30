"""双/三相机采集线程 —— v2（2026-10-25 实测重构）

与 v1 的差别（全部基于 <ROBOT_USER> 实测，非推测）：
  1. 设备用 /dev/v4l/by-id 解析，不再写死 /dev/videoN
     —— 实测 video0 会因 USB 反复重枚举而"凭空出现/消失"，节点号不可靠。
  2. 每路独立分辨率 / 帧率请求 / 图像参数（A68-1600W 原生支持 1920x1080）。
  3. 帧序号 seq 递增 —— record.py 靠它判断"是不是新帧"，
     避免 30Hz 循环把同一帧重复写进 mp4（v1 的致命 bug：mp4 变成 2 倍速）。
  4. 启动自检打印每路协商结果 + 实测帧率，不达标直接告警。

实测硬约束（2026-10-25 于 <ROBOT_HOSTNAME> / <ROBOT_USER>）：
  * 两台 UVC 相机都挂在 USB2.0 480M 的 Bus001 同一条总线上。
  * 单路可 30fps；两路同开 → 各 15.5fps；三路同开 → 各 8.3fps。
    这是总线带宽对半分，改曝光/改分辨率都救不回来。
  * 想让两路都跑 30fps：必须把其中一路挪到 USB3.0 口（Bus002）。
    前提是先解决 Bus002 上那个每 15~90 秒掉线重连的 GenesysLogic USB3.1 Hub。
  * Generic HD Camera（video2）帧率请求是 2 倍关系：请求 60 才得到 30fps。
    A68-1600W（video6）没有这个关系，请求多少给多少（但受总线限制）。

用法：
    cams = Cameras()          # 默认 top=Generic HD Camera, wrist=A68-1600W
    cams.start()              # 返回每路的 OK/FAIL 说明
    (ts, frame, seq), ... = cams.get()
"""
import os
import glob
import time
import threading

import cv2

BY_ID_DIR = "/dev/v4l/by-id"


def resolve_dev(name_hint, index=0):
    """把 by-id 名字片段解析成真实 /dev/videoN，找不到再回退。

    name_hint: by-id 里出现的关键字（大小写不敏感），例如 'A68-1600W'
    index:     -video-index0 / index1，UVC 的 index0 是采集口，index1 是 metadata
    """
    if not os.path.isdir(BY_ID_DIR):
        return None
    want = f"-video-index{index}"
    cands = [p for p in glob.glob(os.path.join(BY_ID_DIR, "*"))
             if want in p and name_hint.lower() in os.path.basename(p).lower()]
    if not cands:
        return None
    real = os.path.realpath(sorted(cands)[0])
    return real if os.path.exists(real) else None


def list_video_devices():
    """枚举当前所有 /dev/videoN 及其名字，用于自检日志"""
    out = []
    for p in sorted(glob.glob("/dev/video*"),
                    key=lambda x: int("".join(c for c in x if c.isdigit()) or 0)):
        name = ""
        try:
            with open(f"/sys/class/video4linux/{os.path.basename(p)}/name") as f:
                name = f.read().strip()
        except Exception:
            name = "?"
        out.append((p, name))
    return out


class CameraWorker(threading.Thread):
    """持续抓帧，只保留最新一帧（丢弃过期帧，保证低延迟）。seq 用于判断新帧。"""

    def __init__(self, name, dev, width=640, height=480, fps=30, fps_req=None,
                 brightness=None, contrast=None, saturation=None, gamma=None,
                 gain=None, exposure=None, auto_exposure=None, fourcc="MJPG"):
        super().__init__(daemon=True)
        self.name = name
        self.dev = dev                      # 真实路径 /dev/videoN
        self.width, self.height = width, height
        self.fps = fps
        # fps_req: 实际发给驱动的帧率请求值。Generic HD Camera 需要 2 倍才能拿到目标值。
        self.fps_req = fps_req if fps_req is not None else fps
        self.brightness, self.contrast = brightness, contrast
        self.saturation, self.saturation = saturation, saturation
        self.gamma, self.gain = gamma, gain
        self.exposure, self.auto_exposure = exposure, auto_exposure
        self.fourcc = fourcc

        self.cap = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.latest = None                  # (ts, frame)
        self.seq = 0
        self.frame_count = 0
        self.fps_measured = 0.0
        self.real_w = self.real_h = 0
        self.ok = False
        self.err = ""

    # ---------------- 打开 ----------------
    def open(self):
        self.cap = cv2.VideoCapture(self.dev, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            self.err = f"cannot open {self.dev}"
            return False
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*self.fourcc))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps_req)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if self.auto_exposure is not None:
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, self.auto_exposure)
        for prop, val in ((cv2.CAP_PROP_BRIGHTNESS, self.brightness),
                          (cv2.CAP_PROP_CONTRAST, self.contrast),
                          (cv2.CAP_PROP_GAMMA, self.gamma),
                          (cv2.CAP_PROP_GAIN, self.gain),
                          (cv2.CAP_PROP_EXPOSURE, self.exposure)):
            if val is not None:
                self.cap.set(prop, val)

        ok, fr = False, None
        for _ in range(10):                 # 有些 UVC 首帧要等 1~2 秒
            ok, fr = self.cap.read()
            if ok and fr is not None:
                break
            time.sleep(0.2)
        if not ok or fr is None:
            self.err = f"no frame from {self.dev}"
            return False

        self.real_h, self.real_w = fr.shape[0], fr.shape[1]
        with self._lock:
            self.latest = (time.time(), fr)
            self.seq = 1
            self.frame_count = 1
        self.ok = True
        return True

    # ---------------- 抓帧循环 ----------------
    def run(self):
        n, t0 = 0, time.time()
        while not self._stop.is_set():
            ok, fr = self.cap.read()
            if not ok or fr is None:
                time.sleep(0.003)
                continue
            ts = time.time()
            with self._lock:
                self.latest = (ts, fr)
                self.seq += 1
                self.frame_count += 1
            n += 1
            if n % 30 == 0:
                dt = time.time() - t0
                if dt > 0:
                    self.fps_measured = n / dt
                n, t0 = 0, time.time()
        if self.cap:
            self.cap.release()

    # ---------------- 取值 ----------------
    def get(self):
        """返回 (ts, frame, seq)"""
        with self._lock:
            if self.latest is None:
                return (None, None, 0)
            ts, fr = self.latest
            return (ts, fr, self.seq)

    def stop(self):
        self._stop.set()


class Cameras:
    """多路相机集合。默认 top + wrist 两路；可加 tof（iHawk100 深度，需单独解析）。"""

    # 实测得到的设备签名（by-id 关键字）；换机器/换相机时改这里就行
    SIGNATURES = {
        "top":   "Generic_HD_Camera",       # 1e45:0209  HD Camera        实测 video2
        "wrist": "A68-1600W",               # SunplusIT A68-1600W         实测 video6
        "tof":   "iHawk100",                # Berxel iHawk100 (ToF)       实测 video0
    }

    def __init__(self):
        self.workers = {}
        # ---------------- top：顶部全景（640x480 够，帧率优先）----------------
        self.workers["top"] = CameraWorker(
            "top", resolve_dev("Generic_HD_Camera") or "/dev/video2",
            width=640, height=480,
            fps=30, fps_req=60,              # 实测：此机型请求 60 才得到 30fps
            brightness=64, contrast=100, gamma=300, gain=128,
            auto_exposure=3,
        )
        # ---------------- wrist：腕部特写（原生 1920x1080，带宽够时可上 1080p）--
        self.workers["wrist"] = CameraWorker(
            "wrist", resolve_dev("A68-1600W") or "/dev/video6",
            width=640, height=480,           # 双路同总线时只能 480p/15fps；
                                             # 挪到 USB3 口后改成 1920x1080
            fps=30, fps_req=60,
            brightness=255, contrast=95, gamma=300, gain=128,
            auto_exposure=3,
        )
        self.bandwidth_share = False         # 启动自检时置位

    # ---------------- 生命周期 ----------------
    def start(self, probe_seconds=2.5):
        msgs = []
        for c in self.workers.values():
            if c.open():
                c.start()
                msgs.append(f"{c.name}({c.dev}) OK {c.real_w}x{c.real_h}")
            else:
                msgs.append(f"{c.name}({c.dev}) FAIL: {c.err}")

        time.sleep(probe_seconds)            # 让 fps_measured 有样本

        lines = []
        for c in self.workers.values():
            if c.ok:
                lines.append(f"{c.name}: {c.real_w}x{c.real_h} 实测 {c.fps_measured:.1f}fps "
                             f"(请求 {c.fps_req})")
            else:
                lines.append(f"{c.name}: FAIL {c.err}")
        msgs.extend(lines)

        # 带宽自检：多路同时开门且实测帧率都只有目标的一半，说明在分总线带宽
        ok_workers = [c for c in self.workers.values() if c.ok]
        if len(ok_workers) >= 2:
            low = [c for c in ok_workers if c.fps_measured < c.fps * 0.8]
            if len(low) >= 2:
                self.bandwidth_share = True
                msgs.append(
                    "[WARN] 多路共用 USB2.0 带宽：实测帧率约为目标的一半。"
                    "要两路都 30fps，需把一路挪到 USB3.0 口。"
                )
        return msgs

    def get(self, name):
        w = self.workers.get(name)
        return w.get() if w else (None, None, 0)

    def get_all(self):
        return {n: w.get() for n, w in self.workers.items()}

    def stats(self):
        return {n: (f"{w.fps_measured:.1f}fps", w.frame_count, w.ok)
                for n, w in self.workers.items()}

    def effective_fps(self):
        """所有启用相机里最低的实测帧率 —— record.py 用它决定 mp4 的写入帧率"""
        vals = [w.fps_measured for w in self.workers.values() if w.ok and w.fps_measured > 0]
        return min(vals) if vals else 0.0

    def stop(self):
        for w in self.workers.values():
            w.stop()
        time.sleep(0.3)


# ---------------- 向后兼容 v1 接口 ----------------
class DualCameras(Cameras):
    """v1 兼容层：老代码 (`DualCameras()` + `.start()` + `.get()->((t,f),(t,f))`) 不用改。"""

    def get(self, name=None):
        if name:
            return super().get(name)
        t_top, f_top, _ = super().get("top")
        t_wrist, f_wrist, _ = super().get("wrist")
        return (t_top, f_top), (t_wrist, f_wrist)


if __name__ == "__main__":
    print("=== 当前 /dev/video* ===")
    for p, n in list_video_devices():
        print(f"  {p}: {n}")
    print("\n=== by-id 解析 ===")
    for k in Cameras.SIGNATURES:
        print(f"  {k:6s} -> {resolve_dev(Cameras.SIGNATURES[k])}")

    print("\n=== 启动自检 ===")
    cams = Cameras()
    for m in cams.start():
        print(" ", m)
    print("\n=== 采样 5 秒 ===")
    t0 = time.time()
    last_seq = {}
    while time.time() - t0 < 5:
        for n, (ts, fr, seq) in cams.get_all().items():
            if seq != last_seq.get(n):
                last_seq[n] = seq
        time.sleep(0.01)
    for n, (fps, cnt, ok) in cams.stats().items():
        print(f"  {n}: {fps} frames={cnt} ok={ok}")
    print(f"  effective_fps={cams.effective_fps():.1f}")
    cams.stop()
