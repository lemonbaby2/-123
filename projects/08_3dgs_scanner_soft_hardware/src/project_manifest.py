"""Machine-readable manifest for the 3DGS scanner soft-hardware archive."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def build_manifest() -> dict[str, object]:
    files = sorted(path for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts)
    by_suffix: dict[str, int] = {}
    total_bytes = 0
    for path in files:
        suffix = path.suffix.lower() or "<none>"
        by_suffix[suffix] = by_suffix.get(suffix, 0) + 1
        total_bytes += path.stat().st_size

    return {
        "project": "08_3dgs_scanner_soft_hardware",
        "title": "3DGS Scanner Soft-Hardware Project",
        "root": str(ROOT),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "file_types": by_suffix,
        "key_outputs": [
            "README.md",
            "docs/hardware_overview.md",
            "docs/engineering_report/BMS_SLAM_Bringup_Analysis_Report_V1.0_2026-08-03.pdf",
            "docs/engineering_report/BMS_SLAM_Bringup_Test_Matrix_V1.0_2026-08-03.xlsx",
            "docs/references/research_repositories.md",
        ],
        "safety_gate": "Do not connect a real 3S2P pack until the BQ76920 VC mapping and true BMS PCB package are corrected.",
    }


if __name__ == "__main__":
    print(json.dumps(build_manifest(), ensure_ascii=False, indent=2, sort_keys=True))
