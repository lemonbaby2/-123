# 简历内容 / Agent 成果 与 GitHub·Gitee 发布核对 · 2026-11-20

> 核对对象：`2026李梓鹏机器人简历(27)(1).pdf`（3 页）+ 本轮 agent 工作
> 平台：GitHub `lemonbaby2`（38 个公开仓库）· Gitee `li-zipeng123`（28 个公开仓库）
> 方法：逐页提取简历 → 拉取两平台仓库清单与文件树 → 读 README / 证据矩阵 → 本机算力实跑复测

## 结论

**❌ 没有全部发布，而且差距不小。**

16 个核对条目里，达到「真实代码 + 实测数据/图 + 指标可复现」的只有 **2 项**（Dy3DGS-SLAM、TAC-R2S2R 两篇论文的复现资产）；**9 项**只有 clean-room 演示 / dry-run / 脱敏代码；**3 项完全没发布**（世界模型、Hermes+全机 agent 接入、Metatron coding-agent 复现）。

更重要的是：**这不是我发现的漏洞，是你自己的仓库已经写明的边界**。`-123/docs/RESUME_EVIDENCE_MATRIX.md` 原文：

> 指标标签：`简历报告值`：来源于候选人简历，仓库未独立验证；`演示测试值`：由合成数据和本仓库代码产生，只验证实现逻辑。
> `RESUME_2026_PROJECT_INDEX.md`：世界模型一栏 —— **「暂无对应的原创公开工程」**。

也就是说，仓库的公开口径是诚实的，但**简历里的实机指标没有一个有公开的同口径复测数据**。

## 逐条核对（0=未发布 / 1=演示或 mock / 2=真实代码+实测数据）

| ID | 简历条目 | GitHub | Gitee | 真实图 | 指标可复现 | 缺什么 |
|---|---|---|---|---|---|---|
| R1 | LingBot-VLA 2.0 / 蚂蚁灵波 R2 / RoboTwin | 1 | 1 | 1 | 0 | R2 实机训练日志、50k+10k 权重、55 维适配层证据、LeRobot 数据集 |
| R2 | 斑马 Zebra / YOLO11-P2 + AIFI/CCFM | 1 | 0 | 0 | 0 | 喷头图像/标签、权重、TensorRT engine、42→18ms 延迟日志 |
| R3 | Cloud Ginger / CCU / OpenVLA | 1 | 0 | 0 | 0 | CCU API、AWQ 量化日志、LoadMap 轨迹、动作延迟 |
| R4 | GeoScan Pro / LIO-SAM + RTK | 2 | 2 | 1 | 0 | 双天线 RTK <0.2° 实测、USB-CDC 带宽测试、专利正文 |
| R5 | **世界模型 / 动作条件预测** | 0 | 0 | 0 | 0 | **整个工程都没有**：20+ 帧预测、MSE-32%、PSNR 28.5dB、避碰+25% |
| R6 | OpenVLA 语言驱动操作 | 1 | 0 | 0 | 0 | 1000+ 轨迹、92.5% 抓放日志、<60ms 端到端 |
| R7 | Qwen2.5-VL 工业 VQA / SOP | 2 | 2 | 1 | 0 | 98.2% 召回 / <3.5% 幻觉的同口径复测、产线视频与标签 |
| R8 | ROS2 + 3DGS Lego 可视化 | 2 | 1 | 2 | 1 | 原 Lego 资产、12s H.264、Isaac Sim 集成 |
| R9 | 四足 SLAM / CUDA / Vicon | 1 | 0 | 0 | 0 | CUDA kernel、Vicon 真值、100h 长稳日志、回环 -63% 测量 |
| R10 | STM32-FreeRTOS BMS | 1 | 0 | 0 | 0 | 电芯数据、Bi-LSTM 教师、QAT、MCU 固件、SOC<2% HIL |
| P1 | 论文 Dy3DGS-SLAM | 2 | 0 | 2 | 2 | 原稿与审稿状态（投稿政策） |
| P2 | 论文 TAC-R2S2R | 2 | 2 | 2 | 2 | 无（160 seed 验证运行 + CSV + 图已发布） |
| P3 | 4 项专利 / 竞赛获奖 | 1 | 0 | 0 | 0 | 申请号、权利要求、证书扫描件 |
| A1 | Agent：R1 离线自学习 | 2 | 0 | 1 | 1 | 20h 自强化原始日志 |
| **A2** | **Agent：Hermes 修复 + 全机本地模型接入** | **0** | **0** | **0** | **0** | `patch_approval_parse.py`、`setup_local_models.py`、`BENCH_20261115.md` 全在本机 |
| **A3** | **Agent：Metatron coding-agent 复现** | **0** | **0** | **0** | **0** | `metatron_trial.py`、4 份 `results_*.json`、`RESULT.md`、`DGX.md` 全在本机 |

