# MicroDuck 双足机器人短跑策略：奖励结构与命令覆盖的实证

这里归档的是 **2026-10 在 DGX Spark（GB10）上真实跑出来的训练与测速数据**，不是论文里的示意图，也不是他人结果的转述。

- 仿真栈：mjlab（MuJoCo Warp 后端）+ rsl_rl（PPO）
- 硬件：NVIDIA DGX Spark GB10，aarch64，121 GB 统一内存
- 环境数：4096 并行；v1 跑到 888 迭代、v2 跑到 250 迭代
- 对照口径：同一 checkpoint 序号（model_250）、同一测速命令、同一 32 环境并行协议

> 一句话结论：**改奖励配方能让同样 250 轮迭代的速度提升约 3.1 倍；但更硬的约束是速度命令上界——命令给多少，策略就只跑多少。**

---

## 1. 为什么值得记录

出厂配方（`Mjlab-Velocity-Flat-MicroDuck`）的速度命令范围只有 **±0.4 m/s**，这套策略在物理上不具备短跑能力。要让它跑快，必须同时改两件事：

1. **命令区间**：把 `lin_vel_x` 从 ±0.4 抬到 0.8–2.6 m/s；
2. **奖励权重**：让"跑得快"在回报里占主导，而不是让"踮脚腾空"占主导。

只做第 1 步会失败——这就是本文的 v1。

## 2. 两个版本的配方差异

| 奖励项 | v1 | v2 | 作用 |
|---|---|---|---|
| `track_linear_velocity` | 3.0 | **6.0** | 速度追踪，任务主目标 |
| `air_time` | 5.0 | **1.0** | v1 里它比速度奖励还值钱，直接诱发 reward hacking |
| `air_time.threshold_min` | 0.10 s | **0.22 s** | 抬高门槛，堵住"站着踮脚" |
| `air_time.threshold_max` | 0.35 s | 0.35 s | 上限不变 |
| `foot_slip` | −0.35 | −0.35 | 滑步＝假速度，保持重罚 |
| `action_rate_l2` | −0.05 | −0.05 | 不压爆发力 |
| 命令 `lin_vel_x` | 0.8–2.6 | **0.8–2.0 → 课程抬升** | v2 收窄上界，避免命令跳变 |
| 回合长度 | 12.0 s | 12.0 s | 与官方一致 |

## 3. 实测结果

### 3.1 同口径对照（model_250，命令 1.6 m/s，32 环境 × 1000 步，丢前 100 步暖机）

| 版本 | 平均前进速度 | 中位数 | P95 | 单帧峰值 | 单环境峰值 |
|---|---|---|---|---|---|
| v1（奖励失衡） | **0.1481 m/s** | 0.1539 | 0.2058 | 0.2507 | 0.8628 |
| v2（本文配方） | **0.4572 m/s** | 0.4560 | 0.6988 | 0.9335 | 1.8246 |
| 倍数 | **3.09×** | 2.96× | 3.39× | 3.72× | 2.11× |

数据：[`data/v1_speed_cmd16.json`](data/v1_speed_cmd16.json) · [`data/v2_speed.json`](data/v2_speed.json)

### 3.2 命令覆盖效应（同一 v2 检查点，只改测速命令）

| 测速命令 | 平均前进速度 | 单帧峰值 | 解释 |
|---|---|---|---|
| 1.6 m/s（课程内） | **0.4572 m/s** | 0.9335 | 策略按训练分布执行 |
| 2.6 m/s（超课程上界） | **0.1797 m/s** | 0.5457 | 命令跳到分布外，速度反而掉 61% |

数据：[`data/v2_speed_cmd26.json`](data/v2_speed_cmd26.json)

**这是本实验最有价值的发现**：可达到的速度上界由训练时的命令覆盖决定，不是由奖励权重决定。奖励只决定"愿不愿意跑快"，命令分布决定"会不会跑快"。

### 3.3 v1 的失败轨迹

v1 跑到 888 迭代时，回合奖励一路涨到 49.36，回合长度顶满 600 步（从不跌倒），但实测速度只有 **0.0905 m/s**，而且越训越慢（0.135 → 0.091）。

