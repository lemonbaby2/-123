# 具身智能技术对话摘录

> 来源：本人 2025-09 至 2026-10 期间与 AI 结对编程助手的实际工作对话，覆盖 141 个会话。
> 本目录筛选出其中 **8 个与具身智能 / 机器人 / 仿真直接相关**的会话，做了脱敏与结构化整理。

## 为什么收录这个目录

这些不是"聊过什么"的流水账，而是**工程决策的现场记录**——每次踩坑、每个报错根因、每次方案被推翻重来的判断依据。相比结果性的 README，它更能说明问题是怎么被定位的。

## 脱敏规则

| 处理 | 内容 |
|---|---|
| 替换为占位符 | SSH 账号/密码、代理凭据、内网 IPv4、公网入口 IP、主机名、手机号、邮箱、网盘分享链接与提取码 |
| 删除 | 工具调用原始输出、系统提示注入、大段日志回显 |
| 保留 | 技术判断、报错根因、参数取值、架构取舍、验证数据 |
| 不收录 | 教学备课、兼职授课、求职投递、企业产线 SOP（含客户信息）等与具身智能无关的会话 |

**占位符对照**：`<ROBOT_HOST>` 真机 IP ｜ `<ROBOT_USER>` / `<ROBOT_PASSWORD>` 登录凭据 ｜ `<PROXY_HOST>` / `<PROXY_USER>` / `<PROXY_PASSWORD>` 内网代理 ｜ `<ARM_HOST>` 机械臂 IP ｜ `<INTERNAL_IP>` 其余内网地址 ｜ `<PHONE>` / `<EMAIL>` 联系方式 ｜ `<REDACTED>` 其他已打码的值

> 会话中的 ROS 节点名（`bobac3_arm`、`bobac3_hand`）、工作区名（`bobac3_ws`、`bobac_factory`）等工程标识予以保留——它们是技术上下文，不含凭据。

## 索引

| # | 文件 | 主题 | 关键内容 |
|---|---|---|---|
| 01 | [01_robotwin_lingbot_vpn.md](01_robotwin_lingbot_vpn.md) | RoboTwin 2.0 / LingBot-VLA 2.0 参赛准备与内网链路 | 图灵 SOCKS5 认证纠错（PDF 密码有误）、赛事环境探查（Docker `bobac-env`、双 Berxel 相机、RealMan RM-e6）、真机采集方案 |
| 02 | [02_vla_vlm_corpus.md](02_vla_vlm_corpus.md) | VLA / VLM 技术资料全机检索与归档 | 全盘扫描 VLA/VLM 文档、论文、笔记并分类打包 |
| 03 | [03_dual_gpu_and_camera.md](03_dual_gpu_and_camera.md) | 双显卡算力验证与相机链路诊断 | RTX 4060 + 5060 Ti 算力/显存/功耗实测、`sm_120` 需 CUDA 12.8+、Berxel + UVC 相机枚举 |
| 04 | [04_microduck_task1.md](04_microduck_task1.md) | MicroDuck 组队学习 Task1 | 篮球平衡 PPO → ONNX → BPU → MuJoCo 全链，与参考实现的差距分析 |
| 05 | [05_competition_materials.md](05_competition_materials.md) | 算力券申请与参赛技术材料 | 天池算力券流程、GitHub 机器人项目盘点、团队简介撰写 |
| 06 | [06_ros2_sim_stack.md](06_ros2_sim_stack.md) | ROS2 机械臂 / SLAM / 感知仿真环境核验 | 虚拟机内仿真库与机械臂、SLAM、感知包的完整性检查 |
| 07 | [07_ros2_humble_setup.md](07_ros2_humble_setup.md) | Ubuntu 22.04 + ROS2 Humble 环境搭建 | 安装链路与依赖处理 |
| 08 | [08_ros2_practice.md](08_ros2_practice.md) | ROS2 实训与排错 | 节点/话题/编译问题定位 |

## 怎么读

- **想看工程判断力**：读 01。里面有"PDF 文档写的密码是错的，实测返回 `01 01` 失败、`01 00` 通过"这类只有真跑过才知道的细节。
- **想看踩坑能力**：读 02 和 03。`torch.cuda.device_count()=0` 一路查到"所有 venv 里装的都是 `+cpu` 版本"、`sm_120` 编译不过一路查到 CUDA Toolkit 版本。
- **想看完整链路**：读 04。从 PPO 训练到 ONNX 导出到板端推理到 MuJoCo 回放。

## 声明

本目录为个人工作记录摘录，已删除所有可识别第三方（雇主、客户、同事、学生）的信息。若发现仍有遗漏的敏感内容，请提 issue，会立即修正。
