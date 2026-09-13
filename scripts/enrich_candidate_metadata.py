#!/usr/bin/env python3
"""Verify DOI metadata for candidates recommended by the review ledger."""

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
DATA = ROOT / "data"
OUTPUT = DATA / "candidate_metadata.json"
USER_AGENT = "PolarEvidenceAtlas/1.0 (+https://github.com/skate-debug/polar-evidence-atlas)"


def candidate_path() -> Path:
    private_path = DATA / "candidates.json"
    return private_path if private_path.exists() else DATA / "public" / "candidates.json"


def fetch(doi: str, retries: int = 3):
    request = urllib.request.Request(
        f"https://doi.org/{doi}",
        headers={"Accept": "application/vnd.citationstyles.csl+json", "User-Agent": USER_AGENT},
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return doi, json.loads(response.read().decode("utf-8")), None
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt + 1 == retries:
                return doi, None, str(exc)
            time.sleep(1.5 * (attempt + 1))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    candidates = json.loads(candidate_path().read_text(encoding="utf-8"))["candidates"]
    candidate_by_id = {candidate["id"]: candidate for candidate in candidates}
    reviews = json.loads((DATA / "candidate_reviews.json").read_text(encoding="utf-8"))["reviews"]
    selected = [review for review in reviews if review.get("decision") == "include"]

    existing = {}
    if OUTPUT.exists():
        existing = json.loads(OUTPUT.read_text(encoding="utf-8")).get("records", {})
    candidate_dois = {}
    for review in selected:
        candidate = candidate_by_id.get(review["candidate_id"], {})
        doi = (review.get("resolved_doi") or candidate.get("doi") or "").lower()
        if doi:
            candidate_dois[doi] = review["candidate_id"]
    records = {doi: record for doi, record in existing.items() if doi in candidate_dois}
    requested = list(candidate_dois) if args.force else [doi for doi in candidate_dois if doi not in records]
    errors = {}
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 8))) as executor:
        futures = [executor.submit(fetch, doi) for doi in requested]
        for future in as_completed(futures):
            doi, record, error = future.result()
            if record:
                records[doi] = record
            else:
                errors[doi] = error
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selection": "candidate_reviews decision=include",
        "candidate_ids": dict(sorted(candidate_dois.items())),
        "records": dict(sorted(records.items())),
        "errors": errors,
    }
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)
    print(f"Candidate DOI verification: {len(records)}/{len(candidate_dois)} records; {len(errors)} error(s).")
    return 0 if len(records) == len(candidate_dois) else 1


if __name__ == "__main__":
    raise SystemExit(main())
