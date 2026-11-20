# Zipeng Li | Embodied AI & Robotics Systems Portfolio

[中文](README.md) · [Research index](docs/RESEARCH.md) · [Evidence matrix](docs/RESUME_EVIDENCE_MATRIX.md) · [Offline bundle](dist/lizipeng-embodied-ai-portfolio.zip)

This public portfolio contains clean-room, runnable projects plus one ROS 2 teaching platform: resume reconstructions, GaussPatrol, a 3DGS scanner soft-hardware archive, and a differential-drive course lab.

It is **not** production source code from any employer. It contains no customer data, credentials, proprietary maps, model weights, or unpublished patent/paper content. Resume metrics are explicitly treated as reported historical results; repository tests validate only the included synthetic demos.

## 2026-11-21 full local run

Hardware: RTX 4060 8GB (a second GPU reports `GPU is lost`), system Python 3.13 without
torch, remote DGX unreachable. **The 16 resume projects cannot all be executed here** —
VLA 50k+10k-step training, 3DGS, TensorRT engines, Vicon ground truth and 100 h stability
logs need a multi-GPU DGX and original datasets. Everything that *can* run was run,
and the rest is listed as NOT_RUNNABLE rather than faked.

| Stage | Real result |
|---|---|
| Ollama GPU inference | 24 real calls, 3 models; steady 163.2 / 94.3 / 14.1 tok/s (2B / 7B / 9B); 588 nvidia-smi samples, peak VRAM 7388 MiB, peak util 100% |
| MuJoCo hurdle grid | 48 real episodes, best score 2.879, 3 cleared, 41 zero-fall |
| METATRON coding-agent | 5 rounds with trajectory feedback, local 7B: -0.704 -> -0.704 |
| Repository self-check | 61 tests, 58 PASS, 3 FAIL (missing `evidence/course_demo_5min.mp4`) |
| Runnability ledger | 3 runnable / 6 partial / 6 not runnable / 1 verified upstream |

Eight real figures are in [`docs/figures/`](docs/figures/), each with a provenance entry
in `evidence/FIGURE_PROVENANCE.json`. No number is synthesized.

## New projects

| Project | Content | Boundary |
|---|---|---|
| [12 Agent runtime](projects/12_agent_runtime_2026-11/README.md) | Idempotent local-model wiring script, Hermes approval verdict-parser fix, measured agent-runtime benchmark | Sanitised; no config/.env/keys; small local models are unfit for primary tool orchestration |
| [13 METATRON coding-agent](projects/13_metatron_coding_agent/README.md) | MuJoCo physics + frozen PD stand-in + AST sandbox + evaluation + iteration loop, 5 real result logs | NVIDIA base-policy weights/MoCap are unpublished — this is a workflow reproduction, not a full paper reproduction |

## Run

```bash
python scripts/verify_layout.py
python scripts/run_tests.py
python scripts/run_all_demos.py
```

Every project is self-contained; no root package installation or third-party Python dependency is required. For example:

```bash
python projects/01_quadruped_slam/src/quadruped_slam.py
python projects/01_quadruped_slam/tests/test_quadruped_slam.py -v
```

## Deliverables

| Project | Runnable artifact | Engineering focus |
|---|---|---|
| [Quadruped SLAM](projects/01_quadruped_slam/README.md) | Python, tests, config, standalone C++17 voxel demo | deterministic edge pipeline |
| [Ginger robot](projects/02_ginger_robot/README.md) | Python, tests, mock config | local web/ROS control |
| [GeoScan Pro](projects/03_geoscan_pro/README.md) | Python and independent tests | multi-sensor handheld mapping |
| [Industrial vision](projects/04_industrial_vision/README.md) | Python and independent tests | small defects and edge inference |
| [ROS2 + 3DGS](projects/05_ros2_3dgs/README.md) | Python, tests, sample data, ROS2 workspace | frame/topic/timestamp correctness |
| [BMS](projects/06_bms/README.md) | Python, tests, config, standalone C++17 demo | MCU-oriented state estimation |
| [GaussPatrol](projects/07_gausspatrol/README.md) | patrol simulation, tests, SVG/PLY results, technical and submission docs | embodied competition system closure |
| [3DGS scanner soft-hardware](projects/08_3dgs_scanner_soft_hardware/README.md) | PCB PDFs, SOPs, engineering report, test matrix and research references | BMS/main-controller hardware archive |
| [ROS2 course lab](projects/10_ros2_course_lab/README.md) | differential-drive URDF/Xacro, ros2_control, Gazebo world, ros_gz bridge, odometry/PID/SLAM, web dashboard, 5-min screen recording | reproducible ROS2 system integration and fault diagnosis |

See each design under [`projects/`](projects/), the research trail in [`docs/RESEARCH.md`](docs/RESEARCH.md), and the exact resume-to-artifact boundary in [`docs/RESUME_EVIDENCE_MATRIX.md`](docs/RESUME_EVIDENCE_MATRIX.md).

## Verification contract

CI parses all Python files, runs the eight independent test programs on Python 3.10 and 3.12, executes all demos as separate processes, validates the repository layout and local README links, builds the two C++17 projects, and regenerates the deterministic source bundle. Synthetic tests demonstrate code behavior only; they do not reproduce hardware metrics.

The README structure follows the practical overview/dependencies/run/data/troubleshooting/citation flow used by [LIO-SAM](https://github.com/TixiaoShan/LIO-SAM), [rosbridge_suite](https://github.com/RobotWebTools/rosbridge_suite), [GraphDeCo's 3D Gaussian Splatting](https://github.com/graphdeco-inria/gaussian-splatting), and [Ultralytics](https://github.com/ultralytics/ultralytics). No restricted upstream code is copied here.

## Licensing

Original demo code in this repository is MIT licensed. Referenced projects and papers retain their own licenses. In particular, the original GraphDeco 3D Gaussian Splatting implementation has non-commercial research restrictions, while Ultralytics software uses AGPL-3.0 or an enterprise license.
