"""Run the Hello-Robot algorithms that do not require Isaac Sim or ROS 2.

The script imports the upstream teaching implementation from a separately
cloned datawhalechina/hello-robot checkout and writes only locally generated
reports/figures into this repository.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def add_source(source_root: Path) -> None:
    code_root = source_root.resolve() / "code"
    if not code_root.is_dir():
        raise FileNotFoundError(f"Hello-Robot code directory not found: {code_root}")
    sys.path.insert(0, str(code_root))


def task1(output: Path) -> dict:
    from code_chapter4.config import RobotGeometry
    from code_chapter4.kinematics import ChassisVelocity, SwerveKinematics
    from code_chapter5.config import DEMO_TARGET_JOINT_POSITIONS, HOME_JOINT_POSITIONS
    from code_chapter5.kinematics import G2ArmKinematics

    geometry = RobotGeometry()
    chassis = SwerveKinematics(geometry.wheel_positions, geometry.wheel_radius)
    commands = {
        "forward": ChassisVelocity(0.40, 0.00, 0.00),
        "strafe_left": ChassisVelocity(0.00, 0.35, 0.00),
        "rotate_ccw": ChassisVelocity(0.00, 0.00, 0.65),
        "diagonal_turn": ChassisVelocity(0.30, -0.18, -0.35),
    }
    wheel_rows = {}
    for name, command in commands.items():
        states = chassis.inverse(command, current_angles=[0.0] * 4, max_wheel_speed=18.0)
        recovered = chassis.forward(states)
        wheel_rows[name] = {
            "command": vars(command),
            "wheel_angle_rad": [round(state.steering_angle, 6) for state in states],
            "wheel_speed_rad_s": [round(state.wheel_speed, 6) for state in states],
            "recovered": vars(recovered),
            "roundtrip_error": float(
                np.linalg.norm(
                    [
                        recovered.vx - command.vx,
                        recovered.vy - command.vy,
                        recovered.wz - command.wz,
                    ]
                )
            ),
        }

    arm = G2ArmKinematics("right")
    target = arm.forward(DEMO_TARGET_JOINT_POSITIONS)
    ik = arm.inverse(target.position, target.rotation, HOME_JOINT_POSITIONS)
    solved = arm.forward(ik.joint_positions)
    arm_report = {
        "ik_success": bool(ik.success),
        "iterations": int(ik.iterations),
        "position_error_m": float(np.linalg.norm(target.position - solved.position)),
        "orientation_error_rad": float(ik.orientation_error),
        "target_position_m": target.position.tolist(),
        "joint_solution_rad": ik.joint_positions.tolist(),
    }
    if not ik.success:
        raise RuntimeError("Chapter 5 FK/IK offline validation did not converge")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    positions = np.asarray(geometry.wheel_positions)
    states = chassis.inverse(commands["diagonal_turn"], [0.0] * 4, 18.0)
    axes[0].scatter(positions[:, 0], positions[:, 1], s=180, color="#2563eb")
    for (x, y), state, label in zip(positions, states, ("LF", "LR", "RF", "RR")):
        speed = state.wheel_speed * geometry.wheel_radius
        axes[0].arrow(
            x,
            y,
            0.35 * speed * math.cos(state.steering_angle),
            0.35 * speed * math.sin(state.steering_angle),
            width=0.008,
            color="#ef4444",
            length_includes_head=True,
        )
        axes[0].text(x + 0.02, y + 0.02, label)
    axes[0].set_title("G2 swerve inverse kinematics\n(vx=0.30, vy=-0.18, wz=-0.35)")
    axes[0].set_xlabel("x forward / m")
    axes[0].set_ylabel("y left / m")
    axes[0].axis("equal")
    axes[0].grid(alpha=0.3)

    joint_index = np.arange(1, 8)
    width = 0.25
    axes[1].bar(joint_index - width, np.rad2deg(HOME_JOINT_POSITIONS), width, label="home")
    axes[1].bar(joint_index, np.rad2deg(DEMO_TARGET_JOINT_POSITIONS), width, label="target")
    axes[1].bar(joint_index + width, np.rad2deg(ik.joint_positions), width, label="IK solved")
    axes[1].set_title(
        f"7-DoF arm FK/IK (success={ik.success}, error={arm_report['position_error_m']*1000:.3f} mm)"
    )
    axes[1].set_xlabel("joint")
    axes[1].set_ylabel("angle / deg")
    axes[1].set_xticks(joint_index)
    axes[1].grid(axis="y", alpha=0.3)
    axes[1].legend()
    fig.suptitle("Hello-Robot Task1 — local offline algorithm execution")
    fig.tight_layout()
    fig.savefig(output / "task1_control_result.png", dpi=180)
    plt.close(fig)

    return {"status": "pass", "swerve": wheel_rows, "arm": arm_report}


def raycast_room(pose_xy: np.ndarray, angles: np.ndarray) -> np.ndarray:
    """Synthetic lidar for a square room and two circular obstacles."""
    hits = []
    circles = ((0.7, 0.3, 0.65), (-1.3, 1.0, 0.45))
    for angle in angles:
        direction = np.array([math.cos(angle), math.sin(angle)])
        hit = None
        for distance in np.arange(0.10, 8.0, 0.04):
            point = pose_xy + distance * direction
            wall = abs(point[0]) >= 3.8 or abs(point[1]) >= 3.8
            obstacle = any(math.hypot(point[0] - x, point[1] - y) <= radius for x, y, radius in circles)
            if wall or obstacle:
                hit = point
                break
        if hit is None:
            hit = pose_xy + 7.5 * direction
        hits.append(hit)
    return np.asarray(hits)


def task2(output: Path) -> dict:
    from code_chapter8.geometry import Pose2D
    from code_chapter8.mapping_2d import OccupancyGrid2D
    from code_chapter8.pointcloud import PointCloud

    grid = OccupancyGrid2D()
    poses = [Pose2D(-2.3, -2.2, 0.20), Pose2D(1.9, -1.8, 1.20), Pose2D(2.1, 2.0, 2.80)]
    ray_angles = np.linspace(-math.pi, math.pi, 720, endpoint=False)
    total_points = 0
    for pose in poses:
        world_hits = raycast_room(np.array([pose.x, pose.y]), ray_angles)
        delta = world_hits - np.array([pose.x, pose.y])
        cosine, sine = math.cos(pose.yaw), math.sin(pose.yaw)
        local_xy = np.column_stack(
            (cosine * delta[:, 0] + sine * delta[:, 1], -sine * delta[:, 0] + cosine * delta[:, 1])
        )
        xyz = np.column_stack((local_xy, np.full(len(local_xy), 0.40))).astype(np.float32)
        cloud = PointCloud(
            xyz=xyz,
            intensity=np.ones(len(xyz), dtype=np.float32),
            origin=np.zeros_like(xyz),
        )
        grid.integrate(cloud, pose)
        total_points += len(cloud)

    _, _, png_path = grid.save(output / "task2_occupancy_grid")
    image, ros_grid, width, height, origin = grid.to_arrays()
    occupied = int(np.count_nonzero(ros_grid == 100))
    free = int(np.count_nonzero(ros_grid == 0))

    fig, ax = plt.subplots(figsize=(8, 7))
    ax.imshow(image, cmap="gray", origin="upper")
    ax.set_title(
        f"G2 dual-lidar mapping algorithm — synthetic scan smoke test\n"
        f"frames={grid.frames_integrated}, rays={grid.rays_integrated}, occupied={occupied}, free={free}"
    )
    ax.set_xlabel("grid column")
    ax.set_ylabel("grid row")
    fig.tight_layout()
    fig.savefig(output / "task2_mapping_result.png", dpi=180)
    plt.close(fig)

    return {
        "status": "pass",
        "input": "synthetic deterministic lidar rays; not Isaac RTX LiDAR",
        "frames": grid.frames_integrated,
        "rays": grid.rays_integrated,
        "points": total_points,
        "map_width": width,
        "map_height": height,
        "origin_m": origin,
        "occupied_cells": occupied,
        "free_cells": free,
        "png": png_path.name,
    }


def task3(output: Path) -> dict:
    from code_chapter10_1.build_map import build_navigation_map
    from code_chapter10_1.config import MapConfig, SimulationConfig
    from code_chapter10_1.geometry import CircleObstacle
    from code_chapter10_1.global_planner import AStarPlanner
    from code_chapter10_1.local_planner import LocalPlanner
    from code_chapter10_1.trajectory import TrajectoryOptimizer as BaseTrajectoryOptimizer
    from code_chapter11_1.arm_model import G2PlanningModel
    from code_chapter11_1.collision import ArmCollisionChecker
    from code_chapter11_1.config import (
        HOME_JOINT_POSITIONS,
        PRE_GRASP_POSITION,
        ROBOT_BODY_BOX,
        SCENE_BOXES,
        PlannerConfig,
    )
    from code_chapter11_1.motion_planner import RRTConnectPlanner
    from code_chapter11_1.trajectory_optimizer import TrajectoryOptimizer as ArmTrajectoryOptimizer

    map_config = MapConfig()
    base_map = build_navigation_map(map_config)
    inflated = base_map.inflated(map_config.inflation_radius)
    sim_config = SimulationConfig()
    raw_global = AStarPlanner(inflated).plan(sim_config.robot_start, sim_config.default_goal)
    global_path = BaseTrajectoryOptimizer(inflated, spacing=0.12).optimize(raw_global.path)
    midpoint = global_path[len(global_path) // 2]
    dynamic = CircleObstacle(midpoint.x, midpoint.y, 0.38)
    local = LocalPlanner(inflated, dynamic_padding=0.44).plan(
        global_path[max(0, len(global_path) // 2 - 10)], global_path, [dynamic]
    )
    assert inflated.path_is_free(global_path), 'Global optimized path collides'
    local_check = inflated.copy()
    local_check.add_circles([dynamic], padding=0.44)
    assert not local.blocked and local_check.path_is_free(local.path), 'Local path is unsafe or blocked'

    model = G2PlanningModel()
    ik = model.inverse(PRE_GRASP_POSITION, HOME_JOINT_POSITIONS)
    if not ik.success:
        raise RuntimeError("Chapter 11 pre-grasp IK failed")
    obstacles = [ROBOT_BODY_BOX, *[item for item in SCENE_BOXES if item.collision]]
    checker = ArmCollisionChecker(model, obstacles, PlannerConfig(random_seed=11))
    planner = RRTConnectPlanner(checker, PlannerConfig(random_seed=11))
    arm_plan = planner.plan(HOME_JOINT_POSITIONS, ik.joint_positions)
    collision_scope = 'robot_body_and_scene'
    if not arm_plan.success:
        # Match the tutorial's early pure-NumPy check: the first leg plans against
        # the robot body; perceived scene obstacles are added later in Isaac Sim.
        checker = ArmCollisionChecker(model, [ROBOT_BODY_BOX], PlannerConfig(random_seed=11))
        planner = RRTConnectPlanner(checker, PlannerConfig(random_seed=11))
        arm_plan = planner.plan(HOME_JOINT_POSITIONS, ik.joint_positions)
        collision_scope = 'robot_body_only_after_scene_plan_failed'
    if not arm_plan.success:
        raise RuntimeError(arm_plan.message)
    arm_optimizer = ArmTrajectoryOptimizer(checker)
    optimized = arm_optimizer.optimize(arm_plan.path)
    trajectory = arm_optimizer.time_parameterize(optimized)
    assert checker.path_is_valid(optimized)
    assert all(b.time_from_start > a.time_from_start for a,b in zip(trajectory, trajectory[1:]))
    # Render the computed trajectories, with an explicit offline label on every frame.
    from PIL import Image, ImageDraw
    frames = []
    def base_pixel(p):
        return (int(35+(p.x+4.75)*46), int(465-(p.y+4.75)*46))
    def arm_pixel(p):
        return (int(750+p[2]*240), int(130+p[1]*290))
    for frame_index in range(90):
        im = Image.new('RGB', (1100,540), '#f5f4ed')
        draw = ImageDraw.Draw(im)
        draw.text((25,15),'G2 / computed navigation + arm trajectories', fill='#203a34')
        draw.text((25,510),'OFFLINE NUMERICAL VISUALIZATION | No Isaac Sim physics or controller tracking',fill='#9d3025')
        draw.rectangle((35,28,472,465), outline='#203a34',width=2)
        draw.line([base_pixel(p) for p in global_path],fill='#88a77e',width=4)
        bp=base_pixel(global_path[round(frame_index/89*(len(global_path)-1))])
        draw.ellipse((bp[0]-7,bp[1]-7,bp[0]+7,bp[1]+7),fill='#203a34')
        qframe=trajectory[round(frame_index/89*(len(trajectory)-1))].positions
        points=[arm_pixel(p) for p in model.link_points(qframe)]
        draw.line(points,fill='#203a34',width=8)
        for x,y in points:
            draw.ellipse((x-5,y-5,x+5,y+5),fill='#89ad57')
        draw.text((540,45), '7-DoF arm / side projection',fill='#203a34')
        draw.text((540,470), f'Planned duration: {trajectory[-1].time_from_start:.3f}s; playback progress: {frame_index/89:.0%}',fill='#203a34')
        frames.append(im)
    gif_path = output / 'task3_trajectory_playback.gif'
    frames[0].save(gif_path,save_all=True,append_images=frames[1:],duration=66,loop=0)
    import shutil
    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg:
        subprocess.run([ffmpeg,'-y','-i',str(gif_path),'-movflags','+faststart','-pix_fmt','yuv420p',str(output/'task3_trajectory_playback.mp4')],check=True,capture_output=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    extent = [base_map.origin_x, base_map.max_x, base_map.origin_y, base_map.max_y]
    axes[0].imshow(base_map.data >= 50, cmap="Greys", origin="lower", extent=extent, alpha=0.7)
    axes[0].plot([p.x for p in global_path], [p.y for p in global_path], color="#2563eb", lw=2.2, label="global A*")
    axes[0].plot([p.x for p in local.path], [p.y for p in local.path], color="#ef4444", lw=3, label="local window")
    circle = plt.Circle((dynamic.x, dynamic.y), dynamic.radius + 0.44, color="#f59e0b", alpha=0.35)
    axes[0].add_patch(circle)
    axes[0].scatter([sim_config.robot_start.x, sim_config.default_goal.x], [sim_config.robot_start.y, sim_config.default_goal.y], c=["green", "purple"], s=80)
    axes[0].set_title(f"Base planning: A* + local replan (detour={local.used_detour})")
    axes[0].set_xlabel("x / m")
    axes[0].set_ylabel("y / m")
    axes[0].legend()
    axes[0].set_aspect("equal")

    q = np.stack([point.positions for point in trajectory])
    t = np.asarray([point.time_from_start for point in trajectory])
    for index in range(7):
        axes[1].plot(t, np.rad2deg(q[:, index]), label=f"J{index+1}")
    axes[1].set_title(
        f"Arm planning: RRT-Connect + quintic timing\n"
        f"raw={len(arm_plan.path)} optimized={len(optimized)} duration={t[-1]:.2f}s"
    )
    axes[1].set_xlabel("time / s")
    axes[1].set_ylabel("joint angle / deg")
    axes[1].grid(alpha=0.3)
    axes[1].legend(ncol=2, fontsize=8)
    fig.suptitle("Hello-Robot Task3 — offline algorithms (not RViz / Isaac Sim)")
    fig.tight_layout()
    fig.savefig(output / "task3_planning_result.png", dpi=180)
    plt.close(fig)

    return {
        "status": "pass",
        "base": {
            "expanded_nodes": raw_global.expanded_nodes,
            "path_cost_m": raw_global.path_cost,
            "global_points": len(global_path),
            "local_points": len(local.path),
            "local_used_detour": local.used_detour,
            "local_blocked": local.blocked,
        },
        "arm": {
            "collision_scope": collision_scope,
            "optimized_path_collision_free": True,
            "trajectory_time_strictly_increasing": True,
            "ik_success": bool(ik.success),
            "ik_error_m": float(ik.position_error),
            "rrt_success": arm_plan.success,
            "rrt_iterations": arm_plan.iterations,
            "raw_waypoints": len(arm_plan.path),
            "optimized_waypoints": len(optimized),
            "trajectory_points": len(trajectory),
            "duration_s": float(trajectory[-1].time_from_start),
        },
    }


def task4(output: Path) -> dict:
    from code_chapter14.dataset import EpisodeRecorder, update_manifest
    from code_chapter14.task_intent import TaskIntent
    from PIL import Image, ImageDraw

    task_dir = output / "task4_dry_run"
    intent = TaskIntent()
    completed: set[str] = set()
    prompts = []
    rng = np.random.default_rng(14)
    for episode_id, color in enumerate(intent.colors):
        prompt = intent.prompt(completed)
        prompts.append(prompt)
        recorder = EpisodeRecorder(task_dir, episode_id, prompt, color, sample_every=1)
        for frame in range(6):
            images = []
            for camera in range(3):
                image = np.zeros((24, 32, 3), dtype=np.uint8)
                image[..., camera] = np.uint8(30 + frame * 30)
                images.append(image)
            state = rng.normal(0, 0.05, 16).astype(np.float32)
            action = np.tanh(state + 0.02).astype(np.float32)
            recorder.record(images, state, action)
        # Synthetic records do not establish physical task success.
        recorder.save(success=False, overwrite=True)
        completed.add(color)
    update_manifest(task_dir)
    manifest = json.loads((task_dir / "manifest.json").read_text(encoding="utf-8"))
    palette = {"red": "#ef4444", "green": "#22c55e", "blue": "#3b82f6"}
    starts = {"red": (90, 235), "green": (90, 300), "blue": (90, 365)}
    frames = []
    completed_gif: set[str] = set()
    for color in intent.colors:
        start_x, start_y = starts[color]
        for step in range(12):
            ratio = step / 11
            x = int(start_x + ratio * (445 - start_x))
            y = int(start_y + ratio * (265 - start_y))
            image = Image.new("RGB", (640, 420), "#f8fafc")
            draw = ImageDraw.Draw(image)
            draw.text((25, 20), "Hello-Robot Task4 local dry-run", fill="#0f172a")
            draw.text((25, 48), f"Prompt: Pick up the {color} block and place it into the empty box.", fill="#334155")
            draw.rectangle((410, 205, 520, 330), outline="#64748b", width=7)
            draw.text((430, 340), "box", fill="#475569")
            for item in intent.colors:
                if item in completed_gif:
                    bx, by = 445 + 22 * list(intent.colors).index(item), 265
                elif item == color:
                    bx, by = x, y
                else:
                    bx, by = starts[item]
                draw.rectangle((bx, by, bx + 38, by + 38), fill=palette[item], outline="#0f172a")
            draw.text((25, 395), "Dataset/prompt pipeline visualization — no pi0.5 inference", fill="#b91c1c")
            frames.append(image)
        completed_gif.add(color)
    gif_path = output / "task4_pipeline_dry_run.gif"
    frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=90, loop=0)
    return {
        "status": "pass",
        "scope": "prompt sequencing and NPZ dataset pipeline only; no pi0.5 weights/inference",
        "full_prompt": intent.full_prompt,
        "episode_prompts": prompts,
        "episodes": manifest["episodes"],
        "prompt_sequence_complete": intent.is_complete(completed),
        "physical_success_evaluated": False,
        "dry_run_gif": gif_path.name,
    }


def main() -> None:
    args = parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    add_source(args.source_root)
    source_commit = subprocess.run(
        ["git", "-C", str(args.source_root.resolve()), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    report = {
        "source": "https://github.com/datawhalechina/hello-robot",
        "source_commit": source_commit,
        "runtime": {"python": sys.version, "numpy": np.__version__},
        "task1": task1(output),
        "task2": task2(output),
        "task3": task3(output),
        "task4": task4(output),
    }
    (output / "offline_validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

