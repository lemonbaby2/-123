import math
import unittest

from portfolio_demos import bms, gaussian_viz, geoscan, ginger, quadruped, vision


class QuadrupedTests(unittest.TestCase):
    def test_voxel_filter(self):
        points = [(0.01, 0.01, 0.0), (0.02, 0.02, 0.0), (1.0, 1.0, 1.0)]
        self.assertEqual(len(quadruped.voxel_downsample(points, 0.1)), 2)

    def test_icp_recovers_pose(self):
        source = [(0.0, 0.0), (1.0, 0.0), (1.2, 1.0), (-0.1, 0.8)]
        expected = (0.3, -0.2, 0.05)
        pose, residual = quadruped.icp_2d(source, quadruped.apply_pose(source, expected))
        for actual, target in zip(pose, expected):
            self.assertAlmostEqual(actual, target, places=5)
        self.assertLess(residual, 1e-7)

    def test_bad_imu_dt_is_rejected(self):
        with self.assertRaises(ValueError):
            quadruped.ImuPreintegrator2D().integrate(0, 0, 0, 0.2)


class GingerTests(unittest.TestCase):
    def test_recovery_order(self):
        health = ginger.RobotHealth(False, False, False, False, False, 0.0)
        self.assertEqual(ginger.first_failed_stage(health), ginger.RecoveryStage.NIC)

    def test_navigation_gate(self):
        health = ginger.RobotHealth(True, True, True, True, True, 0.2)
        with self.assertRaises(RuntimeError):
            ginger.build_navigation_command(health, 1.0, 2.0, 0.0)

    def test_map_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            ginger.validated_map_uri("/maps/../secret.yaml")


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


class VisionTests(unittest.TestCase):
    def test_metrics(self):
        truth = [vision.Box(0, 0, 2, 2)]
        metrics = vision.detection_metrics([vision.Box(0, 0, 2, 2)], truth)
        self.assertEqual(metrics["recall"], 1.0)
        self.assertEqual(metrics["precision"], 1.0)

    def test_quantization_error_is_bounded(self):
        values = [-2.0, -0.2, 0.3, 1.7]
        _, restored, scale = vision.symmetric_int8(values)
        self.assertLessEqual(max(abs(a - b) for a, b in zip(values, restored)), scale / 2 + 1e-12)

    def test_p2_sampling(self):
        result = vision.validate_p2_pyramid([4, 8, 16, 32], 10)
        self.assertTrue(result["has_p2"])
        self.assertTrue(result["adequate_sampling"])


class GaussianTests(unittest.TestCase):
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
        points = gaussian_viz.parse_ascii_ply(self.PLY)
        message = gaussian_viz.marker_array(points, "map", 3)
        self.assertEqual(len(message["markers"]), 1)
        self.assertEqual(message["markers"][0]["header"]["frame_id"], "map")

    def test_time_reversal(self):
        point = gaussian_viz.parse_ascii_ply(self.PLY)
        valid, reason = gaussian_viz.validate_stream([
            gaussian_viz.marker_array(point, stamp_ns=2),
            gaussian_viz.marker_array(point, stamp_ns=1),
        ])
        self.assertFalse(valid)
        self.assertEqual(reason, "time_reversed")


class BmsTests(unittest.TestCase):
    def test_ekf_converges(self):
        plant = bms.TheveninCell(soc=0.8)
        estimator = bms.AdaptiveEkf(soc=0.65)
        initial_error = abs(plant.soc - estimator.soc)
        for _ in range(200):
            voltage = plant.step(1.0, 1.0)
            estimator.update(1.0, voltage, 1.0)
        self.assertLess(abs(plant.soc - estimator.soc), initial_error)

    def test_balancing_respects_temperature(self):
        mask = bms.balancing_mask([0.7, 0.8, 0.9], [25, 25, 60])
        self.assertEqual(mask, [False, False, False])

    def test_scheduler_budget(self):
        self.assertTrue(bms.schedulability([("a", 1.0, 10.0)])["within_budget"])


if __name__ == "__main__":
    unittest.main()
