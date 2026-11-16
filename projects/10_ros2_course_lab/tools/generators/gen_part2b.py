# -*- coding: utf-8 -*-
"""生成 W12 的课堂脚本、自检脚本与工作空间级一键脚本。"""
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ros2_ws_w12')
SCRIPTS = os.path.join(ROOT, 'src', 'week12_odometry', 'scripts')
TOP = {}

SCR = {}

SCR['check_w12.sh'] = r'''#!/usr/bin/env bash
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
'''

SCR['drive_demo.sh'] = r'''#!/usr/bin/env bash
# ============================================================
#  drive_demo.sh —— 课堂驾驶脚本（四段动作，全部走 /cmd_vel_target）
# ============================================================
#  用法：bash drive_demo.sh a|b|c|all|stop
#    a   直行 3 s @ 0.35 m/s        检验 wheel_radius
#    b   原地左转 2 s @ 0.8 rad/s   检验 wheel_separation
#    c   画圈 6 s @ 0.30 / 0.60     给 SLAM 建图采集一圈数据
#    all a→b→c→stop
#    stop 立即零速
#  ★ 发的是 TwistStamped：Jazzy 的 diff_drive_controller 不收 Twist。
#  ★ 指令先到 velocity_arbiter，看门狗 0.6 s 超时会自动归零，
#    所以每段必须用 -r 10 持续发，不能 pub 一次就完事。
# ------------------------------------------------------------
set +u
WS="${WS:-$HOME/ros2_ws_w12}"
source "$WS/env.sh"
TOPIC=/cmd_vel_target
TYPE=geometry_msgs/msg/TwistStamped

send() {  # $1=线速度 $2=角速度 $3=持续秒数
  local lv="$1" av="$2" dur="$3"
  # TwistStamped = header + twist(Twist)，twist 下面直接是 linear/angular。
  # 写成 twist: {twist: {...}} 会多套一层，ros2 topic pub 不报错但字段全 0，
  # 表现为「命令发了车不动」——这与 Jazzy 只收 TwistStamped 是两类不同的坑。
  local payload="{header: {frame_id: base_link}, twist: {linear: {x: $lv, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: $av}}}"
  timeout "$dur" ros2 topic pub -r 10 "$TOPIC" "$TYPE" "$payload" >/dev/null 2>&1 &
  local pid=$!
  sleep "$dur"
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}

case "${1:-all}" in
  a)    echo '[A] 直行 3 s @ 0.35 m/s';  send 0.35 0.0 3 ;;
  b)    echo '[B] 左转 2 s @ 0.8 rad/s'; send 0.0 0.8 2 ;;
  c)    echo '[C] 画圈 6 s @ 0.30/0.60'; send 0.30 0.60 6 ;;
  stop) echo '[STOP] 零速';               send 0.0 0.0 1 ;;
  all)
    echo '[A] 直行 3 s @ 0.35 m/s';  send 0.35 0.0 3
    echo '[B] 左转 2 s @ 0.8 rad/s'; send 0.0 0.8 2
    echo '[C] 画圈 6 s';             send 0.30 0.60 6
    echo '[STOP] 零速';              send 0.0 0.0 1
    ;;
  *) echo "用法：bash drive_demo.sh a|b|c|all|stop"; exit 1 ;;
esac
echo '完成。看板上应能看到轨迹 / PID 曲线 / 占用栅格同步变化。'
'''

