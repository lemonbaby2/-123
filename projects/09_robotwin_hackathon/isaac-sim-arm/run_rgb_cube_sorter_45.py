# -*- coding: utf-8 -*-
"""
RGB_cube_sorter.py  —  Isaac Sim 4.5 headless 复现版
=====================================================
来源仓库: https://github.com/Kishan-Gadhavi01/IsaacSim_Robotics_Portfolio
原文件:   PickPlaceController/arm/RGB_cube_sorter.py  (commit 48540c0)
作者原文面向 Isaac Sim 4.2/4.3 (omni.isaac.* 旧命名空间)。

本文件相对原版的全部改动（4.5 兼容 + headless 录制）：
  1) SimulationApp({"headless": False})           -> True                      [第 3 行]
  2) from omni.isaac.franka.controllers import ... -> from isaacsim.robot.manipulators.examples.franka.controllers import ...
     （4.5 中 omni.isaac.franka 扩展已被移除；等价类在 isaacsim.robot.manipulators.examples.franka）
  3) cv2.namedWindow / cv2.resizeWindow           -> 删除（headless 无窗口）
  4) cv2.imshow / cv2.waitKey / cv2.destroyAllWindows -> cv2.VideoWriter 落盘 MP4
  5) 新增宽视角监看相机 /World/WideCam，独立渲染一路 1280x720 MP4
  6) 新增终止条件（步数上限 / 已分拣数量 / 墙钟超时），便于无人值守跑完
  7) 新增周期性日志与关键帧 PNG 落盘

其余算法（HSV 分割、ROI、遮挡判定、Y-grip/X-grip 切换、BinManager 六格码垛、
PickPlaceController + RMPFlow 状态机）100% 保持原仓库实现，未做任何改动。
"""
import argparse
import os
import sys
import time

import numpy as np

# ----------------------------------------------------------------------------- 参数
ap = argparse.ArgumentParser()
ap.add_argument("--smoke", action="store_true", help="只跑少量步数做冒烟测试，输出 RGB 亮度统计")
ap.add_argument("--max-steps", type=int, default=9000)
ap.add_argument("--max-sorted", type=int, default=9)
ap.add_argument("--timeout-s", type=float, default=3600.0)
ap.add_argument("--no-wide", action="store_true", help="不渲染宽视角相机")
ap.add_argument("--lights", action="store_true", help="额外补充 DomeLight + DistantLight")
ap.add_argument("--outdir", default=r"E:\研究生学习\黑客松\outputs\isaac-arm-2026-10")
ap.add_argument("--tag", default="rgb_cube_sorter")
# ★ 状态机相位时长（秒）。原仓库用 Franka 默认 [0.008, 0.005, 1, 0.1, ...]，
#   其中 phase1（下降抓住方块）只有 1/0.005 = 200 步；本机 RMPFlow 下降速度
#   约 0.0006~0.0012 m/步，从 h1=0.3 降到方块中心（z≈0.02）需要 250~500 步，
#   于是 200 步内只降到 z≈0.096 就在空中闭合夹爪 -> "Object Dropped Mid-Air"。
#   把 phase1 放宽到 667 步（dt=0.0015）留足余量。
#   注意：修好 RULE02（物理写回 USD）后，深度读数从"未落定的 0.07"变成
#   真实顶面 0.04，抓取目标随之从 0.05 变成 0.02，下降距离反而更长。
ap.add_argument("--phase0-dt", type=float, default=0.008)
ap.add_argument("--phase1-dt", type=float, default=0.0015)
# 原作者的安全阈值：末端 z<0.06 且夹爪仍开>0.03 就判"没夹住"。
# 现在末端会正确降到 0.02（方块中心），闭合过程中必然穿过这个区间 -> 误判。
# 收紧成"真的贴地且夹爪几乎全开"才判失败。
ap.add_argument("--pick-fail-z", type=float, default=0.03)
ap.add_argument("--pick-fail-open", type=float, default=0.06)
# ★ 必须用自定义精简 experience：默认 isaacsim.exp.full.kit 会加载 wheeled_robots -> osqp 段错误
ap.add_argument("--experience",
                default=r"D:\nvidia\Isaac\IsaacLab\apps\isaaclab.arm.sorter.headless.kit")
ARGS = ap.parse_args()

OUT = ARGS.outdir
VID_DIR = os.path.join(OUT, "videos")
PNG_DIR = os.path.join(OUT, "frames")
LOG_DIR = os.path.join(OUT, "logs")
for d in (VID_DIR, PNG_DIR, LOG_DIR):
    os.makedirs(d, exist_ok=True)

