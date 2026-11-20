# 替换清单（本地候选，尚未推送）

生成时间：2026-11-21 00:52:37　目标仓库：`lemonbaby2/-123`

**模式：ADDITIVE_ONLY（只增改，不删除任何现有项目）**

## 为什么不做「全量替换」

原有 11 个项目的 clean-room 实现、独立测试和三层指标标签是仓库最有价值的诚实资产。把它们整体删除换成 8GB 本机的推理/仿真产物，既丢失可复现性，又会把演示数据抬成实机成绩。本轮只做：① 补真实性能图与可跑性账本；② 新增两个**真正做过且已脱敏**的 Agent 项目；③ 写完整 README。

## 文件动作

| 动作 | 路径 | 字节 |
|---|---|---|
| ADD | `evidence/AUDIT.md` | 9739 |
| ADD | `evidence/coverage.json` | 7076 |
| ADD | `evidence/benchmarks.json` | 13227 |
| ADD | `evidence/FIGURE_PROVENANCE.json` | 1001 |
| ADD | `evidence/round2_full_report.json` | 6103 |
| ADD | `evidence/round2_gpu_samples.json` | 53533 |
| ADD | `evidence/logs/repo_tests_full.log` | 11024 |
| ADD | `evidence/logs/round2_demos_full.log` | 7954 |
| ADD | `evidence/logs/round2_verify_layout_full.log` | 435 |
| ADD | `evidence/logs/round2_runner.log` | 4824 |
| ADD | `evidence/logs/round2_tests_full.log` | 11038 |
| ADD | `evidence/logs/repo_demos_full.log` | 7968 |
| ADD | `docs/figures/fig1_coverage_matrix.png` | 137403 |
| ADD | `docs/figures/fig2_ollama_gpu.png` | 90798 |
| ADD | `docs/figures/fig3_metatron_convergence.png` | 111499 |
| ADD | `docs/figures/fig4_hurdle_grid.png` | 82613 |
| ADD | `docs/figures/fig5_repo_selfcheck.png` | 35008 |
| ADD | `docs/figures/fig6_agent_latency.png` | 63369 |
| ADD | `docs/figures/fig7_gpu_trace.png` | 122151 |
| ADD | `docs/figures/fig8_runnability_ledger.png` | 127858 |
| ADD | `scripts/run_benchmarks.py` | 3932 |
| ADD | `scripts/make_figures.py` | 12644 |
| ADD | `scripts/round2_full_run.py` | 16134 |
| ADD | `scripts/make_figures_round2.py` | 6258 |
| ADD | `projects/12_agent_runtime_2026-11/setup_local_models.py` | 5840 |
| ADD | `projects/12_agent_runtime_2026-11/BENCH.md` | 5319 |
| ADD | `projects/12_agent_runtime_2026-11/Hermes_approval_patch.md` | 0 |
| ADD | `projects/13_metatron_coding_agent/metatron_trial.py` | 16944 |
| ADD | `projects/13_metatron_coding_agent/RESULT.md` | 3992 |
| ADD | `projects/13_metatron_coding_agent/DGX.md` | 2960 |
| ADD | `projects/13_metatron_coding_agent/run_on_dgx.sh` | 1318 |
| ADD | `projects/13_metatron_coding_agent/results_cloud.json` | 2899 |
| ADD | `projects/13_metatron_coding_agent/results_cloud2.json` | 5567 |
| ADD | `projects/13_metatron_coding_agent/results_local.json` | 5129 |
| ADD | `projects/13_metatron_coding_agent/results_local_trace.json` | 8990 |
| ADD | `projects/13_metatron_coding_agent/results_round2_local.json` | 9126 |

## 需要改动的既有文件（推送时）

| 文件 | 动作 | 风险 |
|---|---|---|
| `README.md` | 用本候选包版本替换 | 低；保留原三层口径与全部 11 个项目导航 |
| `README_EN.md` | 用本候选包版本替换 | 低 |
| `docs/RESUME_EVIDENCE_MATRIX.md` | **不改**（保留三层标签） | — |
| `projects/01..11/**` | **不改不删** | — |

## 未解决、需本人拍板

1. `evidence/course_demo_5min.mp4` 断链：上传真实录屏到 Release，还是把 README 改为外部资料链接（当前 README 已如实标注失败）。
2. 简历 7 组无证据指标：保留「历史报告值」口径、改写为区间，还是从简历删除。
3. 是否把 B 类产物拆成独立公开仓库，而不是并入本仓库。
4. 是否推送、推到哪个分支（`main` 直接提交 / 新分支 + PR）。

## 脱敏核验

组装脚本扫描结果：`NONE`（发现任何 `sk-*` / `gho_*` / `ghp_*` / 长 Bearer token 会硬中止）。
已替换：Tailscale / 局域网 IP、DGX 主机名、SSH 用户名、中转域名、本机绝对路径。

> 本目录是**审阅产物**。截至生成时未执行任何 `git push`、未改动远端仓库。
