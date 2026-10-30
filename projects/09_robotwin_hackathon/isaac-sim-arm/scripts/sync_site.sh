#!/usr/bin/env bash
# ============================================================================
#  生成「公网部署子集」：只含网页运行时真正需要的文件
#  排除：日志、上游仓库副本、交付包 zip、字体、截图工作区、构建脚本
#  用途：上传体积从 ~90 MB 压到 ~21 MB，同时保证页面 100% 可渲染
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

OUT="dist/site"

echo "=== 重建 $OUT ==="
rm -rf "$OUT"
mkdir -p "$OUT"/{videos,photos,frames,data}

echo "=== 前端三件套 ==="
cp -p index.html style.css app.js "$OUT/"
printf "  index.html %6.1f KB | style.css %6.1f KB | app.js %6.1f KB\n" \
  "$(stat -c%s index.html | awk '{print $1/1024}')" \
  "$(stat -c%s style.css   | awk '{print $1/1024}')" \
  "$(stat -c%s app.js      | awk '{print $1/1024}')"

echo "=== 视频 ==="
cp -p videos/*.mp4 "$OUT/videos/"

echo "=== 照片 ==="
cp -p photos/*.jpg "$OUT/photos/"

echo "=== 帧图 / 海报 ==="
cp -p frames/*.jpg "$OUT/frames/"

echo "=== 数据 ==="
cp -p data/*.json "$OUT/data/"

echo
echo "=== 校验完整性 ==="
python_bin="C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe"
if [ -x "$python_bin" ]; then
  ( cd "$OUT" && "$python_bin" - <<'PY'
import os, re, sys
html = open("index.html", encoding="utf-8").read()
refs = {m.group(1).split("?")[0] for m in re.finditer(r'(?:src|href)="([^"#][^"]*)"', html)}
refs = {r for r in refs if not r.startswith(("http", "mailto:", "data:"))}
refs |= {"data/curves_franka_lift.json"}          # app.js 里 fetch 的
miss = [r for r in sorted(refs) if not os.path.isfile(r)]
print(f"  引用 {len(refs)} 项，缺失 {len(miss)}")
for m in miss:
    print("  MISS", m)
sys.exit(1 if miss else 0)
PY
  )
fi

echo
du -sh "$OUT"
echo "=== 目录构成 ==="
du -sh "$OUT"/*/ | sort -h
echo "=== 文件数 ==="
find "$OUT" -type f | wc -l