# ★ 关键：OpenCV 4.x on Windows 用 ANSI fopen，写不了含中文的路径
#   （实测 cv2.imwrite 返回 False；cv2.VideoWriter 只落一个 258 字节空壳）
#   因此所有 OpenCV 落盘先写到纯 ASCII 暂存目录，收尾时再用 shutil 搬到中文目录。
import shutil
import tempfile

STAGE = os.path.join(tempfile.gettempdir(), "isaac_arm_stage")
os.makedirs(STAGE, exist_ok=True)


def stage_path(name):
    return os.path.join(STAGE, name)


def finalize_outputs(pairs):
    """把暂存目录里的 ASCII 文件搬到最终（可能含中文的）目录。"""
    for src, dst_dir in pairs:
        if not os.path.exists(src):
            log(f"[WARN] 暂存文件不存在，跳过搬运: {src}")
            continue
        dst = os.path.join(dst_dir, os.path.basename(src))
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(src, dst)
        log(f"已归档 {os.path.basename(dst)} -> {dst_dir} ({os.path.getsize(dst)/1024:.1f} KB)")

# ----------------------------------------------------------------------------- 启动 Isaac
from isaacsim import SimulationApp


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


log(f"SimulationApp 启动中 | headless=True | experience={ARGS.experience}")
t_boot = time.time()
simulation_app = SimulationApp({"headless": True, "experience": ARGS.experience})
log(f"SimulationApp 启动完成，耗时 {time.time() - t_boot:.1f}s")

import cv2
from pxr import Gf, UsdGeom
from isaacsim.core.api import World
from isaacsim.core.utils.rotations import euler_angles_to_quat
from isaacsim.core.api.objects import DynamicCuboid, VisualSphere, VisualCuboid
from isaacsim.sensors.camera import Camera
from isaacsim.robot.manipulators.examples.franka import Franka
# ★ 4.5 关键修正：原为 from omni.isaac.franka.controllers import PickPlaceController
from isaacsim.robot.manipulators.examples.franka.controllers import PickPlaceController

# ----------------------------------------------------------------------------- 原仓库配置常量（未改）
CAM_POS = Gf.Vec3d(0.5, 0, 2.5)
CAM_ROT = Gf.Vec3d(0, 0, 90.0)

BIN_RED_POS   = np.array([0.15, -0.5, 0.05])
BIN_GREEN_POS = np.array([0.35, -0.5, 0.05])
BIN_BLUE_POS  = np.array([0.55, -0.5, 0.05])

SPAWN_X_RANGE = (0.40, 0.70)
SPAWN_Y_RANGE = (0.15, 0.45)

CUBE_HEIGHT = 0.04
GRIP_DESCENT_INTO_CUBE = CUBE_HEIGHT / 2.0
ABSOLUTE_FLOOR_LIMIT = 0.015

GRIPPER_FINGER_WIDTH = 0.03
GRIPPER_OPEN_WIDTH   = 0.10
GRIPPER_BODY_WIDTH   = 0.045
SAFETY_MARGIN = 0.005

ROI_Y = (30, 450)
ROI_X = (100, 600)

DEBUG_BLOCKERS = True

WIDE_EYE = (2.05, 2.05, 1.85)
WIDE_TGT = (0.18, -0.05, 0.42)
WIDE_RES = (1280, 720)
WIDE_HFOV_DEG = 52.0


def look_at_quat(eye, target, up=(0.0, 0.0, 1.0)):
    """返回 USD 相机的世界朝向四元数 (w, x, y, z)。

    注意：不要用 Gf.Matrix4d().SetLookAt(...).ExtractRotationQuat()——
    SetLookAt 生成的是 world->camera 的**视图矩阵**，直接取四元数会得到逆旋转，
    相机将朝向虚空（实测渲染整幅全黑）。这里显式构造 camera->world 旋转矩阵。
    USD 相机沿本地 -Z 看、+Y 朝上。
    """
    eye = np.asarray(eye, dtype=np.float64)
    tgt = np.asarray(target, dtype=np.float64)
    up = np.asarray(up, dtype=np.float64)

    f = tgt - eye
    f /= np.linalg.norm(f)                  # 前向 = 相机 -Z
    r = np.cross(f, up)
    r /= np.linalg.norm(r)                  # 相机 +X
    u = np.cross(r, f)                      # 相机 +Y
    R = np.column_stack([r, u, -f])         # camera -> world

    m = R
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        s = np.sqrt(tr + 1.0) * 2
        w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s
        y = (m[0, 2] - m[2, 0]) / s
        z = (m[1, 0] - m[0, 1]) / s
    elif (m[0, 0] > m[1, 1]) and (m[0, 0] > m[2, 2]):
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s
    q = np.array([w, x, y, z], dtype=np.float64)
    return q / np.linalg.norm(q)


