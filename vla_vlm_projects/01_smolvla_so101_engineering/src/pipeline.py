"""Dependency-free VLA action safety demo.

This is intentionally a dry-run reference. Real SmolVLA inference is delegated to
Hugging Face LeRobot; the adapter here demonstrates the engineering boundary.
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class GateResult:
    accepted: bool
    reason: str
    actions: list[list[float]]


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def safety_gate(
    action_chunk: Iterable[Iterable[float]],
    limits: list[list[float]],
    max_step_delta: float,
    perception_confidence: float,
    min_confidence: float,
) -> GateResult:
    raw = [list(map(float, row)) for row in action_chunk]
    if perception_confidence < min_confidence:
        return GateResult(False, "perception_confidence_too_low", [])
    if not raw:
        return GateResult(False, "empty_action_chunk", [])
    dim = len(limits)
    if any(len(row) != dim for row in raw):
        return GateResult(False, "action_dimension_mismatch", [])

    out: list[list[float]] = []
    for i, row in enumerate(raw):
        bounded = [clamp(v, limits[j][0], limits[j][1]) for j, v in enumerate(row)]
        if i:
            prev = out[-1]
            bounded = [
                clamp(v, prev[j] - max_step_delta, prev[j] + max_step_delta)
                for j, v in enumerate(bounded)
            ]
        out.append(bounded)
    return GateResult(True, "dry_run_safe_chunk", out)


def demo() -> dict[str, object]:
    cfg = json.loads((ROOT / "config/system.json").read_text())
    predicted = [
        [0.05, 0.10, -0.05, 0.02, 0.00, 0.20],
        [0.12, 0.40, -0.10, 0.04, 0.01, 0.55],
        [0.20, 1.80, -0.15, 0.08, 0.02, 0.90],
    ]
    result = safety_gate(
        predicted,
        cfg["action_limits"],
        float(cfg["max_step_delta"]),
        perception_confidence=0.91,
        min_confidence=float(cfg["min_perception_confidence"]),
    )
    return {
        "project": "smolvla_so101_engineering",
        "mode": "dry-run",
        "accepted": result.accepted,
        "reason": result.reason,
        "input_steps": len(predicted),
        "safe_action_chunk": result.actions,
    }

if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
