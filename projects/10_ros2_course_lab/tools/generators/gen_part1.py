# -*- coding: utf-8 -*-
"""生成 W12 课件包：包骨架 + launch + 配置 + 世界 + RViz。"""
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ros2_ws_w12')
PKG = os.path.join(ROOT, 'src', 'week12_odometry')

FILES = {}

# ---------------------------------------------------------------- CMake
FILES['CMakeLists.txt'] = r'''cmake_minimum_required(VERSION 3.16)
project(week12_odometry)

find_package(ament_cmake REQUIRED)

# 资源：launch / 参数 / 世界 / RViz
install(DIRECTORY launch config worlds rviz
        DESTINATION share/${PROJECT_NAME}
        USE_SOURCE_PERMISSIONS)

# 可执行脚本统一装到 lib/<包名>/，ros2 run 才能找到
install(PROGRAMS
        scripts/velocity_arbiter.py
        scripts/telemetry_node.py
        scripts/odom_eval.py
        scripts/check_w12.sh
        scripts/drive_demo.sh
        scripts/save_map.sh
        scripts/stop_all.sh
        DESTINATION lib/${PROJECT_NAME})

ament_package()
'''

FILES['package.xml'] = r'''<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>week12_odometry</name>
  <version>1.0.0</version>
  <description>W12 运动学、里程计与 PID 控制：Gazebo 仿真 + SLAM 建图 + 网页看板</description>
  <maintainer email="course@example.com">ROS2 Course</maintainer>
  <license>Apache-2.0</license>

  <buildtool_depend>ament_cmake</buildtool_depend>

  <exec_depend>rclpy</exec_depend>
  <exec_depend>geometry_msgs</exec_depend>
  <exec_depend>nav_msgs</exec_depend>
  <exec_depend>sensor_msgs</exec_depend>
  <exec_depend>tf2_msgs</exec_depend>
  <exec_depend>std_msgs</exec_depend>
  <exec_depend>xacro</exec_depend>
  <exec_depend>robot_state_publisher</exec_depend>
  <exec_depend>ros_gz_sim</exec_depend>
  <exec_depend>ros_gz_bridge</exec_depend>
  <exec_depend>gz_ros2_control</exec_depend>
  <exec_depend>controller_manager</exec_depend>
  <exec_depend>diff_drive_controller</exec_depend>
  <exec_depend>joint_state_broadcaster</exec_depend>
  <exec_depend>rviz2</exec_depend>
  <exec_depend>slam_toolbox</exec_depend>
  <exec_depend>nav2_map_server</exec_depend>
  <exec_depend>diffbot_description</exec_depend>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
'''

