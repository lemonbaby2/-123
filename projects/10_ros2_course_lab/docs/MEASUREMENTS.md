# 实测记录与口径

所有数字来自 2026-11-13 / 2026-11-16 在 NVIDIA GB10 (aarch64) 工作站上的课堂环境复现，环境为 Ubuntu 24.04 LTS + ROS 2 Jazzy + Gazebo Sim 8.11.0。原始终端回显见 [evidence/selfcheck_w12.txt](../evidence/selfcheck_w12.txt)。

## 1. 节点与话题

| 检查项 | 结果 |
|---|---|
| 工作空间构建 | 2 个包，1.71 s，无错误 |
| 自检 | PASS = 24 / FAIL = 0 |
| `/odom` | 98.3–99.7 Hz |
| `/scan` | 9.8 Hz |
| `/map` | 1–2 Hz |
| `/clock` | Publisher count = 1 |
| `slam_toolbox` 生命周期 | `active [3]` |
| 建图尺寸 | 199×199，分辨率 0.05 m/格 |
| 地图保存 | pgm + yaml 均已落盘 |

## 2. 里程计精度

评估脚本 `odom_eval.py` 以 Gazebo 动态模型真值（`/world/arena_w12/dynamic_pose/info`）为参照，唯一动态模型即差速车。

| 阶段 | odom | 真值 | 相对误差 |
|---|---|---|---|
| A 段直行 | 2.4363 m | 2.4361 m | **+0.0082 %**（0.2 mm） |
| A+B+C 综合终点 | — | — | 9.3 mm |

相对误差定义：`(odom − truth) / |truth| × 100 %`。正号代表里程计走多了，优先调小 `wheel_radius`；转向角度偏差大则优先调小 `wheel_separation`。

**口径限制**：这是 Gazebo 内的仿真真值，不是真实地面车辆的标定结果。真值话题桥接后 `child_frame_id` 与时间戳为空，脚本依赖「唯一动态模型」这一前提；若世界里加入其他动态物体，真值会取错。

## 3. 速度 PID

`load_factor=0.65` 是人为注入的教学扰动，用来模拟爬坡/打滑造成的速度损失。控制律为前馈 + 修正：

```
u = clamp(target + Kp·e + Ki·∫e + Kd·ė, ±0.8)
e = target − measured
积分项限幅 ±1.0；停车时清积分；看门狗 0.6 s
```

| 观测 | 数值 |
|---|---|
| 目标线速度 | 0.350 m/s |
| 实测线速度 | 0.318–0.334 m/s |
| 控制器输出 | 0.487–0.516 |
| 松手后输出 | −0.275（主动制动） |

`tests/test_course_algorithms.py` 用一阶惯性电机模型重放同一控制律：目标 0.35、负载 0.65 时收敛到 0.339 m/s，输出约 0.52，与课堂观测同一量级。测试不是实机数据的替代品。

## 4. 可视化学证据

- [Gazebo 世界与差速车](../evidence/gazebo_world.png)：10×10 m 场地、围墙、L 形内墙、车体与传感器。
- [RViz 里程计与 SLAM](../evidence/rviz_odom_slam.png)：模型、TF、激光点云、odom 轨迹、占用栅格。
- [网页看板](../evidence/web_dashboard.png)：四宫格（轨迹 / PID 曲线 / 激光极坐标 / SLAM 地图）与状态栏。
- [5 分钟连续录屏](../evidence/course_demo_5min.mp4)：300.0 s / 1920×1080 / H.264 / 7.2 MB，按 Gazebo 80 s → RViz 75 s → 看板 85 s → Gazebo 收尾切窗，期间循环跑 A/B/C 三段。

录屏使用真实 X11 桌面（`DISPLAY=:1`）。Xvfb 上的 Gazebo GUI 会崩（libgallium / dri2，ARM GB10），不能用来录制。

## 5. 不能从本仓库推断的内容

- 真实机器人、真实激光雷达或真实场地的定位精度；
- 长稳运行、温度/功耗、急停与失效注入结果；
- Ubuntu 22.04 / 26.04 的实机回显；
- 任何生产环境的安全结论。

这些属于「设计目标」或「历史报告值」，本仓库不把它们包装成当前实测。
