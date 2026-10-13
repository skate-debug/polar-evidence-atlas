#!/usr/bin/env python3
"""Verify DOI metadata and export APA 7 references for the seep inventory."""
from __future__ import annotations
import argparse
import html
import json
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from citation_utils import bibliographic_date_parts

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = DATA / "cold_seep_metadata.json"


def load(name, fallback):
    path = DATA / name
    if not path.exists():
        path = DATA / "public" / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def fetch(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "EarthOceanEvidenceAtlas/2.0 (https://github.com/skate-debug/polar-evidence-atlas)"})
            with urllib.request.urlopen(req, timeout=35) as response:
                return doi, json.load(response)["message"], None
        except Exception as exc:
            if attempt == 3:
                return doi, None, str(exc)
            time.sleep(2 * (attempt + 1))


def one(value):
    if isinstance(value, list):
        value = value[0] if value else ""
    value = " ".join(re.sub(r"<[^>]+>", "", html.unescape(str(value or ""))).split())
    return re.sub(r"N\s*2\s*O", "N2O", value)


def sentence_case(title):
    title = one(title)
    protected = ["South China Sea", "Haima", "Jiaolong", "Formosa", "Site F", "Haiyang", "Shenhu", "Qiongdongnan", "Dongsha", "Taiwan", "China", "Gulf of Mexico", "LucaPCycle", "Campylobacterota", "Sulfurovum", "Sulfurimonas", "Gigantidas", "Bathymodiolus", "Archivesica", "Aspergillus", "Penicillium", "Bacillus", "Abyssisolibacter", "Candidatus", "Effluviviacota", "Stenotrophomonas", "Dechloromonas", "Methyloprofundus", "ANME", "SMTZ", "DNA", "RNA", "MAG", "MAGs", "DMSP", "DMS", "N2O", "PFAS", "CO2", "PVC", "SCS", "EPS364", "aCPSF1", "κ", "H2S"]
    protected += ["Natsushima", "Paralepetopsis", "Neolepetopsidae", "Acharax", "Solemyidae", "Solemyida", "Bivalvia", "Lindaspio", "Macellicephaloides", "Uschakov", "Annelida", "Polynoidae", "Mytilus", "Talaromyces", "Alternaria", "Curvularia", "Streptomyces", "Westerdykella", "Neorhizobium", "Fontisubflavum", "Nitrincola", "Marinobacter", "Psychrosphaera", "Salegentibacter", "Aequorivita", "Hwangdonia", "Iocasia", "Lysinibacillus", "Cyphocaris", "Alvinocaris", "Alvinocarididae", "Reniuristis", "Lysianassoidea", "Uristidae", "Amphipoda", "Chrysopetalidae", "Decapoda", "Caridea", "Shinkaia", "Paraescarpia", "Siboglinidae", "Calyptogena", "South Yungan East Ridge"]
    protected += re.findall(r"\b(?:[A-Z]{2,}\d*[- ]\d+(?:[- ]\d+)?|WO2|M8S5|N1-1)\b", title)
    tokens = {}
    for index, term in enumerate(sorted(protected, key=len, reverse=True)):
        pattern = re.compile(r"(?<![A-Za-z])" + re.escape(term) + r"(?![A-Za-z])", re.I)
        token = f"zxq{index}qxz"
        if pattern.search(title):
            title = pattern.sub(token, title)
            tokens[token] = term
    title = title.lower()
    if title:
        title = title[0].upper() + title[1:]
    title = re.sub(r"(:\s+)([a-z])", lambda m: m[1] + m[2].upper(), title)
    for token, term in tokens.items():
        title = re.sub(re.escape(token), term, title, flags=re.I)
    return title


def author_text(author):
    family = author.get("family") or author.get("lastName")
    given = author.get("given") or author.get("firstName") or ""
    if not family:
        return author.get("literal") or author.get("fullName", "")
    initials = " ".join("-".join(piece[0].upper() + "." for piece in part.split("-") if piece) for part in given.split() if part)
    return family + (", " + initials if initials else "")


