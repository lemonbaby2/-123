from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import quadruped_slam as slam  # noqa: E402


class QuadrupedSlamTests(unittest.TestCase):
    def test_voxel_filter(self):
        points = [(0.01, 0.01, 0.0), (0.02, 0.02, 0.0), (1.0, 1.0, 1.0)]
        self.assertEqual(len(slam.voxel_downsample(points, 0.1)), 2)

    def test_icp_recovers_pose(self):
        source = [(0.0, 0.0), (1.0, 0.0), (1.2, 1.0), (-0.1, 0.8)]
        expected = (0.3, -0.2, 0.05)
        pose, residual = slam.icp_2d(source, slam.apply_pose(source, expected))
        for actual, target in zip(pose, expected):
            self.assertAlmostEqual(actual, target, places=5)
        self.assertLess(residual, 1e-7)

    def test_bad_imu_dt_is_rejected(self):
        with self.assertRaises(ValueError):
            slam.ImuPreintegrator2D().integrate(0, 0, 0, 0.2)


if __name__ == "__main__":
    unittest.main()
