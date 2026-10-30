"""从 rsl_rl 的 tfevents 文件里抽出训练曲线，输出 JSON 供前端绘图。

用法:
    python extract_curves.py <tfevents文件> <输出json> [max_points]

与上一版（Go2）相比：
  - 任务换成 Isaac-Lift-Cube-Franka-v0，奖励/终止项 tag 名完全不同
  - 因此不再写死 keep 白名单，而是全量导出 + 等间隔降采样到 max_points 点
  - 前端按 tag 名正则挑要画的曲线
"""

import json
import os
import sys

from tensorboard.backend.event_processing.event_accumulator import EventAccumulator


def downsample(points, max_points):
    n = len(points)
    if n <= max_points:
        return points
    step = n / float(max_points)
    out = [points[int(i * step)] for i in range(max_points)]
    if out[-1] != points[-1]:
        out.append(points[-1])
    return out


def main() -> int:
    if len(sys.argv) < 3:
        print("用法: python extract_curves.py <tfevents文件> <输出json> [max_points]")
        return 2

    event_path = sys.argv[1]
    out_path = sys.argv[2]
    max_points = int(sys.argv[3]) if len(sys.argv) > 3 else 400

    acc = EventAccumulator(
        event_path,
        size_guidance={
            "scalars": 0,
            "tensors": 0,
            "histograms": 0,
            "images": 0,
            "audio": 0,
            "compressedHistograms": 0,
            "graph": 0,
            "meta_graph": 0,
            "run_metadata": 0,
        },
    )
    acc.Reload()

    tags = acc.Tags().get("scalars", [])
    series = {}
    for tag in tags:
        events = acc.Scalars(tag)
        if not events:
            continue
        pts = [{"step": int(e.step), "value": round(float(e.value), 6)} for e in events]
        series[tag] = downsample(pts, max_points)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {"tags": sorted(series.keys()), "raw_counts": {k: len(acc.Scalars(k)) for k in series},
             "series": series},
            f,
            ensure_ascii=False,
        )

    print(f"已写出 {out_path}  （{len(series)} 条标量，每条最多 {max_points} 点）")
    for k in sorted(series.keys()):
        pts = series[k]
        print(f"  {k:52s} {len(pts):4d} 点  末值={pts[-1]['value']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
