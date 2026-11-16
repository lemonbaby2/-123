#!/usr/bin/env bash
# 在 DGX 上把 VLA 验收门户公开到公网 (Tailscale Funnel)。
# 前提: DGX funnel 端口 10000-10014 + 443 当前已被生产/ros2/Embodied Studio 占满,
# 因此需要一个"空闲"端口。释放任一端口(或新增允许的 funnel 端口)后, 取消下方注释并填端口。
set -e
PORT="${1:-18932}"        # 本地门户端口 (已在 vla-portal.service 监听)
FUNNEL_PORT="${2:-10013}" # 期望对外 funnel 端口; 必须是 AllowFunnel 列表内且当前无 handler 的端口

echo "检查 $FUNNEL_PORT 是否空闲..."
if tailscale funnel status 2>/dev/null | grep -q ":$FUNNEL_PORT "; then
  echo "端口 $FUNNEL_PORT 已被占用, 请换一个空闲 funnel 端口 (如 10011/10012/10013/10014 中确认无 handler 者)。"
  exit 1
fi

echo "建立 $FUNNEL_PORT -> 127.0.0.1:$PORT 的 funnel 映射..."
tailscale serve --https="$FUNNEL_PORT" --set-path=/ "http://127.0.0.1:$PORT"
tailscale funnel --bg "$FUNNEL_PORT"
echo "已尝试公开: https://spark-a8d2.tail83f79e.ts.net:$FUNNEL_PORT/"
echo "若仍连不上, 多为该端口不在 AllowFunnel 列表; 请联系管理员放开或换端口。"
