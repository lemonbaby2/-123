#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""无 ROS 依赖的课堂演示：0.35 m/s 目标速度 + 0.65 人为负载下的速度环。

输出为一行 JSON，便于 CI 或面试现场直接解析。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from course_algorithms import PIDController, relative_error_percent  # noqa: E402


def main():
    pid = PIDController(kp=1.8, ki=0.35, kd=0.02, max_output=0.8)
    target, load, measured = 0.35, 0.65, 0.0
    samples = []
    for i in range(300):
        err, p, integ, d, out = pid.step(target, measured, 0.05)
        measured += (out * load - measured) * 0.3
        if i % 50 == 0:
            samples.append({"step": i, "target": round(target, 4),
                            "measured": round(measured, 4),
                            "output": round(out, 4)})
    released = pid.step(0.0, measured, 0.05)
    print(json.dumps({
        "scenario": "velocity PID with injected 0.65 load",
        "target_mps": target,
        "final_measured_mps": round(measured, 4),
        "final_relative_error_pct": round(relative_error_percent(measured, target), 3),
        "release_output": round(released[-1], 4),
        "samples": samples,
        "note": "load_factor is a teaching disturbance, not a real robot model",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
