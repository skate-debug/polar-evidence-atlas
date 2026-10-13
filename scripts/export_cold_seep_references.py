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
GENERA = "Abyssisolibacter Acharax Aequorivita Alternaria Alvinocaris Arcobacter Archivesica Aspergillus Bacillus Bathyacmaea Bathymodiolus Calyptogena Curvularia Cyphocaris Cycloclasticus Dechloromonas Desulfosarcina Enigmaticolus Fontisubflavum Gigantidas Hwangdonia Iocasia Lindaspio Lysinibacillus Macellicephaloides Marinobacter Methanochimaera Methanofollis Methylobacter Methyloprofundus Munidopsis Mytilus Natsushima Neorhizobium Nitrincola Oligobrachia Ophioplinthaca Ophiophthalmus Paraescarpia Paralepetopsis Penicillium Phymorhynchus Psychrosphaera Pyropelta Reniuristis Salegentibacter Sericosura Shinkaia Stenotrophomonas Streptomyces Sulfurimonas Sulfurovum Talaromyces Thermochiton Toxicocladosporium Trichoderma Westerdykella".split()


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
    raw = title[0] if isinstance(title, list) and title else title
    italic_terms = [one(term) for term in re.findall(r"<(?:i|em)>(.*?)</(?:i|em)>", str(raw or ""), re.S)]
    title = one(title)
    for genus in GENERA:
        # Source-reported binomials and a genus followed by "sp." retain italics.
        italic_terms += re.findall(r"\b" + genus + r" [a-z]{3,}\b(?=\s|[,.])", title)
        if re.search(r"\b" + genus + r"\s+sp\.", title):
            italic_terms.append(genus)
    italic_terms = [term for term in italic_terms if not re.search(r"\b(?:gen|species|strains|and|from|with|isolated)$", term)]
    # Inline markup can leave whitespace inside stereochemical identifiers.
    title = re.sub(r"(\d)\s+([RS])\s*[-‐]", r"\1\2-", title)
    protected = ["South China Sea", "Haima", "Jiaolong", "Formosa", "Site F", "Haiyang", "Shenhu", "Qiongdongnan", "Dongsha", "Taiwan", "China", "Gulf of Mexico", "LucaPCycle", "Campylobacterota", "Sulfurovum", "Sulfurimonas", "Gigantidas", "Bathymodiolus", "Archivesica", "Aspergillus", "Penicillium", "Bacillus", "Abyssisolibacter", "Candidatus", "Effluviviacota", "Stenotrophomonas", "Dechloromonas", "Methyloprofundus", "ANME", "SMTZ", "DNA", "RNA", "MAG", "MAGs", "DMSP", "DMS", "N2O", "PFAS", "CO2", "PVC", "SCS", "EPS364", "aCPSF1", "κ", "H2S"]
    protected += ["Natsushima", "Paralepetopsis", "Neolepetopsidae", "Acharax", "Solemyidae", "Solemyida", "Bivalvia", "Lindaspio", "Macellicephaloides", "Uschakov", "Annelida", "Polynoidae", "Mytilus", "Talaromyces", "Alternaria", "Curvularia", "Streptomyces", "Westerdykella", "Neorhizobium", "Fontisubflavum", "Nitrincola", "Marinobacter", "Psychrosphaera", "Salegentibacter", "Aequorivita", "Hwangdonia", "Iocasia", "Lysinibacillus", "Cyphocaris", "Alvinocaris", "Alvinocarididae", "Reniuristis", "Lysianassoidea", "Uristidae", "Amphipoda", "Chrysopetalidae", "Decapoda", "Caridea", "Shinkaia", "Paraescarpia", "Siboglinidae", "Calyptogena", "South Yungan East Ridge"]
    protected += ["Toxicocladosporium", "Trichoderma", "Arcobacter", "Methanochimaera", "Methanofollis", "Heimdallarchaeia", "Asgard", "Phymorhynchus", "Bathyacmaea", "Pyropelta", "Thermochiton", "Munidopsis", "Ophioplinthaca", "Ophiophthalmus", "Enigmaticolus", "PacBio", "16S", "18S", "rRNA", "mRNA", "PFASs", "Raman", "Lingtou Promontory", "Four-Way Closure Ridge", "Okinawa Trough", "Pleistocene", "Holocene", "Quaternary", "Pacific", "CycleGAN", "MeHg", "Hg", "Mg", "Ca", "Ba"]
    # Keep source-reported acronyms, strain identifiers, and chemical labels.
    protected += re.findall(r"\b(?:[A-Z]{2,}[A-Z0-9]*(?:[-‐][A-Z0-9]+)*|[A-Z]\d+[A-Za-z0-9]*|\d+[RS]|M8S5|aCPSF1)\b", title)
    protected += re.findall(r"(?<=\s)[CSN](?=\s|/)", title)
    protected += re.findall(r"(?<=[-–])([A-Z])\b", title)
    protected += re.findall(r"\b(?:fumitremorgin|divergolide|shovelmycin)\s+[A-Z](?:[–-][A-Z])?", title, re.I)
    protected += italic_terms
    protected += GENERA
    protected += ["Gulf of Cadiz", "Gulf of Cádiz", "Gulf of California", "Costa Rica", "Scotian Basin", "Scotian Slope", "Svalbard", "Spitsbergen", "Laptev", "Barents", "Chukchi", "Mediterranean", "Caspian", "Black Sea", "North Sea", "Point Dume", "Monterey Bay", "Guaymas Basin", "Ginsburg", "Hikurangi Margin", "New Zealand", "Krishna-Godavari", "Cauvery-Mannar", "Okinawa", "Northeast Pacific", "Eastern North Pacific", "Atlantic", "Pacific Ocean", "Pacific", "Indian Ocean", "Arctic", "Antarctic", "Southern Ocean", "Congo", "NanoSIMS", "FISH", "eDNA", "nifH", "mcrA", "nifHDK", "ANME-SRB", "SEEP-SRB", "SparCC", "PICRUSt2", "Hola", "LoVe", "Lofoten", "Vesterålen", "Norway", "Methanoliparia", "Argoarchaeum", "Syntrophoarchaeum", "Idas", "Methanoperedens"]
    tokens = {}
    for index, term in enumerate(sorted(protected, key=len, reverse=True)):
        pattern = re.compile(r"(?<![A-Za-z])" + re.escape(term) + r"(?![A-Za-z])", 0 if len(term) == 1 else re.I)
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
    for term in sorted(set(italic_terms), key=len, reverse=True):
        title = re.sub(r"(?<![A-Za-z*])" + re.escape(term) + r"(?![A-Za-z*])", lambda match: "*" + match[0] + "*", title)
    title = re.sub(r"\s+([,;:])", r"\1", title)
    title = re.sub(r"\bCARD\s*[-‐–]\s*FISH\b", "CARD-FISH", title)
    return title


