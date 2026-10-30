"""双相机 30Hz 采集线程（Berxel iHawk100, UVC MJPG）
暗光环境提亮：video2 亮度64/对比度100/伽马300；video6 亮度255/对比度95/伽马300
"""
import cv2, threading, time


class CameraWorker(threading.Thread):
    """持续抓帧，只保留最新一帧（丢弃过期帧，保证低延迟）"""

    def __init__(self, name, device, width=640, height=480, fps=30,
                 brightness=64, contrast=100, saturation=100, gamma=300):
        super().__init__(daemon=True)
        self.name, self.device = name, device
        self.width, self.height, self.fps = width, height, fps
        self.brightness, self.contrast = brightness, contrast
        self.saturation, self.gamma = saturation, gamma
        self.cap = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.latest = None      # (timestamp, frame)
        self.frame_count = 0
        self.fps_measured = 0.0
        self.ok = False
        self.err = ""

    def open(self):
        self.cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not self.cap.isOpened():
            self.err = f"cannot open {self.device}"
            return False
        # ---- 暗光提亮（曝光/增益已由固件顶格，这里推亮度/对比度/伽马）----
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)      # 手动曝光
        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness)
        self.cap.set(cv2.CAP_PROP_CONTRAST, self.contrast)
        self.cap.set(cv2.CAP_PROP_SATURATION, self.saturation)
        self.cap.set(cv2.CAP_PROP_GAMMA, self.gamma)
        self.cap.set(cv2.CAP_PROP_GAIN, 128)
        ok, fr = self.cap.read()
        if not ok or fr is None:
            self.err = f"no frame from {self.device}"
            return False
        self.ok = True
        return True

    def run(self):
        n, t0 = 0, time.time()
        while not self._stop.is_set():
            ok, fr = self.cap.read()
            if not ok or fr is None:
                time.sleep(0.005)
                continue
            ts = time.time()
            with self._lock:
                self.latest = (ts, fr)
                self.frame_count += 1
            n += 1
            if n % 60 == 0:
                dt = time.time() - t0
                self.fps_measured = n / dt if dt > 0 else 0
                n, t0 = 0, time.time()
        if self.cap:
            self.cap.release()

    def get(self):
        with self._lock:
            return self.latest

    def stop(self):
        self._stop.set()


class DualCameras:
    def __init__(self, top_dev="/dev/video2", wrist_dev="/dev/video6",
                 width=640, height=480, fps=30):
        # video2(top): brightness 上限 64; video6(wrist): brightness 上限 255
        self.top = CameraWorker("top", top_dev, width, height, fps,
                                brightness=64, contrast=100, gamma=300)
        self.wrist = CameraWorker("wrist", wrist_dev, width, height, fps,
                                  brightness=255, contrast=95, gamma=300)

    def start(self):
        r = []
        for c in (self.top, self.wrist):
            if c.open():
                c.start()
                r.append(f"{c.name}({c.device}) OK")
            else:
                r.append(f"{c.name}({c.device}) FAIL: {c.err}")
        return r

    def get(self):
        return self.top.get(), self.wrist.get()

    def stats(self):
        return (f"top: {self.top.fps_measured:.1f}fps frames={self.top.frame_count}",
                f"wrist: {self.wrist.fps_measured:.1f}fps frames={self.wrist.frame_count}")

    def stop(self):
        self.top.stop(); self.wrist.stop()
