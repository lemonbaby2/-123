# 当前分支：MicroDuck Task1

这是 `microduck-task1` 提交分支，核心交付位于 [`task1/`](task1/)。

## 直接验证

```bash
python -m pip install onnx
python datawhale_microduck/task1/Task1_safe_check.py
```

预期策略契约：`obs [1, 61] → actions [1, 14]`。完整 Notebook、5 秒闭环视频、轨迹和机器可读报告见 [`task1/README.md`](task1/README.md)。不要对课程原始 Notebook 直接执行 `Run All`。

Jupyter 启动方式和环境边界见 [`START_HERE.md`](START_HERE.md)。

