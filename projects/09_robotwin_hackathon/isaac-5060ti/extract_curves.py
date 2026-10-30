"""从 rsl_rl 的 tfevents 文件里抽出训练曲线，输出 JSON 供前端绘图。

用法:
    python extract_curves.py <tfevents文件> <输出json>
"""

import json
import os
import sys

from tensorboard.backend.event_processing.event_accumulator import EventAccumulator


def main() -> int:
    if len(sys.argv) < 3:
        print("用法: python extract_curves.py <tfevents文件> <输出json>")
        return 2

    event_path = sys.argv[1]
    out_path = sys.argv[2]

    acc = EventAccumulator(
        event_path,
        size_guidance={
            "scalars": 0,          # 0 = 全部载入
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
        # rsl_rl 记录的 step 就是迭代数
        series[tag] = [
            {"step": int(e.step), "value": round(float(e.value), 6)} for e in events
        ]

    # 只抽出画主图需要的几条，避免 JSON 过大
    keep = {
        "Train/mean_reward",
        "Train/mean_episode_length",
        "Train/mean_value_loss",
        "Train/mean_surrogate_loss",
        "Train/learning_rate",
        "Train/mean_noise_std",
        "Episode/Reward/track_lin_vel_xy_exp",
        "Episode/Reward/track_ang_vel_z_exp",
        "Episode_Termination/base_contact",
        "Metrics/base_velocity/error_vel_xy",
        "Metrics/base_velocity/error_vel_yaw",
        "Episode/Total_reward",
        "Episode/Length",
        "Loss/value_function",
        "Loss/surrogate",
        "Policy/learning_rate",
    }
    picked = {k: v for k, v in series.items() if k in keep}
    # 若 keep 一个都没命中，就把全部标量都吐出去
    if not picked:
        picked = series

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"tags": sorted(picked.keys()), "series": picked}, f, ensure_ascii=False)

    print(f"已写出 {out_path}")
    for k in sorted(picked.keys()):
        pts = picked[k]
        print(f"  {k:48s} {len(pts):4d} 点  末值={pts[-1]['value']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
