#!/usr/bin/env python3
"""Refresh DOI metadata while retaining the curated scientific profiles."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = ROOT / "data" / "sources.json"
OUTPUT_PATH = ROOT / "data" / "metadata.json"
USER_AGENT = "PolarEvidenceAtlas/1.0 (+https://github.com/skate-debug/polar-evidence-atlas)"


def fetch_csl(doi: str, retries: int = 3) -> tuple[str, dict | None, str | None]:
    url = f"https://doi.org/{doi}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.citationstyles.csl+json",
            "User-Agent": USER_AGENT,
        },
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                record = json.loads(response.read().decode("utf-8"))
                return doi, record, None
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt + 1 == retries:
                return doi, None, str(exc)
            time.sleep(1.5 * (attempt + 1))
    return doi, None, "unknown error"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--force", action="store_true", help="refetch metadata already in the cache")
    args = parser.parse_args()

    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    existing = {}
    if OUTPUT_PATH.exists():
        existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8")).get("records", {})

    dois = [source["doi"].lower() for source in sources]
    requested = dois if args.force else [doi for doi in dois if doi not in existing]
    records = {doi: value for doi, value in existing.items() if doi in dois}
    errors: dict[str, str] = {}

    if requested:
        with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 8))) as executor:
            futures = {executor.submit(fetch_csl, doi): doi for doi in requested}
            for future in as_completed(futures):
                doi, record, error = future.result()
                if record:
                    records[doi] = record
                else:
                    errors[doi] = error or "unknown error"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": "DOI content negotiation (CSL-JSON)",
        "records": dict(sorted(records.items())),
        "errors": errors,
    }
    temp = OUTPUT_PATH.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(OUTPUT_PATH)
    print(f"Metadata cache: {len(records)}/{len(dois)} DOI records; {len(errors)} fetch errors.")
    return 0 if len(records) == len(dois) else 1


if __name__ == "__main__":
    raise SystemExit(main())
