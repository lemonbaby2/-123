from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = os.getenv("SOP_QA_URL", "http://127.0.0.1:8114")
CREDENTIALS = Path(
    os.getenv(
        "SOP_QA_CREDENTIALS",
        "/home/xjai/Desktop/sop xjai/2026.8.23/runtime/integrated-8114/initial_credentials.txt",
    )
)
OUTPUT = Path(__file__).resolve().parent / "release_8114"


def credentials(username: str) -> tuple[str, str]:
    for line in CREDENTIALS.read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) == 3 and fields[1] == username:
            return fields[1], fields[2]
    raise RuntimeError(f"Missing QA credentials for {username}")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    username, password = credentials("admin")
    report: dict[str, object] = {"url": BASE_URL, "checks": {}, "http_errors": [], "console_errors": []}
    checks = report["checks"]
    assert isinstance(checks, dict)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path="/usr/bin/google-chrome")
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on(
            "response",
            lambda response: report["http_errors"].append({"status": response.status, "url": response.url})
            if response.status >= 400 else None,
        )
        page.on(
            "console",
            lambda message: report["console_errors"].append(message.text) if message.type == "error" else None,
        )
        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.fill("#loginUsername", username)
        page.fill("#loginPassword", password)
        page.click("#loginButton")
        page.wait_for_selector("body.authenticated")
        page.click('.nav-item[data-view="annotation"]')
        page.wait_for_function("document.querySelector('#annotVideo').readyState >= 2")
        page.select_option("#annotSourceFilter", "all")
        page.select_option("#annotStatusFilter", "all")
        page.wait_for_timeout(800)
        items = page.evaluate(
            """async () => {
                const video = document.querySelector('#annotVideoSelect').value;
                const time = document.querySelector('#annotVideo').currentTime || 0;
                const response = await fetch(`/api/annotations?video=${encodeURIComponent(video)}&time=${time.toFixed(3)}&source=all&status=all&limit=300`);
                return (await response.json()).items;
            }"""
        )
        checks["current_frame_ai_boxes"] = len(items)
        target = max(items, key=lambda item: (item["box"][2] - item["box"][0]) * (item["box"][3] - item["box"][1]))

        def click_target() -> None:
            canvas = page.locator("#annotCanvas")
            canvas.scroll_into_view_if_needed()
            bounds = canvas.bounding_box()
            if bounds is None:
                raise RuntimeError("Annotation canvas is not visible")
            page.mouse.click(
                bounds["x"] + (target["box"][0] + target["box"][2]) * bounds["width"] / 2,
                bounds["y"] + (target["box"][1] + target["box"][3]) * bounds["height"] / 2,
            )

        page.click("#clearBox")
        click_target()
        page.wait_for_function("!document.querySelector('#deleteSelectedBox').disabled")
        checks["mouse_select"] = page.locator("#selectedBoxTitle").inner_text()
        intercepted = {"count": 0}

        def intercept_delete(route) -> None:
            intercepted["count"] += 1
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"ok": True, "deleted_count": 1, "message": "QA intercepted"}),
            )

        page.route("**/api/annotations/delete", intercept_delete)
        page.keyboard.press("Delete")
        page.wait_for_timeout(500)
        page.unroute("**/api/annotations/delete", intercept_delete)
        checks["delete_key_intercepted"] = intercepted["count"] == 1
        page.fill("#annotLabel", "QA自定义标签")
        page.fill("#annotRegion", "QA自定义区域")
        page.click("#rememberAnnotationVocabulary")
        checks["custom_vocabulary"] = page.evaluate(
            "localStorage.getItem('sop.annotation.labels').includes('QA自定义标签') && localStorage.getItem('sop.annotation.regions').includes('QA自定义区域')"
        )
        page.click("#clearBox")
        click_target()
        page.wait_for_function("!document.querySelector('#setStartKeyframe').disabled")
        page.click("#setStartKeyframe")
        start = int(page.input_value("#trackStartFrame"))
        end = int(page.input_value("#trackEndFrame"))
        checks["track_range"] = {"start": start, "end": end, "valid": end > start}
        task_id = page.input_value("#cvatWorkbenchTask")
        job_response = page.evaluate(
            "task => fetch(`/api/cvat/jobs?task_id=${task}`).then(async response => ({status: response.status, data: await response.json()}))",
            task_id,
        )
        checks["cvat_jobs"] = {
            "task": task_id,
            "status": job_response["status"],
            "count": len(job_response["data"].get("items", [])),
        }
        page.click('.nav-item[data-view="training"]')
        page.wait_for_function("document.querySelector('#trainingVideoSelect').options.length >= 23")
        page.wait_for_function("document.querySelector('#trainingVideoThumbnail').naturalWidth > 0", timeout=30_000)
        checks["training_video_count"] = page.locator("#trainingVideoSelect option").count()
        checks["thumbnail"] = page.locator("#trainingVideoThumbnail").evaluate(
            "image => ({width: image.naturalWidth, height: image.naturalHeight})"
        )
        checks["spark_button"] = page.locator("#oneClickTraining").inner_text()
        checks["prelabel_status"] = page.evaluate(
            "fetch('/api/annotations/prelabel/status').then(response => response.json()).then(value => ({status: value.status, frames: value.catalog_sampled_frames, detections: value.catalog_detections, candidates: value.catalog_candidates}))"
        )
        page.screenshot(path=str(OUTPUT / "training_video_thumbnail.png"), full_page=True)
        browser.close()
    report["passed"] = bool(
        checks["current_frame_ai_boxes"] > 0
        and checks["delete_key_intercepted"]
        and checks["custom_vocabulary"]
        and checks["track_range"]["valid"]
        and checks["cvat_jobs"]["status"] == 200
        and checks["cvat_jobs"]["count"] > 0
        and checks["training_video_count"] >= 23
        and checks["thumbnail"]["width"] > 0
        and not report["http_errors"]
    )
    (OUTPUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
