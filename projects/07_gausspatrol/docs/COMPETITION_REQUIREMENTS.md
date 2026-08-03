# GOAI 2026 具身未来赛题要求与 GaussPatrol 映射

## 来源与核对时间

- 用户提供 PDF：`datawhale的具身.pdf`，21 页，2026-08-04 本地读取并逐页渲染核对；
- 赛事页面：<https://www.goaihz.com/tracks?track=embodied&channel=dw9>；
- 手册列出的双臂 X-Eval 资源入口：<https://xsparkai.com/goai-2026/>。

本文件是团队工作摘要，不替代组委会最新通知。网页、群公告、硬件型号、SDK 和日期变化时，以组委会书面说明为准。

## 赛道与时间

手册把具身未来分为双臂操作能力测试和产业园区全地形巡逻挑战。手册中的阶段日期为：

| 阶段 | 手册日期 | 关键交付 |
|---|---|---|
| 报名/初赛材料 | 7 月 16 日至 8 月 20 日 | 项目简介、技术方案、Demo（可选/推荐）、代码仓库链接 |
| 初赛评审 | 8 月 21 日至 23 日 | 完整性、技术方案、Demo、开源材料 |
| 决赛线下调试准备 | 8 月 25 日至 9 月 20 日 | 实机调试、测试报告、最终代码和材料 |
| 总决赛 | 9 月 22 日至 23 日 | 现场演示、答辩、最终提交 |

## 产业园区赛题核心任务

手册描述的能力包括复杂地形通过、多任务巡逻、路径规划、任务调度、感知融合与实时定位。环境包含坡道、碎石/楼梯、湿滑路面、未知障碍和动态干扰。队伍需要在规定点位完成任务并尽量缩短总时间。

手册提到以山猫 S10 机器人作为巡逻赛题参考平台，并说明入围队伍可获得产品手册、二次开发接口和答疑支持。由于当前仓库没有这些受控资料，所有 `/s10/*` 消息名均标为待 SDK 核对。

## 计分理解

手册的巡逻决赛说明以“任务完成时间 × 模式系数”为核心；在完成全部点位前提下时间越低越好。模式系数表中，人工操作为 1.0，自主跟随为 1.3，自主导航为 1.4。另有一处页脚文字写成除以 1.2/1.0，和后续正式表格并不完全一致，因此本项目不自行断言最终公式，赛前必须向组委会确认。

没有完成全部点位、偏离指定路线、违反安全规则或出现碰撞会影响排名或判罚。GaussPatrol 因此优先记录完成率、碰撞、避障、任务时间和自主控制状态，而不是只展示地图。

## 初赛材料映射

| 要求 | GaussPatrol 文件 |
|---|---|
| 项目简介 | [`../submission/PROJECT_BRIEF.md`](../submission/PROJECT_BRIEF.md) |
| 技术方案 | [`TECHNICAL_PROPOSAL.md`](TECHNICAL_PROPOSAL.md) 与生成 PDF |
| 开源协议说明 | [`DATA_LICENSE_AND_REFERENCES.md`](DATA_LICENSE_AND_REFERENCES.md) |
| Demo | `python ../run_demo.py --output ../artifacts/local_run` |
| GitHub 链接 | 仓库 `projects/07_gausspatrol` 目录 |

## 复赛材料映射

| 要求 | GaussPatrol 文件 |
|---|---|
| 可运行 Demo | `run_demo.py`、固定场景配置、样例产物 |
| 代码仓库 | `src/gausspatrol`、独立测试 |
| 技术文档 | `docs/TECHNICAL_PROPOSAL.md` |
| 评测结果 | `artifacts/sample_run/metrics.json`、`RUN_REPORT.md` |
| 资源使用说明 | `DATA_LICENSE_AND_REFERENCES.md` |
| 复现步骤 | README 快速开始和 `EVALUATION_PROTOCOL.md` |

## 尚未满足的真机条件

- 山猫 S10 产品手册、URDF、SDK、控制/状态消息定义；
- 现场任务地图、点位、起终点、安全边界和最终计分公式；
- 真机 LiDAR/IMU/RGB-D 标定与 rosbag；
- Isaac Lab 可用 robot asset 与可控关节/轮足接口；
- 真实设备缺陷类别、数据许可和标注规范；
- 现场网络、算力、电源、防护和急停流程。

这些条件未补齐前，仓库只能作为工程基线和比赛准备材料，不能宣称已经完成官方赛题验收。
