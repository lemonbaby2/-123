# 10 · ROS 2 课程实验平台：差速车运动学、里程计、PID 与 SLAM 可视化

这是一套面向课堂教学的 **ROS 2 Jazzy 全链路实验包**，把「仿真—控制—里程计—闭环—建图—网页可视化」串成一次 90 分钟可演示的完整链路。配套广州现代信息工程职业技术学院《机器学习与智能机器人应用技术》第 12–13 周教学。

它不是算法演示 PPT： Gazebo 里车真的跑，RViz 里 TF / 点云 / 轨迹 / 占用栅格同时在动，网页看板按 500 ms 刷新，PID 曲线能看出前馈与积分在补什么。

> **真实性边界**
> - **仓库实测**：`tests/` 下的算法单测与结构校验在此仓库可重跑；`evidence/selfcheck_w12.txt` 是 2026-11-13 在 DGX 上的 24 项终端回显；三张 PNG 与 5 分钟 MP4 是真实桌面录屏。
> - **课堂环境**：Ubuntu 22.04 + ROS 2 Humble 的代码按官方接口编写并在课程虚拟机中使用，本仓库没有该发行版的实机回显。
> - **待核**：Ubuntu 26.04 无本机样本，命令手册中该列标记为 C 级，不能当作已验证结果。
> - 演示中的 `load_factor=0.65` 是**人为注入的教学扰动**（模拟爬坡/打滑），不是真实机器人的物理模型。

## 一分钟验证（不需要 ROS、不需要 GPU）

```bash
python tests/test_course_algorithms.py -v      # 核心算法数值与接口
python tests/test_package_layout.py -v         # 结构、语法、脱敏、实测证据
python src/demo.py                             # 输出可解析 JSON 的演示
```

`demo.py` 只使用标准库，打印一段 0.35 m/s 目标速度在 0.65 负载下的 PID 闭环过程。

## 目录

| 路径 | 内容 |
|---|---|
| [src/course_algorithms.py](src/course_algorithms.py) | 从真实 ROS 节点抽出的纯 Python 核心算法：差速正/逆运动学、里程计积分、四元数偏航、前馈 PID、看门狗、TwistStamped 契约、激光极坐标、栅格索引 |
| [tests/](tests/test_course_algorithms.py) | 16 项算法单测 + 13 项结构/安全性检查，无 ROS 依赖 |
| [ros2_ws/](ros2_ws/README.md) | 完整 ROS 2 工作空间：URDF/Xacro、ros2_control、Gazebo 世界、ros_gz 桥接、里程计、PID 仲裁、slam_toolbox、RViz 配置、网页看板、自检与清场脚本 |
| [portal/](portal/index.html) | 课程资源门户单页：演示片播放、明日课件、ROS2/Ubuntu 命令搜索、学习网站；配 [range_server.py](portal/range_server.py) 支持 HTTP Range 拖动进度 |
| [teaching/](teaching/ROS2与Ubuntu全量命令与验证代码手册_20261116.xlsx) | 12 工作表命令与代码手册、[课件讲义](teaching/Gazebo世界模型与ROS2桥接_课件讲义_20261116.pdf)、[5000 字教师讲稿](teaching/ROS2运动学里程计与PID_教师演讲稿_5000字.docx) |
| [evidence/](evidence/selfcheck_w12.txt) | 24 项自检回显、[Gazebo 实拍](evidence/gazebo_world.png)、[RViz 实拍](evidence/rviz_odom_slam.png)、[看板实拍](evidence/web_dashboard.png)、[5 分钟录屏](evidence/course_demo_5min.mp4)、示例地图 |
| [docs/REPRODUCE.md](docs/REPRODUCE.md) | 从零构建与启动顺序、命令逐条解释 |
| [docs/MEASUREMENTS.md](docs/MEASUREMENTS.md) | 实测数字与口径，含误差计算式 |
| [docs/SECURITY.md](docs/SECURITY.md) | 隔离域、清场脚本、公开仓库脱敏原则 |
| [docs/LEARNING_LINKS.md](docs/LEARNING_LINKS.md) | 14 条 ROS 2 / Gazebo / Nav2 / SLAM 学习入口 |
| [docs/NEXT_STEPS_ROADMAP.md](docs/NEXT_STEPS_ROADMAP.md) | **学完 MuJoCo / ROS 2 / SLAM / Nav2 之后的 6 阶段路线**：状态估计 → 3DGS 语义建图 → MoveIt2 → VLA → 边缘部署，附 90 天排期与 11 个已 API 核实的资源 |