SCR['save_map.sh'] = r'''#!/usr/bin/env bash
# ============================================================
#  save_map.sh —— 把 slam_toolbox 建好的地图存盘并挂到网页看板
# ============================================================
#  map_saver_cli 会产出两个文件：w12_map.pgm（栅格图）+ w12_map.yaml（元数据）。
#  少任何一张，AMCL / Nav2 都读不了 —— 讲课时务必强调「地图是两张」。
# ------------------------------------------------------------
set -e
WS="${WS:-$HOME/ros2_ws_w12}"
STAMP="$(date '+%Y%m%d_%H%M%S')"
OUT="$WS/maps/w12_map_$STAMP"
mkdir -p "$WS/maps" "$WS/dashboard/maps"

source "$WS/env.sh"

ros2 run nav2_map_server map_saver_cli -f "$OUT" \
  --ros-args -p use_sim_time:=true

[ -f "$OUT.pgm" ] && [ -f "$OUT.yaml" ] || { echo '保存失败：缺 pgm 或 yaml'; exit 1; }
cp "$OUT.pgm" "$OUT.yaml" "$WS/dashboard/maps/"
ln -sfn "$(basename "$OUT").pgm"  "$WS/dashboard/maps/latest.pgm"
ln -sfn "$(basename "$OUT").yaml" "$WS/dashboard/maps/latest.yaml"

echo "已保存：$OUT.pgm / $OUT.yaml"
echo "网页可下载：http://127.0.0.1:8130/maps/latest.pgm"
'''

SCR['stop_all.sh'] = r'''#!/usr/bin/env bash
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
'''

TOP['env.sh'] = r'''#!/usr/bin/env bash
# ============================================================
#  env.sh —— 所有课堂脚本的统一环境入口
# ============================================================
#  为什么要有这个文件：
#   生产机（DGX）上可能同时跑着别的 ROS 2 演示。用独立的
#   ROS_DOMAIN_ID + GZ_PARTITION 把 W12 隔在自己的 DDS 域与 Gazebo 分区里，
#   既不干扰别人，也不会出现「/clock 三个发布者」的经典事故。
#   在老师独占的 Ubuntu / VMware 上，这组值同样适用，无需改动。
#  ⚠ 不能用 set -u 包着 source：ROS 2 的 setup.bash 里有未绑定变量。
# ------------------------------------------------------------
if [ -z "${ROS_DISTRO:-}" ]; then
  for d in jazzy humble rolling; do
    [ -f "/opt/ros/$d/setup.bash" ] && ROS_DISTRO="$d" && break
  done
fi
if [ -n "${ROS_DISTRO:-}" ]; then
  source "/opt/ros/$ROS_DISTRO/setup.bash"
fi
WS="${WS:-$HOME/ros2_ws_w12}"
if [ -f "$WS/install/setup.bash" ]; then
  source "$WS/install/setup.bash"
fi
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-42}"
export GZ_PARTITION="${GZ_PARTITION:-w12course}"
export WS
'''

TOP['00_一键构建.sh'] = r'''#!/usr/bin/env bash
# ============================================================
#  00_一键构建.sh —— 在 Ubuntu 上从零构建 W12 工作空间
# ============================================================
#  ⚠ 不能用 set -u：/opt/ros/<distro>/setup.bash 里引用了
#     AMENT_TRACE_SETUP_FILES 等未定义变量，开 -u 会直接
#     "unbound variable" 中断。这是 ROS 2 脚本的固有行为。
# ------------------------------------------------------------
set -eo pipefail
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 自动探测发行版，不写死 jazzy：学生机可能是 Humble
if [ -z "${ROS_DISTRO:-}" ]; then
  for d in jazzy humble rolling; do
    [ -f "/opt/ros/$d/setup.bash" ] && ROS_DISTRO="$d" && break
  done
fi
[ -n "${ROS_DISTRO:-}" ] || { echo '未找到 /opt/ros/*/setup.bash，请先装 ROS 2'; exit 1; }
source "/opt/ros/$ROS_DISTRO/setup.bash"
echo "ROS_DISTRO=$ROS_DISTRO   arch=$(dpkg --print-architecture)"

# 依赖检查（只提示，不擅自 apt，避免动生产机）
MISS=()
for p in ros_gz_sim ros_gz_bridge gz_ros2_control slam_toolbox nav2_map_server rviz2 xacro; do
  ros2 pkg prefix "$p" >/dev/null 2>&1 || MISS+=("$p")
done
if [ ${#MISS[@]} -gt 0 ]; then
  echo "缺少依赖：${MISS[*]}"
  echo "安装命令：sudo apt install ${MISS[*]/#/ros-$ROS_DISTRO-}  （包名里的下划线换成连字符）"
  echo "提示：ros_gz_sim→ros-${ROS_DISTRO}-ros-gz-sim，gz_ros2_control→ros-${ROS_DISTRO}-gz-ros2-control"
fi

cd "$WS"
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source "$WS/install/setup.bash"
chmod +x "$WS"/src/week12_odometry/scripts/* "$WS"/dashboard/server.py 2>/dev/null || true
echo
echo "构建完成。下一步：bash $WS/01_启动课堂.sh"
'''

