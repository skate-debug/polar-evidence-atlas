#!/usr/bin/env python3
"""Build portable graph exports, bibliography, and the self-contained explorer."""

from __future__ import annotations

import csv
import html
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DIST = ROOT / "dist"
REFERENCES = ROOT / "references"
TEMPLATE = ROOT / "web" / "template.html"
APP = ROOT / "web" / "app.js"
ARTICLE = ROOT / "article" / "polar-earth-systems-introduction.md"


def load(path: Path, fallback=None):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def public_fallback(name: str) -> Path:
    """Prefer the private working cache, then its abstract-free public snapshot."""
    private_path = DATA / name
    return private_path if private_path.exists() else DATA / "public" / name


def one(value):
    if isinstance(value, list):
        value = value[0] if value else ""
    return html.unescape(value or "") if isinstance(value, str) else value or ""


def author_name(author: dict, family_first: bool = False) -> str:
    if author.get("literal"):
        return author["literal"]
    given = author.get("given", "").strip()
    family = author.get("family", "").strip()
    if family_first and family:
        return f"{family}, {given}".strip().rstrip(",")
    return " ".join(part for part in (given, family) if part)


def issued_date(record: dict) -> str:
    parts = record.get("issued", {}).get("date-parts", [[]])
    if not parts or not parts[0]:
        return ""
    values = [str(value) for value in parts[0]]
    if len(values) > 1:
        values[1] = values[1].zfill(2)
    if len(values) > 2:
        values[2] = values[2].zfill(2)
    return "-".join(values)


def slim_metadata(source: dict, metadata: dict) -> dict:
    authors = [author_name(author) for author in metadata.get("author", [])]
    return {
        "authors": authors,
        "author_short": (
            authors[0] + (" et al." if len(authors) > 1 else "") if authors else ""
        ),
        "journal": one(metadata.get("container-title")),
        "published": issued_date(metadata),
        "volume": str(metadata.get("volume", "")),
        "issue": str(metadata.get("issue", "")),
        "pages": str(metadata.get("page", "")),
        "publisher": str(metadata.get("publisher", "")),
        "type": str(metadata.get("type", "article-journal")),
        "url": f"https://doi.org/{source['doi']}",
    }


def bib_escape(value: str) -> str:
    value = value.replace("\\", "\\textbackslash{}")
    for before, after in (("&", "\\&"), ("%", "\\%"), ("#", "\\#")):
        value = value.replace(before, after)
    return value


def bibtex(source: dict, metadata: dict) -> str:
    authors = " and ".join(author_name(author, family_first=True) for author in metadata.get("author", []))
    journal = one(metadata.get("container-title"))
    fields = [
        ("author", authors),
        ("title", source["title"]),
        ("journal", journal),
        ("year", str(source["year"])),
        ("volume", str(metadata.get("volume", ""))),
        ("number", str(metadata.get("issue", ""))),
        ("pages", str(metadata.get("page", ""))),
        ("doi", source["doi"]),
        ("url", f"https://doi.org/{source['doi']}"),
    ]
    body = ",\n".join(f"  {name} = {{{bib_escape(value)}}}" for name, value in fields if value)
    return f"@article{{{source['citation_key']},\n{body}\n}}"


def source_concept_edges(source: dict) -> list[tuple[str, str, str]]:
    profile = source["study_profile"]
    values: list[tuple[str, str, str]] = []
    for pole in source["poles"]:
        pole_id = {
            "Arctic": "pole:arctic",
            "Antarctic": "pole:antarctic",
            "Bipolar": "pole:bipolar",
        }.get(pole)
        if pole_id:
            values.append((source["id"], pole_id, "covers_pole"))
    for region in source.get("regions", []):
        values.append((source["id"], region, "covers_region"))
    for domain in source["domains"]:
        values.append((source["id"], "domain:" + re.sub(r"[^a-z0-9]+", "-", domain.lower()).strip("-"), "covers_domain"))
    for field, predicate in (
        ("habitats", "samples"),
        ("methods", "uses_method"),
        ("focal_taxa", "studies_taxon"),
        ("focal_processes", "studies_process"),
        ("environmental_drivers", "evaluates_driver"),
    ):
        for concept in profile.get(field, []):
            values.append((source["id"], concept, predicate))
    return values