# ---------------------------------------------------------------- launch
FILES['launch/demo_w12.launch.py'] = r'''#!/usr/bin/env python3
"""
demo_w12.launch.py —— 第12周课堂一键启动：Gazebo → ros2_control → 里程计 → SLAM → 看板
=====================================================================================
启动顺序（顺序错了必然失败，W10 已踩过）：
  1. gz sim 载入 arena_w12.sdf          物理世界先存在
  2. ros_gz_bridge                      /clock 与传感器立刻可用
  3. robot_state_publisher              展开 xacro，发布 /robot_description 与静态 TF
  4. ros_gz_sim create -topic           生成实体，gz_ros2_control 插件此时才加载
  5. spawner 两个控制器（幂等）          先状态广播，后运动控制
  6. velocity_arbiter                   看门狗 + PID 闭环 + 指令仲裁
  7. telemetry_node                     把 ROS 数据落成 JSON 给网页看板
  8. rviz2 / slam_toolbox（可选）        可视化与建图

课堂用法（在 Ubuntu 桌面终端执行）：
  source ~/ros2_ws_w12/install/setup.bash
  ros2 launch week12_odometry demo_w12.launch.py                 # 全开窗：Gazebo+RViz+SLAM
  ros2 launch week12_odometry demo_w12.launch.py gui:=false     # 无桌面/SSH：只跑服务
  ros2 launch week12_odometry demo_w12.launch.py slam:=false    # 只讲运动学，不建图
  ros2 launch week12_odometry demo_w12.launch.py mode:=pid      # 切到 PID 闭环演示

★ 三个高频坑，都写进注释里了：
  · GZ_SIM_SYSTEM_PLUGIN_PATH 必须手动补 gz_ros2_control 的 lib，否则 /controller_manager 不出现
  · /clock 只能有一个发布者，反复启停会残留 bridge 子进程 → RViz 每 2 秒清屏
  · Jazzy 的 diff_drive_controller 只收 TwistStamped，发 Twist 会静默丢消息
"""
import os

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable, DeclareLaunchArgument, ExecuteProcess,
    IncludeLaunchDescription, TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import IfCondition, UnlessCondition
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
import xacro


def generate_launch_description():
    desc_share = get_package_share_directory('diffbot_description')
    w12_share = get_package_share_directory('week12_odometry')

    xacro_file = os.path.join(desc_share, 'urdf', 'diffbot_sensors.urdf.xacro')
    world_file = os.path.join(w12_share, 'worlds', 'arena_w12.sdf')
    rviz_file = os.path.join(w12_share, 'rviz', 'demo_w12.rviz')
    bridge_file = os.path.join(w12_share, 'config', 'bridge_w12.yaml')
    slam_file = os.path.join(w12_share, 'config', 'slam_w12.yaml')
    data_file = '/tmp/w12_dashboard.json'
    cmd_file = '/tmp/w12_cmd.json'

    # xacro 在 launch 阶段就展开成字符串：RSP 只认 URDF，不认 xacro。
    # 传感器版（diffbot_sensors）带 2D 激光雷达，SLAM 才能拿到 /scan。
    robot_description = xacro.process_file(xacro_file).toxml()

    gui = LaunchConfiguration('gui')
    use_rviz = LaunchConfiguration('rviz')
    use_slam = LaunchConfiguration('slam')
    mode = LaunchConfiguration('mode')
    world = LaunchConfiguration('world')

    # gz sim 参数：-r 立即步进；-s 只跑服务器（SSH 必须）；-v2 日志级别
    gz_with_gui = ExecuteProcess(
        cmd=['gz', 'sim', '-r', '-v2', world],
        output='screen', condition=IfCondition(gui), on_exit=Shutdown(),
    )
    gz_headless = ExecuteProcess(
        cmd=['gz', 'sim', '-r', '-s', '-v2', world],
        output='screen', condition=UnlessCondition(gui), on_exit=Shutdown(),
    )

    # 幂等控制器激活：gz_ros2_control 有时已自动 load 并 active，
    # 再 spawner 一次会刷一屏 ERROR。先查再补，课堂演示不出现假故障。
    def ensure_controller(name, delay):
        check = (
            'ros2 control list_controllers 2>/dev/null '
            f'| grep -q "{name}.*active" && exit 0; '
            f'exec ros2 run controller_manager spawner {name} '
            '--controller-manager /controller_manager'
        )
        return TimerAction(period=delay, actions=[
            ExecuteProcess(cmd=['bash', '-c', check], output='screen'),
        ])

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true',
                              description='true=打开 Gazebo GUI 窗口（需 DISPLAY）'),
        DeclareLaunchArgument('rviz', default_value='true',
                              description='true=打开 RViz2 可视化窗口'),
        DeclareLaunchArgument('slam', default_value='true',
                              description='true=启动 slam_toolbox 在线建图'),
        DeclareLaunchArgument('mode', default_value='passthrough',
                              description='passthrough=直接转发 | pid=速度闭环'),
        DeclareLaunchArgument('load_factor', default_value='1.0',
                              description='教学负载注入：1.0=无负载；0.65=车只能跑出指令的 65%，'
                                          'PID 补偿过程在网页看板上一眼可见'),
        DeclareLaunchArgument('world', default_value=world_file,
                              description='SDF 世界文件路径'),

        # model:// 解析路径
        AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', desc_share),
        # ★ 环境坑：gz_ros2_control 没装环境钩子，不补这一行插件加载失败
        AppendEnvironmentVariable(
            'GZ_SIM_SYSTEM_PLUGIN_PATH',
            os.path.join(get_package_prefix('gz_ros2_control'), 'lib')),

        # ---------- 1. Gazebo（GUI / 纯服务器 二选一） ----------
        gz_with_gui,
        gz_headless,

        # ---------- 2. 唯一的一个桥 ----------
        # /clock 多个发布者会让 RViz 反复 "Detected jump back in time"，
        # 所以本文件只声明一个 parameter_bridge，绝不再额外起第二个。
        Node(
            package='ros_gz_bridge', executable='parameter_bridge',
            name='w12_bridge', output='screen',
            parameters=[{'config_file': bridge_file, 'use_sim_time': True}],
        ),

        # ---------- 3. 机器人描述 + 静态 TF ----------
        Node(
            package='robot_state_publisher', executable='robot_state_publisher',
            name='robot_state_publisher', output='screen',
            parameters=[{'robot_description': robot_description, 'use_sim_time': True}],
        ),

        # ---------- 4. 生成实体 ----------
        Node(
            package='ros_gz_sim', executable='create', output='screen',
            arguments=['-topic', '/robot_description', '-name', 'diffbot',
                       '-x', '0.0', '-y', '0.0', '-z', '0.05'],
        ),

        # ---------- 5. 控制器（create 是异步的，延迟 8/10 s） ----------
        ensure_controller('joint_state_broadcaster', 8.0),
        ensure_controller('diff_drive_controller', 10.0),

        # ---------- 6. 指令仲裁：看门狗 + PID ----------
        TimerAction(period=11.0, actions=[
            Node(
                package='week12_odometry', executable='velocity_arbiter.py',
                name='velocity_arbiter', output='screen',
                parameters=[{
                    'mode': mode,
                    'cmd_file': cmd_file,
                    'timeout': 0.6,
                    'kp': 1.8, 'ki': 0.35, 'kd': 0.02,
                    'max_linear': 0.8,
                    # ParameterValue 必须显式转 float：LaunchConfiguration 求值是字符串，
                    # 而 arbiter 把 load_factor 声明成 double，直接传会类型冲突。
                    'load_factor': ParameterValue(
                        LaunchConfiguration('load_factor'), value_type=float),
                    'use_sim_time': True,
                }],
            ),
        ]),

        # ---------- 7. 遥测：ROS → JSON → 网页看板 ----------
        TimerAction(period=12.0, actions=[
            Node(
                package='week12_odometry', executable='telemetry_node.py',
                name='w12_telemetry', output='screen',
                parameters=[{'data_file': data_file, 'use_sim_time': True}],
            ),
        ]),

        # ---------- 8. RViz2 ----------
        TimerAction(period=13.0, actions=[
            Node(
                package='rviz2', executable='rviz2', output='screen',
                condition=IfCondition(use_rviz),
                arguments=['-d', rviz_file],
                parameters=[{'use_sim_time': True}],
            ),
        ]),

        # ---------- 9. SLAM Toolbox 在线异步建图 ----------
        # 依赖：/scan（gpu_lidar 桥出）、odom→base_footprint（控制器发）、
        #       base_footprint→lidar_link（RSP 发静态 TF）。三者齐了才不报 TF 错。
        #
        # ★★ 必须 include 官方 launch，不能自己写 Node ★★
        #   slam_toolbox 是 LifecycleNode：普通 Node 起完后停在 unconfigured，
        #   参数文件照样加载、日志照样打印，但永远不发 /map，
        #   表现为「/map Publisher count = 0」，且日志只有一句 stack size。
        #   官方 online_async_launch.py 用 LifecycleNode + EmitEvent 自动发
        #   TRANSITION_CONFIGURE / TRANSITION_ACTIVATE，缺了这两步就是白起。
        TimerAction(period=15.0, actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(os.path.join(
                    get_package_share_directory('slam_toolbox'), 'launch',
                    'online_async_launch.py')),
                launch_arguments={
                    'slam_params_file': slam_file,
                    'use_sim_time': 'true',
                    'autostart': 'true',
                    'use_lifecycle_manager': 'false',
                }.items(),
                condition=IfCondition(use_slam),
            ),
        ]),
    ])
'''

