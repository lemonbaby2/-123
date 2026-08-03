"""Deterministic synthetic defect detector and transparent AP calculation."""

from __future__ import annotations

import random
import time
from typing import Iterable

from .models import Detection, Equipment, ScenarioConfig


class SyntheticDefectDetector:
    """A seeded detector surrogate; it is not YOLO and uses no images or learned weights."""

    def __init__(self, config: ScenarioConfig):
        self.config = config
        self.random = random.Random(config.random_seed + 202)

    def inspect(self, equipment: Equipment) -> tuple[list[Detection], float]:
        started = time.perf_counter_ns()
        detections: list[Detection] = []
        if equipment.defect_class and self.random.random() <= self.config.detection_probability:
            iou = min(0.98, max(0.0, self.random.gauss(0.78, 0.10)))
            confidence = min(0.99, max(0.05, self.random.gauss(0.84, 0.08)))
            detections.append(
                Detection(
                    equipment.equipment_id,
                    equipment.defect_class,
                    confidence,
                    iou,
                    iou >= 0.5,
                )
            )
        if self.random.random() <= self.config.false_positive_probability:
            detections.append(
                Detection(
                    equipment.equipment_id,
                    "surface_anomaly",
                    min(0.75, max(0.05, self.random.gauss(0.38, 0.12))),
                    0.0,
                    False,
                )
            )
        checksum = sum(ord(char) for char in equipment.equipment_id) * 2654435761 % 2**32
        _ = tuple((checksum ^ index) & 0xFF for index in range(64))
        elapsed_ms = (time.perf_counter_ns() - started) / 1e6
        return detections, elapsed_ms


def detection_metrics(detections: Iterable[Detection], ground_truth_defects: int) -> dict[str, float | int]:
    if ground_truth_defects < 0:
        raise ValueError("ground_truth_defects must be non-negative")
    ordered = sorted(detections, key=lambda item: item.confidence, reverse=True)
    true_positive = 0
    false_positive = 0
    precision_recall: list[tuple[float, float]] = []
    matched_equipment: set[str] = set()
    for detection in ordered:
        valid = detection.is_true_positive and detection.equipment_id not in matched_equipment
        if valid:
            true_positive += 1
            matched_equipment.add(detection.equipment_id)
        else:
            false_positive += 1
        precision = true_positive / (true_positive + false_positive)
        recall = true_positive / ground_truth_defects if ground_truth_defects else 0.0
        precision_recall.append((precision, recall))

    average_precision = 0.0
    if ground_truth_defects:
        for threshold_index in range(11):
            threshold = threshold_index / 10.0
            candidates = [precision for precision, recall in precision_recall if recall >= threshold]
            average_precision += (max(candidates) if candidates else 0.0) / 11.0
    false_negative = max(0, ground_truth_defects - true_positive)
    return {
        "ground_truth_defects": ground_truth_defects,
        "detections": len(ordered),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": true_positive / max(1, true_positive + false_positive),
        "recall": true_positive / ground_truth_defects if ground_truth_defects else 0.0,
        "miss_rate": false_negative / ground_truth_defects if ground_truth_defects else 0.0,
        "ap50_11point": min(1.0, average_precision),
    }
