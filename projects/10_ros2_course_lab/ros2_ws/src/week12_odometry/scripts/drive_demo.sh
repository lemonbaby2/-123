#!/usr/bin/env bash
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
