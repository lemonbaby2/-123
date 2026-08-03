# GaussPatrol 可复现运行报告

> 自动生成。所有数值来自当前仓库确定性二维仿真。`shifted` 是人为增加里程计噪声、速度下降和检测退化的压力场景，不是真机 Sim-to-Real 实测。

![指标对比](dashboard.svg)

## 结果摘要

| 指标 | Nominal | Shifted | 口径 |
|---|---:|---:|---|
| 路线完成率 | 100.0% | 100.0% | 到达检查点/计划检查点 |
| ATE RMSE | 0.0187 m | 0.1125 m | 2D 估计轨迹对真值 |
| RPE RMSE | 0.0073 m | 0.0267 m | 相邻步位移误差 |
| 动态避障成功率 | 100.0% | 100.0% | 成功重规划/触发次数 |
| 规划 P95 | 15.759 ms | 11.106 ms | 本机 Python `perf_counter` |
| 感知 P95 | 0.050 ms | 0.056 ms | 合成检测器函数耗时，不是 YOLO |
| 地图完整度 | 89.5% | 89.5% | 被观测静态障碍边界栅格占比 |
| 缺陷 AP50 (11-point) | 1.000 | 0.636 | 合成设备缺陷检测 |
| 碰撞 | 0 | 0 | 几何碰撞检查 |
| 模型任务时间 | 74.35 s | 90.45 s | 距离/地形速度+等待 |

## 可视化

- [Nominal 轨迹](nominal_trajectory.svg)
- [Shifted 轨迹](shifted_trajectory.svg)
- [Nominal Gaussian PLY](nominal_gaussians.ply)
- [Shifted Gaussian PLY](shifted_gaussians.ply)
- [完整机器可读指标](metrics.json)
- [事件日志](events.jsonl)

## 不能从本报告推出的结论

- 没有运行 LIO-SAM、FAST-LIVO2、YOLO、Isaac Lab 或真实 3DGS 训练；
- 没有连接山猫 S10、LiDAR、IMU、RGB-D 或 `ros2_control`；
- 没有真实雨天、碎石、楼梯、动态人员或设备缺陷数据；
- 因此这些结果只能证明仓库闭环和评测代码可运行，不能作为比赛真机成绩。
