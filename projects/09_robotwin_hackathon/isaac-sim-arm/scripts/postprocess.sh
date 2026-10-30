#!/usr/bin/env bash
# 后处理：把 OpenCV 写的 mpeg4 视频转成浏览器兼容的 h264，并抽海报帧/关键帧
set -u
cd "$(dirname "$0")"

echo "=== 1) 转码 h264（浏览器兼容） ==="
for pair in "rgb_cube_sorter_wide:wide" "rgb_cube_sorter_dashboard:dashboard"; do
  src="videos/${pair%%:*}.mp4"
  dst="videos/sorter_${pair##*:}.mp4"
  if [ ! -f "$src" ]; then echo "  [跳过] 源文件不存在: $src"; continue; fi
  ffmpeg -y -v error -i "$src" \
    -c:v libx264 -preset veryfast -crf 24 -pix_fmt yuv420p \
    -movflags +faststart -an "$dst"
  echo "  $dst  $(du -h "$dst" | cut -f1)"
done

echo "=== 2) 抽海报帧 ==="
ffmpeg -y -v error -ss 1 -i videos/sorter_wide.mp4 -frames:v 1 -q:v 3 frames/poster_wide.jpg
ffmpeg -y -v error -ss 1 -i videos/sorter_dashboard.mp4 -frames:v 1 -q:v 3 frames/poster_dash.jpg
ls -la frames/poster_*.jpg

echo "=== 3) 抽关键帧（按分拣进度 30% / 55% / 80%） ==="
DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 videos/sorter_wide.mp4)
echo "  宽视角时长 ${DUR}s"
for spec in "0.30:key_1" "0.55:key_2" "0.80:key_3"; do
  r="${spec%%:*}"; name="${spec##*:}"
  t=$(awk -v d="$DUR" -v r="$r" 'BEGIN{printf "%.2f", d*r}')
  ffmpeg -y -v error -ss "$t" -i videos/sorter_wide.mp4 -frames:v 1 -q:v 3 "frames/${name}.jpg"
  echo "  frames/${name}.jpg @ ${t}s"
done

echo "=== 4) 结果 ==="
ls -la videos/ frames/
