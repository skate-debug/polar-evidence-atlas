#!/usr/bin/env python3
"""Materialize explicitly reviewed bilingual evidence packets and queue decisions.

Discovery never creates packets. Every packet in config/cold_seep_reviewed.json
contains editorial extraction from a read source. Existing source IDs are kept.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

from add_cold_seep_seed import HABITATS, SITE_REGION
from citation_utils import bibliographic_date_parts
from export_cold_seep_references import one
from update_zh_translations import claim_payload, source_payload, concept_payload, digest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHECKED = "2026-10-13"
HABITATS.update({"unspecified": "habitat:cold-seep", "organic-substrate": "habitat:seep-organic-substrate"})
EXTRA_CONCEPTS = [
    ["method:isolate-genome-sequencing", "Method", "Isolate genome sequencing", "分离株基因组测序", "Genome sequencing of a cultured microbial isolate.", "对培养分离的微生物进行基因组测序。"],
    ["method:host-transcriptomics", "Method", "Host transcriptomics", "宿主转录组学", "RNA profiling of the animal host; distinct from environmental metatranscriptomics.", "动物宿主 RNA 分析，与环境宏转录组相区分。"],
    ["method:natural-product-analysis", "Method", "Natural-product structural analysis", "天然产物结构分析", "Isolation and chemical characterization of microbial metabolites.", "微生物代谢物的分离及化学结构鉴定。"],
    ["method:biochemical-assay", "Method", "Biochemical and bioactivity assays", "生化与生物活性实验", "Defined-substrate, enzyme, or cell-assay measurements; scope follows the cited experiment.", "明确底物、酶或细胞实验的测量，适用范围以原文为准。"],
    ["process:methanogenesis", "Process", "Methanogenesis", "产甲烷作用", "Microbial methane production; substrate pathways and experimental support remain source-specific.", "微生物产生甲烷的过程；底物途径与实验支持以各文献为准。"],
    ["habitat:seep-organic-substrate", "Habitat", "Seep-associated wood and organic substrates", "冷泉相关沉木与有机基质", "Wood or other organic material sampled in a seep setting, distinct from host tissue or sediment.", "冷泉环境采集的沉木等有机物，与宿主组织及沉积物区分。"],
]


def read(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="replace only the explicit reviewed packet IDs")
    args = parser.parse_args()
    packets = read(ROOT / "config/cold_seep_reviewed.json", [])
    decisions = read(ROOT / "config/cold_seep_review_decisions.json", [])
    sources, claims = read(DATA / "sources.json"), read(DATA / "claims.json")
    inventory = read(DATA / "cold_seep_candidates.json", read(DATA / "public/cold_seep_candidates.json"))
    candidates = {item["doi"]: item for item in inventory["candidates"]}
    metadata = read(DATA / "metadata.json", read(DATA / "public/metadata.json"))
    checked = read(DATA / "cold_seep_metadata.json", read(DATA / "public/cold_seep_metadata.json"))["records"]
    translations = read(DATA / "i18n.zh-CN.json")
    concepts = read(DATA / "concepts.json")
    known_concepts = {item["id"] for item in concepts}
    for cid, kind, label, zh, description, description_zh in EXTRA_CONCEPTS:
        concept = {"id": cid, "type": kind, "label": label, "description": description}
        if cid not in known_concepts:
            concepts.append(concept)
        translations["concepts"][cid] = {"label": zh, "description": description_zh, "_source_hash": digest(concept_payload(concept))}
    ledger = read(DATA / "cold_seep_reviews.json", {"reviews": []})
    reviews = {item["doi"]: item for item in ledger["reviews"]}
    if len({item["doi"] for item in packets}) != len(packets):
        raise SystemExit("Duplicate DOI in reviewed packets")
    if args.refresh:
        ids = {"src:scs-" + item["slug"] for item in packets}
        claim_ids = {"claim:scs-" + item["slug"] for item in packets}
        sources = [item for item in sources if item["id"] not in ids]
        claims = [item for item in claims if item["id"] not in claim_ids]
    by_doi = {item["doi"]: item for item in sources}
    for packet in packets:
        doi = packet["doi"]
        if doi not in candidates or doi not in checked:
            raise SystemExit(f"Missing inventory or independently resolved metadata: {doi}")
        candidate, record = candidates[doi], checked[doi]
        cache = read(ROOT / ".research-cache" / (re.sub(r"[^a-z0-9]+", "-", doi) + ".json"), {})
        abstract = cache.get("record", {}).get("abstractText") or candidate.get("abstract") or record.get("abstract", "")
        access = packet.get("access", "abstract")
        if not abstract and not packet.get("evidence_url"):
            raise SystemExit(f"No inspected source material: {doi}")
        if "full_text" in access and not cache.get("sections") and not packet.get("evidence_url"):
            raise SystemExit(f"Missing full-text evidence: {doi}")
        title = one(record.get("title") or candidate["title"])
        year = int(bibliographic_date_parts(record)[0])
        sid, cid = "src:scs-" + packet["slug"], "claim:scs-" + packet["slug"]
        scope, design, finding, limit = (packet[key] for key in ("scope", "design", "finding", "limit"))
        temporal = packet.get("time", ["Sampling date not specified in the inspected abstract.", "所核查摘要未说明采样日期。"])
        locator = packet.get("locator", ["Abstract: study design and principal results.", "摘要：研究设计与主要结果。"])
        source_url = packet.get("evidence_url") or (f"https://europepmc.org/article/MED/{candidate['pmid']}" if candidate.get("pmid") else "https://doi.org/" + doi)
        basis = "DOI bibliographic metadata and source passage inspected; " + ("abstract-scoped evidence only." if access == "abstract" else "specific full-text sections listed in the claim locator.")
        basis_zh = "已核查 DOI 出版信息及支持论断的原文；" + ("本档案仅依据公开摘要。" if access == "abstract" else "全文核查范围见论断中的证据位置。")
        source = {
            "id": sid, "citation_key": "SCS" + "".join(word.title() for word in packet["slug"].split("-")),
            "doi": doi, "title": title, "year": year, "poles": [], "collection": "scs-cold-seeps",
            "regions": ["region:south-china-sea"] + [SITE_REGION[site] for site in packet["sites"] if site in SITE_REGION],
            "compartments": packet["compartments"], "topics": packet["topics"], "sites": packet["sites"],
            "domains": packet.get("domains", ["Cold-seep prokaryotes", "Cold-seep biogeochemistry"]),
            "study_type": packet["type"][0],
            "study_profile": {"spatial_scope": scope[0], "temporal_scope": temporal[0], "sample_design": design[0],
                "habitats": [HABITATS[value] for value in packet["compartments"]],
                "methods": ["method:" + value for value in packet["methods"]],
                "measured_or_derived": [value[0] for value in packet["variables"]],
                "focal_taxa": packet.get("taxa", []), "focal_processes": ["process:" + value for value in packet.get("processes", [])],
                "environmental_drivers": []},
            "key_findings": [finding[0]], "limitations": [limit[0]],
            "cite_for": [packet["type"][0] + " within the stated study scope.", finding[0]],
            "do_not_overcite": [limit[0]], "data_accessions": packet.get("accessions", []),
            "curation": {"status": "curated", "basis": basis, "last_verified": CHECKED, "access_level": access,
                "evidence_url": source_url, "review_packet": "config/cold_seep_reviewed.json"},
        }
        claim = {"id": cid, "source_id": sid, "subject": sid,
            "predicate": packet.get("predicate", "associated_with"), "object": packet["object"],
            "statement": finding[0], "scope": scope[0], "evidence_type": packet["evidence_type"],
            "evidence_basis": design[0], "locator": locator[0], "confidence": "moderate", "confidence_note": limit[0]}
        if doi in by_doi:
            if by_doi[doi]["id"] != sid:
                raise SystemExit(f"DOI already curated under a different ID: {doi}")
            source = by_doi[doi]
            claim = next(item for item in claims if item["id"] == cid)
        else:
            sources.append(source)
            claims.append(claim)
            by_doi[doi] = source
        metadata["records"][doi] = record
        translations["sources"][sid] = {
            "title": packet["title_zh"], "study_type": packet["type"][1],
            "study_profile": {"spatial_scope": scope[1], "temporal_scope": temporal[1], "sample_design": design[1],
                "measured_or_derived": [value[1] for value in packet["variables"]]},
            "key_findings": [finding[1]], "limitations": [limit[1]],
            "cite_for": [packet["type"][1] + "，适用范围以采样设计为准。", finding[1]],
            "do_not_overcite": [limit[1]], "curation_basis": basis_zh, "_source_hash": digest(source_payload(source)),
        }
        translations["claims"][cid] = {"statement": finding[1], "scope": scope[1], "evidence_basis": design[1],
            "locator": locator[1], "confidence_note": limit[1], "_source_hash": digest(claim_payload(claim))}
        reviews[doi] = {"doi": doi, "candidate_id": candidate["id"], "status": "curated", "reviewed_at": CHECKED,
            "source_id": sid, "access_level": access, "evidence_url": source_url, "locator": locator[0],
            "metadata_status": "verified", "support_status": "supported_after_narrowing",
            "reason": "Source-scoped evidence profile and claim added; see the specific study limitation.",
            "reason_zh": "已建立与原文范围一致的证据档案和论断；使用时请参阅研究局限。",
            "next_action": "Inspect full Methods, results and supplements before extracting finer quantitative claims." if access == "abstract" else "Extend with additional section- or figure-specific claims as needed.",
            "inspected_abstract_sha256": hashlib.sha256(abstract.encode()).hexdigest() if abstract else None}
    for item in decisions:
        if item["doi"] in by_doi:
            raise SystemExit(f"Non-curated decision overlaps curated source: {item['doi']}")
        reviews[item["doi"]] = {**item, "candidate_id": candidates[item["doi"]]["id"], "reviewed_at": CHECKED}
    # Preserve the earlier release's reviewed profiles, without claiming a new read.
    for source in sources:
        if source.get("collection") == "scs-cold-seeps" and source["doi"] not in reviews:
            doi = source["doi"]
            reviews[doi] = {"doi": doi, "candidate_id": candidates[doi]["id"], "source_id": source["id"],
                "status": "curated", "reviewed_at": source["curation"]["last_verified"],
                "access_level": source["curation"].get("access_level", "abstract"), "metadata_status": "verified",
                "evidence_url": "https://doi.org/" + doi, "support_status": "supported_after_narrowing",
                "reason": "Reviewed source profile retained from the initial SCS release.", "reason_zh": "保留南海冷泉首版中已核查的证据档案。"}
    write(DATA / "sources.json", sources)
    write(DATA / "claims.json", claims)
    write(DATA / "concepts.json", concepts)
    write(DATA / "metadata.json", metadata)
    write(DATA / "i18n.zh-CN.json", translations)
    write(DATA / "cold_seep_reviews.json", {"schema_version": "1.0", "updated_at": CHECKED,
        "policy": "Editorial source-review decisions persist independently of discovery; abstract review is not full-text review.",
        "reviews": sorted(reviews.values(), key=lambda item: item["doi"])})
    print(f"Materialized {len(packets)} reviewed packets; {len(sources)} total sources, {len(claims)} claims, {len(reviews)} queue decisions.")


if __name__ == "__main__":
    main()
