"""Reject incomplete project folders and broken local README links."""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "projects"


def main() -> None:
    projects = sorted(path for path in PROJECTS.iterdir() if path.is_dir())
    if len(projects) != 8:
        raise RuntimeError(f"expected 8 projects, found {len(projects)}")
    for project in projects:
        required = [project / "README.md", project / "src", project / "tests"]
        missing = [path for path in required if not path.exists()]
        if missing:
            raise RuntimeError(f"{project.name} missing: {missing}")

    markdown_files = [ROOT / "README.md", ROOT / "README_EN.md", *ROOT.rglob("projects/*/README.md")]
    pattern = re.compile(r"\[[^]]+\]\((?!https?://|#|mailto:)([^)]+)\)")
    for document in markdown_files:
        for target in pattern.findall(document.read_text(encoding="utf-8")):
            clean_target = target.split("#", 1)[0]
            if clean_target and not (document.parent / clean_target).resolve().exists():
                raise RuntimeError(f"broken link in {document.relative_to(ROOT)}: {target}")
    print("layout: 8 projects complete; local README links valid")


if __name__ == "__main__":
    main()
