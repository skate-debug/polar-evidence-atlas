#!/usr/bin/env python3
"""Discover ten years of SCS seep literature and export a searchable inventory.

Topic tags are provisional title/abstract classifications, not verified claims.
Only explicitly curated profiles can contribute scientific graph edges.
"""
from __future__ import annotations

import argparse
import csv
import calendar
import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = DATA / "cold_seep_candidates.json"
API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
USER_AGENT = "EarthOceanEvidenceAtlas/2.0 (+https://github.com/skate-debug/polar-evidence-atlas)"
COMPARTMENTS = {
    "water-column": r"water.column|seawater|pelagic|water layers",
    "bottom-water": r"bottom.water|overlying.water|plume",
    "sediment": r"sediment|porewater|pore.water|subsurface|subseafloor",
    "interface": r"sediment.water.interface|benthic.water.interface|benthic.filter",
    "symbiosis": r"symbio|holobiont|gill|mussel|clam|tubeworm|sponge.associated",
    "carbonate": r"carbonate|microbial.mat|biofilm",
}
TOPICS = {
    "community": r"microbial.diversity|community|communities|microbiome|co.occurrence|assembly",
    "genomes": r"metagenom|genom|evolution|microdiversity",
    "methane": r"methan|ANME|Methylococc|methylotroph",
    "sulfur": r"sulf|sulph|syntroph|Campylobacter",
    "nitrogen": r"nitrogen|nitrate|nitrite|ammoni|denitrif|nitrif|diazotroph",
    "phosphorus": r"phosph|mercury|trace.metal|iron|manganese",
    "carbon": r"organic.matter|organic.carbon|carbon.fix|carbon.cycl|hydrocarbon|alkane|dehalogen",
    "viruses": r"virus|viral|virom|phage|CRISPR|defen[sc]e.system",
    "microeukaryotes": r"microeuk|protist|fung|ciliate|foraminifer",
    "symbioses": r"symbio|holobiont|bacteriocyte|gill",
    "cultivation": r"cultiv|cultur|isolat|sp\. nov|natural.product|biosynthe",
    "geochemistry": r"geochem|isotop|hydrate|seepage|methane.flux|carbonate|plume|transport",
    "disturbance": r"pollut|microplastic|mercury|resistan|pathogen|PFAS|halogen",
    "methods": r"sensor|observator|Raman|in.situ|sampling|acoustic|submersible",
}
SITE_RULES = {
    "haima": r"haima",
    "site-f": r"site[ -]?f\b|\bf.site|formosa.ridge|jiaolong",
    "haiyang4": r"haiyang.?4",
    "dongsha": r"dongsha|GMGS2",
    "shenhu": r"shenhu",
    "qiongdongnan": r"qiongdongnan",
    "wenhai": r"wenhai",
    "lingshui": r"lingshui",
    "newborn": r"newborn|human.induced",
    "comparative": r"globally|global.distribut|gulf.of.mexico|scotian|cross.region|worldwide|subarctic.to.tropical",
}


def read_data(name: str, fallback):
    path = DATA / name
    if not path.exists():
        path = DATA / "public" / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def classify(text: str, rules: dict) -> list[str]:
    return [key for key, pattern in rules.items() if re.search(pattern, text, re.I)]


def plain_text(value: str) -> str:
    for _ in range(3):
        decoded = html.unescape(value)
        if decoded == value:
            break
        value = decoded
    return " ".join(re.sub(r"<[^>]+>", "", value).split())


def normalized_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", plain_text(value).lower())