# ---------------------------------------------------------------- config
FILES['config/bridge_w12.yaml'] = r'''# ============================================================
#  bridge_w12.yaml  —— W12 Gazebo ↔ ROS 2 桥接表（唯一一个 bridge）
# ============================================================
# 字段三件套 ros_topic_name / ros_type_name / gz_type_name 必须齐；
# direction 用 GZ_TO_ROS（仿真 → ROS）。
# 注意世界名已经改成 arena_w12，所以真值话题路径也随之改变，
# 写成 /world/arena/dynamic_pose/info 会拿到空数据，且不报错。
# ------------------------------------------------------------

# 1) 时钟：全链路 use_sim_time=true，唯一来源是 Gazebo
- ros_topic_name: /clock
  gz_topic_name: /clock
  ros_type_name: rosgraph_msgs/msg/Clock
  gz_type_name: gz.msgs.Clock
  direction: GZ_TO_ROS

# 2) 2D 激光：SLAM Toolbox 的输入，也是 RViz 的 LaserScan 显示源
- ros_topic_name: /scan
  gz_topic_name: /scan
  ros_type_name: sensor_msgs/msg/LaserScan
  gz_type_name: gz.msgs.LaserScan
  direction: GZ_TO_ROS

# 3) IMU：W13 卡尔曼融合要用，W12 先把它接出来做数据体检
- ros_topic_name: /imu/data_raw
  gz_topic_name: /imu
  ros_type_name: sensor_msgs/msg/Imu
  gz_type_name: gz.msgs.IMU
  direction: GZ_TO_ROS

# 4) 相机：RViz 的 Image 面板
- ros_topic_name: /camera/image_raw
  gz_topic_name: /camera/image
  ros_type_name: sensor_msgs/msg/Image
  gz_type_name: gz.msgs.Image
  direction: GZ_TO_ROS

- ros_topic_name: /camera/camera_info
  gz_topic_name: /camera/camera_info
  ros_type_name: sensor_msgs/msg/CameraInfo
  gz_type_name: gz.msgs.CameraInfo
  direction: GZ_TO_ROS

# 5) 仿真真值：odom_eval.py / telemetry 用它算「里程计到底差多少」
#    gz.msgs.Pose_V → tf2_msgs/TFMessage，帧名形如 arena_w12/diffbot
- ros_topic_name: /world/arena_w12/dynamic_pose/info
  gz_topic_name: /world/arena_w12/dynamic_pose/info
  ros_type_name: tf2_msgs/msg/TFMessage
  gz_type_name: gz.msgs.Pose_V
  direction: GZ_TO_ROS
'''

