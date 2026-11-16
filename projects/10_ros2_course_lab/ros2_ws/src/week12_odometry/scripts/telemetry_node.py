#!/usr/bin/env python3
"""
telemetry_node.py —— ROS 2 → JSON 遥测桥（网页看板的数据源）
============================================================
为什么不直接让网页连 rosbridge：
  rosbridge_suite 要额外装 websocket 依赖，教室网络一断就全黑；
  而且大专课堂上「浏览器读一个本地 JSON」比「WebSocket 握手」好讲一百倍。
本节点把所有要看的数据落成 /tmp/w12_dashboard.json，
dashboard/server.py 用标准库 http.server 提供给浏览器，零第三方依赖。

输出 JSON 字段：
  ts          墙钟秒
  odom        {x,y,yaw,vx,wz}            轮式里程计
  truth       {x,y,yaw}                  Gazebo 仿真真值
  trail       [[x,y],...]                odom 轨迹（最多 1500 点）
  truth_trail [[x,y],...]                真值轨迹
  scan        {ranges[180], range_max}   激光下采样
  map         {w,h,res,ox,oy,cells}      占用栅格，cells 是字符串：# 占 / . 空 / 空格 未知
  pid         {target,measured,err,P,I,D,out}
  hz          {odom,scan,map}             近 1 秒话题帧数
  error_m     odom 与真值的当前平面距离（米）

★ 两个必须处理的坑：
  1) LaserScan 的 ranges 里有 inf / nan，Python json.dumps 会写出 Infinity，
     浏览器 JSON.parse 直接抛错 → 全部替换成有限值。
  2) 写文件要「先写 .tmp 再 os.replace」，否则浏览器可能读到半个 JSON。
"""
import json
import math
import os
import time
from collections import deque

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry, OccupancyGrid
from sensor_msgs.msg import LaserScan
from tf2_msgs.msg import TFMessage
from std_msgs.msg import Float32MultiArray


