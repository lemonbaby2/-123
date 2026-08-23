# SOP 本地项目版本总表（2026-08-22）

## 当前与历史入口

访问 `http://192.168.1.129:8099` 查看统一入口。`8096` 已恢复为当前对话的完整集成版本，其他页面使用 `8101` 至 `8105` 并行保留。

| 端口 | 版本 | 2026-08-22 本机状态 |
| --- | --- | --- |
| 8096 | 当前完整平台 | HTTP 200 |
| 8099 | 版本统一入口 | HTTP 200 |
| 8101 | 2026-08-22 视频库变体 | HTTP 200 |
| 8102 | 2026-08-21 轨迹跟踪版 | HTTP 200 |
| 8103 | 2026-08-20 协同标注版 | HTTP 200 |
| 8104 | 2026-08-19 网页/公网配置版 | HTTP 200 |
| 8105 | 2026-08-19 第三摄像头版 | HTTP 200 |
| 8081 | CVAT | HTTP 200（使用 `localhost` Host 路由） |

详细端口、服务名和恢复方法见 `deploy/versioned/README.md`。源码快照范围见 `version-archive/README.md`。

## 已确认的本地资料来源

- 当前 Git 交付仓库：`/home/xjai/Desktop/sop xjai/work-delivery-repo`
- 2026-08-21 标注增强运行版：`/home/xjai/Desktop/sop xjai/SOP分析平台_摄像头接入与低延迟标注增强版_20260819/SOP分析平台_老板汇报版`
- 2026-08-22 视频库流程变体：`/home/xjai/sop_project/SOP分析平台_老板汇报版`
- 2026-08-20 协同标注清理版：`/home/xjai/Desktop/sop_xjai_clean_export5/.../SOP分析平台_老板汇报版`
- 2026-08-19 网页前后端版：`/home/xjai/Desktop/sop xjai/wangye qianhoudaun`
- 2026-08-19 第三摄像头版：`/home/xjai/Desktop/sop xjai/交付_20260819_第三摄像头/.../SOP分析平台_老板汇报版`
- 微信 SOP 最终说明文档：`/home/xjai/文档/xwechat_files/wxid_y7nnhh1o7ide22_8b48/msg/file/2026-08/`
- 官方 CVAT：`/home/xjai/tools/cvat`

`sop_xjai_clean_export2` 与 `sop_xjai_clean_export4` 的前端核心文件哈希一致，因此列为同一页面族，不重复占用端口。所有原始目录和大型交付 ZIP 仍保留在本机。

## GitHub 边界

GitHub 分支保存全部可公开复现的代码、APP/Windows 源码、配置模板、文档、测试报告和历史页面快照。生产数据库、登录密码、网盘访问参数、CVAT Token、摄像头凭据、视频和模型不进入公开 Git；它们在本机权限受控目录和既有离线交付包中保留。

## 公网状态

上述入口使用 RFC1918 地址，只能在可路由的局域网或 VPN 内打开。8102 的临时公网隧道配置已归档，但当前隧道服务未形成稳定交付，不能承诺异地可访问。正式公网发布前需完成固定域名、TLS、强认证、角色权限、反向代理/WAF、限流、日志审计、备份恢复和书面授权的安全测试。

## 资料索引

- 闭环架构和完成状态：`sop-platform/docs/22_宁波视觉SOP闭环系统总体方案_20260822.md`
- 2026-08-18 至 2026-08-22 Codex 对话脱敏索引：`sop-platform/docs/23_Codex对话整理与交付索引_20260818-20260822.md`
- 操作、标注、审核、训练和 MES 使用说明：`sop-platform/docs/24_SOP平台完整使用说明_闭环版_20260822.md`
