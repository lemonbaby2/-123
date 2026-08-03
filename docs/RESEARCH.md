# 研究论文、官方文档与开源资料索引

检索日期：2026-08-03。优先列作者论文、官方文档和原作者仓库。此处只提供链接、用途与许可证提醒，不镜像论文 PDF 或第三方源码。

## 1. SLAM、点云与多传感器融合

| 资料 | 用途 | 代码/许可提示 |
|---|---|---|
| [LOAM: Lidar Odometry and Mapping in Real-time](https://www.ri.cmu.edu/pub_files/2014/7/Ji_LidarMapping_RSS2014_v8.pdf) | LiDAR 里程计与低频建图双线程基线 | 论文方法；确认具体实现仓库许可 |
| [LIO-SAM paper](https://arxiv.org/abs/2007.00258) / [official repository](https://github.com/TixiaoShan/LIO-SAM) | LiDAR-IMU 紧耦合、去畸变、因子图 | BSD-3-Clause；原仓库主线为 ROS1，并提供 ROS2 分支 |
| [GTSAM documentation](https://gtsam.org/docs/) / [iSAM2 API](https://gtsam.org/doxygen/a04947.html) | 增量非线性因子图优化 | BSD；前端传感器处理需自行实现 |
| [IMU Preintegration on Manifold](https://arxiv.org/abs/1512.02363) / [GTSAM PIM](https://borglab.github.io/gtsam/preintegratedimumeasurements/) | 将高频 IMU 汇总为关键帧间约束 | 注意坐标系、重力方向、偏置与协方差 |
| [ORB-SLAM3](https://arxiv.org/abs/2007.11898) / [repository](https://github.com/UZ-SLAMLab/ORB_SLAM3) | 单目/双目/RGB-D 与视觉惯性 SLAM | GPL-3.0；与闭源产品组合前需审查 |
| [SuperPoint](https://arxiv.org/abs/1712.07629) | 自监督兴趣点与描述子 | 论文与模型权重可能有不同使用条件 |
| [SuperGlue](https://arxiv.org/abs/1911.11763) / [reference code](https://github.com/magicleap/SuperGluePretrainedNetwork) | 基于注意力/GNN 的局部特征匹配 | 原仓库许可与权重条款需单独核对 |
| [PCL ICP tutorial](https://pointclouds.org/documentation/tutorials/iterative_closest_point.html) | ICP 工程接口与收敛判断 | BSD |

本仓库的 `quadruped.py` 与 `geoscan.py` 是独立教学实现，只复现核心数据流，不复制上述工程代码。

## 2. 3D Gaussian Splatting 与 ROS2 可视化

| 资料 | 用途 | 许可提示 |
|---|---|---|
| [3D Gaussian Splatting paper](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/) | 高斯原语、各向异性协方差和可见性感知 splatting | 论文可读 |
| [GraphDeco reference implementation](https://github.com/graphdeco-inria/gaussian-splatting) | 训练与实时 viewer 参考 | 原许可限制为非商业研究/评估；不是通用 MIT |
| [ROS2 Marker tutorial](https://docs.ros.org/en/rolling/Tutorials/Intermediate/RViz/Marker-Display-types/Marker-Display-types.html) | RViz2 Marker/MarkerArray 与批量绘制 | ROS 文档 |
| [visualization_msgs](https://docs.ros.org/en/jazzy/p/visualization_msgs/) | ROS2 可视化消息定义 | Apache-2.0/BSD 以包为准 |
| [REP-105](https://www.ros.org/reps/rep-0105.html) | `map`/`odom`/`base_link` 坐标约定 | ROS 规范 |

仓库只解析一个自制的小型 ASCII PLY，并输出兼容 MarkerArray 的 JSON 结构；不包含 GraphDeco 源码或 Lego 数据。

## 3. 机器人 Web 控制与边缘部署

| 资料 | 用途 | 许可提示 |
|---|---|---|
| [rosbridge_suite](https://github.com/RobotWebTools/rosbridge_suite) / [ROS2 docs](https://docs.ros.org/en/jazzy/p/rosbridge_suite/) | 通过 WebSocket 以 JSON 访问 ROS topic/service | BSD-3-Clause；生产环境需认证、限流与网络隔离 |
| [Nav2 Map Server](https://docs.nav2.org/configuration/packages/map_server/configuring-map-server.html) | 地图托管与加载请求 | Apache-2.0；版本间参数存在差异 |
| [Nav2 Simple Commander](https://docs.nav2.org/commander_api/index.html) | Python 导航任务接口 | Apache-2.0 |
| [TensorRT best practices](https://docs.nvidia.com/deeplearning/tensorrt/latest/performance/best-practices.html) | 基准、精度、算子与延迟优化闭环 | NVIDIA 文档/SDK 条款 |
| [TensorRT quantization schemes](https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/quantized-types-schemes.html) | INT8 Q/DQ 与误差来源 | 新版 TensorRT 强调显式量化；按实际版本适配 |
| [ONNX Runtime quantization](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html) | 动态/静态量化与调试 | MIT |

## 4. 工业视觉与时序故障预测

| 资料 | 用途 | 许可提示 |
|---|---|---|
| [Ultralytics YOLO11 documentation](https://docs.ultralytics.com/models/yolo11/) | YOLO11 任务、训练、导出与基准 | AGPL-3.0 或企业许可；官方说明没有单独正式论文 |
| [Feature Pyramid Networks](https://arxiv.org/abs/1612.03144) | 多尺度特征与高分辨率层 | 论文方法 |
| [Faster R-CNN](https://arxiv.org/abs/1506.01497) | RPN 与检测头基线 | 论文方法/具体实现许可各异 |
| [Long Short-Term Memory](https://www.bioinf.jku.at/publications/older/2604.pdf) | 时序状态与门控记忆 | 论文方法 |
| [COCO evaluation](https://cocodataset.org/#detection-eval) | AP/AR 指标口径 | 数据集和 API 各有条款 |

## 5. 模型压缩、BMS 与实时系统

| 资料 | 用途 | 许可提示 |
|---|---|---|
| [Distilling the Knowledge in a Neural Network](https://arxiv.org/abs/1503.02531) | 教师-学生软目标蒸馏 | 论文方法 |
| [PyTorch quantization](https://pytorch.org/docs/stable/quantization.html) | PTQ/QAT 与导出 | BSD-style |
| [Adaptive EKF for SOC on STM32](https://arxiv.org/abs/2504.05936) | MCU 上自适应协方差与 SOC 估计 | 论文；本仓库为独立简化实现 |
| [FreeRTOS scheduling](https://www.freertos.org/Documentation/02-Kernel/02-Kernel-features/01-Tasks-and-co-routines/04-Task-scheduling) | 固定优先级抢占与时间片 | MIT；端口/内核版本需锁定 |
| [FreeRTOS queues](https://www.freertos.org/Documentation/02-Kernel/02-Kernel-features/02-Queues-mutexes-and-semaphores/01-Queues) | ISR/任务与任务间通信 | 避免无界阻塞和大对象复制 |
| [ISO 26262 overview](https://www.iso.org/standard/68383.html) | 道路车辆功能安全生命周期 | 标准正文受版权保护；合规需正式流程和证据 |

## 6. 建议公开数据集

- [KITTI Odometry](https://www.cvlibs.net/datasets/kitti/eval_odometry.php)：视觉/LiDAR 里程计；遵循数据条款。
- [EuRoC MAV](https://projects.asl.ethz.ch/datasets/doku.php?id=kmavvisualinertialdatasets)：视觉惯性 SLAM。
- [TUM RGB-D](https://cvg.cit.tum.de/data/datasets/rgbd-dataset)：RGB-D SLAM。
- [MVTec AD](https://www.mvtec.com/company/research/datasets/mvtec-ad)：工业异常检测，注意非商业许可条款。
- [NASA battery datasets](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/)：退化/SOH 研究，核对具体数据说明。

## 7. 许可证使用建议

1. 论文思想、开源实现和模型权重是三个不同的权利对象。
2. 商业产品优先选择 BSD/MIT/Apache-2.0 兼容依赖；GPL/AGPL 或非商业许可证必须由法务审查。
3. 不把第三方仓库整包复制进作品集；使用链接、固定 commit、补丁和 SPDX 清单。
4. 训练数据必须记录来源、授权、隐私处理和保留周期。
