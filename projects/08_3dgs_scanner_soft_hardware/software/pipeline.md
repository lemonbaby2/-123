# 3DGS Scanner Software Pipeline

## Offline First

The first implementation should be offline and repeatable:

1. Load a recorded scan session.
2. Validate metadata and calibration files.
3. Run odometry or import a known trajectory.
4. Convert frames and poses into the selected 3DGS backend input format.
5. Train/reconstruct.
6. Export viewer artifacts and quality logs.

## Live Preview Later

Live preview should wait until:

- timestamps are stable,
- power faults are handled,
- sensor calibration is repeatable,
- offline reconstruction works on the scanner's own datasets.

## Quality Metrics

| Metric | Purpose |
|---|---|
| Pose drift | Detect odometry instability |
| Reprojection / alignment error | Check calibration |
| Reconstruction coverage | Find missing viewpoints |
| Runtime and GPU memory | Size Jetson / workstation requirements |
| Export size | Estimate storage and cloud-sync needs |
