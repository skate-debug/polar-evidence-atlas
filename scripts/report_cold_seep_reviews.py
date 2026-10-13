#!/usr/bin/env python3
"""Export the persistent SCS queue ledger and bilingual citation-ready profiles."""
from __future__ import annotations
import csv
import json
from collections import Counter
from pathlib import Path
from export_cold_seep_references import reference

ROOT = Path(__file__).resolve().parents[1]
DATA, DIST = ROOT / "data", ROOT / "dist"
LABELS = {
    "curated": "Curated evidence / 已建立证据档案",
    "awaiting_source_review": "Awaiting source review / 待核查原文",
    "awaiting_source_text": "Source text needed / 需获取支持性原文",
    "screened_context": "Screened context / 已初筛背景文献",
    "excluded": "Excluded / 已排除",
    "linked_notice": "Linked correction / 已关联勘误",
    "version_check": "Publication version check / 需核查发表版本",
}


def load(name, default=None):
    path = DATA / name
    if not path.exists():
        path = DATA / "public" / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def main():
    inventory = load("cold_seep_candidates.json")
    reviews = {item["doi"]: item for item in load("cold_seep_reviews.json", {"reviews": []})["reviews"]}
    sources = [source for source in load("sources.json") if source.get("collection") == "scs-cold-seeps"]
    by_doi = {source["doi"]: source for source in sources}
    metadata = load("cold_seep_metadata.json")["records"]
    zh = load("i18n.zh-CN.json")["sources"]
    claims = load("claims.json")
    claim_zh = load("i18n.zh-CN.json")["claims"]
    concepts = {item["id"]: item for item in load("concepts.json")}
    concept_zh = load("i18n.zh-CN.json")["concepts"]
    rows = []
    for paper in inventory["candidates"]:
        review = reviews.get(paper["doi"], {})
        rows.append({"doi": paper["doi"], "title": paper["title"], "year": paper["year"],
            "status": "curated" if paper["doi"] in by_doi else review.get("status", "awaiting_source_review"),
            **{key: review.get(key, "") for key in ("access_level", "reviewed_at", "metadata_status", "source_id", "evidence_url", "locator", "reason", "reason_zh", "next_action")}})
    counts = Counter(row["status"] for row in rows)
    access = Counter("full_text_extracts" if "full_text" in source["curation"].get("access_level", "") else "abstract" for source in sources)
    DIST.mkdir(exist_ok=True)
    with (DIST / "cold-seep-review.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# South China Sea source-review ledger / 南海冷泉原文核查记录", "",
        f"Publication window / 发表时间范围：{inventory['since']}–{inventory['until']}.", "",
        f"{len(rows)} inventory DOI records; {len(sources)} curated profiles. DOI records are not necessarily distinct studies: notices and retained preprints are counted separately.", "",
        "DOI 记录数不等于独立研究数：勘误及保留的预印本单独计数。原文初筛、摘要证据提取与全文核查分别记录，背景初筛不产生图谱论断。", "",
        "| Review stage / 核查阶段 | Records / 记录数 |", "| --- | ---: |"]
    lines += [f"| {label} | {counts[status]} |" for status, label in LABELS.items()]
    lines += ["", f"Curated access / 精选档案核查材料：{access['abstract']} abstract-scoped / 限于摘要；{access['full_text_extracts']} inspected full-text excerpts / 已核查相关全文段落。", "",
        "A full-text-excerpt label identifies the sections actually inspected; it does not claim that every figure or supplement was reviewed. Abstract-scoped packets must be narrowed to explicit abstract findings. Neither DOI verification nor title screening is treated as claim verification.", "",
        "“全文段落”仅表示记录的相关部分已核查，并不代表全部图表或补充材料均已检查。摘要档案仅保留摘要明确支持的结论。出版信息核查或标题初筛不能替代论断证据核查。", "",
        "## Review queue / 核查队列", ""]
    for status in LABELS:
        if status == "curated":
            continue
        lines += ["### " + LABELS[status], ""]
        for row in rows:
            if row["status"] != status:
                continue
            lines += [f"- [{row['title']}](https://doi.org/{row['doi']}) ({row['year']}). {row['reason'] or 'No editorial source decision yet.'} {row['reason_zh']}",
                f"  Next action: {row['next_action'] or 'Inspect the source, record scope and extract supported findings.'}"]
        lines += [""]
    lines += ["## Version provenance / 版本来源", "",
        "Collapsed records remain in discovery provenance and are not counted as independent active queue entries. / 合并版本保留发现来源，不计作独立的当前队列记录。", ""]
    for item in inventory.get("collapsed_versions", []):
        lines += [f"- [{item['doi']}](https://doi.org/{item['doi']}) → [{item['published_doi']}](https://doi.org/{item['published_doi']}); {item['basis']}."]
    (DIST / "cold-seep-review-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    profiles = ["# Curated South China Sea evidence profiles / 南海冷泉精选证据档案", "",
        "Original paraphrases; cite the primary study for scientific statements. Chinese is a reading translation; published bibliographic titles remain canonical.", "",
        "以下为原始概括，科学论断请引用对应原文。中文为阅读译文，正式文献标题保留出版语言。", ""]
    candidates = {item["doi"]: item for item in inventory["candidates"]}
    for source in sorted(sources, key=lambda item: (-item["year"], item["title"])):
        translated = zh[source["id"]]
        citation = reference(candidates[source["doi"]], metadata[source["doi"]])[0]
        profile, profile_zh = source["study_profile"], translated["study_profile"]
        profiles += ["## " + source["title"], "", translated["title"], "", citation, ""]
        for label, value, value_zh in (
            ("Design / 研究设计", profile["sample_design"], profile_zh["sample_design"]),
            ("Sampling scope / 采样范围", profile["spatial_scope"], profile_zh["spatial_scope"]),
            ("Time / 时间", profile["temporal_scope"], profile_zh["temporal_scope"]),
            ("Methods / 方法", "; ".join(concepts[mid]["label"] for mid in profile["methods"]), "；".join(concept_zh[mid]["label"] for mid in profile["methods"])),
            ("Measured or derived / 测量或推导指标", "; ".join(profile["measured_or_derived"]), "；".join(profile_zh["measured_or_derived"])),
            ("Findings / 发现", " ".join(source["key_findings"]), " ".join(translated["key_findings"])),
            ("Citation limits / 引用边界", " ".join(source["limitations"]), " ".join(translated["limitations"])),
        ):
            profiles += [f"**{label}**: {value}", "", value_zh, ""]
        review = reviews.get(source["doi"], {})
        access_label = "inspected full-text excerpts / 已核查相关全文段落" if "full_text" in source["curation"].get("access_level", "") else "abstract-scoped / 限于摘要"
        profiles += [f"Evidence access / 核查材料：{access_label}; verified / 核查日期：{source['curation']['last_verified']}.", ""]
        for claim in (item for item in claims if item["source_id"] == source["id"]):
            profiles += [f"Evidence locator / 证据位置：{claim['locator']}", "", claim_zh[claim["id"]]["locator"], ""]
        evidence_url = review.get("evidence_url") or source["curation"].get("evidence_url")
        if evidence_url:
            profiles += [f"[Inspected source / 核查来源]({evidence_url}) · `{source['id']}`", ""]
        if source.get("data_accessions"):
            profiles += ["Data accessions / 数据登录号：" + ", ".join(source["data_accessions"]), ""]
    (DIST / "cold-seep-evidence-profiles.md").write_text("\n".join(profiles).rstrip() + "\n", encoding="utf-8")
    print(f"SCS review: {len(rows)} DOI records; " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))


if __name__ == "__main__":
    main()
