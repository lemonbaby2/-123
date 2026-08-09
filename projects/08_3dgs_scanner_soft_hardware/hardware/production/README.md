# Production and Bring-Up Gate

Do not release boards to fabrication until the following gate is closed.

## Fabrication Gate

| Check | Requirement | Status |
|---|---|---|
| Schematic ERC | No unreviewed errors; BQ76920 VC mapping corrected | Open |
| PCB DRC | Clearance, width, solder mask, hole and courtyard checks passed | Open |
| Netlist compare | Schematic-to-PCB netlist match | Open |
| BMS high current path | MOS, shunt, connector, copper width and thermal path verified | Open |
| Sense routing | B-, B1, B2, B+ Kelvin routing and RC filters verified | Open |
| Assembly variants | DNP table for U5/U10, RF selectors, CAN termination and boot straps | Open |
| Production outputs | Gerber, drill, BOM, CPL, stack-up, assembly drawing | Open |

## Manual Soldering Notes

- Solder only the minimum bring-up population first: power tree, protection, programming/debug and measurement points.
- Leave high-current MOS/load branch unpopulated or isolated until low-current rails pass.
- Use hot air only where needed; avoid overheating IMU/GNSS/RF modules.
- Clean flux around BMS cell sense inputs, IMU analog supply and RF antenna path.
- Inspect fine-pitch ICs, QFN pads, polarity parts, connector pin 1 and 0-ohm option links under microscope.

## First Power-Up Rule

Use a current-limited bench supply and isolated simulated cell sources first. Never use the real 3S2P pack as the first debug source.
