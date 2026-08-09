# Roadmap

## Phase 0 - Archive and Review

- Organize current PDF, SOP and analysis artifacts.
- Document missing Altium/Gerber/BOM/CPL files.
- Mark BMS VC mapping and high-current power risks as blocking.

## Phase 1 - Hardware Release Candidate

- Correct BMS schematic and PCB source.
- Recalculate high-current protection and adapter sizing.
- Produce complete fabrication and assembly packages.
- Add assembly variant table.
- Run DRC/ERC/DFM and netlist comparison.

## Phase 2 - Board Bring-Up

- Bring up BMS with simulated cells.
- Bring up main controller rails and debug interfaces.
- Validate GNSS, IMU, PPS, CAN, UART and lidar power control.
- Close issue register before real pack and high-power loads.

## Phase 3 - Capture Software

- Define sensor list and timestamp model.
- Implement scan session folder format.
- Add metadata, calibration and log writers.
- Validate on public datasets before hardware capture.

## Phase 4 - 3DGS Reconstruction

- Add offline reconstruction adapter.
- Compare gaussian-splatting, gsplat, SplaTAM and GS-SDF style backends.
- Add quality metrics: alignment error, coverage, runtime, memory and export size.

## Phase 5 - Integrated Scanner Demo

- Capture a controlled scene.
- Run odometry, reconstruction and viewer export.
- Package repeatable demo dataset and release checklist.
