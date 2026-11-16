# 第 12 周课件包 · 运动学、里程计与 PID 控制

**课程**：《机器学习与智能机器人应用技术》智能机器人线 · 第 12 周
**学校**：广州现代信息工程职业技术学院
**验证环境**：Ubuntu 24.04.4 LTS (aarch64) + ROS 2 Jazzy + Gazebo Harmonic 8.11.0
**验证主机**：DGX spark-a8d2（`<LAB_HOST>`）

---

## 一、这套东西解决什么

下周 90 分钟课堂要同时展示「车真的在动」「里程计在漂」「PID 在补」「地图长出来」四件事。
本包把它们做成**四个同时可见的窗口/页面**，全部挂在 Ubuntu 桌面上：

| # | 窗口 / 页面 | 看到什么 | 对应知识点 |
|---|---|---|---|
| 1 | Gazebo GUI | 差速车在 10×10 m 封闭场地运动，有围墙、色块、L 形内墙 | 物理仿真、传感器有东西可看 |
| 2 | RViz2 | 机器人模型、TF 树、LaserScan 点云、里程计轨迹箭头、SLAM 占用栅格 | TF / 坐标系 / 地图 |
| 3 | 网页看板 `http://127.0.0.1:8130/` | 四宫格：odom vs 真值轨迹、PID 曲线、激光极坐标、占用栅格地图 | 误差、闭环、建图 |
| 4 | Firefox（自动打开） | 上面那个看板，可用按钮直接开车 | 人机交互 |

网页看板**不依赖 rosbridge / flask / numpy**，只用 Python 标准库 `http.server`，
教室断网也能跑。数据链路是：`telemetry_node.py` 订阅 ROS 话题 → 写 `/tmp/w12_dashboard.json`
→ 浏览器每 500 ms 拉一次。

---

## 二、三步启动（Ubuntu 桌面终端）

```bash
cd ~/ros2_ws_w12
bash 00_一键构建.sh          # 约 1–2 分钟；只第一次需要
bash 01_启动课堂.sh          # 拉起 Gazebo + RViz2 + SLAM + 看板，约 20 s
bash src/week12_odometry/scripts/check_w12.sh   # 20 项自检，全绿再开讲
```

开讲后：

```bash
bash src/week12_odometry/scripts/drive_demo.sh a     # A 段直行 3 s
bash src/week12_odometry/scripts/drive_demo.sh b     # B 段原地左转 2 s
bash src/week12_odometry/scripts/drive_demo.sh c     # C 段画圈 6 s（给 SLAM 采集）
bash src/week12_odometry/scripts/drive_demo.sh all   # 三段连跑
bash 03_保存地图.sh                                  # 存 w12_map.pgm + .yaml
bash 02_停止全部.sh                                  # 下课清场
```

也可以在网页看板上直接按方向按钮开车，网页会写 `/tmp/w12_cmd.json`，
`velocity_arbiter.py` 读取后转发给控制器。

---

## 三、目录结构

```
ros2_ws_w12/
├── 00_一键构建.sh  / 01_启动课堂.sh  / 02_停止全部.sh  / 03_保存地图.sh
├── src/
│   ├── diffbot_description/          差速底盘（URDF/Xacro + 控制器 YAML）
│   │   ├── urdf/diffbot.common.xacro         几何 + 惯性 + ros2_control 接口
│   │   ├── urdf/diffbot_sensors.urdf.xacro   相机 / 2D 激光 / IMU
│   │   └── config/diffbot_controllers.yaml   轮径 0.05 / 轮距 0.36 / 协方差
│   └── week12_odometry/              W12 新增
│       ├── launch/demo_w12.launch.py          九段启动顺序（注释里写了全部坑）
│       ├── config/bridge_w12.yaml             /clock /scan /imu /真值
│       ├── config/slam_w12.yaml               slam_toolbox 参数
│       ├── worlds/arena_w12.sdf               10×10 m 场地 + L 形内墙
│       ├── rviz/demo_w12.rviz                 Grid/Model/TF/Scan/Map/Odom/Image
│       └── scripts/
│           ├── velocity_arbiter.py   ★ 看门狗 + PID + 指令仲裁
│           ├── telemetry_node.py     ★ ROS → JSON 遥测
│           ├── odom_relay.py         私有 odom → 标准 /odom
│           ├── odom_eval.py          里程计精度评估（A 直行 / B 转向）
│           ├── check_w12.sh          20 项自检
│           ├── drive_demo.sh         A/B/C 三段驾驶
│           ├── save_map.sh           地图存盘
│           └── stop_all.sh           清残留（/clock 单发布者）
├── dashboard/                       网页看板（原生 HTML/Canvas/JS）
└── logs/ maps/                      运行日志与地图产物
```

---

## 四、五个必须知道的坑（讲稿里会逐个演示）

1. **`/clock` 只能有一个发布者。** 反复启停仿真会残留 `ros_gz_bridge` 子进程，
   RViz 每 2 秒报 `Detected jump back in time` 并清屏。重开前跑 `02_停止全部.sh`。
   核验：`ros2 topic info /clock` 的 `Publisher count` 必须是 1。
2. **Jazzy 的 `diff_drive_controller` 只收 `TwistStamped`。** 发 `Twist` 不报错，
   消息静默丢弃，表现为「命令发了车不动」。核验：`ros2 topic list -t | grep cmd_vel`。
