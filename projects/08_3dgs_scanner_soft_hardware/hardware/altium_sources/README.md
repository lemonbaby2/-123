# Altium Source Package Placeholder

当前资料夹没有发现 `.PrjPcb`, `.SchDoc`, `.PcbDoc`, `.OutJob`, `.BomDoc`, Gerber, NC Drill, BOM 或 CPL 源文件。

请后续把 Altium 工程按以下结构补齐：

```text
hardware/altium_sources/
├── bms_3s2p/
│   ├── project/
│   ├── fabrication/
│   ├── assembly/
│   └── exports/
└── slam_main_controller/
    ├── project/
    ├── fabrication/
    ├── assembly/
    └── exports/
```

## Required Files

| Category | Required files |
|---|---|
| Project source | `.PrjPcb`, `.SchDoc`, `.PcbDoc`, project libraries |
| Fabrication | Gerber X2, NC Drill, stack-up, impedance table, board outline |
| Assembly | BOM with manufacturer part numbers, CPL/centroid, assembly drawing |
| Review | ERC/DRC report, netlist compare, DFM report, high-current and thermal review |
| Release | Revision tag, date, author, ECN/change log |

## Naming Convention

```text
<board>_<document>_<rev>_<yyyy-mm-dd>.<ext>
```

Example:

```text
bms_3s2p_schematic_revA_2026-08-10.SchDoc
slam_main_controller_pcb_revA_2026-08-10.PcbDoc
```
