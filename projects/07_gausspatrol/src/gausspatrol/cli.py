"""Command-line entry point for GaussPatrol."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .mission import run_benchmark
from .reporting import write_artifacts


def default_scenario() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "default_scenario.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic GaussPatrol patrol benchmark")
    parser.add_argument("--scenario", type=Path, default=default_scenario())
    parser.add_argument("--output", type=Path, help="write SVG/PLY/JSON/Markdown artifacts")
    parser.add_argument("--json-only", action="store_true", help="emit compact JSON and do not write artifacts")
    args = parser.parse_args()
    benchmark = run_benchmark(args.scenario)
    if args.output and not args.json_only:
        written = write_artifacts(benchmark, args.scenario, args.output)
        print(json.dumps({"artifacts": [str(path) for path in written], "benchmark": benchmark.summary()}, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(benchmark.summary(), ensure_ascii=False, indent=2, sort_keys=True))
