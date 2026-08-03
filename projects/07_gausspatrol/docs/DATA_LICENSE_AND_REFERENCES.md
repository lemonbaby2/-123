# 数据、开源、模型与参考资料说明

## 仓库自有内容

- `config/default_scenario.json`：人工设计的合成园区；
- `artifacts/sample_run/*`：由本仓库代码生成；
- `src/gausspatrol/*`：clean-room 标准库实现；
- 没有客户数据、人脸、真实园区图像、厂商 SDK、模型权重或比赛受控数据。

原创代码沿用仓库 MIT License。合成配置与生成报告可随仓库使用；引用本项目时建议附 commit 和 seed。

## 计划使用但未随仓库分发的上游

| 项目 | 用途 | 采用前必须核对 |
|---|---|---|
| [LIO-SAM](https://github.com/TixiaoShan/LIO-SAM) | LiDAR-IMU 定位 | 许可证、ROS 版本、传感器要求 |
| [FAST-LIVO2](https://github.com/hku-mars/FAST-LIVO2) | LiDAR-IMU-视觉定位 | 许可证、相机/LiDAR 支持、算力 |
| [Navigation2](https://github.com/ros-navigation/navigation2) | 任务/全局/局部导航 | Apache-2.0、插件配置 |
| [Isaac Lab](https://github.com/isaac-sim/IsaacLab) | 地形控制训练 | BSD-3-Clause、Isaac Sim 条款、asset 权利 |
| [Ultralytics](https://github.com/ultralytics/ultralytics) | 缺陷/动态体检测候选 | AGPL-3.0 或企业许可、模型/data 许可 |
| [3D Gaussian Splatting](https://github.com/graphdeco-inria/gaussian-splatting) | 场景重建候选 | 官方研究许可和商业限制 |

本仓库没有复制这些项目代码。比赛最终开源时，应把真正采用的依赖、commit、修改、许可证文本和模型来源写入 SBOM/NOTICE。

## 真实数据治理

- 采集前确认园区、设备、人员和场地授权；
- 人员图像尽量现场脱敏或不落盘；
- 训练、验证、测试按场地/设备/日期拆分；
- 标注保存指南版本、人员、复核和争议样本；
- 数据集卡记录用途、限制、地理/天气分布和删除机制；
- 比赛平台/厂商数据只按条款使用，不上传公开仓库。

## API 与云服务

当前代码不调用商业 API。若以后使用云模型或地图服务，要记录供应商、地区、价格、速率限制、数据保留和离线 fallback。安全控制不得依赖公网 API。

## 比赛材料

用户提供的比赛 PDF 只用于理解规则，未复制进公开仓库。项目内是团队自行编写的摘要，并链接官方赛事页面。若组委会授权公开原手册，可另行添加原始文件与来源说明。
