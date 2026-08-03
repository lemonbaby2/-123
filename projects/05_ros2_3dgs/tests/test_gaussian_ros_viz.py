from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import gaussian_ros_viz as viz  # noqa: E402


class GaussianRosVizTests(unittest.TestCase):
    PLY = """ply
format ascii 1.0
element vertex 1
property float x
property float y
property float z
property float scale
property float opacity
property uchar red
property uchar green
property uchar blue
end_header
0 1 2 0.1 0.8 255 0 10
"""

    def test_parse_and_marker(self):
        points = viz.parse_ascii_ply(self.PLY)
        message = viz.marker_array(points, "map", 3)
        self.assertEqual(len(message["markers"]), 1)
        self.assertEqual(message["markers"][0]["header"]["frame_id"], "map")

    def test_time_reversal(self):
        point = viz.parse_ascii_ply(self.PLY)
        valid, reason = viz.validate_stream([
            viz.marker_array(point, stamp_ns=2),
            viz.marker_array(point, stamp_ns=1),
        ])
        self.assertFalse(valid)
        self.assertEqual(reason, "time_reversed")


if __name__ == "__main__":
    unittest.main()
