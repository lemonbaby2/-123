"""Write source-backed SVG, JSON, PLY and Markdown artifacts."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from html import escape
import json
from pathlib import Path
from typing import Iterable

from .mission import BenchmarkResult, MissionResult
from .models import Pose2D, ScenarioConfig
from .world import load_scenario


PALETTE = {
    "background": "#f7f9fc",
    "grid": "#dde4ee",
    "obstacle": "#334155",
    "truth": "#0f766e",
    "estimate": "#f97316",
    "checkpoint": "#7c3aed",
    "equipment": "#dc2626",
    "dynamic": "#eab308",
}


def _polyline(points: Iterable[Pose2D], sx: float, sy: float, height: float) -> str:
    return " ".join(f"{point.x_m * sx:.1f},{height - point.y_m * sy:.1f}" for point in points)


def trajectory_svg(result: MissionResult, config: ScenarioConfig) -> str:
    width, height = 1000.0, 700.0
    sx, sy = width / config.width_m, height / config.height_m
    elements = [
        f'<rect width="{width}" height="{height}" fill="{PALETTE["background"]}"/>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif}.label{font-size:14px;fill:#0f172a}.small{font-size:11px;fill:#475569}</style>',
    ]
    for x_m in range(int(config.width_m) + 1):
        elements.append(f'<line x1="{x_m*sx:.1f}" y1="0" x2="{x_m*sx:.1f}" y2="{height}" stroke="{PALETTE["grid"]}" stroke-width="0.6"/>')
    for y_m in range(int(config.height_m) + 1):
        y = height - y_m * sy
        elements.append(f'<line x1="0" y1="{y:.1f}" x2="{width}" y2="{y:.1f}" stroke="{PALETTE["grid"]}" stroke-width="0.6"/>')
    terrain_colors = {"gravel": "#d6d3d1", "ramp": "#bfdbfe", "wet": "#bae6fd", "rubble": "#fed7aa"}
    for patch in config.terrain:
        rect = patch.bounds
        elements.append(
            f'<rect x="{rect.x_min_m*sx:.1f}" y="{height-rect.y_max_m*sy:.1f}" width="{(rect.x_max_m-rect.x_min_m)*sx:.1f}" height="{(rect.y_max_m-rect.y_min_m)*sy:.1f}" fill="{terrain_colors.get(patch.name,"#e2e8f0")}" opacity="0.45"/>'
        )
        elements.append(f'<text class="small" x="{rect.x_min_m*sx+5:.1f}" y="{height-rect.y_max_m*sy+16:.1f}">{escape(patch.name)} / {escape(patch.gait_mode)}</text>')
    for rect in config.static_obstacles:
        elements.append(
            f'<rect x="{rect.x_min_m*sx:.1f}" y="{height-rect.y_max_m*sy:.1f}" width="{(rect.x_max_m-rect.x_min_m)*sx:.1f}" height="{(rect.y_max_m-rect.y_min_m)*sy:.1f}" fill="{PALETTE["obstacle"]}" rx="3"/>'
        )
    for index, checkpoint in enumerate(config.checkpoints):
        elements.append(f'<circle cx="{checkpoint.x_m*sx:.1f}" cy="{height-checkpoint.y_m*sy:.1f}" r="8" fill="{PALETTE["checkpoint"]}" stroke="white" stroke-width="2"/>')
        elements.append(f'<text class="label" x="{checkpoint.x_m*sx+10:.1f}" y="{height-checkpoint.y_m*sy-8:.1f}">C{index}</text>')
    for equipment in config.equipment:
        color = PALETTE["equipment"] if equipment.defect_class else "#16a34a"
        elements.append(f'<rect x="{equipment.x_m*sx-5:.1f}" y="{height-equipment.y_m*sy-5:.1f}" width="10" height="10" fill="{color}" transform="rotate(45 {equipment.x_m*sx:.1f} {height-equipment.y_m*sy:.1f})"/>')
    for obstacle in config.dynamic_obstacles:
        points = " ".join(f"{x*sx:.1f},{height-y*sy:.1f}" for x, y in obstacle.path)
        elements.append(f'<polygon points="{points}" fill="none" stroke="{PALETTE["dynamic"]}" stroke-width="2" stroke-dasharray="5 5"/>')
    elements.append(f'<polyline points="{_polyline(result.truth_path,sx,sy,height)}" fill="none" stroke="{PALETTE["truth"]}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
    elements.append(f'<polyline points="{_polyline(result.estimated_path,sx,sy,height)}" fill="none" stroke="{PALETTE["estimate"]}" stroke-width="2" stroke-dasharray="6 4"/>')
    elements.extend([
        '<rect x="18" y="18" width="345" height="95" rx="8" fill="white" opacity="0.94" stroke="#cbd5e1"/>',
        f'<text class="label" x="34" y="43">GaussPatrol - {escape(result.scenario)} trajectory</text>',
        f'<text class="small" x="34" y="65">truth: teal | estimate: orange | dynamic route: yellow</text>',
        f'<text class="small" x="34" y="85">completion={result.route_completion_rate:.1%}, ATE={result.trajectory["ate_rmse_m"]:.3f} m, collisions={result.collisions}</text>',
        f'<text class="small" x="34" y="103">map completeness={result.map_completeness:.1%}, AP50={float(result.perception["ap50_11point"]):.3f}</text>',
    ])
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}">' + "".join(elements) + "</svg>\n"


def dashboard_svg(benchmark: BenchmarkResult) -> str:
    metrics = [
        ("Route completion", benchmark.nominal.route_completion_rate, benchmark.shifted.route_completion_rate, 1.0, "%"),
        ("Avoidance success", benchmark.nominal.avoidance_success_rate, benchmark.shifted.avoidance_success_rate, 1.0, "%"),
        ("Map completeness", benchmark.nominal.map_completeness, benchmark.shifted.map_completeness, 1.0, "%"),
        ("Defect AP50", float(benchmark.nominal.perception["ap50_11point"]), float(benchmark.shifted.perception["ap50_11point"]), 1.0, ""),
        ("ATE RMSE (lower)", benchmark.nominal.trajectory["ate_rmse_m"], benchmark.shifted.trajectory["ate_rmse_m"], max(0.15, benchmark.shifted.trajectory["ate_rmse_m"] * 1.2), "m"),
        ("Mission time (lower)", benchmark.nominal.modelled_mission_time_s, benchmark.shifted.modelled_mission_time_s, max(1.0, benchmark.shifted.modelled_mission_time_s * 1.1), "s"),
    ]
    width, height = 1100, 640
    parts = [f'<rect width="{width}" height="{height}" fill="#f8fafc"/>', '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#0f172a}.title{font-size:26px;font-weight:700}.label{font-size:15px}.value{font-size:12px;fill:#475569}</style>', '<text class="title" x="50" y="52">GaussPatrol reproducible benchmark</text>', '<text class="value" x="50" y="78">Measured from deterministic repository simulation; shifted is a stress proxy, not real-robot data.</text>']
    for index, (name, nominal, shifted, maximum, unit) in enumerate(metrics):
        y = 125 + index * 82
        parts.append(f'<text class="label" x="50" y="{y}">{escape(name)}</text>')
        for offset, value, color, label in ((0, nominal, "#0f766e", "nominal"), (28, shifted, "#f97316", "shifted")):
            bar_width = 720 * min(1.0, max(0.0, value / maximum))
            parts.append(f'<rect x="250" y="{y-18+offset}" width="720" height="18" rx="4" fill="#e2e8f0"/>')
            parts.append(f'<rect x="250" y="{y-18+offset}" width="{bar_width:.1f}" height="18" rx="4" fill="{color}"/>')
            shown = f"{value*100:.1f}%" if unit == "%" else f"{value:.3f} {unit}".strip()
            parts.append(f'<text class="value" x="980" y="{y-4+offset}">{label}: {shown}</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">' + "".join(parts) + "</svg>\n"


def run_report_markdown(benchmark: BenchmarkResult) -> str:
    nominal, shifted = benchmark.nominal, benchmark.shifted
    return f"""# GaussPatrol 可复现运行报告

