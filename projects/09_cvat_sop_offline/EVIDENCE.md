# 验收证据与边界

## CVAT 固定版本验收

- 上游提交：`8a2c233b8561090646f8d4c088b8e7b50ecb7605`
- 服务端镜像：`cvat/server:2.73.1-arm64`
- 服务端镜像摘要：`sha256:3adf1b3f7d95eb0bed9adae471a12319e22212cd21e935c3c80007a9edd70def`
- Windows 中文 UI 镜像摘要：`sha256:8997a19d554052e77c5cb7f8989848b1030c04df00ffd8cfe8f2f8a8ad8e71ce`
- 测试任务：Task `1293` / Job `1290`
- 媒体：344 帧，1280x720 MP4
- 标签：`目标物体`
- 矩形：`xtl=320, ytl=180, xbr=960, ybr=540`
- 导出格式：`CVAT for video 1.1`
- 导出 ZIP SHA-256：`fd8d3673ef55e39e5c941225fbe4421747b62035612be3d209886db7059666ee`
- 无通知最终截图 SHA-256：`a303c0e28272068cb34d8fc7375deda19d87eac46479b086edf4ce528368ebeb`
- 浏览器验收 JSON SHA-256：`cb1865e76fcc59f847e9c0ebc62d35d9beea56a75d7e8637a60869fb3bef7431`

导出文件不进入公开仓库，因为它来自本地业务数据卷。公开记录只保留任务结构、验证方式和内容摘要。

## Windows 工件

- CVAT 启动器：`CVAT中文离线标注平台.exe`
- CVAT 启动器 SHA-256：`e57282ca96127d1aa037db2cc2e881dd958fc558e796ae0505a326d170c965a2`
- SOP 启动器：`SOP平台.exe`
- SOP 启动器 SHA-256：`193054f55f94304311f3b87b569b27e99e57c3fb8ddc4e46f76cb010048230d6`
- 两个启动器都是 Windows GUI PE；CVAT 启动器依赖 Docker Desktop + WSL2，SOP 启动器依赖同目录 Python 运行时和应用文件。

## 尚未宣称完成的项目

- 目标 Windows 主机上的 Docker Desktop 安装与端到端启动验收。
- 所有 CVAT 页面逐词 100% 汉化。
- Windows 上 GPU 推理、摄像头驱动与训练性能验收。
- 生产数据、模型商业许可与客户授权审计。
