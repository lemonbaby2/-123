# CVAT + Cloudflare Tunnel 配置

此目录解决 CVAT 在 Quick Tunnel 下的 CSRF 和导出回跳内网问题。

1. 把 `production_cloudflare.py` 放到 CVAT 根目录 `config/`。
2. 把 `docker-compose.cloudflare.yml` 放到 CVAT 根目录。
3. 将文件中的两个公网域名改为当前 CVAT Tunnel 地址。
4. 先 `pg_dump` 备份，再仅重建 `cvat_server`。
5. 使用公网会话实测 Save、Dataset Export 和 ZIP Download。

该 overlay 不修改 `cvat_db`、Redis、视频命名卷和现有 Task。

