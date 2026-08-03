# ROS2、山猫 S10 与 Isaac Lab 接入方案

## 当前状态

`integration/ros2_interface.yaml` 和 `isaac_lab_terrain_curriculum.yaml` 是经过工程约束设计的接口草案，但尚未在 ROS2、Isaac Lab 或 S10 上执行。供应商消息名、控制模式和安全限制必须在获得官方 SDK 后核对。

## ROS2 组件

建议包划分：

```text
gausspatrol_bringup      launch、参数、生命周期编排
gausspatrol_localization LIO wrapper、健康状态
gausspatrol_perception   动态体/缺陷 detector、跟踪
gausspatrol_mission      BT/状态机、点位验证
gausspatrol_control      地形限速、安全门控、S10 adapter
gausspatrol_mapping      点云、3DGS 异步任务、报告索引
gausspatrol_msgs         Defect/Event/MissionState 消息
```

传感器驱动和 LIO 使用 composable node 时，要验证 intra-process 与 loaned message 是否真的生效。生命周期启动顺序为驱动→TF/标定→定位→地图/感知→规划→控制；任一必需组件未 active 时控制保持 disabled。

## S10 SDK 待确认项

- 机器人是速度级、姿态级、关节级还是 gait service/action；
- wheel-foot 模式、步态枚举、切换前提和反馈；
- 状态消息频率、时间戳、关节顺序、接触/滑移信息；
- 最大速度、坡度、负载、制动距离和保护区域；
- 急停、watchdog、上电/下电、失联行为；
- URDF、惯量、碰撞体、关节限制和坐标约定。

获得文档前不编造接口。`/s10/gait_command` 只是占位契约。

## Isaac Lab 路线

1. 导入并验证官方/团队 URDF 或 USD，质量与惯量和手册一致；
2. 先复现厂商平地 gait，再训练高层速度/步态策略；
3. 课程从平地、缓坡到碎石、低摩擦和外力扰动；
4. domain randomization 包含摩擦、质量、时延、传感噪声和执行器强度；
5. policy export 后用相同观测归一化和动作限幅；
6. 真机先系留、低速、软保护区，逐项放开；
7. 硬件安全层独立于策略并具有更高优先级。

## 控制责任边界

GaussPatrol 高层只给速度和 gait 意图。底层姿态稳定、关节/轮控制、过流/过温和跌倒保护由厂商控制器或经过认证的低层控制器负责。高层 ML 不得直接绕过急停和硬件限制。

## Bring-up 清单

- 静止检查所有 TF、关节方向、IMU 重力和 LiDAR 外参；
- 抬架检查轮/腿方向、速度符号和急停；
- 0.1 m/s 平地直线，验证 odom 与真值；
- 低速原地转向，确认 stop distance；
- 单传感器断开、控制节点崩溃、网络断开；
- 坡道、碎石、低摩擦逐项测试，不混合增加风险；
- 最后再引入动态人员和完整任务。

## 数据记录

每次测试记录 commit、镜像、参数、SDK/固件、标定 hash、电量、温度、负载、地形、天气、安全员和异常。rosbag2 不得遗漏 `/tf_static`、原始传感器、控制命令、robot state 和事件日志。
