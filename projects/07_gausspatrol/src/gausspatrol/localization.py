"""Synthetic odometry/landmark fusion and trajectory metrics."""

from __future__ import annotations

import math
import random
from typing import Sequence

from .models import Pose2D, ScenarioConfig


class LocalizationEstimator:
    def __init__(self, initial: Pose2D, config: ScenarioConfig):
        self.pose = initial
        self.config = config
        self.random = random.Random(config.random_seed + 101)
        self.travel_m = 0.0

    def predict(self, previous_true: Pose2D, current_true: Pose2D) -> Pose2D:
        dx = current_true.x_m - previous_true.x_m
        dy = current_true.y_m - previous_true.y_m
        distance = math.hypot(dx, dy)
        self.travel_m += distance
        noise_x = self.random.gauss(0.0, self.config.odometry_noise_std_m)
        noise_y = self.random.gauss(0.0, self.config.odometry_noise_std_m)
        bias = self.config.odometry_bias_per_m * distance
        yaw = math.atan2(dy, dx) if distance else self.pose.yaw_rad
        self.pose = Pose2D(self.pose.x_m + dx + noise_x + bias, self.pose.y_m + dy + noise_y - 0.5 * bias, yaw)
        return self.pose

    def correct_with_landmark(self, truth: Pose2D) -> Pose2D:
        gain = min(1.0, max(0.0, self.config.landmark_correction_gain))
        self.pose = Pose2D(
            self.pose.x_m + gain * (truth.x_m - self.pose.x_m),
            self.pose.y_m + gain * (truth.y_m - self.pose.y_m),
            truth.yaw_rad,
        )
        return self.pose


def trajectory_metrics(truth: Sequence[Pose2D], estimate: Sequence[Pose2D]) -> dict[str, float]:
    if len(truth) != len(estimate) or len(truth) < 2:
        raise ValueError("truth and estimate trajectories need equal length >= 2")
    squared = [(a.x_m - b.x_m) ** 2 + (a.y_m - b.y_m) ** 2 for a, b in zip(truth, estimate)]
    relative_squared = []
    for index in range(1, len(truth)):
        true_dx = truth[index].x_m - truth[index - 1].x_m
        true_dy = truth[index].y_m - truth[index - 1].y_m
        est_dx = estimate[index].x_m - estimate[index - 1].x_m
        est_dy = estimate[index].y_m - estimate[index - 1].y_m
        relative_squared.append((true_dx - est_dx) ** 2 + (true_dy - est_dy) ** 2)
    return {
        "ate_rmse_m": math.sqrt(sum(squared) / len(squared)),
        "rpe_rmse_m": math.sqrt(sum(relative_squared) / len(relative_squared)),
        "max_position_error_m": math.sqrt(max(squared)),
    }
