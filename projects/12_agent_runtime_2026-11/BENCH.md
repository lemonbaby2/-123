# 全机 Agent 本地模型接入与内测报告 · 2026-11-15

## 结论

✅ Hermes 桌面端已**完整启动**（主进程 31784 / 后端 50888 / 网关 8642）。
✅ 本机 Ollama 已起，统一端点 `http://127.0.0.1:11434/v1`（key `ollama`），8 个模型可用。
✅ Hermes / Codex CLI / OpenCode / Continue 已新增本地 provider，**默认模型一律未改**。
✅ 审批守卫改走本地模型，彻底脱离外网代理与坏中转，11/07 的「超时拒绝命令」不再复发。
🟡 远端 Tailscale DGX 在线但服务端口不通、SSH 无授权，暂未接入。
❌ Claude Code / Cline / Copilot 需 Anthropic 协议网关，本机未装，未擅自改动。

## 一、两个真根因（今天才暴露）

| 现象 | 根因 | 修复 |
|---|---|---|
| 桌面端双击/启动后一闪即退 | WorkBuddy 会话注入 `ELECTRON_RUN_AS_NODE=1`，把 Electron 当纯 Node CLI | 启动前清空该变量与 `NODE_OPTIONS` |
| 所有外网模型调用 `Connection error` | 会话级 `HTTPS_PROXY=127.0.0.1:7890` 是死端口；实际代理在 **7891** | 重启桌面端时注入 7891；守卫改本地不再依赖代理 |

## 二、模型端点实测

| 端点 | 结果 |
|---|---|
| `127.0.0.1:11434` 本机 Ollama | ✅ 200，8 模型（之前只是服务没起，开机启动项 `Ollama.lnk` 已存在） |
| `127.0.0.1:8642` Hermes 网关 | ✅ OpenAI 兼容，`/v1/chat/completions` 200 |
| `<RELAY_HOST>` 中转 | ✅ 直连可达，但**回复内容整体重复**（`OKOK`），不适合做主模型 |
| `chatgpt.com` Codex OAuth | ✅ 必须走代理 7891 |
| `api.deepseek.com` | ❌ 402 余额不足 |
| `<LAN_HOST>:8300 / :11434` | ❌ 不可达 |
| Tailscale `<DGX_TAILSCALE_IP>` (<DGX_HOST>) | 🟡 ping 通（DERP 418ms），11434/8300/8085/18501 等 9 个端口全 000；SSH 被拒（publickey/password） |

## 三、接入矩阵

| 软件 | 配置文件 | 动作 | 使用方式 |
|---|---|---|---|
| Hermes Agent | `AppData/Local/hermes/config.yaml` | 补全本地 7 模型清单、本地模型设为第一兜底、`auxiliary.approval` → `qwen2.5-coder:7b` | 新会话选 `custom:ollama-local`；或 `hermes -z "..." --provider custom:ollama-local -m qwen3.5:9b-q4_K_M` |
| Codex CLI | `~/.codex/config.toml` | 新增 `[model_providers.ollama-local]` + `[profiles.ollama-local]` | `codex --profile ollama-local` |
| OpenCode | `~/.config/opencode/opencode.json` | 新增 `ollama-local` provider（7 模型） | 模型选择器里选 |
| Continue | `~/.continue/config.yaml` | 新增 ollama / qwen3.5:9b 条目 | Continue 模型列表 |
| Claude Code / Cline / Copilot | — | **未改**（需 Anthropic ↔ OpenAI 协议转换） | 装 `litellm` 或 `claude-code-router` 后指向 11434 |

所有改动有 `.bak-YYYYmmdd-HHMMSS` 备份；`setup_local_models.py` 幂等，可重复跑、`--verify` 只读检查。

## 四、内测性能（<WORKSPACE>，单轮 `hermes -z`）

| 用例 | 通道 | 耗时 | tokens | 结果 |
|---|---|---|---|---|
| 短答保真「只回复 OK」 | Codex / gpt-5.5（云端） | 16.3s | 8225 | ✅ `OK🦾` |
| 短答保真 | 本地 qwen3.5:9b | 45.4s | 8264 | ✅ `OK` |
| 裸 API tool_calls | 本地 qwen3.5:9b | — | — | ✅ 标准 `tool_calls` 字段 |
| 裸 API tool_calls | 本地 qwen2.5-coder:7b | — | — | ❌ 只在 content 里吐 JSON |
| 完整 agent 工具编排 | 本地 qwen3.5:9b | 83.2s | — | ❌ 编造 `hermes register --target 19b3.exe` |
| 完整 agent 工具编排 | 云端 gpt-5.5 / gpt-5.4 | 84.5s / 9.4s | — | ❌ 输出命令代码块而非执行 |
| 完整 agent 工具编排 | Codex / gpt-5.6-sol | 19.0s | — | 🟡 返回 1 个真实目录名 |
| 审批阶梯 `approvals test` | 静态 | — | — | ✅ allow / allow / ask-approval / hardline-deny |
| 守卫裁决（本地 7B） | 纯本地 | — | — | ✅ 只读 APPROVE；`rm -rf /` DENY；`icacls` DENY |

**判读**：本地 9B 适合离线问答、兜底、审批守卫；**不适合做主力 agent 的工具编排**（长系统提示 ~8194 tok 下会幻觉）。`-z` 单轮模式的工具编排普遍不稳，桌面多轮会话需另行复测。

## 五、遗留与恢复指引

1. **Claude Code 系列**：`pip install litellm` → `litellm --model ollama/qwen3.5:9b-q4_K_M --api_base http://127.0.0.1:11434 --port 4000`，再把 `ANTHROPIC_BASE_URL` 指过去。未擅自安装。
2. **Tailscale 远端**：需李老师在 DGX 上把 Ollama 绑到 `0.0.0.0` 并放行端口，或提供 SSH 密钥；之后把 `setup_local_models.py` 的 `BASE` 换掉即可全量切换。
3. **代理易变**：7891 若换端口，只需重启 Hermes 时重新注入；守卫走本地后已不受影响。
4. **Codex 配置会被桌面版重写**：若 `[model_providers.ollama-local]` 消失，重跑一次 `setup_local_models.py`。

## 六、可执行命令

```bash
# 幂等接入 / 只读核验
python <WORKDIR>/agent_model_setup/setup_local_models.py
python <WORKDIR>/agent_model_setup/setup_local_models.py --verify

# 本地模型跑 Hermes
cd "<WORKSPACE>" && hermes -z "任务" --provider custom:ollama-local -m qwen3.5:9b-q4_K_M

# Codex 走本地
codex --profile ollama-local

# 统一 OpenAI 兼容端点（任何软件）
curl http://127.0.0.1:11434/v1/models
```