> 自动生成。所有数值来自当前仓库确定性二维仿真。`shifted` 是人为增加里程计噪声、速度下降和检测退化的压力场景，不是真机 Sim-to-Real 实测。

![指标对比](dashboard.svg)

## 结果摘要

| 指标 | Nominal | Shifted | 口径 |
|---|---:|---:|---|
| 路线完成率 | {nominal.route_completion_rate:.1%} | {shifted.route_completion_rate:.1%} | 到达检查点/计划检查点 |
| ATE RMSE | {nominal.trajectory['ate_rmse_m']:.4f} m | {shifted.trajectory['ate_rmse_m']:.4f} m | 2D 估计轨迹对真值 |
| RPE RMSE | {nominal.trajectory['rpe_rmse_m']:.4f} m | {shifted.trajectory['rpe_rmse_m']:.4f} m | 相邻步位移误差 |
| 动态避障成功率 | {nominal.avoidance_success_rate:.1%} | {shifted.avoidance_success_rate:.1%} | 成功重规划/触发次数 |
| 规划 P95 | {nominal.planning_latency_ms['p95']:.3f} ms | {shifted.planning_latency_ms['p95']:.3f} ms | 本机 Python `perf_counter` |
| 感知 P95 | {nominal.perception_latency_ms['p95']:.3f} ms | {shifted.perception_latency_ms['p95']:.3f} ms | 合成检测器函数耗时，不是 YOLO |
| 地图完整度 | {nominal.map_completeness:.1%} | {shifted.map_completeness:.1%} | 被观测静态障碍边界栅格占比 |
| 缺陷 AP50 (11-point) | {float(nominal.perception['ap50_11point']):.3f} | {float(shifted.perception['ap50_11point']):.3f} | 合成设备缺陷检测 |
| 碰撞 | {nominal.collisions} | {shifted.collisions} | 几何碰撞检查 |
| 模型任务时间 | {nominal.modelled_mission_time_s:.2f} s | {shifted.modelled_mission_time_s:.2f} s | 距离/地形速度+等待 |

