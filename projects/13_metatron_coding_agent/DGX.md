# 远端 DGX 试跑 Metatron 方案 · 交接说明

## 结论：今天**没能在 DGX 上执行**，不是方案问题，是链路不通

| 探测项 | 结果 |
|---|---|
| Tailscale 节点 `<DGX_HOST>` = `<DGX_TAILSCALE_IP>` | ✅ 在线（`idle`，ping 经 DERP ~418ms） |
| TCP 端口 22 / 11434 / 8300 / 8085 / 18501 | ❌ 全部 `000`，连不上 |
| SSH `<USER> / nvidia / admin / ubuntu` | ❌ `Permission denied (publickey,password)`，其中 ubuntu 直接超时 |
| 局域网 `<LAN_HOST> / .71 / .218 / .133:22` | ❌ 全部 closed |
| `<LAN_HOST>:8300 / :11434`（new-api / Ollama） | ❌ 不可达 |
| 本机 SSH 公钥 | 有 `id_ed25519.pub`、`pazhou_remote.pub`、`wsl_scp_key.pub`，但 DGX 未授权其中任何一个 |
| Tailscale 子网路由 | 无 subnet router 广告，只有 CGNAT 段 |

按只读边界，没有尝试改 DGX 配置、重启服务或强登。

## 恢复条件（三选一，需李老师本人操作）

1. 把本机 `~/.ssh/id_ed25519.pub` 追加到 DGX 目标用户的 `~/.ssh/authorized_keys`；
2. 在 DGX 上把 Ollama / 推理服务绑到 `0.0.0.0` 并放行 Tailscale 端口（当前服务可能只绑 127.0.0.1）；
3. 在 DGX 上开启 Tailscale subnet router，把 DGX 所在网段广告出来。

恢复后验证：

```bash
ssh <USER>@<DGX_TAILSCALE_IP> 'hostname; nvidia-smi --query-gpu=name,memory.total --format=csv'
curl http://<DGX_TAILSCALE_IP>:11434/v1/models
```

## DGX 上一键复现（链路恢复后执行）

`run_on_dgx.sh` 会拉起本机同款最小闭环（MuJoCo + Coding Agent 迭代），
不需要 NVIDIA 未公开的权重：

```bash
bash run_on_dgx.sh --rounds 5 --task hurdle
```

## 真·全量复现（Isaac Lab 版）还缺什么

论文 arXiv:2610.38027 的 base policy 是**冻结的生成式全身控制模型**，
训练数据含 MoCap、合成恢复轨迹、重定向场景交互动作。截至 2026-11-15：

- ❌ 无官方代码仓库（GitHub `org:NVIDIA metatron` = 0，`metatron humanoids` = 0）
- ❌ 无 checkpoint / 权重 / MoCap 数据
- ❌ 项目页 404/403

所以即使 DGX 有 128GB HBM 和 Isaac Sim，也**无法复现论文的全身控制能力**。
可复现的只有 skill 层工作流（Coding Agent 写代码 → 仿真 → 迭代），
也就是本机已经跑通的那部分。

若要做「NVIDIA 官方栈」的等价替代，可用这三个**真实开源**项目在 DGX 上搭：

| 项目 | 用途 | 状态 |
|---|---|---|
| `isaac-sim/IsaacLab` | 仿真 / RL 训练 | ✅ 公开，8.6k stars |
| `NVIDIA/Isaac-GR00T` | 人形 VLA 基础模型 | ✅ 公开，8.3k stars |
| `unitreerobotics/unitree_rl_gym` | G1 真机/仿真 RL | ✅ 公开，3.6k stars |

宇树 G1 的 walking / get-up 可走 `unitree_rl_gym` + Isaac Lab 部署；
但「不重训策略、只写代码加新技能」这一条，只有 Metatron 的冻结 base policy 能做到，
目前公开渠道拿不到。