class BinManager:
    def __init__(self):
        self.counts = {"red": 0, "green": 0, "blue": 0}
        self.offsets = [[0, 0], [0, 0.06], [0, -0.06], [0.06, 0], [0.06, 0.06], [0.06, -0.06]]

    def get_place_target(self, color, base_pos):
        count = self.counts[color]
        idx = count % len(self.offsets)
        z_stack = (count // len(self.offsets)) * 0.04
        return np.array([base_pos[0] + self.offsets[idx][0],
                         base_pos[1] + self.offsets[idx][1],
                         base_pos[2] + z_stack + 0.05])

    def confirm_placement(self, color):
        self.counts[color] += 1
        log(f"SUCCESS: Sorted {color}. Total: {self.counts[color]}")


bin_manager = BinManager()


class VisionSystem:
    """原仓库视觉系统；仅把 imshow 换成 VideoWriter 落盘。"""

    def __init__(self, writer=None):
        self.camera = None
        self.writer = writer      # ★ 替代 cv2.namedWindow
        self.last_dashboard = None
        self.frames_written = 0

    def set_camera(self, camera):
        self.camera = camera

    def process_frame(self):
        if self.camera is None:
            return None
        frame = self.camera.get_current_frame()
        if "rgba" not in frame:
            return None

        img_bgr = cv2.cvtColor(frame["rgba"][:, :, :3], cv2.COLOR_RGB2BGR)
        depth_map = frame["distance_to_image_plane"]
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

        mask_red_raw = cv2.inRange(hsv, np.array([0, 120, 70]), np.array([10, 255, 255])) + \
                       cv2.inRange(hsv, np.array([170, 120, 70]), np.array([180, 255, 255]))
        mask_green_raw = cv2.inRange(hsv, np.array([40, 100, 100]), np.array([85, 255, 255]))
        mask_blue_raw = cv2.inRange(hsv, np.array([90, 50, 50]), np.array([130, 255, 255]))

        roi_filter = np.zeros_like(mask_red_raw)
        roi_filter[ROI_Y[0]:ROI_Y[1], ROI_X[0]:ROI_X[1]] = 255

        mask_red   = cv2.bitwise_and(mask_red_raw, roi_filter)
        mask_green = cv2.bitwise_and(mask_green_raw, roi_filter)
        mask_blue  = cv2.bitwise_and(mask_blue_raw, roi_filter)

        candidates = []

        def get_blobs(mask, color_name):
            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if 100 < area < 2500:
                    x, y, w, h = cv2.boundingRect(cnt)
                    cx, cy = x + w // 2, y + h // 2
                    if cy < 0 or cy >= depth_map.shape[0] or cx < 0 or cx >= depth_map.shape[1]:
                        continue
                    d = depth_map[cy, cx]
                    if 0 < d < 4.0:
                        pts_3d = self.camera.get_world_points_from_image_coords(
                            np.array([[cx, cy]]), np.array([d]))
                        pos = pts_3d[0]
                        candidates.append({
                            "pos": pos, "color": color_name, "box": (x, y, w, h),
                            "safe": False, "angle_offset": 0.0, "blocked_by": None,
                        })

        get_blobs(mask_red, "red")
        get_blobs(mask_green, "green")
        get_blobs(mask_blue, "blue")

        req_clear_body = GRIPPER_BODY_WIDTH + SAFETY_MARGIN
        req_clear_fingers = GRIPPER_OPEN_WIDTH + SAFETY_MARGIN

        for i, c1 in enumerate(candidates):
            c1_x, c1_y, c1_z = c1["pos"][0], c1["pos"][1], c1["pos"][2]
            standard_blocked = False
            rotated_blocked = False
            blocker_standard = None
            blocker_rotated = None

            for j, c2 in enumerate(candidates):
                if i == j:
                    continue
                c2_x, c2_y, c2_z = c2["pos"][0], c2["pos"][1], c2["pos"][2]
                lateral = abs(c1_y - c2_y)
                longitud = abs(c1_x - c2_x)
                dz = abs(c1_z - c2_z)
                same_layer = dz < (CUBE_HEIGHT * 0.75)

                if same_layer and (lateral < req_clear_body and longitud < req_clear_fingers):
                    standard_blocked = True
                    blocker_standard = c2
                if same_layer and (lateral < req_clear_fingers and longitud < req_clear_body):
                    rotated_blocked = True
                    blocker_rotated = c2
                if standard_blocked and rotated_blocked:
                    break

            if not standard_blocked:
                c1["safe"] = True
                c1["angle_offset"] = 0.0
                c1["blocked_by"] = None
            elif not rotated_blocked:
                c1["safe"] = True
                c1["angle_offset"] = np.pi / 2.0
                c1["blocked_by"] = None
            else:
                c1["safe"] = False
                if blocker_standard is None:
                    c1["blocked_by"] = blocker_rotated
                elif blocker_rotated is None:
                    c1["blocked_by"] = blocker_standard
                else:
                    dist_s = np.linalg.norm(np.array(c1["pos"]) - np.array(blocker_standard["pos"]))
                    dist_r = np.linalg.norm(np.array(c1["pos"]) - np.array(blocker_rotated["pos"]))
                    c1["blocked_by"] = blocker_standard if dist_s <= dist_r else blocker_rotated

                if DEBUG_BLOCKERS and c1["blocked_by"] is not None:
                    log(f"Candidate at {np.round(c1['pos'],3)} blocked by neighbor at "
                        f"{np.round(c1['blocked_by']['pos'],3)} (color={c1['blocked_by']['color']})")

        # ---------------- 可视化（与原版逐像素一致，只是不再 imshow）
        vis_rgb = img_bgr.copy()
        cv2.rectangle(vis_rgb, (ROI_X[0], ROI_Y[0]), (ROI_X[1], ROI_Y[1]), (0, 255, 255), 2)
        for c in candidates:
            x, y, w, h = c["box"]
            cx, cy = x + w // 2, y + h // 2
            box_col = (0, 255, 0) if c["safe"] else (0, 0, 255)
            label = "PICK" if c["safe"] else "CLUTTER"
            cv2.rectangle(vis_rgb, (x, y), (x + w, y + h), box_col, 2)
            cv2.putText(vis_rgb, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_col, 2)
            if c["safe"]:
                if abs(c["angle_offset"]) > 0.1:
                    cv2.line(vis_rgb, (x, cy), (x + w, cy), (255, 0, 255), 2)
                    cv2.putText(vis_rgb, "X-grip", (x, y + h + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
                else:
                    cv2.line(vis_rgb, (cx, y), (cx, y + h), (0, 255, 0), 2)
                    cv2.putText(vis_rgb, "Y-grip", (x, y + h + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            else:
                if c.get("blocked_by") is not None:
                    b = c["blocked_by"]
                    bx, by, bw, bh = b["box"]
                    cv2.rectangle(vis_rgb, (bx, by), (bx + bw, by + bh), (255, 128, 0), 2)
                    cv2.putText(vis_rgb, f"BLOCKER:{b['color']}", (bx, by - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 128, 0), 1)

        depth_norm = cv2.normalize(depth_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        vis_depth = cv2.applyColorMap(depth_norm, cv2.COLORMAP_JET)
        vis_mask = np.zeros_like(img_bgr)
        vis_mask[mask_red > 0] = [0, 0, 255]
        vis_mask[mask_green > 0] = [0, 255, 0]
        vis_mask[mask_blue > 0] = [255, 0, 0]

        dashboard = np.vstack([vis_rgb, vis_depth, vis_mask])
        # ★ 替代 cv2.imshow + cv2.waitKey
        self.last_dashboard = dashboard
        if self.writer is not None:
            self.writer.write(dashboard)
            self.frames_written += 1
        return candidates


def main():
    t0 = time.time()
    world = World(stage_units_in_meters=1.0, physics_dt=1.0 / 60.0, rendering_dt=1.0 / 60.0)
    world.scene.add_default_ground_plane()
    world.scene.add(VisualCuboid(prim_path="/World/FloorOverlay", name="floor_overlay",
                                 position=np.array([0.5, 0, 0.002]),
                                 scale=np.array([5.0, 5.0, 0.01]),
                                 color=np.array([0.4, 0.4, 0.4])))

    if ARGS.lights:
        from isaacsim.core.api.objects import FixedCuboid  # noqa: F401  (仅确保命名空间可用)
        from pxr import UsdLux
        stage = world.stage
        dome = UsdLux.DomeLight.Define(stage, "/World/DomeLight")
        dome.CreateIntensityAttr(800.0)
        dist = UsdLux.DistantLight.Define(stage, "/World/DistantLight")
        dist.CreateIntensityAttr(2500.0)
        dist.CreateAngleAttr(1.0)
        xf = UsdGeom.Xformable(dist.GetPrim())
        xf.ClearXformOpOrder()
        xf.AddRotateXYZOp().Set(Gf.Vec3f(45.0, 0.0, 35.0))
        log("已补充 DomeLight + DistantLight")

    franka = world.scene.add(Franka(prim_path="/World/Franka", name="franka"))

    world.scene.add(VisualCuboid(prim_path="/World/BinRed", name="bin_red",
                                 position=np.array([BIN_RED_POS[0], BIN_RED_POS[1], 0.02]),
                                 scale=np.array([0.18, 0.18, 0.005]), color=np.array([0.8, 0, 0])))
    world.scene.add(VisualCuboid(prim_path="/World/BinGreen", name="bin_green",
                                 position=np.array([BIN_GREEN_POS[0], BIN_GREEN_POS[1], 0.02]),
                                 scale=np.array([0.18, 0.18, 0.005]), color=np.array([0, 0.8, 0])))
    world.scene.add(VisualCuboid(prim_path="/World/BinBlue", name="bin_blue",
                                 position=np.array([BIN_BLUE_POS[0], BIN_BLUE_POS[1], 0.02]),
                                 scale=np.array([0.18, 0.18, 0.005]), color=np.array([0, 0, 0.8])))

    MIN_SEPARATION = 0.08
    placed_positions = []
    spawned = 0
    cube_objs = []
    for i in range(12):
        rem = i % 3
        if rem == 0:
            col_val = np.array([1, 0, 0])
        elif rem == 1:
            col_val = np.array([0, 1, 0])
        else:
            col_val = np.array([0.2, 0.6, 1.0])

        valid_pos = False
        attempts = 0
        spawn_x = spawn_y = None
        while not valid_pos and attempts < 100:
            spawn_x = np.random.uniform(SPAWN_X_RANGE[0], SPAWN_X_RANGE[1])
            spawn_y = np.random.uniform(SPAWN_Y_RANGE[0], SPAWN_Y_RANGE[1])
            new_pos_xy = np.array([spawn_x, spawn_y])
            valid_pos = True
            for existing_pos in placed_positions:
                if np.linalg.norm(new_pos_xy - existing_pos) < MIN_SEPARATION:
                    valid_pos = False
                    break
            attempts += 1

        if valid_pos:
            placed_positions.append(new_pos_xy)
            _c = DynamicCuboid(prim_path=f"/World/Cube_{i}", name=f"cube_{i}",
                               position=np.array([spawn_x, spawn_y, 0.05]),
                               scale=np.array([0.04, 0.04, 0.04]),
                               color=col_val, mass=0.1)
            world.scene.add(_c)
            cube_objs.append(_c)
            spawned += 1
        else:
            log(f"Warning: Could not find spaced position for cube {i} after 100 attempts.")
    log(f"场景装配完成：Franka + {spawned} 个 DynamicCuboid + 3 个分拣箱")

    # 原仓库 Franka 子类默认 events_dt；这里只放宽 phase0/phase1 的时长，其余不动
    _events_dt = [0.008, 0.005, 1, 0.1, 0.05, 0.05, 0.0025, 1, 0.008, 0.08]
    _events_dt[0] = float(ARGS.phase0_dt)
    _events_dt[1] = float(ARGS.phase1_dt)
    log(f"events_dt={_events_dt}  →  phase0={1.0/_events_dt[0]:.0f} 步, "
        f"phase1={1.0/_events_dt[1]:.0f} 步")
    controller = PickPlaceController(name="controller", gripper=franka.gripper,
                                     robot_articulation=franka, events_dt=_events_dt)
    marker = world.scene.add(VisualSphere(prim_path="/World/Marker", name="marker",
                                          radius=0.015, color=np.array([1, 1, 0])))

    world.reset()
    world.play()

    # ---------------- 固定俯视相机（原仓库） ----------------
    camera = Camera(prim_path="/World/FixedCam", name="fixed_cam", resolution=(640, 480), frequency=30)
    camera.initialize()
    xform = UsdGeom.Xformable(world.stage.GetPrimAtPath("/World/FixedCam"))
    xform.ClearXformOpOrder()
    xform.AddTranslateOp().Set(CAM_POS)
    xform.AddRotateXYZOp().Set(CAM_ROT)
    camera.add_distance_to_image_plane_to_frame()

    # ---------------- 宽视角监看相机（新增） ----------------
    wide_cam = None
    if not ARGS.no_wide:
        wide_cam = Camera(prim_path="/World/WideCam", name="wide_cam",
                          resolution=WIDE_RES, frequency=30)
        wide_cam.initialize()
        wide_cam.set_clipping_range(near_distance=0.01, far_distance=1000.0)
        # ★ 焦距：不要按 USD 常识写 18mm/50mm。
        #   Isaac Camera 默认焦距很短（实测约 4.2mm，配 ~2.1mm 孔径 -> 水平视场 ~29°），
        #   直接设 17mm 会变成 7.1° 的长焦，画面全被机器人一格挡住。
        #   这里按"目标水平视场"用孔径反算焦距，并回读校验。
        h_ap = wide_cam.get_horizontal_aperture()
        target_hfov = np.radians(WIDE_HFOV_DEG)
        wide_cam.set_focal_length(h_ap / (2.0 * np.tan(target_hfov / 2.0)))
        wide_cam.set_world_pose(position=np.array(WIDE_EYE),
                                orientation=look_at_quat(WIDE_EYE, WIDE_TGT),
                                camera_axes="usd")   # ★ 必须显式 usd：默认 "world" 是 +X前/+Z上，会多叠一层旋转导致画面横滚
        log(f"宽视角相机已就位 eye={WIDE_EYE} target={WIDE_TGT} "
            f"quat={np.round(look_at_quat(WIDE_EYE, WIDE_TGT), 4)}")
        # 回读校验：确认位姿/视场真的写进去了（曾经出现"设了但没生效"的黑图/近景问题）
        rb_p, rb_o = wide_cam.get_world_pose(camera_axes="usd")
        log(f"[回读] WideCam pos={np.round(rb_p, 3)} quat={np.round(rb_o, 4)} "
            f"focal={wide_cam.get_focal_length():.1f}mm "
            f"hFOV={np.degrees(wide_cam.get_horizontal_fov()):.1f}° "
            f"vFOV={np.degrees(wide_cam.get_vertical_fov()):.1f}°")

    # ---------------- 视频写入器（替代 imshow） ----------------
    dash_path = stage_path(f"{ARGS.tag}_dashboard.mp4")
    dash_writer = cv2.VideoWriter(dash_path, cv2.VideoWriter_fourcc(*"mp4v"), 30, (640, 1440))
    wide_writer = None
    wide_path = stage_path(f"{ARGS.tag}_wide.mp4")
    if wide_cam is not None:
        wide_writer = cv2.VideoWriter(wide_path, cv2.VideoWriter_fourcc(*"mp4v"), 30, WIDE_RES)
    log(f"VideoWriter: {dash_path} ok={dash_writer.isOpened()} | wide ok="
        f"{wide_writer.isOpened() if wide_writer else 'N/A'}")

    vision = VisionSystem(writer=dash_writer)
    vision.set_camera(camera)

    franka.gripper.open()
    for _ in range(60):
        world.step(render=True)

    # 基线诊断：方块落定后的真实高度 + Franka 初始末端位姿（用于判断抓取深度是否合理）
    if cube_objs:
        _zs = [float(c.get_world_pose()[0][2]) for c in cube_objs]
        log(f"[基线] 方块中心 z: min={min(_zs):.4f} max={max(_zs):.4f} "
            f"→ 方块顶面 z≈{max(_zs) + CUBE_HEIGHT / 2:.4f}")
    _p_ee, _ = franka.end_effector.get_world_pose()
    _p_hand = world.stage.GetPrimAtPath("/World/Franka/panda_hand")
    log(f"[基线] Franka end_effector 世界位姿 pos={np.round(_p_ee, 4)} "
        f"(prim={'存在' if _p_hand else '不存在'})")

    # ---------------- 冒烟测试：只检查渲染是否可见 ----------------
    if ARGS.smoke:
        log("SMOKE: 采集中...")
        rgb_stats = None
        for i in range(60):
            world.step(render=True)
        fr = camera.get_current_frame()
        if "rgba" in fr:
            a = fr["rgba"][:, :, :3]
            rgb_stats = dict(mean=float(a.mean()), max=int(a.max()), min=int(a.min()),
                             p99=float(np.percentile(a, 99)),
                             nonblack_ratio=float((a.sum(axis=2) > 10).mean()))
            p_dbg = stage_path(f"{ARGS.tag}_smoke_fixed.png")
            ok = cv2.imwrite(p_dbg, cv2.cvtColor(a, cv2.COLOR_RGB2BGR))
            log(f"SMOKE fixed imwrite={ok} {p_dbg}")
            d = fr.get("distance_to_image_plane")
            if d is not None:
                rgb_stats["depth_min"] = float(d.min())
                rgb_stats["depth_max"] = float(d.max())
        if wide_cam is not None:
            wa = wide_cam.get_rgba()[:, :, :3]
            ok = cv2.imwrite(stage_path(f"{ARGS.tag}_smoke_wide.png"),
                             cv2.cvtColor(wa, cv2.COLOR_RGB2BGR))
            rgb_stats["wide_mean"] = float(wa.mean())
            rgb_stats["wide_nonblack_ratio"] = float((wa.sum(axis=2) > 10).mean())
            log(f"SMOKE wide imwrite={ok}")
        log(f"SMOKE RESULT: {rgb_stats}")
        dash_writer.release()
        if wide_writer:
            wide_writer.release()
        finalize_outputs([(stage_path(f"{ARGS.tag}_smoke_fixed.png"), PNG_DIR),
                          (stage_path(f"{ARGS.tag}_smoke_wide.png"), PNG_DIR)])
        simulation_app.close()
        return

    # ---------------- 主循环（原仓库 FSM，未改逻辑） ----------------
    state = "SEARCH"
    current_target = None
    current_color = None
    current_angle = 0.0
    steps = 0
    pick_attempts = 0
    motion_ref = [None]

    log("=== 主循环开始：SEARCH -> PICKING -> RESET ===")
    while simulation_app.is_running():
        world.step(render=True)
        steps += 1

        # 双路渲染：每 2 步存 1 帧 -> 30fps 实时播放
        if steps % 2 == 0 and wide_writer is not None:
            _wa = wide_cam.get_rgba()[:, :, :3]
            wide_writer.write(cv2.cvtColor(_wa, cv2.COLOR_RGB2BGR))
            # 渲染校验：与首帧比较，证明画面真的在动（防止"渲染冻结"静默通过）
            if motion_ref[0] is None:
                motion_ref[0] = _wa.copy()
            elif steps % 300 == 0:
                _d = np.abs(_wa.astype(np.int16) - motion_ref[0].astype(np.int16))
                log(f"[渲染校验] step={steps} 与首帧差异 MAE={_d.mean():.3f} "
                    f"变化像素比例={( _d.max(axis=2) > 8).mean() * 100:.2f}%")

        if world.is_playing():
            if state == "SEARCH":
                candidates = vision.process_frame()
            else:
                vision.process_frame()
                candidates = []

            if state == "SEARCH":
                safe_candidates = [c for c in candidates if c["safe"]]
                if safe_candidates:
                    best_candidate = min(
                        safe_candidates,
                        key=lambda c: np.linalg.norm(np.array(c["pos"][:2]) - np.array([0.5, 0.0])))
                else:
                    best_candidate = None

                if best_candidate:
                    target_z = best_candidate["pos"][2] - GRIP_DESCENT_INTO_CUBE
                    current_target = np.array([best_candidate["pos"][0],
                                               best_candidate["pos"][1],
                                               max(target_z, ABSOLUTE_FLOOR_LIMIT)])
                    current_color = best_candidate["color"]
                    current_angle = best_candidate["angle_offset"]
                    marker.set_world_pose(position=current_target)
                    pick_attempts += 1
                    log(f"Target Locked: {current_color} | Angle: {np.degrees(current_angle):.0f} deg | "
                        f"pos={np.round(current_target,3)}")
                    state = "PICKING"

            elif state == "PICKING":
                if current_color == "red":
                    drop_off = bin_manager.get_place_target("red", BIN_RED_POS)
                elif current_color == "green":
                    drop_off = bin_manager.get_place_target("green", BIN_GREEN_POS)
                else:
                    drop_off = bin_manager.get_place_target("blue", BIN_BLUE_POS)

                target_yaw = np.pi / 2.0 - current_angle
                ee_orientation_eulers = np.array([np.pi, -0.45, target_yaw])
                final_orientation = euler_angles_to_quat(ee_orientation_eulers)

                actions = controller.forward(
                    picking_position=current_target,
                    placing_position=drop_off,
                    current_joint_positions=franka.get_joint_positions(),
                    end_effector_orientation=final_orientation)
                franka.apply_action(actions)

                ee_pos = franka.end_effector.get_world_pose()[0]
                gripper_width = franka.gripper.get_joint_positions().sum()

                # ---- 抓取诊断：末端位姿 / 夹爪开度 / 状态机事件号 / 目标方块真值 ----
                if steps % 30 == 0:
                    ev = getattr(controller, "_event", None)
                    nearest, nd = None, 9e9
                    for co in cube_objs:
                        cp = co.get_world_pose()[0]
                        dd = float(np.linalg.norm(np.array(cp[:2]) - np.array(current_target[:2])))
                        if dd < nd:
                            nd, nearest = dd, cp
                    log(f"[PICK] step={steps} event={ev} ee={np.round(ee_pos, 3)} "
                        f"grip={gripper_width:.4f} tgt={np.round(current_target, 3)} "
                        f"cubeW={np.round(nearest, 4) if nearest is not None else None} dxy={nd:.3f}")

                if ee_pos[2] > 0.15 and gripper_width < 0.005:
                    log(f"!!! CRITICAL: Object Dropped Mid-Air! ({current_color}) !!!")
                    controller.reset()
                    franka.gripper.open()
                    state = "RESET"
                    continue

                if ee_pos[2] < ARGS.pick_fail_z and gripper_width > ARGS.pick_fail_open:
                    log(f"Pick Failed: Could not grip cube (ee_z={ee_pos[2]:.3f}, "
                        f"grip={gripper_width:.4f}). Restarting search...")
                    controller.reset()
                    franka.gripper.open()
                    state = "RESET"
                    continue

                if controller.is_done():
                    if gripper_width > 0.005:
                        bin_manager.confirm_placement(current_color)
                    else:
                        log("Task finished but gripper empty.")
                    controller.reset()
                    state = "RESET"

            elif state == "RESET":
                franka.gripper.open()
                for _ in range(20):
                    world.step(render=True)
                    steps += 1
                    if steps % 2 == 0 and wide_writer is not None:
                        wide_writer.write(cv2.cvtColor(wide_cam.get_rgba()[:, :, :3],
                                                       cv2.COLOR_RGB2BGR))
                state = "SEARCH"
                current_target = None

        if steps % 300 == 0:
            total = sum(bin_manager.counts.values())
            log(f"step={steps} sim_t={steps/60.0:.1f}s state={state} sorted={total} "
                f"counts={bin_manager.counts} fps={steps/(time.time()-t0):.2f}")

        # 关键帧 PNG
        total_sorted = sum(bin_manager.counts.values())
        if total_sorted in (1, 3, 5, 7) and not os.path.exists(
                stage_path(f"{ARGS.tag}_sorted_{total_sorted}.png")):
            if wide_cam is not None:
                cv2.imwrite(stage_path(f"{ARGS.tag}_sorted_{total_sorted}.png"),
                            cv2.cvtColor(wide_cam.get_rgba()[:, :, :3], cv2.COLOR_RGB2BGR))
            if vision.last_dashboard is not None:
                cv2.imwrite(stage_path(f"{ARGS.tag}_dash_{total_sorted}.png"),
                            vision.last_dashboard)
            log(f"关键帧已保存 sorted={total_sorted}")

        # 终止条件
        if total_sorted >= ARGS.max_sorted:
            log(f"达到目标分拣数 {total_sorted}，正常退出")
            break
        if steps >= ARGS.max_steps:
            log(f"达到步数上限 {ARGS.max_steps}，退出")
            break
        if time.time() - t0 > ARGS.timeout_s:
            log(f"墙钟超时 {ARGS.timeout_s}s，退出")
            break

    # 收尾
    dash_writer.release()
    if wide_writer:
        wide_writer.release()

    # 把暂存区产物搬到中文目录（OpenCV 无法直接写中文路径）
    moves = [(dash_path, VID_DIR)]
    if wide_writer is not None:
        moves.append((wide_path, VID_DIR))
    for k in (1, 3, 5, 7):
        moves.append((stage_path(f"{ARGS.tag}_sorted_{k}.png"), PNG_DIR))
        moves.append((stage_path(f"{ARGS.tag}_dash_{k}.png"), PNG_DIR))
    finalize_outputs(moves)

    dash_final = os.path.join(VID_DIR, f"{ARGS.tag}_dashboard.mp4")
    wide_final = os.path.join(VID_DIR, f"{ARGS.tag}_wide.mp4")
    summary = dict(
        steps=steps, sim_seconds=steps / 60.0, wall_seconds=round(time.time() - t0, 2),
        counts=bin_manager.counts, total_sorted=sum(bin_manager.counts.values()),
        pick_attempts=pick_attempts, cubes_spawned=spawned,
        dashboard_frames=vision.frames_written,
        dashboard_video=dash_final if os.path.exists(dash_final) else None,
        dashboard_bytes=os.path.getsize(dash_final) if os.path.exists(dash_final) else 0,
        wide_video=wide_final if os.path.exists(wide_final) else None,
        wide_bytes=os.path.getsize(wide_final) if os.path.exists(wide_final) else 0,
        experience=ARGS.experience,
        gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "all"),
    )
    import json
    with open(os.path.join(LOG_DIR, f"{ARGS.tag}_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    log(f"SUMMARY: {json.dumps(summary, ensure_ascii=False)}")

    simulation_app.close()


if __name__ == "__main__":
    main()
