# 宁波 SOP 平台完整代码与版本档案

本仓库保存 SOP 网页、Python 后端、Windows 原生客户端、CVAT 集成、摄像头接入、训练/复核脚本、部署配置、说明文档和历史页面源码。

- 当前完整平台：[`sop-platform/`](sop-platform/)
- 本机版本与局域网入口：[`SOP_VERSION_INDEX_20260822.md`](SOP_VERSION_INDEX_20260822.md)
- 闭环总体方案：[`sop-platform/docs/22_宁波视觉SOP闭环系统总体方案_20260822.md`](sop-platform/docs/22_宁波视觉SOP闭环系统总体方案_20260822.md)
- Codex 对话脱敏索引：[`sop-platform/docs/23_Codex对话整理与交付索引_20260818-20260822.md`](sop-platform/docs/23_Codex对话整理与交付索引_20260818-20260822.md)
- 平台完整使用说明：[`sop-platform/docs/24_SOP平台完整使用说明_闭环版_20260822.md`](sop-platform/docs/24_SOP平台完整使用说明_闭环版_20260822.md)
- CVAT Webhook 后端开发说明：[`sop-platform/docs/25_CVAT_Webhook与AnnotationOnly后端开发说明_20260822.md`](sop-platform/docs/25_CVAT_Webhook与AnnotationOnly后端开发说明_20260822.md)
- SOP 与 CVAT 融合平台完整说明：[`sop-platform/docs/26_SOP与CVAT融合平台完整操作说明_20260822.md`](sop-platform/docs/26_SOP与CVAT融合平台完整操作说明_20260822.md)
- 历史源码快照：[`version-archive/`](version-archive/)
- 多版本 systemd 部署：[`deploy/versioned/`](deploy/versioned/)
- GitHub 安全发布包：[`releases/`](releases/)

当前 2026-08-23 融合站为 `http://192.168.1.129:8112`，CVAT 为 `http://192.168.1.129:8081`。原生产入口 `8096`、版本索引 `8099`、`8101`～`8105` 和 2026-08-22 融合站 `8111` 已冻结保留，新站不覆盖旧站运行目录和数据库。

上述地址是局域网入口。`192.168.1.129` 不是公网 IP，8102 临时隧道当前也不作为稳定交付入口。正式异地访问须通过企业 VPN，或在完成固定域名、TLS、认证、授权、限流、审计和备份后发布。

2026-08-23 新增并实测：23/23 视频 Range 播放、可移动介质导入进度与自动刷新、三种客户导出、CVAT Project/Organization 作用域、HMAC Webhook annotation-only 双向同步、YOLOv8s-World 训练目录、三路共享相机代理、MediaMTX H.264 RTSP/HLS 和 7 天 fMP4 录像。RTSP 地址为 `rtsp://192.168.1.129:8554/cam0` 至 `cam2`。

- 最新完整说明书：[`sop-platform/docs/27_宁波视觉SOP_CVAT闭环平台完整说明书_20260823.md`](sop-platform/docs/27_宁波视觉SOP_CVAT闭环平台完整说明书_20260823.md)
- Word 说明书：[`sop-platform/docs/27_宁波视觉SOP_CVAT闭环平台完整说明书_20260823.docx`](sop-platform/docs/27_宁波视觉SOP_CVAT闭环平台完整说明书_20260823.docx)
- 发布验收报告：[`sop-platform/docs/28_20260823独立融合版发布验收报告.md`](sop-platform/docs/28_20260823独立融合版发布验收报告.md)
- 浏览器验收：[`sop-platform/qa/release_8112/report.json`](sop-platform/qa/release_8112/report.json)
- 相机网关：[`sop-platform/camera-gateway/`](sop-platform/camera-gateway/)

17:00 增量抓取脚本与 systemd 模板已交付，但本机尚未完成 rclone OAuth，因此未启用生产定时器。Hard Case 自动回流、真实 MES 现场联调，以及 RT-DETRv2、D-FINE、Anomalib 完整训练验收仍待完成。

仓库不包含生产密码、Token、SQLite、视频、摄像头凭据、大模型权重和训练数据。自动检测与自动跟踪结果必须人工复核，量产状态保持 `HOLD`。
