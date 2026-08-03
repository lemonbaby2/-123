"""Safe mock control plane for a rosbridge-connected service robot."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import PurePosixPath
from typing import Any


class RecoveryStage(str, Enum):
    NIC = "nic"
    SSH = "ssh"
    ROS = "ros"
    NAVIGATION = "navigation"
    MAP = "map"
    MOTION = "motion"


@dataclass(frozen=True)
class RobotHealth:
    nic_up: bool
    ssh_ok: bool
    ros_ok: bool
    navigation_ok: bool
    map_loaded: bool
    localization_confidence: float
    emergency_stop: bool = False


def first_failed_stage(health: RobotHealth) -> RecoveryStage | None:
    checks = [
        (RecoveryStage.NIC, health.nic_up),
        (RecoveryStage.SSH, health.ssh_ok),
        (RecoveryStage.ROS, health.ros_ok),
        (RecoveryStage.NAVIGATION, health.navigation_ok),
        (RecoveryStage.MAP, health.map_loaded),
        (
            RecoveryStage.MOTION,
            health.localization_confidence >= 0.75 and not health.emergency_stop,
        ),
    ]
    return next((stage for stage, passed in checks if not passed), None)


def navigation_allowed(health: RobotHealth) -> tuple[bool, str]:
    failed = first_failed_stage(health)
    return (failed is None, "ready" if failed is None else f"blocked_at:{failed.value}")


def rosbridge_publish(topic: str, message: dict[str, Any]) -> dict[str, Any]:
    if not topic.startswith("/"):
        raise ValueError("ROS topic must be absolute")
    return {"op": "publish", "topic": topic, "msg": message}


def rosbridge_service(service: str, arguments: dict[str, Any], request_id: str) -> dict[str, Any]:
    if not service.startswith("/") or not request_id:
        raise ValueError("service must be absolute and request_id non-empty")
    return {"op": "call_service", "service": service, "args": arguments, "id": request_id}


def validated_map_uri(uri: str, allowed_root: str = "/maps") -> str:
    """Allow a normalized YAML path below a configured robot-side map root."""
    path = PurePosixPath(uri)
    root = PurePosixPath(allowed_root)
    if path.suffix.lower() not in {".yaml", ".yml"} or ".." in path.parts:
        raise ValueError("map URI must be a normalized YAML path")
    if path.parts[: len(root.parts)] != root.parts:
        raise ValueError("map URI is outside the allowed root")
    return str(path)


def build_navigation_command(health: RobotHealth, x: float, y: float, yaw: float) -> dict[str, Any]:
    allowed, reason = navigation_allowed(health)
    if not allowed:
        raise RuntimeError(reason)
    return rosbridge_publish(
        "/goal_pose",
        {
            "header": {"frame_id": "map"},
            "pose": {"x": float(x), "y": float(y), "yaw": float(yaw)},
        },
    )


def demo() -> dict[str, object]:
    recovering = RobotHealth(True, True, True, True, False, 0.91)
    healthy = RobotHealth(True, True, True, True, True, 0.91)
    return {
        "recovery_stage": first_failed_stage(recovering).value,
        "map_request": rosbridge_service(
            "/map_server/load_map",
            {"map_url": validated_map_uri("/maps/demo.yaml")},
            "load-map-001",
        ),
        "navigation": build_navigation_command(healthy, 1.2, -0.3, 0.0),
        "note": "mock protocol only; no physical robot is contacted",
    }


if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2, sort_keys=True))
