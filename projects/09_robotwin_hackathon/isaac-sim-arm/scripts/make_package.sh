#!/usr/bin/env bash
# ============================================================================
#  打交付包：代码 / 算法与设计文档 / 前端 / 后端 / 媒体 / 日志 / 自定义 kit
#  排除：上游 41 MB 演示媒体、OpenCV 中转临时目录、字体（16.8 MB，仅渲染用）、截图工作区
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

NAME="isaac-arm-sorter-2026-10"
DIST="dist/$NAME"
ZIP="dist/${NAME}.zip"
KIT_SRC="D:/nvidia/Isaac/IsaacLab/apps/isaaclab.arm.sorter.headless.kit"

echo "=== 清理旧包 ==="
rm -rf "$DIST" "$ZIP"
mkdir -p "$DIST"/{isaac,data,videos,photos,frames,logs,repo_isaacsim_robotics_portfolio}

echo "=== 1. 复现代码 + 前端 + 后端 + 流水线脚本 ==="
for f in run_rgb_cube_sorter_45.py serve.py launch.py \
         index.html style.css app.js README.md \
         extract_curves.py map_highlights.py check_site.py \
         make_highlight.sh make_detect.sh make_photos.sh postprocess.sh; do
  if [ -f "$f" ]; then cp -p "$f" "$DIST/"; printf "  + %-32s %8.1f KB\n" "$f" "$(stat -c%s "$f" | awk '{print $1/1024}')"
  else echo "  ! 缺失 $f"; fi
done

echo "=== 2. 自定义 experience kit ==="
if [ -f "$KIT_SRC" ]; then
  cp -p "$KIT_SRC" "$DIST/isaac/"
  printf "  + isaac/isaaclab.arm.sorter.headless.kit  %8.1f KB\n" "$(stat -c%s "$KIT_SRC" | awk '{print $1/1024}')"
else
  echo "  ! 找不到 kit: $KIT_SRC"; exit 1
fi

echo "=== 3. 数据 ==="
cp -p data/*.json "$DIST/data/" && echo "  + data/ $(ls -1 data/*.json | wc -l) 个 json"

echo "=== 4. 视频（全部 4 个成片）==="
cp -p videos/*.mp4 "$DIST/videos/" && du -sh "$DIST/videos"

echo "=== 5. 照片 / 帧 ==="
cp -p photos/*.jpg "$DIST/photos/" && echo "  + photos/ $(ls -1 photos/*.jpg | wc -l) 张"
cp -p frames/poster_*.jpg frames/key_*.jpg "$DIST/frames/" 2>/dev/null && echo "  + frames/ $(ls -1 "$DIST/frames" | wc -l) 个"

echo "=== 6. 日志（原始全量）==="
cp -p logs/run_rgb_cube_sorter.log logs/train_franka_lift.log \
      logs/rgb_cube_sorter_summary.json logs/*_summary.json "$DIST/logs/" 2>/dev/null || true
du -sh "$DIST/logs"

echo "=== 7. 上游源码副本（剔除 41 MB media/）==="
if [ -d repo_isaacsim_robotics_portfolio ]; then
  ( cd repo_isaacsim_robotics_portfolio && \
    find . -path ./media -prune -o -type f -print0 | \
    tar --null -cf - --files-from=- ) | ( cd "$DIST/repo_isaacsim_robotics_portfolio" && tar -xf - )
  du -sh "$DIST/repo_isaacsim_robotics_portfolio"
  echo "  （上游 media/ 41 MB 演示 GIF/MP4 按设计排除）"
fi

echo "=== 8. 写 MANIFEST ==="
(
  cd "$DIST"
  {
    echo "# ${NAME} 交付清单"
    echo "# 生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "# 本机: $(hostname)"
    echo
    printf "%-58s %10s\n" "文件" "字节"
    printf "%-58s %10s\n" "----------------------------------------------------------" "----------"
    find . -type f ! -name MANIFEST.txt -printf "%p\t%s\n" | sort | while IFS=$'\t' read -r p s; do
      printf "%-58s %10s\n" "${p#./}" "$s"
    done
    echo
    echo "# 合计文件数: $(find . -type f ! -name MANIFEST.txt | wc -l)"
    echo "# 合计字节: $(find . -type f ! -name MANIFEST.txt -printf "%s\n" | awk '{s+=$1} END{print s}')"
  } > MANIFEST.txt
  grep -E "^# 合计" MANIFEST.txt
)

echo "=== 9. 压缩 ==="
( cd dist && rm -f "${NAME}.zip" && \
  zip -r -9 -q "${NAME}.zip" "$NAME" && \
  echo "  完成: dist/${NAME}.zip" )
ls -la "$ZIP" | awk '{printf "  包体积: %.2f MB\n", $5/1048576}'
