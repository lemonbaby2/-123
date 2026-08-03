"""Sensor quality, factor-graph and USB frame demos for the handheld mapper."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import struct
from typing import Iterable


def crc16_ccitt(data: bytes, seed: int = 0xFFFF) -> int:
    crc = seed
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def encode_frame(message_type: int, sequence: int, payload: bytes) -> bytes:
    if not 0 <= message_type <= 255 or not 0 <= sequence <= 65535 or len(payload) > 1024:
        raise ValueError("frame field out of range")
    body = struct.pack("<BHH", message_type, sequence, len(payload)) + payload
    return b"\xA5\x5A" + body + struct.pack("<H", crc16_ccitt(body))


def decode_frame(frame: bytes) -> tuple[int, int, bytes]:
    if len(frame) < 9 or frame[:2] != b"\xA5\x5A":
        raise ValueError("invalid frame header")
    message_type, sequence, length = struct.unpack("<BHH", frame[2:7])
    if len(frame) != 9 + length:
        raise ValueError("invalid payload length")
    body, expected = frame[2:-2], struct.unpack("<H", frame[-2:])[0]
    if crc16_ccitt(body) != expected:
        raise ValueError("CRC mismatch")
    return message_type, sequence, frame[7:-2]


@dataclass(frozen=True)
class SensorSample:
    name: str
    age_ms: float
    covariance: float
    finite: bool = True


def sensor_quality(sample: SensorSample) -> tuple[bool, str]:
    if not sample.finite:
        return False, "non_finite"
    limits = {"imu": (20.0, 0.05), "lidar": (150.0, 0.20), "rtk": (1000.0, 1.0), "camera": (250.0, 0.5)}
    if sample.name not in limits:
        return False, "unknown_sensor"
    max_age, max_covariance = limits[sample.name]
    if sample.age_ms > max_age:
        return False, "stale"
    if sample.covariance > max_covariance:
        return False, "uncertain"
    return True, "accepted"


@dataclass(frozen=True)
class RelativeFactor:
    i: int
    j: int
    dx: float
    dy: float
    weight: float


@dataclass(frozen=True)
class AbsoluteFactor:
    i: int
    x: float
    y: float
    weight: float


def optimize_pose_graph(
    node_count: int,
    relative: Iterable[RelativeFactor],
    absolute: Iterable[AbsoluteFactor],
    iterations: int = 80,
) -> list[tuple[float, float]]:
    """Small weighted relaxation solver illustrating incremental graph constraints."""
    if node_count < 1:
        raise ValueError("node_count must be positive")
    rel = list(relative)
    anchors = [AbsoluteFactor(0, 0.0, 0.0, 1e6), *absolute]
    poses = [[0.0, 0.0] for _ in range(node_count)]
    for _ in range(iterations):
        proposals: list[list[tuple[float, float, float]]] = [[] for _ in poses]
        for factor in rel:
            proposals[factor.j].append((poses[factor.i][0] + factor.dx, poses[factor.i][1] + factor.dy, factor.weight))
            proposals[factor.i].append((poses[factor.j][0] - factor.dx, poses[factor.j][1] - factor.dy, factor.weight))
        for factor in anchors:
            proposals[factor.i].append((factor.x, factor.y, factor.weight))
        for index, candidates in enumerate(proposals):
            if candidates:
                total = sum(weight for _, _, weight in candidates)
                poses[index] = [
                    sum(x * weight for x, _, weight in candidates) / total,
                    sum(y * weight for _, y, weight in candidates) / total,
                ]
    return [(x, y) for x, y in poses]


def remove_dynamic_points(points: Iterable[tuple[float, float, int]], dynamic_labels: set[int]) -> list[tuple[float, float]]:
    return [(x, y) for x, y, label in points if label not in dynamic_labels and math.isfinite(x) and math.isfinite(y)]


def demo() -> dict[str, object]:
    frame = encode_frame(3, 42, b"imu:ok")
    decoded = decode_frame(frame)
    graph = optimize_pose_graph(
        3,
        [RelativeFactor(0, 1, 1.0, 0.0, 20.0), RelativeFactor(1, 2, 1.0, 0.0, 20.0)],
        [AbsoluteFactor(2, 2.05, -0.02, 5.0)],
    )
    samples = [SensorSample("imu", 4.0, 0.01), SensorSample("rtk", 350.0, 0.2)]
    return {
        "usb_frame_bytes": len(frame),
        "usb_round_trip": {"type": decoded[0], "sequence": decoded[1], "payload": decoded[2].decode()},
        "optimized_poses": [[round(x, 4), round(y, 4)] for x, y in graph],
        "sensor_gates": {sample.name: sensor_quality(sample)[1] for sample in samples},
        "static_points": len(remove_dynamic_points([(0.0, 0.0, 0), (1.0, 1.0, 7)], {7})),
    }


if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2, sort_keys=True))
