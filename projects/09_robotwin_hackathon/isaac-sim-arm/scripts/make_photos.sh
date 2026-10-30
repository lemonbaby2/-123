#!/usr/bin/env bash
# ============================================================================
#  按 8 次成功放置的时间轴抽照片
#  成功时刻（wide / 30fps / 60 步每秒）：23.0 46.5 69.5 93.0 116.5 140.0 163.5 187.0
#  每个成功点抽 2 张：
#     *_carry.jpg  成功前 3.5 s，机械臂正夹持工件飞向目标仓（最有画面感）
#     *_placed.jpg 成功后 0.3 s，工件已落仓
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

SRC="videos/sorter_wide.mp4"
DIR="photos"
mkdir -p "$DIR"

TIMES=(23.0 46.5 69.5 93.0 116.5 140.0 163.5 187.0)
COLORS=(green red blue red blue red blue green)
TOTALS=(1 1 1 2 2 3 3 2)

[ -f "$SRC" ] || { echo "缺少 $SRC"; exit 1; }

for i in "${!TIMES[@]}"; do
  n=$(printf "%02d" $((i+1)))
  t=${TIMES[$i]}; c=${COLORS[$i]}; tot=${TOTALS[$i]}
  tc=$(awk "BEGIN{printf \"%.2f\", $t-3.5}")
  tp=$(awk "BEGIN{printf \"%.2f\", $t+0.3}")
  ffmpeg -y -v error -ss "$tc" -i "$SRC" -frames:v 1 -q:v 2 "$DIR/pick_${n}_${c}_carry.jpg"
  ffmpeg -y -v error -ss "$tp" -i "$SRC" -frames:v 1 -q:v 2 "$DIR/pick_${n}_${c}_placed.jpg"
  echo "第 ${n} 件 ${c}（累计 ${tot}）: carry@${tc}s  placed@${tp}s"
done

# 主视觉：开局无遮挡全景
ffmpeg -y -v error -ss 1.0 -i "$SRC" -frames:v 1 -q:v 2 "$DIR/hero_wide.jpg"
# 终局全景
ffmpeg -y -v error -ss 333.0 -i "$SRC" -frames:v 1 -q:v 2 "$DIR/final_sorted.jpg"

echo "--- 共 $(ls -1 "$DIR" | wc -l) 张"
du -sh "$DIR"
