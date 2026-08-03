"""Build a deterministic, source-only offline portfolio bundle."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
ARCHIVE = DIST / "lizipeng-embodied-ai-portfolio.zip"
EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", ".venv", "build", "install", "log"}


def source_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.relative_to(ROOT).parts):
            continue
        if path == ARCHIVE or path.name.endswith((".pyc", ".pyo")) or path.name == "SHA256SUMS.txt":
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.as_posix())


def build() -> tuple[Path, Path]:
    DIST.mkdir(exist_ok=True)
    files = source_files()
    manifest_lines = []
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            content = path.read_bytes()
            info = zipfile.ZipInfo(f"lizipeng-embodied-ai-portfolio/{relative}", date_time=(2026, 8, 3, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            bundle.writestr(info, content)
            manifest_lines.append(f"{sha256(content).hexdigest()}  {relative}")
        manifest = ("\n".join(manifest_lines) + "\n").encode("utf-8")
        info = zipfile.ZipInfo("lizipeng-embodied-ai-portfolio/SHA256SUMS.txt", date_time=(2026, 8, 3, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        bundle.writestr(info, manifest)
    checksum_path = DIST / "lizipeng-embodied-ai-portfolio.zip.sha256"
    checksum_path.write_text(f"{sha256(ARCHIVE.read_bytes()).hexdigest()}  {ARCHIVE.name}\n", encoding="utf-8")
    return ARCHIVE, checksum_path


if __name__ == "__main__":
    archive, checksum = build()
    print(archive)
    print(checksum)
