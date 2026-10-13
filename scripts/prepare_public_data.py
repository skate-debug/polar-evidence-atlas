#!/usr/bin/env python3
"""Create rights-conscious public snapshots from local literature caches.

The working cache may contain publisher-supplied abstracts. Public snapshots
retain discovery provenance and bibliographic fields while omitting abstracts,
full text, and unused Crossref payload fields.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PUBLIC = DATA / "public"
RESTRICTED_KEYS = {
    "abstract",
    "abstracttext",
    "body",
    "full_text",
    "fulltext",
    "full-text",
}
METADATA_FIELDS = {
    "DOI",
    "URL",
    "author",
    "container-title",
    "issue",
    "issued",
    "language",
    "license",
    "page",
    "publisher",
    "title",
    "type",
    "volume",
    "article-number",
    "published-print",
    "published-online",
    "relation",
    "update-to",
    "metadata_verification_url",
    "metadata_verification_basis",
}
PUBLIC_NAMES = {
    "candidates.json",
    "candidate_archive.json",
    "metadata.json",
    "candidate_metadata.json",
    "cold_seep_candidates.json",
    "cold_seep_metadata.json",
    "global_cold_seep_candidates.json",
    "global_cold_seep_metadata.json",
    "global_cold_seep_archive.json",
}


def strip_restricted(value):
    if isinstance(value, dict):
        return {
            key: strip_restricted(item)
            for key, item in value.items()
            if key.lower() not in RESTRICTED_KEYS
        }
    if isinstance(value, list):
        return [strip_restricted(item) for item in value]
    return value


def slim_metadata(payload: dict) -> dict:
    records = {
        doi: {
            key: strip_restricted(value)
            for key, value in record.items()
            if key in METADATA_FIELDS
        }
        for doi, record in payload.get("records", {}).items()
    }
    return {
        "generated_at": payload.get("generated_at", ""),
        "provider": payload.get("provider", "DOI content negotiation (CSL-JSON)"),
        "public_snapshot_policy": "Bibliographic fields required by the atlas build; abstracts, reference lists, links to content files, and unused provider fields are omitted.",
        "records": dict(sorted(records.items())),
        "errors": payload.get("errors", {}),
    }


def candidate_snapshot(payload: dict) -> dict:
    cleaned = strip_restricted(payload)
    cleaned["public_snapshot_policy"] = (
        "Discovery metadata and review joins only; publisher-supplied abstracts and full text are omitted."
    )
    return cleaned


def build_snapshots() -> dict[str, dict]:
    snapshots: dict[str, dict] = {}
    sources = {
        "candidates.json": candidate_snapshot,
        "candidate_archive.json": candidate_snapshot,
        "metadata.json": slim_metadata,
        "candidate_metadata.json": slim_metadata,
        "cold_seep_candidates.json": candidate_snapshot,
        "cold_seep_metadata.json": slim_metadata,
        "global_cold_seep_candidates.json": candidate_snapshot,
        "global_cold_seep_metadata.json": slim_metadata,
        "global_cold_seep_archive.json": candidate_snapshot,
    }
    for name, transform in sources.items():
        path = DATA / name
        if path.exists():
            snapshots[name] = transform(json.loads(path.read_text(encoding="utf-8")))
    return snapshots


def restricted_paths(value, prefix=""):
    if isinstance(value, dict):
        for key, item in value.items():
            location = f"{prefix}.{key}" if prefix else key
            if key.lower() in RESTRICTED_KEYS:
                yield location
            yield from restricted_paths(item, location)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from restricted_paths(item, f"{prefix}[{index}]")


def write_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify committed snapshots without changing files")
    args = parser.parse_args()
    expected = build_snapshots()
    names = sorted(PUBLIC_NAMES | set(expected) | ({path.name for path in PUBLIC.glob("*.json")} if PUBLIC.exists() else set()))
    errors = []

    if args.check:
        for name in names:
            path = PUBLIC / name
            if not path.exists():
                errors.append(f"missing public snapshot: {path.relative_to(ROOT)}")
                continue
            actual = json.loads(path.read_text(encoding="utf-8"))
            forbidden = list(restricted_paths(actual))
            if forbidden:
                errors.append(f"{path.relative_to(ROOT)} contains restricted fields: {', '.join(forbidden[:5])}")
            if name in expected and actual != expected[name]:
                errors.append(f"stale public snapshot: {path.relative_to(ROOT)}")
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print(f"Public snapshots passed: {len(names)} file(s), no abstract or full-text fields.")
        return 0

    PUBLIC.mkdir(parents=True, exist_ok=True)
    for name, payload in expected.items():
        write_json(PUBLIC / name, payload)
    print(f"Prepared {len(expected)} abstract-free public snapshot(s) in {PUBLIC.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
