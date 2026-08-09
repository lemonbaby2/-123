# Firmware Plan

This folder is reserved for embedded firmware used by the BMS and main controller.

## Planned Targets

| Target | Role |
|---|---|
| STM32 main controller | Power sequencing, sensor control, safety interlocks, CAN/UART/I2C bridge |
| BMS host interface | BQ76920 register bring-up, status polling, protection verification |
| Test firmware | Rail enable tests, GPIO loopback, CAN, PPS, UART and watchdog tests |

## Bring-Up Firmware Checklist

- Keep all high-power outputs disabled after reset.
- Log board revision, firmware version and boot reason.
- Add a service mode that can read BQ76920 registers without enabling load output.
- Add current-limit and watchdog failsafe tests.
- Add a manufacturing test command set for fixture automation.
