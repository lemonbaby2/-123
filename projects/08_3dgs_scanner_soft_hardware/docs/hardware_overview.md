# Hardware Overview

## Available Design Inputs

| Board | Available files | Status |
|---|---|---|
| BMS 3S2P | BMS schematic PDF, BMS PCB PDF export, BMS bring-up SOP | Schematic review complete; PCB source package missing |
| SLAM main controller | Main schematic PDF, main PCB PDF export, main-board SOP | Review complete from PDFs; Altium source package missing |

## BMS Board Summary

The BMS board is centered on TI BQ76920 for a 3-series battery stack. The intended 3S2P battery nodes are:

| Node | Meaning | Harness |
|---|---|---|
| B- | Pack negative / group 1 negative | CN1 CELL0 and high-current BAT_MINUS |
| B1 | Group 1 positive / group 2 negative | CN1 CELL1 |
| B2 | Group 2 positive / group 3 negative | CN1 CELL2 |
| B+ | Group 3 positive / pack positive | CN1 CELL3 and high-current VBAT_IN |

Critical correction required before battery connection:

```text
VC5 = B+
VC4 = VC3 = VC2 = B2
VC1 = B1
VC0 = B-
```

## Main Controller Summary

The main controller board appears to host the embedded compute, navigation and sensor interface functions needed by the scanner:

- Jetson power and communication interface.
- STM32 control / housekeeping domain.
- UM982 GNSS and PPS timing.
- MTi-3 IMU interface and analog/digital supply filtering.
- CAN transceiver, UART, I2C and lidar power switching.
- 5 V, 3V3 and protected high-current power paths.

## Known High-Risk Design Items

| ID | Area | Issue | Required action |
|---|---|---|---|
| HW-P0-001 | BMS VC mapping | Present schematic mapping is not safe for 3S BQ76920 operation | Correct schematic and PCB before real battery |
| HW-P0-002 | BMS PCB package | Current BMS PCB PDF appears duplicated from main board PCB export | Provide real BMS PcbDoc/Gerber/layers |
| HW-P0-003 | TPS16630 | R47 current-limit value conflicts with intended 300 W label | Recalculate or split high-power branch |
| HW-P1-001 | MTi-3 supply | 27 ohm analog supply resistor may cause drop/noise issues | Review against Xsens reference and measure ripple |
| HW-P1-002 | Assembly variants | U5/U10 and RF/CAN selector rules need DNP table | Add assembly option table |

## Production Package Required Before Fabrication

- Altium project: `.PrjPcb`, `.SchDoc`, `.PcbDoc`, libraries and project outputs.
- Fabrication: Gerber X2, NC drill, stack-up, impedance notes, solder mask, paste, board outline.
- Assembly: BOM with MPN, CPL/centroid, assembly drawing, polarity drawing, DNP/variant table.
- Verification: DRC/ERC reports, netlist compare, DFM report, high-current copper calculation, thermal review.