def author_text(author):
    family = author.get("family") or author.get("lastName")
    given = author.get("given") or author.get("firstName") or ""
    if not family:
        return author.get("literal") or author.get("fullName", "")
    if family.isupper():
        family = family.title()
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
    article = str(metadata.get("article-number") or "")
    if article.startswith("10.1128/"):
        article = "e" + article.rsplit(".", 1)[-1]
    if item.get("publication_stage") == "preprint":
        title = "*" + title + "*"
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
            is_article = bool(re.match(r"^[a-z]?\d{5,}$", pages, re.I)) or (bool(re.match(r"^e\d+$", pages, re.I))) or (pages.isdigit() and item.get("doi", "").startswith("10.3390/"))
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
    lines = ["# South China Sea cold-seep literature: APA 7", "", f"Publication discovery window: {inventory.get('since')} to {inventory.get('until')}. Source-review update: 13 October 2026.", "", f"{len(entries)} unique inventory DOI records. Bibliographic metadata has been independently retrieved for {sum(item.get('doi') in records for item in inventory['candidates'])} records. This discovery bibliography also preserves screened background, excluded records, notices and preprints; it is not a count of distinct included studies. Inventory membership does not mean full-text review. Scientific claims should be traced to curated profiles or checked directly against the original paper.", ""]
    lines.extend(entry[0] + "\n" for entry in sorted(entries, key=lambda x: (x[1], str(x[2]), x[0])))
    target = ROOT / "references" / "cold-seep-literature-apa7.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    curated = {item["doi"] for item in sources if item.get("collection") == "scs-cold-seeps"}
    curated_entries = [reference(item, records[item["doi"]]) for item in inventory["candidates"] if item["doi"] in curated]
    curated_lines = ["# Curated South China Sea studies: APA 7 / 南海冷泉精选文献", "", f"{len(curated_entries)} curated source profiles. Evidence access and citation limits are recorded in each profile. / 共 {len(curated_entries)} 篇证据档案，核查材料及引用边界见各档案。", ""]
    curated_lines += [entry[0] + "\n" for entry in sorted(curated_entries, key=lambda x: (x[1], str(x[2]), x[0]))]
    (ROOT / "references/cold-seep-curated-apa7.md").write_text("\n".join(curated_lines), encoding="utf-8")
    print(f"APA 7 bibliography: {len(entries)} records; {len(records)} DOI metadata records; {len(errors)} lookup error(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
