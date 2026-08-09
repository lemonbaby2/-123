from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from project_manifest import build_manifest  # noqa: E402


class ProjectManifestTests(unittest.TestCase):
    def test_manifest_counts_archive_files(self) -> None:
        manifest = build_manifest()
        self.assertEqual(manifest["project"], "08_3dgs_scanner_soft_hardware")
        self.assertGreaterEqual(manifest["file_count"], 30)
        self.assertIn(".pdf", manifest["file_types"])
        self.assertIn(".docx", manifest["file_types"])
        self.assertIn(".xlsx", manifest["file_types"])

    def test_safety_gate_is_visible(self) -> None:
        manifest = build_manifest()
        self.assertIn("BQ76920", manifest["safety_gate"])
        self.assertIn("3S2P", manifest["safety_gate"])


if __name__ == "__main__":
    unittest.main()