def yaw_of(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                      1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def finite(v, default):
    try:
        f = float(v)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


class Telemetry(Node):

    MAX_TRAIL = 1500
    SCAN_POINTS = 180
    MAP_MAX = 110

    def __init__(self):
        super().__init__('w12_telemetry')
        self.declare_parameter('data_file', '/tmp/w12_dashboard.json')
        self.data_file = self.get_parameter('data_file').value

        self.create_subscription(Odometry, '/odom', self.on_odom, 20)
        self.create_subscription(Odometry, '/diff_drive_controller/odom',
                                 self.on_odom, 20)
        self.create_subscription(LaserScan, '/scan', self.on_scan, 10)
        self.create_subscription(OccupancyGrid, '/map', self.on_map, 5)
        self.create_subscription(TFMessage,
                                 '/world/arena_w12/dynamic_pose/info',
                                 self.on_truth, 20)
        self.create_subscription(Float32MultiArray, '/w12/pid_debug',
                                 self.on_pid, 20)

        self.odom = {'x': 0.0, 'y': 0.0, 'yaw': 0.0, 'vx': 0.0, 'wz': 0.0}
        self.truth = None
        self.scan = {'ranges': [], 'range_max': 12.0}
        self.map = None
        self.pid = {'target': 0.0, 'measured': 0.0, 'err': 0.0,
                    'P': 0.0, 'I': 0.0, 'D': 0.0, 'out': 0.0}
        self.trail = []
        self.truth_trail = []
        self.cnt = {'odom': 0, 'scan': 0, 'map': 0}
        self.hz = {'odom': 0.0, 'scan': 0.0, 'map': 0.0}
        self.last_stat = time.time()
        self.hist = deque(maxlen=240)
        self.pid_hist = deque(maxlen=240)

        self.create_timer(0.2, self.flush)
        self.get_logger().info(f'遥测输出：{self.data_file}')

    # ------------------------------------------------------------ 回调
    def on_odom(self, msg: Odometry):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        self.odom = {
            'x': finite(p.x, 0.0), 'y': finite(p.y, 0.0),
            'yaw': yaw_of(q),
            'vx': finite(msg.twist.twist.linear.x, 0.0),
            'wz': finite(msg.twist.twist.angular.z, 0.0),
        }
        self.cnt['odom'] += 1
        self._push(self.trail, (self.odom['x'], self.odom['y']))

    def on_truth(self, msg: TFMessage):
        # Pose_V 桥成 TFMessage 后 child_frame_id 为空（W09 实测），
        # 世界里唯一的动态模型就是 diffbot，所以固定取 transforms[0]。
        if not msg.transforms:
            return
        t = msg.transforms[0].transform
        self.truth = {'x': finite(t.translation.x, 0.0),
                      'y': finite(t.translation.y, 0.0),
                      'yaw': yaw_of(t.rotation)}
        self._push(self.truth_trail, (self.truth['x'], self.truth['y']))

    def _push(self, arr, pt):
        if not arr or math.hypot(pt[0] - arr[-1][0], pt[1] - arr[-1][1]) > 0.06:
            arr.append([round(pt[0], 4), round(pt[1], 4)])
            if len(arr) > self.MAX_TRAIL:
                arr.pop(0)

    def on_scan(self, msg: LaserScan):
        rs = list(msg.ranges)
        if not rs:
            return
        step = max(1, len(rs) // self.SCAN_POINTS)
        rmax = finite(msg.range_max, 12.0)
        self.scan = {
            'ranges': [round(finite(rs[i], rmax), 3)
                       for i in range(0, len(rs), step)][:self.SCAN_POINTS],
            'range_max': rmax,
        }
        self.cnt['scan'] += 1

    def on_map(self, msg: OccupancyGrid):
        w, h = int(msg.info.width), int(msg.info.height)
        if w == 0 or h == 0:
            return
        step = max(1, math.ceil(max(w, h) / self.MAP_MAX))
        nw, nh = math.ceil(w / step), math.ceil(h / step)
        data = msg.data
        rows = []
        for j in range(nh):
            row = []
            for i in range(nw):
                v = data[min(j * step, h - 1) * w + min(i * step, w - 1)]
                row.append('#' if v >= 65 else ('.' if v >= 0 else ' '))
            rows.append(''.join(row))
        self.map = {
            'w': nw, 'h': nh,
            'res': finite(msg.info.resolution * step, 0.05),
            'ox': finite(msg.info.origin.position.x, 0.0),
            'oy': finite(msg.info.origin.position.y, 0.0),
            'cells': rows,
        }
        self.cnt['map'] += 1

    def on_pid(self, msg: Float32MultiArray):
        d = list(msg.data)
        if len(d) >= 7:
            self.pid = dict(zip(
                ['target', 'measured', 'err', 'P', 'I', 'D', 'out'],
                [round(finite(x, 0.0), 4) for x in d[:7]]))

    # ------------------------------------------------------------ 落盘
    def flush(self):
        now = time.time()
        if now - self.last_stat >= 1.0:
            dt = now - self.last_stat
            for k in self.cnt:
                self.hz[k] = round(self.cnt[k] / dt, 1)
                self.cnt[k] = 0
            self.last_stat = now

        err_m = None
        if self.truth:
            err_m = round(math.hypot(self.odom['x'] - self.truth['x'],
                                     self.odom['y'] - self.truth['y']), 4)

        self.hist.append([round(now, 2), round(self.odom['vx'], 3),
                          round(self.pid['target'], 3)])
        self.pid_hist.append([round(now, 2),
                              round(self.pid['target'], 3),
                              round(self.pid['measured'], 3),
                              round(self.pid['out'], 3)])

        doc = {
            'ts': round(now, 2),
            'odom': {k: round(v, 4) for k, v in self.odom.items()},
            'truth': self.truth,
            'trail': self.trail,
            'truth_trail': self.truth_trail,
            'scan': self.scan,
            'map': self.map,
            'pid': self.pid,
            'hz': self.hz,
            'error_m': err_m,
            'hist': list(self.hist),
            'pid_hist': list(self.pid_hist),
            'ok': True,
        }
        tmp = self.data_file + '.tmp'
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(doc, f, ensure_ascii=False,
                          separators=(',', ':'), allow_nan=False)
            os.replace(tmp, self.data_file)
        except (OSError, ValueError) as e:
            self.get_logger().warn(f'遥测落盘失败：{e}')


def main():
    rclpy.init()
    node = Telemetry()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
