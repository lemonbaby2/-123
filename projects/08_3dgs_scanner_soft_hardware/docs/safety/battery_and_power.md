# Battery and Power Safety

## 3S2P Pack Wiring

The 3S2P pack should be treated as three parallel groups connected in series:

| Pack node | Description | BMS sense |
|---|---|---|
| B- | Group 1 negative / pack negative | CELL0 / VC0 |
| B1 | Group 1 positive and group 2 negative | CELL1 / VC1 |
| B2 | Group 2 positive and group 3 negative | CELL2 / VC2/VC3/VC4 junction for 3S BQ76920 mapping |
| B+ | Group 3 positive / pack positive | CELL3 / VC5 |

Connect sense wires from low to high: B-, B1, B2, B+. Disconnect in reverse order.

## Charger / Adapter

- 3S Li-ion charger: 12.6 V CC/CV.
- 3S LiFePO4 charger: 10.95 V CC/CV.
- Charge current must be the minimum allowed by cells, BMS MOS/shunt, connector, cable and thermal design.
- A normal constant-voltage adapter is not a lithium charger.
- Main controller bench bring-up can start at 12 V with 3-5 A current limit, but this is not the full-system adapter rating.

## Absolute No-Go Conditions

- BQ76920 VC mapping is not corrected.
- Real BMS PCB source/Gerber is missing.
- TPS16630 high-power branch current limit is not recalculated.
- Cell sense sequence is uncertain.
- Pack polarity was not checked twice with a DMM.
