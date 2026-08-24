#!/usr/bin/env python3
"""把已下载的宁波 SOP 视频增量导入本地 CVAT Project。

小视频直接上传；大文件生成 720p/15FPS H.264 标注代理后上传。
脚本可长期监视下载目录，所有状态写入 D 盘 JSON，不在日志中输出令牌。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "config" / "baidu_sop_video_manifest.json"
DEFAULT_DATA_ROOT = Path(r"D:\NingboSOPData\Baidu_20260819_21")
DEFAULT_TOKEN_FILE = Path(r"C:\Users\Administrator\AppData\Local\NingboSOPCVAT8113\runtime\cvat_token")
DEFAULT_FFMPEG = Path(r"D:\Anaconda\Library\bin\ffmpeg.exe")


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def source_local_path(source_path: str, data_root: Path) -> Path:
    parts = [part for part in source_path.strip("/").split("/") if part]
    if parts and parts[0] == "宁波SoP项目":
        parts = parts[1:]
    return data_root.joinpath(*parts)


def api_headers(token_file: Path) -> dict[str, str]:
    token = os.getenv("CVAT_TOKEN", "").strip()
    if not token and token_file.is_file():
        token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        raise RuntimeError("未找到 CVAT API Token")
    return {"Authorization": f"Token {token}", "Accept": "application/vnd.cvat+json"}


def paged_results(session: requests.Session, url: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    response = session.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    return payload.get("results", []) if isinstance(payload, dict) else payload


def ensure_project(
    session: requests.Session,
    api_root: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    name = str(manifest["cvat_project_name"])
    projects = paged_results(session, f"{api_root}/api/projects", {"search": name, "page_size": 100})
    project = next((item for item in projects if str(item.get("name")) == name), None)
    if project:
        return project
    colors = ["#0a936f", "#1769d2", "#dc8b12", "#d44747", "#8e44ad", "#2c3e50", "#16a085", "#7f8c8d", "#c0392b"]
    body = {
        "name": name,
        "labels": [
            {"name": label, "color": colors[index % len(colors)], "type": "any"}
            for index, label in enumerate(manifest.get("labels", []))
        ],
    }
    response = session.post(f"{api_root}/api/projects", json=body, timeout=30)
    response.raise_for_status()
    return response.json()


def annotation_proxy(source: Path, data_root: Path, ffmpeg: Path) -> Path:
    relative = source.relative_to(data_root)
    proxy = data_root / "cvat_proxies" / relative.with_suffix(".proxy.mp4")
    if proxy.is_file() and proxy.stat().st_size > 1_000_000:
        return proxy
    if not ffmpeg.is_file():
        raise RuntimeError(f"未找到 ffmpeg：{ffmpeg}")
    proxy.parent.mkdir(parents=True, exist_ok=True)
    partial = proxy.with_suffix(".proxy.part.mp4")
    command = [
        str(ffmpeg), "-hide_banner", "-loglevel", "warning", "-y", "-i", str(source),
        "-vf", "scale='min(1280,iw)':-2,fps=15", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "24", "-an", "-movflags", "+faststart", str(partial),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=24 * 3600, check=False)
    if completed.returncode or not partial.is_file() or partial.stat().st_size < 1_000_000:
        partial.unlink(missing_ok=True)
        raise RuntimeError((completed.stderr or completed.stdout or "标注代理生成失败")[-1200:])
    partial.replace(proxy)
    return proxy


def task_name(item: dict[str, Any]) -> str:
    source = str(item["path"])
    parts = [part for part in source.strip("/").split("/") if part]
    tail = " / ".join(parts[-3:])
    return f"网盘原片｜{tail}"


def ensure_task_and_upload(
    session: requests.Session,
    api_root: str,
    project_id: int,
    name: str,
    video: Path,
) -> dict[str, Any]:
    tasks = paged_results(session, f"{api_root}/api/tasks", {"project_id": project_id, "search": name, "page_size": 100})
    task = next((item for item in tasks if str(item.get("name")) == name), None)
    if task is None:
        response = session.post(f"{api_root}/api/tasks", json={"name": name, "project_id": project_id}, timeout=30)
        response.raise_for_status()
        task = response.json()
    task_id = int(task["id"])
    detail = session.get(f"{api_root}/api/tasks/{task_id}", timeout=30)
    detail.raise_for_status()
    current = detail.json()
    if int(current.get("size") or 0) <= 0:
        with video.open("rb") as handle:
            response = session.post(
                f"{api_root}/api/tasks/{task_id}/data",
                data={"image_quality": "85", "use_zip_chunks": "true", "use_cache": "true"},
                files={"client_files[0]": (video.name, handle, "video/mp4")},
                timeout=(30, 6 * 3600),
            )
        response.raise_for_status()
        state = "已提交CVAT处理"
    else:
        state = "CVAT任务已存在"
    return {"task_id": task_id, "task_name": name, "status": state, "video": str(video)}


def run_once(args: argparse.Namespace) -> dict[str, Any]:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    session = requests.Session()
    session.headers.update(api_headers(args.token_file))
    project = ensure_project(session, args.api_root.rstrip("/"), manifest)
    state = json.loads(args.state.read_text(encoding="utf-8")) if args.state.is_file() else {"items": {}}
    state.update({"project_id": int(project["id"]), "project_name": project["name"], "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")})
    items = state.setdefault("items", {})
    ready_count = 0
    for item in manifest.get("files", []):
        source = source_local_path(str(item["path"]), args.data_root)
        expected = int(item.get("size") or 0)
        if not source.is_file() or source.stat().st_size != expected:
            continue
        ready_count += 1
        key = str(item["path"])
        if str((items.get(key) or {}).get("status")) in {"已提交CVAT处理", "CVAT任务已存在"}:
            continue
        try:
            items[key] = {"status": "准备导入", "source": str(source), "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
            atomic_json(args.state, state)
            upload = source
            if source.stat().st_size > args.direct_limit_gb * 1024 ** 3:
                items[key]["status"] = "生成720p标注代理"
                atomic_json(args.state, state)
                upload = annotation_proxy(source, args.data_root, args.ffmpeg)
            result = ensure_task_and_upload(session, args.api_root.rstrip("/"), int(project["id"]), task_name(item), upload)
            items[key] = {**result, "source": str(source), "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        except Exception as exc:
            items[key] = {"status": "失败待重试", "source": str(source), "error": str(exc), "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        atomic_json(args.state, state)
    state["ready_originals"] = ready_count
    state["total_originals"] = len(manifest.get("files", []))
    state["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    atomic_json(args.state, state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description="百度网盘视频增量导入 CVAT")
    parser.add_argument("--api-root", default="http://10.70.102.210:8081")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE)
    parser.add_argument("--state", type=Path, default=DEFAULT_DATA_ROOT / "cvat_import_state.json")
    parser.add_argument("--ffmpeg", type=Path, default=DEFAULT_FFMPEG)
    parser.add_argument("--direct-limit-gb", type=float, default=1.5)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    while True:
        state = run_once(args)
        completed = sum(1 for item in state.get("items", {}).values() if item.get("status") in {"已提交CVAT处理", "CVAT任务已存在"})
        print(json.dumps({"ok": True, "project_id": state.get("project_id"), "imported": completed, "ready": state.get("ready_originals")}, ensure_ascii=False), flush=True)
        if not args.watch or completed >= int(state.get("total_originals") or 0):
            return 0
        time.sleep(max(15, args.interval))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
