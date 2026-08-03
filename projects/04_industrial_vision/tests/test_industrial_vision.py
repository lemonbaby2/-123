from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import industrial_vision as vision  # noqa: E402


class IndustrialVisionTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
