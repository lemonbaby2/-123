from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeliveryLayoutTest(unittest.TestCase):
    def test_public_delivery_files_exist(self) -> None:
        required = [
            ROOT / "README.md",
            ROOT / "EVIDENCE.md",
            ROOT / "RESUME_PROJECT.md",
            ROOT / "sop" / "Dockerfile",
            ROOT / "sop" / "docker-compose.yml",
            ROOT / "sop" / "source" / "server.py",
            ROOT / "sop" / "source" / "requirements.txt",
            ROOT / "sop" / "source" / "web" / "index.html",
            ROOT / "sop" / "source" / "web" / "app.js",
            ROOT / "sop" / "source" / "web" / "styles.css",
            ROOT / "sop" / "source" / "config" / "network_cameras.example.json",
            ROOT / "scripts" / "Restore-CvatVolumes.ps1",
            ROOT / "windows" / "CvatOfflineLauncher.cs",
            ROOT / "cvat-overlay" / "docker-compose.windows.yml",
        ]
        self.assertEqual([], [str(path.relative_to(ROOT)) for path in required if not path.is_file()])

    def test_no_private_payload_is_committed(self) -> None:
        forbidden_suffixes = {".sqlite3", ".pt", ".pth", ".onnx", ".mp4", ".tar"}
        found = [path for path in ROOT.rglob("*") if path.is_file() and path.suffix.lower() in forbidden_suffixes]
        self.assertEqual([], found)


if __name__ == "__main__":
    unittest.main()
