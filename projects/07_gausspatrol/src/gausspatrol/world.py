"""Grid world, terrain and deterministic 2D range sensing."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable

from .models import DynamicObstacle, Equipment, Pose2D, Rect, ScenarioConfig, TerrainPatch, pose_from_dict, rect_from_dict


GridCell = tuple[int, int]


def load_scenario(path: str | Path, *, variant: str = "nominal") -> ScenarioConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if variant not in data["variants"]:
        raise ValueError(f"unknown scenario variant: {variant}")
    settings = {**data["base"], **data["variants"][variant]}
    return ScenarioConfig(
        name=variant,
        width_m=float(settings["width_m"]),
        height_m=float(settings["height_m"]),
        resolution_m=float(settings["resolution_m"]),
        robot_radius_m=float(settings["robot_radius_m"]),
        max_lidar_range_m=float(settings["max_lidar_range_m"]),
        checkpoints=tuple(pose_from_dict(item) for item in settings["checkpoints"]),
        static_obstacles=tuple(rect_from_dict(item) for item in settings["static_obstacles"]),
        terrain=tuple(
            TerrainPatch(item["name"], rect_from_dict(item["bounds"]), float(item["speed_scale"]), item["gait_mode"])
            for item in settings["terrain"]
        ),
        equipment=tuple(
            Equipment(item["equipment_id"], float(item["x_m"]), float(item["y_m"]), item.get("defect_class"))
            for item in settings["equipment"]
        ),
        dynamic_obstacles=tuple(
            DynamicObstacle(
                item["obstacle_id"],
                tuple((float(point[0]), float(point[1])) for point in item["path"]),
                float(item["radius_m"]),
                int(item["period_steps"]),
            )
            for item in settings["dynamic_obstacles"]
        ),
        odometry_noise_std_m=float(settings["odometry_noise_std_m"]),
        odometry_bias_per_m=float(settings["odometry_bias_per_m"]),
        landmark_correction_gain=float(settings["landmark_correction_gain"]),
        detection_probability=float(settings["detection_probability"]),
        false_positive_probability=float(settings["false_positive_probability"]),
        nominal_speed_mps=float(settings["nominal_speed_mps"]),
        random_seed=int(settings["random_seed"]),
    )


class PatrolWorld:
    def __init__(self, config: ScenarioConfig):
        self.config = config
        self.cols = int(round(config.width_m / config.resolution_m))
        self.rows = int(round(config.height_m / config.resolution_m))
        if self.cols <= 0 or self.rows <= 0:
            raise ValueError("world dimensions must be positive")

    def to_cell(self, x_m: float, y_m: float) -> GridCell:
        col = min(self.cols - 1, max(0, int(x_m / self.config.resolution_m)))
        row = min(self.rows - 1, max(0, int(y_m / self.config.resolution_m)))
        return col, row

    def to_pose(self, cell: GridCell) -> Pose2D:
        col, row = cell
        resolution = self.config.resolution_m
        return Pose2D((col + 0.5) * resolution, (row + 0.5) * resolution)

    def inside(self, cell: GridCell) -> bool:
        col, row = cell
        return 0 <= col < self.cols and 0 <= row < self.rows

    def is_static_occupied(self, cell: GridCell, margin_m: float | None = None) -> bool:
        if not self.inside(cell):
            return True
        pose = self.to_pose(cell)
        margin = self.config.robot_radius_m if margin_m is None else margin_m
        return any(rect.contains(pose.x_m, pose.y_m, margin) for rect in self.config.static_obstacles)

    def dynamic_positions(self, step: int) -> list[tuple[DynamicObstacle, float, float]]:
        return [(obstacle, *obstacle.position(step)) for obstacle in self.config.dynamic_obstacles]

    def dynamic_blocked_cells(self, step: int, extra_margin_m: float = 0.15) -> set[GridCell]:
        blocked: set[GridCell] = set()
        margin = self.config.robot_radius_m + extra_margin_m
        for obstacle, x_m, y_m in self.dynamic_positions(step):
            radius = obstacle.radius_m + margin
            cells = int(math.ceil(radius / self.config.resolution_m))
            center = self.to_cell(x_m, y_m)
            for dx in range(-cells, cells + 1):
                for dy in range(-cells, cells + 1):
                    cell = center[0] + dx, center[1] + dy
                    if self.inside(cell) and self.to_pose(cell).distance(Pose2D(x_m, y_m)) <= radius:
                        blocked.add(cell)
        return blocked

    def collision(self, pose: Pose2D, step: int) -> bool:
        if not 0 <= pose.x_m <= self.config.width_m or not 0 <= pose.y_m <= self.config.height_m:
            return True
        if any(rect.contains(pose.x_m, pose.y_m, self.config.robot_radius_m) for rect in self.config.static_obstacles):
            return True
        for obstacle, x_m, y_m in self.dynamic_positions(step):
            if math.hypot(pose.x_m - x_m, pose.y_m - y_m) <= self.config.robot_radius_m + obstacle.radius_m:
                return True
        return False

    def terrain_at(self, pose: Pose2D) -> TerrainPatch:
        for patch in self.config.terrain:
            if patch.bounds.contains(pose.x_m, pose.y_m):
                return patch
        return TerrainPatch("paved", Rect(0, 0, self.config.width_m, self.config.height_m), 1.0, "trot")

    def neighbors(self, cell: GridCell, dynamic_blocked: set[GridCell]) -> Iterable[tuple[GridCell, float]]:
        for dx, dy, cost in ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)):
            nxt = cell[0] + dx, cell[1] + dy
            if not self.inside(nxt) or self.is_static_occupied(nxt) or nxt in dynamic_blocked:
                continue
            if dx and dy:
                if self.is_static_occupied((cell[0] + dx, cell[1])) or self.is_static_occupied((cell[0], cell[1] + dy)):
                    continue
            yield nxt, cost

    def raycast(self, pose: Pose2D, beams: int = 48) -> list[tuple[float, float, float]]:
        if beams < 4:
            raise ValueError("at least four beams are required")
        hits: list[tuple[float, float, float]] = []
        step_m = self.config.resolution_m / 3.0
        for index in range(beams):
            angle = pose.yaw_rad + 2.0 * math.pi * index / beams
            distance = step_m
            while distance <= self.config.max_lidar_range_m:
                x_m = pose.x_m + math.cos(angle) * distance
                y_m = pose.y_m + math.sin(angle) * distance
                if not 0 <= x_m <= self.config.width_m or not 0 <= y_m <= self.config.height_m:
                    break
                if any(rect.contains(x_m, y_m) for rect in self.config.static_obstacles):
                    hits.append((x_m, y_m, 0.4))
                    break
                distance += step_m
        return hits

    def reference_surface_cells(self) -> set[GridCell]:
        cells: set[GridCell] = set()
        for col in range(self.cols):
            for row in range(self.rows):
                cell = col, row
                if not self.is_static_occupied(cell, margin_m=0.0):
                    continue
                if any(self.inside(nxt) and not self.is_static_occupied(nxt, margin_m=0.0) for nxt in ((col + 1, row), (col - 1, row), (col, row + 1), (col, row - 1))):
                    cells.add(cell)
        return cells
