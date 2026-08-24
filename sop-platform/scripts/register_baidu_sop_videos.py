#!/usr/bin/env python3
"""把 D 盘已完整下载的视频增量登记到现有 8113 视频目录。"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "config" / "baidu_sop_video_manifest.json"
DEFAULT_DATA_ROOT = Path(r"D:\NingboSOPData\Baidu_20260819_21")
DEFAULT_CATALOG = Path(r"C:\Users\Administrator\AppData\Local\NingboSOPCVAT8113\runtime\cloud_video_catalog.json")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def source_path(item: dict, root: Path) -> tuple[Path, Path]:
    parts = [part for part in str(item["path"]).strip("/").split("/") if part]
    if parts and parts[0] == "宁波SoP项目":
        parts = parts[1:]
    relative = Path(*parts)
    return root / relative, relative


def six_steps(duration: float, source: str) -> list[dict]:
    if "波峰焊" in source:
        labels = ["S01 工装与PCB到位", "S02 插装件上料", "S03 波峰焊作业", "S04 焊点检查", "S05 漏焊补焊复核", "S06 成品放行"]
    elif "DTU" in source:
        labels = ["S01 DTU取料", "S02 接线与定位", "S03 上电准备", "S04 参数测试", "S05 结果确认", "S06 标签与下料"]
    elif "烧录" in source:
        labels = ["S01 主板取料", "S02 烧录线连接", "S03 选择程序", "S04 执行烧录", "S05 校验结果", "S06 断开与下料"]
    else:
        labels = ["S01 零件与工装确认", "S02 大零部件定位", "S03 主板或组件安装", "S04 螺钉顺序紧固", "S05 外观与功能复核", "S06 MES放行"]
    return [
        {
            "id": f"S{index + 1:02d}",
            "label": label,
            "start_s": round(duration * index / len(labels), 3),
            "end_s": round(duration * (index + 1) / len(labels), 3),
            "roi": [0.04, 0.04, 0.96, 0.96],
        }
        for index, label in enumerate(labels)
    ]


def register_once(manifest_path: Path, data_root: Path, catalog_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.is_file() else {"videos": []}
    videos = catalog.get("videos", [])
    existing = {str(item.get("baidu_source")): item for item in videos if item.get("baidu_source")}
    added = 0
    repaired = 0
    for source_item in manifest.get("files", []):
        local, relative = source_path(source_item, data_root)
        expected = int(source_item.get("size") or 0)
        source_key = str(source_item["path"])
        media_url = f"media/{relative.as_posix()}"
        if source_key in existing:
            entry = existing[source_key]
            if any(entry.get(field) != media_url for field in ("video", "source_video", "presentation_video")):
                entry.update({"video": media_url, "source_video": media_url, "presentation_video": media_url})
                entry["cloud_source"] = str(local)
                repaired += 1
            continue
        if not local.is_file() or local.stat().st_size != expected:
            continue
        capture = cv2.VideoCapture(str(local))
        if not capture.isOpened():
            continue
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 30)
        frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        capture.release()
        if frames <= 0 or width <= 0 or height <= 0:
            continue
        duration = frames / fps
        digest = hashlib.sha256(source_key.encode("utf-8")).hexdigest()[:12]
        entry = {
            "id": f"video_baidu_{digest}",
            "display_name": f"网盘原片｜{relative.as_posix()}",
            "video": media_url,
            "source_video": media_url,
            "presentation_video": media_url,
            "duration_s": round(duration, 3),
            "fps": round(fps, 3),
            "frames": frames,
            "resolution": f"{width}x{height}",
            "presentation_resolution": f"{width}x{height}",
            "algorithm": "YOLO工业预标 + CVAT人工复核",
            "steps": six_steps(duration, source_key),
            "cloud_source": str(local),
            "baidu_source": source_key,
            "dataset_id": manifest.get("dataset_id"),
            "cvat_project_name": manifest.get("cvat_project_name"),
            "truth_policy": "AI框仅为候选；螺钉、焊点、漏焊、手部与大零部件必须逐帧人工复核。",
        }
        videos.append(entry)
        existing[source_key] = entry
        added += 1
    catalog.update({"videos": videos, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "baidu_registered": len(existing)})
    atomic_json(catalog_path, catalog)
    return {"added": added, "repaired": repaired, "registered": len(existing), "catalog": str(catalog_path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=15)
    args = parser.parse_args()
    while True:
        result = register_once(args.manifest, args.data_root, args.catalog)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if not args.watch:
            return 0
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
