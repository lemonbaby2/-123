from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import bms  # noqa: E402


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
