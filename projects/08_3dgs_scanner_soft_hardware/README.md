# 3DGS Scanner Soft-Hardware Project

面向 3D Gaussian Splatting (3DGS) 扫描仪的软硬件工程仓库。当前仓库先把已有 BMS、SLAM 主控 PCB、首板测试 SOP、工程分析报告和外部研究参考统一归档，作为后续 Altium 源文件、嵌入式固件、上位机扫描软件与 3DGS 重建流水线的主工程入口。

> Safety gate: 当前 BMS 资料存在 P0 阻断项。BQ76920 的 3S VC 映射与均衡网络必须修正，并完成模拟电芯注入测试后，才能接入真实 3S2P 电池包。

## Repository Layout

```text
.
├── hardware/
│   ├── altium_sources/          # Altium 源文件占位与交付清单
│   ├── pcb/pdf_exports/         # 当前可用 PCB 与原理图 PDF
│   ├── production/              # 打板、BOM、CPL、Gerber、DFM 资料入口
│   └── test_sop/                # BMS 与 SLAM 主控首板 SOP
├── firmware/                    # BMS/主控板固件规划入口
├── software/                    # 3DGS 扫描、采集、标定、重建软件规划入口
├── docs/
│   ├── bringup/                 # 首板上电、3S2P 接线和检查清单
│   ├── engineering_report/      # 已生成的详细分析报告、测试矩阵和问题清单
│   ├── references/              # HKU/HKUST/INRIA 等公开项目参考索引
│   └── safety/                  # 电池、上电、适配器和实验安全说明
├── third_party/                 # 不直接复制第三方代码，仅放引用和可选 submodule 说明
└── tools/                       # 项目一致性检查脚本
```

## Current Hardware Scope

- BMS: BQ76920 3S2P 电池保护与采样板，资料来自 `BMS_Schematic1_2026-07-27.pdf` 和当前 PCB PDF 导出。
- Main controller: SLAM 主控 PCB，包含 Jetson/STM32、UM982、MTi-3、CAN、PPS、5V/3V3/12V 等电源与接口链路。
- Battery pack target: 3S2P，分为 B-, B1, B2, B+ 四个采样节点，高电流输出经 BMS 保护输出后再接主控板。
- Adapter rule: BMS 不是充电器。3S Li-ion 需要 12.6 V CC/CV 充电器；3S LiFePO4 需要 10.95 V CC/CV 充电器。主控裸板调试可先用 12 V 3-5 A 限流电源，整机电源必须按最终雷达、Jetson、电机和外设功耗重新核算。

## Blocking Issues Before Real Battery / Board Release

1. Fix BQ76920 3S mapping and balancing network:
   - VC5 = B+
   - VC4 = VC3 = VC2 = B2
   - VC1 = B1
   - VC0 = B-
2. Replace the duplicated/misnamed BMS PCB package with real BMS Gerber, layer stack, BOM, CPL and Altium source files.
3. Recalculate TPS16630 R47 current limit. The present 166 kOhm value is not compatible with the intended high-power branch.
4. Define DNP rules for U5/U10, RF antenna bias 0-ohm selector pairs, CAN termination and boot/config straps.
5. Complete simulated-cell bring-up before connecting a real 3S2P pack.

## Bring-Up Order

1. Documentation gate: check schematic/PCB revision, BOM, CPL, Gerber, assembly drawing and known P0 issues.
2. Bare-board inspection: impedance to ground, rail shorts, diode checks, connector polarity and high-current path continuity.
3. BMS simulated cells: inject B-, B1, B2, B+ with isolated current-limited sources, then verify VC pin voltages and I2C status.
4. Main controller low-current power-up: current-limited 12 V input, check 5 V/3V3 rails, reset/boot pins and oscillator.
5. Interface validation: UART, CAN, I2C, PPS, GNSS, IMU, Jetson interface and lidar power path.
6. Integrated scan stack: sensor timestamping, calibration, odometry, mapping, 3DGS reconstruction and export.

## Software Direction

This repository is prepared for a modular 3DGS scanner stack:

- `capture`: camera/lidar/IMU/GNSS acquisition and timestamp alignment.
- `calibration`: camera intrinsics, camera-lidar extrinsics, IMU alignment and PPS timing.
- `odometry`: LIO/LIVO/VIO front end, initially referencing HKU-MARS FAST-LIO/FAST-LIVO style pipelines.
- `reconstruction`: 3DGS or neural SDF reconstruction backend.
- `viewer`: local visualization, Open3D/gsplat/3DGS viewer integration.
- `export`: point cloud, mesh, Gaussian checkpoint, screenshots and engineering logs.

## Reference Projects

See `docs/references/research_repositories.md` and `docs/references/reference_projects.csv`. These are integrated as references only. Third-party source code is not copied into this repository; use submodules or upstream clones only after checking each project's license.

## GitHub Location

Target location:

```text
https://github.com/lemonbaby2/-123/tree/main/projects/08_3dgs_scanner_soft_hardware
```

This project is intended to live as a named project folder inside the `lemonbaby2/-123` portfolio repository:

```text
projects/08_3dgs_scanner_soft_hardware/
```
