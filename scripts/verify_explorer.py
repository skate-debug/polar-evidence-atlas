#!/usr/bin/env python3
"""Optional browser QA using Playwright and an installed Chrome executable."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8674/")
    parser.add_argument("--chrome", default="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    args = parser.parse_args()
    inventory_path = ROOT / "data" / "cold_seep_candidates.json"
    if not inventory_path.exists():
        inventory_path = ROOT / "data/public/cold_seep_candidates.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    sources = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
    seep_count = sum(source.get("collection") == "scs-cold-seeps" for source in sources)
    review_counts = {}
    for item in json.loads((ROOT / "data/cold_seep_reviews.json").read_text(encoding="utf-8"))["reviews"]:
        review_counts[item["status"]] = review_counts.get(item["status"], 0) + 1
    microbial_count = sum(item["priority"] == "microbial" for item in inventory["candidates"])
    global_path = ROOT / "data/global_cold_seep_candidates.json"
    if not global_path.exists():
        global_path = ROOT / "data/public/global_cold_seep_candidates.json"
    global_inventory = json.loads(global_path.read_text())
    global_reviews = json.loads((ROOT / "data/global_cold_seep_reviews.json").read_text())["reviews"]
    global_count = sum(item["status"] == "curated" for item in global_reviews)
    active_global_dois = {item['doi'] for item in global_inventory['candidates']}
    global_active_count = sum(item["status"] == "curated" and item['doi'] in active_global_dois for item in global_reviews)
    with sync_playwright() as playwright:
        local = urlparse(args.url).hostname in {"localhost", "127.0.0.1", "::1"}
        browser = playwright.chromium.launch(executable_path=args.chrome, headless=True, args=["--no-proxy-server"] if local else [])
        page = browser.new_page(viewport={"width": 1600, "height": 1050})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url + "?collection=scs-cold-seeps", wait_until="networkidle")
        page.wait_for_selector("#sourceList .source-card")
        assert page.title() == "Earth & Ocean Evidence Atlas"
        assert page.locator("#sourceList .source-card").count() == seep_count
        assert page.locator("#libraryRows tr").count() == len(inventory["candidates"])
        page.select_option("#compartmentFilter", "water-column")
        assert page.locator("#sourceList .source-card").count() > 0
        page.locator("#sourceList .source-card").first.click()
        assert page.locator(".detail-title").count() == 1
        page.click("[data-language-choice='zh-CN']")
        assert page.title() == "地球与海洋证据图谱"
        assert re.search(r"[\u4e00-\u9fff]", page.locator(".detail-title").inner_text())
        page.select_option("#libraryPriority", "microbial")
        assert page.locator("#libraryRows tr").count() == microbial_count
        page.fill("#librarySearch", "水体")
        assert 0 < page.locator("#libraryRows tr").count() < microbial_count
        page.fill("#librarySearch", "impossible-no-record-xxxxx")
        assert "没有符合" in page.locator("#libraryRows").inner_text()
        page.fill("#librarySearch", "")
        page.select_option("#libraryPriority", "")
        page.select_option("#libraryReview", "curated")
        assert page.locator("#libraryRows tr").count() == seep_count
        page.select_option("#libraryReview", "awaiting_source_text")
        assert page.locator("#libraryRows tr").count() == review_counts["awaiting_source_text"]
        assert page.locator("#libraryRows [data-library-source]").count() == 0
        page.select_option("#libraryReview", "linked_notice")
        assert page.locator("#libraryRows tr").count() == review_counts["linked_notice"]
        page.select_option("#libraryReview", "")
        page.click("#resetFilters")
        page.select_option("#collectionFilter", "global-cold-seeps")
        assert page.locator("#sourceList .source-card").count() == global_count
        assert page.input_value("#libraryCollection") == "global-cold-seeps"
        assert page.locator("#libraryRows tr").count() == len(global_inventory["candidates"])
        page.select_option("#libraryReview", "curated")
        assert page.locator("#libraryRows [data-library-source]").count() == global_active_count
        assert "global-cold-seep-curated-apa7.md" in page.locator("#libraryRefs").get_attribute("href")
        page.select_option("#libraryReview", "version_check")
        assert page.locator("#libraryRows [data-library-source]").count() == 0
        page.select_option("#libraryReview", "awaiting_source_review")
        assert page.locator("#libraryRows [data-library-source]").count() == 0
        page.select_option("#libraryReview", "")
        page.select_option("#siteFilter", "gulf-mexico")
        assert 0 < page.locator("#sourceList .source-card").count() < global_count
        page.locator("#sourceList .source-card").first.click()
        assert "讨论部分的引用用途" in page.locator("#detailBody").inner_text()
        page.select_option("#libraryCollection", "scs-cold-seeps")
        assert page.locator("#libraryRows tr").count() == len(inventory["candidates"])
        page.click("#resetFilters")
        assert page.locator("#sourceList .source-card").count() == len(sources)
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
        assert page.locator("#sourceList .source-card").count() == seep_count
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        page.screenshot(path=str(shots / "mobile.png"), full_page=False)
        page.goto(args.url + "?collection=global-cold-seeps&lang=en", wait_until="networkidle")
        assert page.locator("#sourceList .source-card").count() == global_count
        assert page.input_value("#libraryCollection") == "global-cold-seeps"
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        assert not errors, errors
        print(json.dumps({"desktop_and_mobile": "passed", "bilingual": "passed", "collection_compartment_filters": "passed", "international_collection_and_shared_dois": "passed", "library_search": "passed", "command_search": "passed", "javascript_errors": errors}, ensure_ascii=False))
        browser.close()


if __name__ == "__main__":
    main()
