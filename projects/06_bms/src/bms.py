"""MCU-oriented Thevenin battery plant, adaptive EKF and balancing logic."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Sequence


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("mean requires at least one value")
    return sum(values) / len(values)


def ocv_from_soc(soc: float) -> float:
    soc = clamp(soc, 0.0, 1.0)
    return 3.0 + 1.15 * soc + 0.05 * math.tanh((soc - 0.5) * 8.0)


def docv_dsoc(soc: float) -> float:
    t = math.tanh((clamp(soc, 0.0, 1.0) - 0.5) * 8.0)
    return 1.15 + 0.4 * (1.0 - t * t)


@dataclass
class TheveninCell:
    capacity_ah: float = 3.0
    r0: float = 0.035
    r1: float = 0.018
    c1: float = 2400.0
    soc: float = 0.8
    v_rc: float = 0.0

    def step(self, current_a: float, dt: float) -> float:
        if dt <= 0 or self.capacity_ah <= 0:
            raise ValueError("dt and capacity must be positive")
        a = math.exp(-dt / (self.r1 * self.c1))
        self.soc = clamp(self.soc - current_a * dt / (self.capacity_ah * 3600.0), 0.0, 1.0)
        self.v_rc = a * self.v_rc + self.r1 * (1.0 - a) * current_a
        return ocv_from_soc(self.soc) - self.v_rc - self.r0 * current_a


@dataclass
class AdaptiveEkf:
    capacity_ah: float = 3.0
    r0: float = 0.035
    r1: float = 0.018
    c1: float = 2400.0
    soc: float = 0.65
    v_rc: float = 0.0
    p00: float = 0.02
    p01: float = 0.0
    p10: float = 0.0
    p11: float = 0.01
    q_soc: float = 1e-7
    q_vrc: float = 1e-6
    measurement_variance: float = 4e-4

    def update(self, current_a: float, terminal_voltage: float, dt: float) -> float:
        if dt <= 0 or not math.isfinite(terminal_voltage):
            raise ValueError("invalid EKF input")
        a = math.exp(-dt / (self.r1 * self.c1))
        self.soc = clamp(self.soc - current_a * dt / (self.capacity_ah * 3600.0), 0.0, 1.0)
        self.v_rc = a * self.v_rc + self.r1 * (1.0 - a) * current_a
        self.p00 += self.q_soc
        self.p01 *= a
        self.p10 *= a
        self.p11 = a * a * self.p11 + self.q_vrc
        h0, h1 = docv_dsoc(self.soc), -1.0
        predicted_voltage = ocv_from_soc(self.soc) - self.v_rc - self.r0 * current_a
        innovation = terminal_voltage - predicted_voltage
        s = h0 * (h0 * self.p00 + h1 * self.p10) + h1 * (h0 * self.p01 + h1 * self.p11) + self.measurement_variance
        k0 = (self.p00 * h0 + self.p01 * h1) / s
        k1 = (self.p10 * h0 + self.p11 * h1) / s
        old = (self.p00, self.p01, self.p10, self.p11)
        self.soc = clamp(self.soc + k0 * innovation, 0.0, 1.0)
        self.v_rc += k1 * innovation
        self.p00 = (1.0 - k0 * h0) * old[0] - k0 * h1 * old[2]
        self.p01 = (1.0 - k0 * h0) * old[1] - k0 * h1 * old[3]
        self.p10 = -k1 * h0 * old[0] + (1.0 - k1 * h1) * old[2]
        self.p11 = -k1 * h0 * old[1] + (1.0 - k1 * h1) * old[3]
        self.measurement_variance = clamp(0.98 * self.measurement_variance + 0.02 * innovation * innovation, 1e-6, 0.02)
        return innovation


def balancing_mask(cell_soc: Sequence[float], temperatures_c: Sequence[float], delta: float = 0.01, max_temp_c: float = 50.0) -> list[bool]:
    if len(cell_soc) != len(temperatures_c) or not cell_soc:
        raise ValueError("SOC and temperature vectors must have the same non-zero length")
    target = mean(cell_soc)
    return [soc > target + delta and temp < max_temp_c for soc, temp in zip(cell_soc, temperatures_c)]


def schedulability(tasks: Sequence[tuple[str, float, float]]) -> dict[str, float | bool]:
    """Conservative utilization check: (name, worst_case_ms, period_ms)."""
    utilization = sum(wcet / period for _, wcet, period in tasks)
    return {"utilization": utilization, "within_budget": utilization <= 0.70}


def demo() -> dict[str, object]:
    plant = TheveninCell(soc=0.80)
    ekf = AdaptiveEkf(soc=0.68)
    errors = []
    for index in range(240):
        current = 1.5 if index < 160 else 0.4
        voltage = plant.step(current, 1.0)
        ekf.update(current, voltage, 1.0)
        errors.append(abs(plant.soc - ekf.soc))
    return {
        "plant_soc": round(plant.soc, 6),
        "estimated_soc": round(ekf.soc, 6),
        "final_abs_error": round(errors[-1], 6),
        "balancing_mask": balancing_mask([0.78, 0.80, 0.83, 0.79], [31.0, 32.0, 34.0, 33.0]),
        "scheduler": schedulability([("sample", 0.2, 10.0), ("estimate", 1.4, 100.0), ("telemetry", 0.5, 50.0)]),
    }


if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2, sort_keys=True))
