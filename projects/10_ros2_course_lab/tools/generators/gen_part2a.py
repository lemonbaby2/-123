# -*- coding: utf-8 -*-
"""生成 W12 的 4 个 ROS 2 Python 节点。"""
import os

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'ros2_ws_w12', 'src', 'week12_odometry', 'scripts')
FILES = {}

FILES['velocity_arbiter.py'] = r'''#!/usr/bin/env python3
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
'''

FILES['odom_relay.py'] = r'''#!/usr/bin/env python3
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
'''

FILES['telemetry_node.py'] = r'''#!/usr/bin/env python3
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
'''

# odom_eval.py：直接复用 W10 实测版，只把世界名与标题换成 W12
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ref', 'w1011',
                   'src', 'week10_control', 'scripts', 'odom_eval.py')
eval_py = open(SRC, encoding='utf-8').read()
eval_py = eval_py.replace('/world/arena/dynamic_pose/info',
                          '/world/arena_w12/dynamic_pose/info')
eval_py = eval_py.replace('W10 里程计精度评估', 'W12 里程计精度评估')
eval_py = eval_py.replace('W10 里程计精度评估（轮式里程计 vs Gazebo 真值）',
                          'W12 里程计精度评估（轮式里程计 vs Gazebo 真值）')
eval_py = eval_py.replace('ros2 run week10_control odom_eval.py',
                          'ros2 run week12_odometry odom_eval.py')
FILES['odom_eval.py'] = eval_py


if __name__ == '__main__':
    os.makedirs(BASE, exist_ok=True)
    for name, text in FILES.items():
        p = os.path.join(BASE, name)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        print('  +', name, len(text.splitlines()), 'lines')
    # 补进 CMakeLists
    cm = os.path.join(os.path.dirname(BASE), 'CMakeLists.txt')
    s = open(cm, encoding='utf-8').read()
    if 'odom_relay.py' not in s:
        s = s.replace('        scripts/velocity_arbiter.py\n',
                      '        scripts/velocity_arbiter.py\n'
                      '        scripts/odom_relay.py\n')
        open(cm, 'w', encoding='utf-8', newline='\n').write(s)
        print('  ~ CMakeLists.txt 增加 odom_relay.py')
    # launch 里补 odom_relay 节点
    lp = os.path.join(os.path.dirname(BASE), 'launch', 'demo_w12.launch.py')
    s = open(lp, encoding='utf-8').read()
    if 'odom_relay' not in s:
        anchor = "        # ---------- 6. 指令仲裁：看门狗 + PID ----------"
        relay = """        # ---------- 5b. 里程计话题归一化 ----------
        TimerAction(period=11.0, actions=[
            Node(
                package='week12_odometry', executable='odom_relay.py',
                name='odom_relay', output='screen',
                parameters=[{'use_sim_time': True}],
            ),
        ]),

"""
        s = s.replace(anchor, relay + anchor)
        open(lp, 'w', encoding='utf-8', newline='\n').write(s)
        print('  ~ launch 增加 odom_relay 节点')
    print('[part2a] done')
