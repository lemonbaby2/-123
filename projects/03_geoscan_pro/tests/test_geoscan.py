from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import geoscan  # noqa: E402


class GeoScanTests(unittest.TestCase):
    def test_frame_round_trip(self):
        frame = geoscan.encode_frame(7, 99, b"payload")
        self.assertEqual(geoscan.decode_frame(frame), (7, 99, b"payload"))

    def test_crc_failure(self):
        frame = bytearray(geoscan.encode_frame(7, 99, b"payload"))
        frame[-1] ^= 0xFF
        with self.assertRaises(ValueError):
            geoscan.decode_frame(bytes(frame))

    def test_pose_graph(self):
        poses = geoscan.optimize_pose_graph(
            3,
            [geoscan.RelativeFactor(0, 1, 1, 0, 10), geoscan.RelativeFactor(1, 2, 1, 0, 10)],
            [geoscan.AbsoluteFactor(2, 2, 0, 2)],
        )
        self.assertAlmostEqual(poses[2][0], 2.0, places=3)


if __name__ == "__main__":
    unittest.main()
