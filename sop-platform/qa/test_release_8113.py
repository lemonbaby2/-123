from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "qa" / "release_8113"
BASE_URL = os.getenv("SOP_QA_URL", "http://127.0.0.1:8113")
CREDENTIALS = Path(
    os.getenv(
        "SOP_QA_CREDENTIALS",
        "/home/xjai/Desktop/sop xjai/2026.8.23/runtime/polished-8113/initial_credentials.txt",
    )
)
AUTH_ENV = Path("/home/xjai/.config/ningbo-sop/polished-8113-auth.env")


def wait_for_service(timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if requests.get(BASE_URL, timeout=2).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"8113 服务在 {timeout:.0f} 秒内未就绪")


def account_credentials(username: str) -> tuple[str, str]:
    for line in CREDENTIALS.read_text(encoding="utf-8").splitlines():
        values = line.split("\t")
        if len(values) == 3 and values[1] == username:
            return values[1], values[2]
    raise RuntimeError(f"未找到 8113 账号：{username}")


def recovery_code() -> str:
    for line in AUTH_ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("SOP_PASSWORD_RECOVERY_CODE="):
            return line.split("=", 1)[1]
    raise RuntimeError("未配置 8113 密码恢复码")


def verify_password_workflow() -> dict[str, object]:
    temporary_password = "qa-temporary-8113"
    username, initial_password = account_credentials("worker")
    session = requests.Session()
    try:
        login = session.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": initial_password}, timeout=10)
        login.raise_for_status()
        changed = session.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": initial_password, "new_password": temporary_password},
            timeout=10,
        )
        changed.raise_for_status()
        session.post(f"{BASE_URL}/api/auth/logout", json={}, timeout=10)
        temporary_login = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "worker", "password": temporary_password},
            timeout=10,
        )
        temporary_login.raise_for_status()
        recovered = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"username": username, "recovery_code": recovery_code(), "new_password": initial_password},
            timeout=10,
        )
        recovered.raise_for_status()
        restored_login = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": username, "password": initial_password},
            timeout=10,
        )
        restored_login.raise_for_status()
        return {"passed": True, "change_password": changed.status_code, "forgot_password": recovered.status_code}
    finally:
        try:
            requests.post(
                f"{BASE_URL}/api/auth/forgot-password",
                json={"username": username, "recovery_code": recovery_code(), "new_password": initial_password},
                timeout=10,
            )
        except requests.RequestException:
            pass


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    wait_for_service()
    username, password = account_credentials("admin")
    report: dict[str, object] = {
        "url": BASE_URL,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "views": [],
        "console_errors": [],
        "http_errors": [],
        "password_workflow": verify_password_workflow(),
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path="/usr/bin/google-chrome")
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.on("console", lambda message: report["console_errors"].append(message.text) if message.type == "error" else None)
        page.on("response", lambda response: report["http_errors"].append({"status": response.status, "url": response.url}) if response.status >= 400 else None)
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60_000)
        page.screenshot(path=str(OUTPUT / "00_login_desktop.png"), full_page=True)
        page.click("#forgotPasswordButton")
        page.wait_for_selector("#forgotPasswordDialog[open]")
        page.screenshot(path=str(OUTPUT / "00_forgot_password_desktop.png"), full_page=True)
        page.click('[data-close-dialog="forgotPasswordDialog"]')
        page.fill("#loginUsername", username)
        page.fill("#loginPassword", password)
        page.click("#loginButton")
        page.wait_for_selector("body.authenticated", timeout=60_000)
        page.wait_for_timeout(3000)
        page.click("#changePasswordButton")
        page.wait_for_selector("#changePasswordDialog[open]")
        page.screenshot(path=str(OUTPUT / "00_change_password_desktop.png"), full_page=True)
        page.click('[data-close-dialog="changePasswordDialog"]')

        for number, view in enumerate(("overview", "monitor", "decision", "annotation", "quality", "training", "mes"), 1):
            page.click(f'.nav-item[data-view="{view}"]')
            page.wait_for_timeout(1200)
            if view == "monitor":
                page.wait_for_function("document.querySelector('#sopVideo').readyState >= 2")
            elif view == "annotation":
                page.wait_for_function("document.querySelector('#annotVideo').readyState >= 2")
                page.wait_for_timeout(600)
            elif view == "mes":
                page.wait_for_function("document.querySelector('#mesLiveFeed').naturalWidth > 0", timeout=30_000)
            path = OUTPUT / f"{number:02d}_{view}_desktop.png"
            page.screenshot(path=str(path), full_page=True)
            report["views"].append({"view": view, "screenshot": str(path), "title": page.locator(f"#view-{view} h1").first.inner_text()})

        page.click('.nav-item[data-view="monitor"]')
        page.wait_for_timeout(2500)
        report["monitor_video"] = page.locator("#sopVideo").evaluate(
            "video => ({readyState: video.readyState, networkState: video.networkState, width: video.videoWidth, height: video.videoHeight, currentSrc: video.currentSrc})"
        )
        page.click('.nav-item[data-view="annotation"]')
        page.wait_for_timeout(2500)
        report["annotation_video"] = page.locator("#annotVideo").evaluate(
            "video => ({readyState: video.readyState, networkState: video.networkState, width: video.videoWidth, height: video.videoHeight, currentSrc: video.currentSrc})"
        )

        page.click('.nav-item[data-view="monitor"]')
        page.click("#startAllCameras")
        page.wait_for_timeout(5000)
        report["camera_images"] = page.locator("#cameraWall img").evaluate_all(
            "images => images.map(image => ({src: image.src, width: image.naturalWidth, height: image.naturalHeight}))"
        )

        mobile = browser.new_context(viewport={"width": 390, "height": 844})
        mobile_page = mobile.new_page()
        mobile_page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60_000)
        mobile_page.fill("#loginUsername", username)
        mobile_page.fill("#loginPassword", password)
        mobile_page.click("#loginButton")
        mobile_page.wait_for_selector("body.authenticated", timeout=60_000)
        mobile_page.wait_for_timeout(2500)
        mobile_page.screenshot(path=str(OUTPUT / "08_overview_mobile.png"), full_page=True)
        mobile_page.click('.nav-item[data-view="annotation"]')
        mobile_page.wait_for_function(
            "document.querySelector('#annotVideo').readyState >= 2",
            timeout=30_000,
        )
        mobile_page.wait_for_timeout(600)
        mobile_page.screenshot(path=str(OUTPUT / "09_annotation_mobile.png"), full_page=True)
        mobile.close()
        context.close()
        browser.close()

    monitor = report.get("monitor_video") or {}
    annotation = report.get("annotation_video") or {}
    cameras = report.get("camera_images") or []
    report["passed"] = bool(
        monitor.get("readyState", 0) >= 1
        and annotation.get("readyState", 0) >= 1
        and len(cameras) >= 3
        and all(item.get("width", 0) > 0 and item.get("height", 0) > 0 for item in cameras[:3])
        and not report["console_errors"]
        and not report["http_errors"]
        and report["password_workflow"].get("passed")
    )
    (OUTPUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
