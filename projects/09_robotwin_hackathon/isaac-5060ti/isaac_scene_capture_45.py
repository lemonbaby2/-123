"""Isaac Sim 4.5 standalone headless 场景捕获。

用 RTX 渲染 + PhysX 物理 + Camera 传感器，绕轨拍摄一堆刚体下落，输出 H.264 mp4。

针对 Isaac Sim 4.5.0 —— SimulationApp 在 `isaacsim.simulation_app`（5.x 才挪到 `isaacsim`）。

用法:
    set OMNI_KIT_ACCEPT_EULA=YES
    python -u isaac_scene_capture_45.py --out out.mp4 --frames 210
"""

import os

os.environ.setdefault("OMNI_KIT_ACCEPT_EULA", "YES")

import argparse  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--frames", type=int, default=210)
parser.add_argument("--out", default="isaac_scene.mp4")
parser.add_argument("--width", type=int, default=1280)
parser.add_argument("--height", type=int, default=720)
parser.add_argument("--renderer", default="RaytracedLighting")
# experience 留空 = 用 Isaac Sim 默认 experience（**必须**：isaacsim.sensors.camera
# 这个扩展只在默认 experience 里被加载；Isaac Lab 的 headless.rendering.kit 不带它，
# 会报 ModuleNotFoundError: No module named 'isaacsim.sensors'）。
# 注意：**绝对不要把 Anaconda 的 Library/bin 加进 PATH**，会让 isaacsim.robot.wheeled_robots
# 里的 osqp 原生扩展在加载时段错误（崩溃点在 ld-linux 里）。
parser.add_argument("--experience", default="")
args = parser.parse_args()

from isaacsim.simulation_app import SimulationApp  # noqa: E402

CFG = {
    "headless": True,
    "renderer": args.renderer,
    "width": args.width,
    "height": args.height,
    "hide_ui": True,
}
if args.experience:
    CFG["experience"] = args.experience

kit = SimulationApp(CFG)

import numpy as np  # noqa: E402

from isaacsim.core.api import World  # noqa: E402
from isaacsim.core.api.objects import (  # noqa: E402
    DynamicCapsule,
    DynamicCone,
    DynamicCuboid,
    DynamicCylinder,
    DynamicSphere,
)
from isaacsim.sensors.camera import Camera  # noqa: E402

# ---------------------------------------------------------------- 场景搭建
world = World(stage_units_in_meters=1.0)
world.scene.add_default_ground_plane()

# 补一盏平行光，否则只有环境光会显得很平
try:
    import omni.usd  # noqa: E402
    from pxr import Sdf, UsdLux  # noqa: E402

    stage = omni.usd.get_context().get_stage()
    light = UsdLux.DistantLight.Define(stage, Sdf.Path("/World/DistantLight"))
    light.CreateIntensityAttr(2200.0)
    light.CreateAngleAttr(0.53)
    xf = light.Prim.GetAttribute("xformOp:rotateXYZ")
    if not xf:
        from pxr import UsdGeom  # noqa: E402

        UsdGeom.Xformable(light.Prim).AddRotateXYZOp().Set((-45.0, 30.0, 0.0))
except Exception as e:  # noqa: BLE001
    print(f"[warn] 灯光设置失败（不影响物理与物理渲染）: {e}", flush=True)

# 物件：立方体 / 球 / 圆锥 / 圆柱 / 胶囊，摆成两圈错落堆叠
SPEC = [
    # (构造类, 颜色, 位置, 缩放)
    (DynamicCuboid, [0.15, 0.55, 0.90], [-1.2, 0.0, 3.4], [0.4, 0.4, 0.4]),
    (DynamicSphere, [0.95, 0.60, 0.15], [-0.9, 0.25, 2.9], [0.32, 0.32, 0.32]),
    (DynamicCone, [0.35, 0.80, 0.35], [0.0, 0.0, 3.2], [0.30, 0.30, 0.30]),
    (DynamicCylinder, [0.85, 0.30, 0.35], [0.9, -0.2, 2.7], [0.28, 0.28, 0.28]),
    (DynamicCapsule, [0.55, 0.35, 0.85], [1.5, 0.15, 3.1], [0.26, 0.26, 0.26]),
    (DynamicCuboid, [0.20, 0.75, 0.70], [-1.0, 0.6, 1.9], [0.34, 0.34, 0.34]),
    (DynamicSphere, [0.90, 0.85, 0.30], [0.2, -0.5, 1.7], [0.28, 0.28, 0.28]),
    (DynamicCone, [0.70, 0.45, 0.25], [1.1, 0.4, 1.8], [0.26, 0.26, 0.26]),
]

objects = []
for i, (cls, color, pos, scale) in enumerate(SPEC):
    obj = world.scene.add(
        cls(
            prim_path=f"/World/obj_{i}",
            name=f"obj_{i}",
            position=np.array(pos, dtype=float),
            scale=np.array(scale, dtype=float),
            color=np.array(color, dtype=float),
        )
    )
    objects.append(obj)

camera = Camera(
    prim_path="/World/orbit_cam",
    position=np.array([6.5, -6.5, 4.2]),
    resolution=(args.width, args.height),
)
camera.set_local_pose(translation=np.array([6.5, -6.5, 4.2]), orientation=None)
camera.initialize()

world.reset()
print("[INFO] 场景就绪，开始绕轨拍摄", flush=True)

# ---------------------------------------------------------------- 绕轨拍摄
import cv2  # noqa: E402

tmp_raw = args.out.replace(".mp4", "_raw.mp4")
writer = cv2.VideoWriter(tmp_raw, cv2.VideoWriter_fourcc(*"mp4v"), 30, (args.width, args.height))

radius = 7.2
height = 3.6
saved = 0

for i in range(args.frames):
    world.step(render=True)

    theta = np.deg2rad(135.0) + 2.0 * np.pi * (i / args.frames) * 0.85
    camera.set_world_pose(
        position=np.array(
            [radius * np.cos(theta), radius * np.sin(theta), height + 0.8 * np.sin(i / 18.0)]
        ),
        orientation=np.array([0.5, 0.5, 0.5, 0.5]),
        camera_axes="usd",
    )

    rgba = camera.get_rgba()
    if rgba is not None:
        frame = rgba[:, :, :3].astype(np.uint8)
        writer.write(frame[:, :, ::-1])  # RGB -> BGR
        saved += 1
    if i % 15 == 0:
        print(f"frame {i}/{args.frames} (已写 {saved})", flush=True)

writer.release()
print(f"[INFO] 原始帧写入完成: {saved}/{args.frames}", flush=True)
kit.close()

# ---------------------------------------------------------------- 转成 H.264
import subprocess  # noqa: E402

tmp_h264 = args.out.replace(".mp4", "_h264.mp4")
# 用绝对路径调用 ffmpeg，**不要**把 Anaconda 的 Library/bin 塞进 PATH
FFMPEG = r"D:\Anaconda\Library\bin\ffmpeg.exe"
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"
subprocess.run(
    [
        FFMPEG, "-y", "-loglevel", "error", "-i", tmp_raw,
        "-an", "-c:v", "libx264", "-crf", "22", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp_h264,
    ],
    check=False,
)
if os.path.exists(tmp_h264) and os.path.getsize(tmp_h264) > 0:
    os.replace(tmp_h264, args.out)
    try:
        os.remove(tmp_raw)
    except OSError:
        pass
    print(f"DONE {args.out} {os.path.getsize(args.out)} bytes", flush=True)
else:
    os.replace(tmp_raw, args.out)
    print(f"DONE(fallback) {args.out}（ffmpeg 未生效，保留 mp4v）", flush=True)
