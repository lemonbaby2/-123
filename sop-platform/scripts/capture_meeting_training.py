#!/usr/bin/env python3
"""Capture sanitized SOP/CVAT training screenshots without saving demo edits."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright


DEFAULT_CREDENTIALS = Path(
    "/home/xjai/Desktop/sop xjai/2026.8.23/runtime/distributed-8116/initial_credentials.txt"
)


def sop_manager_credentials(path: Path) -> tuple[str, str]:
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0].strip() == "管理者":
            return parts[1].strip(), parts[2].strip()
    raise RuntimeError(f"No manager credential found in {path}")


def screenshot(page: Page, output: Path, name: str) -> None:
    target = output / name
    page.screenshot(path=str(target), full_page=False)
    if name.startswith(("11_", "12_", "13_", "14_", "15_", "16_")):
        image = Image.open(target).convert("RGB")
        draw = ImageDraw.Draw(image)
        # CVAT shows the logged-in username at the upper right; training media must not expose accounts.
        draw.rectangle((1515, 0, 1600, 70), fill="#d9d9d9")
        target.unlink()
        image.save(target, quality=96)


def login_sop(page: Page, base_url: str, credentials: Path, output: Path) -> None:
    username, password = sop_manager_credentials(credentials)
    page.goto(base_url, wait_until="networkidle", timeout=60_000)
    screenshot(page, output, "01_SOP登录页_未填写凭据.png")
    page.locator("#loginUsername").fill(username)
    page.locator("#loginPassword").fill(password)
    page.locator("#loginButton").click()
    page.locator("body.authenticated").wait_for(timeout=30_000)
    page.wait_for_timeout(2_000)
    screenshot(page, output, "02_SOP总览与闭环架构.png")


def capture_sop_views(page: Page, output: Path) -> None:
    views = [
        ("monitor", "03_02数据获取与清洗.png"),
        ("decision", "04_03_AI预标注与现场证据.png"),
        ("annotation", "05_04_SOP人工复核与CVAT双向同步.png"),
        ("quality", "06_05数据集构建与质量冻结.png"),
        ("training", "07_06训练验证与部署.png"),
        ("mes", "08_07实时SOP与MES.png"),
    ]
    for view, filename in views:
        page.locator(f'.nav-item[data-view="{view}"]').click()
        page.locator(f"#view-{view}.active").wait_for(timeout=15_000)
        if view == "mes":
            try:
                page.wait_for_function(
                    "document.getElementById('mesLiveFeed').naturalWidth > 0",
                    timeout=15_000,
                )
            except PlaywrightTimeoutError:
                pass
        page.wait_for_timeout(1_500)
        screenshot(page, output, filename)


def login_cvat(page: Page, base_url: str, password: str, output: Path) -> None:
    page.goto(f"{base_url}/auth/login", wait_until="networkidle", timeout=60_000)
    screenshot(page, output, "09_CVAT登录页_未填写凭据.png")
    page.locator("input").first.fill("admin")
    page.get_by_text("Sign in", exact=True).click()
    page.locator('input[type="password"]').wait_for(timeout=15_000)
    screenshot(page, output, "10_CVAT密码步骤_未填写凭据.png")
    page.locator('input[type="password"]').fill(password)
    page.get_by_text("下一步", exact=True).click()
    page.wait_for_url("**/tasks", timeout=30_000)
    page.wait_for_timeout(2_000)
    screenshot(page, output, "11_CVAT任务列表.png")


def open_rectangle_menu(page: Page) -> None:
    page.locator(".cvat-draw-rectangle-control").click()
    page.get_by_text("绘制新矩形框", exact=True).wait_for(timeout=10_000)


def draw_on_canvas(page: Page) -> None:
    canvas = page.locator(".cvat-canvas-container")
    box = canvas.bounding_box()
    if not box:
        raise RuntimeError("CVAT canvas has no visible bounding box")
    x1 = box["x"] + box["width"] * 0.40
    y1 = box["y"] + box["height"] * 0.34
    x2 = box["x"] + box["width"] * 0.59
    y2 = box["y"] + box["height"] * 0.60
    page.mouse.move(x1, y1)
    page.mouse.down()
    page.mouse.move(x2, y2, steps=12)
    page.mouse.up()
    page.wait_for_timeout(900)


def capture_cvat_job(page: Page, base_url: str, output: Path) -> None:
    page.goto(f"{base_url}/tasks/1293/jobs/1290?frame=0", wait_until="networkidle", timeout=120_000)
    page.locator(".cvat-canvas-container").wait_for(timeout=60_000)
    page.wait_for_timeout(3_000)
    screenshot(page, output, "12_CVAT完整标注工作台.png")

    open_rectangle_menu(page)
    screenshot(page, output, "13_CVAT矩形框_形状与Track选择.png")
    page.get_by_text("形状", exact=True).click()
    draw_on_canvas(page)
    screenshot(page, output, "14_CVAT新建并选中矩形框.png")

    page.keyboard.press("Delete")
    page.wait_for_timeout(700)
    screenshot(page, output, "15_CVAT_Delete删除演示框.png")

    open_rectangle_menu(page)
    page.get_by_text("跟踪轨迹", exact=True).click()
    draw_on_canvas(page)
    screenshot(page, output, "16_CVAT_Track与关键帧演示.png")

    # Deliberately do not click Save. Closing the browser discards the training draft.


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sop-url", default="http://192.168.1.129:8116")
    parser.add_argument("--cvat-url", default="http://localhost:8081")
    parser.add_argument("--credentials", type=Path, default=DEFAULT_CREDENTIALS)
    args = parser.parse_args()
    cvat_password = os.environ.get("CVAT_DEMO_PASSWORD", "")
    if not cvat_password:
        raise RuntimeError("CVAT_DEMO_PASSWORD must be supplied only for this process")
    args.output.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path="/usr/bin/google-chrome",
            args=["--ignore-certificate-errors", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            viewport={"width": 1600, "height": 900},
            device_scale_factor=1,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        try:
            page = context.new_page()
            login_sop(page, args.sop_url, args.credentials, args.output)
            capture_sop_views(page, args.output)
            page.close()

            page = context.new_page()
            login_cvat(page, args.cvat_url, cvat_password, args.output)
            capture_cvat_job(page, args.cvat_url, args.output)
            page.close()
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(f"Timed out while capturing training screenshots: {exc}") from exc
        finally:
            browser.close()


if __name__ == "__main__":
    main()
