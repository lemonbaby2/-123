#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核心算法的离线单元测试：python tests/test_course_algorithms.py -v"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from course_algorithms import (  # noqa: E402
    PIDController, clamp, differential_drive_forward, differential_drive_inverse,
    integrate_odometry, relative_error_percent, scan_to_cartesian,
    twist_stamped_payload, validate_twist_stamped, watchdog_expired,
    world_to_cell, yaw_from_quaternion,
)


class TestDifferentialDrive(unittest.TestCase):
    WHEEL_BASE = 0.192       # diffbot.common.xacro 的轮距
    RADIUS = 0.033           # 轮半径 (m)

    def test_straight(self):
        v, omega = differential_drive_forward(1.0, 1.0, self.WHEEL_BASE, self.RADIUS)
        self.assertAlmostEqual(v, self.RADIUS, places=9)
        self.assertAlmostEqual(omega, 0.0, places=9)

    def test_turn_in_place(self):
        v, omega = differential_drive_forward(-1.0, 1.0, self.WHEEL_BASE, self.RADIUS)
        self.assertAlmostEqual(v, 0.0, places=9)
        self.assertAlmostEqual(omega, 2 * self.RADIUS / self.WHEEL_BASE, places=9)

    def test_inverse_roundtrip(self):
        for v, omega in [(0.35, 0.0), (0.2, 0.8), (-0.1, -1.2)]:
            wl, wr = differential_drive_inverse(v, omega, self.WHEEL_BASE, self.RADIUS)
            v2, w2 = differential_drive_forward(wl, wr, self.WHEEL_BASE, self.RADIUS)
            self.assertAlmostEqual(v2, v, places=9)
            self.assertAlmostEqual(w2, omega, places=9)


class TestOdometry(unittest.TestCase):
    def test_straight_one_metre(self):
        # A 段：0.5 m/s 跑 2 s → 1.0000 m，与 odom_eval.py 的阶段 A 对齐
        x, y, th = integrate_odometry(0.0, 0.0, 0.0, 0.5, 0.0, 0.05)
        for _ in range(39):
            x, y, th = integrate_odometry(x, y, th, 0.5, 0.0, 0.05)
        self.assertAlmostEqual(x, 1.0, places=9)
        self.assertAlmostEqual(y, 0.0, places=9)
        self.assertAlmostEqual(th, 0.0, places=9)

    def test_constant_angular_integration(self):
        # 恒定角速度 1 rad/s × 5 s（100 步 × 0.05 s）= 5 rad
        th = 0.0
        for _ in range(100):
            _, _, th = integrate_odometry(0.0, 0.0, th, 0.0, 1.0, 0.05)
        self.assertAlmostEqual(th, 5.0, places=9)

    def test_yaw_from_quaternion(self):
        s = math.sin(math.pi / 4)
        self.assertAlmostEqual(yaw_from_quaternion(0.0, 0.0, s, s), math.pi / 2, places=9)

    def test_measured_A_segment_error(self):
        # 2026-11-13 DGX 实测：A 段 odom 2.4363 m / 真值 2.4361 m
        err = relative_error_percent(2.4363, 2.4361)
        self.assertAlmostEqual(err, 0.00821, places=4)
        self.assertLess(abs(err), 0.01)


class TestPID(unittest.TestCase):
    def test_feedforward_reaches_load_compensated_speed(self):
        # 注入 0.65 负载：闭环必须把输出顶到 target/load ≈ 0.538
        pid = PIDController(kp=1.8, ki=0.35, kd=0.02, max_output=0.8)
        measured = 0.0
        last = 0.0
        for _ in range(300):
            *_rest, out = pid.step(0.35, measured, 0.05)
            # 电机一阶惯性，比代数直连更接近真实底盘
            measured += (out * 0.65 - measured) * 0.3
            last = out
        self.assertGreater(last, 0.35)
        self.assertLess(abs(measured - 0.35), 0.02)

    def test_release_brakes(self):
        pid = PIDController()
        measured = 0.33
        pid.step(0.35, measured, 0.05)
        _, _, _, _, out = pid.step(0.0, measured, 0.05)
        self.assertLess(out, 0.0)          # 松手后主动制动，不是自然滑行

    def test_integral_anti_windup(self):
        pid = PIDController(integral_limit=1.0)
        for _ in range(1000):
            pid.step(1.0, 0.0, 0.2)
        self.assertLessEqual(pid.integral, 1.0)
        self.assertGreaterEqual(pid.integral, -1.0)

    def test_clamp(self):
        self.assertEqual(clamp(2.0, -1.0, 1.0), 1.0)
        self.assertEqual(clamp(-2.0, -1.0, 1.0), -1.0)


class TestContracts(unittest.TestCase):
    def test_twist_stamped_shape(self):
        msg = twist_stamped_payload(0.35, 0.0)
        self.assertTrue(validate_twist_stamped(msg))
        self.assertEqual(msg["twist"]["linear"]["x"], 0.35)

    def test_reject_double_nested_twist(self):
        bad = {"header": {"frame_id": "base_link"},
               "twist": {"twist": {"linear": {"x": 0.35}}}}
        self.assertFalse(validate_twist_stamped(bad))

    def test_watchdog(self):
        self.assertTrue(watchdog_expired(10.0, 9.0, 0.6))
        self.assertFalse(watchdog_expired(10.0, 9.5, 0.6))

    def test_scan_to_cartesian(self):
        pts = scan_to_cartesian([1.0, 2.0, float("inf")], 0.0, math.pi / 2)
        self.assertEqual(len(pts), 2)
        self.assertAlmostEqual(pts[0][0], 1.0, places=9)
        self.assertAlmostEqual(pts[1][1], 2.0, places=9)

    def test_map_index_out_of_range(self):
        self.assertEqual(world_to_cell(3.0, 3.0, 0.0, 0.0, 0.05, 199, 199), (60, 60))
        self.assertEqual(world_to_cell(-1.0, 0.0, 0.0, 0.0, 0.05, 199, 199), (-1, -1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
