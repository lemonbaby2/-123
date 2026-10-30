#!/usr/bin/env bash
# ============================================================================
#  从 333 秒完整录屏中剪出 1~2 分钟精华片
#  时间轴依据：logs/run_rgb_cube_sorter.log 中 8 次 "SUCCESS: Sorted" 的仿真步数
#     视频 30fps × 每 2 步写 1 帧 → 60 步/秒
#     成功时刻 = 23.0 / 46.5 / 69.5 / 93.0 / 116.5 / 140.0 / 163.5 / 187.0 s
#  段落切分（每段都覆盖完整的「对位 → 下探 → 夹取 → 抬升 → 入仓」）：
#     A   2.0 ~  23.5   首件 green 全流程            21.5 s
#     B  90.0 ~ 165.5   red / blue / red / blue      75.5 s
#     C 329.0 ~ 333.3   最终仓内 8 件定格              4.3 s
#  三阶段执行，避免一次性解码多路 333s 源导致 OOM：
#     step1 切段（独立进程，各自只解一段）  step2 交叉淡化拼接  step3 烧字+淡入淡出
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

SRC="videos/sorter_wide.mp4"
FONT="assets/fonts/font.ttc"
TMP="assets/_hl_tmp"
OUT="videos/sorter_highlight.mp4"
mkdir -p "$TMP" videos

[ -f "$SRC" ] || { echo "缺少 $SRC"; exit 1; }
[ -f "$FONT" ] || { echo "缺少 $FONT"; exit 1; }

# ---- 段落参数 -------------------------------------------------------------
A_S=2.0;   A_E=23.5
B_S=90.0;  B_E=165.5
C_S=329.0; C_E=333.30
XF=0.8

cut() {  # $1=start $2=end $3=out
  echo "--- 切段 $3 : $1 -> $2"
  ffmpeg -y -v error -ss "$1" -to "$2" -i "$SRC" -an \
    -c:v libx264 -preset veryfast -crf 16 -pix_fmt yuv420p -r 30 "$3"
}

# ---- step1 切段 -----------------------------------------------------------
cut $A_S $A_E "$TMP/segA.mp4"
cut $B_S $B_E "$TMP/segB.mp4"
cut $C_S $C_E "$TMP/segC.mp4"

A_D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TMP/segA.mp4")
B_D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TMP/segB.mp4")
C_D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TMP/segC.mp4")
echo "实际段长 A=$A_D B=$B_D C=$C_D"

OFF1=$(awk "BEGIN{printf \"%.3f\", $A_D-$XF}")
AB_D=$(awk "BEGIN{printf \"%.3f\", $A_D+$B_D-$XF}")
OFF2=$(awk "BEGIN{printf \"%.3f\", $AB_D-$XF}")
TOTAL=$(awk "BEGIN{printf \"%.3f\", $AB_D+$C_D-$XF}")
FADE_OUT_ST=$(awk "BEGIN{printf \"%.3f\", $TOTAL-0.9}")
echo "offset1=$OFF1 offset2=$OFF2 总长=$TOTAL fadeout@$FADE_OUT_ST"

# ---- step2 交叉淡化拼接 ---------------------------------------------------
echo "--- 拼接 + 交叉淡化"
ffmpeg -y -v error -stats -i "$TMP/segA.mp4" -i "$TMP/segB.mp4" -i "$TMP/segC.mp4" \
  -filter_complex "\
[0:v]fps=30,format=yuv420p[a];\
[1:v]fps=30,format=yuv420p[b];\
[2:v]fps=30,format=yuv420p[c];\
[a][b]xfade=transition=fade:duration=${XF}:offset=${OFF1}[ab];\
[ab][c]xfade=transition=fadeblack:duration=${XF}:offset=${OFF2}[v]" \
  -map "[v]" -an -c:v libx264 -preset veryfast -crf 16 -pix_fmt yuv420p "$TMP/joined.mp4"

JOINED_D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TMP/joined.mp4")
echo "拼接后实际时长 = $JOINED_D"
FADE_OUT_ST=$(awk "BEGIN{printf \"%.3f\", $JOINED_D-0.9}")
OUTRO_ST=$(awk "BEGIN{printf \"%.3f\", $JOINED_D-4.6}")

# ---- step3 烧标题 + 首尾淡入淡出 -----------------------------------------
echo "--- 烧录标题与结果说明"
ffmpeg -y -v error -stats -i "$TMP/joined.mp4" -filter_complex "\
[0:v]drawbox=x=0:y=0:w=iw:h=150:color=black@0.55:t=fill:enable='between(t,0.3,5.0)',\
drawtext=fontfile=${FONT}:text='Isaac Lab 机械臂 RGB 分拣 · 完整复现实录':fontcolor=white:fontsize=46:x=60:y=32:enable='between(t,0.3,5.0)',\
drawtext=fontfile=${FONT}:text='Isaac Sim 4.5 + Isaac Lab 2.1.1 · PickPlaceController + RMPFlow · Franka Panda':fontcolor=0x9AE6B4:fontsize=23:x=62:y=96:enable='between(t,0.3,5.0)',\
drawbox=x=0:y=ih-150:w=iw:h=150:color=black@0.58:t=fill:enable='gte(t,${OUTRO_ST})',\
drawtext=fontfile=${FONT}:text='最终结果：8 件成功入仓（红 3 / 绿 2 / 蓝 3）':fontcolor=white:fontsize=40:x=60:y=h-118:enable='gte(t,${OUTRO_ST})',\
drawtext=fontfile=${FONT}:text='其余 4 件被邻件遮挡：Y 向与 X 向夹爪间隙检测均不通过 → 主动跳过（非抓取失败）':fontcolor=0xFBD38D:fontsize=21:x=62:y=h-58:enable='gte(t,${OUTRO_ST})',\
fade=t=in:st=0:d=0.7,fade=t=out:st=${FADE_OUT_ST}:d=0.9,format=yuv420p[v]" \
  -map "[v]" -an -c:v libx264 -preset slow -crf 21 -pix_fmt yuv420p -movflags +faststart "$OUT"

echo "==> 写出 $OUT"
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,nb_frames,duration -of default=noprint_wrappers=1 "$OUT"
ls -la "$OUT" | awk '{printf "体积 %.2f MB\n", $5/1048576}'
