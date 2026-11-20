# 16 条简历项目的本机可跑性账本 · 2026-11-21

判定依据：`round2_full_run.py` Stage 0 环境探测 + Stage 5 逐条核对。
本机 = RTX 4060 8GB / Python 3.13（无 torch）/ Ollama 本地 9 模型 / MuJoCo 4.0.1；
远端 DGX 全端口不可达。

| ID | 简历条目 | 状态 | 判定依据 |
|---|---|---|---|
| R1 | LingBot-VLA 2.0 / R2 / RoboTwin | ❌ 本机不可跑 | needs DGX multi-GPU 50k+10k-step training, 50k/10k checkpoints, LeRobot dataset |
| R2 | Zebra / YOLO11-P2 + AIFI/CCFM | ❌ 本机不可跑 | needs ZT421T nozzle images/labels, trained weights, TensorRT engine |
| R3 | Cloud Ginger / CCU / OpenVLA | ❌ 本机不可跑 | needs vendor CCU API, Jetson Orin NX, AWQ quantisation log |
| R4 | GeoScan Pro / LIO-SAM + RTK | 🟡 部分可跑 | CRC / factor-graph unit tests run locally; real dual-antenna RTK needs hardware |
| R5 | World model / action-conditioned pred | ❌ 本机不可跑 | no original engineering project exists; 20+ frame / PSNR metrics have no source |
| R6 | OpenVLA language-driven manipulation | ❌ 本机不可跑 | needs 1000+ teleop trajectories and real-arm logs |
| R7 | Qwen2.5-VL industrial VQA / SOP | 🟡 部分可跑 | local Ollama VL inference benchmark runnable; 98.2% recall needs production video+labels |
| R8 | ROS2 + 3DGS Lego visualization | 🟡 部分可跑 | PLY/MarkerArray unit tests run locally; original Lego assets and Isaac Sim absent |
| R9 | Quadruped SLAM / CUDA / Vicon | 🟡 部分可跑 | voxel/ICP unit tests + C++17 build locally; Vicon ground truth and 100h log absent |
| R10 | STM32-FreeRTOS BMS | 🟡 部分可跑 | Thevenin/AEKF unit tests locally; MCU firmware and HIL rig absent |
| P1 | Paper: Dy3DGS-SLAM | 🟡 部分可跑 | repro assets published upstream; full 3DGS training needs DGX |
| P2 | Paper: TAC-R2S2R | ✅ 线上已验证 | 160 seeded runs + CSV + figures already public |
| P3 | Patents (4) / awards | ❌ 本机不可跑 | documents only; no application numbers / scans |
| A1 | Agent: R1 offline self-learning | ✅ 本机可跑全 | pure stdlib; 4/4 offline self-check PASS in repo tests |
| A2 | Agent: Hermes fix + all-agent setup | ✅ 本机可跑全 | setup_local_models.py --verify runs locally; config contains secrets -> must sanitise |
| A3 | Agent: Metatron coding-agent repro | ✅ 本机可跑全 | fully executed this run: Ollama 7B + MuJoCo 48-grid + 5-round loop |

## 统计

- **NOT_RUNNABLE**：6 条
- **PARTIAL**：6 条
- **RUNNABLE**：3 条
- **VERIFIED_UPSTREAM**：1 条

## 状态定义

| 状态 | 含义 |
|---|---|
| 本机可跑全 (RUNNABLE) | 代码与依赖都在本机，本轮已真实执行并留下日志 |
| 线上已验证 (VERIFIED_UPSTREAM) | 完整验证资产已在公开仓库，不需要本机重跑 |
| 部分可跑 (PARTIAL) | clean-room 单测 / 本地推理可跑，但实机指标所需数据、硬件或权重缺失 |
| 本机不可跑 (NOT_RUNNABLE) | 需要多卡 DGX、原始数据集、专有权重或根本不存在对应工程 |

❌ 不等于「项目没做过」，只等于「这台 8GB 机器跑不了、且仓库没有可公开的原始数据」。
任何情况下都不得把 PARTIAL / NOT_RUNNABLE 的演示输出改称实机复现。
