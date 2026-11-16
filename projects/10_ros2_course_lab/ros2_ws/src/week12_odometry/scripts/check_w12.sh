#!/usr/bin/env bash
# ============================================================
#  check_w12.sh —— 上课前 60 秒自检（20 项）
# ============================================================
#  用法：source ~/ros2_ws_w12/install/setup.bash && bash check_w12.sh
#  全绿再开讲；任何一项 FAIL 都按「备注」列排查，不要硬着头皮演示。
# ------------------------------------------------------------
set +u
WS="${WS:-$HOME/ros2_ws_w12}"
source "$WS/env.sh"
PASS=0; FAIL=0; SKIP=0
ok()   { printf '  \033[32mPASS\033[0m  %-46s %s\n' "$1" "$2"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %-46s %s\n' "$1" "$2"; FAIL=$((FAIL+1)); }
skip() { printf '  \033[33mSKIP\033[0m  %-46s %s\n' "$1" "$2"; SKIP=$((SKIP+1)); }
has()  { command -v "$1" >/dev/null 2>&1; }

echo "============================================================"
echo " W12 课堂环境自检   $(date '+%F %T')   host=$(hostname)"
echo "============================================================"

# ---- 1 环境 ----
[ -n "${ROS_DISTRO:-}" ] && ok "ROS_DISTRO 已载入" "$ROS_DISTRO" \
                         || bad "ROS_DISTRO 已载入" "先 source /opt/ros/<distro>/setup.bash"
[ -f "$HOME/ros2_ws_w12/install/setup.bash" ] && ok "工作空间已构建" "install/setup.bash" \
                         || bad "工作空间已构建" "跑 00_一键构建.sh"
has gz && ok "Gazebo 命令可用" "$(gz sim --versions 2>/dev/null | head -1)" \
        || bad "Gazebo 命令可用" "apt install ros-$ROS_DISTRO-ros-gz"
for p in slam_toolbox rviz2 ros_gz_bridge; do
  ros2 pkg prefix "$p" >/dev/null 2>&1 && ok "包 $p" "已安装" \
      || bad "包 $p" "apt install ros-$ROS_DISTRO-${p//_/-}"
done

# ---- 2 进程 ----
pgrep -f 'gz sim' >/dev/null && ok "Gazebo 进程" "运行中" \
      || bad "Gazebo 进程" "跑 01_启动课堂.sh"
pgrep -f parameter_bridge >/dev/null && ok "ros_gz_bridge 进程" "运行中" \
      || bad "ros_gz_bridge 进程" "launch 未起来"
pgrep -f velocity_arbiter.py >/dev/null && ok "velocity_arbiter 节点" "运行中" \
      || bad "velocity_arbiter 节点" "检查 launch 日志"
pgrep -f telemetry_node.py >/dev/null && ok "telemetry 节点" "运行中" \
      || bad "telemetry 节点" "检查 launch 日志"

# ---- 3 /clock 只能有一个发布者 ----
CLK=$(ros2 topic info /clock 2>/dev/null | grep -i 'Publisher count' | grep -oE '[0-9]+' | head -1)
if [ -z "${CLK:-}" ]; then
  bad "/clock 发布者数量" "话题不存在"
elif [ "$CLK" = "1" ]; then
  ok "/clock 发布者数量" "1（正确）"
else
  bad "/clock 发布者数量" "$CLK 个 → 跑 02_停止全部.sh 清残留"
fi

# ---- 4 话题 ----
for t in /odom /scan /map /cmd_vel_target /w12/pid_debug /world/arena_w12/dynamic_pose/info; do
  ros2 topic list 2>/dev/null | grep -qx "$t" && ok "话题 $t" "存在" \
      || bad "话题 $t" "缺失"
done

# ---- 5 控制器 ----
CTRL=$(ros2 control list_controllers 2>/dev/null)
echo "$CTRL" | grep -q 'joint_state_broadcaster.*active' \
  && ok "控制器 joint_state_broadcaster" "active" || bad "控制器 joint_state_broadcaster" "未 active"
echo "$CTRL" | grep -q 'diff_drive_controller.*active' \
  && ok "控制器 diff_drive_controller" "active" || bad "控制器 diff_drive_controller" "未 active"

# ---- 6 cmd_vel 类型必须是 TwistStamped ----
CVT=$(ros2 topic list -t 2>/dev/null | grep 'diff_drive_controller/cmd_vel' | head -1)
echo "$CVT" | grep -q 'TwistStamped' && ok "cmd_vel 消息类型" "TwistStamped（Jazzy 正确）" \
     || bad "cmd_vel 消息类型" "${CVT:-未知} → 发 Twist 会被静默丢弃"

# ---- 7 数据链路 ----
if [ -f /tmp/w12_dashboard.json ]; then
  AGE=$(( $(date +%s) - $(stat -c %Y /tmp/w12_dashboard.json) ))
  [ "$AGE" -lt 6 ] && ok "遥测 JSON 新鲜度" "${AGE}s" || bad "遥测 JSON 新鲜度" "${AGE}s 未更新"
  python3 -c "import json;d=json.load(open('/tmp/w12_dashboard.json'));assert d['ok']" \
    && ok "遥测 JSON 可解析" "ok=true" || bad "遥测 JSON 可解析" "内容损坏"
  ERR=$(python3 -c "import json;print(json.load(open('/tmp/w12_dashboard.json')).get('error_m'))" 2>/dev/null)
  ok "里程计 / 真值误差" "${ERR} m（教学可观察量）"
else
  bad "遥测 JSON 新鲜度" "文件不存在 → telemetry 没起来"
fi

# ---- 8 网页看板 ----
CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:8130/ 2>/dev/null)
[ "$CODE" = "200" ] && ok "网页看板 HTTP" "200  http://127.0.0.1:8130/" \
                    || bad "网页看板 HTTP" "${CODE:-无响应} → 跑 dashboard/server.py"

echo "============================================================"
printf ' 汇总：PASS=%d  FAIL=%d  SKIP=%d\n' "$PASS" "$FAIL" "$SKIP"
[ "$FAIL" -eq 0 ] && echo " 结论：环境就绪，可以开讲。" || echo " 结论：先修 FAIL 项，别带故障上课。"
echo "============================================================"
exit "$([ "$FAIL" -eq 0 ] && echo 0 || echo 1)"
