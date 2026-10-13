#!/usr/bin/env python3
"""Validate the curated polar knowledge graph without third-party packages."""

from __future__ import annotations

import json
import calendar
import re
import sys
from collections import Counter
from pathlib import Path
from datetime import date

from update_zh_translations import claim_payload, concept_payload, digest, source_payload

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

ALLOWED_PREDICATES = {
    "harbours", "associated_with", "infects_or_targets", "encodes_potential_for",
    "drives", "increases", "decreases", "shifts_to", "supplies", "exports",
    "transports", "mixes_with", "limits", "co_limits", "supports", "formed_by",
    "separates", "connects", "catalogues", "projects",
}
EVIDENCE_TYPES = {"reported", "inferred", "modeled", "synthesized"}
CONFIDENCE = {"high", "moderate", "low"}
POLES = {"Arctic", "Antarctic", "Bipolar", "Global"}
SOURCE_REQUIRED = {
    "id", "citation_key", "doi", "title", "year", "domains", "poles",
    "study_type", "study_profile", "key_findings", "limitations", "cite_for",
    "do_not_overcite", "curation",
}
PROFILE_REQUIRED = {
    "spatial_scope", "temporal_scope", "habitats", "methods",
    "sample_design", "measured_or_derived",
}
CLAIM_REQUIRED = {
    "id", "source_id", "subject", "predicate", "object", "statement", "scope",
    "evidence_type", "evidence_basis", "locator", "confidence", "confidence_note",
}


def load(name: str):
    path = DATA / name
    if not path.exists():
        path = DATA / "public" / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"ERROR: cannot read {path}: {exc}") from exc


