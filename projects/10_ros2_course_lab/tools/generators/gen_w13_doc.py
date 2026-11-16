# -*- coding: utf-8 -*-
"""明日课件讲义：Gazebo 世界、模型与 ROS2 桥接。
排版复用 _hw2026/docx_kit + _assign3/assign_kit，数据来自 2026-11-16 DGX 实测。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, '_hw2026'))
sys.path.insert(0, os.path.join(ROOT, '_assign3'))

import assign_kit as ak
from docx_kit import (heading, code_block, figure, add_toc, setup_toc_styles,
                      enable_update_fields, add_footer_page_number, count_chars)

OUT = os.path.join(HERE, 'out', 'Gazebo世界模型与ROS2桥接_课件讲义_20261116.docx')
GAZEBO_PNG = os.path.join(ROOT, '_w12', 'shots', 'w12_gazebo.png')
DASH_PNG = os.path.join(ROOT, '_w12', 'shots', 'w12_dashboard.png')

B = []
def h1(t): B.append(('h1', t))
def h2(t): B.append(('h2', t))
def p(t): B.append(('p', t))
def b(t): B.append(('b', t))
def code(t): B.append(('code', t))
def tb(cap, head, rows, widths, fs=9.5): B.append(('table', cap, head, rows, widths, fs))
def qa(t, lines): B.append(('qa', t, lines))
def note(lines, title, kind='info'): B.append(('note', lines, title, kind))
def fig(path, cap): B.append(('fig', path, cap))

# ============================================================ 开场
h1('课前：把三样东西摆在同一张图上')
p('今天我们讲三件事：Gazebo 的世界、Gazebo 的模型、以及把两者接到 ROS 2 的桥。很多同学学这一块觉得乱，根本原因是把三层东西混在一起记了。请先记住一句话：世界是舞台，模型是演员，桥是翻译。舞台决定物理规则和场地长什么样；演员决定机器人有几条腿、轮子多大、惯量多少；翻译把演员和舞台上的消息翻译成 ROS 2 节点听得懂的语言。三层各管各的，任何一层出问题，现象都表现为「车不动」，所以必须分层查。')
p('这份讲义里的每一条命令、每一个参数，都在 2026 年 11 月 16 日的 DGX 上实跑过。机器是 spark-a8d2，Ubuntu 24.04、ROS 2 Jazzy、Gazebo 8.11，CPU 架构是 ARM64 的 GB10。学生端如果是 Ubuntu 22.04 加 Humble，绝大多数命令一致，差异处我在正文里单独标出来了。Ubuntu 26.04 目前没有实测样本，我不会把没跑过的东西写成「已验证」。')
tb('表 0-1  三层职责与对应文件', ['层', '回答什么问题', '文件 / 包', '出问题时的典型现象'], [
    ['世界 World', '车在什么场地里、物理步长多少、有哪些墙', 'arena_w12.sdf', '场景一片黑、车穿墙、时间跑飞'],
    ['模型 Model', '车长什么样、轮子多大、惯量多少、谁驱动', 'diffbot_sim.urdf.xacro', 'RViz 只出 base_link、车原地抖'],
    ['桥 Bridge', 'Gazebo 的消息怎么变成 ROS 话题', 'bridge_w12.yaml + ros_gz_bridge', '/scan 无数据、车不响应 /cmd_vel'],
], [2.2, 4.8, 4.2, 4.4])

h2('0.1 上课前必须先跑的三条命令')
code('export ROS_DOMAIN_ID=42 GZ_PARTITION=w12course\ncd ~/ros2_ws_w12 && bash src/week12_odometry/scripts/check_w12.sh\n# 期望：PASS=24  FAIL=0  SKIP=0')
p('ROS_DOMAIN_ID 用来在 DDS 层隔离，GZ_PARTITION 用来在 Gazebo 发现层隔离。这台 DGX 上同时还跑着别的班组的传感器演示和小组作业，不隔离就会出现两个 Gazebo 互相发现、/clock 多个发布者、RViz 每两秒报一次时间跳变并清空画面。这两行不是可选的性能优化，是课堂不翻车的前提。')

# ============================================================ 第一讲
h1('第一讲　世界：一个 SDF 文件就是一间教室')
h2('1.1 世界文件的最小骨架')
p('SDF 是 Gazebo 的原生描述格式，可以理解为「仿真世界的 HTML」。一个最小可用世界必须有物理引擎配置、太阳光、地面，然后才是你自己的模型和插件。下面这段是课堂用的骨架，逐行都能讲出东西：')
code('<?xml version="1.0"?>\n<sdf version="1.9">\n  <world name="arena">\n    <physics name="1ms" type="ignored">\n      <max_step_size>0.001</max_step_size>\n      <real_time_factor>1.0</real_time_factor>\n    </physics>\n    <include><uri>model://sun</uri></include>\n    <include><uri>model://ground_plane</uri></include>\n    <include><uri>model://diffbot</uri></include>\n  </world>\n</sdf>')
p('max_step_size 是物理步长，0.001 秒表示每秒解算一千次。real_time_factor 是真实时间倍率，1.0 表示仿真时间和墙钟时间同步。这两个值要连起来看：步长决定精度，倍率决定速度。步长太小而机器算不过来，仿真会自动变慢；倍率设成 5，车看起来像飞，里程计和 PID 全部失真。课堂上我们固定 1.0，不给学生调。')
p('type="ignored" 是 SDF 1.9 的写法，表示让 Gazebo 自己挑合适的物理引擎。老教程里写 type="ode"，在 Gazebo 8 里还能跑，但不推荐——引擎换了以后接触求解的行为会变，同样的墙可能从「挡住」变成「弹开」。')
h2('1.2 加一道墙：static 是关键字')
p('我们的场地中间有一道 L 形内墙，用来让激光雷达看见转角、让 SLAM 建图有东西可画。墙的写法非常短，但有一个字段绝对不能漏：')
code('<model name="wall_L">\n  <static>true</static>\n  <link name="link">\n    <collision><geometry><box><size>0.2 4.0 1.0</size></box></geometry></collision>\n    <visual><geometry><box><size>0.2 4.0 1.0</size></box></geometry></visual>\n    <pose>2.0 0 0.5 0 0 0</pose>\n  </link>\n</model>')
p('static 为 true，物理引擎把这道墙当成无限质量，永远不动。漏写它，车一撞墙，墙就飞了——我见过学生调了半小时里程计，最后发现是墙被撞跑，真值和 odom 当然对不上。collision 决定碰撞形状，visual 决定看得见的形状，两者可以不一样：教学里我们让它们一致，工程里经常让 collision 用简化包围盒，visual 用精细网格，这样既跑得快又看得真。')
h2('1.3 现场解剖：把 SDF 规范化再看一遍')
p('Gazebo 会读取世界文件，把 xacro 展开、把宏替换掉、把默认字段补全。我们直接看它最终拿到的东西：')
code('gz sdf -p worlds/arena_w12.sdf > /tmp/arena_norm.sdf\ngrep -n "plugin\\|static\\|max_step_size" /tmp/arena_norm.sdf | head -20\ngz model --list')
p('这一步的诊断价值极高。如果自己写的插件在原始文件里明明有、规范化之后没了，说明标签放错了层级——这是初学者最常见的失败：把 <plugin> 写在 <model> 外面，或者写在 <sdf> 根下，Gazebo 不报错，直接忽略。')

qa('互问互答 ①　世界和模型能不能写在一个文件里？', [
    '【教师设问】我把机器人模型的 URDF 直接粘进世界 SDF，能不能省掉一个文件？',
    '【学生甲】能吧，反正最后都是 XML，Gazebo 都能读。',
    '【学生乙】读是能读，但维护会乱。模型要反复给 RViz、给 URDF 可视化、给控制器配置用；世界只服务仿真。粘一起以后，改轮半径得在两个地方翻。',
    '【学生丙】而且 ros2_control 的插件参数要引用模型文件里的 xacro 属性，粘进 SDF 以后 $(find ...) 还能解析吗？',
    '【学生乙】这就说不准了，至少不能保证。我倾向按职责拆开：模型一个文件，世界一个文件，桥一个配置。',
    '【教师点评】对。工程上「能跑」和「能维护」是两件事。我们这门课评分里有一项叫系统集成，考的就是你能不能把三层拆清楚再接起来。拆开还有一个好处：同一台车可以放进三个不同世界，同一世界也可以换三台车，不用改一行代码。',
])

fig(GAZEBO_PNG, '图 1-1　课堂 Gazebo 场景实测截图：10×10 m 场地、L 形内墙与差速底盘')
note(['图里的内墙、色块和细柱都是世界文件里的静态模型；机器人本体来自模型文件。两层在 Gazebo 里合成一个场景，但在 ROS 侧看到的只有话题和 TF。',
      '录制条件：DISPLAY=:1 真实 X 桌面，XAUTHORITY=/run/user/1000/gdm/Xauthority。Xvfb 下 Gazebo GUI 会因 libgallium/dri2 崩溃，不要在无头环境里复现这一步。'],
     '看图要点', 'info')

# ============================================================ 第二讲
h1('第二讲　模型：从 URDF/Xacro 到能跑的机器人')
h2('2.1 一个 link 必须具备什么')
p('URDF 用 link 表示刚体、joint 表示连接。Gazebo 对 link 的要求比 RViz 严格得多：RViz 只看 visual，Gazebo 还要看 collision 和 inertial。缺 visual，仿真照样跑，只是看不见；缺 collision，车直接穿过墙；缺 inertial，车会抖动、翻滚、甚至被自己的控制力弹飞。')
code('<link name="base_link">\n  <visual><geometry><box><size>0.3 0.25 0.1</size></box></geometry></visual>\n  <collision><geometry><box><size>0.3 0.25 0.1</size></box></geometry></collision>\n  <inertial>\n    <mass value="3.0"/>\n    <inertia ixx="0.02" ixy="0" ixz="0" iyy="0.03" iyz="0" izz="0.04"/>\n  </inertial>\n</link>')
p('惯性矩阵不要求你手推，但要知道三个对角项代表绕 x/y/z 轴的转动惯量，单位是千克·平方米。数值取得太小，同样力矩下角加速度巨大，车会「神经质」地抖；取得太大，转向迟钝，PID 怎么调都慢半拍。课堂用值来自实测调参，学生做报告时可以照抄，但要写明来源是课堂标定值。')
h2('2.2 轮子的两个必错点')
p('第一个必错点是关节类型。轮子必须写 type="continuous"，不能写 "revolute"。revolute 有上下限，轮子转过一圈就被关节限位卡住；continuous 没有限位，才能一直转。第二个必错点是轮子朝向。URDF 里圆柱体默认沿 z 轴，装到车体侧面必须绕 x 轴转 90 度，也就是 rpy 里的第一个角写成 π/2。漏了这个旋转，轮子会像圆盘一样立在地上横着蹭。')
code('<xacro:macro name="wheel" params="prefix reflect">\n  <joint name="${prefix}_wheel_joint" type="continuous">\n    <parent link="base_link"/>\n    <child link="${prefix}_wheel"/>\n    <origin xyz="0 ${reflect*0.096} -0.02" rpy="1.5708 0 0"/>\n    <axis xyz="0 0 1"/>\n  </joint>\n  <link name="${prefix}_wheel">\n    <visual><geometry><cylinder radius="0.05" length="0.026"/></geometry></visual>\n    <collision><geometry><cylinder radius="0.05" length="0.026"/></geometry></collision>\n    <inertial>\n      <mass value="0.5"/>\n      <inertia ixx="0.001" ixy="0" ixz="0" iyy="0.001" iyz="0" izz="0.002"/>\n    </inertial>\n  </link>\n</xacro:macro>')
p('注意 axis 写的是 0 0 1，配合 rpy 的 π/2，旋转轴才落在车体横轴上。很多同学只改了 rpy 不改 axis，或者两个都改，结果车往前发指令轮子却往地里钻。判断方法很简单：在 Gazebo 里盯着轮子看两秒，转的方向对不对一眼就能看出来。')
h2('2.3 把控制器挂进模型')
p('模型里还有一段 Gazebo 专用标签，用来告诉仿真「谁来驱动这两个关节」：')
code('<gazebo>\n  <plugin filename="gz_ros2_control-system"\n          name="gz_ros2_control::GazeboSimROS2ControlPlugin">\n    <parameters>$(find diffbot_description)/config/diffbot_controllers.yaml</parameters>\n  </plugin>\n</gazebo>')
p('Jazzy 加 Gazebo 8 用 gz_ros2_control-system；如果是 Humble 配 Fortress，插件名是 ignition-gazebo-ros2-control。这就是为什么同一份 URDF 拿到学生端可能不生效——不是代码写错，是插件名跟着发行版变了。')
p('另外，URDF 里的 wheel_radius 与 wheel_separation 必须和 diffbot_controllers.yaml 完全一致。我们这次实测的配置是轮半径 0.05 米、轮距 0.36 米。两处不一致的现象非常隐蔽：车能动、话题有数、里程计也有数，只是数字按比例偏。上次 we 量出 A 段 0.2 毫米误差，前提就是这两处严丝合缝。')
qa('互问互答 ②　RViz 里只有一个 base_link，模型去哪了？', [
    '【教师设问】我把 URDF 加载进 RViz，屏幕上只有坐标系和一个方块，激光点云和数据都在，但机器人模型没了。是不是 URDF 写错了？',
    '【学生甲】肯定是 visual 标签写错，或者模型文件路径不对。',
    '【学生乙】路径对不对看 robot_description 参数有没有内容就知道了。我怀疑是 TF 断了——激光点云能显示是因为它有自己单独的 frame。',
    '【学生丙】我遇到过一次，是忘了起 robot_state_publisher。URDF 只是描述文件，没人发布它，RViz 就没法把 link 按 TF 关系摆出来。',
    '【学生乙】对，而且只起 robot_state_publisher 还不够，joint 是活动关节时还要 joint_state_publisher，否则轮子姿态算不出来。',
    '【教师点评】这就是典型的分层定位。先查参数有没有内容，再查 TF 树，最后才查模型文件。顺序反了就会漫无目的地改 XML。记住这条判据：RViz 只出 base_link，九成是 robot_state_publisher 和 joint_state_publisher 没起来。',
])

# ============================================================ 第三讲
h1('第三讲　桥接：Gazebo 与 ROS 2 之间的翻译官')
h2('3.1 一句话说清 ros_gz_bridge')
p('Gazebo 有自己的消息类型，叫 gz.msgs；ROS 2 有自己的消息类型，叫 sensor_msgs、geometry_msgs 等等。两者名字不一样、字段结构也不一样，互相听不懂。ros_gz_bridge 的作用就是在中间做字段映射和转发。它不关心物理，也不关心控制算法，只做翻译。')
p('桥接配置是一个 YAML 列表，每条映射四个字段缺一不可：')
code('- topic_name: /scan\n  ros_type_name: sensor_msgs/msg/LaserScan\n  gz_type_name: gz.msgs.LaserScan\n  direction: GZ_TO_ROS\n\n- topic_name: /cmd_vel\n  ros_type_name: geometry_msgs/msg/TwistStamped\n  gz_type_name: gz.msgs.Twist\n  direction: ROS_TO_GZ')
p('topic_name 是 ROS 侧的话题名；两个 type_name 必须写成完整的包路径形式；direction 只有 GZ_TO_ROS 和 ROS_TO_GZ 两种。写反了，现象是「话题列表里有这个名字，但永远收不到数据」——因为桥接在往反方向转发。')
h2('3.2 三个必讲的坑')
p('第一个坑是消息类型。Jazzy 的 /cmd_vel 收 TwistStamped，比老的 Twist 多一层 header。桥接的 ROS 侧类型必须写 geometry_msgs/msg/TwistStamped，Gazebo 侧仍写 gz.msgs.Twist。更要命的是命令行发布：如果你写成 twist: {twist: {linear: ...}}，ros2 CLI 不报错，消息也发得出去，但里面的线速度全是零。正确写法只有一层：')
code('ros2 topic pub -r 20 /cmd_vel_target geometry_msgs/msg/TwistStamped \\\n  "{header: {frame_id: base_link}, twist: {linear: {x: 0.35, y: 0, z: 0}, angular: {x: 0, y: 0, z: 0}}}"\n# 排错第一命令：ros2 interface show geometry_msgs/msg/TwistStamped')
p('第二个坑是时钟。Gazebo 会发布 /clock，rosbag 回放加 --clock 也会发布 /clock。两个发布者同时存在时，RViz 每隔两秒报一次 Detected jump back in time，然后清空画面。判据只有一条：ros2 topic info /clock，Publisher count 必须等于 1。')
p('第三个坑是静态 TF。激光雷达装在车顶，它的坐标系 lidar_link 相对 base_footprint 的变换由 robot_state_publisher 通过 /tf_static 发布。这条静态变换丢了，SLAM 收得到 /scan 却永远不建图，日志里全是 MessageFilter 丢弃 scans 的告警。查法：ros2 topic echo /tf_static --once，看有没有 lidar_link。')
tb('表 3-1　桥接故障四步定位', ['步骤', '查什么', '命令', '正常判据'], [
    ['1', 'Gazebo 侧有没有话题', 'gz topic -l | grep -E "cmd_vel|scan"', '能看到 /cmd_vel、/scan'],
    ['2', '桥接进程在不在', 'ros2 node info /parameter_bridge', '列出对应发布/订阅'],
    ['3', 'ROS 侧类型对不对', 'ros2 interface show sensor_msgs/msg/LaserScan', '字段结构匹配 YAML'],
    ['4', '时钟与 TF', 'ros2 topic info /clock; ros2 topic echo /tf_static --once', '发布者=1；有 lidar_link'],
], [1.2, 3.8, 6.2, 4.4])
h2('3.4 启动与验收')
code('ros2 run ros_gz_bridge parameter_bridge \\\n  --ros-args -p config_file:=$HOME/ros2_ws_w12/src/week12_odometry/config/bridge_w12.yaml\n\nros2 topic hz /scan --window 20     # 实测约 9.8 Hz\nros2 topic info /clock              # Publisher count = 1\nros2 topic hz /odom --window 20     # 实测约 99 Hz')
p('频率是判断桥接是否真正在工作的硬指标。只看 ros2 topic list 有 /scan 不够——桥接可能只是建了发布者，字段映射错了就一条不发。hz 有稳定输出，才说明消息真的过来了。')

qa('互问互答 ③　车不动，一定是桥接坏了吗？', [
    '【教师设问】我发了 /cmd_vel_target，车纹丝不动。看板上目标速度有值，实际速度是零。第一反应去查桥接，对不对？',
    '【学生甲】对，车不动肯定是桥没把指令送进 Gazebo。',
    '【学生乙】不一定。看板上目标速度有值，只说明网页到 velocity_arbiter 这一段是通的。后面还有看门狗、PID 仲裁、控制器、桥接、Gazebo 插件五段。',
    '【学生丙】看门狗最容易忘：超过 0.6 秒没新指令就自动归零。用一次 ros2 topic pub 发一条，车只会动一下，然后被看门狗停住。',
    '【学生乙】还有控制器状态。ros2 control list_controllers 看一眼，如果 diff_drive_controller 是 inactive，发什么都白搭。',
    '【教师点评】这就是我们强调分层定位的理由。正确顺序是：指令有没有到目标话题 → 看门狗是不是把它清零了 → 控制器 active 没有 → 桥接有没有映射 → Gazebo 插件有没有加载。每步一条命令，五分钟定位完。上来就改桥接 YAML，可能把本来好的配置改坏。',
])

fig(DASH_PNG, '图 3-1　课堂网页看板实测：轨迹、PID 曲线、激光极坐标与 SLAM 地图四宫格')
p('看板上②号格的三条曲线是判断闭环是否工作的直接证据：黄色是目标速度，绿色是实测速度，橙色是控制器输出。实测里目标 0.350 米每秒，负载 0.65 时实测只有 0.32 左右，PID 把输出顶到 0.49–0.52，几秒后实测爬回 0.33。这条曲线和桥接本身无关，但它能一眼告诉你指令链路上有没有断。')

# ============================================================ 收尾
h1('课堂验收与实验要求')
h2('5.1 三段必做演示')
code('# ① 世界：看场地、看墙、看物理参数\ngz sdf -p worlds/arena_w12.sdf > /tmp/norm.sdf && gz model --list\n\n# ② 模型：展开 Xacro、检查 URDF、看 TF\nxacro src/diffbot_description/urdf/diffbot_sim.urdf.xacro > /tmp/r.urdf\ncheck_urdf /tmp/r.urdf\nros2 run tf2_tools view_frames\n\n# ③ 桥接：查频率、查时钟、查静态 TF\nros2 topic hz /scan --window 20\nros2 topic info /clock\nros2 topic echo /tf_static --once')
h2('5.2 交作业要附的证据')
b('三张窗口截图：Gazebo 场景、RViz 的 TF 树或点云、网页看板四宫格。')
b('两条命令回显：ros2 topic info /clock（发布者=1）与 ros2 control list_controllers（控制器 active）。')
b('一段 30 秒录屏：发速度指令后车动起来，且看板实测速度非零。')
b('一份排错记录：至少写清一个自己遇到的故障，按「现象 → 分层定位 → 根因 → 解法」四段写。')
note(['Ubuntu 26.04 目前没有本机实测样本。如果学生自己装了 26.04 想复现，请先 lsb_release -a 与 ros2 --version 核对发行版，再按官方文档调整包名与插件名。',
      'Humble 学生端的差异：Gazebo 插件名、部分 launch 参数名、以及 ROS 2 CLI 的少数子命令不同；核心的 topic / node / param / interface 命令一致。'],
     '版本兼容说明', 'warn')

h1('附录　命令速查')
tb('表 A-1　三层对应的高频命令', ['层', '命令', '用途'], [
    ['世界', 'gz sim -r -v2 worlds/arena_w12.sdf', '带 GUI 启动世界'],
    ['世界', 'gz sdf -p file.sdf > /tmp/n.sdf', '规范化 SDF'],
    ['世界', 'gz model --list', '列出世界内模型'],
    ['模型', 'xacro file.xacro > /tmp/r.urdf', '展开模型宏'],
    ['模型', 'check_urdf /tmp/r.urdf', '校验 URDF 语义'],
    ['模型', 'ros2 run tf2_tools view_frames', '导出 TF 树'],
    ['桥接', 'ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=bridge.yaml', '启动桥接'],
    ['桥接', 'ros2 topic hz /scan --window 20', '验证消息真的在传'],
    ['桥接', 'ros2 interface show geometry_msgs/msg/TwistStamped', '查字段结构'],
    ['全栈', 'bash check_w12.sh', '24 项自检'],
    ['全栈', 'bash 02_停止全部.sh', '只清自己的场'],
], [1.6, 9.4, 4.6])


def render():
    doc = ak.new_doc(header_text='Gazebo 世界 · 模型 · ROS2 桥接 · 课件讲义')
    ak.cover2(
        doc,
        title='Gazebo 世界、模型与 ROS2 桥接',
        subtitle='明日课堂讲义 —— 三层分离、现场演示与师生互问互答',
        fields=[
            ('课程名称', '机器学习与智能机器人应用技术（智能机器人线）'),
            ('适用周次', '第 13 周课件 · 2 学时（90 分钟）'),
            ('授课对象', '机器人工程 / 智能控制技术专业'),
            ('配套环境', 'Ubuntu 24.04 + ROS 2 Jazzy + Gazebo 8.11（DGX 实测）'),
            ('配套资源', '五分钟演示片 + 网页命令门户 + Excel 全量手册'),
        ],
        date='2026 年 11 月',
    )
    doc.add_page_break()
    add_toc(doc, levels='1-1')
    setup_toc_styles(doc)
    enable_update_fields(doc)
    add_footer_page_number(doc, prefix='— ', first_page_blank=True)
    doc.add_page_break()
    first = False
    for it in B:
        k = it[0]
        if k == 'h1':
            heading(doc, it[1], 1, pb=first)
            first = False
        elif k == 'h2':
            heading(doc, it[1], 2)
        elif k == 'p':
            ak.para(doc, it[1])
        elif k == 'b':
            ak.bullet2(doc, it[1])
        elif k == 'code':
            code_block(doc, it[1])
        elif k == 'table':
            _, cap, head, rows, widths, fs = it
            ak.table2(doc, [head] + rows, caption=cap, widths=widths, font_size=fs)
        elif k == 'qa':
            heading(doc, it[1], 2)
            for ln in it[2]:
                ak.para(doc, ln, indent=False, line=1.35)
        elif k == 'note':
            ak.note(doc, it[1], kind=it[3], title=it[2])
        elif k == 'fig':
            if os.path.exists(it[1]):
                figure(doc, it[1], it[2], width_cm=15.0)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc.save(OUT)
    return doc


if __name__ == '__main__':
    import re
    d = render()
    text = '\n'.join([x.text for x in d.paragraphs] +
                     [c.text for t in d.tables for r in t.rows for c in r.cells])
    print('saved:', OUT)
    print('汉字:', len(re.findall(r'[\u4e00-\u9fff]', text)), '字符:', count_chars(d))
    print('paragraphs:', len(d.paragraphs), 'tables:', len(d.tables), 'KB:', round(os.path.getsize(OUT)/1024, 1))
