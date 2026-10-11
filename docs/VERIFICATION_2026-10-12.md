# 2026-10-12 公开演示验证记录

环境：Windows，Python 3.12.3；代码基准 `f85f12e`。以下命令从仓库根目录执行。

| 命令 | 结果 |
| --- | --- |
| `python scripts/verify_layout.py` | 8 个项目结构完整，本地 README 链接有效 |
| `python scripts/run_tests.py` | 8 个项目共 32 项测试通过 |
| `python scripts/run_all_demos.py` | 8 个项目均输出可解析 JSON |
| `python vla_vlm_projects/run_tests.py` | 两个工程共 6 项测试通过 |
| `python vla_vlm_projects/run_all_demos.py` | 2 个 dry-run 工程均输出可解析 JSON |

这些测试验证公开演示的程序逻辑和样例输出。它们没有连接真实机器人、相机、产线、MCU 或企业数据，也不验证简历中的实机精度、延迟、功耗和生产效果。复测所需原始资产见[项目索引](RESUME_2026_PROJECT_INDEX.md)和[复现清单](REPRODUCTION_CHECKLIST.md)。
