# 安全边界

## 1. 生产机共存规则

这套实验曾在同时运行 34 个生产容器、CVAT 与他人训练进程的工作站上演示。为不干扰生产：

- **DDS 隔离**：`ROS_DOMAIN_ID=42`，所有话题只在自己的域内可见。
- **Gazebo 隔离**：`GZ_PARTITION=w12course`，世界名用 `arena_w12` 前缀，避免与同机其他 Gazebo 实例抢 `/clock`。
- **端口隔离**：看板 8130、门户 8140，均为新端口；不占用已有 8126 / 8090 等生产路由。
- **精确清场**：`stop_all.sh` 只匹配项目独有的可执行文件名（`demo_w12.launch.py`、`arena_w12.sdf`、`velocity_arbiter.py` 等），**禁止**用 `pkill -f 'gz sim'`、`pkill -f rviz2`、`pkill -f parameter_bridge` 这类通用关键词。
- **远程命令陷阱**：SSH 里 `pkill -f 'xxx'` 会匹配远端 `bash -c` 自身导致断连。用方括号正则（`arena[_]w12`）或变量间接引用。
- **GPU 策略**：维持停训决策，不启用任何自训练收割任务，不碰他人训练进程与 CVAT 容器。

## 2. 公开仓库脱敏

以下内容**不会**出现在本项目任何文件（含二进制 Office 文件的 XML）：

| 类别 | 处理方式 |
|---|---|
| 内网 IP / tailnet 地址 | 替换为 `<LAB_HOST>` / `<TAILNET_HOST>` |
| SSH 用户名与密码 | 替换为 `<USER>` / `<PASSWORD>` |
| 私钥、公钥、known_hosts、`*.pem` / `*.key` | 完全不入库；测试会扫描并拒绝 |
| 生产容器名、CVAT 任务号、他人训练路径 | 不写入文档与脚本 |
| 真实门牌、授权凭据、客户数据 | 不存在于此教学包 |

`tests/test_package_layout.py` 会自动扫描全部文本文件与 xlsx/docx 内部 XML，命中敏感串即测试失败。

## 3. SSH 远程连接的正确口径

远程 PC 连不上工作站时，先核对账号而不是重装服务。本教学包不提供任何可用于真实主机的凭据；文档中只保留排障方法：

```bash
ssh <USER>@<TAILNET_HOST>          # 用户名由机器管理员提供
ssh -i <PRIVATE_KEY> <USER>@<TAILNET_HOST>
```

排查顺序：`tailscale ping` → `nc -vz <TAILNET_HOST> 22` → 服务端 `sshd -T` 看 `passwordauthentication` / `permitrootlogin` → `/var/log/auth.log` 看是 `Invalid user` 还是认证失败。不要改密码、改 sshd 配置或重启服务，除非机器所有者明确要求。

## 4. 演示边界

- `load_factor=0.65` 是教学用人为扰动，不是真实物理参数。
- 模拟器内的「真值」来自 Gazebo 动态模型，不等于真实传感器精度。
- 本仓库不提供可直接部署到安全关键设备的控制器；实机迁移仍需 HIL、长稳、急停与失效注入。
