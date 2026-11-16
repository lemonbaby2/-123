#!/usr/bin/env python3
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

        # ---------- 5b. 里程计话题归一化 ----------
        TimerAction(period=11.0, actions=[
            Node(
                package='week12_odometry', executable='odom_relay.py',
                name='odom_relay', output='screen',
                parameters=[{'use_sim_time': True}],
            ),
        ]),

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