TOP['01_启动课堂.sh'] = r'''#!/usr/bin/env bash
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
'''

TOP['02_停止全部.sh'] = r'''#!/usr/bin/env bash
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$WS/src/week12_odometry/scripts/stop_all.sh"
'''

TOP['03_保存地图.sh'] = r'''#!/usr/bin/env bash
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export WS
bash "$WS/src/week12_odometry/scripts/save_map.sh"
'''

TOP['README.md'] = r'''# 第 12 周课件包 · 运动学、里程计与 PID 控制

**课程**：《机器学习与智能机器人应用技术》智能机器人线 · 第 12 周
**学校**：广州现代信息工程职业技术学院
**验证环境**：Ubuntu 24.04.4 LTS (aarch64) + ROS 2 Jazzy + Gazebo Harmonic 8.11.0
**验证主机**：DGX spark-a8d2（`<LAB_HOST>`）

---

## 一、这套东西解决什么

下周 90 分钟课堂要同时展示「车真的在动」「里程计在漂」「PID 在补」「地图长出来」四件事。
本包把它们做成**四个同时可见的窗口/页面**，全部挂在 Ubuntu 桌面上：

| # | 窗口 / 页面 | 看到什么 | 对应知识点 |
|---|---|---|---|
| 1 | Gazebo GUI | 差速车在 10×10 m 封闭场地运动，有围墙、色块、L 形内墙 | 物理仿真、传感器有东西可看 |
| 2 | RViz2 | 机器人模型、TF 树、LaserScan 点云、里程计轨迹箭头、SLAM 占用栅格 | TF / 坐标系 / 地图 |
| 3 | 网页看板 `http://127.0.0.1:8130/` | 四宫格：odom vs 真值轨迹、PID 曲线、激光极坐标、占用栅格地图 | 误差、闭环、建图 |
| 4 | Firefox（自动打开） | 上面那个看板，可用按钮直接开车 | 人机交互 |

网页看板**不依赖 rosbridge / flask / numpy**，只用 Python 标准库 `http.server`，
教室断网也能跑。数据链路是：`telemetry_node.py` 订阅 ROS 话题 → 写 `/tmp/w12_dashboard.json`
→ 浏览器每 500 ms 拉一次。

---

## 二、三步启动（Ubuntu 桌面终端）

```bash
cd ~/ros2_ws_w12
bash 00_一键构建.sh          # 约 1–2 分钟；只第一次需要
bash 01_启动课堂.sh          # 拉起 Gazebo + RViz2 + SLAM + 看板，约 20 s
bash src/week12_odometry/scripts/check_w12.sh   # 20 项自检，全绿再开讲
```

开讲后：

```bash
bash src/week12_odometry/scripts/drive_demo.sh a     # A 段直行 3 s
bash src/week12_odometry/scripts/drive_demo.sh b     # B 段原地左转 2 s
bash src/week12_odometry/scripts/drive_demo.sh c     # C 段画圈 6 s（给 SLAM 采集）
bash src/week12_odometry/scripts/drive_demo.sh all   # 三段连跑
bash 03_保存地图.sh                                  # 存 w12_map.pgm + .yaml
bash 02_停止全部.sh                                  # 下课清场
```

也可以在网页看板上直接按方向按钮开车，网页会写 `/tmp/w12_cmd.json`，
`velocity_arbiter.py` 读取后转发给控制器。

---

## 三、目录结构

```
ros2_ws_w12/
├── 00_一键构建.sh  / 01_启动课堂.sh  / 02_停止全部.sh  / 03_保存地图.sh
├── src/
│   ├── diffbot_description/          差速底盘（URDF/Xacro + 控制器 YAML）
│   │   ├── urdf/diffbot.common.xacro         几何 + 惯性 + ros2_control 接口
│   │   ├── urdf/diffbot_sensors.urdf.xacro   相机 / 2D 激光 / IMU
│   │   └── config/diffbot_controllers.yaml   轮径 0.05 / 轮距 0.36 / 协方差
│   └── week12_odometry/              W12 新增
│       ├── launch/demo_w12.launch.py          九段启动顺序（注释里写了全部坑）
│       ├── config/bridge_w12.yaml             /clock /scan /imu /真值
│       ├── config/slam_w12.yaml               slam_toolbox 参数
│       ├── worlds/arena_w12.sdf               10×10 m 场地 + L 形内墙
│       ├── rviz/demo_w12.rviz                 Grid/Model/TF/Scan/Map/Odom/Image
│       └── scripts/
│           ├── velocity_arbiter.py   ★ 看门狗 + PID + 指令仲裁
│           ├── telemetry_node.py     ★ ROS → JSON 遥测
│           ├── odom_relay.py         私有 odom → 标准 /odom
│           ├── odom_eval.py          里程计精度评估（A 直行 / B 转向）
│           ├── check_w12.sh          20 项自检
│           ├── drive_demo.sh         A/B/C 三段驾驶
│           ├── save_map.sh           地图存盘
│           └── stop_all.sh           清残留（/clock 单发布者）
├── dashboard/                       网页看板（原生 HTML/Canvas/JS）
└── logs/ maps/                      运行日志与地图产物
```

---

## 四、五个必须知道的坑（讲稿里会逐个演示）

1. **`/clock` 只能有一个发布者。** 反复启停仿真会残留 `ros_gz_bridge` 子进程，
   RViz 每 2 秒报 `Detected jump back in time` 并清屏。重开前跑 `02_停止全部.sh`。
   核验：`ros2 topic info /clock` 的 `Publisher count` 必须是 1。
2. **Jazzy 的 `diff_drive_controller` 只收 `TwistStamped`。** 发 `Twist` 不报错，
   消息静默丢弃，表现为「命令发了车不动」。核验：`ros2 topic list -t | grep cmd_vel`。
3. **`GZ_SIM_SYSTEM_PLUGIN_PATH` 要手动补。** `gz_ros2_control` 没装环境钩子，
   不补就加载不到插件，`/controller_manager` 永远不出现。launch 里已处理。
4. **速度环 PID 必须写成 `u = v_target + Kp·e + Ki·∫e + Kd·ė`。**
   少了前馈项 `v_target`，稳态误差趋零时输出也趋零，车反而停下。
5. **地图是两张文件。** `map_saver_cli` 产出 `.pgm`（像素栅格）和 `.yaml`
   （分辨率、origin、占用阈值），少一张 AMCL/Nav2 都读不了。

---

## 五、双版本说明

| 项 | Jazzy（实测） | Humble（学生 VMware 常见） |
|---|---|---|
| `cmd_vel` 类型 | `TwistStamped` | `Twist`（`use_stamped_vel:=false`） |
| Gazebo | Harmonic / `gz sim` | Fortress / `ign gazebo` 或 `gz sim` |
| slam_toolbox | `async_slam_toolbox_node` | 同名，参数基本一致 |
| 世界 SDF 版本 | 1.9 | 1.8~1.9 兼容 |

Humble 上若车不动，第一件事就是 `ros2 topic list -t | grep cmd_vel` 看类型；
把 `drive_demo.sh` 里的 `TYPE` 改成 `geometry_msgs/msg/Twist`、去掉 `header/twist.twist` 一层即可。

---

## 六、与第 10/11 周、第 13/14 周的衔接

- 底盘模型、控制器 YAML 直接复用 W10/W11（`diffbot_description`），保证同一台车。
- W12 产出的 `/odom` 与 `/imu/data_raw` 是 W13 `robot_localization` EKF 的输入。
- W12 现场建的 `w12_map.pgm/.yaml` 是 W14 AMCL 与 Nav2 的地图输入。
- W12 的「里程计漂移」正好引出 W13「为什么要融合」和 W14「为什么要用激光修正」。

---

## 七、生产机共存：独立 DDS 域与 Gazebo 分区

`env.sh` 统一导出 `ROS_DOMAIN_ID=42`、`GZ_PARTITION=w12course`。
在同时跑着别的 ROS 2 演示的机器（例如 DGX 上还有 W11 传感器演示、
三人小组的 RViz 与监控盘）上，这两个变量把 W12 隔在自己的通信域里：

- 不干扰别人的节点、话题、TF；
- 自己的 `/clock` 永远只有一个发布者；
- `02_停止全部.sh` 只按 W12 独有文件名（`arena_w12.sdf` / `demo_w12.rviz` /
  `demo_w12.launch.py` / 四个 py 节点名）精确清理，**绝不使用通用
  `gz sim` / `rviz2` / `parameter_bridge` 关键词 pkill**。

在老师独占的 Ubuntu / VMware 上这组值同样适用，无需改动。
所有课堂脚本（`check_w12.sh` / `drive_demo.sh` / `save_map.sh`）都会先
`source env.sh`，所以另开终端直接执行即可，不用手动 export。

---

## 八、PID 演示怎么开

```bash
MODE=pid bash 01_启动课堂.sh      # 自动把 load_factor 设成 0.65
bash src/week12_odometry/scripts/drive_demo.sh a
```

`passthrough` 模式开车是开环直通；`pid` 模式会给电机注入 0.65 的教学负载
（模拟爬坡 / 打滑），网页看板②号格会出现「目标 0.350 / 实测 0.32 /
输出 0.49–0.52」三条线分开又合拢的过程。这是**人为教学扰动**，真实机器人
恒为 1.0，讲完务必切回默认模式。

---

## 九、2026-11-13 实测记录（DGX spark-a8d2）

| 项 | 实测值 |
|---|---|
| 环境 | Ubuntu 24.04.4 LTS / aarch64 / ROS 2 Jazzy / Gazebo Harmonic 8.11.0 |
| 构建 | `colcon build` 2 包，0.50 s，EXIT=0 |
| 自检 | `check_w12.sh` **PASS=24 / FAIL=0 / SKIP=0** |
| `/clock` 发布者 | 1（正确） |
| 控制器 | `joint_state_broadcaster` + `diff_drive_controller` 均 active |
| `cmd_vel` 类型 | `geometry_msgs/msg/TwistStamped` |
| 话题频率 | odom 98.3–99.7 Hz / scan 9.8–10.0 Hz / map 1–2 Hz |
| A 段直行 | odom 2.4363 m vs 真值 2.4361 m，误差 **0.2 mm** |
| A+B+C 综合 | odom (0.8345, 0.969) vs 真值 (0.8436, 0.9671)，误差 **9.3 mm** |
| PID 闭环 | target 0.350 / measured 0.318–0.334 / out 0.487–0.516（load 0.65） |
| SLAM | `lifecycle=active [3]`，`/map` Publisher count=1，199×199 @ 0.05 m |
| 地图存盘 | `w12_map_20261113_235253.pgm` + `.yaml` |
| 网页看板 | `http://127.0.0.1:8130/` HTTP 200，四宫格全部有数据 |
| 桌面窗口 | Gazebo Sim / RViz2 / Firefox 看板 三个窗口均真实可见 |
| 生产隔离 | 同机 W11 演示与三人小组 4 个进程全程未受影响 |
'''


if __name__ == '__main__':
    os.makedirs(SCRIPTS, exist_ok=True)
    for name, text in SCR.items():
        p = os.path.join(SCRIPTS, name)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        print('  + scripts/', name, len(text.splitlines()), 'lines')
    for name, text in TOP.items():
        p = os.path.join(ROOT, name)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        print('  +', name, len(text.splitlines()), 'lines')
    print('[part2b] done')
