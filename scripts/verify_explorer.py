#!/usr/bin/env python3
"""Optional browser QA using Playwright and an installed Chrome executable."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8674/")
    parser.add_argument("--chrome", default="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    args = parser.parse_args()
    inventory = json.loads((ROOT / "data" / "cold_seep_candidates.json").read_text(encoding="utf-8"))
    microbial_count = sum(item["priority"] == "microbial" for item in inventory["candidates"])
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.chrome, headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1050})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url + "?collection=scs-cold-seeps", wait_until="networkidle")
        page.wait_for_selector("#sourceList .source-card")
        assert page.title() == "Earth & Ocean Evidence Atlas"
        assert page.locator("#sourceList .source-card").count() == 34
        assert page.locator("#libraryRows tr").count() == len(inventory["candidates"])
        page.select_option("#compartmentFilter", "water-column")
        assert page.locator("#sourceList .source-card").count() > 0
        page.locator("#sourceList .source-card").first.click()
        assert page.locator(".detail-title").count() == 1
        page.click("[data-language-choice='zh-CN']")
        assert page.title() == "地球与海洋证据图谱"
        assert "冷泉" in page.locator(".detail-title").inner_text()
        page.select_option("#libraryPriority", "microbial")
        assert page.locator("#libraryRows tr").count() == microbial_count
        page.fill("#librarySearch", "水体")
        assert 0 < page.locator("#libraryRows tr").count() < microbial_count
        page.fill("#librarySearch", "impossible-no-record-xxxxx")
        assert "没有符合" in page.locator("#libraryRows").inner_text()
        page.fill("#librarySearch", "")
        page.click("#resetFilters")
        assert page.locator("#sourceList .source-card").count() == 106
        page.click("#openCommand")
        page.fill("#commandInput", "aed8728")
        assert page.locator(".command-result").count() == 1
        page.keyboard.press("Enter")
        assert "硫化物" in page.locator(".detail-title").inner_text()
        shots = ROOT / ".research-cache" / "qa"
        shots.mkdir(parents=True, exist_ok=True)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(shots / "desktop-source.png"), full_page=False)
        page.click("#resetFilters")
        page.select_option("#collectionFilter", "scs-cold-seeps")
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(700)
        page.screenshot(path=str(shots / "desktop.png"), full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(args.url + "?collection=scs-cold-seeps&lang=zh-CN", wait_until="networkidle")
        assert page.locator("#sourceList .source-card").count() == 34
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        page.screenshot(path=str(shots / "mobile.png"), full_page=False)
        assert not errors, errors
        print(json.dumps({"desktop_and_mobile": "passed", "bilingual": "passed", "collection_compartment_filters": "passed", "library_search": "passed", "command_search": "passed", "javascript_errors": errors}, ensure_ascii=False))
        browser.close()


if __name__ == "__main__":
    main()
