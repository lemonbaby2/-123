# Contributing

## Commit Style

Use short imperative commit messages:

```text
add bms bring-up checklist
update 3dgs reference index
fix power budget assumptions
```

## Engineering Change Rules

- Every schematic or PCB change must include a revision note.
- Every fabrication release must include Gerber, NC Drill, BOM, CPL and DFM checks.
- Every battery-related change must be reviewed against the safety gate in `docs/safety/battery_and_power.md`.
- Third-party code must not be copied into the repository without license review.

## Branches

- `main`: stable project archive and reviewed documentation.
- `feature/*`: software, firmware or hardware documentation work.
- `release/hardware-*`: tagged production output candidates.
