# 09 · 具身智能仿真与真机数据链路（Hackathon Track）

> 归属：**李梓鹏** ｜ 时间跨度：2026-10 ｜ 定位：RoboTwin 2.0 / LingBot-VLA 方向的算力验证、仿真复现与真机数据采集
> 本目录只收**自研代码与文档**。第三方上游仓库、模型权重、数据集、真机凭据一律不入库（见 §5）。

---

## 1. 这个目录解决什么问题

面向"VLA 模型 → 仿真评测 → 真机数据"这条链，把三件在工程上最容易卡住的事做通并留痕：

| 卡点 | 本目录对应的交付 |
|---|---|
| Isaac Sim 版本漂移，上游代码在新版本直接段错误 | `isaac-sim-arm/`：ISAAC 4.5 适配 + 自定义 experience 规避 `osqp` 段错误 |
| 双卡（4060 + 5060 Ti）算力边界不清楚，不知道该跑什么、能跑多大 | `bench/`、`isaac-5060ti/`：架构 / 显存 / 算力 / 训练吞吐实测 |
| 真机采集链路（双相机 + 机械臂 + 关节状态）时间对齐难、易丢帧 | `lingbot-real-pipeline/`：采集成套流水线 + 相机链路诊断方法 |

---

## 2. 子模块

### 2.1 `isaac-sim-arm/` — Isaac Sim 4.5 × Franka RGB-D 分拣

复现目标：**Kishan-Gadhavi01/IsaacSim_Robotics_Portfolio @ 48540c0**（上游）。

**上游代码写于 Isaac Sim 4.2/4.3（`omni.isaac.*` 旧命名空间），在本机 4.5 上原样运行直接 `EXIT=139` 段错误。** 本目录记录把它跑通、跑对，并额外完成 Isaac Lab 机械臂强化学习（PPO / Franka 抓取）的全过程。

| 文件 | 作用 |
|---|---|
| `run_rgb_cube_sorter_45.py` | 主复现脚本，自包含，含 4.5 适配 + 双路录像 + 渲染校验 |
| `serve.py` / `launch.py` | 静态服务后端（Range 206/416、MIME 映射、`/api/info`、`/api/highlights`、`/api/curves`） |
| `web/` | 零依赖前端，原生 canvas 图表 + 照片灯箱 |
| `map_highlights.py` / `scripts/*.sh` | 媒体生产流水线与成片加工 |
| `check_site.py` | 资源存在性 + 标签配平 + 占位符残留校验 |
| `README_原版.md` | 当时的完整交付清单与踩坑记录（保留原文） |

> 上游仓库本体未入库，请自行 `git clone` 后按 `README_原版.md` 的适配说明操作。

### 2.2 `lingbot-real-pipeline/` — 真机数据采集流水线

单臂真机（RealMan GEN65-BI）+ 双目深度相机，经 SSH 远程驱动的批量 episode 采集。

| 文件 | 作用 |
|---|---|
| `run_remote_collect.py` | Windows 侧批量采集驱动器：SSH 下发任务、限时、限条数、断点续采 |
| `toolchain/arm.py` | RealMan JSON 协议封装（`set_arm_stop` / `get_current_arm_state`，joint 单位 0.001°） |
| `toolchain/cams.py` / `cams_v2.py` | 相机枚举与取流，含链路质量判定 |
| `toolchain/record.py` / `record_v2.py` | 录制主循环：RGB + Depth + 关节状态 + 动作时间对齐 |
| `toolchain/collect.py` / `collect_batch.py` / `build_dataset.py` | 采集调度与数据集落盘（LeRobot 兼容结构） |
| `toolchain/rssh.py` | SSH/SFTP 助手，直连 SOCKS5 代理，不依赖 Proxifier |
| `toolchain/realman_bridge.py` + `.json`/`.yaml` | ROS ↔ 裸 JSON 协议桥接与关节限位配置 |
| `toolchain/lingbot_smoke_test.py` / `mock_policy_server.py` | 策略服务连通性冒烟测试与 mock |
| `部署手册.md` / `相机链路诊断_2026-10-25.md` | 部署总纲、相机 USB 链路中断的分层定位方法 |

### 2.3 `vla-slam-stack/` — 双卡 VLA 训练 + Go2 激光建图

| 文件 | 作用 |
|---|---|
| `code/vla_run_train.sh` | GPU1：SmolVLA + LoRA（rank 16），基座 `lerobot/smolvla_base` |
| `code/vla_run_train_act.sh` | GPU0：ACT 从零训练 |
| `code/vla_train_lora.py` | peft 与 lerobot `PreTrainedConfig`（draccus dataclass）不兼容的入口补丁 |
| `code/vla_eval*.sh` / `vla_eval_patched.py` | 策略评测与录像（ACT / LoRA 两条路） |
| `code/go2_simulate.py` / `go2_infer_semantics.py` | Go2 仿真与语义推理 |
| `code/README.md` | **踩坑全集**：`load_vlm_weights` 必须显式给、`use_peft` 分支不可用、`HF_HUB_DISABLE_XET=1` 必需、transformers/hub 版本冲突 |