**R2 特别说明**：GitHub 上的 `ai-fastener-inspection` 是**另一个项目**（YOLOv8n 螺丝螺母，59.2 FPS / mAP 0.926），不是简历里的 Zebra ZT421T 喷头/标签偏位项目。别拿它当 R2 的证据，面试一问就穿。

**R1 特别说明**：本地 `E:/研究生学习/研究生学习/黑客松/lingbot-vla-v2` 有 git 仓库但**没有推到任何远端**；公开的只是琶洲 A 赛道相关工程（`-123/projects/09_robotwin_hackathon`、`vla-pazhou`、`pazhou-a-track-showcase` / Gitee `pazhou-a-vla-bridge`）。

## 三条附带查实

1. **简历身份与已公开材料不一致**：简历写「本科 · 广东工业大学新能源电子器件 · 2024.07 毕业 / 年龄 23」，但 GitHub 已公开 `vlm-3dgs-nav-thesis-midterm-2026-11`（硕士中期检查、学号 2122515166）与两篇在投论文。仓库比简历多出整段研究生经历，面试时会被追问。
2. **线上 `-123` 自检没过**：最新 commit `f7b4ba9`（11-17）在本机实跑 `scripts/run_tests.py` → **61 tests，3 失败**，全部指向 `projects/10_ros2_course_lab/evidence/course_demo_5min.mp4`。README 声称「5 分钟实拍录屏」，文件没入库；`verify_layout.py` 也直接报断链。`run_all_demos.py` 退出码 0。
3. **本地简历仓库拷贝是旧的**：`E:/研究生学习/.../github_-123` 停在 `f551d9a`（10-12，8 个项目），线上已到 `f7b4ba9`（11 个项目 + microduck 实验 5 张图）。别用旧拷贝判断发布状态。

## 已启动算力补齐的真实性能图

本机 **RTX 4060 8GB + 本地 Ollama + MuJoCo**，全部数据现跑现测，无任何合成或推测值。

| 图 | 真实数据源 | 结论 |
|---|---|---|
| `fig1_coverage_matrix.png` | 38 GitHub + 28 Gitee 仓库文件树与 README 审计 | 发布覆盖矩阵，见上表 |
| `fig2_ollama_gpu.png` | `benchmarks.json`：Ollama `/api/chat` 每模型 3 次，首次为冷加载、后 2 次为稳态 | 稳态 2B **176.3** / 7B **95.2** / 9B **13.3 tok/s**；9B 明显带宽受限。8GB 显存装不下多模型，**每次切换冷加载 26.1–90.7s** |
| `fig3_metatron_convergence.png` | `metatron_trial/results_*.json` 四组真实迭代日志 | 带轨迹反馈：本地 7B 把分数 -0.704 → **+0.197**、跌倒率 1.0 → 0.0；云端 gpt-5.5 → +0.133 |
| `fig4_hurdle_grid.png` | `benchmarks.json`：48 组真实 MuJoCo 跨栏仿真 | 最高分 **2.879**，仅 3/48 组合越障（`stride=0.8, vx=0.5, lift≥0.5`），41/48 零跌倒 |
| `fig5_repo_selfcheck.png` | `repo_tests_full.log` 线上最新仓库实跑 | 61 tests / 58 PASS / 3 FAIL，断链 `course_demo_5min.mp4` |
| `fig6_agent_latency.png` | `BENCH_20261115.md` 真实单轮 `hermes -z` 耗时 | 云端短答 16.3s、本地 9B 45.4s；完整 agent 工具编排普遍失败 |

