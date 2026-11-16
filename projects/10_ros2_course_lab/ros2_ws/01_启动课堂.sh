#!/usr/bin/env bash
# ============================================================
#  01_启动课堂.sh —— 一键拉起「Gazebo + RViz2 + SLAM + 网页看板」
# ============================================================
# 四个可视化窗口/页面：
#   1) Gazebo GUI       差速车在 10×10 m 场地里跑（真物理）
#   2) RViz2            机器人模型 / TF / LaserScan / 里程计轨迹 / SLAM 地图
#   3) 网页看板         http://127.0.0.1:8130/  四宫格实时曲线
#   4) Firefox          自动打开看板（可用 AUTO_BROWSER=0 关掉）
# ------------------------------------------------------------
#  ⚠ 不设 -u：source setup.bash 会踩 AMENT_TRACE_SETUP_FILES 未绑定变量
# ------------------------------------------------------------
set +u
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$WS/logs" "$WS/maps"

export DISPLAY="${DISPLAY:-:1}"
export XAUTHORITY="${XAUTHORITY:-/run/user/1000/gdm/Xauthority}"
if ! xdpyinfo >/dev/null 2>&1; then
  echo "⚠ 桌面 $DISPLAY 不可用，自动切到无窗口模式（gui:=false）"
  GUI=false
else
  GUI=true
fi

source "$WS/env.sh"
echo "ROS_DOMAIN_ID=$ROS_DOMAIN_ID  GZ_PARTITION=$GZ_PARTITION（与机器上其他 ROS 2 演示隔离）"

# 默认不清场：生产机上可能同时跑着别的 ROS 2 演示（如 W11 传感器 / 三人小组），
# 贸然 pkill 'gz sim' 会误杀别人的进程。独占机器时才用 CLEAN_FIRST=1 显式清场。
if [ "${CLEAN_FIRST:-0}" = "1" ]; then
  bash "$WS/src/week12_odometry/scripts/stop_all.sh" || true
fi

# ---- 网页看板（标准库 http.server，零第三方依赖） ----
cd "$WS/dashboard"
setsid nohup python3 server.py --port 8130 --data /tmp/w12_dashboard.json \
  > "$WS/logs/dashboard.log" 2>&1 < /dev/null &
echo $! > "$WS/logs/dashboard.pid"

# ---- ROS 2 全链路 ----
# PID 演示时自动注入 0.65 的教学负载：车只能跑出指令的 65%，
# 闭环会把输出顶到 ~0.54 m/s 才让实测速度回到 0.35 m/s，
# 网页看板上「目标 / 实测 / 输出」三条线分开又合拢，PID 的作用一眼可见。
MODE="${MODE:-passthrough}"
LF=1.0
[ "$MODE" = "pid" ] && LF=0.65
cd "$WS"
setsid nohup ros2 launch week12_odometry demo_w12.launch.py \
  gui:="$GUI" rviz:="$GUI" slam:=true mode:="$MODE" load_factor:="$LF" \
  > "$WS/logs/launch.log" 2>&1 < /dev/null &
echo $! > "$WS/logs/launch.pid"

echo "启动中（约 20 s）...  日志：$WS/logs/launch.log"
for i in $(seq 1 20); do sleep 1; printf '.'; done; echo

CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:8130/ || echo 000)
echo "看板 HTTP: $CODE   地址: http://127.0.0.1:8130/"

if [ "${AUTO_BROWSER:-1}" = "1" ] && [ "$GUI" = true ] && command -v firefox >/dev/null; then
  setsid nohup firefox --new-window 'http://127.0.0.1:8130/' \
    >/dev/null 2>&1 < /dev/null &
fi

echo
echo '── 验收清单 ─────────────────────────────────────────'
echo "  bash $WS/src/week12_odometry/scripts/check_w12.sh     # 20 项自检"
echo "  bash $WS/src/week12_odometry/scripts/drive_demo.sh all # 跑 A/B/C 三段"
echo "  bash $WS/03_保存地图.sh                               # 存 SLAM 地图"
echo "  bash $WS/02_停止全部.sh                               # 下课清场"
echo '──────────────────────────────────────────────────────'
