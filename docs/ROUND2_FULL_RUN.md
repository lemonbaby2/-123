# 全量实跑报告 · 2026-11-21 00:42:05

> 原则：Only real execution is recorded. Items requiring DGX / original datasets / proprietary weights are marked NOT_RUNNABLE, never faked.
> 机器：Windows / RTX 4060 8GB (GPU1 lost) / Ollama 127.0.0.1:11434 / MuJoCo 4.0.1

## 结论先行

本机把**物理上能跑的**全部跑全；16 条简历项目中 3 条可跑全、
6 条部分可跑、6 条本机不可跑、
1 条已在远端验证。
**没有任何演示数据被包装成实机成绩，没有为缺失的原始指标生成替代曲线。**

## 阶段明细（串行执行）

| 阶段 | 结果 | 起止 |
|---|---|---|
| 0_environment | `{"gpu_query": "NVIDIA GeForce RTX 4060, 581.57, 8188, 3248, 6", "ollama_models": ["llama3.1:8b", "gpt-oss:20b", "qwen2.5-coder:7b", "deepseek-r1:70b", "deepseek-r1:14b", "qwen3.5:2b-q4_K_M", "qwen3.5:9b-q4_K_M", "nomic-e` | 00:42:05 → 00:42:06 |
| 1_ollama_gpu_benchmark | `{"cold_calls": 9, "warm_calls": 15, "models": ["qwen2.5-coder:7b", "qwen3.5:2b-q4_K_M", "qwen3.5:9b-q4_K_M"], "steady_tps": {"qwen2.5-coder:7b": [95.93, 101.01, 83.4, 93.87, 97.46], "qwen3.5:2b-q4_K_M": [154.07, 165.18, ` | 00:42:06 → 00:47:41 |
| 2_mujoco_grid | `{"episodes": 48, "best_score": 2.879, "cleared": 3, "zero_fall": 41}` | 00:47:41 → 00:47:43 |
| 3_metatron_coding_agent | `{"rounds": 5, "baseline": -0.704, "best": -0.704, "result_file": "results_round2_local.json"}` | 00:47:43 → 00:48:58 |
| 4_repo_selfcheck | `{"run_tests.py": {"exit_code": 1, "log": "repo_tests_full.log"}, "run_all_demos.py": {"exit_code": 0, "log": "round2_demos_full.log"}, "verify_layout.py": {"exit_code": 1, "log": "round2_verify_layout_full.log"}, "tests_` | 00:48:58 → 00:49:04 |
| 5_runnability_ledger | `{"total_items": 16, "by_status": {"NOT_RUNNABLE": 6, "PARTIAL": 6, "VERIFIED_UPSTREAM": 1, "RUNNABLE": 3}}` | 00:49:04 → 00:49:04 |

## 原始输出索引

| 文件 | 内容 |
|---|---|
| `evidence/benchmarks.json` | Ollama 冷加载/稳态逐次调用 + 48 组 MuJoCo 网格 |
| `evidence/round2_gpu_samples.json` | 实跑期间逐点 nvidia-smi 显存/利用率 |
| `evidence/round2_full_report.json` | 全阶段结构化结果与可跑性账本 |
| `evidence/logs/round2_runner.log` | runner 完整 stdout |
| `evidence/logs/repo_tests_full.log` | 线上仓库全量测试原始日志 |
| `evidence/logs/round2_demos_full.log` | 全部 demo 的 JSON 输出 |
| `evidence/FIGURE_PROVENANCE.json` | 每张图的数据来源 |

## 复跑命令

```bash
python scripts/round2_full_run.py
python scripts/make_figures_round2.py
cd upstream_-123 && python scripts/run_tests.py && python scripts/run_all_demos.py
```

## 未完成项（不隐瞒）

1. 远端 DGX 22 / 11434 / 8300 / 8085 / 18501 全部不可达，SSH 无授权 → 需要多卡训练的项目未执行。
2. `evidence/course_demo_5min.mp4` 缺失导致 3 个用例失败；未用占位视频掩盖。
3. 7 组简历历史指标无原始日志，未生成任何曲线；原文见主 README「铁律：不伪造」一节。
