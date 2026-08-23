from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = ROOT / "web" / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a compact inventory for generated prelabel JSONL files")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def inspect_jsonl(path: Path, field: str) -> tuple[int, int]:
    frames = 0
    objects = 0
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            frames += 1
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            values = payload.get(field, [])
            if isinstance(values, list):
                objects += len(values)
    return frames, objects


def main() -> None:
    args = parse_args()
    data_root = args.data_root.resolve()
    output = (args.output or data_root / "prelabel_inventory.json").resolve()
    videos: dict[str, dict[str, object]] = {}
    for path in sorted(data_root.glob("*_frame_annotations.jsonl")):
        video_id = path.name.removesuffix("_frame_annotations.jsonl")
        frames, detections = inspect_jsonl(path, "detections")
        videos.setdefault(video_id, {}).update({
            "detection_frames": frames,
            "detection_count": detections,
            "detection_bytes": path.stat().st_size,
        })
    for suffix in ("_fastener_candidates.jsonl", "_fine_object_candidates.jsonl"):
        for path in sorted(data_root.glob(f"*{suffix}")):
            video_id = path.name.removesuffix(suffix)
            frames, candidates = inspect_jsonl(path, "candidates")
            videos.setdefault(video_id, {}).update({
                "candidate_frames": frames,
                "candidate_count": candidates,
                "candidate_bytes": path.stat().st_size,
            })
    items = []
    for video_id, item in sorted(videos.items()):
        items.append({
            "video_id": video_id,
            "available": bool(item.get("detection_frames") or item.get("candidate_frames")),
            **item,
            "sampled_frames": max(int(item.get("detection_frames") or 0), int(item.get("candidate_frames") or 0)),
            "total_bytes": int(item.get("detection_bytes") or 0) + int(item.get("candidate_bytes") or 0),
        })
    payload = {
        "schema_version": 1,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "videos": items,
        "totals": {
            "videos": len(items),
            "sampled_frames": sum(int(item.get("sampled_frames") or 0) for item in items),
            "detections": sum(int(item.get("detection_count") or 0) for item in items),
            "candidates": sum(int(item.get("candidate_count") or 0) for item in items),
            "bytes": sum(int(item.get("total_bytes") or 0) for item in items),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, output)
    print(json.dumps(payload["totals"], ensure_ascii=False))


if __name__ == "__main__":
    main()
