# R1-VLA Jetson 边缘部署包 v1.0.0

**定位**：把 DGX-R1 Agent Studio 的「自强化 / 蒸馏 / 量化 / 回归守护」工程能力，扩展到机器人 VLA 与世界模型，落到 NVIDIA Jetson Orin（CUDA）边缘盒子。交付的是**可运行的部署程序 + 可一键触发的蒸馏流水线 + 本机安装包**，不是已训练好的权重。

版本：1.0.0 ｜ 日期：2026-11-14 ｜ 自检：**7/7 通过**（无需 CUDA、无需权重）

---

## 0. 先把三个硬事实说清楚

| # | 事实 | 影响 |
|---|---|---|
| 1 | **不存在「Jetson NX 32GB」这个型号**。Orin NX 只有 8GB / 16GB；32GB 是 **Jetson AGX Orin 32GB**，按 NVIDIA 官方为 **1792 CUDA / 200 TOPS** / 204.8 GB/s / 2×DLA / 8 核 / 15–40W / JetPack 6 (sm_87)。**2048 CUDA / 275 TOPS 是 64GB 版**，别混。Xavier NX 16GB 是上一代。 | 部署栈完全不同，需确认盒子实际型号。本包 `probe` 会自动识别并给出档位。详见 `docs/01`（含第三方表格口径冲突的裁定）。 |
| 2 | **「一晚把各种 VLA / 世界模型全部蒸馏出来」做不到。** 公开实证：OpenVLA-OFT 微调要 8×A100/H100 跑 1–2 天；最轻的 SmolVLA 单张 A100 20k 步也要 4–5 小时，且那是从头训 450M 而非蒸馏。Shallow-π（Samsung, arXiv 2601.20262）证明 18→6 层＋交叉注意力 KL 蒸馏可把 Jetson Orin 从 3Hz 提到 ≈10Hz、掉点 <1%，但论文未报告训练时长。 | 本包交付完整流水线与门禁，权重在夜窗分批产出。`plan` 明确写 `feasible_in_one_night=false`，绝不伪造训练结果。务实捷径是直接用现成小 student + 分解式导出。 |
| 3 | **现有产线边缘盒子是 RK3588 + Hailo-8，没有 CUDA。** 那条链必须走 RKNN / HEF，`.pt` 全跑不了。 | 这是两套独立栈，不能混用。见 `docs/04_与RK3588_Hailo链路差异.md`。 |
| 4 | **许可证是硬闸门，不是脚注。** GR00T N1.5 / N1.6 权重为 NVIDIA One-Way **Noncommercial** License，蒸馏后商用不成立；π0.6 / Gemini Robotics / 1X World Model 闭源不可蒸馏。 | 商用蒸馏只能用 **GR00T N1.7（商业许可）/ π0・π0.5(openpi) / OpenVLA-OFT(MIT) / SmolVLA(Apache-2.0)**。注册表 `commercial_ok=false` 会被 `plan` 硬拦。 |

另外：口语里的「师姐模型」按 **世界模型（World Model）** 理解（NVIDIA Cosmos / DynaWM / EnerVerse / 1X World Model 一类）。世界模型参数量级只能留在 DGX 做数据生成与评测，不上边缘盒子。

---

## 1. 快速开始

### 本机（Windows，无需显卡）

```bash
# 解压 zip 后
双击 安装到本机.bat        # 跑 7 项全链路自检
双击 启动控制台.bat        # 打开 http://127.0.0.1:18931
```

控制台可看：硬件档位、17 个模型注册表、任意 teacher 的蒸馏计划、一键自检、一键重新打包。不连外网、不上传数据。

命令行：

```bash
python edge/edge_cli.py probe                      # 硬件探测
python edge/edge_cli.py list --edge-only           # 可边缘部署的模型
python edge/edge_cli.py plan --teacher pi0   # 蒸馏计划（含诚实门禁）
python edge/edge_cli.py distill --teacher pi05     # 生成 DGX 夜窗训练脚本
python edge/edge_cli.py infer --instruction "抓取工件"
python edge/edge_cli.py bench --n 200
python edge/edge_cli.py serve --port 18930         # HTTP 推理服务
python edge/edge_cli.py selftest                   # 7/7 自检
```

### Jetson Orin（JetPack 6）

```bash
scp -r edge/ <user>@<jetson>:~/r1vla/
ssh <user>@<jetson>
cd ~/r1vla/edge && chmod +x install.sh
./install.sh --probe-only          # 先确认型号与 JetPack
./install.sh                       # 装依赖 + 自检
./install.sh --build-engine export/student.onnx --dla 0    # 有 ONNX 后构建 FP16 engine
./install.sh --service             # 注册 systemd --user 常驻服务
```

⛔ `torch` / `tensorrt` 的 aarch64 wheel 由 JetPack 提供，**不要用 pip 覆盖**。

### DGX（蒸馏，夜窗）

