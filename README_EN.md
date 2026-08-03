# Zipeng Li | Embodied AI & Robotics Systems Portfolio

[中文](README.md) · [Research index](docs/RESEARCH.md) · [Evidence matrix](docs/RESUME_EVIDENCE_MATRIX.md) · [Offline bundle](dist/lizipeng-embodied-ai-portfolio.zip)

This public portfolio reconstructs six resume projects as clean-room, runnable demonstrations: quadruped SLAM, a Ginger service-robot control plane, GeoScan Pro sensor fusion, industrial vision, ROS2/3DGS visualization, and an embedded BMS estimator.

It is **not** production source code from any employer. It contains no customer data, credentials, proprietary maps, model weights, or unpublished patent/paper content. Resume metrics are explicitly treated as reported historical results; repository tests validate only the included synthetic demos.

## Run

```bash
python scripts/run_all_demos.py
python -m pip install -e .
python -m unittest discover -s tests -v
```

Or install the local command:

```bash
python -m pip install -e .
portfolio-demo all
```

## Deliverables

| Project | Runnable artifact | Engineering focus |
|---|---|---|
| Quadruped SLAM | IMU preintegration, voxel filter, 2D ICP, loop gate | deterministic edge pipeline |
| Ginger robot | staged diagnostics, rosbridge messages, safety-gated commands | local web/ROS control |
| GeoScan Pro | lightweight factor graph, sensor gates, USB-CDC frames | multi-sensor handheld mapping |
| Industrial vision | detection metrics, P2 config checks, temporal anomaly score, INT8 simulation | small defects and edge inference |
| ROS2 + 3DGS | ASCII PLY parser and MarkerArray conversion | frame/topic/timestamp correctness |
| BMS | Thevenin plant, adaptive EKF, balancing and scheduling | MCU-oriented state estimation |

See each design under [`projects/`](projects/), the research trail in [`docs/RESEARCH.md`](docs/RESEARCH.md), and the exact resume-to-artifact boundary in [`docs/RESUME_EVIDENCE_MATRIX.md`](docs/RESUME_EVIDENCE_MATRIX.md).

## Licensing

Original demo code in this repository is MIT licensed. Referenced projects and papers retain their own licenses. In particular, the original GraphDeco 3D Gaussian Splatting implementation has non-commercial research restrictions, while Ultralytics software uses AGPL-3.0 or an enterprise license.