def get_results(query: str, since: str, until: str) -> tuple[list[dict], int]:
    cursor = "*"
    results = []
    total = 0
    while True:
        params = urllib.parse.urlencode({
            "query": f"({query}) AND FIRST_PDATE:[{since} TO {until}]",
            "format": "json", "resultType": "core", "pageSize": 100,
            "cursorMark": cursor, "sort": "P_PDATE_D desc",
        })
        for attempt in range(3):
            try:
                req = urllib.request.Request(f"{API}?{params}", headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=45) as response:
                    payload = json.load(response)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)
        total = payload.get("hitCount", 0)
        results.extend(payload.get("resultList", {}).get("result", []))
        next_cursor = payload.get("nextCursorMark")
        if len(results) >= total or not next_cursor or next_cursor == cursor:
            return results, total
        cursor = next_cursor


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def export_inventory(payload: dict) -> None:
    target = ROOT / "dist" / "cold-seep-literature.csv"
    target.parent.mkdir(exist_ok=True)
    fields = ["id", "publication_date", "year", "title", "authors", "journal", "doi", "pmid", "pmcid", "compartments", "topics", "sites", "priority", "publication_stage", "status", "classification_basis", "url"]
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    curated = {source["doi"].lower() for source in sources}
    rows = []
    for item in payload["candidates"]:
        row = {field: item.get(field, "") for field in fields}
        row["status"] = "curated" if item.get("doi", "").lower() in curated else "discovered; source review pending"
        for field, value in row.items():
            if isinstance(value, list):
                row[field] = " | ".join(str(x) for x in value)
        rows.append(row)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Exported {len(rows)} inventory rows to {target.relative_to(ROOT)}.")


def finalize_inventory(payload: dict) -> dict:
    overrides = json.loads((ROOT / "config" / "cold_seep_metadata_overrides.json").read_text(encoding="utf-8"))
    specs = {spec["doi"]: spec for spec in json.loads((ROOT / "config" / "cold_seep_seed.json").read_text(encoding="utf-8"))}
    metadata = read_data("cold_seep_metadata.json", {"records": {}})["records"]
    all_dois = {item.get("doi") for item in payload["candidates"]}
    kept = []
    for item in payload["candidates"]:
        if item["title"] in overrides:
            item.update(overrides[item["title"]])
            item["id"] = "seep-candidate:" + re.sub(r"[^a-z0-9]+", "-", item["doi"]).strip("-")
            item["url"] = "https://doi.org/" + item["doi"]
        successors = metadata.get(item.get("doi"), {}).get("relation", {}).get("is-preprint-of", [])
        published = next((x["id"] for x in successors if x.get("id-type") == "doi" and x.get("id", "").lower() in all_dois), None)
        if published:
            collapsed = payload.setdefault("collapsed_versions", [])
            if not any(x["id"] == item["id"] for x in collapsed):
                collapsed.append({"id": item["id"], "doi": item["doi"], "published_doi": published, "basis": "Crossref is-preprint-of relation"})
            continue
        spec = specs.get(item.get("doi"))
        if spec:
            item["compartments"] = spec["compartments"]
            item["topics"] = spec["topics"]
            item["sites"] = spec["sites"]
            item["classification_basis"] = "Source-scoped classification from the inspected curation profile"
        else:
            item["sites"] = classify(item["title"] + " " + item.get("abstract", ""), SITE_RULES) or ["regional"]
        kept.append(item)
    payload["candidates"] = kept
    return payload


