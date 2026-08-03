"""Build a deterministic standalone GaussPatrol competition bundle."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import zipfile


PROJECT = Path(__file__).resolve().parents[1]
DIST = PROJECT / "dist"
ARCHIVE = DIST / "GaussPatrol-GOAI-2026.zip"
CHECKSUM = DIST / "GaussPatrol-GOAI-2026.zip.sha256"
EXCLUDED = {"__pycache__", ".pytest_cache", "dist", "local_run"}


def source_files() -> list[Path]:
    return sorted(
        (
            path
            for path in PROJECT.rglob("*")
            if path.is_file()
            and not any(part in EXCLUDED for part in path.relative_to(PROJECT).parts)
            and not path.name.endswith((".pyc", ".pyo"))
        ),
        key=lambda path: path.as_posix(),
    )


def build() -> tuple[Path, Path]:
    DIST.mkdir(exist_ok=True)
    manifest_lines = []
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in source_files():
            relative = path.relative_to(PROJECT).as_posix()
            content = path.read_bytes()
            info = zipfile.ZipInfo(f"GaussPatrol-GOAI-2026/{relative}", date_time=(2026, 8, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            bundle.writestr(info, content)
            manifest_lines.append(f"{sha256(content).hexdigest()}  {relative}")
        manifest = ("\n".join(manifest_lines) + "\n").encode("utf-8")
        info = zipfile.ZipInfo("GaussPatrol-GOAI-2026/SHA256SUMS.txt", date_time=(2026, 8, 4, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        bundle.writestr(info, manifest)
    CHECKSUM.write_text(f"{sha256(ARCHIVE.read_bytes()).hexdigest()}  {ARCHIVE.name}\n", encoding="utf-8", newline="\n")
    return ARCHIVE, CHECKSUM


if __name__ == "__main__":
    archive, checksum = build()
    print(archive)
    print(checksum)
