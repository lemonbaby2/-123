#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""课程实验的核心算法（纯 Python，无 ROS 依赖）。

这些函数从 `ros2_ws/src/week12_odometry/scripts/` 的真实节点中抽取，
用于在没有 ROS 的机器上验证接口和数值性质；实机链路仍以 ROS 2 节点为准。

来源对应关系：
  differential_drive_*  ← diffbot_description/urdf/diffbot.common.xacro 的轮距/轮半径
  PIDController         ← scripts/velocity_arbiter.py::VelocityArbiter.pid
  yaw_from_quaternion   ← scripts/odom_eval.py::yaw_of
  relative_error_percent← scripts/odom_eval.py::report.rel
  twist_stamped_payload ← scripts/drive_demo.sh 的 Jazzy 消息格式
  watchdog_expired      ← scripts/velocity_arbiter.py::tick 的看门狗
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# ---------------------------------------------------------------- 差速运动学
def differential_drive_forward(v_left: float, v_right: float,
                               wheel_separation: float,
                               wheel_radius: float = 1.0) -> Tuple[float, float]:
    """左右轮线速度 → 车体 (v, omega)。wheel_radius 只用于把轮速换算成 m/s。"""
    vl, vr = v_left * wheel_radius, v_right * wheel_radius
    return (vl + vr) / 2.0, (vr - vl) / wheel_separation


def differential_drive_inverse(v: float, omega: float,
                               wheel_separation: float,
                               wheel_radius: float = 1.0) -> Tuple[float, float]:
    """车体 (v, omega) → 左右轮角速度，是正向变换的解析逆。"""
    vl = v - omega * wheel_separation / 2.0
    vr = v + omega * wheel_separation / 2.0
    return vl / wheel_radius, vr / wheel_radius


def integrate_odometry(x: float, y: float, theta: float,
                       v: float, omega: float, dt: float) -> Tuple[float, float, float]:
    """恒定 (v, omega) 在一个控制周期内的精确积分，避免圆弧走成折线。"""
    if abs(omega) < 1e-9:
        return x + v * dt * math.cos(theta), y + v * dt * math.sin(theta), theta
    r = v / omega
    dtheta = omega * dt
    return (x + r * (math.sin(theta + dtheta) - math.sin(theta)),
            y + r * (math.cos(theta) - math.cos(theta + dtheta)),
            theta + dtheta)


# ---------------------------------------------------------------- 姿态与误差
def yaw_from_quaternion(x: float, y: float, z: float, w: float) -> float:
    """只取平面运动的偏航角，与 odom_eval.py::yaw_of 完全一致。"""
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def relative_error_percent(measured: float, truth: float) -> float:
    if abs(truth) < 1e-9:
        return 0.0
    return (measured - truth) / abs(truth) * 100.0


# ---------------------------------------------------------------- 速度 PID
@dataclass
class PIDController:
    """前馈 + 修正的速度环，带积分限幅和微分项。

    ★ 常见错误：写成 u = Kp*e + Ki*∫e + Kd*ė。稳态 e→0 时输出趋零，车会停下。
      正确形式是 u = target + P + I + D（与 velocity_arbiter.py 一致）。
    """

    kp: float = 1.8
    ki: float = 0.35
    kd: float = 0.02
    max_output: float = 0.8
    integral_limit: float = 1.0
    integral: float = 0.0
    prev_error: float = 0.0
    has_prev: bool = False

    def step(self, target: float, measured: float, dt: float) -> Tuple[float, float, float, float, float]:
        dt = clamp(dt, 0.01, 0.2)
        err = target - measured
        self.integral = clamp(self.integral + err * dt,
                              -self.integral_limit, self.integral_limit)
        deriv = 0.0 if not self.has_prev else (err - self.prev_error) / dt
        self.prev_error, self.has_prev = err, True
        p = self.kp * err
        i = self.ki * self.integral
        d = self.kd * deriv
        out = clamp(target + p + i + d, -self.max_output, self.max_output)
        return err, p, i, d, out

    def reset_integral(self) -> None:
        """停车时清积分，否则再次起步会先冲一下。"""
        self.integral = 0.0


def watchdog_expired(now: float, last_command_ts: float, timeout: float = 0.6) -> bool:
    return now - last_command_ts > timeout


# ---------------------------------------------------------------- ROS 消息契约
def twist_stamped_payload(linear: float, angular: float,
                          frame_id: str = "base_link") -> dict:
    """geometry_msgs/TwistStamped 的 CLI YAML 结构。

    Jazzy 的 diff_drive_controller 只收 TwistStamped；多套一层
    `twist: {twist: {...}}` 不会报错，但所有字段是零 —— 表现为「发了车不动」。
    """
    return {
        "header": {"frame_id": frame_id},
        "twist": {
            "linear": {"x": linear, "y": 0.0, "z": 0.0},
            "angular": {"x": 0.0, "y": 0.0, "z": angular},
        },
    }


def validate_twist_stamped(msg: dict) -> bool:
    """检查是否是可被 Jazzy 正确解析的 TwistStamped 结构。"""
    try:
        t = msg["twist"]
        if "twist" in t:                      # 经典错误：多嵌套一层
            return False
        float(t["linear"]["x"])
        float(t["angular"]["z"])
        msg["header"]["frame_id"]
        return True
    except (KeyError, TypeError, ValueError):
        return False


# ---------------------------------------------------------------- 传感与地图
def scan_to_cartesian(ranges: Sequence[float], angle_min: float,
                      angle_increment: float, range_max: float = 100.0
                      ) -> List[Tuple[float, float]]:
    """激光极坐标 → 车体坐标下的 (x, y)，忽略超出量程和非有限值。"""
    pts = []
    for i, r in enumerate(ranges):
        if not math.isfinite(r) or r <= 0.0 or r > range_max:
            continue
        a = angle_min + i * angle_increment
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def world_to_cell(x: float, y: float, origin_x: float, origin_y: float,
                  resolution: float, width: int, height: int) -> Tuple[int, int]:
    """世界坐标 → 占用栅格索引；越界返回 (-1, -1)，调用方必须检查。"""
    if resolution <= 0:
        raise ValueError("resolution must be positive")
    cx = int(math.floor((x - origin_x) / resolution))
    cy = int(math.floor((y - origin_y) / resolution))
    if 0 <= cx < width and 0 <= cy < height:
        return cx, cy
    return -1, -1


__all__ = [
    "clamp", "differential_drive_forward", "differential_drive_inverse",
    "integrate_odometry", "yaw_from_quaternion", "relative_error_percent",
    "PIDController", "watchdog_expired", "twist_stamped_payload",
    "validate_twist_stamped", "scan_to_cartesian", "world_to_cell",
]