## 用一台 Ubuntu 机器跑起来

```bash
cd ros2_ws
bash 00_一键构建.sh                                   # 首次构建
bash 01_启动课堂.sh                                   # Gazebo + RViz2 + SLAM + 看板
bash src/week12_odometry/scripts/check_w12.sh         # 24 项自检，全绿再开讲
bash src/week12_odometry/scripts/drive_demo.sh all    # A 直行 / B 左转 / C 画圈
bash 03_保存地图.sh                                   # 保存 pgm + yaml
bash 02_停止全部.sh                                   # 下课只清自己的场
```

网页看板默认在 `http://127.0.0.1:8130/`；课程资源门户用 `python3 portal/range_server.py 8140` 启动，浏览 `http://127.0.0.1:8140/`。详细版本差异见[复现说明](docs/REPRODUCE.md)。

## 实测结果（口径见证据文档）

| 项目 | 结果 |
|---|---|
| `/odom` 频率 | 98.3–99.7 Hz；`/scan` 9.8 Hz；`/map` 1–2 Hz |
| A 段直行 | odom 2.4363 m vs Gazebo 真值 2.4361 m，相对误差 **0.0082 %** |
| A+B+C 综合终点误差 | 9.3 mm |
| PID（负载 0.65） | 目标 0.350 m/s，实测 0.318–0.334，输出顶到 0.487–0.516；松手后输出 −0.275 主动制动 |
| SLAM | `active [3]`；地图 199×199 @0.05 m；`map_saver` 产出 pgm + yaml |
| `/clock` | Publisher count = 1（多发布者会让 RViz 每 2 秒跳时间） |
| 课堂自检 | PASS = 24 / FAIL = 0 |

## 这里真正解决的五个坑

1. `slam_toolbox` 是 **LifecycleNode**；用普通 `Node` 起来会停在 `unconfigured`，日志照打但 `/map` 发布者恒为 0。必须 include 官方 `online_async_launch.py`。
2. `set -u` 包住 ROS 2 的 `setup.bash` 会炸（`AMENT_TRACE_SETUP_FILES: unbound variable`），统一用 `set -eo pipefail`。
3. Jazzy 的 `diff_drive_controller` 只收 `TwistStamped`；CLI YAML 必须是 `twist: {linear, angular}`，多套一层 `twist.twist` 会静默全零——两个坑都表现为「发了车不动」。
4. 生产机上不能 `pkill -f 'gz sim'`；本项目用 `ROS_DOMAIN_ID=42` + `GZ_PARTITION=w12course` 双隔离，清场脚本按项目独有文件名精确匹配。
5. SSH 远程命令里出现 `server.py --port 8130` 字面串会被自己的 `pkill` 命中导致断连，改用变量间接引用与方括号正则。

## 下一站：学完这套之后学什么

[完整学习路线手册](docs/NEXT_STEPS_ROADMAP.md)按优先级给出六阶段：**状态估计（P0）→ 3D 语义建图（P0，论文主线）→ MoveIt2 → VLA → 边缘部署 → 多机器人/科研输出**。每个阶段都附动手实验、量化验收标准和经过 GitHub API 核实的上游资源。结论一句话：SLAM/Nav2 的漂移与定位抖动，根因在状态估计层，不在调参；先补这一层，再做三维语义。

## 与仓库其他项目的关系

本项目是**教学与工程验证平台**，不替代 `projects/01_quadruped_slam` 的 SLAM 算子、`projects/04_industrial_vision` 的检测指标或 `projects/09_robotwin_hackathon` 的训练链路。它提供的是可现场演示的 ROS 2 系统集成、故障定位方法和课堂证据链；算法核心以独立纯 Python 模块公开，实机部分以完整工作空间源码公开。

公开版本不含任何私钥、真实内网地址、账号密码或生产机配置；相关内容以 `<LAB_HOST>` / `<TAILNET_HOST>` / `<USER>` / `<PASSWORD>` 占位，详见[安全边界](docs/SECURITY.md)。
