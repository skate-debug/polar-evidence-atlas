#!/usr/bin/env python3
"""Maintain the Simplified-Chinese presentation layer for the explorer.

The English evidence records remain canonical.  This script translates only the
fields presented by the website, stores them separately, and fingerprints each
record so later literature updates can be detected without overwriting valid
translations silently.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = DATA / "i18n.zh-CN.json"
TRANSLATE_URLS = (
    "https://translate.googleapis.com/translate_a/single",
    "https://clients5.google.com/translate_a/single",
)
SPLITTER = "ZXQ987654QXZ"


UI_EN = {
    "site_title": "Polar Evidence Atlas",
    "meta_description": "Citation-first explorer for Arctic and Antarctic biological and Earth-system literature.",
    "catalog_aria": "Literature catalog and filters",
    "literature_filters": "Literature filters",
    "project_files": "Project files",
    "graph_totals": "Knowledge graph totals",
    "brand_home": "Polar Evidence Atlas home",
    "brand_name": "Polar Evidence Atlas",
    "brand_version": "Citation-first · live corpus",
    "search_label": "Search title, author, finding, or DOI",
    "search_placeholder": "Search evidence…",
    "open_command_search": "Open command search",
    "refine_corpus": "Refine corpus",
    "area": "Area",
    "pole": "Pole",
    "year": "Year",
    "evidence": "Evidence",
    "all_areas": "All areas",
    "all_poles": "All polar regions",
    "all_years": "All years",
    "all_evidence": "All evidence",
    "reset_filters": "Reset filters",
    "curated_sources": "Curated sources",
    "language": "Language",
    "english": "English",
    "chinese": "Chinese",
    "color_theme": "Color theme",
    "light": "Light",
    "dark": "Dark",
    "system": "System",
    "eyebrow": "Evidence graph · versioned literature",
    "hero_title": "Read the polar system as connected evidence.",
    "hero_subtitle": "Move from poles to habitats, processes, and individual papers. Every scientific relationship resolves to its sampling scope, analytical basis, confidence, and citation limits.",
    "article_opening": "Article opening",
    "download_graphml": "GraphML",
    "download_jsonld": "JSON-LD",
    "download_bibtex": "BibTeX",
    "stat_sources": "Curated papers",
    "stat_claims": "Atomic claims",
    "stat_recent": "From 2024 onward",
    "stat_candidates": "Promoted / retained",
    "active_filters": "Active filters",
    "clear_all": "Clear all",
    "remove_filter": "Remove {label} filter",
    "graph_structure": "Evidence structure",
    "graph_structure_subtitle": "Areas connect to their most frequent study facets.",
    "overview": "Overview",
    "graph_description": "A layered knowledge graph connecting poles, literature areas, sources, and study concepts. Select a node to filter or inspect sources.",
    "graph_note_overview": "Node counts and edge thickness reflect matching curated sources. Select a pole, area, or facet to narrow the corpus; select a paper for its evidence neighborhood.",
    "graph_no_matches": "No evidence paths match the filters.",
    "layer_pole": "Pole",
    "layer_area": "Literature area",
    "layer_facet": "Frequent study facet",
    "matching_sources": "{count} matching source(s)",
    "source_count": "{count} source(s)",
    "source_graph": "Source evidence neighborhood",
    "source_graph_note": "Profile links show what was sampled, measured, or analyzed. The highlighted arrow is the curated atomic claim; its evidence class and limitations appear in the profile.",
    "evidence_profile": "Evidence profile",
    "evidence_profile_subtitle": "What the paper supports—and what it does not.",
    "how_to_read": "How to read this atlas",
    "how_to_read_body": "Select a paper to inspect its full evidence profile. The overview graph aggregates only curated sources that pass the current filters.",
    "evidence_classes": "Evidence classes",
    "reported": "Reported",
    "reported_definition": "Observed or experimentally measured by the source.",
    "inferred": "Inferred",
    "inferred_definition": "Genome content, host prediction, proxy, association, or reconstruction.",
    "modeled": "Modeled",
    "modeled_definition": "Numerical or statistical model result or projection.",
    "synthesized": "Synthesized",
    "synthesized_definition": "Conclusion assembled across studies in a review.",
    "citation_safety": "Citation safety",
    "citation_safety_body": "Each record separates appropriate citation uses from claims that exceed the study design, sampling domain, or analytical basis.",
    "open_doi": "Open DOI",
    "copy_key": "Copy citation key",
    "copy_bibtex": "Copy BibTeX",
    "study_design": "Study design",
    "type": "Type",
    "space": "Space",
    "time": "Time",
    "sampling": "Sampling",
    "methods": "Methods",
    "variables": "Variables",
    "key_findings": "Key findings",
    "cite_for": "Use this source for",
    "atomic_claim": "Atomic claim",
    "atomic_claims": "Atomic claims",
    "scope": "Scope",
    "basis": "Basis",
    "confidence_reason": "Why this confidence",
    "confidence": "confidence",
    "limitations": "Limitations",
    "do_not_overcite": "Do not over-cite for",
    "data_curation": "Data and curation",
    "accessions": "Accessions",
    "none_recorded": "None recorded in this profile",
    "checked": "Checked",
    "key": "Key",
    "citation_key_copied": "Citation key copied",
    "bibtex_copied": "BibTeX copied",
    "concept_filter": "Concept filter: {label}",
    "clear_concept_filter": "Clear concept filter",
    "matching_papers": "{count} matching paper(s)",
    "no_sources": "No curated sources match these filters.",
    "built_status": "Graph built {built} · Curated records verified through {verified}",
    "candidate_footer": "Candidate results remain quarantined until review",
    "interface_credit": "Interface inspired by ThreeUI Community (MIT)",
    "command_title": "Search the evidence atlas",
    "command_dialog": "Search curated polar literature",
    "command_placeholder": "Title, author, finding, concept, or DOI…",
    "command_results": "Results",
    "command_preview": "Evidence preview",
    "command_empty": "No curated source matches this search.",
    "command_hint_move": "Move",
    "command_hint_open": "Open",
    "command_hint_close": "Close",
    "command_initial": "Start typing to search across English and Chinese evidence text.",
    "published_title": "Published title",
    "translated_title": "Chinese translation",
    "translation_note": "Chinese is a terminology-normalized reading translation; published bibliographic text remains unchanged for citation.",
}


UI_ZH = {
    "site_title": "极地证据图谱",
    "meta_description": "以引文为核心，探索北极与南极生物及地球系统文献。",
    "catalog_aria": "文献目录与筛选条件",
    "literature_filters": "文献筛选条件",
    "project_files": "项目文件",
    "graph_totals": "知识图谱统计",
    "brand_home": "返回极地证据图谱首页",
    "brand_name": "极地证据图谱",
    "brand_version": "引文优先 · 持续更新",
    "search_label": "按标题、作者、研究发现或 DOI 检索",
    "search_placeholder": "检索证据…",
    "open_command_search": "打开快捷检索",
    "refine_corpus": "筛选文献库",
    "area": "研究领域",
    "pole": "极区",
    "year": "年份",
    "evidence": "证据类型",
    "all_areas": "全部领域",
    "all_poles": "全部极区",
    "all_years": "全部年份",
    "all_evidence": "全部证据",
    "reset_filters": "重置筛选条件",
    "curated_sources": "精选文献",
    "language": "语言",
    "english": "English",
    "chinese": "中文",
    "color_theme": "配色模式",
    "light": "浅色",
    "dark": "深色",
    "system": "跟随系统",
    "eyebrow": "证据图谱 · 版本化文献库",
    "hero_title": "以证据网络解读极地系统",
    "hero_subtitle": "从两极延伸至生境、生态过程和具体论文。每一条科学关系均可追溯至采样范围、分析依据、置信度及引用边界。",
    "article_opening": "文章导论",
    "download_graphml": "GraphML",
    "download_jsonld": "JSON-LD",
    "download_bibtex": "BibTeX",
    "stat_sources": "精选论文",
    "stat_claims": "原子化论断",
    "stat_recent": "2024 年及以后",
    "stat_candidates": "已纳入 / 待核验",
    "active_filters": "当前筛选",
    "clear_all": "全部清除",
    "remove_filter": "移除“{label}”筛选条件",
    "graph_structure": "证据结构",
    "graph_structure_subtitle": "研究领域与其中最常见的研究要素相连。",
    "overview": "总览",
    "graph_description": "分层知识图谱连接极区、研究领域、文献来源与研究概念。选择节点可进一步筛选或查看文献。",
    "graph_note_overview": "节点计数与连线粗细表示符合条件的精选文献数量。选择极区、领域或研究要素可缩小文献范围；选择论文可查看其证据邻域。",
    "graph_no_matches": "没有符合当前筛选条件的证据路径。",
    "layer_pole": "极区",
    "layer_area": "研究领域",
    "layer_facet": "高频研究要素",
    "matching_sources": "{count} 篇相关文献",
    "source_count": "{count} 篇文献",
    "source_graph": "文献证据邻域",
    "source_graph_note": "档案连线显示论文采集、测量或分析的对象。高亮箭头表示经过整理的原子化论断；其证据类型与局限性列于右侧档案。",
    "evidence_profile": "证据档案",
    "evidence_profile_subtitle": "明确论文能够支持与不能支持的结论。",
    "how_to_read": "图谱阅读方法",
    "how_to_read_body": "选择论文可查看完整证据档案。总览图仅汇总符合当前筛选条件的精选文献。",
    "evidence_classes": "证据类型",
    "reported": "实测",
    "reported_definition": "由原文直接观察或通过实验测得。",
    "inferred": "推断",
    "inferred_definition": "依据基因组内容、宿主预测、代用指标、关联分析或重建结果得出。",
    "modeled": "模拟",
    "modeled_definition": "数值模型或统计模型的结果与预测。",
    "synthesized": "综合",
    "synthesized_definition": "综述对多项研究进行归纳后得出的结论。",
    "citation_safety": "引用边界",
    "citation_safety_body": "每条记录均区分适合引用的结论，以及超出研究设计、采样范围或分析依据的表述。",
    "open_doi": "打开 DOI",
    "copy_key": "复制引文键",
    "copy_bibtex": "复制 BibTeX",
    "study_design": "研究设计",
    "type": "类型",
    "space": "空间范围",
    "time": "时间范围",
    "sampling": "采样设计",
    "methods": "研究方法",
    "variables": "测量或推导变量",
    "key_findings": "主要发现",
    "cite_for": "适合引用于",
    "atomic_claim": "原子化论断",
    "atomic_claims": "原子化论断",
    "scope": "适用范围",
    "basis": "证据依据",
    "confidence_reason": "置信度说明",
    "confidence": "置信度",
    "limitations": "研究局限",
    "do_not_overcite": "不宜引申用于",
    "data_curation": "数据与整理信息",
    "accessions": "数据登录号",
    "none_recorded": "本档案未记录",
    "checked": "核验日期",
    "key": "引文键",
    "citation_key_copied": "已复制引文键",
    "bibtex_copied": "已复制 BibTeX",
    "concept_filter": "概念筛选：{label}",
    "clear_concept_filter": "清除概念筛选",
    "matching_papers": "符合条件的论文：{count} 篇",
    "no_sources": "没有符合当前筛选条件的精选文献。",
    "built_status": "图谱构建于 {built} · 精选记录核验至 {verified}",
    "candidate_footer": "候选文献须经审核后方可进入知识图谱",
    "interface_credit": "界面设计参考 ThreeUI Community（MIT）",
    "command_title": "检索极地证据图谱",
    "command_dialog": "检索精选极地文献",
    "command_placeholder": "输入标题、作者、研究发现、概念或 DOI…",
    "command_results": "检索结果",
    "command_preview": "证据预览",
    "command_empty": "没有符合检索条件的精选文献。",
    "command_hint_move": "移动",
    "command_hint_open": "打开",
    "command_hint_close": "关闭",
    "command_initial": "开始输入，即可同时检索中英文证据内容。",
    "published_title": "原文标题",
    "translated_title": "中文译题",
    "translation_note": "中文内容经过术语规范化，正式引用仍以原始出版信息为准。",
}


LABELS_ZH = {
    "domains": {
        "Antarctic prokaryotes": "南极原核生物",
        "Antarctic viruses": "南极病毒",
        "Arctic prokaryotes": "北极原核生物",
        "Arctic viruses": "北极病毒",
        "Polar Earth system": "极地地球系统",
        "Polar eukaryotes": "极地真核生物",
    },
    "poles": {"Arctic": "北极", "Antarctic": "南极", "Bipolar": "两极", "Global": "全球"},
    "evidence": {"reported": "实测", "inferred": "推断", "modeled": "模拟", "synthesized": "综合"},
    "confidence": {"high": "高", "moderate": "中等", "low": "低"},
    "predicates": {
        "harbours": "蕴含", "associated_with": "相关于", "infects_or_targets": "感染或靶向",
        "encodes_potential_for": "编码相关潜力", "drives": "驱动", "increases": "增加",
        "decreases": "降低", "shifts_to": "转变为", "supplies": "供应", "exports": "输出",
        "transports": "输送", "mixes_with": "与之混合", "limits": "限制", "co_limits": "共同限制",
        "supports": "支持", "formed_by": "由其形成", "separates": "分隔", "connects": "连接",
        "catalogues": "编目", "projects": "预测", "broader": "上位概念", "covers_pole": "涵盖极区",
        "covers_domain": "涵盖领域", "samples": "采样于", "uses_method": "采用方法",
        "studies_taxon": "研究类群", "studies_process": "研究过程", "evaluates_driver": "评估驱动因素",
    },
    "types": {
        "Pole": "极区", "Region": "区域", "WaterMass": "水团或洋流", "Habitat": "生境",
        "Taxon": "生物类群", "Process": "生态过程", "Driver": "环境驱动因素", "Method": "研究方法",
        "Nutrient": "营养盐", "Geology": "地质要素", "Geochemistry": "地球化学要素",
        "Domain": "研究领域", "Source": "文献来源", "Concept": "概念",
    },
}


# Labels and titles receive a human editorial pass because they are the most
# visible strings and short phrases provide too little context for MT systems.
CONCEPT_LABEL_OVERRIDES_ZH = {
    "pole:bipolar": "两极",
    "region:storfjordrenna": "Storfjordrenna 海槽",
    "region:bonanza-creek": "博南扎溪长期生态研究站",
    "region:qeqertarsuaq": "Qeqertarsuaq（西格陵兰）",
    "region:ross-ice-shelf": "罗斯冰架",
    "region:mercer-subglacial-lake": "默瑟冰下湖",
    "region:dome-fuji": "富士冰穹",
    "region:mertz-polynya": "默茨冰间湖",
    "region:western-antarctic-peninsula": "南极半岛西部",
    "habitat:melt-pond": "融池",
    "habitat:geothermal-soil": "南极地热生境",
    "habitat:sponge-holobiont": "海绵共生整体",
    "habitat:coastal-polynya": "沿岸冰间湖",
    "habitat:plastisphere": "海洋塑料际",
    "taxon:mirusviricota": "Mirusviricota 门",
    "taxon:crassvirales": "Crassvirales 目",
    "taxon:polinton-like-viruses": "Polinton 样病毒",
    "taxon:nitrosopumilaceae": "Nitrosopumilaceae 科",
    "taxon:nitrosopumilus": "“候选”Nitrosopumilus 属",
    "taxon:thioglobus": "Thioglobus 属",
    "taxon:patescibacteria": "Patescibacteria",
    "taxon:tariuqbacteria": "“候选”Tariuqbacteria",
    "taxon:haptophytes": "定鞭藻类",
    "taxon:cryptophytes": "隐藻类",
    "taxon:syndiniales": "Syndiniales 目",
    "taxon:cercozoa": "Cercozoa（丝足虫类）",
    "taxon:mast": "海洋异养型不等鞭毛类群（MAST）",
    "process:sulfur-reduction": "硫与硫酸盐还原",
    "process:atlantification": "大西洋化",
    "process:overturning-circulation": "翻转环流",
    "process:dense-water-formation": "密水形成",
    "driver:sea-ice-cover": "海冰覆盖",
    "driver:light": "光照可用性与光谱",
    "driver:oxygen": "氧可用性",
    "driver:moisture": "水分可用性",
    "driver:water-mass": "水团属性",
    "driver:bathymetry": "海底地形",
    "driver:wind": "风场强迫",
    "water:atlantic-water": "大西洋水",
    "water:pacific-water": "太平洋水",
    "method:stable-isotope-probing": "稳定同位素探针技术",
    "method:review-synthesis": "综述整合",
    "method:seda-dna": "沉积物古 DNA 宏条形码分析",
    "method:genome-resolved-analysis": "基因组解析宏基因组分析",
    "region:aasiaat": "阿西亚特沿岸地区",
    "region:bayelva": "Bayelva 多年冻土观测站",
    "habitat:active-layer-soil": "多年冻土活动层土壤",
    "habitat:benthic-microbial-mat": "底栖微生物席",
    "process:southern-ocean-teleconnection": "南大洋—热带遥相关",
    "driver:southern-annular-mode": "南半球环状模（SAM）",
    "method:community-knowledge": "社区知识协同生产",
    "taxon:antarctic-fur-seal": "南极毛皮海豹（Arctocephalus gazella）",
    "taxon:micromonas-polaris": "Micromonas polaris（极地微单胞藻）",
    "taxon:mpov-44t-a": "Micromonas polaris 病毒 MpoV-44T.A",
    "taxon:mpov-44t-b": "Micromonas polaris 病毒 MpoV-44T.B",
    "process:antimicrobial-resistance": "抗微生物药物耐药潜力",
    "taxon:bacteroidia": "拟杆菌纲",
    "taxon:ice-algae": "海冰藻类",
    "taxon:oleispira": "Oleispira 属",
    "taxon:bermanella": "Bermanella 属",
    "taxon:pseudoalteromonas": "假交替单胞菌属",
    "process:turbulent-nutrient-supply": "湍流营养盐输送",
    "process:sea-ice-melt-export": "海冰融化物质输出",
    "method:edna-metabarcoding": "环境 DNA 宏条形码分析",
    "method:primary-production-assay": "初级生产力测定",
    "method:mesocosm": "中尺度围隔实验",
}


SOURCE_TITLE_OVERRIDES_ZH = {
    "Seasonal dynamics and diversity of Antarctic marine viruses reveal a novel viral seascape": "南极海洋病毒的季节动态与多样性揭示全新的病毒群落图景",
    "Viruses under the Antarctic Ice Shelf are active and potentially involved in global nutrient cycles": "南极冰架下病毒具有活性，并可能参与全球营养元素循环",
    "Novel adaptive immune systems in pristine Antarctic soils": "未受扰动的南极土壤中的新型适应性免疫系统",
    "Distinct and rich assemblages of giant viruses in Arctic and Antarctic lakes": "北极和南极湖泊中独特而丰富的巨型病毒群集",
    "Viral Diversity in Polar Hydrocarbon-Contaminated Soils: A Transect Study from King George Island, Antarctica": "极地烃污染土壤中的病毒多样性：南极乔治王岛横断面研究",
    "Arctic Ocean virus communities and their seasonality, bipolarity, and prokaryotic associations": "北冰洋病毒群落及其季节性、两极分布和原核生物关联",
    "Surface microlayer-mediated virome dissemination in the Central Arctic": "中央北极海表微层介导的病毒组传播",
    "Active virus-host interactions at sub-freezing temperatures in Arctic peat soil": "北极泥炭土中亚冰点温度下的活跃病毒—宿主相互作用",
    "Past and present giant viruses diversity explored through permafrost metagenomics": "通过多年冻土宏基因组学探索古今巨型病毒多样性",
    "Genomic adaptation of giant viruses in polar oceans": "极地海洋巨型病毒的基因组适应",
    "Isolation of a Cohort of Giant Viruses From Above the Arctic Circle in Northern Norway": "从挪威北部北极圈以北地区分离出一组巨型病毒",
    "Genetic isolation and metabolic complexity of an Antarctic subglacial microbiome": "南极冰下微生物组的遗传隔离与代谢复杂性",
    "Metabolically flexible microorganisms rapidly establish glacial foreland ecosystems": "代谢灵活的微生物迅速构建冰川前缘地生态系统",
    "Unveiling unique microbial nitrogen cycling and nitrification driver in coastal Antarctica": "揭示南极沿岸独特的微生物氮循环及硝化作用驱动者",
    "Genomic profiling of Antarctic geothermal microbiomes using long-read, Hi-C, and single-cell techniques": "利用长读长、Hi-C 与单细胞技术解析南极地热微生物组",
    "Unveiling microbial guilds and symbiotic relationships in Antarctic sponge microbiomes": "揭示南极海绵微生物组中的微生物功能群与共生关系",
    "Seasonal recurrence and modular assembly of an Arctic pelagic marine microbiome": "北极远洋微生物组的季节性重现与模块化群落构建",
    "Metagenome-assembled-genomes recovered from the Arctic drift expedition MOSAiC": "MOSAiC 北极漂流考察中回收的宏基因组组装基因组",
    "Atlantic water influx and sea-ice cover drive taxonomic and functional shifts in Arctic marine bacterial communities": "大西洋水输入与海冰覆盖驱动北极海洋细菌群落的分类与功能转变",
    "Discovery of a novel bacterial class with the capacity to drive sulfur cycling and microbiome structure in a paleo-ocean analog": "在古海洋类比环境中发现可驱动硫循环和微生物组结构的新细菌纲",
    "Compendium of 530 metagenome-assembled bacterial and archaeal genomes from the polar Arctic Ocean": "极地北冰洋 530 个宏基因组组装细菌和古菌基因组汇编",
    "Water mass specific genes dominate the Southern Ocean microbiome": "水团特异性基因主导南大洋微生物组",
    "Antarctic soil prokaryotic diversity: a dataset of 319 metagenome-assembled genomes from Deception and Livingston Islands": "南极土壤原核生物多样性：欺骗岛和利文斯顿岛 319 个宏基因组组装基因组数据集",
    "Temporal succession and assembly of marine bacterial communities in Maxwell Bay, Antarctica during summer": "南极麦克斯韦湾夏季海洋细菌群落的时间演替与构建",
    "Nitrogen fixation in Arctic coastal waters (Qeqertarsuaq, West Greenland): influence of glacial melt on diazotrophs, nutrient availability, and seasonal blooms": "北极沿岸水域（西格陵兰 Qeqertarsuaq）的固氮作用：冰川融水对固氮生物、营养盐可用性和季节性藻华的影响",
    "Antarctic phytoplankton communities restructure under shifting sea-ice regimes": "海冰格局变化下南极浮游植物群落的重组",
    "Southern Ocean regime shift: divergent trends in surface phytoplankton community composition using a diagnostic pigment framework": "南大洋生态格局转变：利用诊断色素框架识别表层浮游植物群落组成的分化趋势",
    "Beyond blooms: the winter ecosystem reset determines microeukaryotic community dynamics in the Fram Strait": "超越藻华：冬季生态系统重置决定弗拉姆海峡微型真核生物群落动态",
    "Antarctic benthic ecological change": "南极底栖生态变化",
    "Biogeographic gradients of picoplankton diversity indicate increasing dominance of prokaryotes in warmer Arctic fjords": "微微型浮游生物多样性的生物地理梯度表明较暖北极峡湾中原核生物优势度上升",
    "Surface darkening by abundant and diverse algae on an Antarctic ice cap": "丰富多样的藻类使南极冰帽表面变暗",
    "Oceanic regions shape the composition of the Antarctic plastisphere": "海洋区域塑造南极塑料际群落组成",
    "Intense autumnal coastal biogenic particle settling fluxes align with phytoplankton phenology changes off the western Antarctic Peninsula": "南极半岛西部近海强烈的秋季沿岸生源颗粒沉降通量与浮游植物物候变化一致",
    "Marine eukaryote community responses to the climate and oceanographic changes in Storfjordrenna (southern Svalbard) over the past ~13.3 kyr BP: insights from sedimentary ancient DNA analysis": "过去约 1.33 万年以来 Storfjordrenna 海槽（斯瓦尔巴南部）海洋真核生物群落对气候与海洋变化的响应：沉积物古 DNA 分析",
    "Arctic Ocean bathymetry and its connections to tectonics, oceanography and climate": "北冰洋海底地形及其与构造、海洋学和气候的联系",
    "Antarctic Bottom Water in a changing climate": "变化气候中的南极底层水",
    "Antarctic coastal polynyas in the global climate system": "全球气候系统中的南极沿岸冰间湖",
    "The role of biota in the Southern Ocean carbon cycle": "生物群在南大洋碳循环中的作用",
    "Climate change and terrigenous inputs decrease the efficiency of the future Arctic Ocean’s biological carbon pump": "气候变化和陆源输入降低未来北冰洋生物碳泵效率",
    "Sea ice loss drives a regime shift in Arctic Ocean nitrogen biogeochemistry": "海冰消退驱动北冰洋氮生物地球化学格局转变",
    "The Antarctic Subglacial Hydrological Environment and International Drilling Projects: A Review": "南极冰下水文环境与国际钻探计划：综述",
    "Tectonic structures of the Dome Fuji region, East Antarctica, based on new magnetic data": "基于新磁测数据的东南极富士冰穹区域构造",
    "Tectonic evolution of the Amerasia Basin, Arctic Ocean": "北冰洋阿美拉西亚盆地的构造演化",
    "Recent advances in mineralogy, petrology, geochemistry, and geochronology in East Antarctica": "东南极矿物学、岩石学、地球化学和地质年代学最新进展",
    "The Pan‐Arctic Continental Slope as an Intensifying Conveyer Belt for Nutrients in the Central Arctic Ocean (1985–2015)": "泛北极大陆坡作为中央北冰洋日益强化的营养盐输送带（1985—2015 年）",
    "Around one third of current Arctic Ocean primary production sustained by rivers and coastal erosion": "河流和海岸侵蚀维持当前北冰洋约三分之一的初级生产",
    "Manganese co-limitation of phytoplankton growth and major nutrient drawdown in the Southern Ocean": "锰共同限制南大洋浮游植物生长及主要营养盐消耗",
    "Giant iceberg meltwater increases upper-ocean stratification and vertical mixing": "巨型冰山融水增强上层海洋层化与垂向混合",
    "Arctic Permafrost Thawing Enhances Sulfide Oxidation": "北极多年冻土融化增强硫化物氧化",
    "Geology of the Eurasia Basin and Gakkel Ridge, Arctic Ocean: Review and update": "北冰洋欧亚盆地与加克尔海岭地质：综述与更新",
    "Limited impact of Greenland meltwater on abruptness and reversibility of future Atlantic overturning changes": "格陵兰融水对未来大西洋翻转环流突变性和可逆性的影响有限",
    "Tropical impacts of the Southern Ocean underestimated by mean-state biases": "平均态偏差导致低估南大洋对热带地区的影响",
    "Recent Dominant Transposition Events Affect Gene Regulatory Regions, but Not Coding Sequences, in Polar and Brown Bear Genomes": "近期主要转座事件影响北极熊和棕熊基因组的基因调控区，而不影响编码序列",
    "Impacts of future sea level change on Greenland from community knowledge, coastal mapping, and glacial isostatic adjustment models": "融合社区知识、沿岸测绘和冰川均衡调整模型评估未来海平面变化对格陵兰的影响",
    "Functional genetic potential of benthic microbial mat communities in Arctic, Antarctic, and sub-Antarctic lakes": "北极、南极及亚南极湖泊底栖微生物席群落的遗传功能潜力",
    "Interdecadal shift in the spring Southern Annular Mode intensifies its lagged influence on Antarctic summer sea ice": "春季南半球环状模年代际转变增强其对南极夏季海冰的滞后影响",
    "Capacity of Arctic fjord sediments to degrade carbohydrates from permafrost active layer": "北极峡湾沉积物降解多年冻土活动层来源碳水化合物的能力",
    "Seasonal thawing of high Arctic soils triggers selective microbial growth and predation": "高北极土壤季节性融化触发选择性微生物生长和捕食",
    "Investigating high pathogenicity avian influenza virus incursions to remote islands: detection of H5N1 on Gough Island in the South Atlantic Ocean": "调查高致病性禽流感病毒侵入偏远岛屿：在南大西洋高夫岛检出 H5N1",
    "Chromosome-scale genome assembly and annotation of Jonah's icefish Neopagetopsis ionah": "乔纳冰鱼 Neopagetopsis ionah 的染色体水平基因组组装与注释",
    "Infection Dynamics and Coexistence of Two Novel Arctic Phytoplankton Viruses": "两种新型北极浮游植物病毒的感染动态与共存",
    "Deep metagenomics uncovers functional adaptations and pathogenic risks in the gut microbiome of Antarctic fur seals (Arctocephalus gazella)": "深度宏基因组测序揭示南极毛皮海豹（Arctocephalus gazella）肠道微生物组的功能适应与致病风险",
    "Viral genetic diversity and functional potential in polar and subarctic sea ice": "极地和亚北极海冰中的病毒遗传多样性与功能潜力",
    "Dimethylsulfoniopropionate metabolism shapes microbial ecology and physiological adaptation during the austral winter in Southern Ocean sea ice and seawater": "二甲基巯基丙酸内盐代谢塑造南大洋海冰和海水中南半球冬季的微生物生态与生理适应",
    "High sea ice algal primary production near marine-terminating glaciers linked to turbulence-driven nutrient fluxes across the ice–ocean interface": "入海冰川附近的高海冰藻类初级生产与冰—海界面湍流驱动的营养盐通量相关",
    "Unique microbes released by retreating glaciers are rarely propagated to coastal ecosystems": "退缩冰川释放的特有微生物很少向沿岸生态系统扩散",
    "Distinct Distribution Patterns of Dissolved and Particulate Trace Metals in Surface Waters of the Amundsen Sea: From Polynya to Open Waters": "阿蒙森海表层水中溶解态与颗粒态微量金属的独特分布：从冰间湖到开阔水域",
    "Unveiling Ross Sea eukaryotic diversity through environmental DNA metabarcoding": "利用环境 DNA 宏条形码揭示罗斯海真核生物多样性",
    "Microbial succession and hydrocarbon-degrading potential in Arctic sea ice exposed to dispersed crude oil and chemical dispersant": "暴露于分散原油和化学分散剂的北极海冰中微生物演替及烃降解潜力",
    "Arctic sea-ice ridges are biomass hotspots harboring diverse microbial communities": "北极海冰压力脊是孕育多样微生物群落的生物量热点",
    "Microbial Ecology of Rotten Sea Ice: Implications for Arctic Carbon Cycling with Global Warming": "腐朽海冰的微生物生态：全球变暖背景下对北极碳循环的启示",
    "Microbial and chemical signatures of melting sea-ice: export of bacteria, microeukaryotes, and molecules": "融化海冰的微生物与化学特征：细菌、微型真核生物和分子的输出",
}


# A small number of short or idiomatic fields need more context than a general
# translation service can infer. Keep these editorial overrides beside the
# title pass so subsequent refreshes reproduce the reviewed wording.
SOURCE_CONTENT_OVERRIDES_ZH = {
    "src:piedade-2024-antarctic-viral-seascape": {
        "study_type": "病毒富集组分与细胞组分配对的观察性宏基因组时间序列",
    },
    "src:queiroz-2026-arctic-giant-virus-isolates": {
        "study_type": "基于培养的巨型病毒分离与比较基因组学",
        "do_not_overcite": [
            "整个北极地区的丰度",
            "巨型病毒的完整宿主范围",
            "气候变化驱动的巨型病毒流行率变化",
        ],
    },
}


CLAIM_CONTENT_OVERRIDES_ZH = {
    "claim:028-fram-winter-reset": {
        "statement": "弗拉姆海峡四年时间序列支持“冬季重置”机制：冬季整体环境状态强烈制约次年春季藻华中出现的微型真核生物。",
        "scope": "一套高时间分辨率的海洋微型真核生物时间序列及其动力学网络模型。",
        "evidence_basis": "时间序列观测结合动力学网络与群落状态分析。",
        "locator": "结果与讨论：冬季重置",
        "confidence_note": "时间上的重复出现与模型分析共同支持冬季重置；光照只是综合冬季环境状态的一个组成部分。",
    },
    "claim:047-manganese-colimitation": {
        "statement": "在南大洋外海采样站，同时添加铁和锰所促进的浮游植物生长及主要营养盐消耗均强于仅添加铁。",
        "scope": "在极锋以南选定站点开展的短期、无痕量金属污染船载培养实验。",
        "evidence_basis": "设置铁添加、锰添加、铁锰联合添加及对照处理，并测量生物学与营养盐指标。",
        "locator": "结果：痕量金属添加响应",
        "confidence_note": "这些站点的实验直接支持铁—锰共同限制，但其空间普遍性尚未厘清。",
    },
    "claim:069-mpov-b-arctic-metagenomes": {
        "statement": "在所分析的 Tara 北极宏基因组中，MpoV-44T.B 样测序读段始终多于 MpoV-44T.A 样测序读段，这与营养盐充足条件下双重感染实验所见的竞争排序相反。",
        "scope": "2013 年 5—9 月在 Tara Oceans Polar Circle 七个站位采集的 14 个表层和深层叶绿素最大值层样本。",
        "evidence_basis": "使用 Kraken2 将环境宏基因组测序读段分类至两个分离株基因组，并进行配对的站位水平比较。",
        "locator": "结果 3.4；图 6",
        "confidence_note": "整个数据集中的相对测序读段信号在统计上保持一致，但结果依赖分类器特异性，且不能确定绝对病毒颗粒丰度。",
    },
    "claim:081-amundsen-iron-response-varies": {
        "statement": "五天铁添加实验在冰间湖内几乎未引起叶绿素响应，在外海引起较强响应，而海冰区的响应变异很大，表明阿蒙森海不同水文分区对铁的敏感性不同。",
        "scope": "4 个冰间湖站位，以及外海和海冰区各 5 个培养实验站位。",
        "evidence_basis": "比较船载铁添加实验第五天的叶绿素 a 与配对对照之比。",
        "locator": "结果与讨论 3.1；图 1d 和图 S2",
        "confidence_note": "叶绿素响应为直接测量结果，但实验未分别检验碳固定、物种更替及其他营养盐共同限制。",
    },
    "claim:091-melting-ice-exports-molecules": {
        "statement": "原始海冰特有的 128 个分子式中，有 10 个随后在融水中检出，为冰—水物质连通提供了化学指纹。",
        "scope": "持续 49 小时的弗拉姆海峡海冰融化微宇宙实验。",
        "evidence_basis": "使用 FT-ICR-MS 比较原始海冰、海水和融水中的分子式。",
        "locator": "结果 3.4：海冰融化的化学特征",
        "confidence_note": "分子式重叠支持物质转移，但无法唯一确定分子结构、生物可利用性或生态系统尺度通量。",
    },
    "claim:089-rotten-ice-retains-particulates": {
        "statement": "尽管溶解态物质已排出并在垂向趋于均一，腐化海冰的上层仍保留了颗粒有机碳、颗粒氮和胞外聚合物。",
        "scope": "7 月在乌特恰维克附近两块腐化浮冰上获得的垂向剖面。",
        "evidence_basis": "测量颗粒碳、颗粒氮、胞外聚合物、孔隙率及其垂向分布。",
        "locator": "讨论 4.1 与结论",
        "confidence_note": "样本浮冰中的滞留现象得到直接观测；浮冰解体后物质释放的规模与去向尚未测量。",
    },
}


# Longest entries are protected first.  The Chinese terms follow common usage
# in polar microbiology and oceanography rather than literal word substitution.
TERM_MAP = {
    "paired virus-enriched and cellular-fraction assemblies": "病毒富集组分与细胞组分的配对组装结果",
    "virus-enriched and cellular-fraction assemblies": "病毒富集组分与细胞组分组装结果",
    "cellular-fraction assemblies": "细胞组分组装结果",
    "virus-enriched": "病毒富集",
    "community knowledge co-production": "社区知识协同生产",
    "community knowledge": "社区知识",
    "microbial community assembly": "微生物群落构建",
    "bacterial community assembly": "细菌群落构建",
    "community assembly": "群落构建",
    "modular assembly": "模块化构建",
    "supercontinent assembly": "超大陆聚合",
    "reference genome assemblies": "参考基因组组装结果",
    "reference assemblies": "参考基因组组装结果",
    "genome assembly": "基因组组装",
    "metagenomic assembly": "宏基因组组装",
    "co-assembled": "共组装",
    "co-assembly": "共组装",
    "assembly recovery": "组装恢复率",
    "metagenome-assembled genome": "宏基因组组装基因组",
    "metagenome-assembled genomes": "宏基因组组装基因组",
    "viral operational taxonomic units": "病毒操作分类单元",
    "viral operational taxonomic unit": "病毒操作分类单元",
    "operational taxonomic units": "操作分类单元",
    "operational taxonomic unit": "操作分类单元",
    "single-amplified genomes": "单细胞扩增基因组",
    "single-amplified genome": "单细胞扩增基因组",
    "virus-enriched fraction": "病毒富集组分",
    "virus-enriched and cellular fractions": "病毒富集组分和细胞组分",
    "cellular-size fraction": "细胞粒级组分",
    "cellular fraction": "细胞组分",
    "viral fraction": "病毒组分",
    "size fractions": "粒级组分",
    "size fraction": "粒级组分",
    "size-fractionated": "分粒级",
    "deep chlorophyll maximum": "深层叶绿素最大层",
    "high-rank diversity": "高阶分类多样性",
    "host and bloom succession": "宿主与藻华演替",
    "active infection": "活跃感染",
    "productive-season windows": "高生产力季节时段",
    "productive season": "高生产力季节",
    "seasonal abundance": "季节丰度",
    "relative abundance": "相对丰度",
    "taxonomic richness": "分类单元丰富度",
    "species richness": "物种丰富度",
    "viral seascape": "病毒群落图景",
    "microbial communities": "微生物群落",
    "microbial community": "微生物群落",
    "bacterial communities": "细菌群落",
    "bacterial community": "细菌群落",
    "viral communities": "病毒群落",
    "viral community": "病毒群落",
    "phytoplankton communities": "浮游植物群落",
    "phytoplankton community": "浮游植物群落",
    "eukaryotic communities": "真核生物群落",
    "eukaryotic community": "真核生物群落",
    "community composition": "群落组成",
    "community structure": "群落结构",
    "community dynamics": "群落动态",
    "communities": "群落",
    "community": "群落",
    "assemblages": "群集",
    "assemblage": "群集",
    "abundance": "丰度",
    "richness": "丰富度",
    "seasonal blooms": "季节性藻华",
    "blooms": "藻华",
    "bloom": "藻华",
    "succession": "演替",
    "ecological guilds": "生态功能群",
    "microbial guilds": "微生物功能群",
    "guilds": "功能群",
    "guild": "功能群",
    "picoplankton": "微微型浮游生物",
    "picoeukaryotes": "微微型真核生物",
    "microeukaryotic": "微型真核生物",
    "microeukaryotes": "微型真核生物",
    "microeukaryote": "微型真核生物",
    "water-mass-specific": "水团特异性",
    "water mass specific": "水团特异性",
    "water masses": "水团",
    "water mass": "水团",
    "upper-ocean stratification": "上层海洋层化",
    "vertical mixing": "垂向混合",
    "nutrient drawdown": "营养盐消耗",
    "nutrient fluxes": "营养盐通量",
    "nutrient flux": "营养盐通量",
    "nutrient supply": "营养盐供应",
    "nutrient availability": "营养盐可用性",
    "trace metals": "微量金属",
    "trace metal": "微量金属",
    "regime shift": "生态格局转变",
    "mean-state bias": "平均态偏差",
    "biogenic particles": "生源颗粒",
    "biogenic particle": "生源颗粒",
    "particle settling fluxes": "颗粒沉降通量",
    "particle settling flux": "颗粒沉降通量",
    "marine-terminating glaciers": "入海冰川",
    "marine-terminating glacier": "入海冰川",
    "environmental DNA metabarcoding": "环境 DNA 宏条形码分析",
    "metabarcoding": "宏条形码分析",
    "long-read": "长读长",
    "primary-production assay": "初级生产力测定",
    "mesocosm experiment": "中尺度围隔实验",
    "Southern Annular Mode": "南半球环状模（SAM）",
    "Southern Ocean": "南大洋",
    "Central Arctic Ocean": "中央北冰洋",
    "Arctic Ocean": "北冰洋",
    "West Antarctic Peninsula": "南极半岛西部",
    "Antarctic Peninsula": "南极半岛",
    "East Antarctic Ice Sheet": "东南极冰盖",
    "West Antarctic Ice Sheet": "西南极冰盖",
    "West Spitsbergen Current": "西斯匹次卑尔根海流",
    "East Greenland Current": "东格陵兰海流",
    "Antarctic Circumpolar Current": "南极绕极流",
    "Atlantic Meridional Overturning Circulation": "大西洋经向翻转环流",
    "North Atlantic Current": "北大西洋流",
    "Pacific-origin water": "太平洋源水",
    "Atlantic-origin water": "大西洋源水",
    "glacial forelands": "冰川前缘地",
    "glacial foreland": "冰川前缘地",
    "ice-shelf cavity": "冰架下空腔",
    "ice shelf cavity": "冰架下空腔",
    "ice shelves": "冰架",
    "ice shelf": "冰架",
    "sea-ice": "海冰",
    "sea ice": "海冰",
    "brine channels": "卤水通道",
    "melt ponds": "融池",
    "ice algae": "冰藻",
    "subglacial": "冰下",
    "permafrost active layer": "多年冻土活动层",
    "active layer": "活动层",
    "permafrost": "多年冻土",
    "shotgun metagenomics": "鸟枪法宏基因组测序",
    "viral metagenomics": "病毒宏基因组学",
    "metatranscriptomics": "宏转录组学",
    "metaproteomics": "宏蛋白质组学",
    "metagenomics": "宏基因组学",
    "metagenomic": "宏基因组",
    "microbiomes": "微生物组",
    "microbiome": "微生物组",
    "viromes": "病毒组",
    "virome": "病毒组",
    "bacteriophages": "噬菌体",
    "bacteriophage": "噬菌体",
    "prokaryotes": "原核生物",
    "prokaryotic": "原核生物",
    "eukaryotes": "真核生物",
    "eukaryotic": "真核生物",
    "archaea": "古菌",
    "bacteria": "细菌",
    "viruses": "病毒",
    "virus": "病毒",
    "flow cytometry": "流式细胞术",
    "amplicon sequencing": "扩增子测序",
    "chlorophyll a": "叶绿素 a",
    "dissolved organic carbon": "溶解有机碳",
    "particulate organic carbon": "颗粒有机碳",
    "dissolved inorganic carbon": "溶解无机碳",
    "dissolved inorganic nutrients": "溶解无机营养盐",
    "primary production": "初级生产",
    "carbon fixation": "碳固定",
    "nitrogen fixation": "固氮作用",
    "denitrification": "反硝化作用",
    "nitrification": "硝化作用",
    "chemoautotrophy": "化能自养",
    "viral lysis": "病毒裂解",
    "lysogeny": "溶原状态",
    "host prediction": "宿主预测",
    "host links": "宿主关联",
    "co-occurrence": "共现关系",
    "assembly": "组装",
    "assemblies": "组装结果",
    "catalogues": "目录",
    "catalogue": "目录",
    "polynyas": "冰间湖",
    "polynya": "冰间湖",
    "plastisphere": "塑料际",
    "holobiont": "共生整体",
    "primary productivity": "初级生产力",
    "productivity": "生产力",
    "Fram Strait": "弗拉姆海峡",
    "Bering Strait": "白令海峡",
    "Chukchi Sea": "楚科奇海",
    "Beaufort Sea": "波弗特海",
    "Barents Sea": "巴伦支海",
    "Weddell Sea": "威德尔海",
    "Ross Sea": "罗斯海",
    "Amundsen Sea": "阿蒙森海",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def source_payload(source: dict) -> dict:
    profile = source["study_profile"]
    return {
        "title": source["title"],
        "study_type": source["study_type"],
        "study_profile": {
            "spatial_scope": profile["spatial_scope"],
            "temporal_scope": profile["temporal_scope"],
            "sample_design": profile["sample_design"],
            "measured_or_derived": profile["measured_or_derived"],
        },
        "key_findings": source["key_findings"],
        "limitations": source["limitations"],
        "cite_for": source["cite_for"],
        "do_not_overcite": source["do_not_overcite"],
        "curation_basis": source["curation"]["basis"],
    }


def claim_payload(claim: dict) -> dict:
    return {
        "statement": claim["statement"],
        "scope": claim["scope"],
        "evidence_basis": claim["evidence_basis"],
        "locator": claim["locator"],
        "confidence_note": claim["confidence_note"],
    }


def concept_payload(concept: dict) -> dict:
    return {"label": concept["label"], "description": concept["description"]}


def flatten(value, path=()):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from flatten(item, path + (index,))
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from flatten(item, path + (key,))


def set_path(target, path, value):
    current = target
    for part in path[:-1]:
        current = current[part]
    current[path[-1]] = value


def protect_terms(text: str) -> tuple[str, dict[str, str]]:
    protected = text
    replacements: dict[str, str] = {}
    terms = sorted(TERM_MAP.items(), key=lambda item: len(item[0]), reverse=True)
    for index, (english, chinese) in enumerate(terms):
        token = f"ZXQ{index:06d}QXZ"
        pattern = re.compile(r"(?<![A-Za-z])" + re.escape(english) + r"(?![A-Za-z])", re.IGNORECASE)
        if pattern.search(protected):
            protected = pattern.sub(token, protected)
            replacements[token] = chinese
    return protected, replacements


def polish(text: str) -> str:
    protected_phrases = {
        "社区知识": "ZXQ900001QXZ",
        "社区参与": "ZXQ900002QXZ",
        "社区优先": "ZXQ900003QXZ",
    }
    for phrase, token in protected_phrases.items():
        text = text.replace(phrase, token)
    fixes = (
        ("大会产生", "组装获得"), ("大会生成", "组装获得"), ("大会", "组装"),
        ("组件产生", "组装获得"), ("组件生成", "组装获得"),
        ("组分组件", "组分组装结果"), ("参考组件", "参考基因组组装结果"),
        ("所使用的组件恢复", "所采用的组装恢复率"),
        ("冰川前陆", "冰川前缘地"), ("元基因组", "宏基因组"),
        ("操作分类单位", "操作分类单元"), ("病毒操作分类单位", "病毒操作分类单元"),
        ("南极周极流", "南极绕极流"), ("南极环流", "南极绕极流"),
        ("有机体", "生物"), ("古细菌", "古菌"), ("活动性感染", "活跃感染"),
        ("大小分数", "粒级组分"), ("季节性丰富", "季节丰度"),
        ("开花演替", "藻华演替"), ("季节性水华", "季节性藻华"),
        ("社区", "群落"), ("群落复发", "群落复现"),
        ("群落继承", "群落演替"), ("群落集会", "群落构建"), ("群落组装", "群落构建"),
        ("细胞分数", "细胞粒级组分"), ("病毒分数", "病毒组分"),
        ("元条形码", "宏条形码分析"), ("中宇宙", "中尺度围隔实验"),
        ("南方冬季", "南半球冬季"), ("海洋终止冰川", "入海冰川"),
        ("体制转变", "生态格局转变"), ("制度转变", "生态格局转变"),
        ("海冰政权", "海冰格局"), ("海冰制度", "海冰格局"),
        ("营养通量", "营养盐通量"), ("天文台", "观测站"),
        ("极地熊", "北极熊"), ("颠覆性变化", "翻转环流变化"),
        ("核细胞病毒目", "Nucleocytoviricota 各目"),
        ("核细胞病毒门", "Nucleocytoviricota 门"), ("核细胞病毒", "Nucleocytoviricota"),
        ("横噬菌体", "crAss-like 噬菌体"), ("波林顿样", "Polinton 样"),
        ("尾虫", "丝足虫类"), ("海洋原生藻菌", "海洋异养型不等鞭毛类群（MAST）"),
        ("弹匣", "MAG"), ("弹夹", "MAG"), ("显着", "显著"),
        ("中高品质", "中高质量"), ("高级多样性", "高阶分类多样性"),
        ("宿主链接", "宿主关联"), ("巨噬细胞", "crAss-like 噬菌体"),
        ("南极核病毒", "南极 Nucleocytoviricota"),
        ("生产季节窗口", "高生产力季节时段"), ("生产季节", "高生产力季节"),
        ("元转录组", "宏转录组"), ("病毒片段读数", "病毒组分测序读段"),
        ("主机独占性", "宿主专一性"), ("主机链接", "宿主关联"),
        ("病毒——主机", "病毒—宿主"), ("主机", "宿主"),
        ("长读程序集", "长读长组装结果"), ("参考程序集", "参考基因组组装结果"),
        ("程序集", "组装结果"), ("装配", "组装"),
        ("宏基因组读取", "宏基因组测序读段"), ("读取招募", "测序读段招募"),
        ("读取映射", "测序读段比对"), ("读取图谱", "测序读段比对率"),
        ("HiFi 读取", "HiFi 测序读段"), ("Illumina 读取", "Illumina 测序读段"),
        ("驱动程序", "驱动者"), ("邻近链接", "邻近连接信息"),
        ("古 ASV", "古菌 ASV"), ("代谢行会", "代谢功能群"),
        ("政权过渡", "格局转变"), ("搁置反硝化作用预算", "陆架反硝化预算"),
        ("无花果。", "图"), ("代表一个人", "仅代表一个个体"),
        ("放线蕨直系同源物", "辐鳍鱼纲直系同源基因"),
        ("通过作图、k-mer", "通过序列比对、k-mer"),
        ("测序读段图谱超过", "测序读段比对率超过"),
        ("通用实验宿主确认", "普遍的实验宿主验证"),
        ("巨-病毒", "巨型病毒"),
        ("巨蛋白-病毒", "巨型病毒"), ("大量新颖性", "高度新颖性"),
        ("SAG分类法", "SAG 分类鉴定"), ("MAG分类法", "MAG 分类鉴定"),
        ("平均核苷酸同一性", "平均核苷酸一致性"),
        ("行会结构", "功能群结构"), ("公会", "功能群"),
        ("直接清洁进入冰下湖时获得的样品", "通过洁净钻探直接进入冰下湖后获得的样品"),
        ("澳大利亚夏季", "南半球夏季"), ("澳大利亚春季", "南半球春季"),
        ("澳大利亚冬季", "南半球冬季"), ("澳大利亚季节", "南半球季节"),
        ("南方-夏季", "南半球夏季"), ("南方夏季", "南半球夏季"),
        ("加工速率", "过程速率"), ("环境协会", "环境关联"),
        ("古环境协会", "古环境关联"), ("冰流协会", "冰流关联"),
        ("代理协会", "代用指标关联"), ("冰川融化协会", "冰川融水关联"),
        ("协会网络", "关联网络"),
        ("养分利用率", "营养盐可用性"), ("开花时间", "藻华时间"),
        ("开花区", "藻华面积"), ("春季开花", "春季藻华"),
        ("熔体贡献", "融化贡献"), ("地区特有现象", "区域特有性"),
        ("在观察到的条件下，熔体变暗占总表面熔化量的 2.4%。", "在观测条件下，藻华导致的表面变暗对地表总融化量的贡献最高达 2.4%。"),
        ("群落以绿藻纲、三线藻纲和钩线藻纲为主；钩线虫变异表明存在大量未充分表征的区域多样性。", "群落以绿藻纲（Chlorophyceae）、Trebouxiophyceae 和 Ancylonema 为主；Ancylonema 的变异表明该地区仍存在大量未被充分表征的多样性。"),
        ("高夫的人口患病率", "高夫岛种群中的感染率"),
        ("人群患病率", "种群感染率"), ("未解决内部不一致", "尚未厘清内部不一致"),
        ("两项调查均以夏末为样本，因此季节性演替和冬季群落仍未解决。", "两项调查均在夏末采样，因此尚不能解析季节演替及冬季群落。"),
        ("年份之间的不平等站点", "两年间采样站数量不一致"),
        ("映射读数", "比对测序读段"),
        ("微观世界", "微宇宙实验"), ("海冰熔炼缩影", "海冰融化微宇宙实验"),
        ("短海冰熔体微宇宙实验", "短期海冰融化微宇宙实验"),
        ("海冰熔体供应铁", "海冰融水输入铁"), ("海冰熔体的归因", "海冰融水来源归因"),
        ("熔体分数", "融化比例"), ("布卢姆变暗", "藻华致暗"),
        ("掠过", "摄食"), ("当代邮轮调查", "当代科考航次调查"),
        ("船上孵化", "船载培养实验"), ("清洁船载培养实验", "无痕量金属污染船载培养实验"),
        ("SCALE 巡航", "SCALE 科考航次"), ("南极环球航行收藏", "南极绕极航行采样集"),
        ("开放式流层薄冰", "开放漂流区的饼状冰"),
        ("95% ANI/85% 比对分数", "95% ANI/85% 比对覆盖比例"),
        ("基于序列的分类法", "基于序列的分类鉴定"),
        ("相对读取信号", "相对测序读段信号"), ("样读数", "样测序读段"),
        ("Illumina DNA 和 RNA 读数", "Illumina DNA 和 RNA 测序读段"),
        ("菌株特异性读数对", "菌株特异性测序读段由分类器对"),
        ("底栖微生物垫", "底栖微生物席"), ("湖垫", "湖泊微生物席"),
        ("17 个垫子", "17 个微生物席"), ("垫子之间", "微生物席之间"),
        ("一张垫子", "一处微生物席"), ("极地垫轮廓", "极地微生物席模式"),
        ("极性微生物垫", "极地微生物席"),
        ("这些垫子", "这些微生物席"), ("湖泊微生物垫", "湖泊微生物席"),
        ("澳大利亚夏末", "南半球夏末"), ("同一性", "一致性"),
        ("双极", "两极"), ("Giant-病毒", "巨型病毒"),
        ("极性病毒", "极地病毒"), ("极性相关基因", "极地相关基因"),
        ("非极性海绵", "非极地海绵"), ("极性限制", "极地限定"),
        ("完全的极性分布", "极地限定分布"), ("极性分布", "极地分布"),
        ("仅出现极性", "仅在极地出现"), ("环极性颜料合成", "环极诊断色素综合分析"),
        ("每个极性相关基因", "每个极地相关基因"), ("极性基因组", "极地相关基因组"),
        ("各类船用病毒", "各类海洋病毒"), ("唯一的司机", "唯一的驱动因素"),
        ("人口特有现象", "种群特有性"), ("人口", "种群"),
        ("签名人群", "特征种群"), ("居民微生物组", "常驻微生物组"),
        ("常住种群", "常驻种群"), ("季节性波动的种群", "季节波动种群"),
        ("整个北极地区的制服更换", "整个北极范围内一致的群落替代"),
        ("货架", "大陆架"), ("省份", "分区"), ("放牧", "摄食"),
        ("气海碳汇", "海气碳汇"), ("固定植物", "定鞭藻"),
        ("附着植物", "定鞭藻"), ("隐生植物", "隐藻"), ("隐植物", "隐藻"),
        ("疣微生物", "疣微菌门"), ("恢复的拟杆菌和疣微菌门基因组", "重建获得的拟杆菌门和疣微菌门基因组"),
        ("碳出口", "碳输出"), ("潜在的碳输出影响", "对碳输出的潜在影响"),
        ("该地区是一个巨大的大气净碳汇", "该区域是显著的净大气碳汇"),
        ("微生物回收", "微生物再循环"), ("固定碳到达深度", "固定碳输送至深层"),
        ("不同的出口范围和方法", "不同的碳输出参考深度与方法"),
        ("审查规模范围", "综述尺度的估计范围"), ("南大洋碳输出管制", "南大洋碳输出的控制因素"),
        ("审查指出", "综述指出"), ("该审查", "该综述"),
        ("区域审查综合", "区域综述整合"), ("审查摘要", "综述摘要"),
        ("审查结论", "综述结论"), ("审查雷达", "综述整合雷达"),
        ("评论文本", "综述文本"), ("评论材料", "综述材料"),
        ("评论摘要", "综述摘要"), ("开放获取评论", "开放获取综述"),
        ("海洋地质学和构造学评论", "海洋地质与构造综述"),
        ("该评论", "该综述"), ("评论：", "综述："),
        ("易于理解的全文", "可获取的全文"), ("易于理解的出版商文本", "可获取的出版商文本"),
        ("易于理解的综述文本", "可获取的综述文本"),
        ("摇滚时代", "岩石年龄"), ("超级大陆", "超大陆"),
        ("太古代寒武纪", "太古代至寒武纪"), ("地球年代学", "地质年代学"),
        ("稀有的沿海露头", "稀少的沿海露头"),
        ("均匀的东南南极地壳", "均一的东南极地壳"),
        ("最近的矿物学和地质年代学限制", "最新矿物学与地质年代学约束"),
        ("每个冰雪覆盖区域下方的直接地质学", "每个冰雪覆盖区下方的直接地质证据"),
        ("瓶子孵化", "瓶中培养"), ("CAN SINE 和 LINE 签名", "CAN SINE 与 LINE 特征"),
        ("横截面", "横断面"), ("在架下", "在冰架下"), ("冰下洞穴", "冰架下空腔"),
        ("活动信号", "活性信号"), ("溶源生活方式", "溶原生活史"),
        ("每个回收的病毒", "每个重建获得的病毒"),
        ("易于理解的出版商全文", "可获取的出版商全文"),
        ("可访问的", "可获取的"), ("摘要且", "摘要及"),
        ("探险", "科考"), ("无法解决", "无法解析"), ("仍未解决", "尚未厘清"),
        ("案例研究解决了", "案例研究解析了"),
        ("集会制度", "群落构建格局"), ("永久制度", "永久性格局"),
        ("输出制度", "输出格局"), ("政权转变", "格局转变"),
        ("低范围状态", "低面积格局"),
        ("数据受限的海洋生物地球化学产品", "受观测数据约束的海洋生物地球化学产品"),
        ("水华绘图", "藻华范围制图"), ("无需咨询初步研究", "未查阅原始研究"),
        ("特别是当审查涉及更广泛的组合时微生物底栖生物", "综述所讨论的更广泛底栖生物群集中的微生物底栖类群"),
        ("沿海通量与近海南大洋输出格局不同", "沿岸通量不同于南大洋外海输出格局"),
        ("该时机支持耦合的格局转变", "这一时间对应关系支持相互耦合的格局转变"),
        ("架子回收", "陆架再循环"), ("常量营养素", "宏量营养盐"),
        ("近海水域的生长和宏量营养盐的减少", "外海水域的浮游植物生长和宏量营养盐消耗"),
        ("未来固定碳汇", "固定不变的未来碳汇"),
        ("微观范围", "微宇宙实验范围"), ("giant-病毒", "巨型病毒"),
        ("Mercer 冰下 Lake", "默瑟冰下湖"), ("扩增和排序", "扩增和测序"),
        ("机载磁图案", "机载航磁图"), ("再加工", "改造"),
        ("网格观测产品", "网格化观测产品"), ("生态生活方式", "生态策略"),
        ("冰层密集的水域", "海冰密集覆盖水域"),
        ("大西洋的流入和冰层的减少", "大西洋水输入和海冰减少"),
        ("大西洋的流入和冰的减少", "大西洋水输入和海冰减少"),
        ("细菌状况", "细菌群落格局"), ("实验孤立原因", "实验上单独验证的原因"),
        ("栖息地宽度", "生境广度"),
        ("38 种生境通才、111 种专家", "38 个生境广适种、111 个生境专性种"),
        ("固定与隔离的状态", "特有性与隔离状态"),
        ("解决了不同的早期和晚期生长部分", "区分出不同的早期与晚期生长组分"),
        ("分类单元解决的早期和晚期生长", "分类单元分辨的早期与晚期生长"),
        ("大量非增长多样性部分", "大量未检测到生长的多样性组分"),
        ("水文地理状况", "水文分区"),
        ("仅回收了两块易碎的腐烂絮凝物，并且一块尝试的絮凝物解体，限制了复制和标准化。", "仅成功采集了两块脆弱的腐化浮冰，另一次浮冰采样过程中样品解体，因此重复性和标准化程度有限。"),
        ("架子、斜坡、盆地、山脊、窗台和通道", "大陆架、陆坡、海盆、海岭、海槛和通道"),
        ("结构化摘要和易于理解的支持文章摘要", "结构化摘要及可获取的文章补充摘要"),
        ("结构化抽象且易于理解的纸质文本", "结构化摘要及可获取的论文正文"),
        ("数据受限的底栖氮循环建模研究", "受观测数据约束的底栖氮循环模拟研究"),
        ("融水池", "融池"), ("2026 年发布的当代隔离调查", "发表于 2026 年的当代分离株调查"),
        ("成功隔离", "成功分离"),
        ("隔离表明了收集的可行性，但不表明区域丰富度或生态优势。", "分离培养证实了病毒活性，但不能代表其区域丰富度或生态优势。"),
        ("现有参考文献的相似度", "现有参考基因组的相似度"),
        ("南极洲和瑞士沿海地区", "南极和瑞士冰川前缘地"),
        ("候选冷/共生功能", "候选冷适应与共生功能"),
        ("未来亚特兰化结果", "未来大西洋化情景下的结果"),
        ("排他性估计", "专一性估计"), ("高度微观多样性", "高度微多样性"),
        ("卫星海洋颜色", "卫星海色遥感产品"), ("能源景观", "能量景观"),
        ("对预期的亚特兰化具有更大的适应性", "面对预期的大西洋化具有更强恢复力"),
        ("操作性实验", "操纵实验"),
        ("短读映射", "短读长序列比对"), ("冰块预测", "冰盖变化预测"),
        ("PacBio HiFi 读数", "PacBio HiFi 测序读段"),
        ("两条病毒", "两株病毒"), ("微胞菌菌株", "Micromonas polaris 株系"),
        ("批量海冰宏基因组学", "常规海冰宏基因组学"),
        ("批量 0.2 微米过滤器宏基因组", "0.2 µm 滤膜常规宏基因组"),
        ("五天的叶绿素反应并不能隔离所有共同限制的营养物质、物种转变或长期生态系统反应。", "五天叶绿素响应实验无法分别检验所有共同限制营养盐、物种更替或长期生态系统响应。"),
        ("阶段解析结果", "溶解态—颗粒态分级结果"),
        ("上层冰上", "海冰上层"), ("既成为管道又成为暂时的储存库", "既充当输送通道，也构成暂时储库"),
        ("氨氧化亚硝化菌宿主", "氨氧化古菌“候选”Nitrosopumilus 宿主"),
        ("公共加入", "公共数据登录号"), ("引线", "开阔水道"),
        ("全局测序读段招募", "全球数据集测序读段招募"),
        ("存放的原始读数", "已归档的原始测序读段"),
        ("映射和 BUSCO", "序列比对和 BUSCO"),
        ("537 个分类 vOTU", "537 个已分类的 vOTU"),
        ("尾号为噬菌体的订单。", "有尾噬菌体的一个分类目。"),
        ("原先被视为病毒的培养物", "原先被视为单一病毒的培养物"),
        ("之前被视为病毒的培养物", "原先被视为单一病毒的培养物"),
        ("在单次感染中，MpoV-44T.A 可以更快地裂解共享的北极微胞菌宿主；在等粒子双重感染中，MpoV-44T.B基因组产量下降至其单次感染产量的18正负8%。", "在单独感染中，MpoV-44T.A 对共同的极地微单胞藻（Micromonas polaris）宿主裂解更快；在等病毒颗粒数的双重感染中，MpoV-44T.B 的基因组产量降至单独感染时的 18 ± 8%。"),
        ("尽管实验室竞争较弱，但在分析的北极塔拉宏基因组中，MpoV-44T.B 样测序读段明显比 MpoV-44T.A 样测序读段丰富。", "尽管 MpoV-44T.B 在实验室竞争中较弱，但在所分析的 Tara 北极宏基因组中，MpoV-44T.B 样测序读段显著多于 MpoV-44T.A 样测序读段。"),
        ("对比北极小单胞菌的感染和双重竞争动态", "比较两株病毒感染极地微单胞藻时的动力学与双重感染竞争"),
        ("所有北极天然浮游植物的竞争等级病毒", "所有北极天然浮游植物—病毒系统中的竞争排序"),
        ("结构化摘要和可获取的支持文章摘要", "结构化摘要及可获取的文章补充摘要"),
    )
    for before, after in fixes:
        text = text.replace(before, after)
    text = re.sub(r"长读(?!长)", "长读长", text)
    text = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", text)
    text = re.sub(r"\s+([，。；：！？、）])", r"\1", text)
    text = re.sub(r"（\s+", "（", text)
    for phrase, token in protected_phrases.items():
        text = text.replace(token, phrase)
    return text.strip()


def normalize_translation(value):
    if isinstance(value, str):
        return polish(value)
    if isinstance(value, list):
        return [normalize_translation(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_translation(item) for key, item in value.items()}
    return value


def request_translation(text: str, attempts: int = 5) -> str:
    encoded = urllib.parse.urlencode({
        "client": "dict-chrome-ex", "sl": "en", "tl": "zh-CN", "dt": "t", "q": text,
    }).encode()
    for attempt in range(attempts):
        last_error = None
        for url in TRANSLATE_URLS:
            request = urllib.request.Request(
                url,
                data=encoded,
                headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0"},
            )
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    payload = json.load(response)
                return "".join(part[0] for part in payload[0])
            except Exception as exc:
                last_error = exc
        if attempt + 1 == attempts and last_error:
            raise last_error
        time.sleep(2.5 * (attempt + 1))
    raise RuntimeError("translation request failed")


def translate_strings(strings: list[str], cache: dict[str, str]) -> list[str]:
    output: list[str] = [""] * len(strings)
    pending: list[tuple[int, str, dict[str, str]]] = []
    for index, text in enumerate(strings):
        if text in cache:
            output[index] = cache[text]
            continue
        protected, replacements = protect_terms(text)
        pending.append((index, protected, replacements))

    # Keep requests short enough for the public endpoint while amortizing latency.
    cursor = 0
    while cursor < len(pending):
        batch: list[tuple[int, str, dict[str, str]]] = []
        char_count = 0
        while cursor < len(pending):
            candidate = pending[cursor]
            next_size = char_count + len(candidate[1]) + len(SPLITTER) + 2
            if batch and next_size > 5200:
                break
            batch.append(candidate)
            char_count = next_size
            cursor += 1
        joined = f"\n{SPLITTER}\n".join(item[1] for item in batch)
        translated = request_translation(joined)
        parts = translated.split(SPLITTER)
        if len(parts) != len(batch):
            # Fall back to individual requests when a provider alters a separator.
            parts = [request_translation(item[1]) for item in batch]
        for (index, _protected, replacements), part in zip(batch, parts):
            value = part.strip()
            for token, chinese in replacements.items():
                value = value.replace(token, chinese)
            value = polish(value)
            output[index] = value
            cache[strings[index]] = value
        time.sleep(0.12)
    return output


def translate_payload(payload: dict, cache: dict[str, str]) -> dict:
    result = json.loads(json.dumps(payload, ensure_ascii=False))
    paths_and_strings = list(flatten(payload))
    translated = translate_strings([value for _, value in paths_and_strings], cache)
    for (path, _), value in zip(paths_and_strings, translated):
        set_path(result, path, value)
    return result


def status(translations: dict, sources: list[dict], claims: list[dict], concepts: list[dict]):
    groups = {
        "sources": (sources, source_payload),
        "claims": (claims, claim_payload),
        "concepts": (concepts, concept_payload),
    }
    missing = []
    stale = []
    for group, (records, payload_for) in groups.items():
        existing = translations.get(group, {})
        for record in records:
            record_id = record["id"]
            entry = existing.get(record_id)
            if not entry:
                missing.append(f"{group}:{record_id}")
            elif entry.get("_source_hash") != digest(payload_for(record)):
                stale.append(f"{group}:{record_id}")
    return missing, stale


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", action="store_true", help="translate missing or changed records")
    parser.add_argument("--force", action="store_true", help="regenerate all translated records")
    parser.add_argument(
        "--group", choices=("all", "concepts", "sources", "claims"), default="all",
        help="limit generation to one translation group",
    )
    args = parser.parse_args()

    sources = load_json(DATA / "sources.json")
    claims = load_json(DATA / "claims.json")
    concepts = load_json(DATA / "concepts.json")
    if OUTPUT.exists():
        translations = load_json(OUTPUT)
    else:
        translations = {"sources": {}, "claims": {}, "concepts": {}}

    translations["schema_version"] = "1.0"
    translations["language"] = "zh-CN"
    translations["source_language"] = "en"
    translations["ui"] = {"en": UI_EN, "zh-CN": UI_ZH}
    translations["labels"] = LABELS_ZH
    translations.setdefault("sources", {})
    translations.setdefault("claims", {})
    translations.setdefault("concepts", {})

    missing, stale = status(translations, sources, claims, concepts)
    if not args.generate:
        print(f"Chinese translation coverage: {len(missing)} missing, {len(stale)} stale.")
        if missing:
            print("Missing: " + ", ".join(missing[:12]) + ("…" if len(missing) > 12 else ""))
        if stale:
            print("Stale: " + ", ".join(stale[:12]) + ("…" if len(stale) > 12 else ""))
        return 1 if missing or stale else 0

    cache: dict[str, str] = {}
    groups = (
        ("concepts", concepts, concept_payload),
        ("sources", sources, source_payload),
        ("claims", claims, claim_payload),
    )
    if args.group != "all":
        groups = tuple(group for group in groups if group[0] == args.group)
    total_changed = 0
    for group, records, payload_for in groups:
        pending_records = []
        all_strings = []
        for record in records:
            payload = payload_for(record)
            fingerprint = digest(payload)
            existing = translations[group].get(record["id"])
            if not args.force and existing and existing.get("_source_hash") == fingerprint:
                continue
            paths_and_strings = list(flatten(payload))
            pending_records.append((record["id"], payload, fingerprint, paths_and_strings, len(all_strings)))
            all_strings.extend(value for _, value in paths_and_strings)

        if not pending_records:
            continue
        print(f"Translating {len(pending_records)} {group} record(s)…", flush=True)
        translated_strings = translate_strings(all_strings, cache)
        for record_id, payload, fingerprint, paths_and_strings, offset in pending_records:
            translated = json.loads(json.dumps(payload, ensure_ascii=False))
            values = translated_strings[offset:offset + len(paths_and_strings)]
            for (path, _), value in zip(paths_and_strings, values):
                set_path(translated, path, value)
            translated["_source_hash"] = fingerprint
            translations[group][record_id] = translated
            total_changed += 1
        translations["generated_at"] = datetime.now(timezone.utc).isoformat()
        OUTPUT.write_text(json.dumps(translations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Translated {total_changed} changed record(s) in total.", flush=True)

    for group in ("concepts", "sources", "claims"):
        translations[group] = normalize_translation(translations[group])
    for concept_id, label in CONCEPT_LABEL_OVERRIDES_ZH.items():
        if concept_id in translations["concepts"]:
            translations["concepts"][concept_id]["label"] = label
    for source in sources:
        override = SOURCE_TITLE_OVERRIDES_ZH.get(source["title"])
        if override and source["id"] in translations["sources"]:
            translations["sources"][source["id"]]["title"] = override
    for source_id, fields in SOURCE_CONTENT_OVERRIDES_ZH.items():
        if source_id in translations["sources"]:
            translations["sources"][source_id].update(fields)
    for claim_id, fields in CLAIM_CONTENT_OVERRIDES_ZH.items():
        if claim_id in translations["claims"]:
            translations["claims"][claim_id].update(fields)

    valid_source_ids = {record["id"] for record in sources}
    valid_claim_ids = {record["id"] for record in claims}
    valid_concept_ids = {record["id"] for record in concepts}
    for group, valid_ids in (("sources", valid_source_ids), ("claims", valid_claim_ids), ("concepts", valid_concept_ids)):
        translations[group] = {key: value for key, value in translations[group].items() if key in valid_ids}

    translations["generated_at"] = datetime.now(timezone.utc).isoformat()
    translations["translation_note"] = "Terminology-normalized Simplified-Chinese reading translation; English evidence records remain canonical."
    OUTPUT.write_text(json.dumps(translations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    missing, stale = status(translations, sources, claims, concepts)
    print(f"Chinese translation coverage: {len(missing)} missing, {len(stale)} stale; {total_changed} updated.")
    return 1 if missing or stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
