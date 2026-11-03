# 【Datawhale MicroDuck 组队学习】第 85 期学习记录

学习者：patient熬（2 群）。本目录区分课程原始资料、个人笔记与本机生成的实验结果；不把官方预录素材写成个人实测，也不把仿真结果等同于真机指标。

快速复现请从 [START_HERE.md](START_HERE.md) 开始。文档结构对 [Datawhale Hello-Robot](https://github.com/datawhalechina/hello-robot) 的工程化组织方式做了参考，但两个课程的机器人本体、仿真器和运行依赖不同，具体边界见 [HELLO_ROBOT_REFERENCE.md](HELLO_ROBOT_REFERENCE.md)。

| 任务 | 笔记 | 复现入口 | 结果与边界 |
| --- | --- | --- | --- |
| Task1 篮球平衡 | [Task1 学习笔记](task1/Task1_学习笔记.md) | [课程 Notebook](task1/Task1_篮球平衡_Notebook.ipynb)、[安全检查](task1/Task1_safe_check.py) | 61→14 ONNX，250 步/5 秒本机短仿真，0 重置；不是重新训练或真机验证。视频、轨迹和 JSON 在 `task1/`。|
| Task2 浏览器物理扰动 | [Task2 学习笔记](task2/Task2_学习笔记.md) | [课程 Notebook](task2/Task2_浏览器物理扰动_Notebook.ipynb)、[官方教学资料](task2/official_materials/README.md) | 浏览器 MuJoCo 接触/外力交互，具体本机验证和不足见笔记。|
| Task3–Task8 + 加餐 | **见 `microduck-task2` 分支** | [task3/notebooks 目录](https://github.com/lemonbaby2/-123/tree/microduck-task2/datawhale_microduck/task3/notebooks) | 8 个任务打包在 `task3/` 下，按 `00`–`09` 编号定位，详见下表。|
| **Task8 性能优化** | [优化报告](task8-optimization/README.md) | [优化脚本](task8-optimization/lightnav_opt.py)、[18 组原始数据](task8-optimization/reports/summary.csv) | 控制层优化，三场景平均残余距离改善 **21.7%**；不训练、不改权重、不用目标真值。|

### Task3–Task8 在 `microduck-task2` 分支的定位

`main` 分支只放了 Task1/Task2，Task3 之后的内容在 **`microduck-task2` 分支**的 `datawhale_microduck/task3/notebooks/` 下：

| 课程 Task | notebook 文件名 | 主题 |
| --- | --- | --- |
| — | `00_MuJoCo策略控制_HelloWorld.ipynb` | 环境预热 |
| Task1 | `01_篮球平衡_PPO_ONNX_BPU_MuJoCo.ipynb` | PPO 篮球平衡（main 也有） |
| Task2 | `02_浏览器物理扰动_回放与接口.ipynb` | mjswan 浏览器扰动（main 也有） |
| Task3 | `03_高跷行走_课程与ONNX_BPU.ipynb` | 形态课程 / 高跷 |
| Task4 | `04_摆动旋转_ONNX_BPU_MuJoCo.ipynb` | 自激摆动 |
| Task5 | `05_球平衡_FastSAC_ONNX_BPU.ipynb` | FastSAC 球平衡（54 维观测） |
| Task6 | `06_梯面攀爬_接触与部署模板.ipynb` | 双策略攀爬 |
| Task7 | `07_RDK网页与多策略_BPU验收.ipynb` | RDK X5 端侧（未验收，无板） |
| Task8 | `08_LightNav0_视觉语言导航_GPU_多场景.ipynb` | 视觉语言导航 |
| 加餐 | `09_跨缝跳跃_PPO_GPU_ONNX.ipynb` | 跨缝跳跃 |

**注意两个已知边界**：Task3/Task4 的 `--task Mjlab-Stilt-Flat-MicroDuck` / `Mjlab-SwingPump-MicroDuck` 在 mjlab 任务注册表里不存在（会报 `invalid choice`），notebook 显示 9/9 全绿但异常在日志里；Task7 没有 RDK X5 硬件，BPU 部分标记为 `not_run_no_board`。


## 运行与来源

Task1 原始 Notebook 的训练与视频格不应直接 `Run All`。公开模型文件并非课程 Notebook 自动生成。安全检查只检查环境定位和模型输入输出；已记录的短仿真结果由独立本机闭环生成。

Task2 源自 [Datawhale Every Embodied 专题](https://github.com/datawhalechina/every-embodied/tree/main/16-%E4%B8%93%E9%A2%98%E7%BB%84%E9%98%9F%E5%AD%A6%E4%B9%A0/05-MicroDuck%E8%BF%90%E5%8A%A8%E7%AD%96%E7%95%A5%E4%B8%8E%E4%BB%BB%E5%8A%A1%E5%BC%80%E5%8F%91%E4%B8%93%E9%A2%98) 与 [mjswan Playground](https://github.com/ttktjmt/mjswan_playground)。课程素材和模型的许可不因放在本仓库而变为仓库根目录的 MIT 许可；详见各任务的来源和许可说明。
