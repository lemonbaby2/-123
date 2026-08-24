"""宁波视觉 SOP + CVAT 一体化工作台 V2 Windows 客户端。

客户端不复制中心数据，也不启动第二套服务；所有电脑连接同一 SOP/CVAT 中心机。
首次无法连接时会显示地址配置页，配置保存在当前用户的 LocalAppData。
"""

from __future__ import annotations

import html
import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

import webview


APP_TITLE = "宁波视觉SOP + CVAT 一体化工作台 V2"
DEFAULT_CONFIG = {
    "server_url": "http://10.70.102.210:8113",
    "cvat_url": "http://10.70.102.210:8081",
}
CONFIG_DIR = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "NingboSOPUnified"
CONFIG_PATH = CONFIG_DIR / "client.json"


def normalize_url(value: str) -> str:
    value = str(value or "").strip().rstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("地址必须以 http:// 或 https:// 开头，并包含主机名和端口。")
    return value


def load_config() -> dict[str, str]:
    config = dict(DEFAULT_CONFIG)
    try:
        saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        for key in config:
            if saved.get(key):
                config[key] = normalize_url(saved[key])
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    return config


def save_config(config: dict[str, str]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(CONFIG_PATH)


def probe_server(server_url: str, timeout: float = 4.0) -> tuple[bool, str]:
    try:
        request = urllib.request.Request(
            f"{normalize_url(server_url)}/api/health",
            headers={"User-Agent": "NingboSOPUnified/2026.08.24"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if response.status == 200 and payload.get("status") == "ok":
            return True, str(payload.get("service") or "SOP 中心服务正常")
        return False, f"健康检查返回异常：HTTP {response.status}"
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as exc:
        return False, str(exc)


def portal_url(config: dict[str, str]) -> str:
    query = urllib.parse.urlencode({"desktop": "1", "cvat": config["cvat_url"]})
    return f"{config['server_url']}/unified/?{query}"


def setup_html(config: dict[str, str], error_message: str = "") -> str:
    server = html.escape(config["server_url"], quote=True)
    cvat = html.escape(config["cvat_url"], quote=True)
    error = html.escape(error_message or "请确认中心机已启动，或填写可访问的局域网/公网地址。")
    return f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{APP_TITLE}</title><style>
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;background:linear-gradient(135deg,#071d36,#0d4775);font-family:'Microsoft YaHei UI','Segoe UI',sans-serif;color:#10243e}}
.card{{width:min(720px,92vw);padding:38px;border-radius:18px;background:#fff;box-shadow:0 30px 80px #00142c88}}.mark{{width:48px;height:48px;display:grid;place-items:center;border-radius:13px;color:#fff;background:linear-gradient(135deg,#19a8b8,#1769e0);font-weight:900}}
h1{{margin:20px 0 8px;font-size:28px}}p{{color:#667890;line-height:1.7}}.error{{padding:12px;border:1px solid #f0d4ad;border-radius:8px;background:#fff8ec;color:#9a5c18;font-size:13px}}
form{{display:grid;gap:18px;margin-top:24px}}label{{display:grid;gap:8px;font-size:13px;font-weight:700}}input{{height:48px;padding:0 14px;border:1px solid #cfdae5;border-radius:8px;font:inherit}}button{{height:48px;border:0;border-radius:8px;color:white;background:#1769e0;font-weight:800;cursor:pointer}}button:disabled{{opacity:.6}}#message{{min-height:20px;margin:0;font-size:12px}}.hint{{font-size:12px}}
</style></head><body><section class='card'><div class='mark'>NB</div><h1>连接一体化中心服务</h1><p>本客户端只连接中心系统，不会覆盖旧网页或复制业务数据。内网使用中心机 IP，外网可填写 Cloudflare Tunnel 的 HTTPS 地址。</p><div class='error'>{error}</div>
<form id='form'><label>SOP 中心地址<input id='server' value='{server}' required></label><label>CVAT 地址<input id='cvat' value='{cvat}' required></label><button id='save'>保存并连接</button><p id='message'></p></form><p class='hint'>配置文件：%LOCALAPPDATA%\\NingboSOPUnified\\client.json</p></section>
<script>
const form=document.getElementById('form'),button=document.getElementById('save'),message=document.getElementById('message');
form.addEventListener('submit',async event=>{{event.preventDefault();button.disabled=true;button.textContent='正在检测…';message.textContent='';try{{const result=await window.pywebview.api.save_config(document.getElementById('server').value,document.getElementById('cvat').value);if(!result.ok)throw new Error(result.message);message.textContent='连接成功，正在进入工作台…';}}catch(error){{message.textContent=error.message;message.style.color='#c0392b';}}finally{{button.disabled=false;button.textContent='保存并连接';}}}});
</script></body></html>"""


class DesktopBridge:
    def __init__(self, config: dict[str, str]) -> None:
        self.config = config
        self.window: webview.Window | None = None
        self._cvat_window: webview.Window | None = None

    def bind(self, window: webview.Window) -> None:
        self.window = window

    def get_config(self) -> dict[str, str]:
        return {"ok": True, **self.config, "config_path": str(CONFIG_PATH)}

    def save_config(self, server_url: str, cvat_url: str) -> dict[str, object]:
        try:
            candidate = {"server_url": normalize_url(server_url), "cvat_url": normalize_url(cvat_url)}
            healthy, message = probe_server(candidate["server_url"])
            if not healthy:
                return {"ok": False, "message": f"SOP 中心连接失败：{message}"}
            save_config(candidate)
            self.config = candidate
            if self.window:
                threading.Timer(0.25, lambda: self.window.load_url(portal_url(candidate))).start()
            return {"ok": True, "message": message}
        except (OSError, ValueError) as exc:
            return {"ok": False, "message": str(exc)}

    def open_cvat(self, route: str = "/tasks") -> dict[str, object]:
        try:
            base = normalize_url(self.config["cvat_url"])
            safe_route = "/" + str(route or "tasks").lstrip("/")
            target = f"{base}{safe_route}"
            try:
                self._cvat_window = webview.create_window(
                    "官方 CVAT 标注工作区",
                    url=target,
                    width=1440,
                    height=900,
                    min_size=(1080, 680),
                    resizable=True,
                )
            except Exception:
                webbrowser.open(target, new=2)
            return {"ok": True, "url": target}
        except ValueError as exc:
            return {"ok": False, "message": str(exc)}

    def open_external(self, url: str) -> dict[str, object]:
        try:
            webbrowser.open(normalize_url(url), new=2)
            return {"ok": True}
        except ValueError as exc:
            return {"ok": False, "message": str(exc)}


def main() -> None:
    config = load_config()
    healthy, message = probe_server(config["server_url"])
    bridge = DesktopBridge(config)
    if healthy:
        window = webview.create_window(
            APP_TITLE,
            url=portal_url(config),
            js_api=bridge,
            width=1600,
            height=980,
            min_size=(1180, 720),
            resizable=True,
        )
    else:
        window = webview.create_window(
            APP_TITLE,
            html=setup_html(config, message),
            js_api=bridge,
            width=920,
            height=760,
            min_size=(760, 620),
            resizable=True,
        )
    bridge.bind(window)
    webview.start(debug=False, gui="edgechromium")


if __name__ == "__main__":
    main()
