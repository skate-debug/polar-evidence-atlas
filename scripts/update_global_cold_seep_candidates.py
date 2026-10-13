#!/usr/bin/env python3
"""Cumulative international cold-seep discovery; no automatic claim promotion."""
from __future__ import annotations
import argparse
import calendar
import csv
import json
import re
import hashlib
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from update_cold_seep_candidates import get_results, classify, COMPARTMENTS, TOPICS, plain_text, write_json
from export_cold_seep_references import fetch, one

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
USER_AGENT = "EarthOceanEvidenceAtlas/2.2 (+https://github.com/skate-debug/polar-evidence-atlas)"
REGIONS = {
    "gulf-mexico": r"Gulf.of.Mexico|Mississippi.Canyon|Green.Canyon|GOM[- ]D|GOM[- ]C|\bGoM\b",
    "northeast-pacific": r"Cascadia|Hydrate.Ridge|Santa.Monica|Eastern.North.Pacific|Eel.River|Point.Dume|Oregon|Del.Mar|Southern.California",
    "costa-rica": r"Costa.Rica|Mound.12|Mound.11|Quepos|Jaco.Scar",
    "mediterranean": r"Mediterranean|Napoli|Amon.mud|Nile.deep|Olimpi|Palmahim",
    "black-sea": r"Black.Sea|Marmara|Dnepr|Dnieper",
    "caspian": r"Caspian",
    "arctic-seeps": r"Arctic|Svalbard|Barents|Laptev|Haakon|H[aå]kon|Storfjordrenna|Vestnesa|Kongsfjord|Baffin",
    "north-sea": r"North.Sea|Darci",
    "hikurangi": r"Hikurangi|New.Zealand|Omakere|Opouawe|Urut[iī]",
    "indian-ocean-seeps": r"Krishna.Godavari|Cauvery.Mannar|Makran|Arabian.Sea|Bay.of.Bengal|Indian.Ocean",
    "japan-seeps": r"Japan.Trench|Sagami|Nankai|Hatsushima|Ryukyu|Okinawa",
    "atlantic-seeps": r"Scotian|Cadiz|C[aá]diz|Congo.fan|Gulf.of.Guinea|Niger.Delta|Angola",
    "antarctic-seeps": r"Antarctic|Weddell|Ross.Sea|South.Georgia",
    "global-comparison": r"global|worldwide|cross.region|geographically.diverse",
}
SCS = r"South.China.Sea|Haima|Haiyang.?4|Jiaolong|Formosa|\bSite.?F\b|Dongsha|Shenhu|Qiongdongnan|Wenhai|Lingshui"
MICROBIAL = r"microb|bacter|archae|virus|viral|virom|fung|protist|symbio|metagenom|methanotroph|ANME|foraminifer"


