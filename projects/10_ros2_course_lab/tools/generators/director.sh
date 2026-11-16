#!/usr/bin/env bash
# W13 五分钟演示片 · 录屏导演脚本
# 依赖：DISPLAY=:1 + XAUTHORITY + 已在跑的 W12 全栈（Gazebo / RViz / 看板）
# 说明：整段 300 s 连续录制，按时间线在三个窗口间切换，同时循环跑 A/B/C 三段动作。
set -eo pipefail

export DISPLAY="${DISPLAY:-:1}"
export XAUTHORITY="${XAUTHORITY:-/run/user/1000/gdm/Xauthority}"

WS=/home/nvidia/ros2_ws_w12
OUT="${1:-/tmp/w13_demo_raw.mp4}"
DUR="${2:-300}"

log() { printf '[director %s] %s\n' "$(date +%H:%M:%S)" "$*"; }

find_win() {
  wmctrl -l | grep -F "$1" | head -1 | awk '{print $1}'
}

GZ=$(find_win 'Gazebo Sim')
RV=$(find_win 'demo_w12.rviz')
DB=$(find_win '课堂看板')
log "窗口：Gazebo=$GZ RViz=$RV 看板=$DB"
[ -n "$GZ" ] && [ -n "$RV" ] && [ -n "$DB" ] || { echo '窗口缺失，终止'; exit 2; }

# 1) 三个窗口统一铺满 1920x1080
for w in "$GZ" "$RV" "$DB"; do
  wmctrl -i -r "$w" -b remove,maximized_vert,maximized_horz 2>/dev/null || true
  wmctrl -i -r "$w" -e "0,0,0,1920,1080" 2>/dev/null || true
done
sleep 3

# 2) 后台循环跑车（每轮 A/B/C 约 55 s）
setsid nohup bash -c "for i in 1 2 3 4 5 6; do bash $WS/src/week12_odometry/scripts/drive_demo.sh all; sleep 2; done" \
  > /tmp/w13_drive.log 2>&1 < /dev/null &
log '跑车循环已启动'

# 3) 连续录屏
ffmpeg -hide_banner -loglevel warning -y \
  -f x11grab -framerate 15 -video_size 1920x1080 -i :1.0 \
  -t "$DUR" -c:v libx264 -preset veryfast -crf 24 -pix_fmt yuv420p \
  -movflags +faststart "$OUT" > /tmp/w13_ffmpeg.log 2>&1 &
FF=$!
log "录制中：${DUR}s → $OUT (pid $FF)"
sleep 3

# 4) 导演时间线
wmctrl -i -a "$GZ"; log '段落 1：Gazebo 世界与模型'
sleep 80
wmctrl -i -a "$RV"; log '段落 2：RViz 里程计轨迹 / 激光 / SLAM 地图'
sleep 75
wmctrl -i -a "$DB"; log '段落 3：网页看板 PID 闭环'
sleep 85
wmctrl -i -a "$GZ"; log '段落 4：回到 Gazebo 收尾'

wait "$FF" || true
log '录制结束'
ls -la "$OUT"
ffprobe -v error -show_entries format=duration,size -show_entries stream=width,height,codec_name -of default=noprint_wrappers=1 "$OUT" 2>&1 | head -12
echo REC_DONE
