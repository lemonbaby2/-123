#!/usr/bin/env python3
"""把网盘下载和 CVAT 导入状态发布为 SOP 网页可读的非敏感 JSON。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = PROJECT_ROOT / "server.py"
DEFAULT_OUTPUT = PROJECT_ROOT / "web" / "data" / "baidu_project_status.json"
DEFAULT_CSV = PROJECT_ROOT / "analysis" / "百度网盘_SOP_CVAT视频映射_20260824.csv"


def load_status() -> dict:
    spec = importlib.util.spec_from_file_location("ningbo_sop_status_module", SERVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 SOP 状态模块")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.baidu_project_status()


def write_status(output: Path, csv_output: Path) -> None:
    payload = load_status()
    payload["published_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(output)
    cvat_items = (payload.get("cvat_import") or {}).get("items") or {}
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    csv_temporary = csv_output.with_suffix(csv_output.suffix + ".tmp")
    with csv_temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["源网盘路径", "批次", "工位", "本地状态", "已下载字节", "应有字节", "SOP视频ID", "CVAT项目ID", "CVAT任务ID", "CVAT任务状态"])
        writer.writeheader()
        for item in payload.get("files", []):
            source = str(item.get("source_path") or "")
            cvat = cvat_items.get(source) or {}
            writer.writerow({
                "源网盘路径": source,
                "批次": item.get("batch"),
                "工位": item.get("station"),
                "本地状态": item.get("status"),
                "已下载字节": item.get("downloaded_bytes"),
                "应有字节": item.get("expected_bytes"),
                "SOP视频ID": f"video_baidu_{hashlib.sha256(source.encode('utf-8')).hexdigest()[:12]}",
                "CVAT项目ID": (payload.get("cvat_import") or {}).get("project_id"),
                "CVAT任务ID": cvat.get("task_id"),
                "CVAT任务状态": cvat.get("status") or "等待原片",
            })
    csv_temporary.replace(csv_output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=5)
    args = parser.parse_args()
    while True:
        write_status(args.output, args.csv_output)
        if not args.watch:
            return 0
        time.sleep(max(2, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
