#!/usr/bin/env bash
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