def load(name, default):
    path = DATA / name
    if not path.exists():
        path = DATA / "public" / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def cached_query(key, since, until, request):
    """Reuse successful same-day query responses when resuming a large batch."""
    path = ROOT / ".research-cache" / ("global-query-" + hashlib.sha256((key + since + until + date.today().isoformat()).encode()).hexdigest()[:20] + ".json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    for attempt in range(5):
        try:
            result = request()
            write_json(path, result)
            return result
        except Exception:
            if attempt == 4:
                raise
            time.sleep(min(4 * 2**attempt, 20))


def publication(record):
    parts = [record.get(key, {}).get("date-parts", [[]])[0] for key in ("published", "published-online", "published-print", "issued")]
    parts = min((item for item in parts if item), default=[])
    return "-".join(str(value) if index == 0 else str(value).zfill(2) for index, value in enumerate(parts))


def in_window(value, since, until):
    try:
        parts = [int(part) for part in value.split("-")]
        if len(parts) == 3:
            start = end = date(*parts).isoformat()
        elif len(parts) == 2:
            year, month = parts
            start, end = date(year, month, 1).isoformat(), date(year, month, calendar.monthrange(year, month)[1]).isoformat()
        else:
            start, end = date(parts[0], 1, 1).isoformat(), date(parts[0], 12, 31).isoformat()
        return since <= start and end <= until
    except (ValueError, TypeError, IndexError):
        return False


def candidate(doi, title, abstract, published, authors, journal, **extra):
    text = title + " " + abstract
    return {"id": "global-seep-candidate:" + re.sub(r"[^a-z0-9]+", "-", doi).strip("-"),
        "doi": doi, "title": title, "abstract": abstract, "publication_date": published, "year": int(published[:4]),
        "authors": authors, "journal": journal, "collection": "global-cold-seeps", "url": "https://doi.org/" + doi,
        "publication_stage": "preprint" if doi.startswith(("10.1101/", "10.21203/", "10.2139/", "10.20944/", "10.64898/", "10.22541/", "10.7287/peerj.preprints")) else "journal_record",
        "compartments": classify(text, COMPARTMENTS) or ["unspecified"], "topics": classify(text, TOPICS) or ["geochemistry"],
        "sites": classify(text, REGIONS) or ["global-unspecified"], "priority": "microbial" if re.search(MICROBIAL, text, re.I) else "context",
        "classification_basis": "Provisional title/abstract tags; sample geography and evidence require source review", **extra}


def scope_match(text):
    return not re.search(SCS, text, re.I) or bool(classify(text, REGIONS))


def export_inventory(payload):
    reviews = {item["doi"]: item for item in load("global_cold_seep_reviews.json", {"reviews": []})["reviews"]}
    rows = []
    fields = ["doi", "title", "publication_date", "year", "journal", "authors", "compartments", "topics", "sites", "priority", "publication_stage", "status", "access_level", "reason", "reason_zh", "next_action", "source_id"]
    for item in payload["candidates"]:
        review = reviews.get(item["doi"], {})
        row = {key: item.get(key, review.get(key, "")) for key in fields}
        row["status"] = review.get("status", "awaiting_source_review")
        rows.append({key: " | ".join(str(part) for part in value) if isinstance(value, list) else value for key, value in row.items()})
    target = ROOT / "dist/global-cold-seep-literature.csv"
    target.parent.mkdir(exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Global seep inventory: {len(rows)} DOI records")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since")
    parser.add_argument("--until", default=date.today().isoformat())
    parser.add_argument("--export-only", action="store_true")
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--supplement-only", action="store_true", help="add an explicit inspected DOI shortlist without another search")
    args = parser.parse_args()
    previous = load("global_cold_seep_candidates.json", {"candidates": []})
    if args.export_only:
        export_inventory(previous)
        return
    until = date.fromisoformat(args.until)
    try:
        start = until.replace(year=until.year - 10)
    except ValueError:
        start = until.replace(year=until.year - 10, day=28)
    since = args.since or start.isoformat()
    metadata = load("global_cold_seep_metadata.json", {"records": {}, "errors": {}})
    archive = load("global_cold_seep_archive.json", {"candidates": []})
    archived = {item["doi"]: item for item in archive["candidates"]}
    for item in previous["candidates"]:
        if not in_window(item.get("publication_date", ""), since, args.until):
            archived[item["doi"]] = {**item, "archived_at": datetime.now(timezone.utc).isoformat(), "archive_reason": "Outside the current rolling discovery window; evidence and reviews remain available"}
    records = {item["doi"]: item for item in previous["candidates"] if in_window(item.get("publication_date", ""), since, args.until)}
    records.update({doi: item for doi, item in archived.items() if in_window(item.get("publication_date", ""), since, args.until)})
    config = json.loads((ROOT / "config/global_cold_seep_queries.json").read_text())
    run_at = datetime.now(timezone.utc).isoformat()
    logs, failures = [], []
    if not args.metadata_only and not args.supplement_only:
        for query in config["queries"]:
            try:
                results, count = cached_query(query["id"], since, args.until, lambda: get_results(query["query"], since, args.until))
                logs.append({**query, "hit_count": count})
                print(query["id"], count, "database matches", flush=True)
                for result in results:
                    doi = result.get("doi", "").lower().strip()
                    title, abstract = plain_text(result.get("title", "")), plain_text(result.get("abstractText", ""))
                    if not doi or not scope_match(title + " " + abstract) or not in_window(result.get("firstPublicationDate", ""), since, args.until):
                        continue
                    author_records = result.get("authorList", {}).get("author", [])
                    authors = [item.get("fullName") or " ".join(part for part in (item.get("firstName"), item.get("lastName")) if part) for item in author_records]
                    info = result.get("journalInfo", {})
                    old = records.get(doi, {})
                    records[doi] = candidate(doi, title, abstract, result["firstPublicationDate"], authors, info.get("journal", {}).get("title", ""),
                        pmid=result.get("pmid", ""), pmcid=result.get("pmcid", ""), volume=info.get("volume", ""), issue=info.get("issue", ""), pages=result.get("pageInfo", ""),
                        author_records=author_records, first_discovered_at=old.get("first_discovered_at", run_at), last_seen_at=run_at,
                        matched_queries=list(dict.fromkeys(old.get("matched_queries", []) + [query["id"]])), discovery_source="Europe PMC core API")
            except Exception as exc:
                failures.append({"query": query["id"], "error": str(exc)})
        for query in config["crossref_queries"]:
            try:
                params = urllib.parse.urlencode({"query.bibliographic": query, "filter": f"from-pub-date:{since},until-pub-date:{args.until},type:journal-article", "rows": 100})
                req = urllib.request.Request("https://api.crossref.org/works?" + params, headers={"User-Agent": USER_AGENT})
                def retrieve():
                    with urllib.request.urlopen(req, timeout=50) as response:
                        return json.load(response)["message"]["items"]
                results = cached_query("crossref:" + query, since, args.until, retrieve)
                added = 0
                for result in results:
                    title, abstract = one(result.get("title")), plain_text(result.get("abstract", ""))
                    text = title + " " + abstract
                    if not re.search(r"seep", text, re.I) or not scope_match(text) or not classify(text, REGIONS):
                        continue
                    doi = result["DOI"].lower()
                    if doi in records or not in_window(publication(result), since, args.until):
                        continue
                    authors = [" ".join(part for part in (item.get("given"), item.get("family")) if part) for item in result.get("author", [])]
                    records[doi] = candidate(doi, title, abstract, publication(result), authors, one(result.get("container-title")), first_discovered_at=run_at, last_seen_at=run_at,
                        matched_queries=["crossref:" + query], discovery_source="Crossref publisher-deposited metadata")
                    metadata["records"][doi] = result
                    added += 1
                logs.append({"query": query, "provider": "Crossref", "returned": len(results), "added": added})
                print(query, added, "added", flush=True)
            except Exception as exc:
                failures.append({"query": query, "error": str(exc)})
        if failures:
            raise SystemExit(f"Discovery incomplete; previous public inventory preserved: {failures}")
    supplement = ROOT / "config/global_cold_seep_supplementary_dois.json"
    explicit_dois = set(json.loads(supplement.read_text()) if supplement.exists() else [])
    packet_path = ROOT / "config/global_cold_seep_reviewed.json"
    if packet_path.exists():
        explicit_dois.update(item['doi'] for item in json.loads(packet_path.read_text()))
    for doi in sorted(explicit_dois):
        if doi in records:
            continue
        if doi in archived and not in_window(archived[doi]["publication_date"], since, args.until):
            continue
        cache_path = ROOT / ".research-cache" / (re.sub(r"[^a-z0-9]+", "-", doi) + ".json")
        cached = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        record = cached.get("csl")
        if not record:
            _, record, error = fetch(doi)
            if not record:
                raise SystemExit(f"Supplement DOI unresolved: {doi}: {error}")
        text = cached.get("record", {})
        published = text.get("firstPublicationDate") or publication(record)
        if not in_window(published, since, args.until):
            raise SystemExit(f"Supplement outside window: {doi}: {published}")
        authors = [" ".join(part for part in (item.get("given"), item.get("family")) if part) for item in record.get("author", [])]
        records[doi] = candidate(doi, one(record.get("title")), plain_text(text.get("abstractText") or record.get("abstract", "")), published, authors, one(record.get("container-title")),
            pmid=text.get("pmid", ""), pmcid=text.get("pmcid", ""), matched_queries=["explicit-comparison-supplement"], discovery_source="Inspected primary-source DOI follow-up", first_discovered_at=run_at, last_seen_at=run_at)
        metadata["records"][doi] = record
    # Broad database retrieval sometimes matches an incidental seep mention.
    # Retain abstract-free audit provenance for records filtered at this stage.
    source_dois = {item["doi"] for item in load("sources.json", []) if item.get("collection") == "scs-cold-seeps" and "comparative" not in item.get("sites", [])}
    filtered = {item["doi"]: item for item in previous.get("scope_filtered", [])}
    for doi, item in list(records.items()):
        # Public snapshots intentionally omit abstracts. A completed lexical
        # discovery screen must persist when its original text is unavailable.
        if item.get("discovery_scope_screen") == "lexical_or_editorial":
            continue
        text = item["title"] + " " + item.get("abstract", "")
        explicit = re.search(r"\b(?:cold|methane|hydrocarbon|oil|gas|marine)[-\s]+seeps?\b|\bmud[- ]volcano|\bgas[- ]hydrate", text, re.I)
        if doi not in explicit_dois and (doi in source_dois or not (explicit or (re.search(r"seep", item["title"], re.I) and classify(text, REGIONS)))):
            filtered[doi] = {"doi": doi, "title": item["title"], "basis": "Existing source profile contains SCS-only sampled scope" if doi in source_dois else "No explicit seep/hydrate association in title or available abstract; incidental database match"}
            records.pop(doi)
        else:
            filtered.pop(doi, None)
            item["discovery_scope_screen"] = "lexical_or_editorial"
    shared = load("cold_seep_metadata.json", {"records": {}})["records"]
    for doi in records:
        if doi in shared:
            metadata["records"].setdefault(doi, shared[doi])
    pending = [doi for doi in records if doi not in metadata["records"]]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch, doi): doi for doi in pending}
        for index, future in enumerate(as_completed(futures), 1):
            doi, record, error = future.result()
            if record:
                metadata["records"][doi] = record
                metadata["errors"].pop(doi, None)
            else:
                metadata["errors"][doi] = error
            if index % 30 == 0:
                print(f"DOI metadata {index}/{len(pending)}", flush=True)
    collapsed = previous.get("collapsed_versions", [])
    for doi, item in records.items():
        if metadata["records"].get(doi, {}).get("type") == "posted-content":
            item["publication_stage"] = "preprint"
    for doi, record in metadata["records"].items():
        successor = next((item.get("id", "").lower() for item in record.get("relation", {}).get("is-preprint-of", []) if item.get("id-type") == "doi" and item.get("id", "").lower() in records), None)
        if doi in records and successor:
            records.pop(doi)
            if not any(item["doi"] == doi for item in collapsed):
                collapsed.append({"doi": doi, "published_doi": successor, "basis": "Crossref is-preprint-of relation"})
    payload = {"generated_at": run_at, "since": since, "until": args.until, "collection": "global-cold-seeps", "queries": logs or previous.get("queries", []),
        "policy": "International cold-seep discussion inventory; provisional geographic tags require source inspection. DOI records include retained preprints and notices.",
        "query_failures": [], "collapsed_versions": collapsed, "scope_filtered": list(filtered.values()), "candidates": sorted(records.values(), key=lambda item: (item["year"], item["publication_date"], item["title"]), reverse=True)}
    archived = {doi: item for doi, item in archived.items() if doi not in records}
    metadata["records"] = {doi: record for doi, record in metadata["records"].items() if doi in records or doi in archived}
    metadata["provider"] = "Crossref REST API and independently inspected publisher/Europe PMC records"
    write_json(DATA / "global_cold_seep_candidates.json", payload)
    write_json(DATA / "global_cold_seep_archive.json", {"generated_at": run_at, "policy": "Records aging out of the rolling window retain source and review joins; no scientific claim is removed by discovery", "candidates": sorted(archived.values(), key=lambda item: item["doi"])})
    write_json(DATA / "global_cold_seep_metadata.json", metadata)
    export_inventory(payload)
    print(f"Metadata resolved: {sum(doi in metadata['records'] for doi in records)}/{len(records)}; errors={len(metadata['errors'])}")


if __name__ == "__main__":
    main()
