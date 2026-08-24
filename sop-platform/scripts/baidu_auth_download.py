#!/usr/bin/env python3
"""使用本机已登录的百度网盘桌面客户端会话下载项目视频。

脚本不会打印或保存登录 Cookie；下载链接仅在进程内短暂使用。
下载采用 ``.part`` 临时文件并支持 HTTP Range 断点续传。
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path, PurePosixPath
from typing import Any

import requests


DEFAULT_COOKIE_DB = Path(
    os.environ.get(
        "BAIDU_NETDISK_COOKIE_DB",
        r"C:\Users\Administrator\AppData\Roaming\baidunetdisk\Network\Cookies",
    )
)
DEFAULT_INVENTORY = Path(
    os.environ.get(
        "BAIDU_SOP_INVENTORY",
        r"C:\Users\Administrator\AppData\Local\Temp\baidu_full_inventory_20260824.json",
    )
)
DEFAULT_OUTPUT = Path(r"D:\NingboSOPData\Baidu_20260819_21")
API_ROOT = "https://pan.baidu.com"
USER_AGENT = "netdisk;8.5.5.103;PC;PC-Windows;10.0.26100;WindowsBaiduYunGuanJia"


def desktop_cookies(cookie_db: Path) -> requests.cookies.RequestsCookieJar:
    if not cookie_db.is_file():
        raise FileNotFoundError(f"未找到百度网盘客户端 Cookie 数据库：{cookie_db}")
    conn = sqlite3.connect(f"file:{cookie_db.as_posix()}?mode=ro", uri=True, timeout=10)
    try:
        rows = conn.execute(
            "SELECT host_key, path, name, value FROM cookies "
            "WHERE value <> '' AND (host_key = '.baidu.com' OR host_key = '.pan.baidu.com' "
            "OR host_key = 'pan.baidu.com' OR host_key = '.pcs.baidu.com' "
            "OR host_key = '.pcsdata.baidu.com')"
        ).fetchall()
    finally:
        conn.close()
    jar = requests.cookies.RequestsCookieJar()
    for domain, path, name, value in rows:
        jar.set(name, value, domain=domain, path=path or "/")
    names = {name for _, _, name, _ in rows}
    if "BDUSS" not in names:
        raise RuntimeError("百度网盘客户端会话中缺少 BDUSS，请先在官方客户端登录")
    return jar


def session_from_desktop(cookie_db: Path) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Referer": "https://pan.baidu.com/disk/main"})
    session.cookies.update(desktop_cookies(cookie_db))
    return session


def get_download_link(session: requests.Session, fs_id: int) -> str:
    response = session.get(
        f"{API_ROOT}/api/filemetas",
        params={"dlink": 1, "fsids": json.dumps([int(fs_id)]), "clienttype": 8, "web": 0},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if int(payload.get("errno", -1)) != 0 or not payload.get("info"):
        raise RuntimeError(f"获取下载地址失败，errno={payload.get('errno')}")
    dlink = str(payload["info"][0].get("dlink") or "")
    if not dlink.startswith("http"):
        raise RuntimeError("百度网盘未返回有效下载地址")
    return dlink


def load_video_inventory(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    videos = [item for item in payload.get("files", []) if str(item.get("path", "")).lower().endswith(".mp4")]
    return sorted(videos, key=lambda item: (int(item.get("size", 0)), str(item.get("path", ""))))


def local_path_for(item: dict[str, Any], output_root: Path) -> Path:
    source = PurePosixPath(str(item["path"]))
    parts = list(source.parts)
    if parts and parts[0] == "/":
        parts = parts[1:]
    if parts and parts[0] == "宁波SoP项目":
        parts = parts[1:]
    return output_root.joinpath(*parts)


def write_status(status_path: Path, payload: dict[str, Any]) -> None:
    status_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = status_path.with_suffix(status_path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(status_path)


def download_one(
    session: requests.Session,
    item: dict[str, Any],
    output_root: Path,
    status_path: Path,
) -> dict[str, Any]:
    destination = local_path_for(item, output_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    expected_size = int(item.get("size", 0))
    if destination.is_file() and destination.stat().st_size == expected_size:
        return {"source_path": item["path"], "local_path": str(destination), "status": "completed", "bytes": expected_size}

    partial = destination.with_suffix(destination.suffix + ".part")
    offset = partial.stat().st_size if partial.is_file() else 0
    started = time.time()
    downloaded = offset
    mode = "ab" if offset else "wb"
    chunk_bytes = 4 * 1024 * 1024
    link = get_download_link(session, int(item["fs_id"]))
    with partial.open(mode) as stream:
        while downloaded < expected_size:
            end = min(expected_size - 1, downloaded + chunk_bytes - 1)
            response = None
            for attempt in range(6):
                try:
                    response = session.get(
                        link,
                        headers={"Range": f"bytes={downloaded}-{end}"},
                        timeout=(30, 120),
                        allow_redirects=True,
                    )
                except requests.RequestException:
                    response = None
                if response is not None and response.status_code == 206:
                    break
                retry_seconds = min(60, 5 * (2 ** attempt))
                write_status(
                    status_path,
                    {
                        "status": "waiting_retry",
                        "source_path": item["path"],
                        "local_path": str(destination),
                        "downloaded_bytes": downloaded,
                        "expected_bytes": expected_size,
                        "retry_seconds": retry_seconds,
                        "message": "百度分块地址正在刷新重试",
                        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    },
                )
                if response is not None:
                    response.close()
                time.sleep(retry_seconds)
                link = get_download_link(session, int(item["fs_id"]))
            if response is None or response.status_code != 206:
                raise RuntimeError(f"百度分块下载失败，HTTP {getattr(response, 'status_code', 'N/A')}")
            chunk = response.content
            response.close()
            required = end - downloaded + 1
            if len(chunk) != required:
                raise RuntimeError(f"百度分块长度不一致：{len(chunk)} != {required}")
            stream.write(chunk)
            downloaded += len(chunk)
            if downloaded % (32 * 1024 * 1024) < len(chunk) or downloaded == expected_size:
                write_status(
                    status_path,
                    {
                        "status": "downloading",
                        "source_path": item["path"],
                        "local_path": str(destination),
                        "downloaded_bytes": downloaded,
                        "expected_bytes": expected_size,
                        "progress": round(downloaded / expected_size * 100, 2) if expected_size else 0,
                        "speed_mib_s": round((downloaded - offset) / max(time.time() - started, 0.1) / 1024 / 1024, 2),
                        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    },
                )
    if expected_size and partial.stat().st_size != expected_size:
        raise RuntimeError(f"文件大小校验失败：{partial.stat().st_size} != {expected_size}")
    partial.replace(destination)
    return {"source_path": item["path"], "local_path": str(destination), "status": "completed", "bytes": destination.stat().st_size}


def main() -> int:
    parser = argparse.ArgumentParser(description="百度网盘宁波 SOP 视频断点下载器")
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cookie-db", type=Path, default=DEFAULT_COOKIE_DB)
    parser.add_argument("--status", type=Path, default=DEFAULT_OUTPUT / "download_status.json")
    parser.add_argument("--contains", action="append", default=[], help="仅下载源路径包含指定文字的视频，可重复")
    parser.add_argument("--limit", type=int, default=0, help="最多下载多少个视频；0 表示全部")
    parser.add_argument("--probe", action="store_true", help="只验证登录会话和下载链接，不下载")
    args = parser.parse_args()

    videos = load_video_inventory(args.inventory)
    if args.contains:
        videos = [item for item in videos if any(text in str(item["path"]) for text in args.contains)]
    if args.limit > 0:
        videos = videos[: args.limit]
    if not videos:
        raise RuntimeError("清单中没有符合条件的 MP4 视频")

    session = session_from_desktop(args.cookie_db)
    if args.probe:
        get_download_link(session, int(videos[0]["fs_id"]))
        print(json.dumps({"ok": True, "message": "本机网盘登录会话与下载接口有效", "video_count": len(videos)}, ensure_ascii=False))
        return 0

    results: list[dict[str, Any]] = []
    for index, item in enumerate(videos, start=1):
        write_status(
            args.status,
            {
                "status": "starting",
                "current_index": index,
                "total": len(videos),
                "source_path": item["path"],
                "completed": results,
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
        destination = local_path_for(item, args.output)
        was_complete = destination.is_file() and destination.stat().st_size == int(item.get("size") or 0)
        result = download_one(session, item, args.output, args.status)
        results.append(result)
        if not was_complete:
            time.sleep(8)
    write_status(
        args.status,
        {"status": "completed", "total": len(videos), "completed": results, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")},
    )
    print(json.dumps({"ok": True, "completed": len(results), "status_file": str(args.status)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
