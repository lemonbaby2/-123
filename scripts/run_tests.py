"""Discover and run each project's tests without installing a shared package."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    test_files = sorted((ROOT / "projects").glob("*/tests/test_*.py"))
    if len(test_files) != 7:
        raise RuntimeError(f"expected 7 project test files, found {len(test_files)}")
    for test_file in test_files:
        print(f"\n=== {test_file.relative_to(ROOT)} ===", flush=True)
        subprocess.run([sys.executable, str(test_file), "-v"], cwd=test_file.parents[1], check=True)


if __name__ == "__main__":
    main()
