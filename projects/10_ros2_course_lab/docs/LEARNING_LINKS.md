# 学习资源入口

这 14 条是从课程命令手册里捡回来的常用入口，按用途分组。全部是外部站点，链接有效性不由本仓库保证。

## 官方文档（查接口和参数的第一站）

| 名称 | 地址 | 用途 |
|---|---|---|
| ROS 2 Jazzy 文档 | https://docs.ros.org/en/jazzy/ | 本仓库 24.04 环境对应 |
| ROS 2 Humble 文档 | https://docs.ros.org/en/humble/ | 学生端 22.04 环境对应 |
| ROS 2 Tutorials | https://docs.ros.org/en/jazzy/Tutorials.html | 节点、话题、Launch 入门 |
| rviz2 用户指南 | https://github.com/ros2/rviz | `.rviz` 配置格式 |
| Gazebo Sim 文档 | https://gazebosim.org/docs | SDF、世界、模型 |
| ros_gz 桥接 | https://github.com/gazebosim/ros_gz | 桥接 YAML 四字段 |
| Navigation2 文档 | https://navigation.ros.org/ | 导航栈与调参 |
| slam_toolbox | https://github.com/SteveMacenski/slam_toolbox | Lifecycle 状态机 |
| ros2_control 文档 | https://control.ros.org/ | 硬件接口与控制器 |

## 中文教程与代码参考

| 名称 | 地址 | 用途 |
|---|---|---|
| 古月居 ROS2 入门教程 | https://www.guyuehome.com/ | 课程主参考 |
| ros2_21_tutorials | https://github.com/guyuehome/ros2_21_tutorials | 离线包源码 |
| ROS 中文网 | https://www.ros.org.cn/ | 中文社区 |
| ROS2 官方示例 | https://github.com/ros2/examples | 可直接跑的最小例子 |
| Gitee 镜像 | https://gitee.com/mirrors | GitHub 拉不动时替代 |

## 怎么把这些链接用起来

1. 课堂上遇到「发了速度车不动」，先查 `ros2 topic info /cmd_vel` 的消息类型，再到 Jazzy 文档核对 `TwistStamped`。
2. 建图不出图，查 `ros2 lifecycle get /slam_toolbox`，对照 slam_toolbox 的 Lifecycle 说明。
3. 世界里的墙不显示，查 SDF 的 `<static>true</static>` 与 `<geometry>`，对照 Gazebo Sim 文档。
4. 桥接字段全零，对照 ros_gz 的 YAML 四字段：`ros_topic_name` / `ros_type_name` / `gz_type_name` / `direction`。

完整的逐条命令与注释在 [命令与代码手册](../teaching/ROS2与Ubuntu全量命令与验证代码手册_20261116.xlsx)，其中 Ubuntu 26.04 一列标为「待核」，首次使用前请先在本机验证。
