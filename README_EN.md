# Zipeng Li | Embodied AI & Robotics Systems Portfolio

[中文](README.md) · [Research index](docs/RESEARCH.md) · [Evidence matrix](docs/RESUME_EVIDENCE_MATRIX.md) · [Offline bundle](dist/lizipeng-embodied-ai-portfolio.zip)

This public portfolio reconstructs six resume projects as clean-room, runnable demonstrations: quadruped SLAM, a Ginger service-robot control plane, GeoScan Pro sensor fusion, industrial vision, ROS2/3DGS visualization, and an embedded BMS estimator.

It is **not** production source code from any employer. It contains no customer data, credentials, proprietary maps, model weights, or unpublished patent/paper content. Resume metrics are explicitly treated as reported historical results; repository tests validate only the included synthetic demos.

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

See each design under [`projects/`](projects/), the research trail in [`docs/RESEARCH.md`](docs/RESEARCH.md), and the exact resume-to-artifact boundary in [`docs/RESUME_EVIDENCE_MATRIX.md`](docs/RESUME_EVIDENCE_MATRIX.md).

## Verification contract

CI parses all Python files, runs the six independent test programs on Python 3.10 and 3.12, executes all demos as separate processes, validates the repository layout and local README links, builds the two C++17 projects, and regenerates the deterministic source bundle. Synthetic tests demonstrate code behavior only; they do not reproduce the resume's hardware metrics.

The README structure follows the practical overview/dependencies/run/data/troubleshooting/citation flow used by [LIO-SAM](https://github.com/TixiaoShan/LIO-SAM), [rosbridge_suite](https://github.com/RobotWebTools/rosbridge_suite), [GraphDeCo's 3D Gaussian Splatting](https://github.com/graphdeco-inria/gaussian-splatting), and [Ultralytics](https://github.com/ultralytics/ultralytics). No restricted upstream code is copied here.

## Licensing

Original demo code in this repository is MIT licensed. Referenced projects and papers retain their own licenses. In particular, the original GraphDeco 3D Gaussian Splatting implementation has non-commercial research restrictions, while Ultralytics software uses AGPL-3.0 or an enterprise license.
