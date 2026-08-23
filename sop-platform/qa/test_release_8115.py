from __future__ import annotations

import json
import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = os.getenv("SOP_QA_URL", "http://127.0.0.1:8115")
CREDENTIALS = Path(
    os.getenv(
        "SOP_QA_CREDENTIALS",
        "/home/xjai/Desktop/sop xjai/2026.8.23/runtime/integrated-8115/initial_credentials.txt",
    )
)
OUTPUT = Path(__file__).resolve().parent / "release_8115"


def credentials(username: str) -> tuple[str, str]:
    for line in CREDENTIALS.read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) == 3 and fields[1] == username:
            return fields[1], fields[2]
    raise RuntimeError(f"Missing QA credentials for {username}")


def number_after(label: str, text: str) -> int:
    match = re.search(rf"{label}\s+(\d+)", text)
    if not match:
        raise AssertionError(f"Missing {label!r} count in {text!r}")
    return int(match.group(1))


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    username, password = credentials("admin")
    report: dict[str, object] = {
        "url": BASE_URL,
        "checks": {},
        "http_errors": [],
        "console_errors": [],
    }
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
        page.wait_for_function("document.querySelector('#annotationFilterSummary').textContent.includes('原始')")

        default_summary = page.locator("#annotationFilterSummary").inner_text()
        raw_total = number_after("原始", default_summary)
        filtered_total = number_after("筛选后", default_summary)
        checks["recommended_filter"] = {
            "minimum_confidence": page.locator("#annotConfidenceFilter").input_value(),
            "overlap_suppression": page.locator("#annotSuppressOverlap").is_checked(),
            "show_region_boxes": page.locator("#annotShowRegionBoxes").is_checked(),
            "display_limit": page.locator("#annotDisplayLimit").input_value(),
            "raw_total": raw_total,
            "filtered_total": filtered_total,
            "summary": default_summary,
        }
        checks["table_page_rows"] = page.locator("#annotationRows tr").count()
        checks["page_summary"] = page.locator("#annotationPageSummary").inner_text()
        page.locator("#view-annotation").screenshot(path=OUTPUT / "recommended_candidate_review.png")

        page.locator("#annotConfidenceFilter").evaluate(
            "element => { element.value = '0'; element.dispatchEvent(new Event('input', { bubbles: true })); }"
        )
        page.check("#annotShowRegionBoxes")
        page.uncheck("#annotSuppressOverlap")
        page.select_option("#annotDisplayLimit", "300")
        expanded_summary = page.locator("#annotationFilterSummary").inner_text()
        expanded_total = number_after("筛选后", expanded_summary)
        checks["expanded_all_candidates"] = {
            "filtered_total": expanded_total,
            "summary": expanded_summary,
            "page_summary": page.locator("#annotationPageSummary").inner_text(),
        }
        page.click("#annotationNextPage")
        checks["expanded_second_page"] = {
            "page_summary": page.locator("#annotationPageSummary").inner_text(),
            "row_count": page.locator("#annotationRows tr").count(),
        }

        page.click("#resetAnnotationFilters")
        restored_summary = page.locator("#annotationFilterSummary").inner_text()
        checks["reset_filter"] = {
            "minimum_confidence": page.locator("#annotConfidenceFilter").input_value(),
            "overlap_suppression": page.locator("#annotSuppressOverlap").is_checked(),
            "show_region_boxes": page.locator("#annotShowRegionBoxes").is_checked(),
            "display_limit": page.locator("#annotDisplayLimit").input_value(),
            "summary": restored_summary,
        }
        page.locator(".annot-stage").screenshot(path=OUTPUT / "filtered_annotation_canvas.png")
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#annotationFilterSummary").scroll_into_view_if_needed()
        checks["mobile_layout"] = {
            "viewport_width": page.evaluate("document.documentElement.clientWidth"),
            "page_scroll_width": page.evaluate("document.documentElement.scrollWidth"),
            "filter_width": round(page.locator(".annotation-filter-strip").bounding_box()["width"]),
        }
        page.screenshot(path=OUTPUT / "annotation_filters_mobile.png")
        browser.close()

    assert raw_total > filtered_total > 0
    assert checks["table_page_rows"] <= 25
    assert expanded_total == raw_total
    assert "第 2 /" in checks["expanded_second_page"]["page_summary"]
    assert checks["expanded_second_page"]["row_count"] <= 25
    assert checks["reset_filter"]["minimum_confidence"] == "25"
    assert checks["reset_filter"]["overlap_suppression"] is True
    assert checks["reset_filter"]["show_region_boxes"] is False
    assert checks["reset_filter"]["display_limit"] == "40"
    assert checks["mobile_layout"]["page_scroll_width"] <= checks["mobile_layout"]["viewport_width"]
    assert checks["mobile_layout"]["filter_width"] <= checks["mobile_layout"]["viewport_width"]
    assert not report["http_errors"]
    assert not report["console_errors"]
    report["passed"] = True
    (OUTPUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
