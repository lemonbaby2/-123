# 2026-08-25 公网 CVAT 与 SOP 标注闭环版本

分支：`sop-public-cvat-roundtrip-20260825`  
对比基线：`sop-unified-20260823`

## 本次结论

本版本将“公网 CVAT 保存/导出失败、SOP 跳错内网地址、不同账号看不到同一项目、CVAT 标注无法回到对应整段视频、标签目录不可扩展”五个问题合并整改。CVAT 与 SOP 使用同一台服务器、同一个 CVAT PostgreSQL 数据库和同一个 Project #2；没有复制第二套 CVAT 数据库。

2026-08-25 现场验收结果：

- 公网 CVAT 登录：HTTP 200。
- 公网 CVAT 原样保存 Job #3 标注：HTTP 200，不再出现 CSRF Origin checking failed。
- 公网启动 YOLO 1.1 数据集导出：HTTP 202，后台状态 `finished`。
- 公网 ZIP 下载：HTTP 200，实测 527389 字节。
- CVAT 数据保持：2 个 Project、9 个 Task；Project 与 Task 统一归属 `cvat_admin`。
- SOP 新版：12/12 段已登记视频可播放；7 段已下载网盘原片与 CVAT Task #3～#9 一一绑定。
- 公网整段视频 Range 请求：HTTP 206，`3分37秒.mp4` 返回正确 `Content-Range`。
- 自定义标签：新增“连接器”成功，Project #2 当前 10 个标签；标签带 `SOP步骤`、`质量结论`、`物料编码`、`工位编号`、`批次号` 属性。
- CVAT → SOP annotation-only 回流：Task #5 同步任务状态 `completed`，生成可追溯 Annotation Version；当前该 Task 尚无人工框，因此版本计数为 0，系统未伪造标注。

## 12 张问题截图逐项分析

| 截图 | 现场现象 | 根因 | 本版本处理 |
|---|---|---|---|
| 1 | 公网创建 CVAT Task 报 CSRF Failed | Quick Tunnel 公网 Origin 不在 Django 信任列表 | 新增 Cloudflare 专用 production settings 与 Compose overlay |
| 2 | Projects 页面空白 | 登录的是受限标注账号或过滤条件未清除 | `cvat_admin` 设为有效超级管理员，项目/任务统一归属管理员 |
| 3 | 保存、导出、日志上报全部报 Origin checking failed | 所有写请求都被 CSRF 中间件拒绝 | 精确信任当前公网 Origin；保存、导出、下载均实测 |
| 4 | Tasks 能看到部分任务 | 任务实际存在，但访问入口和账号作用域不一致 | SOP 统一跳公网 Project #2/Tasks，任务均用同库读取 |
| 5 | SOP 有“双向同步”页面 | 页面能力存在，但入口配置仍指向内网 | 前端从 `public_endpoints.json` 读取唯一公网 CVAT 地址 |
| 6、7、10 | “打开 CVAT”按钮可能跳 `10.70.102.210:8081` | 源码写死或后端返回 LAN URL | 所有入口集中覆盖为同一公网 CVAT Project/Tasks |
| 8 | Project #1/#2 可见 | 说明数据并未丢失，是身份/入口问题 | 保留两个 Project，不新建重复数据库 |
| 9 | 固定工位口径可填写 | 工位字段与 CVAT 标签目录没有统一管理 | 新增 Project 标签管理器和业务属性字段 |
| 11 | `labeler01` 登录后 Projects 无结果 | 账号权限/组织作用域不同 | 按用户要求统一使用 `cvat_admin` 查看共享信息；原标注账号仍保留 |
| 12 | CVAT 只有预置标签下拉框 | Project 标签必须先维护，任务中不能随意临时造类 | SOP 新增“自定义标签与数据字段”，写入 Project 后全员共用 |

## 与 `sop-unified-20260823` 的核心差异

| 项目 | 2026-08-23 基线 | 2026-08-25 本分支 |
|---|---|---|
| 公网 CVAT 写操作 | 未覆盖 Quick Tunnel CSRF | 信任 Origin、恢复公网 Host、实测保存/导出/下载 |
| CVAT 导出结果 URL | 可能返回内网地址 | 返回当前公网 HTTPS 域名 |
| SOP → CVAT 链接 | LAN/localhost 配置为主 | `public_endpoints.json` 统一公网入口 |
| 账号可见性 | 标注账号按权限看不同资源 | `cvat_admin` 统一看到 2 Project/9 Task |
| 网盘视频 | 无本次 8 月 19/21 日完整映射 | 12 段清单、断点下载、增量导入、Task/视频绑定 |
| 整视频回流 | annotation-only 为主 | annotation-only + 对应原视频可播放 + Task 一键绑定 |
| 标签扩展 | 产线配置预置标签 | Project 自定义标签、颜色、形状、业务属性、审计 |
| 数据真实性 | 自动框需人工复核 | 继续保持；无人工框时明确返回 0，不伪造精度或标签 |
| 旧站保护 | 冻结版本说明 | 旧公网 SOP 保留，同时发布新版独立入口 |

## 源码入口

- SOP 后端：`sop-platform/server.py`
- 页面：`sop-platform/web/index.html`
- 前端逻辑：`sop-platform/web/app.js`
- 公网端点配置：`sop-platform/web/data/public_endpoints.json`
- 网盘下载：`sop-platform/scripts/baidu_auth_download.py`
- CVAT 增量导入：`sop-platform/scripts/cvat_import_baidu_videos.py`
- Task/视频映射：`sop-platform/scripts/register_baidu_sop_videos.py`
- 新版 SOP 启动：`sop-platform/scripts/Start-SOPPublicRoundtrip.ps1`
- Quick Tunnel：`sop-platform/scripts/Start-SOPPublicQuickTunnel.ps1`
- CVAT Cloudflare 配置：`sop-platform/deploy/cvat-cloudflare/`
- 完整部署与故障说明：`sop-platform/docs/41_公网CVAT保存导出与SOP视频回流整改_20260825.md`

## 当前边界

Quick Tunnel 是测试/演示入口，随机域名没有 SLA。生产环境应改为 Cloudflare Named Tunnel、固定域名、访问策略和双副本 connector。共享 `cvat_admin` 满足“所有人看到同一数据”的当前要求，但会降低个人操作审计精度；量产阶段建议恢复个人账号并使用同一 Organization/Project 权限，而不是长期共用密码。

仓库不提交 CVAT Token、Cookie、SQLite、PostgreSQL 备份、原始 MP4、训练权重或生产密码。

