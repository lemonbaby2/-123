#!/usr/bin/env bash
# ============================================================================
#  「视觉感知流水线」讲解短片 1280x720
#  源：videos/sorter_dashboard.mp4 = np.vstack([vis_rgb, vis_depth, vis_mask])
#      即 3 行，每行 640x480，总 640x1440
#        行1 y=0    vis_rgb   顶视 RGB + ROI 黄框 + PICK/CLUTTER/BLOCKER + grip 方向线
#        行2 y=480  vis_depth cv2.COLORMAP_JET 伪彩（归一化后 蓝=近 红=远）
#        行3 y=960  vis_mask  红/绿/蓝 三段 HSV 阈值掩膜叠加
#  取 red #2 这一抓放循环：原始 78.0 ~ 92.0 s（共 14 s）
#  排版：2x2 网格，每格 640x360；内容按比例缩到 480x360 居中留黑边，第 4 格为判读图例
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

SRC="videos/sorter_dashboard.mp4"
FONT="assets/fonts/font.ttc"
OUT="videos/sorter_detect.mp4"
mkdir -p videos

[ -f "$SRC" ] || { echo "缺少 $SRC"; exit 1; }
[ -f "$FONT" ] || { echo "缺少 $FONT"; exit 1; }

S=78.0; E=92.0; D=14
CELL="scale=480:360,pad=640:360:80:0:color=black"
LBL="fontfile=${FONT}:fontsize=21:fontcolor=white:x=88:y=8:box=1:boxcolor=black@0.65:boxborderw=6"

ffmpeg -y -v error -stats -ss $S -to $E -i "$SRC" \
  -f lavfi -t $D -i "color=c=0x0e141b:s=640x360:r=60" \
  -filter_complex "\
[0:v]crop=640:480:0:0,  ${CELL},drawtext=${LBL}:text='① 顶视 RGB + 检测判读'[a];\
[0:v]crop=640:480:0:480,${CELL},drawtext=${LBL}:text='② 深度图 JET 伪彩（蓝近 红远）'[b];\
[0:v]crop=640:480:0:960,${CELL},drawtext=${LBL}:text='③ HSV 三段阈值掩膜（红/绿/蓝）'[c];\
[1:v]drawtext=fontfile=${FONT}:text='判读图例':fontcolor=0x9AE6B4:fontsize=25:x=28:y=22,\
drawtext=fontfile=${FONT}:text='绿框 PICK　　间隙足够，可安全抓取':fontcolor=0x86EFAC:fontsize=20:x=28:y=74,\
drawtext=fontfile=${FONT}:text='红框 CLUTTER　Y/X 两向均被挡，主动跳过':fontcolor=0xFCA5A5:fontsize=20:x=28:y=112,\
drawtext=fontfile=${FONT}:text='橙框 BLOCKER　造成遮挡的邻件':fontcolor=0xFDBA74:fontsize=20:x=28:y=150,\
drawtext=fontfile=${FONT}:text='绿竖线 Y-grip　常规夹持方向':fontcolor=0x86EFAC:fontsize=20:x=28:y=188,\
drawtext=fontfile=${FONT}:text='紫横线 X-grip　旋转 90° 后夹持':fontcolor=0xE9D5FF:fontsize=20:x=28:y=226,\
drawtext=fontfile=${FONT}:text='黄框为 ROI，ROI 外一律不计':fontcolor=0xFDE68A:fontsize=20:x=28:y=264,\
drawtext=fontfile=${FONT}:text='清障判据：夹爪体 45mm ／ 张开 100mm ／ 安全余量 5mm':fontcolor=0x94A3B8:fontsize=17:x=28:y=306[d];\
[a][b][c][d]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0[v]" \
  -map "[v]" -an -c:v libx264 -preset slow -crf 21 -pix_fmt yuv420p -movflags +faststart "$OUT"

echo "==> 写出 $OUT"
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,nb_frames,duration -of default=noprint_wrappers=1 "$OUT"
ls -la "$OUT" | awk '{printf "体积 %.2f MB\n", $5/1048576}'
