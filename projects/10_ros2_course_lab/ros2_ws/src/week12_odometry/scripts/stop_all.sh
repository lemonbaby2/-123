#!/usr/bin/env bash
# ============================================================
#  stop_all.sh —— 彻底清场（重点清 /clock 的重复发布者）
# ============================================================
# 反复启停仿真后，残留的 ros_gz_bridge 子进程会继续发 /clock，
# 于是出现 2~3 个发布者，RViz 每 2 秒报
#   "Detected jump back in time" 并清空画面。
# 这是本课程第 1 号课堂事故，下课前/重开前必跑本脚本。
# ------------------------------------------------------------
#  ⚠ 生产机上可能同时跑着别人的 ROS 2 演示（W11 传感器、三人小组 RViz 等）。
#     绝对不能用 'gz sim' / 'rviz2' / 'parameter_bridge' 这种通用关键词 pkill，
#     会误杀。这里只按「W12 独有文件名」+「启动脚本记录的进程组」精确清理。
# ------------------------------------------------------------
set +u
WS="${WS:-$HOME/ros2_ws_w12}"
echo '清理 W12 自己的进程（不碰机器上其他 ROS 2 演示）...'

# 1) 按启动脚本记录的 PGID 杀整个进程组（setsid 起的独立会话）
for f in "$WS/logs/launch.pid" "$WS/logs/dashboard.pid"; do
  [ -f "$f" ] || continue
  pid="$(cat "$f" 2>/dev/null || echo '')"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
  fi
  rm -f "$f"
done

# 2) 补刀：每个关键词都只可能出现在 W12 自己的命令行里
for pat in 'demo_w12.launch.py' 'arena_w12.sdf' 'demo_w12.rviz' \
           'velocity_arbiter.py' 'telemetry_node.py' 'odom_relay.py' \
           'odom_eval.py' 'server.py --port 8130'; do
  pkill -f "$pat" 2>/dev/null || true
done
sleep 1
# gz GUI 被 TERM 后偶尔留孤儿进程，会继续发 /clock → 下次启动出现 2 个发布者。
# 用 [_] 形式的正则：既匹配真实文件名，又不会匹配到本脚本命令行里的字面串。
for pat in 'arena[_]w12' 'demo[_]w12' 'velocity[_]arbiter' 'telemetry[_]node'; do
  pkill -9 -f "$pat" 2>/dev/null || true
done
sleep 1
rm -f /tmp/w12_cmd.json /tmp/w12_dashboard.json /tmp/w12_dashboard.json.tmp
echo '残留检查：'
pgrep -af 'arena_w12|demo_w12|velocity_arbiter|telemetry_node|odom_relay' || echo '  无残留'
echo '复核：ros2 topic info /clock → 本 domain 的 Publisher count 应为 0（下次启动后为 1）'