3. **`GZ_SIM_SYSTEM_PLUGIN_PATH` 要手动补。** `gz_ros2_control` 没装环境钩子，
   不补就加载不到插件，`/controller_manager` 永远不出现。launch 里已处理。
4. **速度环 PID 必须写成 `u = v_target + Kp·e + Ki·∫e + Kd·ė`。**
   少了前馈项 `v_target`，稳态误差趋零时输出也趋零，车反而停下。
5. **地图是两张文件。** `map_saver_cli` 产出 `.pgm`（像素栅格）和 `.yaml`
   （分辨率、origin、占用阈值），少一张 AMCL/Nav2 都读不了。

---

## 五、双版本说明

| 项 | Jazzy（实测） | Humble（学生 VMware 常见） |
|---|---|---|
| `cmd_vel` 类型 | `TwistStamped` | `Twist`（`use_stamped_vel:=false`） |
| Gazebo | Harmonic / `gz sim` | Fortress / `ign gazebo` 或 `gz sim` |
| slam_toolbox | `async_slam_toolbox_node` | 同名，参数基本一致 |
| 世界 SDF 版本 | 1.9 | 1.8~1.9 兼容 |

Humble 上若车不动，第一件事就是 `ros2 topic list -t | grep cmd_vel` 看类型；
把 `drive_demo.sh` 里的 `TYPE` 改成 `geometry_msgs/msg/Twist`、去掉 `header/twist.twist` 一层即可。

---

## 六、与第 10/11 周、第 13/14 周的衔接

- 底盘模型、控制器 YAML 直接复用 W10/W11（`diffbot_description`），保证同一台车。
- W12 产出的 `/odom` 与 `/imu/data_raw` 是 W13 `robot_localization` EKF 的输入。
- W12 现场建的 `w12_map.pgm/.yaml` 是 W14 AMCL 与 Nav2 的地图输入。
- W12 的「里程计漂移」正好引出 W13「为什么要融合」和 W14「为什么要用激光修正」。

---

## 七、生产机共存：独立 DDS 域与 Gazebo 分区

`env.sh` 统一导出 `ROS_DOMAIN_ID=42`、`GZ_PARTITION=w12course`。
在同时跑着别的 ROS 2 演示的机器（例如 DGX 上还有 W11 传感器演示、
三人小组的 RViz 与监控盘）上，这两个变量把 W12 隔在自己的通信域里：

- 不干扰别人的节点、话题、TF；
- 自己的 `/clock` 永远只有一个发布者；
- `02_停止全部.sh` 只按 W12 独有文件名（`arena_w12.sdf` / `demo_w12.rviz` /
  `demo_w12.launch.py` / 四个 py 节点名）精确清理，**绝不使用通用
  `gz sim` / `rviz2` / `parameter_bridge` 关键词 pkill**。

在老师独占的 Ubuntu / VMware 上这组值同样适用，无需改动。
所有课堂脚本（`check_w12.sh` / `drive_demo.sh` / `save_map.sh`）都会先
`source env.sh`，所以另开终端直接执行即可，不用手动 export。

---

## 八、PID 演示怎么开

```bash
MODE=pid bash 01_启动课堂.sh      # 自动把 load_factor 设成 0.65
bash src/week12_odometry/scripts/drive_demo.sh a
```

`passthrough` 模式开车是开环直通；`pid` 模式会给电机注入 0.65 的教学负载
（模拟爬坡 / 打滑），网页看板②号格会出现「目标 0.350 / 实测 0.32 /
输出 0.49–0.52」三条线分开又合拢的过程。这是**人为教学扰动**，真实机器人
恒为 1.0，讲完务必切回默认模式。

---

## 九、2026-11-13 实测记录（DGX spark-a8d2）

| 项 | 实测值 |
|---|---|
| 环境 | Ubuntu 24.04.4 LTS / aarch64 / ROS 2 Jazzy / Gazebo Harmonic 8.11.0 |
| 构建 | `colcon build` 2 包，0.50 s，EXIT=0 |
| 自检 | `check_w12.sh` **PASS=24 / FAIL=0 / SKIP=0** |
| `/clock` 发布者 | 1（正确） |
| 控制器 | `joint_state_broadcaster` + `diff_drive_controller` 均 active |
| `cmd_vel` 类型 | `geometry_msgs/msg/TwistStamped` |
| 话题频率 | odom 98.3–99.7 Hz / scan 9.8–10.0 Hz / map 1–2 Hz |
| A 段直行 | odom 2.4363 m vs 真值 2.4361 m，误差 **0.2 mm** |
| A+B+C 综合 | odom (0.8345, 0.969) vs 真值 (0.8436, 0.9671)，误差 **9.3 mm** |
| PID 闭环 | target 0.350 / measured 0.318–0.334 / out 0.487–0.516（load 0.65） |
| SLAM | `lifecycle=active [3]`，`/map` Publisher count=1，199×199 @ 0.05 m |
| 地图存盘 | `w12_map_20261113_235253.pgm` + `.yaml` |
| 网页看板 | `http://127.0.0.1:8130/` HTTP 200，四宫格全部有数据 |
| 桌面窗口 | Gazebo Sim / RViz2 / Firefox 看板 三个窗口均真实可见 |
| 生产隔离 | 同机 W11 演示与三人小组 4 个进程全程未受影响 |
