"""Terrain-aware command policy and safety envelope.

This module produces abstract commands only. A hardware adapter must map them to
the S10 SDK/ros2_control after vendor documentation and real-robot validation.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import TerrainPatch


@dataclass(frozen=True)
class MotionCommand:
    linear_speed_mps: float
    yaw_rate_radps: float
    gait_mode: str
    enabled: bool
    reason: str


class TerrainController:
    def __init__(self, nominal_speed_mps: float, max_yaw_rate_radps: float = 0.8):
        if nominal_speed_mps <= 0 or max_yaw_rate_radps <= 0:
            raise ValueError("controller limits must be positive")
        self.nominal_speed_mps = nominal_speed_mps
        self.max_yaw_rate_radps = max_yaw_rate_radps

    def command(self, terrain: TerrainPatch, *, localization_healthy: bool, obstacle_clear: bool) -> MotionCommand:
        if not localization_healthy:
            return MotionCommand(0.0, 0.0, terrain.gait_mode, False, "localization_unhealthy")
        if not obstacle_clear:
            return MotionCommand(0.0, 0.0, terrain.gait_mode, False, "obstacle_stop")
        speed = self.nominal_speed_mps * min(1.0, max(0.1, terrain.speed_scale))
        return MotionCommand(speed, 0.0, terrain.gait_mode, True, "ready")
