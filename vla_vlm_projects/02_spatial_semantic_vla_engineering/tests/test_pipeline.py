import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pipeline import backproject, transform_point, robust_depth

class TestGeometry(unittest.TestCase):
    def test_center_backprojects_on_z_axis(self):
        p=backproject(320,240,1.0,{'fx':600,'fy':600,'cx':320,'cy':240})
        self.assertEqual(p,[0.0,0.0,1.0])
    def test_transform_translation(self):
        p=transform_point([1,2,3],[[1,0,0],[0,1,0],[0,0,1]],[0.5,-0.5,1])
        self.assertEqual(p,[1.5,1.5,4])
    def test_robust_depth_filters_outliers(self):
        self.assertAlmostEqual(robust_depth([0,0.6,0.61,8,0.62],0.1,2.0),0.61)

if __name__=='__main__': unittest.main()