### 2.4 `isaac-5060ti/` — RTX 5060 Ti 上的 Isaac Sim / Isaac Lab 落地

`sm_120` 新架构在 Isaac Sim 4.5 上的实际可行性验证：驱动/容器依赖下载（`dl_nv.sh`）、torch 安装与校验（`install_torch.sh` / `verify_torch.py`）、numpy 与 ROS 冲突修复（`fix_numpy_ros.sh`）、场景抓帧（`isaac_scene_capture_45.py`）、Go2 训练曲线导出。

### 2.5 `bench/` — 双卡硬件体检与容量边界

| 文件 | 内容 |
|---|---|
| `gpu_bench/gpu_bench.py` + `result*.json` | 单卡算力、显存、满载功耗、压力测试 |
| `gpu_bench/ddp_bench.py` | 双卡 DDP 吞吐 |
| `gpu_bench/model_capacity.py` | 模型容量估算（BF16 / FP8 / 4-bit） |
| `gpu_bench/sm_arch_check.cu` | SM 架构探测（`sm_89` vs `sm_120`） |
| `gpu_bench/cupy_bench.py` | CuPy 与 torch 的算子级对比 |
| `gpu_bench/*.md` | 《GPU 双卡体检报告》《GPU 架构 / 模型容量 / CUDA 升级》 |
| `cpu_bench/` | CPU 负载与健康报告 |

---

## 3. 关键结论（可直接引用）

- Isaac Sim 4.5 加载默认 `isaacsim.exp.full.kit` 时，`isaacsim.robot.wheeled_robots` 的 `osqp._osqp.cp310-win_amd64.pyd` 会让进程在任何 `print` 之前就 `EXIT=139`。必须用自定义 experience 避开。
- `isaaclab.python.headless.rendering` 默认 `physics.updateToUsd=false` / `fabricUpdateTransformations=false`，此时**录像是静止图且不报任何错**；做可视化必须显式打开。
- SmolVLA + LoRA 训练时 `--policy.load_vlm_weights=true` 漏给 = VLM 主干随机初始化，LoRA 训练完全无意义；`--policy.use_peft=true` 分支要求 `pretrained_path` 指向适配器目录，会报 `Can't find 'adapter_config.json'`，正确做法是 `use_peft=false` + 顶层 `--peft.method_type=LORA`。
- `HF_HUB_DISABLE_XET=1` 必需：HF 镜像不代理 `cas-bridge.xethub.hf.co`，不禁用 Xet 会在下载权重时 DNS 失败并无限重试。

---

## 4. 复现方式

所有脚本的**网络地址与凭据已替换为占位符**（`<ROBOT_HOST>`、`<ROBOT_USER>`、`<ROBOT_PASSWORD>`、`<PROXY_HOST>`、`<PROXY_USER>`、`<PROXY_PASSWORD>`、`<ARM_HOST>`、`<INTERNAL_IP>`）。复现前请按自己的环境填写：

```bash
# 真机采集
export ROBOT_HOST=<你的机器人IP>      # 或直接修改 run_remote_collect.py 的 HOST/USER/PWD
python run_remote_collect.py --host <IP> --user <USER> --pass <PASSWORD> --minutes 180

# VLA 双卡训练（参考 vla-slam-stack/code/README.md）
bash code/vla_run_train.sh      # GPU1: SmolVLA + LoRA
bash code/vla_run_train_act.sh  # GPU0: ACT
```

---

## 5. 未入库内容与原因

| 未入库 | 原因 |
|---|---|
| 第三方上游仓库（`repo_isaacsim_robotics_portfolio/`、`deploy_kit/lingbot-vla-v2/`、`vendor/three.js`） | 他人版权，请按各自 LICENSE 自行 clone |
| 模型权重、TensorRT engine、`.pt` / `.onnx` / `.safetensors` | 体积与许可限制 |
| 采集数据集（`episodes/`、`datasets/`、`*.npz`、`*.mp4`） | 体积 + 真机场景隐私 |
| 仿真录屏、照片、渲染帧 | 体积；如需展示请见简历附作品站 |
| 真机 IP、SSH 账号/密码、代理凭据、内网拓扑 | **已在入库前全部替换为占位符**；本目录不含任何可用凭据 |

---

## 6. 证据分级（延续本仓库 README 的诚信框架）

沿用仓库根 README 的三级标签，本目录内容严格按此标注：

| 标签 | 本目录中的例子 |
|---|---|
| **仓库实测值** | `bench/result*.json` 里的算力/显存/功耗数字；`EXIT=139` 段错误复现与规避；SmolVLA LoRA 参数报错链 |
| **演示测试值** | `isaac-sim-arm/` 的分拣成功率（合成场景 + 固定种子） |
| **历史报告值** | 真机采集的 episode 条数与平均耗时（原始数据集未随仓库发布） |
| **第三方成果（非本人）** | 上游 `IsaacSim_Robotics_Portfolio` 的场景与算法本体；LingBot-VLA 2.0 模型本体 |

> 本目录代码是为公开展示整理的工程实现记录，不含任职单位生产源码、客户数据、设备凭据、未公开模型权重与专利正文。
