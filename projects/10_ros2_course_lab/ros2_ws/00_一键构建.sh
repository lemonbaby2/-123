#!/usr/bin/env bash
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
