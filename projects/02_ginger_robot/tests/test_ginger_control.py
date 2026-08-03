from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import ginger_control as ginger  # noqa: E402


class GingerControlTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