def duplicate_values(values):
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def main() -> int:
    sources = load("sources.json")
    claims = load("claims.json")
    concepts = load("concepts.json")
    locations = load("locations.geojson")
    candidates_payload = load("candidates.json")
    candidate_archive = load("candidate_archive.json")
    candidate_reviews = load("candidate_reviews.json")
    candidate_verifications = load("candidate_verifications.json")
    translations = load("i18n.zh-CN.json")
    taxonomy = json.loads((ROOT / "config" / "collections.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []

    if not all(isinstance(group, list) for group in (sources, claims, concepts)):
        errors.append("sources.json, claims.json, and concepts.json must each be arrays")
        sources, claims, concepts = [], [], []

    source_ids = {item.get("id") for item in sources}
    concept_ids = {item.get("id") for item in concepts}
    node_ids = source_ids | concept_ids

    for label, values in (
        ("source ID", [item.get("id") for item in sources]),
        ("claim ID", [item.get("id") for item in claims]),
        ("concept ID", [item.get("id") for item in concepts]),
        ("DOI", [str(item.get("doi", "")).lower() for item in sources]),
        ("citation key", [item.get("citation_key") for item in sources]),
    ):
        duplicates = duplicate_values(values)
        if duplicates:
            errors.append(f"duplicate {label}(s): {', '.join(map(str, duplicates))}")

    for source in sources:
        sid = source.get("id", "<missing>")
        missing = SOURCE_REQUIRED - source.keys()
        if missing:
            errors.append(f"{sid}: missing source fields {sorted(missing)}")
        if not str(sid).startswith("src:"):
            errors.append(f"{sid}: source ID must start with src:")
        if not re.match(r"^10\.\S+?/\S+$", str(source.get("doi", ""))):
            errors.append(f"{sid}: malformed DOI {source.get('doi')!r}")
        if not re.match(r"^[A-Za-z][A-Za-z0-9_-]+$", str(source.get("citation_key", ""))):
            errors.append(f"{sid}: malformed citation key")
        if not isinstance(source.get("year"), int) or not 1900 <= source.get("year", 0) <= 2100:
            errors.append(f"{sid}: invalid year")
        if not source.get("domains") or not isinstance(source.get("domains"), list):
            errors.append(f"{sid}: domains must be a non-empty list")
        if not set(source.get("poles", [])) <= POLES or (not source.get("poles") and not source.get("regions")):
            errors.append(f"{sid}: invalid pole labels")
        for region in source.get("regions", []):
            if region not in concept_ids:
                errors.append(f"{sid}: unknown region {region}")
        if source.get("collection") == "scs-cold-seeps":
            for field in ("compartments", "topics", "sites"):
                allowed = {item["id"] for item in taxonomy[field]}
                if not source.get(field) or not set(source[field]) <= allowed:
                    errors.append(f"{sid}: invalid or missing {field}")
            if source.get("poles"):
                errors.append(f"{sid}: SCS source must use regions instead of polar labels")
        profile = source.get("study_profile", {})
        missing_profile = PROFILE_REQUIRED - profile.keys()
        if missing_profile:
            errors.append(f"{sid}: missing profile fields {sorted(missing_profile)}")
        for field in ("habitats", "methods", "focal_taxa", "focal_processes", "environmental_drivers"):
            for ref in profile.get(field, []):
                if ref not in concept_ids:
                    errors.append(f"{sid}: {field} references unknown concept {ref}")
        for field in ("key_findings", "limitations", "cite_for", "do_not_overcite"):
            if not isinstance(source.get(field), list) or not source.get(field):
                errors.append(f"{sid}: {field} must be a non-empty list")
        curation = source.get("curation", {})
        if curation.get("status") != "curated":
            errors.append(f"{sid}: curated source must have curation.status=curated")
        if not curation.get("basis") or not re.match(r"^\d{4}-\d{2}-\d{2}$", curation.get("last_verified", "")):
            errors.append(f"{sid}: incomplete curation basis or verification date")

    promoted_candidate_ids = [source.get("candidate_id") for source in sources if source.get("candidate_id")]
    if duplicate_values(promoted_candidate_ids):
        errors.append("multiple curated sources reference the same candidate ID")

    claim_sources = Counter()
    for claim in claims:
        cid = claim.get("id", "<missing>")
        missing = CLAIM_REQUIRED - claim.keys()
        if missing:
            errors.append(f"{cid}: missing claim fields {sorted(missing)}")
        extra = set(claim) - (CLAIM_REQUIRED | {"qualifiers"})
        if extra:
            errors.append(f"{cid}: unsupported claim fields {sorted(extra)}")
        if not str(cid).startswith("claim:"):
            errors.append(f"{cid}: claim ID must start with claim:")
        if claim.get("source_id") not in source_ids:
            errors.append(f"{cid}: unknown source {claim.get('source_id')}")
        else:
            claim_sources[claim["source_id"]] += 1
        for field in ("subject", "object"):
            if claim.get(field) not in node_ids:
                errors.append(f"{cid}: {field} references unknown node {claim.get(field)}")
        if claim.get("predicate") not in ALLOWED_PREDICATES:
            errors.append(f"{cid}: unsupported predicate {claim.get('predicate')}")
        if claim.get("evidence_type") not in EVIDENCE_TYPES:
            errors.append(f"{cid}: invalid evidence type")
        if claim.get("confidence") not in CONFIDENCE:
            errors.append(f"{cid}: invalid confidence")
        for field in ("statement", "scope", "evidence_basis", "locator", "confidence_note"):
            if not isinstance(claim.get(field), str) or len(claim.get(field, "").strip()) < 3:
                errors.append(f"{cid}: {field} must contain text")

    for sid in sorted(source_ids - claim_sources.keys()):
        errors.append(f"{sid}: curated source has no atomic claim")

    for concept in concepts:
        cid = concept.get("id", "<missing>")
        if not all(concept.get(field) for field in ("id", "type", "label", "description")):
            errors.append(f"{cid}: concept requires id, type, label, and description")
        if concept.get("broader") and concept["broader"] not in concept_ids:
            errors.append(f"{cid}: broader concept does not exist: {concept['broader']}")

    translation_groups = (
        ("sources", sources, source_payload),
        ("claims", claims, claim_payload),
        ("concepts", concepts, concept_payload),
    )
    if translations.get("language") != "zh-CN" or translations.get("source_language") != "en":
        errors.append("i18n.zh-CN.json must declare language=zh-CN and source_language=en")
    for group, records, payload_for in translation_groups:
        localized = translations.get(group, {})
        expected_ids = {record.get("id") for record in records}
        missing_ids = expected_ids - set(localized)
        extra_ids = set(localized) - expected_ids
        if missing_ids:
            errors.append(f"Chinese translation layer lacks {len(missing_ids)} {group} record(s)")
        if extra_ids:
            errors.append(f"Chinese translation layer contains {len(extra_ids)} orphaned {group} record(s)")
        for record in records:
            entry = localized.get(record.get("id"), {})
            if entry and entry.get("_source_hash") != digest(payload_for(record)):
                errors.append(f"{record.get('id')}: Chinese translation is stale")
    ui = translations.get("ui", {})
    if set(ui.get("en", {})) != set(ui.get("zh-CN", {})):
        errors.append("English and Chinese interface dictionaries must contain identical keys")

    if locations.get("type") != "FeatureCollection":
        errors.append("locations.geojson must be a FeatureCollection")
    location_ids = [feature.get("id") for feature in locations.get("features", [])]
    if duplicate_values(location_ids):
        errors.append("locations.geojson contains duplicate feature IDs")
    for feature in locations.get("features", []):
        feature_id = feature.get("id")
        if feature_id not in concept_ids:
            errors.append(f"locations.geojson feature references unknown concept {feature_id}")
        ref = feature.get("properties", {}).get("concept_id")
        if ref and ref not in concept_ids:
            errors.append(f"locations.geojson references unknown concept {ref}")
        geometry = feature.get("geometry")
        if geometry and geometry.get("type") == "Point":
            coordinates = geometry.get("coordinates", [])
            if (
                not isinstance(coordinates, list) or len(coordinates) != 2
                or not all(isinstance(value, (int, float)) for value in coordinates)
                or not -180 <= coordinates[0] <= 180 or not -90 <= coordinates[1] <= 90
            ):
                errors.append(f"locations.geojson feature {feature_id} has invalid point coordinates")

    seep_inventory = load("cold_seep_candidates.json")
    seep_records = seep_inventory.get("candidates", [])
    lower, upper = seep_inventory.get("since", ""), seep_inventory.get("until", "")
    for field in ("id", "doi"):
        if duplicate_values([item.get(field) for item in seep_records]):
            errors.append(f"cold-seep inventory contains duplicate {field}s")
    for item in seep_records:
        publication = item.get("publication_date", "")
        try:
            parts = [int(part) for part in publication.split("-")]
            if len(parts) == 3:
                start = end = date(*parts).isoformat()
            elif len(parts) == 2:
                year, month = parts
                start = date(year, month, 1).isoformat()
                end = date(year, month, calendar.monthrange(year, month)[1]).isoformat()
            else:
                start, end = date(parts[0], 1, 1).isoformat(), date(parts[0], 12, 31).isoformat()
            if not lower <= start or not end <= upper:
                errors.append(f"{item.get('id')}: publication date outside SCS window")
        except (ValueError, IndexError, TypeError):
            errors.append(f"{item.get('id')}: invalid publication date")
    curated_seep_dois = {source["doi"] for source in sources if source.get("collection") == "scs-cold-seeps"}
    if not curated_seep_dois <= {item.get("doi") for item in seep_records}:
        errors.append("SCS inventory does not contain every curated SCS DOI")

    candidates = candidates_payload.get("candidates", [])
    archived_candidates = candidate_archive.get("candidates", [])
    reviews = candidate_reviews.get("reviews", [])
    candidate_ids = {candidate.get("id") for candidate in candidates}
    archived_candidate_ids = {candidate.get("id") for candidate in archived_candidates}
    if duplicate_values([candidate.get("id") for candidate in archived_candidates]):
        errors.append("candidate_archive.json contains duplicate candidate IDs")
    if candidate_ids & archived_candidate_ids:
        errors.append("current and archived candidate snapshots contain overlapping IDs")
    review_ids = [review.get("candidate_id") for review in reviews]
    if duplicate_values(review_ids):
        errors.append("candidate_reviews.json contains duplicate candidate IDs")
    allowed_decisions = {"include", "background", "exclude", "defer"}
    for review in reviews:
        rid = review.get("candidate_id", "<missing>")
        if rid not in candidate_ids and rid not in archived_candidate_ids and rid not in promoted_candidate_ids:
            warnings.append(f"candidate review no longer occurs in current discovery snapshot: {rid}")
        if review.get("decision") not in allowed_decisions:
            errors.append(f"{rid}: invalid candidate-review decision")
        score = review.get("relevance_score")
        if not isinstance(score, int) or not 0 <= score <= 10:
            errors.append(f"{rid}: candidate relevance score must be an integer from 0 to 10")
        if not review.get("review_note") or not review.get("reason_codes"):
            errors.append(f"{rid}: incomplete review rationale")
    unreviewed_candidates = candidate_ids - set(review_ids)
    if unreviewed_candidates:
        warnings.append(f"{len(unreviewed_candidates)} current candidate(s) await screening")

    verification_records = candidate_verifications.get("records", [])
    verification_ids = [record.get("candidate_id") for record in verification_records]
    if duplicate_values(verification_ids):
        errors.append("candidate_verifications.json contains duplicate candidate IDs")
    known_review_ids = candidate_ids | archived_candidate_ids | set(promoted_candidate_ids)
    verified_reviews_by_id = {
        review.get("candidate_id"): review for review in reviews
        if review.get("candidate_id") in known_review_ids
    }
    include_ids = {
        candidate_id for candidate_id, review in verified_reviews_by_id.items()
        if review.get("decision") == "include"
    }
    if include_ids - set(verification_ids):
        errors.append(f"{len(include_ids - set(verification_ids))} included candidate(s) lack verification packets")
    if set(verification_ids) - include_ids:
        errors.append(f"{len(set(verification_ids) - include_ids)} verification packet(s) are not include decisions in the current or archived review ledger")
    allowed_verification_stages = {"full_text_checked", "publisher_page_checked", "doi_abstract_verified"}
    allowed_promotion_recommendations = {"ready_for_structured_curation", "hold_for_full_text_extraction"}
    required_verification_fields = {
        "candidate_id", "doi", "verification_stage", "verification_url", "proposed_poles",
        "proposed_domains", "study_type", "spatial_scope", "temporal_scope", "methods",
        "headline_result", "principal_limitations", "promotion_recommendation",
    }
    for record in verification_records:
        rid = record.get("candidate_id", "<missing>")
        missing = required_verification_fields - record.keys()
        if missing:
            errors.append(f"{rid}: missing verification fields {sorted(missing)}")
        if record.get("verification_stage") not in allowed_verification_stages:
            errors.append(f"{rid}: invalid verification stage")
        if record.get("promotion_recommendation") not in allowed_promotion_recommendations:
            errors.append(f"{rid}: invalid promotion recommendation")
        if record.get("promotion_recommendation") == "ready_for_structured_curation" and record.get("verification_stage") != "full_text_checked":
            errors.append(f"{rid}: only a full-text-checked candidate can be ready for structured curation")
        if not re.match(r"^10\.\S+?/\S+$", str(record.get("doi", ""))):
            errors.append(f"{rid}: malformed verified DOI")
        review = verified_reviews_by_id.get(rid, {})
        expected_doi = str(review.get("resolved_doi") or review.get("doi") or "").lower()
        if expected_doi and str(record.get("doi", "")).lower() != expected_doi:
            errors.append(f"{rid}: verified DOI differs from screening ledger DOI")
        for field in ("proposed_poles", "proposed_domains", "methods", "principal_limitations"):
            if not isinstance(record.get(field), list) or not record.get(field):
                errors.append(f"{rid}: {field} must be a non-empty list")
        if not set(record.get("proposed_poles", [])) <= POLES:
            errors.append(f"{rid}: invalid proposed pole labels")
    verification_by_id = {record.get("candidate_id"): record for record in verification_records}
    for source in sources:
        promoted_id = source.get("candidate_id")
        if not promoted_id:
            continue
        verification = verification_by_id.get(promoted_id)
        if not verification:
            warnings.append(f"curated source {source['id']} references a candidate without a verification packet")
            continue
        if source.get("doi", "").lower() != verification.get("doi", "").lower():
            errors.append(f"{source['id']}: curated DOI differs from candidate verification DOI")
        if verification.get("verification_stage") != "full_text_checked":
            errors.append(f"{source['id']}: promoted candidate was not full-text checked")

    recent = sum(source.get("year", 0) >= 2024 for source in sources)
    polar_sources = [source for source in sources if source.get("collection", "polar") == "polar"]
    if polar_sources and sum(source.get("year", 0) >= 2024 for source in polar_sources) / len(polar_sources) < 0.7:
        warnings.append("fewer than 70% of curated sources are from 2024 onward")

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Validation failed: {len(errors)} error(s), {len(warnings)} warning(s).")
        return 1

    domains = Counter(domain for source in sources for domain in source["domains"])
    evidence = Counter(claim["evidence_type"] for claim in claims)
    print(
        f"Validation passed: {len(sources)} sources, {len(claims)} claims, "
        f"{len(concepts)} concepts, {recent} sources from 2024 onward."
    )
    review_counts = Counter(review.get("decision") for review in reviews if review.get("candidate_id") in candidate_ids)
    print("Candidate review: " + ", ".join(f"{key}={value}" for key, value in sorted(review_counts.items())))
    verification_counts = Counter(record.get("verification_stage") for record in verification_records)
    print("Candidate verification: " + ", ".join(f"{key}={value}" for key, value in sorted(verification_counts.items())))
    print("Domains: " + ", ".join(f"{key}={value}" for key, value in sorted(domains.items())))
    print("Evidence: " + ", ".join(f"{key}={value}" for key, value in sorted(evidence.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
