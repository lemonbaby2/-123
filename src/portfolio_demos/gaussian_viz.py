"""ASCII PLY to ROS2-style MarkerArray conversion without ROS dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .common import clamp


@dataclass(frozen=True)
class Gaussian:
    x: float
    y: float
    z: float
    scale: float
    opacity: float
    red: int
    green: int
    blue: int


def parse_ascii_ply(text: str) -> list[Gaussian]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[0] != "ply" or "format ascii 1.0" not in lines:
        raise ValueError("only ASCII PLY 1.0 is supported")
    try:
        end = lines.index("end_header")
    except ValueError as exc:
        raise ValueError("missing end_header") from exc
    properties = [line.split()[-1] for line in lines[:end] if line.startswith("property ")]
    required = {"x", "y", "z"}
    if not required.issubset(properties):
        raise ValueError("PLY must contain x/y/z")
    output: list[Gaussian] = []
    for row in lines[end + 1 :]:
        values = row.split()
        if len(values) != len(properties):
            raise ValueError("PLY row/property mismatch")
        item = dict(zip(properties, values))
        output.append(
            Gaussian(
                x=float(item["x"]),
                y=float(item["y"]),
                z=float(item["z"]),
                scale=max(0.001, float(item.get("scale", item.get("scale_0", 0.03)))),
                opacity=clamp(float(item.get("opacity", 1.0)), 0.0, 1.0),
                red=int(item.get("red", 200)),
                green=int(item.get("green", 200)),
                blue=int(item.get("blue", 200)),
            )
        )
    return output


def marker_array(gaussians: Iterable[Gaussian], frame_id: str = "map", stamp_ns: int = 0) -> dict[str, object]:
    if not frame_id or stamp_ns < 0:
        raise ValueError("invalid frame or timestamp")
    markers = []
    for index, gaussian in enumerate(gaussians):
        markers.append(
            {
                "header": {"frame_id": frame_id, "stamp_ns": stamp_ns},
                "ns": "gaussians",
                "id": index,
                "type": "SPHERE",
                "action": "ADD",
                "pose": {"position": {"x": gaussian.x, "y": gaussian.y, "z": gaussian.z}},
                "scale": {"x": 2 * gaussian.scale, "y": 2 * gaussian.scale, "z": 2 * gaussian.scale},
                "color": {
                    "r": gaussian.red / 255.0,
                    "g": gaussian.green / 255.0,
                    "b": gaussian.blue / 255.0,
                    "a": gaussian.opacity,
                },
            }
        )
    return {"markers": markers}


def validate_stream(messages: Iterable[dict[str, object]]) -> tuple[bool, str]:
    last_stamp = -1
    frame: str | None = None
    for message in messages:
        markers = message.get("markers", [])
        for marker in markers:  # type: ignore[assignment]
            header = marker["header"]
            if frame is None:
                frame = header["frame_id"]
            if header["frame_id"] != frame:
                return False, "frame_changed"
            if header["stamp_ns"] < last_stamp:
                return False, "time_reversed"
            last_stamp = header["stamp_ns"]
    return True, "valid"


def demo(sample_path: str | None = None) -> dict[str, object]:
    path = Path(sample_path) if sample_path else Path(__file__).parents[2] / "projects" / "05_ros2_3dgs" / "sample_gaussians.ply"
    gaussians = parse_ascii_ply(path.read_text(encoding="utf-8"))
    message = marker_array(gaussians, stamp_ns=1_000_000)
    return {"gaussians": len(gaussians), "markers": len(message["markers"]), "stream": validate_stream([message])[1], "frame": "map"}
