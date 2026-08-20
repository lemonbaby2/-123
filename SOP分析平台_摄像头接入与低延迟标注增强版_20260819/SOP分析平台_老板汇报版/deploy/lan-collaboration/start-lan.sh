#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export SOP_HOST="${SOP_HOST:-0.0.0.0}"
export SOP_PORT="${SOP_PORT:-8097}"
export SOP_COLLAB_DB="${SOP_COLLAB_DB:-$ROOT/runtime/collaboration.sqlite3}"
export SOP_DEFAULT_PASSWORD="${SOP_DEFAULT_PASSWORD:?Set SOP_DEFAULT_PASSWORD before first start}"
export CVAT_URL="${CVAT_URL:-http://$(hostname -I | awk '{print $1}'):8081}"

cd "$ROOT"
exec python3 server.py
