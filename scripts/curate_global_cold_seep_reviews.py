#!/usr/bin/env python3
"""Materialize explicit international seep evidence; reuse existing DOI profiles."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from datetime import date
from citation_utils import bibliographic_date_parts
from export_cold_seep_references import one
from curate_cold_seep_reviews import HABITATS
from update_zh_translations import claim_payload, source_payload, concept_payload, digest
from update_global_cold_seep_candidates import load, export_inventory
from update_cold_seep_candidates import write_json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHECKED = "2026-10-13"
METHODS = [
    ("machine-learning", "Machine-learning prediction and validation", "机器学习预测与验证", "Statistical learning models with study-specific training and external validation."),
    ("fluorescence-in-situ-hybridization", "Fluorescence in situ hybridization (FISH)", "荧光原位杂交（FISH）", "Probe-based visualization of identified cells or transcripts, including CARD- and HCR-FISH variants."),
    ("nanosims", "Nanoscale secondary ion mass spectrometry (NanoSIMS)", "纳米二次离子质谱（NanoSIMS）", "Cell- or material-specific isotope measurements; incubation and labeling conditions remain source-specific."),
    ("lipid-biomarker-analysis", "Lipid biomarker analysis", "脂质生物标志物分析", "Lipid composition and isotope proxies for community or metabolic interpretation."),
    ("hydrodynamic-modeling", "Hydrodynamic transport modeling", "水动力输运模拟", "Physical transport and mixing simulations constrained by study-specific observations."),
    ("metabolomics", "Metabolomics", "代谢组学", "Chemical profiling of community metabolites; detection does not by itself assign production to a specific organism."),
    ("metaproteomics", "Metaproteomics", "宏蛋白组学", "Community protein identification linked to genome or pathway annotations; expression and process rates remain distinct."),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="revise only generated global packet profiles and claims")
    parser.add_argument("--review-date", help="verification date for newly inspected packets; existing dates are preserved unless a packet explicitly changes reviewed_at")
    args = parser.parse_args()
    if args.review_date:
        date.fromisoformat(args.review_date)
    packets = json.loads((ROOT / "config/global_cold_seep_reviewed.json").read_text())
    if len({packet['doi'] for packet in packets}) != len(packets):
        raise SystemExit("Duplicate DOI in global packets")
    sources, claims, concepts = (load(name + ".json", []) for name in ("sources", "claims", "concepts"))
    translations, metadata = load("i18n.zh-CN.json", {}), load("metadata.json", {"records": {}})
    inventory = load("global_cold_seep_candidates.json", {"candidates": []})
    archive = load("global_cold_seep_archive.json", {"candidates": []})
    checked = load("global_cold_seep_metadata.json", {"records": {}})["records"]
    candidates = {item["doi"]: item for item in archive["candidates"] + inventory["candidates"]}
    taxonomy = json.loads((ROOT / "config/collections.json").read_text())
    known = {item["id"] for item in concepts}
    for slug, label, label_zh, description in METHODS:
        concept = {"id": "method:" + slug, "type": "Method", "label": label, "description": description}
        if concept["id"] not in known:
            concepts.append(concept)
            known.add(concept["id"])
            translations["concepts"][concept["id"]] = {"label": label_zh, "description": label_zh + "，实验与分析适用范围以对应原文为准。", "_source_hash": digest(concept_payload(concept))}
    site_regions = {}
    for entry in taxonomy["sites"]:
        if not entry.get("concept_id"):
            continue
        site_regions[entry["id"]] = entry["concept_id"]
        concept = {"id": entry["concept_id"], "type": "Region", "label": entry["label"], "description": "Named comparison area; exact stations and sample scope follow each source."}
        if concept["id"] not in known:
            concepts.append(concept)
            known.add(concept["id"])
            translations["concepts"][concept["id"]] = {"label": entry["zh"], "description": "具名比较区域；具体站位及样品范围以各文献为准。", "_source_hash": digest(concept_payload(concept))}
    terrestrial = {"id": "habitat:terrestrial-methane-seep", "type": "Habitat", "label": "Terrestrial methane seep water and ice", "description": "Groundwater or ice at a terrestrial methane seep; a contextual comparison to marine cold seeps."}
    if terrestrial["id"] not in known:
        concepts.append(terrestrial)
        translations["concepts"][terrestrial["id"]] = {"label": "陆地甲烷渗漏水与冰", "description": "陆地甲烷渗漏地下水或冰，作为海洋冷泉的背景比较。", "_source_hash": digest(concept_payload(terrestrial))}
    HABITATS["terrestrial-seep"] = terrestrial["id"]
    if args.refresh:
        new_source_ids = {"src:gcs-" + packet["slug"] for packet in packets if not packet.get("existing_source_id")}
        new_claim_ids = {"claim:gcs-" + packet["slug"] for packet in packets}
        sources = [item for item in sources if item["id"] not in new_source_ids]
        claims = [item for item in claims if item["id"] not in new_claim_ids]
    by_doi = {source["doi"]: source for source in sources}
    claim_ids = {claim["id"] for claim in claims}
    old_reviews = {item["doi"]: item for item in load("global_cold_seep_reviews.json", {"reviews": []})["reviews"]}
    for packet in packets:
        doi = packet["doi"]
        review_date = packet.get("reviewed_at") or old_reviews.get(doi, {}).get("reviewed_at") or args.review_date or CHECKED
        if doi not in candidates or doi not in checked:
            raise SystemExit(f"Missing international inventory or independent DOI metadata: {doi}")
        candidate, record = candidates[doi], checked[doi]
        cache_path = ROOT / ".research-cache" / (re.sub(r"[^a-z0-9]+", "-", doi) + ".json")
        cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        abstract = cache.get("record", {}).get("abstractText") or candidate.get("abstract") or record.get("abstract")
        access = packet.get("access", "abstract")
        if not abstract and not packet.get("evidence_url"):
            raise SystemExit(f"No inspected supporting source: {doi}")
        if "full_text" in access and not cache.get("sections") and not packet.get("evidence_url"):
            raise SystemExit(f"No full-text supporting passages: {doi}")
        sid, cid = packet.get("existing_source_id") or "src:gcs-" + packet["slug"], "claim:gcs-" + packet["slug"]
        if doi in by_doi and by_doi[doi]["id"] != sid:
            raise SystemExit(f"Reuse the existing source ID for duplicate DOI: {doi}")
        scope, design, finding, limit = (packet[key] for key in ("scope", "design", "finding", "limit"))
        methods = list(packet["methods"])
        # Normalize method features already present in the editorial design.
        for pattern, slug in ((r"FISH", "fluorescence-in-situ-hybridization"), (r"NanoSIMS", "nanosims"), (r"lipid", "lipid-biomarker-analysis"), (r"hydrodynamic|ROMS|Gerris", "hydrodynamic-modeling")):
            if re.search(pattern, design[0], re.I) and slug not in methods:
                methods.append(slug)
        temporal = packet.get("time", ["Sampling date not extracted from the inspected material.", "所核查材料未提取采样日期。"])
        locator = packet.get("locator", ["Abstract: design and primary findings.", "摘要：研究设计与主要发现。"])
        source_url = packet.get("evidence_url") or ("https://europepmc.org/article/MED/" + candidate["pmid"] if candidate.get("pmid") else "https://doi.org/" + doi)
        basis = "International comparison source inspected; " + ("abstract-scoped findings only." if "full_text" not in access else "only the full-text sections in the claim locator were inspected.")
        basis_zh = "已核查国际比较文献；" + ("发现限于摘要支持的范围。" if "full_text" not in access else "仅核查论断证据位置记录的相关全文段落。")
        source = {"id": sid, "citation_key": "GCS" + "".join(word.title() for word in packet["slug"].split("-")), "doi": doi,
            "title": one(record.get("title") or candidate["title"]), "year": int(bibliographic_date_parts(record)[0]),
            "poles": [], "collection": "global-cold-seeps", "regions": list(dict.fromkeys(site_regions[site] for site in packet["sites"])),
            "compartments": packet["compartments"], "topics": packet["topics"], "sites": packet["sites"],
            "domains": packet.get("domains", ["Cold-seep prokaryotes", "Cold-seep biogeochemistry"]), "study_type": packet["type"][0],
            "study_profile": {"spatial_scope": scope[0], "temporal_scope": temporal[0], "sample_design": design[0], "habitats": [HABITATS[value] for value in packet["compartments"]],
                "methods": ["method:" + value for value in methods], "measured_or_derived": [value[0] for value in packet["variables"]],
                "focal_taxa": packet.get("taxa", []), "focal_processes": ["process:" + value for value in packet.get("processes", [])], "environmental_drivers": []},
            "key_findings": [finding[0]], "limitations": [limit[0]], "cite_for": [packet["discussion"][0], finding[0]], "do_not_overcite": [limit[0]], "data_accessions": packet.get("accessions", []),
            "curation": {"status": "curated", "basis": basis, "access_level": access, "last_verified": review_date, "evidence_url": source_url, "review_packet": "config/global_cold_seep_reviewed.json"}}
        if doi not in by_doi:
            sources.append(source)
            by_doi[doi] = source
            translations["sources"][sid] = {"title": packet["title_zh"], "study_type": packet["type"][1],
                "study_profile": {"spatial_scope": scope[1], "temporal_scope": temporal[1], "sample_design": design[1], "measured_or_derived": [value[1] for value in packet["variables"]]},
                "key_findings": [finding[1]], "limitations": [limit[1]], "cite_for": [packet["discussion"][1], finding[1]], "do_not_overcite": [limit[1]], "curation_basis": basis_zh, "_source_hash": digest(source_payload(source))}
        claim = {"id": cid, "source_id": sid, "subject": sid, "predicate": packet.get("predicate", "associated_with"), "object": packet["object"],
            "statement": finding[0], "scope": scope[0], "evidence_type": packet["evidence_type"], "evidence_basis": design[0], "locator": locator[0], "confidence": "moderate", "confidence_note": limit[0]}
        if cid not in claim_ids and not packet.get("existing_source_id"):
            claims.append(claim)
            translations["claims"][cid] = {"statement": finding[1], "scope": scope[1], "evidence_basis": design[1], "locator": locator[1], "confidence_note": limit[1], "_source_hash": digest(claim_payload(claim))}
        metadata["records"][doi] = record
        old_reviews[doi] = {"doi": doi, "candidate_id": candidate["id"], "source_id": sid, "status": "curated", "reviewed_at": review_date,
            "metadata_status": "verified", "support_status": "supported_after_narrowing", "access_level": access, "evidence_url": source_url, "locator": locator[0],
            "reason": packet["discussion"][0], "reason_zh": packet["discussion"][1], "next_action": "Inspect complete Methods and supplements before extracting further quantitative comparisons." if "full_text" not in access else "Add further figure-specific comparisons when relevant.",
            "compartments": packet["compartments"], "topics": packet["topics"], "sites": packet["sites"],
            "comparison_role": packet.get("comparison_role", "regional_comparison"), "inspected_abstract_sha256": hashlib.sha256(str(abstract).encode()).hexdigest() if abstract else None}
    for item in inventory["candidates"]:
        review = old_reviews.get(item["doi"])
        if review and review["status"] == "curated":
            for field in ("compartments", "topics", "sites"):
                item[field] = review[field]
            item["classification_basis"] = "Explicit inspected international comparison packet"
            continue
        if re.match(r"^(WITHDRAWN|RETRACTED)\b", item["title"], re.I):
            old_reviews[item["doi"]] = {"doi": item["doi"], "candidate_id": item["id"], "status": "excluded", "access_level": "metadata_only", "metadata_status": "verified", "support_status": "unresolved",
                "reason": "The publisher/depository title explicitly marks this record withdrawn or retracted; it supplies no graph evidence.", "reason_zh": "出版方／预印本库标题明确标记为撤回或撤稿，该记录不提供图谱证据。", "next_action": "Check the withdrawal notice and any formally linked successor before future reconsideration."}
            continue
        if item["publication_stage"] == "preprint" and (not review or review['status'] == 'awaiting_source_review'):
            old_reviews[item["doi"]] = {"doi": item["doi"], "candidate_id": item["id"], "status": "version_check", "access_level": "metadata_only", "metadata_status": "verified", "support_status": "unresolved",
                "reason": "Preprint status identified in DOI metadata; the source and any peer-reviewed successor still require review.", "reason_zh": "DOI 出版信息识别为预印本；原文及可能的同行评议后续版本仍待核查。", "next_action": "Resolve official version relations, confirm sample scope and inspect supported findings before promotion."}
            continue
        old_reviews.setdefault(item["doi"], {"doi": item["doi"], "candidate_id": item["id"], "status": "awaiting_source_review", "access_level": "unreviewed",
            "metadata_status": "verified" if item["doi"] in checked else "unresolved", "support_status": "unresolved", "reason": "Discovered comparison candidate; sample geography and scientific claim support await editorial inspection.",
            "reason_zh": "发现的比较候选文献；采样地域与科学论断支持范围待人工核查。", "next_action": "Read source material, confirm non-SCS sampling, record design and extract a supported comparison."})
    for name, value in (("sources", sources), ("claims", claims), ("concepts", concepts), ("i18n.zh-CN", translations), ("metadata", metadata), ("global_cold_seep_candidates", inventory)):
        write_json(DATA / (name + ".json"), value)
    write_json(DATA / "global_cold_seep_reviews.json", {"schema_version": "1.0", "updated_at": args.review_date or CHECKED, "policy": "International discussion comparisons; sources shared with other collections are reused by DOI, never duplicated.", "reviews": sorted(old_reviews.values(), key=lambda item: item["doi"])})
    export_inventory(inventory)
    print(f"International packets: {len(packets)}; total unique sources={len(sources)}, claims={len(claims)}")


if __name__ == "__main__":
    main()
