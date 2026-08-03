# GaussPatrol 评测协议

## 1. 结果分级

- `repository-sim`：由公开代码和固定场景生成，可直接重跑；
- `stress-proxy`：人为增加噪声/退化的 shifted 场景，不是真实域；
- `robot-measured`：未来由 S10、现场数据和真值系统生成，当前为空。

任何图表必须标注所属级别。禁止把 `stress-proxy` 写成 Sim-to-Real 真机变化。

## 2. 复现命令

```bash
python projects/07_gausspatrol/tests/test_gausspatrol.py -v
python projects/07_gausspatrol/run_demo.py \
  --output projects/07_gausspatrol/artifacts/local_run
```

固定输入是 `config/default_scenario.json`。关键随机决策使用显式 seed。wall runtime 和函数 latency 与机器负载相关，不要求字节一致；路线、TP/FN/FP、ATE/RPE、完成率、碰撞、Gaussian 数和覆盖率应一致。

## 3. 指标定义

### 路线完成率

`reached checkpoints / planned checkpoints`。起点不计为待完成点，返航点计入。

### ATE/RPE

ATE 为逐步二维位置误差平方均值开根号。RPE 为相邻步真值位移与估计位移差的 RMSE。真机版必须说明 SE(3) 对齐方法、采样时间间隔和真值来源。

### 避障成功率

动态障碍进入安全包络触发一次 attempt；若基于当前动态占据找到新路径则记 success。零触发时返回 100% 只表示没有失败，不应作为强避障证据，因此报告同时显示 attempt 数。

### 延迟

`planning_latency_ms` 与 `perception_latency_ms` 使用 Python `perf_counter_ns` 测量函数 wall time，报告 mean/P95/max/sample count。合成 detector 延迟不代表 YOLO；真机必须测相机接收至决策发布的端到端延迟。

### 地图完整度

当前定义为被 raycast hit 覆盖的静态障碍边界栅格/全部参考边界栅格。它不是 3DGS PSNR/SSIM/LPIPS。真 3DGS 应另外评测 held-out view 的 PSNR/SSIM/LPIPS 和缺陷区域可见性。

### 缺陷 AP50

按 confidence 排序，IoU≥0.5 且同一设备首次匹配算 TP，使用 11-point interpolated AP。真实比赛需按官方指标或 COCO API 重新评估并保留类别、样本数和置信区间。

### 模型任务时间

等于移动距离/地形限速 + 动态障碍等待时间。它用于比较策略，不包含真实执行器、网络、控制周期或图像采集时延。

## 4. 真机实验矩阵

| 维度 | 最低水平 |
|---|---|
| 地形 | 平地、坡道、碎石/台阶、低摩擦 |
| 动态体 | 无、单人横穿、多人/车混合 |
| 光照 | 日间、背光、低照、补光 |
| 定位 | 正常、弱几何、快速转向、传感器短时断开 |
| 网络 | 正常、延迟、丢包、完全断开 |
| 电量/温度 | 满电、中电、低电、热稳态 |

每格至少多次独立回合，完整保留成功和失败。安全违规不因任务完成而忽略。

## 5. Sim-to-Real

同一任务、起点、控制限幅和指标脚本分别运行 Isaac Lab 与真机。报告绝对值和变化：完成率百分点、速度下降、路线时间增加、跌倒/滑移、能耗、ATE 和避障。若仿真 asset、摩擦或传感器模型未校准，不应将 gap 归因于策略本身。
