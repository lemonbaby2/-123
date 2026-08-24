"""Windows client for the Ningbo SOP collaboration platform V3."""

from __future__ import annotations

import html
import json
import os
import threading
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

import webview


TITLE = "宁波视觉SOP多人标注与决策平台 V3"
DEFAULT = {"server_url": "http://10.70.102.210:8117", "cvat_url": "http://10.70.102.210:8081"}
CONFIG_DIR = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "NingboSOPUnifiedV3"
CONFIG_PATH = CONFIG_DIR / "client.json"


def normalize(value: str) -> str:
    value = str(value or "").strip().rstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("地址必须以 http:// 或 https:// 开头。")
    return value


def load_config() -> dict[str, str]:
    config = dict(DEFAULT)
    try:
        saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        config.update({key: normalize(saved[key]) for key in config if saved.get(key)})
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    return config


def save_config(config: dict[str, str]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(CONFIG_PATH)


def probe(server_url: str, timeout: float = 5.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(f"{normalize(server_url)}/api/health", timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return response.status == 200 and payload.get("status") == "ok", str(payload.get("service") or "服务正常")
    except Exception as exc:
        return False, str(exc)


def target_url(config: dict[str, str]) -> str:
    query = urllib.parse.urlencode({"desktop": "1", "cvat": config["cvat_url"]})
    return f"{config['server_url']}/unified-v3/?{query}"


def setup_page(config: dict[str, str], error: str) -> str:
    server = html.escape(config["server_url"], quote=True)
    cvat = html.escape(config["cvat_url"], quote=True)
    reason = html.escape(error or "中心服务暂不可达")
    return f"""<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>{TITLE}</title><style>
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;background:linear-gradient(135deg,#071e38,#0a5279);font-family:'Microsoft YaHei UI',sans-serif;color:#102640}}.card{{width:min(720px,92vw);padding:38px;border-radius:18px;background:#fff;box-shadow:0 25px 70px #00142680}}.logo{{width:48px;height:48px;display:grid;place-items:center;border-radius:13px;color:#fff;background:linear-gradient(135deg,#1ab1bd,#176bd8);font-weight:900}}h1{{margin:20px 0 6px}}p{{color:#687b8e;line-height:1.7}}.error{{padding:11px;border:1px solid #eed7b2;border-radius:8px;background:#fff8ed;color:#9b5b19;font-size:12px}}form{{display:grid;gap:16px;margin-top:22px}}label{{display:grid;gap:7px;font-size:13px;font-weight:700}}input{{height:46px;padding:0 13px;border:1px solid #ccd8e3;border-radius:8px}}button{{height:46px;border:0;border-radius:8px;color:#fff;background:#176bd8;font-weight:800}}</style>
<body><section class='card'><div class='logo'>NB</div><h1>连接 SOP 协同中心</h1><p>局域网填写中心机地址；外网填写 Cloudflare Tunnel 的 HTTPS 地址。配置不会覆盖旧软件。</p><div class='error'>{reason}</div><form id='form'><label>SOP V3 地址<input id='server' value='{server}'></label><label>CVAT 地址<input id='cvat' value='{cvat}'></label><button>保存并连接</button><p id='message'></p></form></section><script>document.getElementById('form').addEventListener('submit',async e=>{{e.preventDefault();const r=await window.pywebview.api.save_config(document.getElementById('server').value,document.getElementById('cvat').value);document.getElementById('message').textContent=r.message||''}})</script></body></html>"""


class Bridge:
    def __init__(self, config: dict[str, str]) -> None:
        self.config = config
        self.window: webview.Window | None = None

    def bind(self, window: webview.Window) -> None:
        self.window = window

    def save_config(self, server_url: str, cvat_url: str) -> dict[str, object]:
        try:
            candidate = {"server_url": normalize(server_url), "cvat_url": normalize(cvat_url)}
            healthy, message = probe(candidate["server_url"])
            if not healthy:
                return {"ok": False, "message": f"连接失败：{message}"}
            save_config(candidate)
            self.config = candidate
            if self.window:
                threading.Timer(0.2, lambda: self.window.load_url(target_url(candidate))).start()
            return {"ok": True, "message": "连接成功"}
        except (OSError, ValueError) as exc:
            return {"ok": False, "message": str(exc)}

    def open_cvat(self, route: str = "/tasks") -> dict[str, object]:
        try:
            target = f"{normalize(self.config['cvat_url'])}/{str(route).lstrip('/')}"
            try:
                webview.create_window("官方 CVAT 标注工作区", url=target, width=1440, height=900, min_size=(1080, 680))
            except Exception:
                webbrowser.open(target, new=2)
            return {"ok": True, "url": target}
        except ValueError as exc:
            return {"ok": False, "message": str(exc)}


def main() -> None:
    config = load_config()
    healthy, message = probe(config["server_url"])
    bridge = Bridge(config)
    if healthy:
        window = webview.create_window(TITLE, url=target_url(config), js_api=bridge, width=1600, height=980, min_size=(1180, 720))
    else:
        window = webview.create_window(TITLE, html=setup_page(config, message), js_api=bridge, width=900, height=740, min_size=(760, 620))
    bridge.bind(window)
    webview.start(debug=False, gui="edgechromium")


if __name__ == "__main__":
    main()
