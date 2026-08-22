# CVAT 中文离线标注与 SOP 分析平台

这是 CVAT 2.73.1 与本地 SOP 分析平台的可公开部署覆盖层。它固定上游版本，补充中文界面、常驻矩形框入口、绘制十字准星、Windows 启动器和离线 Docker 编排，并保留任务导出与恢复流程。

> 公开边界：本目录不包含账号、口令、内网地址、业务视频、生产数据库、客户标注、模型权重或 Docker 镜像。完整数据交付包通过受控离线渠道传输。CVAT 上游代码与镜像遵循其原始 MIT 许可证；SOP 生产数据和模型不随作品集分发。

## 已验证结果

| 项目 | 验证结果 |
|---|---|
| CVAT 版本 | 2.73.1，ARM64 服务端与 8 个 RQ worker 原生运行 |
| 中文界面 | 导航、任务、作业、导入导出、工作区与绘图工具常用词条覆盖 |
| 矩形工具 | 工具栏入口常驻；无矩形标签时禁用并给出原因 |
| 十字准星 | 矩形、长方体与椭圆绘制启用 crosshair |
| 视频任务 | Task 1293，344 帧，1280x720，矩形轨迹坐标 `(320,180)-(960,540)` |
| 官方导出 | `CVAT for video 1.1` ZIP 含 `annotations.xml`、`<track>` 和 `<box>` |
| Windows 启动器 | .NET Framework WinForms PE，可启动固定 Docker Compose 并打开本机网页 |
| SOP 本机模式 | WinForms 启动器 + Python 3.12 嵌入式运行时，监听 `127.0.0.1:8096` |

验收只说明上述固定版本和测试任务已经通过，不代表所有上游 CVAT 页面均已完成逐词人工翻译，也不代表未安装 Docker Desktop 的 Windows 主机能够运行 CVAT。

## 目录

```text
.
├── cvat-overlay/        # CVAT UI 修改、Compose 与 Docker 构建文件
├── windows/             # CVAT Windows 启动器源码与已编译 EXE
├── sop/                 # SOP 本机/容器部署模板与公开源码索引
├── scripts/             # Windows 恢复与启动脚本
├── tests/               # 静态交付检查
└── EVIDENCE.md          # 验收口径、哈希与限制
```

## CVAT 部署

先取得 CVAT 2.73.1 源码，再将 `cvat-overlay/` 中的同名文件覆盖到源码树。构建固定镜像后启动：

```bash
docker compose -f docker-compose.yml -f docker-compose.windows.yml up -d
```

Windows 离线交付目录还需要 `images/cvat-offline-amd64.tar`。启动器首次运行会执行 `docker load`，随后启动 Compose。CVAT 是多服务系统，因此 EXE 是桌面启动和状态窗口，不是把 PostgreSQL、Redis、后端和前端硬塞进单个 PE 文件。

## SOP 本机部署

完整离线包把 `SOP平台.exe`、`server.py`、`web/`、`config/`、`runtime/` 与 `python-runtime/` 放在同一目录。双击 EXE 后在本机启动：

```text
http://127.0.0.1:8096
```

基础网页、SQLite 标注和审计使用 Python 标准库即可运行；摄像头推理和训练还需要 OpenCV、Ultralytics/PyTorch 及相应权重。SOP 的完整脱敏源码历史已固定在 `lemonbaby2/work` 的提交 `2395071fa51cc68a84897c7e13a2c0bdf9677db9`，本目录只保存部署边界与离线封装文件，避免重复维护两份源码。

## 恢复与校验

在 PowerShell 中先加载镜像，再恢复数据卷，最后启动：

```powershell
docker load -i .\images\cvat-offline-amd64.tar
powershell -ExecutionPolicy Bypass -File .\scripts\Restore-CvatVolumes.ps1
.\CVAT中文离线标注平台.exe
```

交付包根目录的 `SHA256SUMS.txt` 用于逐文件校验。恢复前应确认 Docker Desktop 使用 Linux 容器和 WSL2 后端，并至少预留 30 GB 可用空间。

## 简历表述

可直接使用的项目描述见 [RESUME_PROJECT.md](RESUME_PROJECT.md)。其中把“固定版本已验收”和“仍需目标 Windows 主机验收”分开陈述，避免把本地 Linux 验证扩写成未发生的 Windows 生产验收。