奖励分项：`air_time` 贡献 4.45，`track_linear_velocity` 只有 0.45。也就是说，**策略发现"站着把脚踮起来"能拿 90% 的分，而真的往前跑只值 10%**。典型的 reward hacking。

数据：[`data/v1_metrics.json`](data/v1_metrics.json)（888 迭代完整曲线）· [`data/v1_speed.json`](data/v1_speed.json)

## 4. 图表

| 文件 | 内容 |
|---|---|
| [`figs/fig2_v1_training.png`](figs/fig2_v1_training.png) | v1 训练曲线：奖励上升但速度下降 |
| [`figs/fig3_reward_imbalance.png`](figs/fig3_reward_imbalance.png) | v1 奖励分项占比（air_time 4.45 vs 速度 0.45） |
| [`figs/fig4_speed_compare.png`](figs/fig4_speed_compare.png) | 各配方实测速度对比 |
| [`figs/fig5_public_benchmark.png`](figs/fig5_public_benchmark.png) | 与公开成绩对照（**口径不同，仅作参照**） |
| [`figs/fig6_v1_v2_curves.png`](figs/fig6_v1_v2_curves.png) | v1 与 v2 训练曲线同图对照 |

## 5. 与公开成绩的关系：说清楚边界

社区公开过的 MicroDuck 短跑成绩包括 2.07 m/s（4090D、512 环境、13500 迭代）、1.88 m/s（Max Sumrall）、1.6 m/s（Hannes）。

**本实验没有达到这些数字，也不打算暗示达到了。**差别在三点：

| 维度 | 公开成绩 | 本实验 |
|---|---|---|
| 迭代数 | 13500 | 250（v2 当前检查点） |
| 并行环境 | 512 | 4096 |
| 硬件 | RTX 4090D | DGX Spark GB10（统一内存，非独显） |
| 测速口径 | 未公开逐帧统计方式 | 32 环境 × 1000 步，报均值/中位数/P95/单帧峰值/单环境峰值五个口径 |

本实验的可比之处在于**对照组内部**：v1 与 v2 除奖励配方外完全同条件，因此 3.09× 这个倍数是干净的。

## 6. 复现

DGX 侧（仓库不含模型权重与仿真资产）：

```bash
# 1. 训练
cd ~/duck-rl
.venv/bin/train Mjlab-SprintV2-Flat-MicroDuck \
    --env.scene.num-envs 4096 --agent.max-iterations 3000 \
    --agent.run-name duck_sprint_v2 --agent.logger tensorboard \
    --agent.save-interval 250 --video True --video-length 300 --video-interval 250

# 2. 导出训练曲线
.venv/bin/python export_sprint_metrics.py logs/rsl_rl/velocity/<run_dir> -o logs/v2_metrics.json

# 3. 独立进程测速（不依赖训练统计）
.venv/bin/python probe_sprint_speed.py \
    --ckpt logs/rsl_rl/velocity/<run_dir>/model_250.pt \
    --task Mjlab-SprintV2-Flat-MicroDuck --cmd 1.6 \
    --steps 1000 --num-envs 32 -o logs/v2_speed.json
```

本机侧（只依赖 matplotlib）：

```bash
python scripts/make_figs.py     # data/*.json → figs/*.png
python scripts/build_paper.py   # data + figs → 双栏 docx
```

> `scripts/` 里两个脚本是从本机 paper-agent 目录直接归档的，内含原始绝对路径常量。跑之前把 `DATA`/`FIGS` 指向本目录即可，逻辑不需改动。

## 7. 铁律

1. **回合奖励不是性能。** 唯一判据是独立进程测出的前进速度。
2. **没有实测数字就不写性能结论**，预期收益一律不写成结果。
3. **失败必须归类**（几何 / 物理 / 语义 / 策略—目标），不能一律叫"域偏移"。
4. **改动可追溯**：每版配方对应一个任务名、一份日志、一组检查点。

## 8. 待补

- [ ] v2 训练到 3000 迭代后按同协议重测，填满迭代轴
- [ ] 腾空时间（air_time）实测值与奖励值的偏差统计
- [ ] 对称性增强 / 域随机化消融（队列已排，未跑完）
- [ ] 从 mjlab 策略导出 ONNX 并在边缘设备上验证推理延迟
