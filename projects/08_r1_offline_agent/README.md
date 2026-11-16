# R1-VLA 离线自学习 Agent

> 断网 / 无 WiFi 也能回答、试错、记忆、上线的工业机器人 VLA 自主 Agent。
> 全部逻辑仅依赖 Python 标准库，**零外部下载、零模型依赖、零外联**。

---

## 它解决什么

1. **离线答疑**：知识库全部在本地 `memory/`，检索用纯 Python BM25（中英混排 bigram），
   断网也能从自己的知识库找答案，绝不编造库外事实。
2. **自主决策与执行**：内置动作分发（`answer` / `daily_vla` / `ingest` / `reconcile`），
   可触发每日 VLA 验收、吸收新文档、复核历史错误项。
3. **每天 20h 自学习（Action 试错）**：内测窗口对任务库反复试错 —
   - 正确 → 固化进 `memory/verified.jsonl`（记忆回去）
   - 错误 → 进 `memory/recheck.jsonl`（标记原因，等待复核）
   - `reconcile` 基于已增长的知识库重新核对，通过则转正。
4. **满一月精确后上线**：门控要求 `天数≥30 且 精确率≥0.90 且 知识库条目≥200` → 标记 `go_live`。

---

## 快速启动

```bat
start.bat          :: Windows 一键: 离线控制台 + 后台自学习
install.bat        :: 安装 + 注册每日 20h 计划任务
```

```bash
python start.py --offline --web --loop --budget 72000   # 生产: 控制台+每日20h
python start.py --offline --loop --budget 60            # 演示: 60秒窗口看分流
python start.py --offline --reconcile                   # 复核历史错误项
python start.py --ingest <目录或文件>                   # 吸收一份新文档
```

控制台（仅本机）：http://127.0.0.1:18941

---

## 离线合规

- `core/guard.py` 在安装 `strict_offline` 后**拦截一切非回环 socket 连接**，
  只放行 `127.0.0.1`（本地 Ollama）。已自检：连接 `8.8.8.8` 被拒。
- 检索、校验、记忆、上线门控全部本地完成，不需要任何外部服务。
- 若本机有 Ollama（联网时 `ollama pull qwen2.5:7b` 一次），离线问答将调用本地模型合成更完整答案；
  无 Ollama 时自动降级为「检索增强模板」，依旧可答。

---

## 目录

```
core/        kb.py 知识库(BM25) | agent.py 闭环+动作 | llm.py 本地LLM兜底
             verify.py 自我校验 | selflearn.py 20h试错+记忆+门控 | guard.py 离线护栏 | web.py 控制台
corpus/      知识库语料 (提问归档/顶刊清单/VLA研究/每日验收报告/边缘部署)
tasks/       自学习任务库 (sample_tasks.jsonl)
memory/      知识库索引 + 记忆(verified/recheck) + 状态(state.json)
dgx/         systemd --user service+timer (DGX 上每日20h内测)
docs/        架构 / 自学习机制 / 与每日VLA验收关系
```

---

## 与「每日 VLA 验收公网门户」的关系

- 本 Agent 是**离线大脑**：答疑、试错、记忆、上线决策。
- `dgx/r1-vla-accept`（另一交付）是**在线肌肉**：每天在 DGX 上真跑 WALL-OSS-0.5 推理，
  产出验收报告+曲线，结果回灌进本 Agent 的 `corpus/`，形成「在线验收 → 离线吸收」闭环。
- VLA 门户已本地运行（127.0.0.1:18932，每日 05:30 定时，已产出 PASS 报告 + 4 张曲线）。
  公网暴露受 DGX funnel 端口（10000–10014 + 443）已全部占用于生产/ros2/Embodied Studio 所限，
  释放任一端口后执行 `dgx/enable_public.sh` 即可一键公网化。

详见 `docs/`。
