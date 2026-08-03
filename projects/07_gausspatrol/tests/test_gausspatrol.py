from dataclasses import replace
from pathlib import Path
import json
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from gausspatrol.localization import LocalizationEstimator, trajectory_metrics  # noqa: E402
from gausspatrol.control import TerrainController  # noqa: E402
from gausspatrol.mapping import GaussianMap  # noqa: E402
from gausspatrol.mission import run_benchmark, run_mission  # noqa: E402
from gausspatrol.models import Detection, Pose2D, Rect  # noqa: E402
from gausspatrol.perception import detection_metrics  # noqa: E402
from gausspatrol.planning import AStarPlanner, PlanningError  # noqa: E402
from gausspatrol.reporting import write_artifacts  # noqa: E402
from gausspatrol.world import PatrolWorld, load_scenario  # noqa: E402


SCENARIO = PROJECT / "config/default_scenario.json"


class WorldAndPlanningTests(unittest.TestCase):
    def setUp(self):
        self.config = load_scenario(SCENARIO)
        self.world = PatrolWorld(self.config)

    def test_round_trip_cell_has_bounded_error(self):
        pose = Pose2D(2.2, 3.7)
        restored = self.world.to_pose(self.world.to_cell(pose.x_m, pose.y_m))
        self.assertLessEqual(pose.distance(restored), self.config.resolution_m / 1.4)

    def test_static_obstacle_is_occupied(self):
        self.assertTrue(self.world.is_static_occupied(self.world.to_cell(6.0, 3.0)))
        self.assertFalse(self.world.is_static_occupied(self.world.to_cell(1.0, 1.0)))

    def test_astar_path_is_collision_free(self):
        path = AStarPlanner(self.world).plan(self.config.checkpoints[0], self.config.checkpoints[1], step=0)
        self.assertGreater(len(path), 2)
        self.assertTrue(all(not self.world.is_static_occupied(self.world.to_cell(item.x_m, item.y_m)) for item in path))

    def test_occupied_goal_is_rejected(self):
        with self.assertRaises(PlanningError):
            AStarPlanner(self.world).plan(self.config.checkpoints[0], Pose2D(6.0, 3.0), step=0)

    def test_raycast_hits_static_geometry(self):
        hits = self.world.raycast(Pose2D(4.0, 3.0), beams=24)
        self.assertTrue(hits)


class EstimationAndPerceptionTests(unittest.TestCase):
    def test_safety_controller_blocks_unhealthy_localization(self):
        config = load_scenario(SCENARIO)
        terrain = PatrolWorld(config).terrain_at(Pose2D(2.0, 10.0))
        command = TerrainController(1.0).command(terrain, localization_healthy=False, obstacle_clear=True)
        self.assertFalse(command.enabled)
        self.assertEqual(command.linear_speed_mps, 0.0)

    def test_landmark_correction_reduces_error(self):
        config = load_scenario(SCENARIO, variant="shifted")
        estimator = LocalizationEstimator(Pose2D(0, 0), config)
        estimator.pose = Pose2D(1.0, -1.0)
        truth = Pose2D(0.2, 0.1)
        before = estimator.pose.distance(truth)
        after = estimator.correct_with_landmark(truth).distance(truth)
        self.assertLess(after, before)

    def test_trajectory_metrics_are_zero_for_identical_paths(self):
        path = [Pose2D(0, 0), Pose2D(1, 0), Pose2D(1, 1)]
        metrics = trajectory_metrics(path, path)
        self.assertEqual(metrics["ate_rmse_m"], 0.0)
        self.assertEqual(metrics["rpe_rmse_m"], 0.0)

    def test_detection_metrics_count_duplicate_as_false_positive(self):
        detections = [
            Detection("pump", "leak", 0.9, 0.8, True),
            Detection("pump", "leak", 0.8, 0.7, True),
        ]
        metrics = detection_metrics(detections, 1)
        self.assertEqual(metrics["true_positive"], 1)
        self.assertEqual(metrics["false_positive"], 1)
        self.assertLessEqual(metrics["ap50_11point"], 1.0)


class MappingMissionAndReportingTests(unittest.TestCase):
    def test_gaussian_ply_schema_and_count(self):
        world = PatrolWorld(load_scenario(SCENARIO))
        gaussian_map = GaussianMap(world)
        gaussian_map.integrate([(5.0, 2.0, 0.4), (5.1, 2.0, 0.4)])
        text = gaussian_map.to_ascii_ply()
        self.assertIn("format ascii 1.0", text)
        self.assertIn("element vertex 1", text)

    def test_nominal_mission_completes_without_collision(self):
        result = run_mission(load_scenario(SCENARIO))
        self.assertTrue(result.completed)
        self.assertEqual(result.route_completion_rate, 1.0)
        self.assertEqual(result.collisions, 0)
        self.assertGreater(result.avoidance_attempts, 0)
        self.assertGreater(result.map_completeness, 0.5)

    def test_shifted_scenario_degrades_localization_and_detection(self):
        benchmark = run_benchmark(SCENARIO)
        self.assertGreater(benchmark.shifted.trajectory["ate_rmse_m"], benchmark.nominal.trajectory["ate_rmse_m"])
        self.assertLess(float(benchmark.shifted.perception["ap50_11point"]), float(benchmark.nominal.perception["ap50_11point"]))

    def test_artifact_writer_produces_parseable_metrics_and_manifest(self):
        benchmark = run_benchmark(SCENARIO)
        with tempfile.TemporaryDirectory() as directory:
            files = write_artifacts(benchmark, SCENARIO, directory)
            names = {path.name for path in files}
            self.assertIn("dashboard.svg", names)
            self.assertIn("nominal_gaussians.ply", names)
            self.assertIn("SHA256SUMS.txt", names)
            metrics = json.loads((Path(directory) / "metrics.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["nominal"]["completed"])


if __name__ == "__main__":
    unittest.main()
