"""Discover and run each project's tests without installing a shared package."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


EXPECTED_MIN = 10  # 09 是归档型项目无 tests；10 是 ROS2 课程平台，含 2 个测试文件


def main() -> None:
    test_files = sorted((ROOT / "projects").glob("*/tests/test_*.py"))
    if len(test_files) < EXPECTED_MIN:
        raise RuntimeError(f"expected at least {EXPECTED_MIN} project test files, found {len(test_files)}")
    for test_file in test_files:
        print(f"\n=== {test_file.relative_to(ROOT)} ===", flush=True)
        subprocess.run([sys.executable, str(test_file), "-v"], cwd=test_file.parents[1], check=True)


if __name__ == "__main__":
    main()