def reference(item, metadata):
    authors = metadata.get("author") or item.get("author_records", [])
    names = [author_text(author) for author in authors]
    names = [name for name in names if name]
    if len(names) > 20:
        author_line = ", ".join(names[:19]) + ", … " + names[-1]
    elif len(names) > 1:
        author_line = ", ".join(names[:-1]) + ", & " + names[-1]
    else:
        author_line = names[0] if names else item["title"]
    parts = bibliographic_date_parts(metadata)
    year = parts[0] if parts else item["year"]
    title = sentence_case(metadata.get("title") or item["title"])
    journal = one(metadata.get("container-title") or item.get("journal"))
    volume = str(metadata.get("volume") or item.get("volume", ""))
    issue = str(metadata.get("issue") or item.get("issue", ""))
    pages = str(metadata.get("page") or item.get("pages", ""))
    article = metadata.get("article-number", "")
    if item.get("publication_stage") == "preprint":
        detail = "[Preprint]. " + (journal or "Preprint server")
    else:
        detail = f"*{journal}"
        if volume:
            detail += f", {volume}"
        detail += "*"
        if issue:
            detail += f"({issue})"
        if article:
            detail += f", Article {article}"
        elif pages and pages != "Not Available":
            is_article = bool(re.match(r"^[a-z]?\d{5,}$", pages, re.I)) or (bool(re.match(r"^e\d+$", pages, re.I))) or (pages.isdigit() and journal in {"Marine Drugs", "Microorganisms", "Biology", "Molecules", "Genes", "International Journal of Molecular Sciences", "Journal of Fungi"})
            if re.match(r"^\d+-\d+$", pages):
                pages = pages.replace("-", "–")
            detail += f", {'Article ' if is_article else ''}{pages}"
    url = f"https://doi.org/{item['doi']}" if item.get("doi") else item.get("url", "")
    return f"{author_line} ({year}). {title.rstrip('.')}. {detail}. {url}", author_line.lower(), year


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    inventory = load("cold_seep_candidates.json", {"candidates": []})
    cached = load("cold_seep_metadata.json", {"records": {}, "errors": {}})
    records = cached.get("records", {})
    overrides = json.loads((ROOT / "config" / "cold_seep_metadata_overrides.json").read_text(encoding="utf-8"))
    records.update(overrides.get("doi_records", {}))
    active_dois = {item.get("doi") for item in inventory["candidates"] if item.get("doi")}
    records = {doi: record for doi, record in records.items() if doi in active_dois}
    # Use already resolved DOI records when available.
    for item in inventory["candidates"]:
        path = ROOT / ".research-cache" / (re.sub(r"[^a-z0-9]+", "-", item.get("doi", "")) + ".json")
        if path.exists():
            csl = json.loads(path.read_text(encoding="utf-8")).get("csl")
            if csl:
                records.setdefault(item["doi"], csl)
    errors = {doi: error for doi, error in cached.get("errors", {}).items() if doi not in records}
    if args.verify:
        pending = [item["doi"] for item in inventory["candidates"] if item.get("doi") and item["doi"] not in records]
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(fetch, doi): doi for doi in pending}
            for index, future in enumerate(as_completed(futures), 1):
                doi, record, error = future.result()
                if record:
                    records[doi] = record
                else:
                    errors[doi] = error
                if index % 25 == 0:
                    print(f"DOI metadata checks: {index}/{len(pending)}", flush=True)
        payload = {"provider": "Crossref REST API, DOI content negotiation, and explicitly inspected publisher records", "records": dict(sorted(records.items())), "errors": errors}
        OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    entries = [reference(item, records.get(item.get("doi"), {})) for item in inventory["candidates"]]
    lines = ["# South China Sea cold-seep literature: APA 7", "", f"Publication discovery window: {inventory.get('since')} to {inventory.get('until')}. Updated for the 12 October 2026 release.", "", f"{len(entries)} unique inventory records. Bibliographic metadata has been independently retrieved for {sum(item.get('doi') in records for item in inventory['candidates'])} records. Inventory membership does not mean a paper has been full-text reviewed; preprints are labeled explicitly. Scientific claims should be traced to curated evidence profiles or checked directly against the original paper.", ""]
    lines.extend(entry[0] + "\n" for entry in sorted(entries, key=lambda x: (x[1], str(x[2]), x[0])))
    target = ROOT / "references" / "cold-seep-literature-apa7.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    print(f"APA 7 bibliography: {len(entries)} records; {len(records)} DOI metadata records; {len(errors)} lookup error(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
