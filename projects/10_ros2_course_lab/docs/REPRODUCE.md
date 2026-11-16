# 复现说明

## 1. 两种使用方式

| 方式 | 目标 | 依赖 |
|---|---|---|
| 离线算法验证 | 检查算法接口、数值性质、仓库完整性 | Python 3.10+ 与 `openpyxl`/`PyYAML`（仅结构测试需要） |
| 实机课堂复现 | 在 Ubuntu 上跑完整 ROS 2 链路 | Ubuntu 24.04 + ROS 2 Jazzy + Gazebo 8.11 + ros_gz_bridge + slam_toolbox + Nav2 |

离线验证不需要 ROS、GPU 或网络：

```bash
python tests/test_course_algorithms.py -v
python tests/test_package_layout.py -v
python src/demo.py
```

## 2. 实机构建顺序

在 Ubuntu 桌面终端：

```bash
cd ros2_ws
bash 00_一键构建.sh        # colcon build，只在首次或改源码后执行
bash 01_启动课堂.sh        # 拉起 Gazebo + RViz2 + SLAM + 看板；约 20 s
bash src/week12_odometry/scripts/check_w12.sh
```

`check_w12.sh` 全绿后再开讲。任何一项 FAIL 都按备注排查，不要硬着头皮演示。

启动脚本用 `env.sh` 注入统一环境，关键是两个隔离变量：

```bash
export ROS_DOMAIN_ID=42          # DDS 域隔离，避免与同机其他 ROS 演示串话题
export GZ_PARTITION=w12course    # Gazebo 分区隔离，避免世界名与 /clock 冲突
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws_w12/install/setup.bash
```

**不要用 `set -u`** 包住 `source`：ROS 2 的 `setup.bash` 引用了未绑定变量 `AMENT_TRACE_SETUP_FILES`，会直接报错退出。

## 3. 课堂动作脚本

```bash
bash src/week12_odometry/scripts/drive_demo.sh a     # A 段直行
bash src/week12_odometry/scripts/drive_demo.sh b     # B 段原地左转
bash src/week12_odometry/scripts/drive_demo.sh c     # C 段画圈，给 SLAM 采集
bash src/week12_odometry/scripts/drive_demo.sh all   # 三段连跑
bash 03_保存地图.sh                                  # 存 pgm + yaml
bash 02_停止全部.sh                                  # 下课清场
```

网页看板在 `http://127.0.0.1:8130/`，可直接按方向按钮开车。指令写入 `/tmp/w12_cmd.json`，`velocity_arbiter.py` 读文件后转发。

## 4. 版本差异（不要跨发行版照抄）

| 项 | Ubuntu 22.04 / Humble | Ubuntu 24.04 / Jazzy（本仓库实测） | Ubuntu 26.04 |
|---|---|---|---|
| ROS 发行版 | `humble` | `jazzy` | 待核 |
| 速度指令 | `Twist` 常见 | 只收 `TwistStamped` | 待核 |
| Gazebo | Fortress / Garden 或 classic | `gz sim` 8.11 | 待核 |
| 桥接包 | `ros-humble-ros-gz` | `ros-jazzy-ros-gz-bridge` | 待核 |
| Python | 3.10 | 3.12 | 待核 |

26.04 列在命令手册里标为 C 级「待核」，首次使用请先执行 `ros2 --version` 与 `lsb_release -a` 核对，不要把未验证的命令写成已验证。

## 5. 课程资源门户

```bash
python3 portal/range_server.py 8140
# 浏览器打开 http://127.0.0.1:8140/
```

`range_server.py` 是标准库实现的静态服务器，支持 HTTP Range。默认 `python3 -m http.server` **不支持** Range，视频无法拖动进度条。门户包含 5 分钟演示片、明日课件三栏、ROS2/Ubuntu 命令搜索、学习网站与 Excel 手册下载。

## 6. 常见失败路径

| 现象 | 根因 | 处理 |
|---|---|---|
| 发了速度车不动 | 发了 `Twist` 或 CLI YAML 多套一层 `twist.twist` | 改成 `TwistStamped`，字段直接是 `linear/angular` |
| `/map` 发布者恒为 0 | `slam_toolbox` 停在 `unconfigured` | include 官方 `online_async_launch.py` |
| RViz 每 2 秒清空画面 | `/clock` 多发布者 | `ros2 topic info /clock` 必须 Publisher = 1 |
| RViz 只有 base_link | 缺 `robot_state_publisher` / `joint_state_publisher` | 补静态 TF 发布节点 |
| 松开指令车还在跑 | 没有看门狗 | 超时 0.6 s 发零速并清积分 |
| 构建脚本报 unbound variable | `set -u` 与 ROS setup 冲突 | 改 `set -eo pipefail` |
