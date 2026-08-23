#!/usr/bin/env bash
set -euo pipefail

gateway_url="${SOP_CAMERA_GATEWAY_URL:-http://127.0.0.1:8112}"
gateway_token="${SOP_CAMERA_GATEWAY_TOKEN:?SOP_CAMERA_GATEWAY_TOKEN is required}"
rtsp_base="${SOP_CAMERA_RTSP_BASE:-rtsp://127.0.0.1:8554}"
pids=()

stop_publishers() {
  if ((${#pids[@]})); then
    kill "${pids[@]}" 2>/dev/null || true
    wait "${pids[@]}" 2>/dev/null || true
  fi
}
trap stop_publishers EXIT INT TERM

for camera_id in 0 1 2; do
  ffmpeg -nostdin -hide_banner -loglevel warning \
    -i "${gateway_url}/api/camera/mjpeg?camera=${camera_id}&gateway_token=${gateway_token}" \
    -an -vf "fps=12,scale='min(1280,iw)':-2" \
    -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p -g 24 \
    -f rtsp -rtsp_transport tcp "${rtsp_base}/cam${camera_id}" &
  pids+=("$!")
done

wait -n "${pids[@]}"
