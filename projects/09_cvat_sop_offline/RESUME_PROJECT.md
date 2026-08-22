# 简历项目描述

## CVAT 中文离线标注与 SOP 分析平台 | 2026.08

- 基于 CVAT 2.73.1 完成本地化部署，补充中文 UI 覆盖、常驻矩形框工具、无矩形标签禁用提示与绘制十字准星，保持上游多边形、折线、点、椭圆、长方体、Mask、跟踪和复核等工具入口。
- 在 ARM64 主机原生构建 CVAT 后端，并将 server 与 8 个 RQ worker 从 AMD64/QEMU 切换为 ARM64；通过健康检查、任务读取和官方数据集导出验证服务链路。
- 导入 344 帧 1280x720 MP4，完成矩形轨迹标注并导出 `CVAT for video 1.1`，自动检查 ZIP 中标签、`<track>`、`<box>` 与坐标数据。
- 设计 Windows WinForms 启动器和固定 Docker Compose 离线包，覆盖镜像加载、服务启停、健康轮询、浏览器打开、日志与本地数据卷；对 EXE、数据库快照和导出物生成 SHA-256 清单。
- 封装本地 SOP 分析平台的前后端、SQLite 审计库、模型注册表和 Windows Python 运行时，支持无局域网依赖的 `127.0.0.1` 本机访问；将生产数据、模型权重和凭据与公开源码分层交付。

技术栈：CVAT、React/TypeScript、Django、PostgreSQL、Redis/Kvrocks、Docker Compose、ARM64/AMD64 多架构构建、Python、SQLite、C# WinForms、PowerShell。

说明：CVAT Windows 版依赖 Docker Desktop/WSL2；SOP 基础本机模式由嵌入式 Python 启动，高级推理功能另需相应运行库与模型。目标 Windows 主机验收结果应在实际完成后再写入简历。

