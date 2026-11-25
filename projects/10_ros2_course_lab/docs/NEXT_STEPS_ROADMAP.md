# 学完 MuJoCo + ROS 2 + SLAM + Nav2 之后：机器人学习路线手册

> 版本：2026-11-25 · 适用：本仓库 `projects/10_ros2_course_lab` 第 7–8 章之后
> 资源真实性：本文所有外部仓库均于 2026-11-25 经 GitHub REST API 实测（star / fork / pushed_at / archived），见[第 6 节](#6-资源清单已核实)。

## 结论先行

**你已经闭环的是「移动机器人自主移动」的最小链路；下一个瓶颈不是再学一个仿真器，而是三件事：状态估计的深度、三维语义表示、学习策略。**

| 现状（已实测） | 缺口 | 下一站优先级 |
|---|---|---|
| MuJoCo 物理仿真 + 双引擎对照（L07） | 只会前向仿真，不会从数据反推状态 | **P0 状态估计**：EKF / 因子图 / VIO-LIO |
| ROS 2 Jazzy 通信、Launch、TF、QoS（L08） | 工程化与实时性没系统练 | **P1 系统工程**：ros2_control / DDS / CI |
| slam_toolbox 2D 建图、AMCL 定位 | 停在 2D 栅格，没有三维与语义 | **P0 3DGS / 语义建图**（直论文） |
| Nav2 全局+局部规划、A\*、代价地图调参 | 只会移动，不会操作；不会学习 | **P1 MoveIt2 与 VLA** |

如果只选一件事先做：**状态估计（Stage 1）**。SLAM 的放射状拖影、AMCL 抖动、里程计漂移，根因都在这里；它同时是 3DGS 位姿和 VLA 策略观测的地基。

---

## 0. 路线总览

```
已掌握 ──► [1] 状态估计 ──► [2] 3D 重建与语义 ──┐
  │            (P0)            (P0·论文主线)      │
  ├─► [3] ros2_control + MoveIt2 (P1·移动操作) ──┤
  ├─► [4] Isaac Lab + VLA       (P1·具身智能) ──┤
  └─► [5] 边缘部署 + 系统工程    (P1·落地)  ─────┴─► [6] 多机器人 / 科研输出
```

| 阶段 | 主题 | 优先级 | 为什么此时学 | 可交付证据 |
|---|---|---|---|---|
| 1 | 状态估计与多传感器融合 | **P0** | SLAM/AMCL 的所有"玄学问题"都在这层 | EKF 对比曲线、ATE/RPE 报告 |
| 2 | 3D 重建与语义建图 | **P0** | 直连你的学位论文与 `projects/05_ros2_3dgs` | 3DGS 场景 + 开放词汇查询演示 |
| 3 | ros2_control + MoveIt2 | P1 | 从"能走"补到"能操作" | 机械臂抓抓演示 + 控制器参数表 |
| 4 | Isaac Lab + VLA / 模仿学习 | P1 | 具身智能岗位主战场；DGX 已跑通 Isaac Lab | 139 环境清单 + PPO 训练曲线 |
| 5 | 边缘部署与系统工程 | P1 | 工业视觉岗刚需；RKNN/Hailo 已有产线 | INT8 误差界 + 帧率/功耗实测 |
| 6 | 多机器人协同与科研输出 | P2 | 从"会做"到"能讲、能写、能带学生" | 论文/比赛材料 + 20 周教案 |

---

## 1. Stage 1 · 状态估计与多传感器融合（P0，2–4 周）

**目标**：把"里程计 + 激光 + IMU"从各说各话变成一个有统计意义的状态估计器。

### 必学知识点

1. **概率基础**：高斯分布、协方差传播、贝叶斯滤波；马氏距离做异常门控。
2. **滤波器**：EKF / UKF / ESKF（误差状态）区别，什么时候该用因子图而不是滤波。
3. **因子图**：`gtsam::FactorGraph`、ISAM2 增量平滑、回环与先验因子。
4. **时间同步**：`/scan` 与 `/odom` 时间戳错配是 L08 实测 7.2° 转角的根因——必须先修时间再调算法。
5. **坐标约定**：REP-105、`base_footprint`、TF 树唯一父节点；TF 时间戳用传感器采集时刻。
6. **评估**：ATE / RPE（EVO 工具），没有真值时用闭环残差 + 地图一致性替代。

### 动手实验（复用本仓库工作空间）

```bash
# 1) 从 L08 场景录一段 bag，用作所有估计器的共同输入
ros2 bag record -o ~/est_bag /scan /odom /tf /tf_static /cmd_vel

# 2) 先复现"时间错配"这个 bug：把 TF 时间戳改回 /odom，看地图是否出现放射状扇形
#    对照代码：slam_nav/pkg/src/nav_car/scripts/odom_tf.py（已修好的版本）

# 3) 写一个纯 Python EKF 融合 /odom 与 /scan 的 2D 位姿，输出 CSV
#    验收：静止 60 s 位置漂移 < 0.05 m；旋转 360° 后航向误差 < 2°

# 4) 升级到 gtsam ISAM2，加入回环因子；用 slam_params_noloop.yaml 做关回环对照
```

### 验收标准

- 能说清 EKF 与 ISAM2 的适用边界，并给出本场景选型的量化理由。
- 有 ATE/RPE 数字，不是"看起来好多了"。
- 时间同步错误能主动复现并定位，不再靠调参碰运气。

### 资源

- [borglab/gtsam](https://github.com/borglab/gtsam) ★3,807 · 活跃（2026-11-25 push）
- [cartographer-project/cartographer_ros](https://github.com/cartographer-project/cartographer_ros) ★1,861 · **最后提交 2024-03，代码可读但别当活跃主线**
- 本仓库 `docs/MEASUREMENTS.md`（L08 误差口径）

---

## 2. Stage 2 · 3D 重建与语义建图（P0，4–6 周，论文主线）

**目标**：从 2D 占用栅格走到"带语义的三维可通行地图"，这是你学位论文《动态环境下 VLM 辅助三维高斯语义建图与机器人目标导航》的主战场。

### 必学知识点

1. **3DGS 原理**：稀疏点云初始化 → 高斯属性优化 → 可微光栅化；与 NeRF 的取舍。
2. **相机模型与外参**：针孔 + 畸变、imu 预积分、位姿初值质量决定重建成败。
3. **动态环境处理**：时序 mask、动态物体剔除、语义引导的静态/动态分割。
4. **VLM 辅助**：CLIP / GroundingDINO / SAM 做开放词汇标注，把"椅子""门"写进高斯属性。
5. **导航接口**：从 3DGS 里抽可通行区域 → 投影成 2D costmap → 接 Nav2（复用 L08）。
6. **评价指标**：PSNR / SSIM / LPIPS（渲染）+ mIoU（语义）+ 导航成功率（下游）。

### 动手实验

```bash
# DGX 侧（不要在 4GB 显存的本机跑）
# 1) 用 Isaac Sim / Gazebo 相机传感器录一段环视序列（L07 的相机桥接可直接改）
# 2) COLMAP 求位姿 → graphdeco 官方 3DGS 训练 → 得到 .ply
# 3) 在本仓库 projects/05_ros2_3dgs 的 ASCII PLY 解析器上加载你的场景
# 4) 加一层语义：用 VLM 输出 open-vocabulary mask，写进 PLY 的额外属性
# 5) 投影成 2D 占用图，喂给 L08 的 Nav2 —— 这就是论文实验闭环
```

### 验收标准

- 能生成可交互查看的 3DGS 场景，并报告 PSNR / 训练时长 / 显存峰值。
- 语义查询（"找门"）能返回空间位置，且误检有量化统计。
- 下游导航成功率有 baseline 与语义增强版的对照表。

### 资源

- [graphdeco-inria/gaussian-splatting](https://github.com/graphdeco-inria/gaussian-splatting) ★24,544 · 原始参考实现
- 本仓库 [projects/05_ros2_3dgs](../05_ros2_3dgs/README.md)、[projects/07_gausspatrol](../07_gausspatrol/README.md)、[projects/08_3dgs_scanner_soft_hardware](../08_3dgs_scanner_soft_hardware/README.md)
- 算力边界：3DGS 训练必须走 DGX；本机 RTX 3050 Ti 4 GB 只够看结果

---

## 3. Stage 3 · ros2_control + MoveIt2（P1，3–4 周）

**目标**：从"差速车能走"扩展到"机械臂能抓"，补齐移动操作（mobile manipulation）这条线。

### 必学知识点

1. `ros2_control` 三件套：`hardware_interface` / `controller_manager` / 控制器插件；`position_controllers` 与 `joint_trajectory_controller` 区别。
2. URDF/Xacro 的 `<transmission>`、`<gazebo>` 插件、惯量与碰撞——L07 的差速车可以直接扩成机械臂。
3. MoveIt2：`move_group`、SRDF、Planning Scene、OMPL  planners（RRTConnect vs TRRT）。
4. 抓取：IK 可达性、夹爪 `GripperCommand`、碰撞检测与容许接触。
5. 真机安全：限位、急停、软限位与 `ros2_control` 的 `state_interface` 反馈闭环。

### 动手实验

```bash
# 1) 在 L07 工作空间加一个 6 轴臂 URDF（mujoco_menagerie 的 franka/panda 可直接转）
# 2) ros2_control 配 joint_trajectory_controller，Gazebo 里用 ros2_gz 插件驱动
# 3) MoveIt2 Setup Assistant 生成 SRDF，跑 RRTConnect 规划一条避障轨迹
# 4) 验收指标：规划成功率 ≥ 95%（100 次随机目标），单次规划 < 200 ms
```

### 验收标准

- 能在 Gazebo 里完成"移动底盘到桌前 → 机械臂抓取 → 放回"的完整序列。
- 能解释 `ros2_control` 与直接发 `/cmd_vel` 的本质区别（闭环状态反馈 vs 开环速度）。

### 资源

- [ros-controls/ros2_control](https://github.com/ros-controls/ros2_control) ★1,070 · 活跃
- [moveit/moveit2](https://github.com/moveit/moveit2) ★2,134 · 活跃
- [google-deepmind/mujoco_menagerie](https://github.com/google-deepmind/mujoco_menagerie) ★4,409 · 模型库（2026-11-24 已核实）

---

## 4. Stage 4 · Isaac Lab + VLA / 模仿学习（P1，6–8 周）

**目标**：从"手写控制器"走到"让策略自己学"，这是具身智能岗位的主战场，也是你 DGX 已有资产最厚的方向。

### 必学知识点

1. **RL 基础**：PPO、奖励设计、域随机化；奖励权重决定行为（MicroDuck 实验里踮脚刷分）。
2. **Isaac Lab 3.0**：无 `--headless` 参数、任务名无 `-v0`、物理后端 `newton_mjwarp`；训练用 `train.py --rl_library rsl_rl`。
3. **模仿学习**：ACT / Diffusion Policy，遥操作数据采集与 `lerobot` 数据格式。
4. **VLA**：OpenVLA / pi0 的架构差异，VLM  backbone 与动作 tokenizer。
5. **命令覆盖**：策略只在训练命令分布内有效，超分布会掉 61% 速度（仓库实测）。

### 动手实验（DGX）

```bash
source ~/isaacsim-venv/bin/env.sh
cd ~/IsaacLab

# 1) 列出 139 个环境（已实测）
python scripts/reinforcement_learning/list_envs.py

# 2) 训练 Go2 平地，记录速度曲线
python scripts/reinforcement_learning/train.py \
  --task Go2-Flat --rl_library rsl_rl --video --video_length 200 --video_interval 1000

# 3) LeRobot 采集一小段遥操作数据 → 微调 ACT → 在本机只做评估可视化
```

### 验收标准

- 能给出 `0.19 s/iter`（64 env）量级的训练吞吐报告，并解释与论文数字的口径差异。
- 有"奖励权重错误 → 行为退化"的对照实验，而不是只报最好看的那次。

### 资源与算力红线

| 项目 | Star | 最近 push | 本机 4 GB 能跑吗 |
|---|---:|---|---|
| [huggingface/lerobot](https://github.com/huggingface/lerobot) | 29,082 | 2026-11-25 | ❌ 训练必须 DGX |
| [Physical-Intelligence/openpi](https://github.com/Physical-Intelligence/openpi) | 14,762 | 2026-08-24 | ❌ |
| [isaac-sim/IsaacLab](https://github.com/isaac-sim/IsaacLab) | 8,720 | 2026-11-25 | ❌ 官方最低 16 GB 显存 |
| [openvla/openvla](https://github.com/openvla/openvla) | 7,349 | 2025-03-23 | ❌ |

> 停训令仍有效：DGX 34 个生产容器只读，训练需老师明确解锁，不自动启动任何 harvest 任务。

---

## 5. Stage 5 · 边缘部署与系统工程（P1，3–4 周）

**目标**：把"仿真里能跑"变成"产线上能跑、能查、能交接"。

### 必学知识点

1. 模型压缩：INT8/FP16 量化、校准集选择、量化误差界（本仓库 `projects/04_industrial_vision` 已有指标框架）。
2. 边缘推理：RKNN（RK3588）、Hailo-8 HEF、TensorRT；帧率 / 延迟 / 功耗三元组。
3. ROS 2 工程化：`colcon` + `ament` 测试、CI（GitHub Actions）、Docker 多阶段构建。
4. DDS 调优：`ROS_DOMAIN_ID` 隔离、QoS 兼容性、大点云用 BEST_EFFORT。
5. 可观测性：日志分级、`rosbag` 回放回归、版本号与 commit 绑定。

### 动手实验

```bash
# 1) 把 L08 的 A* 路径规划核心抽成纯 Python 模块，写 pytest（本仓库 src/course_algorithms.py 是范例）
# 2) 给工作空间加 GitHub Actions：colcon build + colcon test 必须全绿
# 3) 选一张检测模型做 INT8 量化，报告 mAP50 掉点与推理加速比
# 4) 在 RK3588 工控机部署，测 P50/P99 延迟与温度
```

### 验收标准

- 每次提交都有 CI 回显，不是"我本地跑过"。
- 量化掉点有数字和容忍阈值，不是"看着差不多"。

---

## 6. Stage 6 · 多机器人协同与科研输出（P2，持续）

1. 分布式 SLAM / 地图融合、任务分配（ auction / market-based）。
2. 论文写作：把 Stage 1–2 的对照实验整理成方法 + 消融 + 真实场景。
3. 教学转化：每个实验拆成 90 分钟课堂包（讲稿 + 代码 + 截图 + 自检脚本），直接补进 20 周教案。
4. 岗位材料：算法岗看 ATE/RPE 与部署数字；教师岗看课堂闭环与学生可复现性。

---

## 7. 90 天排期建议

| 周 | 主线任务 | 交付物 |
|---|---|---|
| 1–2 | 状态估计理论 + EKF 复现 | 融合曲线 + 时间错配复现报告 |
| 3–4 | GTSAM / ISAM2 + 回环对照 | ATE/RPE 表 + 因子图代码 |
| 5–6 | 3DGS 原理 + 官方实现跑通 | 可交互场景 + PSNR 报告 |
| 7–8 | 语义标注 + VLM 开放词汇 | 语义 PLY + 查询演示 |
| 9–10 | 3D→2D 投影接 Nav2 | 语义导航成功率对照 |
| 11–12 | ros2_control + MoveIt2 | 抓取演示 + 规划成功率 |
| 13–14 | Isaac Lab RL 基础 | 训练曲线 + 奖励消融 |
| 15–16 | LeRobot / ACT 模仿学习 | 采集-训练-评估闭环 |
| 17–18 | 量化 + 边缘部署 | INT8 误差界 + 帧率功耗表 |
| 19–20 | 论文/教案/简历证据整理 | 投稿稿 + 2 个课堂包 |

---

## 8. 算力路由（必须遵守）

| 任务 | 放哪 | 理由 |
|---|---|---|
| 编译、单测、纯 Python 算法、文档 | 本机 | 不占 DGX，< 30 s |
| 3DGS 训练、Isaac Lab、VLA 微调、视频转码 | **DGX spark-a8d2** | 本机 4 GB 显存是硬瓶颈 |
| 产线推理 | RK3588 / Hailo 工控机 | 靠近相机、低延迟 |
| 任何 > 30 s 或 > 2 GB 内存的命令 | **DGX** | 本机 Chrome 常驻 7 GB，commit 已顶过 99% |

本机记忆红线：pagefile 需老师双击扩容脚本后重启；不要在本机跑训练。

---

## 9. 八条铁律（踩过的坑，别再踩）

1. **时间先于算法**：TF 用传感器采集时刻；时间戳错配先修，再谈滤波。
2. **没有指标就没有进步**：每条路线都要 ATE/RPE/mAP/成功率之一，不能只截图。
3. **分清证据等级**：仓库实测 / 历史报告值 / 推导值必须标注，不混写。
4. **生产机只读**：DGX 34 个容器不动；清场按项目独有文件名精确匹配。
5. **DDS 双隔离**：`ROS_DOMAIN_ID` + `GZ_PARTITION` 同时设，否则别的课抢 `/map`。
6. **别在本机跑训练**：4 GB 显存 + 16 GB 内存的结论已经给过，不要重测。
7. **上游活跃度要看**：Cartographer / ORB-SLAM3 已长期无提交，读代码可以，选型要谨慎。
8. **先核实再推荐**：任何外部资源，先查 API star / pushed_at / archived，再写进手册。

---

## 10. 资源清单（已核实）

核实方式：`GET https://api.github.com/repos/{owner}/{repo}`，记录 `stargazers_count` / `forks_count` / `pushed_at` / `archived`。核实时间 **2026-11-25**。

| 仓库 | Star | Fork | 最后 push | 归档 | 用途 |
|---|---:|---:|---|---|---|
| [huggingface/lerobot](https://github.com/huggingface/lerobot) | 29,082 | 6,134 | 2026-11-25 | 否 | 模仿学习 / 数据采集 |
| [graphdeco-inria/gaussian-splatting](https://github.com/graphdeco-inria/gaussian-splatting) | 24,544 | 3,510 | 2025-10-17 | 否 | 3DGS 原始实现 |
| [Physical-Intelligence/openpi](https://github.com/Physical-Intelligence/openpi) | 14,762 | 2,670 | 2026-08-24 | 否 | pi0 VLA |
| [UZ-SLAMLab/ORB_SLAM3](https://github.com/UZ-SLAMLab/ORB_SLAM3) | 9,274 | 3,214 | 2024-07-24 | 否 | 视觉/VIO SLAM（GPL-3.0） |
| [isaac-sim/IsaacLab](https://github.com/isaac-sim/IsaacLab) | 8,720 | 4,025 | 2026-11-25 | 否 | RL 训练 |
| [openvla/openvla](https://github.com/openvla/openvla) | 7,349 | 877 | 2025-03-23 | 否 | OpenVLA |
| [ros-navigation/navigation2](https://github.com/ros-navigation/navigation2) | 5,113 | 2,040 | 2026-11-25 | 否 | Nav2（已学，进阶调参） |
| [borglab/gtsam](https://github.com/borglab/gtsam) | 3,807 | 1,019 | 2026-11-25 | 否 | 因子图 |
| [moveit/moveit2](https://github.com/moveit/moveit2) | 2,134 | 843 | 2026-11-24 | 否 | 机械臂规划 |
| [cartographer-project/cartographer_ros](https://github.com/cartographer-project/cartographer_ros) | 1,861 | 1,288 | 2024-03-10 | 否 | 2D/3D 建图参考 |
| [ros-controls/ros2_control](https://github.com/ros-controls/ros2_control) | 1,070 | 510 | 2026-11-25 | 否 | 控制器框架 |

> Star 数会随时间变化，本表是 2026-11-25 快照；活跃度判断以 `pushed_at` 为准，不以 star 为准。

---

## 11. 真实性边界

- **已实测**：L07/L08 的 ROS 2 Jazzy + Gazebo 8.11 链路、DGX Isaac Lab 139 环境、3.09× MicroDuck 内部对照、本手册 11 个仓库的 API 数据。
- **推荐但未在本仓库验证**：Stage 2–5 的实验步骤是按上游文档与已有代码推导的学习路径，不是本仓库跑出的结果。
- **未验证**：Ubuntu 26.04 样本、真实机器人抓取、VLA 真机部署。

更新记录：2026-11-25 初版，11 个仓库 API 核实完成。
