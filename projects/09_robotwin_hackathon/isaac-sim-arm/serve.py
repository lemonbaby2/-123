#!/usr/bin/env python3
"""
serve.py — Isaac Lab 机械臂分拣复现站点的静态服务 + 轻量 API

为什么不用 `python -m http.server`：
  1) 标准库 SimpleHTTPRequestHandler 不支持 HTTP Range（206），
     浏览器拖动视频进度条、或 Safari 播放时会失败；
  2) 缺 MIME 映射（.mp4 / .json 在部分环境会返回 application/octet-stream）；
  3) 没有结构化运行数据接口。

本服务提供：
  GET /                     → index.html
  GET /api/info             → 运行摘要 JSON（分拣结果 / 时间轴 / 视频规格 / 主机地址）
  GET /api/highlights       → data/highlights.json（8 次成功放置的时间轴）
  GET /api/curves           → data/curves_franka_lift.json（RL 训练曲线）
  GET /<静态文件>            → 带 Range / ETag / Cache-Control 的静态响应

用法：
  python serve.py                      # 0.0.0.0:18355（局域网可访问）
  python serve.py --port 9000
  python serve.py --host 127.0.0.1     # 仅本机
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))

MIME = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
    ".log": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".zip": "application/zip",
    ".py": "text/plain; charset=utf-8",
    ".sh": "text/plain; charset=utf-8",
    ".kit": "text/plain; charset=utf-8",
}


def lan_ips() -> list[str]:
    """返回本机所有非回环 IPv4 地址。"""
    ips: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    # 通过「连一个外部地址但不发数据」拿到默认出网网卡地址
    for probe in ("8.8.8.8", "223.5.5.5"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.4)
            s.connect((probe, 53))
            ips.add(s.getsockname()[0])
            s.close()
        except OSError:
            pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


def build_info(port: int) -> dict:
    info: dict = {"service": "isaac-arm-sorter", "root": ROOT, "port": port}

    for name, rel in (("highlights", "data/highlights.json"),
                      ("summary", "logs/rgb_cube_sorter_summary.json")):
        p = os.path.join(ROOT, rel)
        if os.path.isfile(p):
            try:
                info[name] = json.load(open(p, encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                info[name] = None

    vids = {}
    vdir = os.path.join(ROOT, "videos")
    if os.path.isdir(vdir):
        for f in sorted(os.listdir(vdir)):
            if f.endswith(".mp4"):
                vids[f] = os.path.getsize(os.path.join(vdir, f))
    info["videos"] = vids

    pdir = os.path.join(ROOT, "photos")
    info["photos"] = (len([f for f in os.listdir(pdir) if f.lower().endswith(".jpg")])
                      if os.path.isdir(pdir) else 0)

    info["lan_urls"] = [f"http://{ip}:{port}/index.html" for ip in lan_ips()]
    return info


class Handler(SimpleHTTPRequestHandler):
    server_version = "IsaacArmSorter/1.0"
    protocol_version = "HTTP/1.1"

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def guess_type(self, path):  # noqa: D102
        ext = os.path.splitext(str(path))[1].lower()
        return MIME.get(ext) or super().guess_type(path)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    # ------------------------------------------------------------------
    #  HTTP Range（206 Partial Content）
    #  标准库 SimpleHTTPRequestHandler 不支持 Range，浏览器拖视频进度条会失败。
    # ------------------------------------------------------------------
    def _parse_range(self, size: int):
        raw = self.headers.get("Range")
        if not raw or not raw.startswith("bytes="):
            return None
        spec = raw[len("bytes="):].strip()
        if "," in spec:                       # 多段不支持，退化为整文件
            return None
        try:
            start_s, _, end_s = spec.partition("-")
            if start_s == "":                 # bytes=-N 末尾 N 字节
                n = int(end_s)
                if n <= 0:
                    return None
                return max(0, size - n), size - 1
            start = int(start_s)
            end = int(end_s) if end_s else size - 1
            if start >= size or start > end:
                return "unsatisfiable"
            return start, min(end, size - 1)
        except (ValueError, TypeError):
            return None

    def _send_range(self, fs_path: str) -> bool:
        """若请求带 Range 且文件存在，则直接回 206/416 并返回 True。"""
        if not self.headers.get("Range"):
            return False
        if not os.path.isfile(fs_path):
            return False

        size = os.path.getsize(fs_path)
        rng = self._parse_range(size)
        if rng is None:
            return False
        if rng == "unsatisfiable":
            self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return True

        start, end = rng
        length = end - start + 1
        self.send_response(HTTPStatus.PARTIAL_CONTENT)
        self.send_header("Content-Type", self.guess_type(fs_path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()

        if self.command == "HEAD":
            return True
        try:
            with open(fs_path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(256 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
        return True

    def do_GET(self) -> None:  # noqa: N802
        route = unquote(urlparse(self.path).path)

        if route == "/api/info":
            return self._send_json(build_info(self.server.server_address[1]))
        if route in ("/api/highlights", "/api/curves"):
            rel = "data/highlights.json" if route.endswith("highlights") else "data/curves_franka_lift.json"
            p = os.path.join(ROOT, rel)
            if not os.path.isfile(p):
                return self._send_json({"error": "not found", "file": rel}, 404)
            return self._send_json(json.load(open(p, encoding="utf-8")))

        # 目录 → index.html
        fs_path = self.translate_path(self.path)
        if os.path.isdir(fs_path):
            idx = os.path.join(fs_path, "index.html")
            if os.path.isfile(idx) and not route.endswith("/"):
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                self.send_header("Location", route + "/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if os.path.isfile(idx):
                self.path = route.rstrip("/") + "/index.html"

        # Range 优先（视频拖进度条 / Safari 播放依赖 206）
        if self._send_range(self.translate_path(self.path)):
            return

        return super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802
        return self.do_GET()

    def copyfile(self, source, outputfile) -> None:  # 大文件流式拷贝
        try:
            while True:
                buf = source.read(1024 * 256)
                if not buf:
                    break
                outputfile.write(buf)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0", help="监听地址（0.0.0.0 = 局域网可访问）")
    ap.add_argument("--port", type=int, default=18355)
    args = ap.parse_args()

    handler = partial(Handler, directory=ROOT)
    httpd = ThreadingHTTPServer((args.host, args.port), handler)
    httpd.daemon_threads = True

    print(f"根目录 : {ROOT}")
    print(f"监听   : {args.host}:{args.port}")
    print(f"本机   : http://127.0.0.1:{args.port}/index.html")
    for ip in lan_ips():
        print(f"局域网 : http://{ip}:{args.port}/index.html")
    print("按 Ctrl+C 停止")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
