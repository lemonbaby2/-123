#!/usr/bin/env python3
"""
velocity_arbiter.py —— W12 核心节点：指令仲裁 + 看门狗 + 速度 PID 闭环
======================================================================
一个节点回答三个课堂问题：
  Q1 为什么松开键盘小车还在跑？        → 没有看门狗，最后一条 cmd_vel 会一直生效
  Q2 为什么发了 0.5 m/s 车只跑 0.33？ → 负载/摩擦，开环控制无能为力
  Q3 PID 到底在补什么？                → 用 /odom 的实测速度做反馈，补上损失的那部分

数据流：
  网页看板 ──写 /tmp/w12_cmd.json──┐
  命令行   ──/cmd_vel_target──────┼→ [arbiter] ─→ /diff_drive_controller/cmd_vel
  /odom  ──实测线速度（反馈）─────┘        └→ /w12/pid_debug（供看板画曲线）

★ 速度环 PID 必须用「前馈 + 修正」：
     u = v_target + Kp·e + Ki·∫e + Kd·ė   （e = v_target − v_measured）
  如果直接用 u = Kp·e，稳态 e→0 时 u→0，车反而会停下来 —— 这是学生最常写错的一行。

★ Jazzy 的 diff_drive_controller 只收 geometry_msgs/msg/TwistStamped。
  发 Twist 不会报错，消息被静默丢弃，表现为「命令发了，车不动」。

参数：
  mode         passthrough（开环直通） | pid（闭环）
  timeout      看门狗超时秒数，超时立即发零速，默认 0.6 s
  kp/ki/kd     PID 增益
  max_linear   输出限幅
  load_factor  教学用「负载注入」：把发给电机的指令乘以该系数模拟爬坡。
               1.0 = 无负载；0.65 = 车只能跑出指令的 65%，PID 的作用一眼可见。
               ⚠ 这是**人为注入的教学扰动**，真实机器人不要这样写。
"""
import json
import os
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import Float32MultiArray


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class VelocityArbiter(Node):

    def __init__(self):
        super().__init__('velocity_arbiter')
        self.declare_parameter('mode', 'passthrough')
        self.declare_parameter('cmd_file', '/tmp/w12_cmd.json')
        self.declare_parameter('timeout', 0.6)
        self.declare_parameter('kp', 1.8)
        self.declare_parameter('ki', 0.35)
        self.declare_parameter('kd', 0.02)
        self.declare_parameter('max_linear', 0.8)
        self.declare_parameter('load_factor', 1.0)

        self.mode = self.get_parameter('mode').value
        self.cmd_file = self.get_parameter('cmd_file').value
        self.timeout = float(self.get_parameter('timeout').value)
        self.kp = float(self.get_parameter('kp').value)
        self.ki = float(self.get_parameter('ki').value)
        self.kd = float(self.get_parameter('kd').value)
        self.max_v = float(self.get_parameter('max_linear').value)
        self.load = float(self.get_parameter('load_factor').value)

        self.pub = self.create_publisher(
            TwistStamped, '/diff_drive_controller/cmd_vel', 10)
        self.debug_pub = self.create_publisher(
            Float32MultiArray, '/w12/pid_debug', 10)

        # 两个指令源：ROS 话题（命令行 / drive_demo.sh）与网页 JSON 文件
        self.create_subscription(TwistStamped, '/cmd_vel_target',
                                 self.on_topic_target, 10)
        # 反馈：优先用 relay 出来的 /odom，兼容控制器私有话题
        self.create_subscription(Odometry, '/odom', self.on_odom, 20)
        self.create_subscription(Odometry, '/diff_drive_controller/odom',
                                 self.on_odom, 20)

        self.target_v = 0.0        # 目标线速度 m/s
        self.target_w = 0.0        # 目标角速度 rad/s
        self.target_ts = 0.0       # 墙钟时间戳，供看门狗判断
        self.measured_v = 0.0
        self.integral = 0.0
        self.prev_err = 0.0
        self.last_t = None
        self.last_file_mtime = 0.0
        self.debug = [0.0] * 7     # target, measured, err, P, I, D, out

        self.create_timer(0.05, self.tick)     # 20 Hz
        self.get_logger().info(
            f'arbiter 启动：mode={self.mode} timeout={self.timeout}s '
            f'kp={self.kp} ki={self.ki} kd={self.kd} load={self.load}')

    # ------------------------------------------------------------ 输入
    def on_topic_target(self, msg: TwistStamped):
        self.target_v = float(msg.twist.linear.x)
        self.target_w = float(msg.twist.angular.z)
        self.target_ts = time.time()

    def read_cmd_file(self):
        """网页看板把指令写成 JSON；用 mtime 变化避免每次 tick 都解析文件。"""
        try:
            m = os.path.getmtime(self.cmd_file)
            if m <= self.last_file_mtime:
                return
            self.last_file_mtime = m
            with open(self.cmd_file, 'r', encoding='utf-8') as f:
                d = json.load(f)
            # 只有「比话题指令更新」才覆盖，避免网页与命令行互相打架
            if float(d.get('ts', 0)) >= self.target_ts:
                self.target_v = clamp(float(d.get('linear', 0.0)), -1.0, 1.0)
                self.target_w = clamp(float(d.get('angular', 0.0)), -2.5, 2.5)
                self.target_ts = float(d.get('ts', time.time()))
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    def on_odom(self, msg: Odometry):
        self.measured_v = float(msg.twist.twist.linear.x)

    # ------------------------------------------------------------ 控制
    def pid(self, target, measured, now):
        err = target - measured
        dt = 0.05 if self.last_t is None else clamp(now - self.last_t, 0.01, 0.2)
        self.last_t = now

        # 抗积分饱和：积分项限在 ±1.0，否则停车时仍会「积分 windup」冲出去
        self.integral = clamp(self.integral + err * dt, -1.0, 1.0)
        deriv = (err - self.prev_err) / dt
        self.prev_err = err

        P = self.kp * err
        I = self.ki * self.integral
        D = self.kd * deriv
        # ★ 前馈 + 修正，缺了 target 这一项稳态会掉回 0
        out = clamp(target + P + I + D, -self.max_v, self.max_v)
        return err, P, I, D, out

    def tick(self):
        now = time.time()
        self.read_cmd_file()

        # ---- 看门狗：超过 timeout 没收到任何指令就归零 ----
        if now - self.target_ts > self.timeout:
            self.target_v = 0.0
            self.target_w = 0.0
            # 停车时清积分，否则再次起步会先冲一下
            self.integral = 0.0

        if self.mode == 'pid':
            err, P, I, D, out_v = self.pid(self.target_v, self.measured_v, now)
        else:
            err = self.target_v - self.measured_v
            P = I = D = 0.0
            out_v = clamp(self.target_v, -self.max_v, self.max_v)

        # 教学负载注入：模拟爬坡 / 轮胎打滑造成的速度损失
        cmd_v = out_v * self.load

        m = TwistStamped()
        m.header.stamp = self.get_clock().now().to_msg()
        m.header.frame_id = 'base_link'
        m.twist.linear.x = float(cmd_v)
        m.twist.angular.z = float(self.target_w)
        self.pub.publish(m)

        self.debug = [self.target_v, self.measured_v, err, P, I, D, out_v]
        dbg = Float32MultiArray()
        dbg.data = [float(x) for x in self.debug]
        self.debug_pub.publish(dbg)


def main():
    rclpy.init()
    node = VelocityArbiter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