FILES['config/slam_w12.yaml'] = r'''# ============================================================
#  slam_w12.yaml —— slam_toolbox 在线异步建图（参数名对齐 Jazzy 官方模板）
# ============================================================
# 模板位置：/opt/ros/jazzy/share/slam_toolbox/config/mapper_params_online_async.yaml
# 本文件只改了与教学场景相关的 7 项，其余保持官方默认：
#   resolution 0.05        → 10 m 房间 = 200×200 栅格，看板画得下
#   max_laser_range 12.0   → 与 URDF 里 gpu_lidar 的 <range><max> 一致
#   minimum_travel_distance 0.2  → 默认 0.5 对 0.4 m 小车太大，走半米才更新一帧
#   map_update_interval 1.0      → 课堂要看得见地图长出来，默认 5 s 太慢
#   minimum_time_interval 0.2
#   throttle_scans 1
#   do_loop_closing true   → 绕场地一圈后能看到回环修正（W12 结尾的彩蛋）
# ------------------------------------------------------------
slam_toolbox:
  ros__parameters:
    use_sim_time: true

    solver_plugin: solver_plugins::CeresSolver
    ceres_linear_solver: SPARSE_NORMAL_CHOLESKY
    ceres_preconditioner: SCHUR_JACOBI
    ceres_trust_strategy: LEVENBERG_MARQUARDT
    ceres_dogleg_type: TRADITIONAL_DOGLEG
    ceres_loss_function: None

    odom_frame: odom
    map_frame: map
    base_frame: base_footprint
    scan_topic: /scan
    use_map_saver: true
    mode: mapping

    debug_logging: false
    throttle_scans: 1
    transform_publish_period: 0.02
    map_update_interval: 1.0
    resolution: 0.05
    min_laser_range: 0.12
    max_laser_range: 12.0
    minimum_time_interval: 0.2
    minimum_travel_distance: 0.2
    minimum_travel_heading: 0.2
    transform_timeout: 0.2
    tf_buffer_duration: 30.0
    stack_size_to_use: 40000000
    enable_interactive_mode: false

    use_scan_matching: true
    use_scan_barycenter: true
    scan_buffer_size: 20
    scan_buffer_maximum_scan_distance: 10.0
    link_match_minimum_response_fine: 0.1
    link_scan_maximum_distance: 1.5
    loop_search_maximum_distance: 3.0
    do_loop_closing: true
    loop_match_minimum_chain_size: 10
    loop_match_maximum_variance_coarse: 3.0
    loop_match_minimum_response_coarse: 0.35
    loop_match_minimum_response_fine: 0.45

    correlation_search_space_dimension: 0.5
    correlation_search_space_resolution: 0.01
    correlation_search_space_smear_deviation: 0.1
    loop_search_space_dimension: 8.0
    loop_search_space_resolution: 0.05
    loop_search_space_smear_deviation: 0.03

    distance_variance_penalty: 0.5
    angle_variance_penalty: 1.0
    fine_search_angle_offset: 0.00349
    coarse_search_angle_offset: 0.349
    coarse_angle_resolution: 0.0349
    minimum_angle_penalty: 0.9
    minimum_distance_penalty: 0.5
    use_response_expansion: true
    min_pass_through: 2
    occupancy_threshold: 0.1
'''

