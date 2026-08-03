"""Shared domain models with explicit SI units."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any


@dataclass(frozen=True)
class Pose2D:
    x_m: float
    y_m: float
    yaw_rad: float = 0.0

    def distance(self, other: "Pose2D") -> float:
        return math.hypot(self.x_m - other.x_m, self.y_m - other.y_m)


@dataclass(frozen=True)
class Rect:
    x_min_m: float
    y_min_m: float
    x_max_m: float
    y_max_m: float

    def contains(self, x_m: float, y_m: float, margin_m: float = 0.0) -> bool:
        return (
            self.x_min_m - margin_m <= x_m <= self.x_max_m + margin_m
            and self.y_min_m - margin_m <= y_m <= self.y_max_m + margin_m
        )


@dataclass(frozen=True)
class TerrainPatch:
    name: str
    bounds: Rect
    speed_scale: float
    gait_mode: str


@dataclass(frozen=True)
class Equipment:
    equipment_id: str
    x_m: float
    y_m: float
    defect_class: str | None


@dataclass(frozen=True)
class Detection:
    equipment_id: str
    class_name: str
    confidence: float
    iou_with_truth: float
    is_true_positive: bool


@dataclass(frozen=True)
class DynamicObstacle:
    obstacle_id: str
    path: tuple[tuple[float, float], ...]
    radius_m: float
    period_steps: int

    def position(self, step: int) -> tuple[float, float]:
        if not self.path:
            raise ValueError("dynamic obstacle path must not be empty")
        if len(self.path) == 1:
            return self.path[0]
        phase = (step % self.period_steps) / self.period_steps * len(self.path)
        index = int(phase) % len(self.path)
        next_index = (index + 1) % len(self.path)
        fraction = phase - int(phase)
        x0, y0 = self.path[index]
        x1, y1 = self.path[next_index]
        return x0 + (x1 - x0) * fraction, y0 + (y1 - y0) * fraction


@dataclass(frozen=True)
class ScenarioConfig:
    name: str
    width_m: float
    height_m: float
    resolution_m: float
    robot_radius_m: float
    max_lidar_range_m: float
    checkpoints: tuple[Pose2D, ...]
    static_obstacles: tuple[Rect, ...]
    terrain: tuple[TerrainPatch, ...]
    equipment: tuple[Equipment, ...]
    dynamic_obstacles: tuple[DynamicObstacle, ...]
    odometry_noise_std_m: float
    odometry_bias_per_m: float
    landmark_correction_gain: float
    detection_probability: float
    false_positive_probability: float
    nominal_speed_mps: float
    random_seed: int


@dataclass(frozen=True)
class Event:
    step: int
    kind: str
    message: str
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def pose_from_dict(data: dict[str, Any]) -> Pose2D:
    return Pose2D(float(data["x_m"]), float(data["y_m"]), float(data.get("yaw_rad", 0.0)))


def rect_from_dict(data: dict[str, Any]) -> Rect:
    return Rect(float(data["x_min_m"]), float(data["y_min_m"]), float(data["x_max_m"]), float(data["y_max_m"]))
