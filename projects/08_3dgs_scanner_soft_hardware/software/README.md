# Software Stack Plan

This folder is reserved for the 3DGS scanner software stack.

## Proposed Modules

| Module | Purpose | Suggested dependencies |
|---|---|---|
| capture | Synchronized camera, lidar, IMU and GNSS capture | ROS 2, camera SDK, lidar SDK |
| calibration | Intrinsic/extrinsic calibration and timing checks | Kalibr, OpenCV, Open3D |
| odometry | LIO/LIVO/VIO front end | FAST-LIO, FAST-LIVO2 style pipelines |
| reconstruction | Gaussian Splatting / SDF reconstruction backend | gsplat, gaussian-splatting, SplaTAM, GS-SDF |
| viewer | Live point cloud / Gaussian / trajectory visualization | Open3D, WebGL, SIBR viewer |
| export | Dataset packaging and deliverables | PLY, COLMAP, rosbag, metadata JSON |

## Minimum Dataset Contract

Every scan session should export:

```text
scan_<date>_<scene>/
├── metadata.json
├── calibration/
├── camera/
├── lidar/
├── imu/
├── gnss/
├── trajectories/
├── reconstruction/
└── logs/
```

## Next Implementation Milestones

1. Define sensor list, camera model, lidar model, IMU model and sync source.
2. Add ROS 2 package skeleton and dataset writer.
3. Add calibration scripts and sample metadata schema.
4. Add offline 3DGS reconstruction adapter.
5. Add viewer/export pipeline.
