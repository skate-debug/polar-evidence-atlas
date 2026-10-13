#!/usr/bin/env python3
"""Fetch source material for local curation; downloaded text is never published."""
import argparse
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".research-cache"
API = "https://www.ebi.ac.uk/europepmc/webservices/rest"


def fetch(doi, metadata_only=False):
    path = CACHE / (re.sub(r"[^a-z0-9]+", "-", doi.lower()) + ".json")
    if metadata_only:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"doi": doi, "record": {}, "sections": []}
        request = urllib.request.Request(f"https://doi.org/{doi}", headers={"Accept": "application/vnd.citationstyles.csl+json", "User-Agent": "EarthOceanEvidenceAtlas/2.0"})
        with urllib.request.urlopen(request, timeout=45) as response:
            payload["csl"] = json.load(response)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return doi, str(payload["csl"].get("title", "")), len(payload["sections"])
    params = urllib.parse.urlencode({"query": f'DOI:"{doi}"', "format": "json", "resultType": "core"})
    with urllib.request.urlopen(f"{API}/search?{params}", timeout=40) as response:
        matches = json.load(response).get("resultList", {}).get("result", [])
    record = next((x for x in matches if x.get("doi", "").lower() == doi.lower()), {})
    sections = []
    if record.get("pmcid"):
        try:
            with urllib.request.urlopen(f"{API}/{record['pmcid']}/fullTextXML", timeout=40) as response:
                xml = ET.fromstring(response.read())
            for sec in xml.findall(".//body//sec"):
                title = " ".join(sec.findtext("title", "").split())
                paragraphs = [" ".join("".join(p.itertext()).split()) for p in sec.findall("p")]
                if paragraphs:
                    sections.append({"section": title, "paragraphs": paragraphs})
        except Exception as exc:
            record["full_text_error"] = str(exc)
    payload = {"doi": doi, "record": record, "sections": sections}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doi, record.get("title", ""), len(sections)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("doi", nargs="*")
    parser.add_argument("--list", dest="list_path")
    parser.add_argument("--metadata", action="store_true")
    args = parser.parse_args()
    dois = args.doi
    if args.list_path:
        dois += json.loads(Path(args.list_path).read_text(encoding="utf-8"))
    CACHE.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch, doi, args.metadata): doi for doi in dois}
        for future in as_completed(futures):
            try:
                doi, title, sections = future.result()
                print(f"{doi}: {sections} accessible body sections; {title}", flush=True)
            except Exception as exc:
                print(f"ERROR {futures[future]}: {exc}", flush=True)


if __name__ == "__main__":
    main()
