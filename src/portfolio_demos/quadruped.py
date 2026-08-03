"""Small deterministic SLAM/control building blocks for the quadruped case study."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

from .common import clamp, distance2


Point2 = tuple[float, float]
Point3 = tuple[float, float, float]


def voxel_downsample(points: Iterable[Point3], leaf_size: float) -> list[Point3]:
    """Average points per voxel using bounded, deterministic dictionary storage."""
    if leaf_size <= 0:
        raise ValueError("leaf_size must be positive")
    buckets: dict[tuple[int, int, int], list[float]] = {}
    for x, y, z in points:
        key = (math.floor(x / leaf_size), math.floor(y / leaf_size), math.floor(z / leaf_size))
        acc = buckets.setdefault(key, [0.0, 0.0, 0.0, 0.0])
        acc[0] += x
        acc[1] += y
        acc[2] += z
        acc[3] += 1.0
    return [
        (sx / count, sy / count, sz / count)
        for sx, sy, sz, count in (buckets[key] for key in sorted(buckets))
    ]


def apply_pose(points: Sequence[Point2], pose: tuple[float, float, float]) -> list[Point2]:
    tx, ty, yaw = pose
    c, s = math.cos(yaw), math.sin(yaw)
    return [(c * x - s * y + tx, s * x + c * y + ty) for x, y in points]


def _nearest_pairs(source: Sequence[Point2], target: Sequence[Point2], max_distance: float) -> list[tuple[Point2, Point2]]:
    pairs: list[tuple[Point2, Point2]] = []
    for point in source:
        match = min(target, key=lambda candidate: distance2(point, candidate))
        if distance2(point, match) <= max_distance:
            pairs.append((point, match))
    return pairs


def _rigid_fit(pairs: Sequence[tuple[Point2, Point2]]) -> tuple[float, float, float]:
    if len(pairs) < 2:
        raise ValueError("at least two correspondences are required")
    sx = sum(a[0] for a, _ in pairs) / len(pairs)
    sy = sum(a[1] for a, _ in pairs) / len(pairs)
    tx = sum(b[0] for _, b in pairs) / len(pairs)
    ty = sum(b[1] for _, b in pairs) / len(pairs)
    cross = 0.0
    dot = 0.0
    for (ax, ay), (bx, by) in pairs:
        ax, ay, bx, by = ax - sx, ay - sy, bx - tx, by - ty
        cross += ax * by - ay * bx
        dot += ax * bx + ay * by
    yaw = math.atan2(cross, dot)
    c, s = math.cos(yaw), math.sin(yaw)
    return tx - (c * sx - s * sy), ty - (s * sx + c * sy), yaw


def icp_2d(
    source: Sequence[Point2],
    target: Sequence[Point2],
    *,
    iterations: int = 12,
    max_correspondence: float = 2.0,
) -> tuple[tuple[float, float, float], float]:
    """Teaching ICP. Returns source-to-target pose and final mean residual."""
    if len(source) < 2 or len(target) < 2:
        raise ValueError("source and target need at least two points")
    pose = (0.0, 0.0, 0.0)
    transformed = list(source)
    residual = math.inf
    for _ in range(iterations):
        pairs = _nearest_pairs(transformed, target, max_correspondence)
        delta = _rigid_fit(pairs)
        transformed = apply_pose(transformed, delta)
        dx, dy, dyaw = delta
        px, py, pyaw = pose
        c, s = math.cos(dyaw), math.sin(dyaw)
        pose = (c * px - s * py + dx, s * px + c * py + dy, pyaw + dyaw)
        residual = sum(distance2(a, b) for a, b in _nearest_pairs(transformed, target, max_correspondence)) / len(pairs)
        if abs(dx) + abs(dy) + abs(dyaw) < 1e-8:
            break
    return pose, residual


@dataclass
class ImuPreintegrator2D:
    yaw: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    px: float = 0.0
    py: float = 0.0
    gyro_bias: float = 0.0

    def integrate(self, ax_body: float, ay_body: float, gyro_z: float, dt: float) -> None:
        if not 0.0 < dt <= 0.1:
            raise ValueError("IMU dt must be in (0, 0.1]")
        self.yaw += (gyro_z - self.gyro_bias) * dt
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        ax_world, ay_world = c * ax_body - s * ay_body, s * ax_body + c * ay_body
        self.px += self.vx * dt + 0.5 * ax_world * dt * dt
        self.py += self.vy * dt + 0.5 * ay_world * dt * dt
        self.vx += ax_world * dt
        self.vy += ay_world * dt


@dataclass(frozen=True)
class LoopClosureGate:
    descriptor_threshold: float = 0.15
    minimum_index_gap: int = 30

    def accept(self, current_index: int, candidate_index: int, descriptor_distance: float) -> bool:
        return (
            current_index - candidate_index >= self.minimum_index_gap
            and descriptor_distance <= self.descriptor_threshold
        )


def attention_decision(obstacles: Sequence[tuple[float, float]], goal_bearing: float) -> dict[str, float | str]:
    """Tiny deterministic stand-in for a task-aware attention decision layer."""
    if not obstacles:
        return {"action": "advance", "speed": 0.6, "yaw_rate": clamp(goal_bearing, -0.5, 0.5)}
    risks = [(math.exp(-distance) * (1.0 + max(0.0, math.cos(bearing))), bearing) for distance, bearing in obstacles]
    total = sum(score for score, _ in risks)
    weighted_bearing = sum(score * bearing for score, bearing in risks) / total
    if total > 1.2:
        return {"action": "stop", "speed": 0.0, "yaw_rate": 0.0}
    turn = -0.7 if weighted_bearing >= 0 else 0.7
    return {"action": "avoid", "speed": 0.25, "yaw_rate": turn}


def demo() -> dict[str, object]:
    raw = [(0.01, 0.02, 0.0), (0.03, 0.01, 0.01), (1.0, 0.0, 0.0), (1.02, 0.02, 0.0)]
    filtered = voxel_downsample(raw, 0.1)
    source = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    target = apply_pose(source, (0.4, -0.2, 0.08))
    pose, residual = icp_2d(source, target)
    imu = ImuPreintegrator2D()
    for _ in range(10):
        imu.integrate(0.1, 0.0, 0.02, 0.01)
    return {
        "voxel_points": len(filtered),
        "icp_pose": [round(value, 6) for value in pose],
        "icp_residual": round(residual, 9),
        "imu_delta": [round(imu.px, 6), round(imu.py, 6), round(imu.yaw, 6)],
        "loop_accepted": LoopClosureGate().accept(100, 50, 0.08),
        "decision": attention_decision([(0.8, 0.2), (1.8, -0.4)], 0.1),
    }
