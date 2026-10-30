# 具身智能工程档案（embodied-ai）

这个目录把散落在三处的东西收进同一个可检索结构：**简历里写的项目**、**实际跑过的实验数据**、**与 AI 结对工作时的原始讨论**。

三者分开存放，是因为它们的证据强度不同：

| 目录 | 是什么 | 证据强度 |
|---|---|---|
| [`resume/`](resume/) + [`RESUME_2026_FULL.md`](RESUME_2026_FULL.md) | 2026 版求职简历原件与逐字转录 | 声明（claim），不是证据 |
| [`experiments/`](experiments/) | DGX 上真实跑出的训练曲线与测速 JSON | 可重跑的实测数据 |
| [`dialogues/`](dialogues/) | 与 AI 结对开发过程中的 33 个会话档案 | 过程记录，说明思路怎么来的 |
| [`papers/`](papers/) | 由上述实验数据生成的投稿稿 | 二次产物 |

**不把声明混进证据里。** 简历写的 2.07 m/s 也好、92.5% 成功率也好，都只是声明；只有 `experiments/` 下带 JSON 的数字才当实测看。

---

## 一、简历全文（含全部项目）

- [`RESUME_2026_FULL.md`](RESUME_2026_FULL.md) —— 3 页 PDF 的逐字转录：4 段工作经历、6 段项目经历、6 类技能，外加**每条简历条目到仓库目录的映射表**（标明哪部分可验证、哪部分未公开）。
- [`resume/2026_李梓鹏_具身智能机器人简历.pdf`](resume/2026_李梓鹏_具身智能机器人简历.pdf) —— 原件。

映射表同时列出原稿的 4 处待修问题（日期倒挂、学历分段、成果重复、联系方式公开），投递前需要处理。

## 二、实验档案：MicroDuck 短跑策略

[`experiments/microduck_sprint/`](experiments/microduck_sprint/)

DGX Spark 上用 mjlab（MuJoCo Warp）+ rsl_rl PPO 训双足机器鸭，4096 并行环境。核心结果（同 checkpoint 序号、同命令、同测速协议）：

| 指标 | v1（奖励失衡） | v2（调优后） | 倍数 |
|---|---|---|---|
| 平均前进速度 | 0.1481 m/s | **0.4572 m/s** | **3.09×** |
| 中位数 | 0.1539 | 0.4560 | 2.96× |
| P95 | 0.2058 | 0.6988 | 3.39× |
| 单帧峰值 | 0.2507 | 0.9335 | 3.72× |

两条结论：

1. **奖励权重决定"愿不愿意跑快"**。v1 把腾空奖励给到 5.0，策略立刻学会站着踮脚刷分——回合奖励涨到 49.36、回合长度顶满 600 步（从不跌倒），速度反而从 0.135 掉到 0.091 m/s。奖励分项里 `air_time` 贡献 4.45，速度追踪只有 0.45。
2. **命令覆盖决定"能不能跑快"**。同一个 v2 检查点，把测速命令从 1.6 抬到 2.6（超出训练分布），速度反而掉到 0.1797 m/s（−61%）。这条比第 1 条更硬：奖励只决定意愿，命令分布决定上限。

目录内含 6 份 JSON 原始数据、5 张图、2 个生成脚本，以及复现命令。

> 边界：**没有达到社区公开的 2.07 m/s**。当前只训到 250 迭代，硬件是统一内存的 GB10 而非 4090D，测速口径也不同。可比的是 v1↔v2 这组除配方外完全同条件的对照。

## 三、对话档案：33 个会话

[`dialogues/INDEX.md`](dialogues/INDEX.md)

从本机 WorkBuddy 会话记录（304 个有效会话）里按关键词筛出与具身智能相关的 33 个（2026-08 至 2026-10），每个会话一个文件，只保留**用户提问 + 助手结论**。

主题分布：

| 主题 | 会话数 |
|---|---|
| 世界模型 / Real2Sim | 22 |
| DGX / 算力 | 18 |
| VLA（视觉-语言-动作） | 15 |
| 强化学习与运动控制 | 10 |
| VLM（视觉语言模型） | 9 |
| SLAM / 三维重建 | 7 |
| 工业视觉 / SOP | 4 |
| 边缘部署 | 2 |

> 同一会话可计入多个主题，标签取命中数最高的三项。

抽取口径写在 [`../tools/extract_dialogues.py`](../tools/extract_dialogues.py) 里，可重跑：

```bash
python tools/extract_dialogues.py --scan                                    # 只统计
python tools/extract_dialogues.py --emit embodied-ai/dialogues --min-score 6  # 生成档案
```

判定规则：

1. 只看**用户提问**（不看工具输出），避免长会话靠"提得多"刷分；
2. 同一关键词只计一次；
3. 必须在核心主题（VLA / VLM / 世界模型 / 强化学习 / SLAM）上累计命中 ≥2 个强关键词；
4. 运维、磁盘清理、课件制作这类"顺带提到关键词"的会话按标题正则排除。

被排除的典型：`清理C D E盘并保障虚拟机运行空间`、`安装 opencv 与 numpy 依赖`、`生成AI课件面试演讲稿`。

## 四、论文

[`papers/MicroDuck短跑策略_Real2Sim2Real_双栏投稿稿.docx`](papers/)

基于 `experiments/` 的真实数据生成的双栏投稿稿（A4 双栏、宋体 + Times New Roman、4 表 5 图 13 式）。数据更新后由 `experiments/microduck_sprint/scripts/` 下两个脚本重新生成，不需要手改数字。

---

## 隐私与脱敏

`dialogues/` 里所有内容经过自动脱敏，规则见 `tools/extract_dialogues.py` 的 `SCRUB` 表：

| 类型 | 处理 |
|---|---|
| IPv4 地址（含内网段） | → `<IP>` |
| 主机名（DGX / 本机） | → `<DGX-HOST>` / `<PC-HOST>` |
| 账号密码 | → `<REDACTED>` |
| Git / API token | → `<TOKEN>` |
| 本机用户名与家目录 | → `<USER>` |
| 手机号 / 邮箱 / 微信号 | → `<PHONE>` / `<EMAIL>` / `<WXID>` |

已用 grep 复核：IPv4、手机号、邮箱、wxid、token 均无残留。

**仍然保留的内容**：公司名（求职简历本就公开）、技术栈、指标、失败归因。原始会话记录、工具调用输出、生产系统凭据、客户数据**不在本仓库**。

`RESUME_2026_FULL.md` 保留了简历上的电话与邮箱（求职材料本身就要公开联系方式）。如果不想被爬虫抓取，删掉该文件「一、基本信息」表格里这两行即可，PDF 原件不受影响。

## 目录结构

```text
embodied-ai/
├── README.md                    本文件
├── RESUME_2026_FULL.md          简历逐字转录 + 仓库映射
├── resume/
│   └── 2026_李梓鹏_具身智能机器人简历.pdf
├── experiments/
│   └── microduck_sprint/
│       ├── README.md            配方差异、实测结果、复现命令
│       ├── data/                6 份 JSON（训练曲线 + 测速）
│       ├── figs/                5 张图
│       └── scripts/             make_figs.py / build_paper.py
├── dialogues/
│   ├── INDEX.md                 会话索引与主题分布
│   └── sessions/                33 个会话档案
└── papers/
    └── MicroDuck短跑策略_Real2Sim2Real_双栏投稿稿.docx
```