`python edge/edge_cli.py distill --teacher pi0` 会在 `jobs/` 生成一个 `bash -n` 已通过的 6 阶段脚本，含资源闸门、teacher 权重检查、示教数据检查、伪标签、行为克隆、回归守护、ONNX 导出。**前置条件不满足时脚本会明确停止（exit 2/3），不会伪造成功。**

---

## 2. 目录结构

```
├── README.md                    本文件
├── docs/
│   ├── 01_硬件与型号纠偏.md      型号核实与档位差异
│   ├── 02_模型全景与蒸馏可行性.md 2026 前沿 VLA / 世界模型核实报告
│   ├── 03_部署操作手册.md        分阶段步骤
│   └── 04_与RK3588_Hailo链路差异.md
├── config/models.json           模型注册表（17 条，含许可证/参数量/边缘形态）
├── edge/
│   ├── edge_core.py             硬件探测 / 注册表 / 蒸馏规划 / 动作安全 / 后端
│   ├── edge_cli.py              8 个子命令 + HTTP 服务 + 7 项自检
│   ├── install.sh               Jetson 一键安装 / engine 构建 / 常驻服务
│   └── requirements-jetson.txt
├── desktop/
│   ├── control_panel.py         本机 Web 控制台（标准库，零依赖）
│   └── build_installer.py       生成 zip 安装包 + SHA256
├── jobs/                        运行时生成的 DGX 蒸馏脚本
├── reports/                     自检 / 基准报告
└── dist/                        安装包输出
```

## 3. 模型选型（2026-11 核实）

| 用途 | 首选 | 理由 |
|---|---|---|
| **边缘直接部署** | SmolVLA 450M | Apache-2.0；Orin Nano 8GB ONNX+TRT FP16 实测 **5.25Hz / 1871MB**（第三方「30+Hz」无实测佐证）。本身已是 student，再蒸收益为负 |
| **实时目标形态** | Shallow-π 式 student / Tether 分解式 π0.5 | Shallow-π 在 Jetson Orin ≈10Hz、掉点 <1%；Tether 把 AGX Orin 上 π0.5 从 900ms 降到 **100ms（9×）**，cos=+1.000000 |
| 商用蒸馏 teacher | **GR00T N1.7 / π0 / π0.5 / OpenVLA-OFT** | 许可证允许派生；N1.7 在 Jetson AGX Thor 12.4Hz |
| ⛔ 仅研究 | GR00T N1.5 / N1.6 | One-Way Noncommercial，蒸馏后商用不成立 |
| 感知/场景理解层 | SmolVLM2 / Qwen2.5-VL / YOLO11n | 不输出动作；感知层必须走 TensorRT（Orin NX 上 ONNX 67.92ms vs TRT FP16 4.80ms） |
| 数据引擎（DGX only） | Cosmos-Predict2.5 (2B/14B) 等世界模型 | Transfer2.5-2B 仍需 65.4GB VRAM / 8×A100；1XWM 生成 5s 视频需 11s，**秒级**，不上边缘 |
| 不可蒸馏 | π0.6 / Gemini Robotics On-Device / RT-2 / 1XWM | 闭源或历史参照 |

> **DLA 边界**：DLA 只支持 conv/deconv/FC/activation/pooling/BN，**不支持 Transformer 注意力与流匹配 DiT 的迭代去噪**。TensorRT 只能把卷积子图卸载到 DLA，动作头仍走 GPU。原生 llama.cpp 也不支持 VLA 推理模式，需要 `vla.cpp` 这类派生引擎才能承载 GGUF 动作头。

## 4. 安全与验收

- **三重动作钳位**：关节限位 → 速率限幅（0.15 rad/step）→ 120ms deadline 超时保持原位。自检逐项验证。
- **回归守护**：固定基准集 teacher→student 数值 parity cos ≥ 0.99，未过门禁禁止导出。
- **边缘验收**：分布内成功率 ≥ 0.80、实时 ≥ 5Hz（目标 10Hz）、安全违规 0。
- **生产共存**：蒸馏只在夜窗跑，开训前停 Ollama 让路、训完恢复；沿用 R1 Forge 的资源闸门约定。

## 5. 边界与红线

- 本包**不含任何模型权重**，也不含内网地址、网关 Token、Funnel 域名、本机用户名。
- 不在本机跑训练；不在 Jetson 上跑蒸馏；不在 RK3588 上跑 CUDA。
- 参数量为 `null` 的条目表示**未核实**，禁止当事实引用；来源冲突在 `docs/01` / `docs/02` 逐条列出，不静默取舍。
- **`commercial_ok=false` 的模型不得进入商用蒸馏链**；`plan` 会直接给出阻塞项。
- 世界模型只作为 DGX 侧数据引擎，不在边缘部署。
- 专利交底书中「生产共存自强化 / 无源再量化 / 固定基准回归守护」等未申请细节不进入任何公开产物。
