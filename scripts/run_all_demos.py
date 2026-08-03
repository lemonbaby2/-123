"""Run all demos directly from a source checkout without installing the package."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from portfolio_demos.cli import main  # noqa: E402


if __name__ == "__main__":
    sys.argv = [sys.argv[0], "all"]
    main()
