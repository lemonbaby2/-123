# Metatron 方案试跑结果 · 2026-11-15

## 一、事实核验（先纠正：论文是真的）

| 项 | 结果 |
|---|---|
| 论文 | ✅ **arXiv:2610.38027v1**，*METATRON: A Promptable Whole-Body Execution Layer for Humanoids*，2026-10-27 |
| 作者 | Chen Tessler, Yifeng Jiang, Alec Otto, Yi Shi, Umar Iqbal, Gal Chechik, Xue Bin Peng（NVIDIA Research） |
| 方法 | **冻结的生成式 base policy** + **可编程 skill 层**；skill 是普通代码，由 coding agent 依据运动数据拟合规则，不重训策略 |
| 能力 | G1 真机：行走 / 起身 / 遥操作拾物 / 坐家具；仿真：攀爬、跨栏、踢球、网球等 |
| 官方代码 | ❌ GitHub `org:NVIDIA metatron` = 0；`metatron humanoids` = 0；项目页 404/403 |
| 权重 / MoCap | ❌ 未发布 |

**所以「完整复现 Metatron」今天做不到**。能在本机完整跑的是论文的可复现部分：
**冻结执行层 + Coding Agent 写 skill 代码 → 仿真验证 → 打分/轨迹归因 → 反馈迭代**。

## 二、本机试跑（真跑了，非演示）

环境：RTX 4060 8G + RTX 5060 Ti 16G；新建独立 venv，MuJoCo 4.0.1 + NumPy 2.5.4。
物理：自建平面双足（7 DOF / 5 执行器）+ 栏架；冻结执行层 = PD 全身控制器（替身，不可训练）。
Coding Agent 走 `setup_local_models.py` 建立的本地端点 `127.0.0.1:11434/v1`（`qwen2.5-coder:7b`）；
对照通道走 Hermes 网关 `127.0.0.1:8642/v1`（`gpt-5.5`）。
生成代码经 AST 白名单沙箱（无 import / 无循环 / 受限 builtins）后执行。

| 实验 | 轮数 | 基线 score | 最佳 score | 提升 | 跌倒率 | 越障 |
|---|---|---|---|---|---|---|
| 本地 7B（无轨迹反馈） | 3 | -0.704 | -0.704 | 0 | 1.0 → 1.0 | ❌ |
| 本地 7B（带运动轨迹反馈） | 5 | -0.704 | **+0.197** | **+0.901** | 1.0 → **0.0** | ❌ |
| 云端 gpt-5.5（带轨迹反馈） | 4 | -0.704 | +0.133 | +0.837 | 1.0 → **0.0** | ❌ |

- ✅ **闭环确实生效**：加入 rollout 轨迹（跌倒 x、离栏距离、最低躯干高度）后，两条通道都从「必跌倒」优化到「不跌倒」。
- ❌ **都没找到越障解**：48 组网格搜索证明解存在（3 组能越障，最高 score 2.879，需 stride≈0.8 / vx≈0.5 / 近栏 lift≥0.5 联动），可行域很窄。
- 🟡 云端通道两次生成非法代码（中文冒号 / 语法错误），本地 7B 反而更稳；但两者探索能力都不足以命中窄解。

**判读**：这恰好印证论文的前提——「不用重训、只写代码加技能」依赖一个**足够强的冻结 base policy**。
我们用 PD 替身，执行层能力弱 → 可行域窄 → coding agent 难以靠几次迭代命中。真机/完整复现必须拿到 NVIDIA 的 checkpoint。

## 三、远端 DGX：今天无法执行（硬约束）

| 探测 | 结果 |
|---|---|
| `<DGX_HOST>` = `<DGX_TAILSCALE_IP>` | ✅ Tailscale 在线（idle，DERP ~418ms） |
| TCP 22 / 11434 / 8300 / 8085 / 18501 | ❌ 全 000 |
| SSH lzp / nvidia / admin / ubuntu | ❌ `Permission denied (publickey,password)` / 超时 |
| 局域网 <LAN_HOST>/.71/.218/.133 | ❌ 全 closed |
| new-api <LAN_HOST>:8300 / Ollama :11434 | ❌ 不可达 |

按只读边界未强行登录、未改 DGX 配置。恢复条件与一键脚本见 `DGX.md` / `run_on_dgx.sh`。

## 四、交付物

| 文件 | 说明 |
|---|---|
| `metatron_trial.py` | 完整复现脚本（物理 + 冻结执行层 + 沙箱 + 仿真评估 + 迭代闭环） |
| `results_local_trace.json` / `results_cloud2.json` | 逐轮代码、指标、轨迹、ACCEPT/REJECT 记录 |
| `DGX.md` | DGX 探测证据、恢复条件、官方栈替代方案 |
| `run_on_dgx.sh` | 链路恢复后在 DGX 上一键复现 |

复跑命令：

```bash
cd <WORKDIR>/metatron_trial
./.venv/Scripts/python.exe metatron_trial.py --smoke
./.venv/Scripts/python.exe metatron_trial.py --rounds 5 --task hurdle --tag local_trace
```
