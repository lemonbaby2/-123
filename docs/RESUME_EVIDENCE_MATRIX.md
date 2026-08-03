# 简历证据映射与公开边界

本页回答三个问题：简历写了什么、仓库能够证明什么、还需要什么条件才能复现原始结果。

| 简历条目 | 简历陈述 | 仓库公开证据 | 未公开/待实机验证 |
|---|---|---|---|
| 人工智能讲师/四足机器人 | ROS2+Gazebo/实机；CUDA 点云与 ICP；LOAM+IMU；视觉回环；任务决策 | `quadruped.py` 的预积分、体素滤波、ICP、回环和决策接口；ROS2 骨架；项目设计 | 原机器人代码、赛事材料、Vicon 轨迹、CUDA kernel、100 h 日志 |
| Ginger 机器人 | CCU 调试、SSH/ROS/导航/地图/运动闭环；Web 平台；TensorRT 压缩 | `ginger.py` 的分层诊断、导航门控、rosbridge 协议消息和 mock 状态；接口文档 | 厂商 CCU API、真实 IP/凭据、原网页、模型/数据、Jetson 测试日志 |
| GeoScan Pro | LiDAR/IMU/RTK/视觉融合；LIO-SAM/GTSAM/iSAM2；USB-CDC | `geoscan.py` 的增量 2D 图优化、传感器质量门控、CRC 帧；系统架构 | 产品 CAD/BOM、专利细节、原始 bag/标定、真实 RTK 基线和带宽测试 |
| 工业质检 | YOLO11 P2；LSTM+R-CNN；TensorRT INT8；小缺陷与电机预测 | `vision.py` 的 P2 配置验证、指标计算、时序风险评分和对称 INT8 模拟 | 工厂图像/标签、缺陷定义、模型结构/权重、相机标定、量产统计 |
| ROS2+3DGS | Lego Gaussian 场景接入 RViz2；topic/frame/TF/时序排查 | `gaussian_viz.py` 的 PLY 解析、MarkerArray 批处理与时序检查；ROS2 节点骨架 | 原始 Lego 资产、12 秒视频、原工作区、Isaac Sim 集成 |
| STM32 BMS | Bi-LSTM 蒸馏、剪枝/QAT、C 推理、FreeRTOS、AEKF、主动均衡 | `bms.py` 的 Thevenin+AEKF+均衡；C++ 固定内存参考；任务预算配置 | 电芯测试数据、教师模型、STM32 工程/链接脚本、HIL 结果、ISO 26262 安全案例 |
| 3 项已受理专利 | 简历列出三个名称 | 仅列名称、状态与技术主题 | 申请号、权利要求、说明书（除非权利人确认可公开） |
| Dy3DGS-SLAM 在投论文 | 简历列出题目及“中科院一区·在投” | 提供非论文式架构说明和公开相关工作索引 | 原稿、实验、审稿状态、数据和代码（投稿政策/作者一致同意后） |

## 指标标签

- **简历报告值**：来源于候选人简历，仓库未独立验证。
- **演示测试值**：由合成数据和本仓库代码产生，只验证实现逻辑。
- **实机复现值**：需要固定硬件、软件、数据、标定和评测协议后重新测量。

任何公开介绍、面试幻灯或二次引用都应保留上述标签。
