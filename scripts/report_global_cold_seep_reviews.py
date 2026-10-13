#!/usr/bin/env python3
"""Export international comparison profiles, APA references, and review status."""
from __future__ import annotations
import csv
import json
from collections import Counter
from pathlib import Path
from export_cold_seep_references import reference
from update_global_cold_seep_candidates import load, export_inventory

ROOT = Path(__file__).resolve().parents[1]


def main():
    inventory = load("global_cold_seep_candidates.json", {"candidates": []})
    archive = load("global_cold_seep_archive.json", {"candidates": []})
    metadata = load("global_cold_seep_metadata.json", {"records": {}})["records"]
    reviews = {item["doi"]: item for item in load("global_cold_seep_reviews.json", {"reviews": []})["reviews"]}
    packets = json.loads((ROOT / "config/global_cold_seep_reviewed.json").read_text())
    sources = {item["doi"]: item for item in load("sources.json", [])}
    candidates = {item["doi"]: item for item in archive["candidates"] + inventory["candidates"]}
    active_count = len(inventory["candidates"])
    export_inventory(inventory)
    refs = [reference(item, metadata.get(item["doi"], {})) for item in inventory["candidates"]]
    refs.sort(key=lambda item: (item[1], str(item[2]), item[0]))
    full = ["# International cold-seep inventory: APA 7 / 国际冷泉目录参考文献", "", f"Discovery window: {inventory['since']}–{inventory['until']}; {len(refs)} DOI records.", "",
        "Discovery records include unreviewed candidates and retained preprints. Use the curated bibliography for extracted evidence. / 发现记录包括未核查候选及保留的预印本。已提取证据请使用精选参考文献。", ""]
    full.extend(item[0] + "\n" for item in refs)
    (ROOT / "references/global-cold-seep-literature-apa7.md").write_text("\n".join(full), encoding="utf-8")
    curated_refs = [reference(candidates[packet["doi"]], metadata[packet["doi"]]) for packet in packets]
    curated_refs.sort(key=lambda item: (item[1], str(item[2]), item[0]))
    shared = sum(bool(packet.get("existing_source_id")) for packet in packets)
    curated = ["# International discussion studies: APA 7 / 国际冷泉讨论精选文献", "", f"{len(packets)} inspected comparison profiles; {shared} reuse existing atlas sources by DOI. / 共 {len(packets)} 篇已核查比较档案，{shared} 篇按 DOI 复用已有来源。", ""]
    curated.extend(item[0] + "\n" for item in curated_refs)
    (ROOT / "references/global-cold-seep-curated-apa7.md").write_text("\n".join(curated), encoding="utf-8")
    counts = Counter(reviews.get(item["doi"], {}).get("status", "awaiting_source_review") for item in inventory["candidates"])
    access = Counter("full_text_extracts" if "full_text" in packet.get("access", "abstract") else "abstract" for packet in packets)
    summary = ["# International seep review queue / 国际冷泉核查队列", "", f"Window: {inventory['since']}–{inventory['until']}. {active_count} active DOI records; {len(packets)} persistent curated comparisons; {len(archive['candidates'])} archived records.", "",
        f"Access: {access['abstract']} abstract-scoped, {access['full_text_extracts']} inspected full-text passages. / 核查材料：{access['abstract']} 篇限于摘要，{access['full_text_extracts']} 篇已核查相关全文段落。", "",
        "Shared DOI sources are counted once in the atlas, even when they appear in multiple collections. Candidates have no scientific claim until inspected. / 跨专题共享 DOI 在全图谱仅计一次；候选文献经核查后才产生科学论断。", "",
        "| Status / 状态 | Records / 记录数 |", "|---|---:|"]
    summary += [f"| {status} | {count} |" for status, count in sorted(counts.items())]
    summary += ["", "## Remaining candidates / 待核查候选", ""]
    for item in inventory["candidates"]:
        review = reviews.get(item["doi"], {})
        if review.get("status") == "curated":
            continue
        summary += [f"- [{item['title']}](https://doi.org/{item['doi']}) ({item['year']}; {review.get('status', 'awaiting_source_review')}). {review.get('reason', '')} {review.get('reason_zh', '')}",
            f"  Next action: {review.get('next_action', 'Inspect original sample geography, study design and supported comparison.')}"]
    summary += ["", "## Discovery filtering / 发现阶段过滤", "", "Records omitted by the reproducible scope filter are preserved here for audit. / 可复现范围过滤所省略的记录在此保留以便追溯。", ""]
    summary += [f"- [{item['title']}](https://doi.org/{item['doi']}): {item['basis']}." for item in inventory.get("scope_filtered", [])]
    summary += ["", "## Version provenance / 版本来源", ""]
    summary += [f"- [{item['doi']}](https://doi.org/{item['doi']}) → [{item['published_doi']}](https://doi.org/{item['published_doi']}); {item['basis']}." for item in inventory.get("collapsed_versions", [])]
    summary += ["", "## Rolling-window archive / 滚动时间窗归档", "", "Older source profiles and decisions remain available after their discovery records leave the active window. / 发现记录离开当前时间窗后，较早的证据档案与处理决定仍可访问。", ""]
    summary += [f"- [{item['title']}](https://doi.org/{item['doi']}): {item['archive_reason']}." for item in archive["candidates"]]
    (ROOT / "dist/global-cold-seep-review-summary.md").write_text("\n".join(summary).rstrip() + "\n", encoding="utf-8")
    profile = ["# International cold-seep evidence profiles / 国际冷泉证据档案", "",
        "Use these source-specific comparisons to interpret documented SCS findings. The user's manuscript Results have not been supplied. / 这些文献特定比较用于解释已记录的南海研究发现，目前尚未提供用户稿件的结果。", ""]
    roles = {"regional_comparison": "Regional comparison / 区域比较", "mechanistic_context": "Mechanistic precedent / 机制先例", "contextual_habitat": "Habitat context / 生境背景"}
    for packet in sorted(packets, key=lambda item: (-sources[item['doi']]['year'], sources[item['doi']]['title'])):
        source = sources[packet["doi"]]
        profile += ["## " + source["title"], "", packet["title_zh"], "", reference(candidates[packet['doi']], metadata[packet['doi']])[0], ""]
        for label, key in (("Study scope / 研究范围", "scope"), ("Design / 研究设计", "design"), ("Finding / 发现", "finding"), ("Citation limits / 引用边界", "limit"), ("Discussion use / 讨论用途", "discussion")):
            profile += [f"**{label}**: {packet[key][0]}", "", packet[key][1], ""]
        if packet.get("time"):
            profile += [f"Sampling time / 采样时间：{packet['time'][0]} {packet['time'][1]}", ""]
        locator = packet.get("locator", ["Abstract: design and principal findings.", "摘要：研究设计与主要发现。"])
        profile += [f"Evidence access / 核查材料：{packet.get('access', 'abstract')}; reviewed / 核查日期：{reviews[packet['doi']]['reviewed_at']}.", "",
            f"Evidence locator / 证据位置：{locator[0]}", "", locator[1], "",
            f"[Inspected source / 核查来源]({reviews[packet['doi']]['evidence_url']}) · `{source['id']}` · {roles[packet.get('comparison_role', 'regional_comparison')]}", ""]
        if packet.get("accessions"):
            profile += ["Data accessions / 数据登录号：" + ", ".join(packet["accessions"]), ""]
    (ROOT / "dist/global-cold-seep-evidence-profiles.md").write_text("\n".join(profile).rstrip() + "\n", encoding="utf-8")
    print(f"International comparisons: {len(packets)} curated ({shared} shared DOI sources), {active_count} active inventory records, {len(archive['candidates'])} archived; {dict(access)}")


if __name__ == "__main__":
    main()
