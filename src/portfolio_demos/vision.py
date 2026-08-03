"""Metrics and edge-deployment helpers for the industrial-vision case study."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from .common import clamp


@dataclass(frozen=True)
class Box:
    x1: float
    y1: float
    x2: float
    y2: float
    score: float = 1.0
    label: int = 0


def iou(a: Box, b: Box) -> float:
    width = max(0.0, min(a.x2, b.x2) - max(a.x1, b.x1))
    height = max(0.0, min(a.y2, b.y2) - max(a.y1, b.y1))
    intersection = width * height
    area_a = max(0.0, a.x2 - a.x1) * max(0.0, a.y2 - a.y1)
    area_b = max(0.0, b.x2 - b.x1) * max(0.0, b.y2 - b.y1)
    union = area_a + area_b - intersection
    return intersection / union if union else 0.0


def detection_metrics(predictions: Sequence[Box], truth: Sequence[Box], iou_threshold: float = 0.5) -> dict[str, float | int]:
    matched: set[int] = set()
    true_positive = 0
    for prediction in sorted(predictions, key=lambda item: item.score, reverse=True):
        candidates = [(idx, iou(prediction, target)) for idx, target in enumerate(truth) if idx not in matched and prediction.label == target.label]
        if candidates:
            best_index, overlap = max(candidates, key=lambda item: item[1])
            if overlap >= iou_threshold:
                matched.add(best_index)
                true_positive += 1
    false_positive = len(predictions) - true_positive
    false_negative = len(truth) - true_positive
    precision = true_positive / len(predictions) if predictions else 0.0
    recall = true_positive / len(truth) if truth else 0.0
    miss_rate = false_negative / len(truth) if truth else 0.0
    return {
        "tp": true_positive,
        "fp": false_positive,
        "fn": false_negative,
        "precision": precision,
        "recall": recall,
        "miss_rate": miss_rate,
    }


def validate_p2_pyramid(strides: Sequence[int], object_pixels: float) -> dict[str, float | bool]:
    if sorted(set(strides)) != list(strides) or any(stride <= 0 for stride in strides):
        raise ValueError("strides must be unique, positive and sorted")
    cells_on_smallest_level = object_pixels / strides[0]
    return {"has_p2": 4 in strides, "cells_on_finest_level": cells_on_smallest_level, "adequate_sampling": cells_on_smallest_level >= 2.0}


def symmetric_int8(values: Sequence[float]) -> tuple[list[int], list[float], float]:
    if not values:
        raise ValueError("values must not be empty")
    peak = max(abs(value) for value in values)
    scale = peak / 127.0 if peak else 1.0
    quantized = [int(clamp(round(value / scale), -127, 127)) for value in values]
    restored = [value * scale for value in quantized]
    return quantized, restored, scale


def temporal_fault_score(samples: Sequence[float], alpha: float = 0.25) -> float:
    """EWMA residual score used as a transparent LSTM/R-CNN interface stand-in."""
    if len(samples) < 3 or not 0.0 < alpha <= 1.0:
        raise ValueError("need three samples and alpha in (0, 1]")
    level = samples[0]
    residuals: list[float] = []
    for value in samples[1:]:
        residuals.append(abs(value - level))
        level = alpha * value + (1.0 - alpha) * level
    baseline = sum(residuals[:-1]) / max(1, len(residuals) - 1)
    return residuals[-1] / max(1e-9, baseline)


def demo() -> dict[str, object]:
    truth = [Box(0, 0, 10, 10), Box(20, 20, 25, 25)]
    predictions = [Box(0, 0, 10, 10, 0.95), Box(19, 19, 25, 25, 0.8), Box(40, 40, 45, 45, 0.4)]
    q, restored, scale = symmetric_int8([-1.2, -0.1, 0.0, 0.7, 1.0])
    max_error = max(abs(a - b) for a, b in zip([-1.2, -0.1, 0.0, 0.7, 1.0], restored))
    return {
        "detection": detection_metrics(predictions, truth),
        "pyramid": validate_p2_pyramid([4, 8, 16, 32], 12.0),
        "int8": {"scale": round(scale, 7), "max_abs_error": round(max_error, 7), "codes": q},
        "motor_fault_score": round(temporal_fault_score([1.0, 1.01, 0.99, 1.02, 1.8]), 3),
    }
