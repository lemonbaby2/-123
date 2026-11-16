#!/usr/bin/env python3
"""
odom_relay.py —— 把控制器私有里程计话题重发布成标准 /odom
========================================================
diff_drive_controller 默认把里程计发在 ~/odom，也就是
  /diff_drive_controller/odom
而 RViz 的 Odometry 显示、slam_toolbox 的很多示例、AMCL/Nav2 都默认订阅 /odom。
与其在每个下游配置里改话题名，不如在这里统一 relay 一次。

同时把 /tf 关系原样保留（控制器自己广播 odom→base_footprint，本节点不碰 TF），
避免「两个节点同时广播同一条 TF」导致 RViz 报跳变。
"""
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry


class OdomRelay(Node):

    def __init__(self):
        super().__init__('odom_relay')
        self.pub = self.create_publisher(Odometry, '/odom', 20)
        self.sub = self.create_subscription(
            Odometry, '/diff_drive_controller/odom', self.on_odom, 20)
        self.n = 0

    def on_odom(self, msg: Odometry):
        self.pub.publish(msg)
        self.n += 1
        if self.n == 1:
            self.get_logger().info('odom relay 已连通：/diff_drive_controller/odom → /odom')


def main():
    rclpy.init()
    node = OdomRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
