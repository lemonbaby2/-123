# VLA / VLM 工程化双项目包（2026-08）

本目录是面向 Ubuntu + VSCode + 真实机器人/相机标定的工程化演示包，目标不是复制上游大模型源码，而是把“模型选型 → 标定 → 数据 → 推理 → 动作安全 → 可视化 → 面试讲解”串成可复现结构。

## 两个主工程

1. `01_smolvla_so101_engineering`：SmolVLA + Hugging Face LeRobot + SO-101。重点是动作模型、舵机标定、相机内参、手眼标定、动作 chunk 安全门控和 SVG 轨迹可视化。
2. `02_spatial_semantic_vla_engineering`：Qwen3-VL + Grounded-SAM2 + RGB-D/3D 几何 + SpatialVLA/StarVLA 动作适配接口。重点是开放词汇语义、深度反投影、外参/手眼标定、3D 目标表和语义到动作的安全桥接。

## 立即验证（不下载大模型、不接真机）

```bash
python3 vla_vlm_projects/run_tests.py
python3 vla_vlm_projects/run_all_demos.py
```

两个 demo 都只使用 Python 标准库，输出 JSON 和 SVG，便于 CI / 面试现场演示。真实模型依赖通过各自 `scripts/setup_upstreams.sh` 安装。

## Ubuntu 桌面一键准备

```bash
bash vla_vlm_projects/bootstrap_ubuntu_desktop.sh
```

默认目录：`~/Desktop/VLA_VLM_Engineering_2026`。脚本会克隆本作品集以及官方上游参考仓库；不会自动下载几十 GB 权重，也不会直接驱动机器人。

## 工程安全边界

- 默认全部为 `dry-run`，不会向机械臂发送真实关节命令。
- 真机前必须完成机械限位、急停、速度/加速度/力矩限制、相机/机器人标定和工作空间验证。
- 大模型输出永远不能直接作为电机控制量；必须经过坐标变换、动作归一化、控制器约束和安全状态机。