def main() -> int:
    DIST.mkdir(exist_ok=True)
    REFERENCES.mkdir(exist_ok=True)
    sources = load(DATA / "sources.json", [])
    concepts = load(DATA / "concepts.json", [])
    claims = load(DATA / "claims.json", [])
    locations = load(DATA / "locations.geojson", {"type": "FeatureCollection", "features": []})
    metadata_payload = load(public_fallback("metadata.json"), {"records": {}})
    metadata_records = metadata_payload.get("records", {})
    candidates_payload = load(public_fallback("candidates.json"), {"candidates": []})
    candidate_reviews = load(DATA / "candidate_reviews.json", {"reviews": []})
    candidate_verifications = load(DATA / "candidate_verifications.json", {"records": []})
    translations = load(DATA / "i18n.zh-CN.json", {})
    taxonomy = load(ROOT / "config" / "collections.json", {})
    seep_inventory = load(public_fallback("cold_seep_candidates.json"), {"candidates": []})
    current_candidate_ids = {candidate.get("id") for candidate in candidates_payload.get("candidates", [])}
    current_reviews = [
        review for review in candidate_reviews.get("reviews", [])
        if review.get("candidate_id") in current_candidate_ids
    ]
    review_counts = Counter(review.get("decision", "unreviewed") for review in current_reviews)
    current_verifications = [
        record for record in candidate_verifications.get("records", [])
        if record.get("candidate_id") in current_candidate_ids
    ]
    verification_counts = Counter(
        record.get("verification_stage", "unverified") for record in current_verifications
    )
    promotion_counts = Counter(
        "promoted_to_curated_graph" if record.get("candidate_id") in {
            source.get("candidate_id") for source in sources if source.get("candidate_id")
        } else record.get("promotion_recommendation", "undecided")
        for record in current_verifications
    )

    citation_keys = {source["citation_key"] for source in sources}
    if ARTICLE.exists():
        used_keys = set(re.findall(r"@([A-Za-z][A-Za-z0-9_-]+)", ARTICLE.read_text(encoding="utf-8")))
        unknown = sorted(used_keys - citation_keys)
        if unknown:
            raise SystemExit("Unknown article citation key(s): " + ", ".join(unknown))

    enriched_sources = []
    bib_records = []
    for source in sources:
        item = dict(source)
        item["collection"] = source.get("collection", "polar")
        item["geographic_scopes"] = source["poles"] or (["South China Sea"] if item["collection"] == "scs-cold-seeps" else ["Global"])
        if item["collection"] == "scs-cold-seeps" and "comparative" in source.get("sites", []):
            item["geographic_scopes"].append("Global")
        record = metadata_records.get(source["doi"].lower(), {})
        item["bibliographic"] = slim_metadata(source, record)
        item["bibtex"] = bibtex(source, record)
        enriched_sources.append(item)
        bib_records.append(item["bibtex"])

    domain_values = sorted({domain for source in sources for domain in source["domains"]})
    domain_nodes = [
        {
            "id": "domain:" + re.sub(r"[^a-z0-9]+", "-", domain.lower()).strip("-"),
            "type": "Domain",
            "label": domain,
            "description": f"Curated literature area: {domain}.",
        }
        for domain in domain_values
    ]
    nodes = [
        {
            "id": concept["id"],
            "type": concept["type"],
            "label": concept["label"],
            "description": concept["description"],
            "broader": concept.get("broader", ""),
        }
        for concept in concepts
    ] + domain_nodes + [
        {
            "id": source["id"],
            "type": "Source",
            "label": source["title"],
            "description": source["study_type"],
            "year": source["year"],
            "domains": source["domains"],
            "poles": source["poles"],
            "doi": source["doi"],
            "collection": source.get("collection", "polar"),
            "regions": source.get("regions", []),
            "compartments": source.get("compartments", []),
            "topics": source.get("topics", []),
            "sites": source.get("sites", []),
        }
        for source in sources
    ]

    edges = []
    edge_index = 1
    for concept in concepts:
        if concept.get("broader"):
            edges.append({
                "id": f"edge:{edge_index:04d}", "source": concept["id"],
                "target": concept["broader"], "predicate": "broader",
            })
            edge_index += 1
    for source in sources:
        for start, end, predicate in source_concept_edges(source):
            edges.append({
                "id": f"edge:{edge_index:04d}", "source": start,
                "target": end, "predicate": predicate,
            })
            edge_index += 1
    for claim in claims:
        edges.append({
            "id": f"edge:{edge_index:04d}",
            "source": claim["subject"],
            "target": claim["object"],
            "predicate": claim["predicate"],
            "claim_id": claim["id"],
            "source_id": claim["source_id"],
            "evidence_type": claim["evidence_type"],
            "confidence": claim["confidence"],
            "statement": claim["statement"],
        })
        edge_index += 1

    domain_counts = Counter(domain for source in sources for domain in source["domains"])
    pole_counts = Counter(pole for source in sources for pole in source["poles"])
    year_counts = Counter(str(source["year"]) for source in sources)
    evidence_counts = Counter(claim["evidence_type"] for claim in claims)
    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "generated_at": generated_at,
        "sources": enriched_sources,
        "claims": claims,
        "concepts": concepts,
        "domains": domain_values,
        "locations": locations,
        "nodes": nodes,
        "edges": edges,
        "i18n": translations,
        "taxonomy": taxonomy,
        "cold_seep_library": {
            "since": seep_inventory.get("since", ""),
            "until": seep_inventory.get("until", ""),
            "generated_at": seep_inventory.get("generated_at", ""),
            "papers": [
                {key: item.get(key, "") for key in (
                    "id", "title", "authors", "journal", "year", "publication_date", "doi", "pmcid", "url",
                    "compartments", "topics", "sites", "priority", "classification_basis", "publication_stage",
                )}
                for item in seep_inventory.get("candidates", [])
            ],
        },
        "candidate_summary": {
            "count": len(candidates_payload.get("candidates", [])),
            "screened": len(current_reviews),
            "unreviewed": max(0, len(candidates_payload.get("candidates", [])) - len(current_reviews)),
            "review_counts": dict(sorted(review_counts.items())),
            "verification_counts": dict(sorted(verification_counts.items())),
            "promotion_counts": dict(sorted(promotion_counts.items())),
            "generated_at": candidates_payload.get("generated_at", ""),
            "since": candidates_payload.get("since", ""),
        },
        "stats": {
            "sources": len(sources),
            "claims": len(claims),
            "concepts": len(concepts),
            "recent_sources": sum(source["year"] >= 2024 for source in sources),
            "domain_counts": dict(sorted(domain_counts.items())),
            "pole_counts": dict(sorted(pole_counts.items())),
            "year_counts": dict(sorted(year_counts.items())),
            "evidence_counts": dict(sorted(evidence_counts.items())),
            "collection_counts": dict(sorted(Counter(item["collection"] for item in enriched_sources).items())),
        },
    }

    (DIST / "graph.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (REFERENCES / "polar-kg.bib").write_text("\n\n".join(bib_records) + "\n", encoding="utf-8")
    (REFERENCES / "earth-ocean-kg.bib").write_text("\n\n".join(bib_records) + "\n", encoding="utf-8")

    with (DIST / "nodes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "type", "label", "description", "year", "domains", "poles", "doi", "collection", "regions", "compartments", "topics", "sites"])
        writer.writeheader()
        for node in nodes:
            writer.writerow({
                "id": node.get("id", ""), "type": node.get("type", ""),
                "label": node.get("label", ""), "description": node.get("description", ""),
                "year": node.get("year", ""), "domains": "|".join(node.get("domains", [])),
                "poles": "|".join(node.get("poles", [])), "doi": node.get("doi", ""),
                "collection": node.get("collection", ""), "regions": "|".join(node.get("regions", [])),
                "compartments": "|".join(node.get("compartments", [])), "topics": "|".join(node.get("topics", [])), "sites": "|".join(node.get("sites", [])),
            })
    with (DIST / "edges.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["id", "source", "target", "predicate", "claim_id", "source_id", "evidence_type", "confidence", "statement"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for edge in edges:
            writer.writerow({field: edge.get(field, "") for field in fields})

    graphml_nodes = "\n".join(
        f'    <node id="{html.escape(node["id"], quote=True)}"><data key="d0">{html.escape(node["type"])}</data><data key="d1">{html.escape(node["label"])}</data></node>'
        for node in nodes
    )
    graphml_edges = "\n".join(
        f'    <edge id="{html.escape(edge["id"], quote=True)}" source="{html.escape(edge["source"], quote=True)}" target="{html.escape(edge["target"], quote=True)}"><data key="d2">{html.escape(edge["predicate"])}</data></edge>'
        for edge in edges
    )
    graphml = f'''<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <key id="d0" for="node" attr.name="type" attr.type="string"/>
  <key id="d1" for="node" attr.name="label" attr.type="string"/>
  <key id="d2" for="edge" attr.name="predicate" attr.type="string"/>
  <graph id="polar-kg" edgedefault="directed">
{graphml_nodes}
{graphml_edges}
  </graph>
</graphml>
'''
    (DIST / "graph.graphml").write_text(graphml, encoding="utf-8")

    jsonld_graph = []
    for concept in concepts + domain_nodes:
        item = {
            "@id": concept["id"], "@type": "pkg:" + concept["type"],
            "rdfs:label": concept["label"], "schema:description": concept["description"],
        }
        if concept.get("broader"):
            item["skos:broader"] = {"@id": concept["broader"]}
        jsonld_graph.append(item)
    for source in sources:
        jsonld_graph.append({
            "@id": source["id"], "@type": "schema:ScholarlyArticle",
            "schema:name": source["title"], "schema:datePublished": source["year"],
            "schema:identifier": source["doi"], "schema:sameAs": f"https://doi.org/{source['doi']}",
        })
    for claim in claims:
        jsonld_graph.append({
            "@id": claim["id"], "@type": "pkg:Claim",
            "schema:text": claim["statement"],
            "pkg:subject": {"@id": claim["subject"]},
            "pkg:predicate": claim["predicate"],
            "pkg:object": {"@id": claim["object"]},
            "prov:wasDerivedFrom": {"@id": claim["source_id"]},
            "pkg:evidenceType": claim["evidence_type"], "pkg:confidence": claim["confidence"],
        })
    jsonld = {
        "@context": {
            "pkg": "https://example.org/polar-kg/",
            "schema": "https://schema.org/",
            "prov": "http://www.w3.org/ns/prov#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "skos": "http://www.w3.org/2004/02/skos/core#",
        },
        "@graph": jsonld_graph,
    }
    (DIST / "kg.jsonld").write_text(json.dumps(jsonld, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    template = TEMPLATE.read_text(encoding="utf-8")
    compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    if "/*__POLAR_KG_DATA__*/" not in template:
        raise SystemExit("web/template.html is missing the data marker")
    if "/*__POLAR_KG_APP__*/" not in template:
        raise SystemExit("web/template.html is missing the app marker")
    app = APP.read_text(encoding="utf-8").replace("</", "<\\/")
    document = template.replace("/*__POLAR_KG_DATA__*/", f"window.POLAR_KG_DATA={compact};")
    document = document.replace("/*__POLAR_KG_APP__*/", app)
    (DIST / "polar-knowledge-graph.html").write_text(document, encoding="utf-8")
    (DIST / "earth-ocean-evidence-atlas.html").write_text(document, encoding="utf-8")
    print(f"Built {len(nodes)} nodes, {len(edges)} edges, {len(bib_records)} references, and the explorer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
