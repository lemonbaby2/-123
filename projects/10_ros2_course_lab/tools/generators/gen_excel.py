#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ROS2 + Ubuntu 全量命令与验证代码手册 xlsx 生成器。
证据等级：A=2026-11-16 DGX 实跑；B=22.04/Humble 课程环境按官方接口编写；C=26.04 无样本待核。
"""
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out',
                   'ROS2与Ubuntu全量命令与验证代码手册_20261116.xlsx')
os.makedirs(os.path.dirname(OUT), exist_ok=True)

HF = PatternFill('solid', fgColor='1F3864')
HFONT = Font(name='微软雅黑', size=10, bold=True, color='FFFFFF')
CODE = Font(name='Consolas', size=9)
CN = Font(name='微软雅黑', size=9)
TH = Side(style='thin', color='BFBFBF')
BD = Border(left=TH, right=TH, top=TH, bottom=TH)
WRAP = Alignment(wrap_text=True, vertical='top')
CEN = Alignment(horizontal='center', vertical='center', wrap_text=True)
EVF = {'A': PatternFill('solid', fgColor='C6EFCE'),
       'B': PatternFill('solid', fgColor='FFEB9C'),
       'C': PatternFill('solid', fgColor='FFC7CE')}

wb = Workbook()
ws = wb.active
ws.title = '00_说明'
ws.column_dimensions['A'].width = 20
ws.column_dimensions['B'].width = 104
for k, v in [
    ('文档名称', 'ROS2 与 Ubuntu 全量命令与验证代码手册'),
    ('生成时间', '2026-11-16'),
    ('适用课程', '机器学习与智能机器人应用技术（智能机器人线）第 12–13 周'),
    ('验证主机', 'DGX spark-a8d2 · NVIDIA GB10 (aarch64) · Ubuntu 24.04 · ROS 2 Jazzy · Gazebo 8.11.0'),
    ('课程环境', 'Ubuntu 22.04 + ROS 2 Humble（20 周教案离线包 / VMware 学生端）'),
    ('证据 A', '2026-11-16 在 DGX 实跑通过，有终端回显/截图'),
    ('证据 B', 'Ubuntu 22.04 + Humble 课程环境按官方接口编写，本学期课堂在用；差异处已在备注标出'),
    ('证据 C', 'Ubuntu 26.04 无本机样本，按 LTS 延续性编写；首次使用先 ros2 --version 核对'),
    ('使用方式', '复制“命令/代码”列整格到终端；备注列写清前置条件与常见报错'),
    ('重要提醒', 'aarch64 与 x86_64 的 apt 包名一致，但第三方 .deb / NVIDIA 驱动不可混用'),
]:
    ws.append([k, v])
for r in range(1, ws.max_row + 1):
    for i in (1, 2):
        c = ws.cell(row=r, column=i)
        c.alignment, c.border = WRAP, BD
        c.font = Font(name='微软雅黑', size=9, bold=(i == 1))
    ws.cell(row=r, column=1).fill = PatternFill('solid', fgColor='DEEAF6')


def sheet(name, header, rows, widths, ev=None):
    w = wb.create_sheet(name)
    w.append(header)
    for i in range(1, len(header) + 1):
        c = w.cell(row=1, column=i)
        c.fill, c.font, c.alignment, c.border = HF, HFONT, CEN, BD
    for row in rows:
        w.append(list(row))
    for r in range(2, w.max_row + 1):
        for i in range(1, len(header) + 1):
            c = w.cell(row=r, column=i)
            c.font = CN if i == 1 else CODE
            c.alignment, c.border = WRAP, BD
        if ev:
            c = w.cell(row=r, column=ev)
            c.alignment = CEN
            if c.value in EVF:
                c.fill = EVF[c.value]
                c.font = Font(name='微软雅黑', size=9, bold=True)
    for i, x in enumerate(widths, 1):
        w.column_dimensions[get_column_letter(i)].width = x
    w.freeze_panes = 'A2'
    w.auto_filter.ref = f'A1:{get_column_letter(len(header))}{w.max_row}'
    w.row_dimensions[1].height = 26
    return w


sheet('01_环境验证矩阵',
      ['检查项', '命令', '22.04/Humble', '24.04/Jazzy(实测)', '26.04', '证据', '备注'],
      [
          ('系统版本', 'lsb_release -a', '22.04 LTS', '24.04 LTS', '待核', 'A', '26.04 无本机样本'),
          ('内核架构', 'uname -a', 'x86_64', 'aarch64 GB10', '待核', 'A', 'GB10 是 ARM64，第三方 x86 deb 不可用'),
          ('ROS 发行版', 'ls /opt/ros/', 'humble', 'jazzy', '待核', 'A', 'Jazzy 用 Python 3.12'),
          ('ROS 版本', 'ros2 --version 2>/dev/null || printenv ROS_DISTRO', '用环境变量', 'jazzy', '待核', 'A', 'Humble 无 ros2 --version'),
          ('Gazebo', 'gz sim --versions', 'Fortress/Garden', '8.11.0', '待核', 'A', 'Humble 时代命令前缀不同'),
          ('ros_gz_bridge', "dpkg -l | grep -E 'ros-(humble|jazzy)-ros-gz'", 'ros-humble-ros-gz', 'ros-jazzy-ros-gz-bridge', '待核', 'A', '桥接 YAML 字段两版一致'),
          ('slam_toolbox', 'dpkg -l | grep slam-toolbox', 'ros-humble-slam-toolbox', 'ros-jazzy-slam-toolbox', '待核', 'A', '两版都是 LifecycleNode'),
          ('Nav2', 'dpkg -l | grep nav2-bringup', 'ros-humble-nav2-bringup', 'ros-jazzy-nav2-bringup', '待核', 'A', 'Jazzy cmd_vel 收 TwistStamped'),
          ('ros2_control', 'dpkg -l | grep ros2-control', 'ros-humble-ros2-control', 'ros-jazzy-ros2-control', '待核', 'A', '插件名 gz_ros2_control-system'),
          ('RViz2', 'rviz2 --version 2>&1 | head -2', '11.x', '14.x', '待核', 'A', '.rviz 跨大版本需重存'),
          ('显示', 'echo $DISPLAY; xdpyinfo | grep dimensions', ':0 虚拟机桌面', ':1 1920x1080', '待核', 'A', '录屏必须真 X，Xvfb 会崩'),
          ('Python', "python3 -c 'import sys;print(sys.version)'", '3.10', '3.12', '待核', 'A', '别混装 pip 与 apt 的 numpy'),
          ('ffmpeg', 'ffmpeg -f x11grab -video_size 1280x720 -i :1.0 -t 3 -y /tmp/t.mp4', '可用', '6.1.1', '待核', 'A', '本机 5 分钟演示片已用此命令'),
      ], [16, 54, 20, 24, 10, 7, 46], ev=6)

sheet('02_工作空间与构建', ['用途', '命令 / 代码', '证据'],
      [
          ('建工作空间', 'mkdir -p ~/ros2_ws/src && cd ~/ros2_ws', 'A'),
          ('建 Python 包', 'ros2 pkg create --build-type ament_python week13_bridge --dependencies rclpy', 'A'),
          ('建 C++ 包', 'ros2 pkg create --build-type ament_cmake diffbot_description --dependencies rclcpp urdf xacro', 'A'),
          ('首次构建', 'colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release', 'A'),
          ('只编一个包', 'colcon build --symlink-install --packages-select week13_bridge', 'A'),
          ('重来', 'rm -rf build install log && colcon build --symlink-install', 'A'),
          ('环境注入', 'source /opt/ros/jazzy/setup.bash && source ~/ros2_ws/install/setup.bash', 'A'),
          ('写 env.sh', "cat > ~/env.sh <<'EOF'\nexport ROS_DOMAIN_ID=42\nexport GZ_PARTITION=w13course\nsource /opt/ros/jazzy/setup.bash\nsource ~/ros2_ws/install/setup.bash\nEOF\n. ~/env.sh", 'A'),
          ('查包可执行', 'ros2 pkg executables week12_odometry', 'A'),
          ('查包路径', 'ros2 pkg prefix week12_odometry', 'A'),
          ('禁 set -u', '# ROS setup.bash 含未定义变量 AMENT_TRACE_SETUP_FILES，脚本一律 set -eo pipefail，不要 set -u', 'A'),
      ], [22, 100, 7], ev=3)

sheet('03_URDF与Xacro', ['用途', '命令 / 代码', '证据', '备注'],
      [
          ('Xacro 展开', "xacro src/diffbot_description/urdf/diffbot_sim.urdf.xacro > /tmp/r.urdf && check_urdf /tmp/r.urdf", 'A', 'check_urdf 来自 liburdfdom-tools'),
          ('XML 自检', "python3 -c \"import xml.etree.ElementTree as E;E.parse('r.urdf.xacro');print('OK')\"", 'A', '只查标签闭合'),
          ('模型可视化', 'ros2 launch urdf_tutorial display.launch.py model:=$HOME/ros2_ws/src/diffbot_description/urdf/diffbot_sim.urdf.xacro', 'B', 'Humble 同命令'),
          ('关节状态', 'ros2 run joint_state_publisher_gui joint_state_publisher_gui', 'A', 'RViz 只出 base_link 多半缺这个'),
          ('机器人状态', "ros2 run robot_state_publisher robot_state_publisher --ros-args -p robot_description:=\"$(xacro /tmp/r.urdf)\"", 'A', '缺它 TF 树断'),
          ('轮子宏', '<xacro:macro name="wheel" params="prefix">\n  <link name="${prefix}_wheel">\n    <visual><geometry><cylinder radius="0.033" length="0.026"/></geometry></visual>\n  </link>\n  <joint name="${prefix}_wheel_joint" type="continuous">\n    <parent link="base_link"/><child link="${prefix}_wheel"/>\n    <origin xyz="0 0.096 -0.02" rpy="1.5708 0 0"/><axis xyz="0 0 1"/>\n  </joint>\n</xacro:macro>', 'A', 'continuous + rpy=pi/2，否则轮不转'),
          ('惯性矩阵', '<inertial>\n  <mass value="0.5"/>\n  <inertia ixx="0.001" ixy="0" ixz="0" iyy="0.001" iyz="0" izz="0.002"/>\n</inertial>', 'A', '缺它在 Gazebo 里抖动/穿透'),
          ('Gazebo 插件', '<gazebo>\n  <plugin filename="gz_ros2_control-system" name="gz_ros2_control::GazeboSimROS2ControlPlugin">\n    <parameters>$(find diffbot_description)/config/diffbot_controllers.yaml</parameters>\n  </plugin>\n</gazebo>', 'A', 'Fortress 时代叫 ignition-gazebo-ros2-control'),
      ], [20, 100, 7, 42], ev=3)

sheet('04_Gazebo世界与模型', ['用途', '命令 / 代码', '证据', '备注'],
      [
          ('无头起世界', 'gz sim -r -s -v2 worlds/arena.sdf', 'A', '-s 只跑物理服务'),
          ('带 GUI 起世界', 'DISPLAY=:1 gz sim -r -v2 worlds/arena.sdf', 'A', 'Xvfb 必崩，用真 X'),
          ('列世界内模型', 'gz model --list', 'A', '需同 GZ_PARTITION'),
          ('规范化 SDF', 'gz sdf -p worlds/arena.sdf > /tmp/arena_norm.sdf', 'A', '排查插件被吞'),
          ('看场景', "gz service -s /world/arena/state --reqtype gz.msgs.Empty --reptype gz.msgs.SerializedScene --timeout 2000 --req ''", 'A', 'Gazebo 8 的查询接口'),
          ('世界骨架', '<?xml version="1.0"?>\n<sdf version="1.9">\n  <world name="arena">\n    <physics name="1ms" type="ignored">\n      <max_step_size>0.001</max_step_size>\n      <real_time_factor>1.0</real_time_factor>\n    </physics>\n    <include><uri>model://sun</uri></include>\n    <include><uri>model://ground_plane</uri></include>\n  </world>\n</sdf>', 'A', '1ms 步长 + RTF 1.0 是课堂基准'),
          ('静态墙模型', '<model name="wall_L">\n  <static>true</static>\n  <link name="link">\n    <collision><geometry><box><size>0.2 4.0 1.0</size></box></geometry></collision>\n    <visual><geometry><box><size>0.2 4.0 1.0</size></box></geometry></visual>\n    <pose>2.0 0 0.5 0 0 0</pose>\n  </link>\n</model>', 'A', '墙必须 static，否则被车撞飞'),
          ('隔离分区', 'export GZ_PARTITION=w13course', 'A', '生产机同跑多个 Gazebo 必配'),
          ('清自己的场', "for p in 'arena[_]w12' 'demo[_]w12'; do pkill -f \"$p\" 2>/dev/null || true; done", 'A', '方括号防 SSH 自匹配断连'),
      ], [20, 100, 7, 42], ev=3)

sheet('05_rosgz桥接', ['用途', '命令 / 代码', '证据', '备注'],
      [
          ('查桥接包', "dpkg -l | grep ros-gz-bridge", 'A', 'Jazzy: ros-jazzy-ros-gz-bridge'),
          ('桥接 YAML 格式', '- topic_name: /scan\n  ros_type_name: sensor_msgs/msg/LaserScan\n  gz_type_name: gz.msgs.LaserScan\n  direction: GZ_TO_ROS\n- topic_name: /cmd_vel\n  ros_type_name: geometry_msgs/msg/TwistStamped\n  gz_type_name: gz.msgs.Twist\n  direction: ROS_TO_GZ', 'A', 'Jazzy cmd_vel 是 TwistStamped，桥另一端是 gz.msgs.Twist'),
          ('启动桥接', 'ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=$HOME/ros2_ws/src/bridge/config/bridge_w13.yaml', 'A', '也可用 ros2 launch ros_gz_bridge bridge.launch.py'),
          ('看桥接映射', 'ros2 node info /parameter_bridge | head -30', 'A', '发布/订阅列表即映射结果'),
          ('查话题类型', 'ros2 interface show sensor_msgs/msg/LaserScan | head -20', 'A', '字段不匹配是桥接失败头号原因'),
          ('查 Gazebo 侧', 'gz topic -l | head -20', 'A', '需同 GZ_PARTITION'),
          ('桥接时钟', '- topic_name: /clock\n  ros_type_name: rosgraph_msgs/msg/Clock\n  gz_type_name: gz.msgs.Clock\n  direction: GZ_TO_ROS', 'A', '/clock 多发布者会让 RViz 报跳时并每 2 秒清空'),
          ('时钟发布者数', 'ros2 topic info /clock | grep -i publisher', 'A', '必须 = 1'),
          ('静态 TF', 'ros2 topic echo /tf_static --once', 'A', 'lidar_link 的 TF 缺了 SLAM 直接不工作'),
          ('TF 树导出', 'ros2 run tf2_tools view_frames', 'B', '生成 frames.pdf'),
          ('TF 查询', 'ros2 run tf2_ros tf2_echo base_link lidar_link', 'A', '验证桥接后的传感器坐标'),
      ], [20, 100, 7, 44], ev=3)

sheet('06_控制里程计PID', ['用途', '命令 / 代码', '证据', '备注'],
      [
          ('启动全链路', 'cd ~/ros2_ws && MODE=pid AUTO_BROWSER=1 bash 01_启动课堂.sh', 'A', 'MODE=pid 开环/闭环切换'),
          ('控制器列表', 'ros2 control list_controllers', 'A', '需先 source env.sh'),
          ('查控制器参数', 'ros2 param list /diff_drive_controller', 'A', 'wheel_separation/wheel_radius 必须和 URDF 一致'),
          ('里程计差异方程', 'v=(vr+vl)/2; w=(vr-vl)/L; x+=v*cos(th)*dt; th+=w*dt', 'A', '课堂板书公式'),
          ('PID 公式', 'u = kp*e + ki* integral(e) + kd*(e-e_prev)/dt', 'A', 'kp=1.8 ki=0.35 kd=0.02（实测参数）'),
          ('发 TwistStamped', 'ros2 topic pub -r 20 /cmd_vel_target geometry_msgs/msg/TwistStamped "{header: {frame_id: base_link}, twist: {linear: {x: 0.35}, angular: {z: 0.0}}}"', 'A', '多套一层 twist.twist 会全零且不报错'),
          ('查里程计频率', 'ros2 topic hz /odom --window 20', 'A', '实测 99.1 Hz'),
          ('里程计误差', 'bash src/week12_odometry/scripts/drive_demo.sh all', 'A', '实测 A 段 0.2 mm，综合 9.3 mm'),
          ('网页看板', 'curl -s http://127.0.0.1:8130/api/data | head -c 400', 'A', '四宫格实时数据'),
          ('20 项自检', 'bash src/week12_odometry/scripts/check_w12.sh', 'A', 'PASS=24 FAIL=0'),
      ], [22, 100, 7, 44], ev=3)

sheet('07_SLAM与导航', ['用途', '命令 / 代码', '证据', '备注'],
      [
          ('官方异步建图', 'ros2 launch slam_toolbox online_async_launch.py slam_params_file:=$HOME/ros2_ws/src/week12_odometry/config/slam_w12.yaml use_sim_time:=true', 'A', '必须 include 官方 launch，Node 直接起会卡 unconfigured'),
          ('生命周期状态', 'ros2 lifecycle get /slam_toolbox', 'A', '必须 active [3]'),
          ('手工激活', 'ros2 lifecycle set /slam_toolbox configure && ros2 lifecycle set /slam_toolbox activate', 'A', '仅调试用'),
          ('查地图发布', 'ros2 topic info /map', 'A', 'Publisher count 必须 >=1'),
          ('查地图尺寸', 'ros2 topic echo /map --once | head -12', 'A', '实测 199x199 @0.05 m'),
          ('保存地图', 'ros2 run nav2_map_server map_saver_cli -f ~/ros2_ws/maps/w13_map', 'A', '产 pgm + yaml'),
          ('查看地图', 'eog ~/ros2_ws/maps/w13_map.pgm', 'B', '或 python3 PIL'),
          ('Nav2 启动', 'ros2 launch nav2_bringup navigation_launch.py use_sim_time:=true map:=$HOME/ros2_ws/maps/w13_map.yaml', 'A', '先有地图再导航'),
          ('给导航目标', 'ros2 topic pub --once /goal_pose geometry_msgs/msg/PoseStamped "{header: {frame_id: map}, pose: {pose: {position: {x: 2.0, y: 0.5}}, orientation: {w: 1.0}}}"', 'A', 'Jazzy 用 PoseStamped'),
          ('成本地图', 'ros2 param get /controller_server max_velocity', 'A', '调参先看速度上限'),
      ], [22, 100, 7, 44], ev=3)

# ROS2 命令总表
ros_cmds = [
    ('节点', 'ros2 node list', '列出所有节点'),
    ('节点', 'ros2 node info /slam_toolbox', '查节点发布/订阅/服务'),
    ('话题', 'ros2 topic list -t', '列话题并显示类型'),
    ('话题', 'ros2 topic echo /odom --once', '收一帧就好'),
    ('话题', 'ros2 topic hz /scan --window 20', '实测频率'),
    ('话题', 'ros2 topic bw /map', '带宽'),
    ('话题', 'ros2 topic info /clock', '查发布者数（必须=1）'),
    ('话题', 'ros2 topic pub -r 20 /cmd_vel_target geometry_msgs/msg/TwistStamped "{header: {frame_id: base_link}, twist: {linear: {x: 0.35}}}"', '发布'),
    ('话题', 'ros2 topic pub --once /goal_pose geometry_msgs/msg/PoseStamped "{header: {frame_id: map}, pose: {pose: {position: {x: 2.0, y: 0.5}}, orientation: {w: 1.0}}}"', '单次发布'),
    ('服务', 'ros2 service list -t', '列服务'),
    ('服务', 'ros2 service call /spawn_entity gazebo_msgs/srv/SpawnEntity "{name: bot}"', 'Gazebo 生成实体'),
    ('动作', 'ros2 action list -t', '列动作'),
    ('动作', 'ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{pose: {header: {frame_id: map}, pose: {position: {x: 2.0, y: 0.0}, orientation: {w: 1.0}}}}"', '导航目标'),
    ('参数', 'ros2 param list /diff_drive_controller', '列参数'),
    ('参数', 'ros2 param get /slam_toolbox scan_topic', '读参数'),
    ('参数', 'ros2 param set /velocity_arbiter kp 1.8', '运行时改参数'),
    ('参数', 'ros2 param dump /slam_toolbox > slam_dump.yaml', '导出参数'),
    ('接口', 'ros2 interface list | grep msgs', '列消息类型'),
    ('接口', 'ros2 interface show geometry_msgs/msg/TwistStamped', '查消息字段（排错必用）'),
    ('运行', 'ros2 run <pkg> <exe> --ros-args -p name:=value', '单节点运行'),
    ('启动', 'ros2 launch <pkg> <file>.launch.py arg:=value', '启动'),
    ('启动', 'ros2 launch <pkg> <file>.launch.py --show-args', '看参数列表'),
    ('包', 'ros2 pkg list | grep week', '列包'),
    ('包', 'ros2 pkg executables <pkg>', '列可执行'),
    ('生命周期', 'ros2 lifecycle list /slam_toolbox', '列状态机'),
    ('生命周期', 'ros2 lifecycle get /slam_toolbox', '查当前状态'),
    ('生命周期', 'ros2 lifecycle set /slam_toolbox activate', '切换状态'),
    ('控制', 'ros2 control list_controllers', '控制器列表'),
    ('控制', 'ros2 control list_hardware_components', '硬件组件'),
    ('录制', 'ros2 bag record -a -o /tmp/demo_bag', '全录'),
    ('录制', 'ros2 bag play /tmp/demo_bag --clock', '回放并发布 /clock'),
    ('录制', 'ros2 bag info /tmp/demo_bag', '查看 bag'),
    ('TF', 'ros2 run tf2_tools view_frames', '导出 TF 树 PDF'),
    ('TF', 'ros2 run tf2_ros tf2_echo base_link lidar_link', '两坐标系变换'),
    ('调试', 'ros2 doctor --report', '体检报告'),
    ('调试', 'ros2 wtf', 'Humble 时代的排错命令'),
    ('守护', 'ros2 daemon status', '查守护进程'),
    ('守护', 'ros2 daemon stop && ros2 daemon start', '重启守护'),
    ('环境', 'printenv ROS_DOMAIN_ID ROS_DISTRO GZ_PARTITION', '查环境与隔离域'),
]
sheet('08_ROS2命令全集', ['分类', '命令', '说明'], ros_cmds, [14, 108, 34])

ub_cmds = [
    ('文件', 'pwd; ls -lah; cd -; mkdir -p a/b; touch f', '基础'),
    ('文件', 'cp -r src dst; mv a b; ln -s target link', '复制/移动/软链'),
    ('文件', 'rm -f file; rm -rf dir', '删除（个人目录慎用）'),
    ('查文件', "find ~ -name '*.launch.py' -print", '按名查'),
    ('查文件', 'find . -type f -mtime -1', '一天内改过'),
    ('查内容', "grep -rn 'pattern' src/ --include='*.py'", '递归搜'),
    ('查内容', 'sed -n "10,30p" file', '看指定行'),
    ('查内容', "awk -F: '{print $1}' /etc/passwd", '列处理'),
    ('查内容', 'head -20 file; tail -f logfile', '头/跟随尾'),
    ('权限', 'chmod +x script.sh; chmod 600 ~/.ssh/id_ed25519', '执行/密钥权限'),
    ('权限', 'chown -R <USER>:<USER> dir', '改属主'),
    ('磁盘', 'df -h; du -sh dir; du -h --max-depth=1 ~', '余量/占用'),
    ('内存', 'free -h; top; htop', '内存/进程'),
    ('进程', 'ps aux | grep ros; pgrep -af "gz sim"', '查进程'),
    ('进程', 'pkill -f pattern; kill -9 PID', '杀进程（方括号防自匹配）'),
    ('网络', 'ip a; ip route; ping -c 3 8.8.8.8', '地址/路由/连通'),
    ('网络', 'ss -ltnp; lsof -i:8130', '端口占用'),
    ('网络', 'curl -I http://127.0.0.1:8130/; wget -c URL', 'HTTP 探测/断点续传'),
    ('网络', 'ssh -i key <USER>@<TAILNET_HOST>', '密钥登录'),
    ('网络', 'ssh-copy-id -i key.pub <USER>@<TAILNET_HOST>', '装公钥'),
    ('网络', 'scp -r local nvidia@host:~/dir; rsync -av src/ host:~/dst/', '传文件'),
    ('压缩', 'tar czf a.tgz dir/; tar xzf a.tgz -C /dest', 'tar'),
    ('压缩', 'zip -r a.zip dir/; unzip -l a.zip', 'zip'),
    ('服务', 'systemctl status ssh; journalctl -u ssh -n 50', '服务状态/日志'),
    ('服务', 'systemctl --user status w13rec', '用户级后台任务'),
    ('账号', 'whoami; id; sudo -n true; passwd; chage -l <USER>', '身份/密码状态'),
    ('账号', 'adduser name; usermod -aG sudo,docker name', '建号/加组'),
    ('软件', 'lsb_release -a; uname -a; nvidia-smi', '系统/显卡'),
    ('软件', 'sudo apt update && sudo apt install -y pkg', '装包'),
    ('软件', "dpkg -l | grep -i pkg", '查 deb'),
    ('文本', "cat > f <<'EOF'\n...\nEOF", '写多行文件'),
    ('后台', 'setsid nohup cmd > log 2>&1 < /dev/null &', '脱离 SSH'),
    ('后台', 'systemd-run --user --unit=job --collect cmd', '会话结束也不断'),
    ('终端', 'tmux new -s w13; tmux attach -t w13', '会话保持'),
    ('终端', 'history | grep ros2; alias ll="ls -lah"', '历史/别名'),
    ('计划', 'crontab -e; crontab -l', '定时任务'),
    ('检查', 'bash -n script.sh; python3 -m py_compile x.py', '语法预检'),
]
sheet('09_Ubuntu命令全集', ['分类', '命令', '说明'], ub_cmds, [12, 106, 30])

sheet('10_故障库', ['现象', '根因', '一条命令定位', '解法', '证据'],
      [
          ('ros2 topic pub 后车不动', 'Jazzy 只收 TwistStamped；CLI YAML 多套一层 twist.twist 后全零且不报错', 'ros2 interface show geometry_msgs/msg/TwistStamped', '写成 twist: {linear: {...}, angular: {...}}', 'A'),
          ('slam_toolbox 不发 /map', '它是 LifecycleNode，用普通 Node 起永远停在 unconfigured', 'ros2 lifecycle get /slam_toolbox; ros2 topic info /map', 'include 官方 online_async_launch.py', 'A'),
          ('RViz 每 2 秒清空 / 跳时间', '/clock 有多个发布者（叠加 rosbag --clock 或双 Gazebo）', 'ros2 topic info /clock | grep -i publisher', '只留一个发布者；用 GZ_PARTITION 隔离', 'A'),
          ('RViz 只显示 base_link', '缺 robot_state_publisher 与 joint_state_publisher', 'ros2 run tf2_tools view_frames', '两个节点都起，再查 frames.pdf', 'A'),
          ('脚本报 unbound variable', 'set -u 撞上 ROS setup.bash 的 AMENT_TRACE_SETUP_FILES', 'bash -n env.sh', '脚本一律 set -eo pipefail，不用 set -u', 'A'),
          ('SSH 一执行就断', 'pkill -f 模式匹配到远端 bash -c 自身命令行', 'pgrep -af "pattern"', '用方括号正则 arena[_]w12', 'A'),
          ('Gazebo GUI 黑屏崩溃', 'Xvfb 上 libgallium/dri2 不支持 GUI 渲染', 'xdpyinfo | grep dimensions', '用真实 DISPLAY=:1 + gdm/Xauthority', 'A'),
          ('远程 SSH 用户名全被拒', '试的 7 个里只有 nvidia 存在；root 被 without-password 拒绝', 'grep -v "#" /etc/passwd | cut -d: -f1; sudo sshd -T | grep passwordauth', '用 <USER>/<PASSWORD>，或装公钥免密', 'A'),
          ('colcon build 找不到包', '没 source setup.bash 或包名拼错', 'ros2 pkg list | grep week', 'source 后重建；--packages-select 指定', 'A'),
          ('看板 4 个画布空白', '网页看板服务没起或数据文件没更新', 'curl -s http://127.0.0.1:8130/api/data', '重启 server.py --port 8130', 'A'),
      ], [34, 50, 48, 48, 7], ev=5)

sheet('11_学习网站', ['类别', '名称', '链接', '用法'],
      [
          ('官方文档', 'ROS 2 Jazzy 文档', 'https://docs.ros.org/en/jazzy/', '查接口/参数的第一站'),
          ('官方文档', 'ROS 2 Humble 文档', 'https://docs.ros.org/en/humble/', '学生端 22.04 对应'),
          ('官方教程', 'ROS 2 Tutorials', 'https://docs.ros.org/en/jazzy/Tutorials.html', '从节点话题到 Launch'),
          ('官方教程', 'rviz2 用户指南', 'https://github.com/ros2/rviz', '配置文件格式'),
          ('官方教程', 'Gazebo Sim 文档', 'https://gazebosim.org/docs', 'SDF / 世界 / 模型'),
          ('官方教程', 'ros_gz 桥接', 'https://github.com/gazebosim/ros_gz', '桥接 YAML 字段'),
          ('官方教程', 'Navigation2 文档', 'https://navigation.ros.org/', '导航与调参'),
          ('官方教程', 'slam_toolbox', 'https://github.com/SteveMacenski/slam_toolbox', 'Lifecycle 状态机'),
          ('官方教程', 'ros2_control 文档', 'https://control.ros.org/', '硬件接口与控制器'),
          ('中文教程', '古月居 ROS2 入门教程', 'https://www.guyuehome.com/', '课程主参考'),
          ('中文教程', '古月居 github ros2_21_tutorials', 'https://github.com/guyuehome/ros2_21_tutorials', '离线包源码'),
          ('中文教程', 'ROS 中文网', 'https://www.ros.org.cn/', '中文社区'),
          ('代码参考', 'ROS2 官方示例', 'https://github.com/ros2/examples', '直接跑'),
          ('工具', 'Gitee 镜像（国内快）', 'https://gitee.com/mirrors', 'GitHub 拉不动时替代'),
      ], [14, 38, 62, 36])

wb.save(OUT)
print('saved:', OUT)
print('sheets:', len(wb.sheetnames), wb.sheetnames)
print('size KB:', round(os.path.getsize(OUT) / 1024, 1))
