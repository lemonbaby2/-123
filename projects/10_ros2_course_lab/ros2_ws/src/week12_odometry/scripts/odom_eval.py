#!/usr/bin/env python3
"""
odom_eval.py —— W12 里程计精度评估（轮式里程计 vs Gazebo 真值）
================================================================
为什么需要这个脚本：
  "我看车跑得挺直" 不是测量。差速车的里程计误差主要来自三处：
    1) 轮半径不准      → 直线距离按比例错（systematic）
    2) 轮距不准        → 转弯角度按比例错（systematic）
    3) 打滑            → 随机、不可预测
  只有把 odom 和真值摆在一起算相对误差，才知道该调哪个参数。

跑法（另开一个终端，底盘 launch 已经在跑）：
    ros2 run week12_odometry odom_eval.py

动作脚本（用仿真时间计时，仿真加速也不会冲过头）：
    阶段 A：直行到 odom 累计 1.0 m      ← 检验 wheel_radius
    阶段 B：原地左转到 yaw = +90°       ← 检验 wheel_separation
    阶段 C：停车并打印误差表

真值来源：
  /world/arena_w12/dynamic_pose/info（gz.msgs.Pose_V → tf2_msgs/TFMessage）
  只含**动态**模型，本世界里唯一动态模型就是 diffbot，
  所以 transforms[0] 恒为车体位姿。
  ⚠️ Pose_V 桥成 TFMessage 后 child_frame_id 和 stamp 全为空/0（W09 已确认），
     因此不能用 frame_id 查找，只能靠"顺序 + 唯一动态模型"这个前提。
     如果以后世界里加了别的动态物体，本脚本的真值就会取错，必须改。
"""
import math

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TwistStamped
from tf2_msgs.msg import TFMessage


def yaw_of(q) -> float:
    """四元数 → 偏航角（只取 z 轴旋转，差速车永远在平面内运动）。"""
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                      1.0 - 2.0 * (q.y * q.y + q.z * q.z))


class OdomEval(Node):

    TARGET_DIST = 1.0      # m
    TARGET_YAW = math.pi / 2
    LIN_VEL = 0.5          # m/s
    ANG_VEL = 1.0          # rad/s

    def __init__(self):
        # use_sim_time=True 是必须的：create_timer(0.02) 用的是**节点时钟**。
        # headless 仿真实时因子可达数百倍，若用墙钟，每 20 ms 墙钟对应
        # 好几秒仿真时间，车会在一次 tick 之间冲过目标点甚至撞墙。
        # 打开后 timer 走仿真时间，控制节拍与仿真严格同步。
        from rclpy.parameter import Parameter
        super().__init__('odom_eval',
                         parameter_overrides=[
                             Parameter('use_sim_time',
                                       Parameter.Type.BOOL, True)])
        self.pub = self.create_publisher(
            TwistStamped, '/diff_drive_controller/cmd_vel', 10)
        self.create_subscription(Odometry, '/diff_drive_controller/odom',
                                 self.on_odom, 20)
        self.create_subscription(TFMessage, '/world/arena_w12/dynamic_pose/info',
                                 self.on_truth, 20)

        self.state = 'WAIT'
        self.odom0 = None       # (x, y, yaw) 起点
        self.truth0 = None
        self.odom_now = None
        self.truth_now = None
        self.ticks = 0

        # 用节点时钟（use_sim_time=true 时即仿真时间）驱动状态机，
        # 这样仿真加速 3000 倍也不会"一秒冲过目标点"。
        self.create_timer(0.02, self.tick)
        self.get_logger().info('等待 odom 与真值 ...')

    # ---------- 回调：只存最新值，不在回调里做控制 ----------
    def on_odom(self, msg: Odometry):
        p = msg.pose.pose.position
        self.odom_now = (p.x, p.y, yaw_of(msg.pose.pose.orientation))

    def on_truth(self, msg: TFMessage):
        if not msg.transforms:
            return
        t = msg.transforms[0].transform
        self.truth_now = (t.translation.x, t.translation.y,
                          yaw_of(t.rotation))

    # ---------- 状态机 ----------
    def tick(self):
        self.ticks += 1
        if self.odom_now is None or self.truth_now is None:
            return

        if self.state == 'WAIT':
            # 等 50 个周期让数据稳定，再记起点
            if self.ticks < 50:
                return
            self.odom0, self.truth0 = self.odom_now, self.truth_now
            self.state = 'DRIVE'
            self.get_logger().info('阶段 A：直行 1.0 m')
            return

        if self.state == 'DRIVE':
            dx = self.odom_now[0] - self.odom0[0]
            dy = self.odom_now[1] - self.odom0[1]
            if math.hypot(dx, dy) < self.TARGET_DIST:
                self.send(self.LIN_VEL, 0.0)
            else:
                self.state = 'TURN'
                self.get_logger().info('阶段 B：原地左转 90°')
            return

        if self.state == 'TURN':
            dyaw = self.odom_now[2] - self.odom0[2]
            if dyaw < self.TARGET_YAW:
                self.send(0.0, self.ANG_VEL)
            else:
                self.send(0.0, 0.0)
                self.state = 'DONE'
                self.report()
            return

    def send(self, lv, av):
        m = TwistStamped()
        m.header.stamp = self.get_clock().now().to_msg()
        m.header.frame_id = 'base_link'
        m.twist.linear.x = float(lv)
        m.twist.angular.z = float(av)
        self.pub.publish(m)

    # ---------- 结果 ----------
    def report(self):
        ox, oy, oyaw = self.odom_now
        tx, ty, tyaw = self.truth_now
        ox0, oy0, oyaw0 = self.odom0
        tx0, ty0, tyaw0 = self.truth0

        od = math.hypot(ox - ox0, oy - oy0)
        td = math.hypot(tx - tx0, ty - ty0)
        oa = math.degrees(oyaw - oyaw0)
        ta = math.degrees(tyaw - tyaw0)

        def rel(a, b):
            return 0.0 if abs(b) < 1e-9 else (a - b) / abs(b) * 100.0

        self.get_logger().info('=' * 62)
        self.get_logger().info('  W12 里程计精度评估')
        self.get_logger().info('=' * 62)
        self.get_logger().info(
            f'  A 直行距离   odom={od:7.4f} m   真值={td:7.4f} m   '
            f'相对误差={rel(od, td):+6.2f} %')
        self.get_logger().info(
            f'  B 转向角度   odom={oa:7.2f} °   真值={ta:7.2f} °   '
            f'相对误差={rel(oa, ta):+6.2f} %')
        self.get_logger().info(
            f'  终点位置误差 {math.hypot(ox - tx, oy - ty) * 100:6.2f} cm')
        self.get_logger().info('=' * 62)
        self.get_logger().info(
            '  读法：A 段偏大 → wheel_radius 调小；B 段偏大 → wheel_separation 调小')
        self.get_logger().info(
            '        （相对误差 = (odom - 真值) / |真值|，正数代表 odom 走多了）')

        rclpy.shutdown()


def main():
    rclpy.init()
    node = OdomEval()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
