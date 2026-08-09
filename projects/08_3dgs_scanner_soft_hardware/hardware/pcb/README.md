# PCB Design Exports

This folder contains the currently available PCB and schematic PDF exports.

## Boards

| Board | Folder | Notes |
|---|---|---|
| BMS 3S2P | `pdf_exports/bms/` | BMS schematic is available; BMS PCB PDF must be replaced with the true BMS layout package before release |
| SLAM main controller | `pdf_exports/main_controller/` | Schematic and PCB PDF exports are available |

## Naming

Chinese original filenames were normalized in this project where useful for GitHub readability:

| Original | Project path |
|---|---|
| `主PCB板_PCB1_2026-08-03.pdf` | `hardware/pcb/pdf_exports/main_controller/Main_PCB1_2026-08-03.pdf` |
| `主pcb原理图.pdf` | `hardware/pcb/pdf_exports/main_controller/Main_Schematic.pdf` |

## Release Rule

PDF exports are review artifacts, not fabrication source. The manufacturing release must come from Altium source plus generated Gerber, NC Drill, BOM and CPL files.
