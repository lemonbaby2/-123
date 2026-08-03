"""End-to-end patrol mission orchestration and benchmark comparison."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path
import statistics
import time
from typing import Any

from .control import TerrainController
from .localization import LocalizationEstimator, trajectory_metrics
from .mapping import GaussianMap
from .models import Detection, Event, Pose2D, ScenarioConfig
from .perception import SyntheticDefectDetector, detection_metrics
from .planning import AStarPlanner, PlanningError
from .world import PatrolWorld, load_scenario


@dataclass
class MissionResult:
    scenario: str
    completed: bool
    checkpoints_total: int
    checkpoints_reached: int
    route_completion_rate: float
    route_distance_m: float
    modelled_mission_time_s: float
    wall_runtime_s: float
    trajectory: dict[str, float]
    perception: dict[str, float | int]
    map_completeness: float
    gaussian_count: int
    avoidance_attempts: int
    avoidance_successes: int
    avoidance_success_rate: float
    collisions: int
    replans: int
    planning_latency_ms: dict[str, float]
    perception_latency_ms: dict[str, float]
    terrain_distance_m: dict[str, float]
    gait_switches: int
    steps: int
    truth_path: list[Pose2D]
    estimated_path: list[Pose2D]
    dynamic_history: list[list[tuple[str, float, float]]]
    detections: list[Detection]
    events: list[Event]
    gaussian_map: GaussianMap

    def summary(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("truth_path", "estimated_path", "dynamic_history", "detections", "events", "gaussian_map"):
            data.pop(key, None)
        return data


@dataclass
class BenchmarkResult:
    nominal: MissionResult
    shifted: MissionResult
    sim_to_real_proxy: dict[str, float]

    def summary(self) -> dict[str, Any]:
        return {
            "nominal": self.nominal.summary(),
            "shifted": self.shifted.summary(),
            "sim_to_real_proxy": self.sim_to_real_proxy,
            "disclaimer": "shifted is a deterministic stress simulation, not measured real-robot performance",
        }


def _latency(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "p95": 0.0, "max": 0.0, "samples": 0}
    ordered = sorted(values)
    p95_index = min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)
    return {"mean": statistics.fmean(values), "p95": ordered[p95_index], "max": max(values), "samples": len(values)}


def run_mission(config: ScenarioConfig, *, step_limit: int = 3000) -> MissionResult:
    if len(config.checkpoints) < 2:
        raise ValueError("mission needs a start and at least one checkpoint")
    started = time.perf_counter()
    world = PatrolWorld(config)
    planner = AStarPlanner(world)
    estimator = LocalizationEstimator(config.checkpoints[0], config)
    detector = SyntheticDefectDetector(config)
    controller = TerrainController(config.nominal_speed_mps)
    gaussian_map = GaussianMap(world)
    truth_path = [config.checkpoints[0]]
    estimated_path = [config.checkpoints[0]]
    dynamic_history: list[list[tuple[str, float, float]]] = []
    events: list[Event] = [Event(0, "mission_started", f"scenario={config.name}", {})]
    detections: list[Detection] = []
    planning_latencies: list[float] = []
    perception_latencies: list[float] = []
    terrain_distance: dict[str, float] = {}
    current = config.checkpoints[0]
    step = 0
    route_distance = 0.0
    modelled_time = 0.0
    reached = 0
    replans = 0
    avoidance_attempts = 0
    avoidance_successes = 0
    collisions = 0
    gait_switches = 0
    last_gait = world.terrain_at(current).gait_mode

    targets = list(config.checkpoints[1:])
    for target_index, target in enumerate(targets, 1):
        segment_complete = False
        segment_replans = 0
        while not segment_complete and step < step_limit and segment_replans <= 40:
            plan_started = time.perf_counter_ns()
            try:
                path = planner.plan(current, target, step=step, include_dynamic=True)
            except PlanningError as error:
                planning_latencies.append((time.perf_counter_ns() - plan_started) / 1e6)
                events.append(Event(step, "planning_failed", str(error), {"target": target_index}))
                break
            planning_latencies.append((time.perf_counter_ns() - plan_started) / 1e6)
            if segment_replans:
                replans += 1
            needs_replan = False
            for next_pose in path[1:]:
                next_step = step + 1
                dynamic = [(item.obstacle_id, x_m, y_m) for item, x_m, y_m in world.dynamic_positions(next_step)]
                dynamic_history.append(dynamic)
                unsafe = any(
                    math.hypot(next_pose.x_m - x_m, next_pose.y_m - y_m)
                    <= config.robot_radius_m + obstacle.radius_m + 0.20
                    for obstacle, x_m, y_m in world.dynamic_positions(next_step)
                )
                if unsafe:
                    avoidance_attempts += 1
                    step += 1
                    modelled_time += 0.25
                    events.append(Event(step, "dynamic_avoidance", "dynamic obstacle caused replan", {"target": target_index}))
                    segment_replans += 1
                    try:
                        planner.plan(current, target, step=step, include_dynamic=True)
                        avoidance_successes += 1
                    except PlanningError:
                        pass
                    needs_replan = True
                    break

                previous = current
                current = next_pose
                step = next_step
                move_distance = previous.distance(current)
                route_distance += move_distance
                terrain = world.terrain_at(current)
                command = controller.command(terrain, localization_healthy=True, obstacle_clear=True)
                if not command.enabled:
                    events.append(Event(step, "control_blocked", command.reason, {}))
                    needs_replan = False
                    break
                terrain_distance[terrain.name] = terrain_distance.get(terrain.name, 0.0) + move_distance
                if terrain.gait_mode != last_gait:
                    gait_switches += 1
                    events.append(Event(step, "gait_switch", f"{last_gait}->{terrain.gait_mode}", {"terrain": terrain.name}))
                    last_gait = terrain.gait_mode
                modelled_time += move_distance / max(0.05, command.linear_speed_mps)
                yaw = math.atan2(current.y_m - previous.y_m, current.x_m - previous.x_m) if move_distance else previous.yaw_rad
                current = Pose2D(current.x_m, current.y_m, yaw)
                estimate = estimator.predict(previous, current)
                truth_path.append(current)
                estimated_path.append(estimate)
                if step % 2 == 0:
                    gaussian_map.integrate(world.raycast(current))
                if world.collision(current, step):
                    collisions += 1
                    events.append(Event(step, "collision", "collision invariant violated", {}))
                    needs_replan = False
                    break
            if collisions:
                break
            if not needs_replan and current.distance(target) <= config.resolution_m * 0.75:
                segment_complete = True
                reached += 1
                corrected = estimator.correct_with_landmark(target)
                estimated_path[-1] = corrected
                events.append(Event(step, "checkpoint_reached", f"checkpoint={target_index}", {"x_m": target.x_m, "y_m": target.y_m}))
                nearby = sorted(config.equipment, key=lambda item: math.hypot(item.x_m - target.x_m, item.y_m - target.y_m))
                if nearby and math.hypot(nearby[0].x_m - target.x_m, nearby[0].y_m - target.y_m) <= 1.5:
                    found, latency_ms = detector.inspect(nearby[0])
                    perception_latencies.append(latency_ms)
                    detections.extend(found)
                    events.append(Event(step, "equipment_inspected", nearby[0].equipment_id, {"detections": len(found)}))
            elif not needs_replan:
                break
        if not segment_complete or collisions:
            break

    completed = reached == len(targets) and collisions == 0
    trajectory = trajectory_metrics(truth_path, estimated_path)
    ground_truth = sum(1 for item in config.equipment if item.defect_class)
    perception = detection_metrics(detections, ground_truth)
    events.append(Event(step, "mission_finished", f"completed={completed}", {"checkpoints_reached": reached}))
    return MissionResult(
        scenario=config.name,
        completed=completed,
        checkpoints_total=len(targets),
        checkpoints_reached=reached,
        route_completion_rate=reached / len(targets),
        route_distance_m=route_distance,
        modelled_mission_time_s=modelled_time,
        wall_runtime_s=time.perf_counter() - started,
        trajectory=trajectory,
        perception=perception,
        map_completeness=gaussian_map.completeness(),
        gaussian_count=len(gaussian_map.points()),
        avoidance_attempts=avoidance_attempts,
        avoidance_successes=avoidance_successes,
        avoidance_success_rate=avoidance_successes / avoidance_attempts if avoidance_attempts else 1.0,
        collisions=collisions,
        replans=replans,
        planning_latency_ms=_latency(planning_latencies),
        perception_latency_ms=_latency(perception_latencies),
        terrain_distance_m=terrain_distance,
        gait_switches=gait_switches,
        steps=step,
        truth_path=truth_path,
        estimated_path=estimated_path,
        dynamic_history=dynamic_history,
        detections=detections,
        events=events,
        gaussian_map=gaussian_map,
    )


def run_benchmark(scenario_path: str | Path) -> BenchmarkResult:
    nominal = run_mission(load_scenario(scenario_path, variant="nominal"))
    shifted = run_mission(load_scenario(scenario_path, variant="shifted"))
    nominal_ate = nominal.trajectory["ate_rmse_m"]
    shifted_ate = shifted.trajectory["ate_rmse_m"]
    gap = {
        "route_completion_change_pp": 100.0 * (shifted.route_completion_rate - nominal.route_completion_rate),
        "ate_rmse_change_m": shifted_ate - nominal_ate,
        "ate_relative_change_percent": 100.0 * (shifted_ate - nominal_ate) / max(1e-12, nominal_ate),
        "ap50_change": float(shifted.perception["ap50_11point"]) - float(nominal.perception["ap50_11point"]),
        "modelled_time_change_s": shifted.modelled_mission_time_s - nominal.modelled_mission_time_s,
        "map_completeness_change_pp": 100.0 * (shifted.map_completeness - nominal.map_completeness),
    }
    return BenchmarkResult(nominal, shifted, gap)
