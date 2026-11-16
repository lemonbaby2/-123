#!/usr/bin/env bash
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
