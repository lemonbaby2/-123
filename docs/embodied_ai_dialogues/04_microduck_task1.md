# MicroDuck 组队学习 Task1：篮球平衡 PPO → ONNX → MuJoCo

> 来源会话：`82c190bf-7988-4b7d-a1ac-6509d6e6330c.jsonl` ｜ 原文件 2.4 MB ｜ 用户需求 4 条 / 摘录 56 段
> 本文件为**脱敏摘录**：已删除工具调用原始输出与系统提示注入，并对凭据 / 内网地址 / 主机名 / 手机号 / 邮箱 / 网盘链接做占位替换。


## 1. 需求
帮我完成下列打卡任务和仿真器完整提交到下列链接。欢迎加入第 85 期 MicroDuck 组队学习 2 群！ 🦆 Task1 开跑！认识小鸭子与篮球平衡 🏀 各位航海家，第一个任务来啦～用第一本 Notebook 认识 MicroDuck，搞懂它为什么能稳稳顶住篮球。 📚 本任务主题：模型 / 观测 / 动作 / PPO · 模型 —— 策略网络「61 维观测 → 14 维动作」 · 观测 —— 小鸭子每一瞬间的「全套身体感觉」 · 动作 —— 14 个关节电机怎么动 · PPO —— 它怎么摔几百万次自己学会站稳 ⏰ 截止：10/15 凌晨 03:00 📝 打卡 👉 [https://magicyang.feishu.cn/share/base/form/shrcnCXBWW7pd3HG4yHUjwaGYYx](https://magicyang.feishu.cn/share/base/form/shrcnCXBWW7pd3HG4yHUjwaGYYx) （打开后选 Task1 打就行） 课程入口（第一本 Notebook 在这）👉 [https://github.com/datawhalechina/every-embodied/tree/main/16-专题组队学习/05-MicroDuck运动策略与任务开发专题/01-任务资料/01-MicroDuck篮球平衡强化学习](https://github.com/datawhalechina/every-embodied/tree/main/16-专题组队学习/05-MicroDuck运动策略与任务开发专题/01-任务资料/01-MicroDuck篮球平衡强化学习) 组队：本期组队学习，3-5 人一组。先到「学员介绍」表填自己，组好队再到「组队登记」表登记 [@share-html#docs.qq.com%2F...:https://docs.qq.com/smartsheet/DWFpIamVMZENLb2VY?_fid=XZHjeLdCKoeX](https://docs.qq.com/smartsheet/DWFpIamVMZENLb2VY?_fid=XZHjeLdCKoeX)环境是这期第一道坎，卡住就截图往群里丢，别硬扛～ 一起拿下第一关 🚀 启动上述完整把 你可以把环境搬进 WSL2 Ubuntu，用浏览器开 Jupyter，MuJoCo 的 XML 解析器在 Windows 上对中文路径支持不好。你路径有中文，并且开源的链接在[https://github.com/datawhalechina/every-embodied/tree/main/16-%E4%B8%93%E9%A2%98%E7%BB%84%E9%98%9F%E5%AD%A6%E4%B9%A0/05-MicroDuck%E8%BF

**结论 / 做法**
429 queue.waiting.title (05fe860a504743dd8a40c49e0d2c613c/82c190bf-7988-4b7d-a1ac-6509d6e6330c)

## 2. 需求
帮我完成下列打卡任务和仿真器完整提交到下列链接。欢迎加入第 85 期 MicroDuck 组队学习 2 群！ 🦆 Task1 开跑！认识小鸭子与篮球平衡 🏀 各位航海家，第一个任务来啦～用第一本 Notebook 认识 MicroDuck，搞懂它为什么能稳稳顶住篮球。 📚 本任务主题：模型 / 观测 / 动作 / PPO · 模型 —— 策略网络「61 维观测 → 14 维动作」 · 观测 —— 小鸭子每一瞬间的「全套身体感觉」 · 动作 —— 14 个关节电机怎么动 · PPO —— 它怎么摔几百万次自己学会站稳 ⏰ 截止：10/15 凌晨 03:00 📝 打卡 👉 [https://magicyang.feishu.cn/share/base/form/shrcnCXBWW7pd3HG4yHUjwaGYYx](https://magicyang.feishu.cn/share/base/form/shrcnCXBWW7pd3HG4yHUjwaGYYx) （打开后选 Task1 打就行） 课程入口（第一本 Notebook 在这）👉 [https://github.com/datawhalechina/every-embodied/tree/main/16-专题组队学习/05-MicroDuck运动策略与任务开发专题/01-任务资料/01-MicroDuck篮球平衡强化学习](https://github.com/datawhalechina/every-embodied/tree/main/16-专题组队学习/05-MicroDuck运动策略与任务开发专题/01-任务资料/01-MicroDuck篮球平衡强化学习) 组队：本期组队学习，3-5 人一组。先到「学员介绍」表填自己，组好队再到「组队登记」表登记 [@share-html#docs.qq.com%2F...:https://docs.qq.com/smartsheet/DWFpIamVMZENLb2VY?_fid=XZHjeLdCKoeX](https://docs.qq.com/smartsheet/DWFpIamVMZENLb2VY?_fid=XZHjeLdCKoeX)环境是这期第一道坎，卡住就截图往群里丢，别硬扛～ 一起拿下第一关 🚀 启动上述完整把 你可以把环境搬进 WSL2 Ubuntu，用浏览器开 Jupyter，MuJoCo 的 XML 解析器在 Windows 上对中文路径支持不好。你路径有中文，并且开源的链接在[https://github.com/datawhalechina/every-embodied/tree/main/16-%E4%B8%93%E9%A2%98%E7%BB%84%E9%98%9F%E5%AD%A6%E4%B9%A0/05-MicroDuck%E8%BF

**结论 / 做法**
收到李老师。这是第 85 期 MicroDuck Task1 打卡：跑通 Notebook（WSL2 Ubuntu + MuJoCo，避开中文路径）、输出结果、提交到飞书打卡表。工作区里已有 `MicroDuck_Task1/` 和 `MicroDuck_Task1_Submission/`，我先盘点现状再决定补哪些。

**结论 / 做法**
Notebook 结构、模型契约、WSL 可用性都确认完毕。现在按李老师的要求把环境搬进 WSL2 Ubuntu 跑。先确认 WSL 里的 GPU 可见性和用户环境：

**结论 / 做法**
WSL2 里 GPU 可见（RTX 4060 / 581.57，libcuda 就位），用户 lizp，Python 3.10（需 3.12，用 uv 装）。开始搭建：

**结论 / 做法**
uv 0.13.1 装好。现在把专题目录和模型复制到 WSL 的 ASCII 路径（剔除 Windows .venv 和旧验证输出）：

**结论 / 做法**
复制完成。启动 `uv sync`（大下载：torch 2.9.1 + CUDA 依赖 + mjlab + warp，放后台跑）：

**结论 / 做法**
轨迹数据核验通过：obs (250,61)、actions (250,14) 裁剪在 [-1,1]、done 全 False。本机跑的证据链完整。继续盯 uv sync：

**结论 / 做法**
uv sync 下载了大半（缓存 2.5G）但安装阶段被后台任务的进程组清理杀了。改用 WSL 内部 setsid 脱离进程组的方式重跑：

**结论 / 做法**
脱离进程组的 uv sync 已起来（pid 518）。等待期间加载浏览器技能，为稍后飞书表单提交和 Jupyter 截图做准备：

**结论 / 做法**
agent-browser 就绪。uv sync 正在下大件（cudnn 674MB、triton 等）。趁等待，检查 agent-browser 能否复用系统 Chrome 登录态（飞书表单要登录）：

## 3. 需求
搜索我的github 我好像都做完了，你先去看看有什么改进

**结论 / 做法**
李老师，收到——先不纠结 WSL 抖动，按你的新指令走：去盘点你的 GitHub（lemonbaby2），看 MicroDuck 这块是不是真做完了，并找可改进点。先调起 GitHub 全量盘点技能。

**结论 / 做法**
全量仓库列表拿到。我能直接看到原创仓库里有几个高度相关的（MicroDuck_Task1_Submission 等），但需要完整清单。先看落盘的 JSON，确认 MicroDuck / 具身 / 机器人相关项：

**结论 / 做法**
关键发现：这里**没有**本地工作区里那几个 MicroDuck 仓库（MicroDuck_Task1、MicroDuck_Task1_Submission、MicroDuck_Task2_* 等）。也就是说—— - 本地 `E:\研究生学习\黑客松\` 下已完成的 MicroDuck 成果**根本没有 push 到 GitHub** - GitHub 上 lemonbaby2 里跟 MicroDuck/具身运动策略最接近的只有 `Embodied-AI-Guide`（fork，9/25） 这本身就是最大的"未完成"点。我核对一下这几个候选仓库到底有没有 MicroDuck 内容，并确认本地是否已上传过：

**结论 / 做法**
核心结论基本清晰了：**本地那一大堆 MicroDuck 成果（Task1/Task2 系列）一个都没出现在 GitHub 上**。再深挖最接近的 `Embodied-AI-Guide`，并核实 `lemonbaby2` profile 仓库和 `-123` 简历仓里有没有夹带 MicroDuck 内容：

**结论 / 做法**
429 您的使用量已超出频率限制，将在 2026-10-18 02:45:21 UTC+8 重置，您也可以切换其他模型继续使用。 (ac735aeb25fc4b039e224b700f835808/82c190bf-7988-4b7d-a1ac-6509d6e6330c)

## 4. 需求
https://microduck-mujoco.app.workbuddy.host/ 搜索我的github 我的这只鸭子还不够优秀去对比凯源的鸭子数据GitHub，@image#1:Clipboard_Screenshot.png 如图所示 爬爬楼梯和 01_篮球平衡_PPO_ONNX_BPU_MuJoCo.ipynb都不够优秀，五、第二轮攻坚记录（5 项阻断的解除） Notebook 原阻断根因 解除方式 01 篮球 缺官方仓库与任务注册 DGX 实测有外网（此前 gitclone 镜像 502 误判）→ GIT_CONFIG_GLOBAL=/dev/null 绕过镜像直连 GitHub 克隆 microduck-playground-official；export.py 补 import mjlab_microduck.tasks 修复任务注册 05 球平衡 缺 FastSAC 模型与训练入口 MotrixLab uv sync --package motrix-lab --extra cuda（triton 无 aarch64 轮子，--no-install-package triton 绕行）；补 scripts/train.py / scripts/export_onnx.py 两个 shim 指向 mxlab；learning_starts=0→2 修复空 buffer 采样；40 个 microduck STL + 球资产为 git-LFS 指针，经 media.githubusercontent.com 逐一拉取并 SHA256 校验 → scratch smoke 训练 → ONNX 导出（parity 2.38e-07） 06 梯面 缺 getup 模型与场景 + notebook 600s 超时 导出 official_ladder_getup.opset11.onnx（opset11）并补齐 desk-climb 场景；notebook cell timeout=600→3600；standalone 先行录制验证 30s episode 可在 ~16 分钟完成 08 LightNav 模型服务不可用 克隆 LightNav-0（9.6GB 权重，hf-mirror 直下）；lightnav-0 env 修 torch 2.10.0+cu128 + torchvision 0.25.0+cu128（vllm 0.19.1 ABI 匹配）；关键坑：run_notebook.py 曾把内核 http_proxy 指向本地 7890 代理，websocket CONNECT 隧道被破坏 → 移除代理注入后 3 场景全部 model_stop 09 跨缝 外网下载 + 目录权限 hf-mirror 429 限流 → 本机下载后 scp（S

**结论 / 做法**
李老师，收到。先做三件事摸清现状：① 打开你的站点看实际内容；② 找到“凯源”的鸭子数据仓库做对标；③ 确认双卡环境。先并行探测：

**结论 / 做法**
网站现状已经摸清：它是个 FastAPI + SQLite 的验收报告站，10 本 Notebook、12 段 GPU 视频、parity 验证全都在；报告里自己也承认 **06 梯面攀爬“每次起爬约 1–3 踏后失稳滑落”**，这就是你说的“不够优秀”。现在找“凯源”的鸭子仓库做对标：

**结论 / 做法**
网站内容已确认（10 本 Notebook / 12 段视频 / parity 全过），自认短板是 06 爬梯“1–3 踏失稳”。“凯源”没直接搜到，先放大你的截图找线索：

**结论 / 做法**
截图确认了站点已上线（120s 视频 16 条、第八章 7 条具身成片在线）。但没出现“凯源”的具体地址。先按仓库特征在 GitHub 上找，同时定位站点源码：

**结论 / 做法**
两个本地仓库都指向 `lemonbaby2/-123`。站点源码在 `robot_portal` 或 `robot-public-site`，先确认哪个对应 microduck-mujoco.app.workbuddy.host，同时再精准搜一轮“凯源”的仓库：

**结论 / 做法**
双卡确认：**GPU0 RTX 4060 8GB + GPU1 RTX 5060 Ti 16GB** —— 这就是你说的两张卡。查站点部署配置：

**结论 / 做法**
GitHub 上没找到明确叫“凯源”的仓库（用户搜出 843 个同名，但没有 microduck 关联）。先定位站点源码，再一起向你确认对标对象：

**结论 / 做法**
站点 API 正常（24 段视频、16 段 ≥120s、15 份 validation）。源码不在本工作区，先确认 DGX 通道与双卡可用性：

**结论 / 做法**
双卡可用（4060 8GB sm_89 + 5060 Ti 16GB sm_120，torch 2.9.1+cu128），DGX 当前全部离线。再定位 microduck-mujoco 站的源码目录：

**结论 / 做法**
本机范围内确实没有这个 FastAPI 站的源码（只有一个 `双卡VLA训练实验台` 的 .wbapp）。再精准搜一次“凯源”可能对应的中文仓库，然后向你确认：

**结论 / 做法**
诊断完成，先给结论，再确认三个必须的信息。 ## 一、网站现状（客观数据） | 维度 | 现状 | 判定 | |---|---|---| | Notebook | 00–09 共 10 本，9 本成功，07 无板标记 `not_run_no_board` | ✅ | | 视频 | 24 段，16 段 ≥120s，总时长 2008s | ✅ | | 数值验收 | 15 份 validation，parity 1e-7~1e-6（容差 1e-4） | ✅ | | API | `/api/health` 24 视频、`/api/tasks` 10 任务结构完整 | ✅ | ## 二、两处真正的硬伤（不是包装问题） | 任务 | 问题 | 证据 | |---|---|---| | **06 梯面攀爬** | 官方 climber 权重每次起爬 **1–3 踏就失稳滑落**，120s 视频是“多次真实起爬剪辑”，不是一次登顶 | 站点报告“已知限制”原文承认 | | **01 篮球平衡** | 只有 1500 步、parity 1.19e-06，**缺官方 README 要求的四项评测**：生存率、首次摔倒时间、速度跟踪误差、action-change RMS；也没有多 seed | 官方 `experiments/basketball/README.md` 的评测清单 | 这两项恰好就是你说的“不够优秀”——判断成立，不是错觉。 ## 三、环境实测结果 - **双卡可用**：GPU0 RTX 4060 8GB（sm_89）+ GPU1 RTX 5060 Ti 16GB（sm_120），torch 2.9.1+cu128 能同时看到两张卡 ✅ - **DGX 全部离线**：<INTERNAL_IP>.217 / .133 / Tailscale 100.100.1.14 均 ping 不通 ❌ - **站点源码不在本机**：`microduck-mujoco.app.workbuddy.host` 的 FastAPI 源码没找到，本机 `.wbapp` 只有“双卡VLA训练实验台”（指向

**结论 / 做法**
明白了——“凯源”就是你自己，对标基准是你 GitHub 上已有数据，目标是做出更强的版本。执行方案定了： - **GPU0 (4060)** → 01 篮球平衡完整评测 - **GPU1 (5060 Ti)** → 06 梯面攀爬冲完整登顶 - **重建 FastAPI 站并上线** 先检查环境底子（WSL 双卡可见性、playground venv、爬梯模型是否齐）：

**结论 / 做法**
WSL 双卡都可见 ✅，但 venv 是空的（上次 uv sync 被 WSL 崩溃打断）。重新启动安装（缓存已热），同时查爬梯资产位置：

**结论 / 做法**
WSL 里这些 CUDA 包（torch 858M + cudnn 674M + cublas 567M）反复重下，说明缓存没命中、网络很慢。本机 Windows 的 venv 已经完整且双卡可用——优先验证 Windows 直跑，别在 WSL 上耗时间：

**结论 / 做法**
Windows venv 完整（torch 2.9.1+cu128、mujoco_warp 3.8.1、warp 1.12.0 全 OK）。实测 CUDA 物理能不能跑（之前 README 说 builtin.h 失败）：

**结论 / 做法**
确认了：Windows venv 里**没有 basketball 任务**（只有 Ladder/BallKick），官方 `Vottivott/microduck-playground` 的 basketball env 必须单独拉。先稀疏克隆官方仓库，同时查爬梯模型：

**结论 / 做法**
官方仓库带 `eval_basketball_checkpoint.py` / `eval_basketball_long.py` / `finetune_basketball.py`——正是 01 的评测入口。先验证官方 src 能否在现有 venv 里注册 basketball 任务：

**结论 / 做法**
官方 `eval_basketball_checkpoint.py` 正好输出三项硬指标（生存率 / 首摔时间 / 前向跟踪误差）。看完整用法后立刻开跑：

**结论 / 做法**
开跑 01（GPU0，512 env × 60s，官方口径 `MICRODUCK_BB_CMD_SCALE=2`），同时读爬梯模型清单：

**结论 / 做法**
复现了你说过的坑：**MuJoCo 在含中文的 Windows 路径下 `ParseXML: Error opening file`**。解决办法：把官方仓库搬到纯 ASCII 路径 `E:\microduck\`，用 uv 复用缓存重建 venv（不重新下载）：

**结论 / 做法**
爬梯四个模型已下齐（大小与 models.json 完全一致）。在 ASCII 路径重建 venv（复用 uv 缓存），并校验模型 SHA256：

**结论 / 做法**
uv sync 完成、爬梯模型 SHA256 全部 MATCH ✅。把篮球 checkpoint 复制到 ASCII 路径，开跑 01（GPU0）：

**结论 / 做法**
新 venv 的 torch 是 CPU 版（PyPI 默认）。最快的解法：把已验证的 CUDA venv 整体复制到 ASCII 路径（同盘复制，比重新下 2.5GB 快）：

**结论 / 做法**
5.4GB 复制了 12 分钟还没完（E 盘慢）。改用 Windows junction（零复制，路径即 ASCII），先看进度再决定：

**结论 / 做法**
venv 验证通过：**torch 2.9.1+cu128、RTX 4060、mjlab 路径已是 ASCII** ✅。跑 01 评测：

**结论 / 做法**
🎉 **01 跑通了，CUDA 物理在 Windows 上正常工作**（之前是路径问题不是 GPU 问题）： | 指标 | 本次（seed A, 512 env × 60s） | 官方 README 本地复核 | |---|---|---| | 生存率 | **97.66%** | 98.83% | | 首次摔倒时间 | 28.48 s | — | | 前向跟踪误差 | **0.156 m/s** | 0.112 m/s | 差距确认。现在把爬梯模型就位并启动 GPU1，同时跑 01 的第二个 seed：

**结论 / 做法**
06 重新在跑。同时跑 01 的详细指标版（含 action-change RMS / tilt / offset / 球速）：

**结论 / 做法**
01 的六项指标已拿到（60s 生存率 96.09%、前向 MAE 0.157、横向 0.109、tilt 2.3°、offset 9.6mm、action RMS 0.234）。06 还在跑。开始搭站：先把原站视频与验收资源镜像到本地：

**结论 / 做法**
06 还在跑（desk-climb 60s 单次约 16–30 分钟）。趁这时间写站点前端（动态读 API，新数据自动上屏）：

**结论 / 做法**
52/64 爬到 31 踏（已过 27 踏顶部），但全部 fallen —— **不是爬不上去，是登桌后站不住**。查交接事件：

**结论 / 做法**
交接在 10.2–11.1s 触发（52 个 env），但结束时间均值 10.4s——**交接后 0–2 秒内就倒**。对比官方 evidence 的基准：

**结论 / 做法**
**关键发现：我的结果与官方 evidence 几乎完全一致**——官方自己也是 `survivors 0/64`、52–53 个 env 爬到 31 踏、均值 10.41s。所以不是“我们更差”，而是旧网站把“登顶后站不住”错误表述成“1–3 踏就失稳”。看官方真正的成功口径：

**结论 / 做法**
`actions.npz` 里有每步 `standing_safe` —— 这才是官方“站立成功”的口径。计算 06 的真实站立指标：

**结论 / 做法**
06 真实结果：**22/64（34.4%）最终站在桌上 ≥10s，最长 47.7s**；52/64 爬到 31 踏顶部。官方基准 105/256（41%），同量级。生成 06 验收 JSON：

**结论 / 做法**
01/06 的 v2 数据齐了（06：31.25% 站住 ≥10s、最长 47.66s、52/64 爬到 31 踏）。重启站点加载新数据并验证：

**结论 / 做法**
部署失败原因：`$PORT` 在启动命令里没被展开（uvicorn 收到空的 `--port`）。改成固定 3000（沙箱实际探测端口）重发：

**结论 / 做法**
李老师，做完了。**站点已重建上线，双卡也真跑起来了**。 ## 一、站点（已发布，验证通过） **https://vla-slam-dual-gpu-lab.app.workbuddy.host/?sharecode=ZNRNC7O5LE** **前往「设置—数据管理—应用」中管理** 线上实测：`/api/health` 返回 ok、10 个任务、21 段视频、9 段 ≥120s（总 1168s）、2 份新验收 JSON。前端动态读 API，01 六项指标表 + 06 站立指标表 + 视频网格都正常渲染。 ## 二、双卡实测结果（这次是真跑，不是剪辑凑数） | 任务 | 卡 | 关键结果 | 对标 | 判定 | |---|---|---|---|---| | **01 篮球** | RTX 4060 8GB | 60s 生存率 **96.09%**；首摔 31.28s；前向 MAE **0.156 m/s**；横向 0.109；tilt 0.040 rad；offset 9.6mm；action RMS 0.234 | 官方 98.83% / 0.112 m/s | 🟡 跟踪精度差约 40% | | **06 爬梯** | RTX 5060 Ti 16GB | 52/64 爬到 **31 踏**（顶部 27 踏之上）；交接 52 次；**31.25% 站住 ≥10s**；最长 **47.66s** | 官方 105/256 = 41.0% | 🟡 同量级，样本偏小 | ## 三、两个必须纠正的结论 1. **旧站“1–3 踏就失稳”是错的。** 真实情况是：52/64 都爬到了 31 踏顶部并触发交接，卡在**登桌后的站立阶段**。而且我的 `survivors 0/64` 与官方 evidence 的 `0/64` **完全一致**——不是我们更差。 2. **之前跑不动不是显卡问题，是中文路径。** MuJoCo 在 `E:\研究生学习\黑客松\...` 下直接 `ParseXML: Error opening file`。把仓库+venv 搬到 `E:\mic