## 可视化

- [Nominal 轨迹](nominal_trajectory.svg)
- [Shifted 轨迹](shifted_trajectory.svg)
- [Nominal Gaussian PLY](nominal_gaussians.ply)
- [Shifted Gaussian PLY](shifted_gaussians.ply)
- [完整机器可读指标](metrics.json)
- [事件日志](events.jsonl)

## 不能从本报告推出的结论

- 没有运行 LIO-SAM、FAST-LIVO2、YOLO、Isaac Lab 或真实 3DGS 训练；
- 没有连接山猫 S10、LiDAR、IMU、RGB-D 或 `ros2_control`；
- 没有真实雨天、碎石、楼梯、动态人员或设备缺陷数据；
- 因此这些结果只能证明仓库闭环和评测代码可运行，不能作为比赛真机成绩。
"""


def write_artifacts(benchmark: BenchmarkResult, scenario_path: str | Path, output_dir: str | Path) -> list[Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    nominal_config = load_scenario(scenario_path, variant="nominal")
    shifted_config = load_scenario(scenario_path, variant="shifted")
    files = {
        "metrics.json": json.dumps(benchmark.summary(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        "events.jsonl": "\n".join(json.dumps({"scenario": result.scenario, **event.to_dict()}, ensure_ascii=False, sort_keys=True) for result in (benchmark.nominal, benchmark.shifted) for event in result.events) + "\n",
        "nominal_trajectory.svg": trajectory_svg(benchmark.nominal, nominal_config),
        "shifted_trajectory.svg": trajectory_svg(benchmark.shifted, shifted_config),
        "dashboard.svg": dashboard_svg(benchmark),
        "nominal_gaussians.ply": benchmark.nominal.gaussian_map.to_ascii_ply(),
        "shifted_gaussians.ply": benchmark.shifted.gaussian_map.to_ascii_ply(),
        "RUN_REPORT.md": run_report_markdown(benchmark),
    }
    written = []
    for name, content in files.items():
        path = output / name
        path.write_text(content, encoding="utf-8", newline="\n")
        written.append(path)
    manifest_lines = [f"{sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in sorted(written)]
    manifest = output / "SHA256SUMS.txt"
    manifest.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8", newline="\n")
    written.append(manifest)
    return written