# ---------------------------------------------------------------- RViz
FILES['rviz/demo_w12.rviz'] = r'''Panels:
  - Class: rviz_common/Displays
    Help Height: 70
    Name: Displays
    Property Tree Widget:
      Expanded:
        - /RobotModel1
        - /TF1
      Splitter Ratio: 0.5
    Tree Height: 620
  - Class: rviz_common/Views
    Expanded:
      - /Current View1
    Name: Views
    Splitter Ratio: 0.5
Visualization Manager:
  Class: ""
  Displays:
    - Alpha: 0.5
      Cell Size: 0.5
      Class: rviz_default_plugins/Grid
      Color: 130; 138; 150
      Enabled: true
      Line Style:
        Line Width: 0.03
        Value: Lines
      Name: Grid
      Normal Cell Count: 0
      Plane: XY
      Plane Cell Count: 20
      Reference Frame: <Fixed Frame>
      Value: true
    - Alpha: 1
      Class: rviz_default_plugins/RobotModel
      Description Source: Topic
      Description Topic:
        Depth: 5
        Durability Policy: Transient Local
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /robot_description
      Enabled: true
      Name: RobotModel
      Value: true
      Visual Enabled: true
    - Class: rviz_default_plugins/TF
      Enabled: true
      Frame Timeout: 15
      Frames:
        All Enabled: true
      Marker Scale: 0.3
      Name: TF
      Show Arrows: true
      Show Axes: true
      Show Names: true
      Tree:
        {}
      Value: true
    - Alpha: 1
      Class: rviz_default_plugins/LaserScan
      Color: 0; 255; 90
      Color Transformer: FlatColor
      Enabled: true
      Name: LaserScan
      Size (Pixels): 3
      Size (m): 0.035
      Style: Flat Squares
      Topic:
        Depth: 5
        Durability Policy: Volatile
        History Policy: Keep Last
        Reliability Policy: Best Effort
        Value: /scan
      Use Fixed Frame: true
      Value: true
    - Alpha: 0.8
      Class: rviz_default_plugins/Map
      Color Scheme: map
      Draw Behind: false
      Enabled: true
      Name: SLAM Map
      Topic:
        Depth: 5
        Durability Policy: Transient Local
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /map
      Use Timestamp: false
      Value: true
    - Angle Tolerance: 0.1
      Class: rviz_default_plugins/Odometry
      Covariance:
        Orientation:
          Alpha: 0.4
          Color: 255; 255; 127
          Frame: Local
          Value: true
        Position:
          Alpha: 0.3
          Color: 204; 51; 204
          Frame: Local
          Value: true
        Value: true
      Enabled: true
      Keep: 2000
      Name: Odom Trail
      Shape:
        Alpha: 1
        Axes Length: 1
        Axes Radius: 0.1
        Color: 255; 140; 0
        Head Length: 0.12
        Head Radius: 0.06
        Shaft Length: 0.22
        Shaft Radius: 0.03
        Value: Arrow
      Topic:
        Depth: 5
        Durability Policy: Volatile
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /odom
      Value: true
    - Class: rviz_default_plugins/Image
      Enabled: true
      Max Value: 1
      Min Value: 0
      Name: Camera
      Normalize Range: true
      Topic:
        Depth: 5
        Durability Policy: Volatile
        History Policy: Keep Last
        Reliability Policy: Best Effort
        Value: /camera/image_raw
      Value: true
  Enabled: true
  Global Options:
    Background Color: 40; 44; 52
    Fixed Frame: odom
    Frame Rate: 30
  Name: root
  Tools:
    - Class: rviz_default_plugins/Interact
    - Class: rviz_default_plugins/MoveCamera
    - Class: rviz_default_plugins/Select
    - Class: rviz_default_plugins/FocusCamera
    - Class: rviz_default_plugins/Measure
  Transformation:
    Current:
      Class: rviz_default_plugins/TF
  Value: true
  Views:
    Current:
      Class: rviz_default_plugins/Orbit
      Distance: 9.0
      Focal Point:
        X: 0
        Y: 0
        Z: 0
      Focal Shape Fixed Size: true
      Focal Shape Size: 0.05
      Invert Z Axis: false
      Name: Current View
      Near Clip Distance: 0.01
      Pitch: 0.85
      Target Frame: <Fixed Frame>
      Value: Orbit (rviz)
      Yaw: 0.8
    Saved: ~
Window Geometry:
  Displays:
    collapsed: false
  Height: 960
  Hide Left Dock: false
  Hide Right Dock: false
  Width: 1500
  X: 60
  Y: 60
'''


