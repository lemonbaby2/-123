from __future__ import annotations

import argparse
from collections.abc import Callable

from . import bms, gaussian_viz, geoscan, ginger, quadruped, vision
from .common import pretty


DEMOS: dict[str, Callable[[], dict[str, object]]] = {
    "quadruped": quadruped.demo,
    "ginger": ginger.demo,
    "geoscan": geoscan.demo,
    "vision": vision.demo,
    "gaussian": gaussian_viz.demo,
    "bms": bms.demo,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run clean-room robotics portfolio demos")
    parser.add_argument("demo", choices=["all", *DEMOS], nargs="?", default="all")
    args = parser.parse_args()
    selected = DEMOS if args.demo == "all" else {args.demo: DEMOS[args.demo]}
    print(pretty({name: run() for name, run in selected.items()}))
