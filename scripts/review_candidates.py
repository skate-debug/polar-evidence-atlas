#!/usr/bin/env python3
"""Validate and export the persistent candidate-review ledger."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DIST = ROOT / "dist"
ALLOWED = {"include", "background", "exclude", "defer"}
VERIFICATION_STAGES = {"full_text_checked", "publisher_page_checked", "doi_abstract_verified"}
PROMOTION_RECOMMENDATIONS = {"ready_for_structured_curation", "hold_for_full_text_extraction"}


def data_path(name: str) -> Path:
    private_path = DATA / name
    return private_path if private_path.exists() else DATA / "public" / name


def main() -> int:
    candidates_payload = json.loads(data_path("candidates.json").read_text(encoding="utf-8"))
    ledger = json.loads((DATA / "candidate_reviews.json").read_text(encoding="utf-8"))
    verification_payload = json.loads((DATA / "candidate_verifications.json").read_text(encoding="utf-8"))
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    archive_payload = json.loads(data_path("candidate_archive.json").read_text(encoding="utf-8"))
    candidates = candidates_payload.get("candidates", [])
    reviews = ledger.get("reviews", [])
    verifications = verification_payload.get("records", [])
    by_candidate = {review["candidate_id"]: review for review in reviews}
    by_verification = {record["candidate_id"]: record for record in verifications}
    promoted_by_candidate = {
        source["candidate_id"]: source["id"] for source in sources if source.get("candidate_id")
    }
    errors: list[str] = []

    if len(by_candidate) != len(reviews):
        errors.append("candidate review ledger contains duplicate candidate IDs")
    if len(by_verification) != len(verifications):
        errors.append("candidate verification ledger contains duplicate candidate IDs")
    for review in reviews:
        if review.get("decision") not in ALLOWED:
            errors.append(f"{review.get('candidate_id')}: unsupported decision {review.get('decision')}")
        score = review.get("relevance_score")
        if not isinstance(score, int) or not 0 <= score <= 10:
            errors.append(f"{review.get('candidate_id')}: relevance_score must be an integer from 0 to 10")
        for field in ("review_stage", "review_note", "reviewed_at", "reviewer"):
            if not review.get(field):
                errors.append(f"{review.get('candidate_id')}: missing {field}")
    for record in verifications:
        candidate_id = record.get("candidate_id", "<missing>")
        if record.get("verification_stage") not in VERIFICATION_STAGES:
            errors.append(f"{candidate_id}: unsupported verification stage")
        if record.get("promotion_recommendation") not in PROMOTION_RECOMMENDATIONS:
            errors.append(f"{candidate_id}: unsupported promotion recommendation")
        for field in (
            "doi", "verification_url", "proposed_poles", "proposed_domains", "study_type",
            "spatial_scope", "temporal_scope", "methods", "headline_result", "principal_limitations",
        ):
            if not record.get(field):
                errors.append(f"{candidate_id}: missing verification field {field}")

    rows = []
    unreviewed = []
    for candidate in candidates:
        review = by_candidate.get(candidate["id"])
        if not review:
            unreviewed.append(candidate["id"])
            review = {
                "decision": "unreviewed", "relevance_score": "",
                "reason_codes": [], "review_note": "", "review_stage": "",
                "reviewed_at": "", "reviewer": "",
            }
        verification = by_verification.get(candidate["id"], {})
        curated_source_id = promoted_by_candidate.get(candidate["id"], "")
        workflow_status = (
            "promoted_to_curated_graph" if curated_source_id
            else verification.get("promotion_recommendation", "")
        )
        rows.append({
            "decision": review["decision"],
            "relevance_score": review["relevance_score"],
            "year": candidate.get("year", ""),
            "title": candidate.get("title", ""),
            "doi": review.get("resolved_doi") or candidate.get("doi", ""),
            "pmcid": candidate.get("pmcid", ""),
            "domains": "|".join(candidate.get("domains", [])),
            "poles": "|".join(candidate.get("poles", [])),
            "matched_queries": "|".join(candidate.get("matched_queries", [])),
            "review_stage": review.get("review_stage", ""),
            "reason_codes": "|".join(review.get("reason_codes", [])),
            "review_note": review.get("review_note", ""),
            "reviewed_at": review.get("reviewed_at", ""),
            "verification_stage": verification.get("verification_stage", ""),
            "promotion_recommendation": verification.get("promotion_recommendation", ""),
            "workflow_status": workflow_status,
            "curated_source_id": curated_source_id,
            "proposed_domains": "|".join(verification.get("proposed_domains", [])),
            "proposed_poles": "|".join(verification.get("proposed_poles", [])),
            "study_type": verification.get("study_type", ""),
            "spatial_scope": verification.get("spatial_scope", ""),
            "temporal_scope": verification.get("temporal_scope", ""),
            "methods": "|".join(verification.get("methods", [])),
            "headline_result": verification.get("headline_result", ""),
            "principal_limitations": "|".join(verification.get("principal_limitations", [])),
            "candidate_id": candidate["id"],
            "url": verification.get("verification_url") or review.get("verification_url") or candidate.get("url", ""),
        })

    known_candidate_ids = {candidate["id"] for candidate in candidates}
    archived_candidate_ids = {candidate["id"] for candidate in archive_payload.get("candidates", [])}
    archived_reviews = sorted(set(by_candidate) & archived_candidate_ids)
    orphaned = sorted(set(by_candidate) - known_candidate_ids - archived_candidate_ids - set(promoted_by_candidate))
    valid_review_ids = known_candidate_ids | archived_candidate_ids | set(promoted_by_candidate)
    include_ids = {
        review["candidate_id"] for review in reviews
        if review.get("decision") == "include" and review["candidate_id"] in valid_review_ids
    }
    missing_verifications = sorted(include_ids - set(by_verification))
    noninclude_verifications = sorted(set(by_verification) - include_ids)
    if missing_verifications:
        errors.append(f"{len(missing_verifications)} included candidate(s) lack verification packets")
    if noninclude_verifications:
        errors.append(f"{len(noninclude_verifications)} verification packet(s) do not correspond to included candidates")
    decision_counts = Counter(row["decision"] for row in rows)
    verification_counts = Counter(
        record.get("verification_stage") for record in verifications
        if record.get("candidate_id") in include_ids
    )
    promotion_counts = Counter(
        "promoted_to_curated_graph" if record.get("candidate_id") in promoted_by_candidate
        else record.get("promotion_recommendation")
        for record in verifications if record.get("candidate_id") in include_ids
    )
    reason_counts = Counter(
        code for review in reviews for code in review.get("reason_codes", [])
        if review["candidate_id"] in known_candidate_ids
    )

    DIST.mkdir(exist_ok=True)
    csv_path = DIST / "candidate-review.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: (
            {"include": 0, "background": 1, "defer": 2, "unreviewed": 3, "exclude": 4}.get(row["decision"], 5),
            -(row["relevance_score"] if isinstance(row["relevance_score"], int) else -1),
            -int(row["year"] or 0),
            row["title"],
        )))

    def markdown_link(row):
        url = row["url"] or (f"https://doi.org/{row['doi']}" if row["doi"] else "")
        title = row["title"].replace("[", "\\[").replace("]", "\\]")
        return f"[{title}]({url})" if url else title

    lines = [
        "# Candidate literature review",
        "",
        f"Snapshot: `{candidates_payload.get('generated_at', '')}`  ",
        f"Screened: **{len(candidates) - len(unreviewed)} of {len(candidates)}**  ",
        f"Recommended for source-level verification: **{decision_counts.get('include', 0)}**  ",
        f"Background or methods only: **{decision_counts.get('background', 0)}**  ",
        f"Deferred pending full-text extraction or scope expansion: **{decision_counts.get('defer', 0)}**  ",
        f"Excluded: **{decision_counts.get('exclude', 0)}**  ",
        f"Unreviewed: **{len(unreviewed)}**  ",
        f"Full text checked: **{verification_counts.get('full_text_checked', 0)}**  ",
        f"Publisher page checked: **{verification_counts.get('publisher_page_checked', 0)}**  ",
        f"DOI and abstract checked: **{verification_counts.get('doi_abstract_verified', 0)}**  ",
        f"Promoted to the curated graph: **{promotion_counts.get('promoted_to_curated_graph', 0)}**  ",
        f"Ready but not yet promoted: **{promotion_counts.get('ready_for_structured_curation', 0)}**  ",
        f"Held for full-text extraction: **{promotion_counts.get('hold_for_full_text_extraction', 0)}**",
        "",
        "## Recommended candidates",
        "",
    ]
    for row in sorted(
        (row for row in rows if row["decision"] == "include"),
        key=lambda row: (-int(row["relevance_score"]), -int(row["year"]), row["title"]),
    ):
        stage = row["verification_stage"].replace("_", " ") or "verification missing"
        workflow = row["workflow_status"].replace("_", " ")
        lines.append(f"- **{row['relevance_score']}/10** — {markdown_link(row)} — *{stage}; {workflow}*. {row['review_note']}")
    lines += ["", "## Background-only candidates", ""]
    for row in sorted((row for row in rows if row["decision"] == "background"), key=lambda row: (-int(row["relevance_score"]), row["title"])):
        lines.append(f"- **{row['relevance_score']}/10** — {markdown_link(row)} — {row['review_note']}")
    lines += ["", "## Deferred candidates", ""]
    for row in sorted((row for row in rows if row["decision"] == "defer"), key=lambda row: (-int(row["relevance_score"]), row["title"])):
        lines.append(f"- **{row['relevance_score']}/10** — {markdown_link(row)} — {row['review_note']}")
    lines += ["", "## Exclusion audit", ""]
    for reason, count in reason_counts.most_common():
        lines.append(f"- `{reason}`: {count}")
    if unreviewed:
        lines += ["", "## Awaiting review", ""] + [f"- `{item}`" for item in unreviewed]
    if archived_reviews:
        lines += ["", "## Reviewed candidates retained in the archive", ""] + [f"- `{item}`" for item in archived_reviews]
    if orphaned:
        lines += ["", "## Reviews without a current, archived, or promoted candidate record", ""] + [f"- `{item}`" for item in orphaned]
    (DIST / "candidate-review-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        f"Candidate review: {decision_counts.get('include', 0)} include, "
        f"{decision_counts.get('background', 0)} background, "
        f"{decision_counts.get('defer', 0)} defer, "
        f"{decision_counts.get('exclude', 0)} exclude, {len(unreviewed)} unreviewed; "
        f"{len(orphaned)} orphaned review(s)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