def write_all(files, base=PKG):
    for rel, text in files.items():
        p = os.path.join(base, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        print('  +', rel, len(text.splitlines()), 'lines')


if __name__ == '__main__':
    print('[part1] 生成包骨架 / launch / config / rviz')
    write_all(FILES)

    # ---- 世界文件：复用 W10/W11 的 arena.sdf，改世界名并追加教学障碍 ----
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ref', 'w1011',
                       'src', 'week10_control', 'worlds', 'arena.sdf')
    sdf = open(src, encoding='utf-8').read().replace('<world name="arena">',
                                                      '<world name="arena_w12">')
    extra = r'''
    <!-- ============ W12 追加：L 形隔墙（让 SLAM 地图有可辨识结构） ============ -->
    <!-- 直线墙 + 拐角能直观看出「回环修正」：绕一圈回来后墙会重新对齐 -->
    <model name="wall_inner_a">
      <static>true</static>
      <pose>-1.2 0.8 0.35 0 0 0</pose>
      <link name="link">
        <collision name="c"><geometry><box><size>2.4 0.12 0.7</size></box></geometry></collision>
        <visual name="v">
          <geometry><box><size>2.4 0.12 0.7</size></box></geometry>
          <material>
            <ambient>0.55 0.55 0.58 1</ambient>
            <diffuse>0.65 0.65 0.68 1</diffuse>
          </material>
        </visual>
      </link>
    </model>

    <model name="wall_inner_b">
      <static>true</static>
      <pose>0.0 2.0 0.35 0 0 0</pose>
      <link name="link">
        <collision name="c"><geometry><box><size>0.12 2.4 0.7</size></box></geometry></collision>
        <visual name="v">
          <geometry><box><size>0.12 2.4 0.7</size></box></geometry>
          <material>
            <ambient>0.55 0.55 0.58 1</ambient>
            <diffuse>0.65 0.65 0.68 1</diffuse>
          </material>
        </visual>
      </link>
    </model>

'''
    sdf = sdf.replace('\n  </world>', extra + '  </world>')
    p = os.path.join(PKG, 'worlds', 'arena_w12.sdf')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8', newline='\n').write(sdf)
    print('  + worlds/arena_w12.sdf', len(sdf.splitlines()), 'lines')
    print('[part1] done')
