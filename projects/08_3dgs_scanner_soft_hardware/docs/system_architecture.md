# System Architecture

## Goal

Build a portable scanner that captures synchronized camera/lidar/IMU/GNSS data, estimates a stable trajectory, and reconstructs scenes with 3D Gaussian Splatting or geometry-constrained variants.

## High-Level Blocks

```text
3S2P battery / adapter
        |
        v
BMS and protected power output
        |
        v
SLAM main controller PCB
        |-- Jetson / edge compute
        |-- STM32 housekeeping controller
        |-- lidar power and communication
        |-- camera interface
        |-- IMU / GNSS / PPS timing
        |-- CAN / UART / I2C debug and control
        |
        v
Capture + odometry + 3DGS reconstruction software
        |
        v
Point cloud / trajectory / Gaussian model / viewer export
```

## Data Flow

1. Sensors produce timestamped image, lidar, IMU and GNSS/PPS streams.
2. Capture layer writes raw synchronized data and metadata.
3. Odometry layer estimates trajectory using LIO/LIVO/VIO.
4. Reconstruction layer converts calibrated frames and trajectory into 3DGS/SDF assets.
5. Viewer/export layer provides QA artifacts and deliverables.

## Engineering Interfaces

| Interface | Owner | Expected outputs |
|---|---|---|
| Power | Hardware | Rail status, current, fault, temperature |
| BMS | Hardware/Firmware | Cell voltage, pack voltage, protection flags |
| Sensor sync | Hardware/Firmware/Software | PPS, trigger, timestamp logs |
| Odometry | Software | Pose trajectory, residuals, diagnostics |
| Reconstruction | Software | Gaussian checkpoint, PLY/mesh/point cloud |

## Near-Term Integration Strategy

- Keep hardware bring-up independent from 3DGS software until power and timing are stable.
- Use public datasets first to validate 3DGS reconstruction.
- Use bench-captured static scenes before mobile scanning.
- Add live preview only after offline reconstruction is repeatable.
