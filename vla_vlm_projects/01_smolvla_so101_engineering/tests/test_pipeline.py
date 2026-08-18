import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pipeline import safety_gate

class TestGate(unittest.TestCase):
    def test_clamps_and_smooths(self):
        g = safety_gate([[0,0],[2,0.9]], [[-1,1],[-1,1]], 0.25, 0.9, 0.5)
        self.assertTrue(g.accepted)
        self.assertEqual(g.actions[1], [0.25, 0.25])
    def test_low_confidence_rejected(self):
        g = safety_gate([[0,0]], [[-1,1],[-1,1]], 0.25, 0.2, 0.5)
        self.assertFalse(g.accepted)
    def test_dimension_mismatch(self):
        g = safety_gate([[0]], [[-1,1],[-1,1]], 0.25, 0.9, 0.5)
        self.assertFalse(g.accepted)

if __name__ == '__main__': unittest.main()
