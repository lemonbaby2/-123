# Windows EXE 与 CVAT 服务端完整部署说明

## 1. 交付架构

本交付不是单一网页壳，而是三层结构：

1. Windows 桌面端：本地登录、七段业务导航、相机/视频管理、预标注、CVAT交接、数据集冻结、训练部署、实时SOP和MES结果页。
2. 深度学习运行时：桌面端自动调用 `D:\Anaconda\envs\dl\python.exe`，复用现场 GPU、OpenCV、Ultralytics 和训练脚本。
3. 服务端组件：CVAT 2.73.1、MediaMTX 与原 8113 服务镜像作为独立 ARM64 Linux 组件交付。

## 2. Windows 安装

双击：

`release/宁波视觉SOP_CVAT闭环平台_完整安装程序_20260824.exe`

首次启动会在以下目录生成账号、配置、SQLite数据库、标注版本、训练产物和证据：

`%LOCALAPPDATA%\NingboSOPCVAT8113`

首次账号文件：

`%LOCALAPPDATA%\NingboSOPCVAT8113\runtime\initial_credentials.txt`

登录后应立即由管理员修改密码并限制该文件访问。程序不会把密码、MES令牌或CVAT令牌写入网页源码。

## 3. GPU 运行

本机推荐环境：

```powershell
& 'D:\Anaconda\shell\condabin\conda-hook.ps1'
conda activate dl
python -c "import torch; print(torch.cuda.is_available())"
```

桌面端默认查找：

`D:\Anaconda\envs\dl\python.exe`

可通过系统环境变量 `SOP_CONDA_PYTHON` 指向其他 Python。生产部署前应固定 CUDA、PyTorch、Ultralytics、OpenCV 和 ONNX Runtime 的版本，并完成 8 小时以上稳定性测试。

## 4. CVAT 与流媒体服务

离线包中的 Docker 镜像是 ARM64 Linux 架构，不能直接在普通 AMD64 Windows 工控机中加载。正确方式二选一：

- 在 ARM64 Linux 服务器加载 `宁波SOP_CVAT_ARM64服务端镜像_20260823.tar`；
- 使用随包 CVAT 2.73.1 源码，在目标 AMD64 Linux 服务器重新构建同架构镜像。

约定端口：

- SOP Web/API：8113 或现场映射端口
- CVAT：8081
- MediaMTX RTSP：8554
- MediaMTX HLS：8888
- MediaMTX API：9997

Windows 客户端只访问内网地址，不应把 CVAT、摄像机和 MES 直接暴露到公网。

## 5. 七步业务流程

1. 总览：确认服务在线、质量状态和待处置任务。
2. 数据获取与清洗：接入 UVC/RTSP、导入文件、校验、去重、生成代理视频。
3. AI预标注与证据：生成候选框、风险和证据缺口，候选保持待复核。
4. CVAT人工复核：改框、补框、改类别、关键帧跟踪、Reviewer审核。
5. 数据集构建：冻结 Annotation Version 和 Dataset Version，防止相邻帧泄漏。
6. 训练与部署：GPU训练、统一验证、导出 PT/ONNX、灰度发布和回滚。
7. 实时SOP + MES：左侧检测、右侧六步看板，输出 PASS/NG/REWORK/HOLD 和证据链。

## 6. MES 联调

正式接口至少包含：工单号、产品SN、产线/工位、配方版本、步骤开始结束时间、视觉结果、扭矩/角度、模型版本、关键帧/短视频引用、最终判定和事件编号。

联调顺序：

1. 先在测试环境验证鉴权、幂等键、超时和重试。
2. 再验证断网缓存和网络恢复补传。
3. 最后接入真实工单与工具控制器回执。
4. 未取得 MES 接收成功、扭矩合格和人工真值验收前，生产状态保持 `HOLD`。

## 7. 上线前仍需完成

- 现场相机安装、焦距/曝光/补光和 ROI 标定。
- 由工艺、质量和操作员共同冻结标签目录与六步 SOP。
- CVAT 双人复核与冻结测试集建设。
- 三模型在同一测试集上的 Precision、Recall、mAP、延迟和显存实测。
- MES、PLC、电批、扫码枪的真实协议联调。
- 误报/漏报阈值、回滚策略、账号权限、备份和日志保留周期确认。
- 试生产、8小时稳定性测试和量产验收签字。

任何“90%”或“98%”指标都必须来自人工冻结测试集；当前演示视频和候选标注不能替代量产验收。
