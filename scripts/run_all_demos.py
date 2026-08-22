"""Run every self-contained demo and emit one machine-readable JSON document."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DEMOS = {
    "01_quadruped_slam": ROOT / "projects/01_quadruped_slam/src/quadruped_slam.py",
    "02_ginger_robot": ROOT / "projects/02_ginger_robot/src/ginger_control.py",
    "03_geoscan_pro": ROOT / "projects/03_geoscan_pro/src/geoscan.py",
    "04_industrial_vision": ROOT / "projects/04_industrial_vision/src/industrial_vision.py",
    "05_ros2_3dgs": ROOT / "projects/05_ros2_3dgs/src/gaussian_ros_viz.py",
    "06_bms": ROOT / "projects/06_bms/src/bms.py",
    "07_gausspatrol": ROOT / "projects/07_gausspatrol/run_demo.py",
    "08_3dgs_scanner_soft_hardware": ROOT / "projects/08_3dgs_scanner_soft_hardware/src/project_manifest.py",
    "09_cvat_sop_offline": ROOT / "projects/09_cvat_sop_offline/src/delivery_manifest.py",
}


def run_all() -> dict[str, object]:
    results: dict[str, object] = {}
    child_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    for name, script in DEMOS.items():
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=script.parents[1],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=child_env,
        )
        results[name] = json.loads(completed.stdout)
    return results


if __name__ == "__main__":
    print(json.dumps(run_all(), ensure_ascii=False, indent=2, sort_keys=True))