def crossref_discovery(payload: dict, config: dict) -> dict:
    metadata = read_data("cold_seep_metadata.json", {"records": {}, "errors": {}})
    records = {item.get("doi") or item["id"]: item for item in payload["candidates"]}
    run_at = datetime.now(timezone.utc).isoformat()
    log = []
    for query in config.get("crossref_queries", []):
        params = urllib.parse.urlencode({
            "query.bibliographic": query,
            "filter": f"from-pub-date:{payload['since']},until-pub-date:{payload['until']},type:journal-article",
            "rows": 150,
            "select": "DOI,title,author,container-title,volume,issue,page,article-number,issued,published,published-print,published-online,type,abstract,relation",
        })
        request = urllib.request.Request("https://api.crossref.org/works?" + params, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=50) as response:
            results = json.load(response)["message"]["items"]
        relevant = 0
        added = 0
        for result in results:
            title = plain_text(result.get("title", [""])[0])
            abstract = plain_text(result.get("abstract", ""))
            text = title + " " + abstract
            if not re.search(r"South China Sea|Haima|Formosa|Dongsha|Qiongdongnan", text, re.I) or not re.search(r"seep", text, re.I):
                continue
            relevant += 1
            doi = result["DOI"].lower()
            metadata["records"].setdefault(doi, result)
            if doi in records:
                continue
            dates = []
            month_dates = []
            year_dates = []
            for key in ("published-online", "published-print", "published", "issued"):
                parts = result.get(key, {}).get("date-parts", [[]])[0]
                if len(parts) >= 3:
                    dates.append(f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}")
                elif len(parts) == 2:
                    month_dates.append((int(parts[0]), int(parts[1])))
                elif len(parts) == 1:
                    year_dates.append(int(parts[0]))
            if not dates:
                # Include an imprecise date only if its entire possible
                # interval falls inside the window; do not invent a day.
                if month_dates:
                    year, month = min(month_dates)
                    interval_start = f"{year:04d}-{month:02d}-01"
                    interval_end = f"{year:04d}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"
                    publication_date, precision = f"{year:04d}-{month:02d}", "month"
                elif year_dates:
                    year = min(year_dates)
                    interval_start, interval_end = f"{year:04d}-01-01", f"{year:04d}-12-31"
                    publication_date, precision = str(year), "year"
                else:
                    continue
                if not payload["since"] <= interval_start or not interval_end <= payload["until"]:
                    continue
            else:
                publication_date, precision = min(dates), "day"
                if not payload["since"] <= publication_date <= payload["until"]:
                    continue
            authors = result.get("author", [])
            microbial = bool(re.search(r"microb|bacter|archae|virus|viral|virom|fung|protist|symbio|metagenom|methanotroph|ANME|foraminifer", text, re.I))
            record_id = "seep-candidate:" + re.sub(r"[^a-z0-9]+", "-", doi).strip("-")
            records[doi] = {
                "id": record_id, "collection": "scs-cold-seeps", "status": "candidate", "publication_stage": "journal_record",
                "title": title, "authors": [" ".join(x for x in (a.get("given"), a.get("family")) if x) for a in authors],
                "author_records": [{"firstName": a.get("given", ""), "lastName": a.get("family", "")} for a in authors],
                "journal": result.get("container-title", [""])[0], "volume": result.get("volume", ""), "issue": result.get("issue", ""), "pages": result.get("page", ""),
                "year": int(publication_date[:4]), "publication_date": publication_date, "doi": doi, "pmid": "", "pmcid": "", "abstract": abstract,
                "publication_date_precision": precision,
                "url": f"https://doi.org/{doi}", "compartments": classify(text, COMPARTMENTS), "topics": classify(text, TOPICS),
                "sites": classify(text, SITE_RULES) or ["regional"], "priority": "microbial" if microbial else "context",
                "classification_basis": "Provisional title/abstract tags from publisher-deposited metadata; source review pending",
                "matched_queries": ["crossref:" + query], "discovery_source": "Crossref publisher-deposited metadata",
                "first_discovered_at": run_at, "last_seen_at": run_at,
            }
            added += 1
        log.append({"query": query, "returned": len(results), "scope_matches": relevant, "new_records": added})
        print(f"Crossref {query}: {relevant} scoped matches; {added} added", flush=True)
    metadata["provider"] = "Crossref REST API, DOI content negotiation, and inspected publisher records"
    write_json(DATA / "cold_seep_metadata.json", metadata)
    payload["crossref_searches"] = log
    payload["candidates"] = sorted(records.values(), key=lambda item: (item["year"], item["publication_date"], item["title"]), reverse=True)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--until", default=date.today().isoformat())
    parser.add_argument("--since")
    parser.add_argument("--export-only", action="store_true")
    parser.add_argument("--reclassify", action="store_true", help="apply inspected taxonomy and metadata overrides without a new search")
    parser.add_argument("--crossref-only", action="store_true", help="extend the existing inventory with publisher-deposited marine literature")
    args = parser.parse_args()
    if args.export_only:
        export_inventory(read_data("cold_seep_candidates.json", {"candidates": []}))
        return 0
    if args.reclassify:
        payload = finalize_inventory(read_data("cold_seep_candidates.json", {"candidates": []}))
        write_json(OUTPUT, payload)
        export_inventory(payload)
        return 0
    if args.crossref_only:
        config = json.loads((ROOT / "config" / "cold_seep_queries.json").read_text(encoding="utf-8"))
        payload = finalize_inventory(crossref_discovery(read_data("cold_seep_candidates.json", {"candidates": []}), config))
        write_json(OUTPUT, payload)
        export_inventory(payload)
        return 0
    until = date.fromisoformat(args.until)
    try:
        earliest = until.replace(year=until.year - 10)
    except ValueError:
        earliest = until.replace(year=until.year - 10, day=28)
    since = args.since or earliest.isoformat()
    date.fromisoformat(since)
    config = json.loads((ROOT / "config" / "cold_seep_queries.json").read_text(encoding="utf-8"))
    previous = read_data("cold_seep_candidates.json", {"candidates": []})
    prior = {item["id"]: item for item in previous.get("candidates", [])}
    records = {}
    log = []
    failures = []
    run_at = datetime.now(timezone.utc).isoformat()
    for query in config["queries"]:
        try:
            results, count = get_results(query["query"], since, until.isoformat())
        except Exception as exc:
            failures.append({"query_id": query["id"], "error": str(exc)})
            continue
        log.append({"query_id": query["id"], "query": query["query"], "hit_count": count})
        print(f"{query['id']}: {count} metadata matches", flush=True)
        for result in results:
            title = plain_text(result.get("title", ""))
            doi = result.get("doi", "").lower().strip()
            pmid = result.get("pmid", "")
            record_id = "seep-candidate:" + re.sub(r"[^a-z0-9]+", "-", doi or pmid or title.lower()).strip("-")
            if record_id in records:
                records[record_id]["matched_queries"].append(query["id"])
                continue
            abstract = plain_text(result.get("abstractText", ""))
            text = title + " " + abstract
            authors = [a.get("fullName") or " ".join(x for x in (a.get("firstName"), a.get("lastName")) if x) for a in result.get("authorList", {}).get("author", [])]
            info = result.get("journalInfo", {})
            publication_date = result.get("firstPublicationDate", "")
            sites = classify(text, SITE_RULES)
            microbial = bool(re.search(r"microb|bacter|archae|virus|viral|virom|fung|protist|symbio|metagenom|methanotroph|ANME", text, re.I))
            records[record_id] = {
                "id": record_id, "collection": "scs-cold-seeps", "status": "candidate",
                "title": title, "authors": authors,
                "author_records": result.get("authorList", {}).get("author", []),
                "journal": info.get("journal", {}).get("title", ""),
                "volume": info.get("volume", ""), "issue": info.get("issue", ""),
                "pages": result.get("pageInfo", ""),
                "year": int(publication_date[:4] or result.get("pubYear", 0)),
                "publication_date": publication_date, "doi": doi,
                "pmid": pmid, "pmcid": result.get("pmcid", ""), "abstract": abstract,
                "url": f"https://doi.org/{doi}" if doi else f"https://europepmc.org/article/MED/{pmid}",
                "compartments": classify(text, COMPARTMENTS), "topics": classify(text, TOPICS),
                "sites": sites or ["regional"], "priority": "microbial" if microbial else "context",
                "classification_basis": "Provisional lexical tags from title and abstract; not full-text curation",
                "matched_queries": [query["id"]], "discovery_source": "Europe PMC title/abstract queries",
                "first_discovered_at": prior.get(record_id, {}).get("first_discovered_at", run_at),
                "last_seen_at": run_at,
                "publication_type": result.get("pubTypeList", {}).get("pubType", []),
            }
    # Add inspected comparison studies whose SCS sampling is documented in
    # Methods rather than in the title or abstract. The shortlist is explicit.
    supplementary = []
    for doi in json.loads((ROOT / "config" / "cold_seep_seed_dois.json").read_text(encoding="utf-8")):
        record_id = "seep-candidate:" + re.sub(r"[^a-z0-9]+", "-", doi).strip("-")
        if record_id in records:
            continue
        cache = ROOT / ".research-cache" / (re.sub(r"[^a-z0-9]+", "-", doi) + ".json")
        if cache.exists():
            source = json.loads(cache.read_text(encoding="utf-8"))
            csl = source.get("csl", {})
            record = source.get("record", {})
        else:
            request = urllib.request.Request(f"https://doi.org/{doi}", headers={"Accept": "application/vnd.citationstyles.csl+json", "User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=45) as response:
                csl = json.load(response)
            record = {}
        title_value = csl.get("title", record.get("title", ""))
        title = plain_text(title_value[0] if isinstance(title_value, list) else title_value)
        abstract = plain_text(record.get("abstractText") or csl.get("abstract", ""))
        text = title + " " + abstract
        parts = csl.get("issued", {}).get("date-parts", [[]])[0]
        publication_date = record.get("firstPublicationDate") or "-".join(str(x).zfill(2) if i else str(x) for i, x in enumerate(parts))
        journal = csl.get("container-title", "")
        authors = [" ".join(x for x in (a.get("given"), a.get("family")) if x) for a in csl.get("author", [])]
        records[record_id] = {"id": record_id, "collection": "scs-cold-seeps", "status": "candidate", "title": title,
            "authors": authors, "author_records": [{"firstName": a.get("given", ""), "lastName": a.get("family", "")} for a in csl.get("author", [])],
            "journal": journal[0] if isinstance(journal, list) else journal, "volume": csl.get("volume", ""), "issue": csl.get("issue", ""), "pages": csl.get("page", ""),
            "year": int(publication_date[:4]), "publication_date": publication_date, "doi": doi, "pmid": record.get("pmid", ""), "pmcid": record.get("pmcid", ""),
            "abstract": abstract, "url": f"https://doi.org/{doi}", "compartments": classify(text, COMPARTMENTS), "topics": classify(text, TOPICS),
            "sites": classify(text, SITE_RULES) or ["regional"], "priority": "microbial", "classification_basis": "SCS Methods scope inspected; other tags provisionally classified from title and abstract",
            "matched_queries": ["inspected-scs-methods"], "discovery_source": "DOI-verified supplemental curation shortlist", "first_discovered_at": run_at, "last_seen_at": run_at}
        supplementary.append(doi)
    # Collapse duplicates, and prefer a version of record to an identically
    # titled preprint. Distinct-title preprints remain visibly labeled.
    deduplicated = {}
    duplicates = []
    for item in records.values():
        if item.get("publication_date", "") and not since <= item["publication_date"] <= until.isoformat():
            continue
        item["publication_stage"] = "preprint" if item.get("doi", "").startswith(("10.21203/", "10.1101/")) else "journal_record"
        key = normalized_title(item["title"])
        old = deduplicated.get(key)
        if old:
            prefer_item = (item["publication_stage"] != "preprint", bool(item.get("doi"))) > (old["publication_stage"] != "preprint", bool(old.get("doi")))
            duplicates.append((old if prefer_item else item)["id"])
            if prefer_item:
                deduplicated[key] = item
        else:
            deduplicated[key] = item
    records = {item["id"]: item for item in deduplicated.values()}
    payload = {"generated_at": run_at, "since": since, "until": until.isoformat(),
               "collection": "scs-cold-seeps", "policy": "Title/abstract discovery inventory. Tags are provisional. Only curated source profiles supply graph claims.",
               "queries": log, "query_failures": failures, "supplementary_dois": supplementary, "collapsed_duplicate_ids": duplicates,
               "candidates": sorted(records.values(), key=lambda x: (x["year"], x["priority"] == "microbial", x["publication_date"], x["title"]), reverse=True)}
    if failures:
        print("Incomplete discovery; keeping the previous snapshot. Failures:", failures)
        return 1
    payload = finalize_inventory(crossref_discovery(payload, config))
    write_json(OUTPUT, payload)
    export_inventory(payload)
    print(f"Discovered {len(payload['candidates'])} unique records; {sum(x['priority'] == 'microbial' for x in payload['candidates'])} provisionally microbial. Window: {since} to {until}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
