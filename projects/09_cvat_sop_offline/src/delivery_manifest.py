"""Emit the public deployment contract without requiring Docker."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def build_manifest() -> dict[str, object]:
    required = {
        "cvat_compose": ROOT / "cvat-overlay" / "docker-compose.windows.yml",
        "cvat_launcher_source": ROOT / "windows" / "CvatOfflineLauncher.cs",
        "sop_compose": ROOT / "sop" / "docker-compose.yml",
        "restore_script": ROOT / "scripts" / "Restore-CvatVolumes.ps1",
    }
    return {
        "project": "cvat-sop-offline",
        "cvat_version": "2.73.1",
        "localhost_ports": {"cvat": 8081, "sop": 8096},
        "public_files_complete": all(path.is_file() for path in required.values()),
        "artifacts": sorted(required),
        "private_payload_in_repository": False,
    }


if __name__ == "__main__":
    print(json.dumps(build_manifest(), ensure_ascii=False, sort_keys=True))

