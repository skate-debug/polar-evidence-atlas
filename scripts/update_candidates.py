#!/usr/bin/env python3
"""Discover recent candidate papers without promoting them to curated claims."""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "search_queries.json"
SOURCES_PATH = ROOT / "data" / "sources.json"
OUTPUT_PATH = ROOT / "data" / "candidates.json"
ARCHIVE_PATH = ROOT / "data" / "candidate_archive.json"
API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
USER_AGENT = "PolarEvidenceAtlas/1.0 (+https://github.com/skate-debug/polar-evidence-atlas)"


def readable_snapshot(private_path: Path) -> Path:
    public_path = private_path.parent / "public" / private_path.name
    return private_path if private_path.exists() else public_path


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def query_europe_pmc(query: str, since: str, limit: int) -> list[dict]:
    bounded = f"({query}) AND FIRST_PDATE:[{since} TO 3000-12-31]"
    results: list[dict] = []
    cursor = "*"
    while len(results) < limit:
        params = urllib.parse.urlencode(
            {
                "query": bounded,
                "format": "json",
                "resultType": "core",
                "pageSize": min(100, limit - len(results)),
                "cursorMark": cursor,
                "sort": "P_PDATE_D desc",
            }
        )
        request = urllib.request.Request(f"{API}?{params}", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
        page = payload.get("resultList", {}).get("result", [])
        if not page:
            break
        results.extend(page)
        next_cursor = payload.get("nextCursorMark")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
    return results[:limit]


def author_list(record: dict) -> list[str]:
    authors = record.get("authorList", {}).get("author", [])
    values = []
    for author in authors:
        name = author.get("fullName") or " ".join(
            part for part in (author.get("firstName"), author.get("lastName")) if part
        )
        if name:
            values.append(name)
    return values


def main() -> int:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default=config.get("default_since", "2024-01-01"))
    parser.add_argument("--limit-per-query", type=int, default=25)
    parser.add_argument("--dry-run", action="store_true", help="query and summarize without changing candidate files")
    args = parser.parse_args()
    try:
        date.fromisoformat(args.since)
    except ValueError as exc:
        raise SystemExit("--since must be YYYY-MM-DD") from exc

    curated = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    curated_dois = {source["doi"].lower() for source in curated}
    curated_titles = {normalize_title(source["title"]) for source in curated}
    previous_path = readable_snapshot(OUTPUT_PATH)
    previous_payload = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else {"candidates": []}
    previous_candidates = previous_payload.get("candidates", [])
    previous_by_doi = {item.get("doi", "").lower(): item for item in previous_candidates if item.get("doi")}
    previous_by_title = {normalize_title(item.get("title", "")): item for item in previous_candidates if item.get("title")}
    readable_archive = readable_snapshot(ARCHIVE_PATH)
    archive_payload = json.loads(readable_archive.read_text(encoding="utf-8")) if readable_archive.exists() else {"candidates": []}
    archived_candidates = archive_payload.get("candidates", [])
    archived_by_doi = {item.get("doi", "").lower(): item for item in archived_candidates if item.get("doi")}
    archived_by_title = {normalize_title(item.get("title", "")): item for item in archived_candidates if item.get("title")}
    candidates: dict[str, dict] = {}
    failures: list[dict] = []
    run_at = datetime.now(timezone.utc).isoformat()

    for search in config["queries"]:
        try:
            results = query_europe_pmc(search["query"], args.since, args.limit_per_query)
        except Exception as exc:
            failures.append({"query_id": search["id"], "error": str(exc)})
            continue
        for record in results:
            title = record.get("title", "").strip()
            doi = record.get("doi", "").lower().strip()
            normalized = normalize_title(title)
            if not title or doi in curated_dois or normalized in curated_titles:
                continue
            prior = (
                previous_by_doi.get(doi) if doi else None
            ) or previous_by_title.get(normalized) or (
                archived_by_doi.get(doi) if doi else None
            ) or archived_by_title.get(normalized)
            candidate_id = prior.get("id") if prior else (
                "candidate:" + re.sub(r"[^a-z0-9]+", "-", (doi or normalized).lower()).strip("-")[:100]
            )
            if candidate_id not in candidates:
                publication_date = (
                    record.get("firstPublicationDate")
                    or record.get("electronicPublicationDate")
                    or record.get("journalInfo", {}).get("printPublicationDate")
                    or ""
                )
                year_match = re.match(r"(\d{4})", publication_date)
                pmcid = record.get("pmcid")
                pmid = record.get("pmid")
                url = f"https://doi.org/{doi}" if doi else (
                    f"https://europepmc.org/article/MED/{pmid}" if pmid else ""
                )
                first_discovered = (
                    prior.get("first_discovered_at") or prior.get("discovered_at")
                    if prior else run_at
                )
                candidates[candidate_id] = {
                    "id": candidate_id,
                    "status": "candidate",
                    "title": title,
                    "authors": author_list(record),
                    "journal": record.get("journalTitle") or record.get("journalInfo", {}).get("journal", {}).get("title", ""),
                    "year": int(year_match.group(1)) if year_match else record.get("pubYear"),
                    "publication_date": publication_date,
                    "doi": doi,
                    "pmid": pmid,
                    "pmcid": pmcid,
                    "abstract": re.sub(r"<[^>]+>", "", record.get("abstractText", "")),
                    "url": url,
                    "matched_queries": [search["id"]],
                    "poles": [search["pole"]],
                    "domains": [search["domain"]],
                    "discovered_at": first_discovered,
                    "first_discovered_at": first_discovered,
                    "last_seen_at": run_at,
                    "discovery_runs": int(prior.get("discovery_runs", 1)) + 1 if prior else 1,
                    "discovery_source": "Europe PMC",
                }
            else:
                item = candidates[candidate_id]
                for field, value in (
                    ("matched_queries", search["id"]),
                    ("poles", search["pole"]),
                    ("domains", search["domain"]),
                ):
                    if value not in item[field]:
                        item[field].append(value)

    ordered = sorted(
        candidates.values(),
        key=lambda item: (item.get("publication_date", ""), item.get("title", "")),
        reverse=True,
    )
    payload = {
        "generated_at": run_at,
        "since": args.since,
        "policy": "Metadata-only discovery. Human review is required before promotion to data/sources.json or data/claims.json.",
        "candidates": ordered,
        "query_failures": failures,
    }
    current_ids = set(candidates)
    archive_by_id = {item["id"]: item for item in archived_candidates if item.get("id") not in current_ids}
    for item in previous_candidates:
        if item.get("id") in current_ids:
            continue
        archived = dict(item)
        archived.setdefault("first_discovered_at", archived.get("discovered_at", run_at))
        archived.setdefault("last_seen_at", previous_payload.get("generated_at", run_at))
        archived["retired_at"] = run_at
        archived["retirement_reason"] = "Not returned by the current bounded discovery run or now present in curated sources."
        archive_by_id[archived["id"]] = archived
    archive_output = {
        "updated_at": run_at,
        "policy": "Candidates absent from the latest discovery snapshot are retained here for provenance and review-ledger joins.",
        "candidates": sorted(archive_by_id.values(), key=lambda item: (item.get("retired_at", ""), item.get("title", "")), reverse=True),
    }
    if args.dry_run:
        print(
            f"Dry run: discovered {len(ordered)} unique candidates; would archive "
            f"{len(archive_output['candidates'])}; {len(failures)} query failure(s)."
        )
        return 0 if not failures else 1
    temp = OUTPUT_PATH.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(OUTPUT_PATH)
    archive_temp = ARCHIVE_PATH.with_suffix(".json.tmp")
    archive_temp.write_text(json.dumps(archive_output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    archive_temp.replace(ARCHIVE_PATH)
    print(
        f"Discovered {len(ordered)} unique candidates; archived {len(archive_output['candidates'])}; "
        f"{len(failures)} query failure(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