数值溯源见 `FIGURE_PROVENANCE.json`，原始数据在 `benchmarks.json` / `coverage.json` / `repo_tests_full.log` / `repo_demos_full.log`。

## ❌ 这些图不能补（铁律：不伪造）

以下简历指标在本机全盘检索（`<WORKSPACE>`、`E:/研究生学习`、工作区 `work/`）**没有任何原始日志 / CSV / 权重 / engine**，远端 DGX 又未授权（SSH publickey 拒绝、9 个端口全 000）。因此**不生成任何曲线或柱状图，也不把简历值画成"实测"**：

- Zebra：AP +12%、漏检 15%→9%、编码丢失 0.3%、Orin 42→18ms
- OpenVLA：92.5% 未见零件抓放、<60ms 端到端
- Qwen2.5-VL SOP：召回 98.2%、幻觉 <3.5%
- 世界模型：MSE -32%、PSNR 28.5dB、避碰 +25%
- 四足：回环 -63%、±3cm Vicon、100h 长稳
- BMS：SOC 误差 <2%
- LingBot-VLA：50k+10k steps、全局 batch 384、55 维适配

**要补只能走两条路**：① 回原设备导出 `results.csv` / TensorRT profile / Vicon bag / HIL log；② 在公开仓库的 clean-room 代码上重新评测，并明确标注「本机复测值（非简历历史值）」。`-123` 现有的「演示测试值 / 简历报告值 / 实机复现值」三层标签就是正确做法，继续沿用。

## 可封装清单（只封装真正做过的）

**A 类 · 数据齐，建议新建公开仓库 `resume-evidence-2026-11`**
- `AUDIT.md`、`coverage.json`、`FIGURE_PROVENANCE.json`、6 张 PNG
- `benchmarks.json`、`run_benchmarks.py`、`make_figures.py`（可复跑）
- `repo_tests_full.log` / `repo_demos_full.log`（线上仓库自检留痕）

**B 类 · 真做过但没发布，建议各建独立仓库或并入 A 类**
- `agent-runtime-2026-11`：`setup_local_models.py`、`BENCH_20261115.md`、Hermes 修复说明、`patch_approval_parse.py` 备份（**先脱敏**：配置里有网关 key 与内网地址）
- `metatron-coding-agent-repro`：`metatron_trial.py`、4 份 `results_*.json`、`RESULT.md`、`DGX.md`、`run_on_dgx.sh`

**C 类 · 已有公开仓库，只补图 / 修断链，不重写历史**
- `-123`：把 `fig1` / `fig5` 放进 `docs/figures/`；修 `course_demo_5min.mp4` 断链（上传真实录屏到 Release，或把 README 改成外部链接）——**不能用占位视频冒充**
- `rtk-lidar-fusion-demo`、`tac-r2s2r-verified-runs`、`nantai-sop-threehost`：补本机实测图

**D 类 · 不得作为「已完成项目」封装**
- R2 / R3 / R5 / R6 / R9 / R10 只有 mock / dry-run。仓库里必须继续保留「演示测试值」标签；R5 建议从简历删除或改写为「技术调研」。

## 推送前需要你确认（我没有动任何远端）

1. 推到哪个仓库 / 分支（建议 GitHub 新建 `resume-evidence-2026-11`，Gitee 做镜像）；是否要把 B 类拆成独立仓库。
2. `-123` 的录屏断链怎么修：上传真录屏，还是改 README 标注为外部资料。
3. 简历里 7 组无证据指标是保留「历史报告值」口径、改写为区间，还是删除。
4. B 类封装前要不要我先把 `config.yaml` / `.env` / 网关 key 全部脱敏（**建议做**）。

## 可复跑命令

```bash
cd <WORKDIR>/resume_repo_audit
<WORKDIR>/metatron_trial/.venv/Scripts/python.exe run_benchmarks.py
<WORKDIR>/metatron_trial/.venv/Scripts/python.exe make_figures.py
cd upstream_-123 && python scripts/run_tests.py
```
