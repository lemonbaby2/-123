"""Sparse Gaussian-map surrogate built from deterministic range hits."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .world import GridCell, PatrolWorld


@dataclass
class _Accumulator:
    x_sum: float = 0.0
    y_sum: float = 0.0
    z_sum: float = 0.0
    count: int = 0


class GaussianMap:
    """Voxelized points exported as Gaussian-like PLY primitives; not a trained 3DGS model."""

    def __init__(self, world: PatrolWorld):
        self.world = world
        self._voxels: dict[GridCell, _Accumulator] = {}

    def integrate(self, points: Iterable[tuple[float, float, float]]) -> None:
        for x_m, y_m, z_m in points:
            cell = self.world.to_cell(x_m, y_m)
            accumulator = self._voxels.setdefault(cell, _Accumulator())
            accumulator.x_sum += x_m
            accumulator.y_sum += y_m
            accumulator.z_sum += z_m
            accumulator.count += 1

    def points(self) -> list[tuple[float, float, float, int]]:
        output = []
        for cell in sorted(self._voxels):
            value = self._voxels[cell]
            output.append((value.x_sum / value.count, value.y_sum / value.count, value.z_sum / value.count, value.count))
        return output

    def completeness(self) -> float:
        reference = self.world.reference_surface_cells()
        if not reference:
            return 1.0
        observed = reference.intersection(self._voxels)
        return len(observed) / len(reference)

    def to_ascii_ply(self) -> str:
        points = self.points()
        header = [
            "ply",
            "format ascii 1.0",
            "comment GaussPatrol synthetic range-map Gaussian surrogate",
            f"element vertex {len(points)}",
            "property float x",
            "property float y",
            "property float z",
            "property float scale",
            "property float opacity",
            "property uchar red",
            "property uchar green",
            "property uchar blue",
            "end_header",
        ]
        resolution = self.world.config.resolution_m
        rows = []
        for x_m, y_m, z_m, count in points:
            opacity = min(1.0, 0.35 + 0.08 * count)
            rows.append(f"{x_m:.5f} {y_m:.5f} {z_m:.5f} {0.45 * resolution:.5f} {opacity:.5f} 52 152 219")
        return "\n".join([*header, *rows]) + "\n"

    def write_ply(self, path: str | Path) -> None:
        Path(path).write_text(self.to_ascii_ply(), encoding="utf-8")
