# Research Repository Index

This page collects public repositories relevant to a 3DGS scanner. It is intentionally an index, not a code dump.

## Recommended Architecture Mapping

| Scanner layer | Reference projects | Why it matters |
|---|---|---|
| Lidar-inertial odometry | HKU-MARS FAST_LIO, FAST-LIVO2 | Robust real-time pose front end for moving scanner |
| Visual-lidar mapping | HKU-MARS r3live, FAST-LIVO2 | Colorized mapping and camera-lidar fusion patterns |
| 3DGS reconstruction | INRIA gaussian-splatting, gsplat, SplaTAM, GS-SDF | Gaussian representation, rasterization and dense SLAM references |
| Geometry consistency | HKU-MARS GS-SDF, GS-LIVO | Stronger geometric constraints for scanner-grade reconstruction |
| Visualization / QA | Open3D, SIBR viewer, gsplat tooling | Debug point clouds, trajectories and Gaussian outputs |

## Curated Repositories

### HKU-MARS / GS-SDF

- URL: https://github.com/hku-mars/GS-SDF
- Topic: LiDAR-augmented Gaussian Splatting and neural SDF for geometry-consistent rendering/reconstruction.
- License: GPL-2.0 reported by GitHub API.
- Integration: reference/submodule only unless product licensing is reviewed.

### HKU-MARS / FAST-LIVO2

- URL: https://github.com/hku-mars/FAST-LIVO2
- Topic: Fast direct LiDAR-Inertial-Visual Odometry.
- License: GPL-2.0 reported by GitHub API.
- Integration: primary odometry reference; do not copy source into proprietary firmware/software without license review.

### HKU-MARS / FAST_LIO

- URL: https://github.com/hku-mars/FAST_LIO
- Topic: computationally efficient lidar-inertial odometry.
- License: GPL-2.0 reported by GitHub API.
- Integration: LIO baseline and test dataset reference.

### HKU-MARS / r3live

- URL: https://github.com/hku-mars/r3live
- Topic: robust real-time RGB-colored lidar-inertial-visual state estimation and mapping.
- License: GPL-2.0 reported by GitHub API.
- Integration: reference for colored mapping and sensor fusion.

### HKUST-Aerial-Robotics / GS-LIVO

- URL: https://github.com/HKUST-Aerial-Robotics/GS-LIVO
- Topic: Gaussian Splatting with LiDAR-Inertial-Visual Odometry.
- License: no SPDX license asserted by GitHub API at collection time.
- Integration: reference only until license terms are verified.

### graphdeco-inria / gaussian-splatting

- URL: https://github.com/graphdeco-inria/gaussian-splatting
- Topic: original reference implementation of 3D Gaussian Splatting for real-time radiance field rendering.
- License: no SPDX license asserted by GitHub API at collection time.
- Integration: reference only; check upstream license before product reuse.

### spla-tam / SplaTAM

- URL: https://github.com/spla-tam/SplaTAM
- Topic: dense RGB-D SLAM with 3D Gaussians.
- License: BSD-3-Clause reported by GitHub API.
- Integration: candidate research backend for RGB-D scanner experiments.

### nerfstudio-project / gsplat

- URL: https://github.com/nerfstudio-project/gsplat
- Topic: CUDA accelerated rasterization for Gaussian Splatting.
- License: Apache-2.0 reported by GitHub API.
- Integration: good candidate as an explicit dependency after environment design.

### isl-org / Open3D

- URL: https://github.com/isl-org/Open3D
- Topic: 3D data processing, point cloud handling and visualization.
- License: no SPDX license asserted by GitHub API at collection time.
- Integration: dependency candidate after license verification.

### KwanWaiPang / Awesome-3DGS-SLAM

- URL: https://github.com/KwanWaiPang/Awesome-3DGS-SLAM
- Topic: paper and repository survey for 3DGS SLAM.
- License: no SPDX license asserted by GitHub API at collection time.
- Integration: reference tracker for future literature updates.

## License Policy

1. Keep third-party projects as links or submodules by default.
2. Never paste third-party source into this repository without recording the license, version and reason.
3. GPL code must not be mixed into closed product code without an explicit product licensing decision.
4. Add dependency notices before any public release.
