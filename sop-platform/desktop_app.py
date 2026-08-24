from __future__ import annotations

import ctypes
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import webview

from server import DEFAULT_APP_DATA, ROOT, RUNTIME_ROOT, create_server


APP_TITLE = "宁波视觉SOP与CVAT闭环平台 2026.08.24"
FIRST_RUN_MARKER = RUNTIME_ROOT / ".credentials_shown"
CONDA_PYTHON = Path(os.getenv("SOP_CONDA_PYTHON", r"D:\Anaconda\envs\dl\python.exe"))


def available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_until_ready(url: str, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=1.0) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.15)
    raise RuntimeError("SOP 本地服务启动超时")


def show_first_run_credentials() -> None:
    credential_path = RUNTIME_ROOT / "initial_credentials.txt"
    if FIRST_RUN_MARKER.exists() or not credential_path.exists() or os.name != "nt":
        return
    message = credential_path.read_text(encoding="utf-8")
    message += "\n账号文件位置：\n" + str(credential_path)
    message += "\n\n请拍照或安全保存，登录后立即修改密码。"
    ctypes.windll.user32.MessageBoxW(None, message, "首次登录账号", 0x40 | 0x1000)
    FIRST_RUN_MARKER.write_text(time.strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")


def main() -> None:
    port = available_port()
    base_url = f"http://127.0.0.1:{port}"
    external_process: subprocess.Popen | None = None
    embedded_server = None
    use_conda = bool(getattr(sys, "frozen", False)) and CONDA_PYTHON.is_file() and os.getenv("SOP_FORCE_EMBEDDED", "0") != "1"
    if use_conda:
        child_env = os.environ.copy()
        child_env.update(
            {
                "SOP_HOST": "127.0.0.1",
                "SOP_PORT": str(port),
                "SOP_RUNTIME_DIR": str(DEFAULT_APP_DATA / "runtime"),
                "SOP_CONFIG_DIR": str(DEFAULT_APP_DATA / "config"),
                "SOP_DESKTOP_DIR": str(DEFAULT_APP_DATA / "desktop"),
                "SOP_SPARK_MODEL_DIR": str(DEFAULT_APP_DATA / "model-store"),
            }
        )
        external_process = subprocess.Popen(
            [str(CONDA_PYTHON), str(ROOT / "server.py")],
            cwd=str(ROOT),
            env=child_env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    else:
        embedded_server = create_server("127.0.0.1", port)
        server_thread = threading.Thread(target=embedded_server.serve_forever, name="sop-http", daemon=True)
        server_thread.start()
    wait_until_ready(base_url)
    show_first_run_credentials()

    window = webview.create_window(
        APP_TITLE,
        f"{base_url}/?desktop=1",
        width=1560,
        height=960,
        min_size=(1180, 720),
        background_color="#0b1723",
        text_select=True,
    )

    def shutdown() -> None:
        if embedded_server is not None:
            embedded_server.shutdown()
            embedded_server.server_close()
        if external_process is not None and external_process.poll() is None:
            external_process.terminate()
            try:
                external_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                external_process.kill()

    window.events.closed += shutdown
    webview.start(gui="edgechromium", debug=False, private_mode=False)


if __name__ == "__main__":
    main()
