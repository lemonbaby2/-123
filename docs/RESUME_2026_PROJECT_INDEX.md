# 2026 简历项目：源码与结果索引

更新日期：2026-10-12。这里的“可复现”仅表示公开仓库中的演示命令可运行，不代表简历中的实机指标已经独立复测。所有数值应按[简历证据映射](RESUME_EVIDENCE_MATRIX.md)所述口径解释。

| 简历方向 | 公开代码或资料 | 结果状态 |
| --- | --- | --- |
| 四足机器人 SLAM 与点云优化 | [独立演示](../projects/01_quadruped_slam/) | 单元测试和合成输入演示可运行；原 ROS2/CUDA 工程、Vicon 与长稳日志未公开 |
| Ginger 服务机器人 VLM/VLA 控制 | [协议与安全门控演示](../projects/02_ginger_robot/) | Mock 接口演示可运行；不等同于厂商 CCU 或实机结果 |
| GeoScan Pro 多传感器扫描仪 | [协议/因子图演示](../projects/03_geoscan_pro/) · [软硬件归档](../projects/08_3dgs_scanner_soft_hardware/) | 模拟数据和部分设计文档可查；完整固件、标定与实测原始数据未公开 |
| 工业视觉质检 | [指标与量化演示](../projects/04_industrial_vision/) | 合成输入可运行；产线图像、权重和 TensorRT 实机基准未公开 |
| 世界模型、动作条件预测与 Real2Sim | 暂无对应的原创公开工程 | 原始训练代码、数据和简历所述预测/PSNR 评测输出尚未提供，不把参考论文当作个人结果 |
| VLA 语言指令操作 | [VLA/VLM 工程演示](../vla_vlm_projects/) | 两个 dry-run 项目有源码和测试；1000+ 轨迹、92.5% 实机抓放及端侧延迟数据未公开 |
| VLM 工业 SOP 理解 | [宁波 SOP 源码分支](https://github.com/lemonbaby2/-123/tree/sop-public-cvat-roundtrip-20260825) | 平台源码及部分验收文档已公开；简历中的召回率与幻觉率缺少可公开的同口径复测数据 |
| ROS2 + 3DGS Lego 可视化 | [PLY/ROS2 演示](../projects/05_ros2_3dgs/) | 自制样例可运行；原 Lego 资产和录屏未公开 |
| STM32-FreeRTOS BMS | [AEKF/均衡演示](../projects/06_bms/) · [硬件文档](../projects/08_3dgs_scanner_soft_hardware/) | 模拟测试可运行；原 MCU 工程和 HIL 结果未公开 |
| 宁波螺钉装配 SOP/MES | [2026-08-25 平台源码分支](https://github.com/lemonbaby2/-123/tree/sop-public-cvat-roundtrip-20260825) · [紧固件检测仓库](https://github.com/lemonbaby2/ai-fastener-inspection) | 已有公开代码及部分验收报告；原始车间视频、生产凭据、数据库与未复核标签不在公开代码中 |
| GaussPatrol 巡检仿真 | [独立项目与模拟产物](../projects/07_gausspatrol/) | 仿真代码、测试与产物可重复；实机性能未据此证明 |

## 本地快速验证

在仓库根目录运行：

```bash
python scripts/verify_layout.py
python scripts/run_tests.py
python scripts/run_all_demos.py
python vla_vlm_projects/run_tests.py
python vla_vlm_projects/run_all_demos.py
```

SOP 代码保存在不同 Git 分支中。阅读该分支的 `README.md`、`.gitignore` 和项目说明后再运行；设备地址、授权、数据和模型须由实际部署环境提供。公开仓库没有证明简历中的所有实机指标，也没有为缺失的原始结果生成替代数据。
