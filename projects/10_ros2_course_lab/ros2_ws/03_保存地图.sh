#!/usr/bin/env bash
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export WS
bash "$WS/src/week12_odometry/scripts/save_map.sh"
