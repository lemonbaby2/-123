#!/usr/bin/env python3
"""
display.launch.py —— 只做模型可视化，不启动 Gazebo
====================================================
用途：W10 第一步，先确认 URDF/Xacro 本身没写错（连杆树、TF、关节限位），
      再去接物理仿真。模型都没显示对就上 Gazebo，只会把错误藏在物理里。

两种用法：
  1) 手动拖动关节：  ros2 launch diffbot_description display.launch.py gui:=true
  2) 纯静态查看：    ros2 launch diffbot_description display.launch.py

⚠️ gui:=true 需要 DISPLAY（图形界面）。在 SSH 无 X11 的环境里必须用 gui:=false，
   否则 joint_state_publisher_gui 会直接 abort(-6)，这是 W08 已经踩过的坑。
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    pkg_share = get_package_share_directory('diffbot_description')

    # 允许从命令行换模型文件，默认 W10 底盘
    urdf_file = LaunchConfiguration('urdf_file')
    use_gui = LaunchConfiguration('gui')
    use_rviz = LaunchConfiguration('rviz')

    default_urdf = os.path.join(pkg_share, 'urdf', 'diffbot_sim.urdf.xacro')
    default_rviz = os.path.join(pkg_share, 'rviz', 'diffbot.rviz')

    # xacro 在 launch 阶段就展开成纯 URDF 字符串，再交给 robot_state_publisher。
    # 好处：RSP 不需要知道 xacro 的存在；坏处：改 xacro 必须重启 launch。
    robot_description = xacro.process_file(default_urdf).toxml()

    return LaunchDescription([
        DeclareLaunchArgument(
            'urdf_file', default_value=default_urdf,
            description='要显示的 xacro 文件绝对路径'),
        DeclareLaunchArgument(
            'gui', default_value='false',
            description='true=弹出关节滑块（需要图形界面）'),
        DeclareLaunchArgument(
            'rviz', default_value='true',
            description='是否启动 RViz2'),

        # 把 URDF 字符串塞进参数，RSP 负责算整棵 TF 树
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_description,
                         'use_sim_time': False}]),

        # 无 GUI：用一个会动的小节点持续发关节角，让轮子转起来
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            condition=UnlessCondition(use_gui),
            parameters=[{'robot_description': robot_description}]),

        # 有 GUI：滑块手动调
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            condition=IfCondition(use_gui),
            parameters=[{'robot_description': robot_description}]),

        Node(
            package='rviz2',
            executable='rviz2',
            condition=IfCondition(use_rviz),
            arguments=['-d', default_rviz],
            output='screen'),
    ])
