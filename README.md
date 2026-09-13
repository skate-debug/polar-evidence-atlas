# Polar Evidence Atlas

[Open the bilingual atlas / 打开双语图谱](https://skate-debug.github.io/polar-evidence-atlas/)

An updateable, citation-first knowledge graph for:

- Antarctic viruses
- Arctic viruses
- Antarctic prokaryotes
- Arctic prokaryotes
- Arctic and Antarctic eukaryotes
- Polar geography, geology, geochemistry, nutrients, and hydrological/ocean circulation

The repository deliberately separates **curated evidence** from **automatically discovered candidates**. Search results never become factual graph edges until a person reviews them.

## What is included

- `data/sources.json` — manually curated source profiles with study design, spatial and temporal scope, methods, focal organisms/processes, key results, limitations, data accessions, and citation guidance.
- `data/claims.json` — atomic, paraphrased claims with source, evidence locator, scope, confidence, and graph-ready subject–predicate–object fields.
- `data/concepts.json` — controlled entities for poles, regions, habitats, taxa, processes, drivers, methods, nutrients, and water masses/currents.
- `data/locations.geojson` — named study areas and representative coordinates. Polygon-scale regions are intentionally not reduced to invented point coordinates.
- `data/public/candidates.json` — abstract-free public snapshot of machine-discovered literature awaiting curation. The local working cache is `data/candidates.json` and is intentionally ignored by Git.
- `data/candidate_reviews.json` — persistent title-and-abstract decisions for every discovered candidate.
- `data/candidate_verifications.json` — study-design, result, limitation, access-stage, and promotion packets for retained candidates.
- `data/public/candidate_archive.json` — abstract-free public archive of retired candidates, preserved for provenance and stable review-ledger joins.
- `data/i18n.zh-CN.json` — coverage-tracked Simplified-Chinese reading translations for the interface, concepts, evidence profiles, and atomic claims. English source records remain canonical for citation.
- `article/polar-earth-systems-introduction.md` — a citation-keyed article opening on polar geography, geology, geochemistry, nutrients, and circulation.
- `dist/polar-knowledge-graph.html` — a self-contained bilingual English/Chinese literature and graph explorer with a ThreeUI-inspired catalog shell, responsive evidence inspector, command search, active-filter chips, and light/dark/system themes.
- `dist/nodes.csv`, `dist/edges.csv`, `dist/graph.graphml`, and `dist/kg.jsonld` — interoperable exports for Gephi, Cytoscape, Neo4j import workflows, and linked-data tools.
- `references/polar-kg.bib` — BibTeX generated from DOI metadata and curated fallbacks.

The seed set prioritizes 2024–2026 literature and retains a limited number of 2021–2023 studies when they supply a key time series, genome catalogue, experimental design, or mechanistic baseline.

## Current snapshot

- 72 DOI-verified curated papers, each with a complete study and citation-safety profile
- 91 atomic evidence claims, with every curated paper represented
- 253 controlled concepts and 331 total exported nodes
- 1,077 exported semantic, provenance, study-design, and hierarchy edges
- 61 of 72 curated papers published from 2024 onward
- 48 papers published in 2025–2026, including 31 from 2026
- 161 automatically discovered candidates in the fully screened current snapshot: 12 retained for verification, 10 classified as background or methods references, 12 deferred pending full-text extraction or scope expansion, and 127 excluded
- Across the persistent current-and-archived review ledger, 27 retained candidates have verification packets: 14 have been full-text checked and promoted into the curated graph, 1 has an official publisher page checked, and 12 have DOI metadata and abstracts checked, leaving 13 held for deeper full-text extraction

Domain labels intentionally overlap: a paper about viruses beneath an ice shelf can contribute simultaneously to the Antarctic-virus, Antarctic-prokaryote, and polar-Earth-system views.

## Quick start

```bash
make all
open index.html
```

Or serve the exports locally:

```bash
make serve
# http://localhost:8000/dist/polar-knowledge-graph.html
```

Only Python's standard library is required.

The explorer borrows interface ideas from the MIT-licensed [ThreeUI Community](https://github.com/MengTo/threeui)—especially its compact catalog rail, contextual command search, active controls, restrained surfaces, and theme selector—while retaining this repository's dependency-free HTML, CSS, and JavaScript implementation. No ThreeUI runtime code or bundled media assets are included.

## Update workflow

```bash
# Discover recent candidates. This does not alter curated claims.
make update

# Preview the discovery and archive changes without writing candidate files.
make update-dry-run

# Export the persistent screening decisions as CSV and Markdown.
make review-report

# Verify DOI metadata for candidates recommended by the screen.
make candidate-metadata

# Refresh DOI metadata, validate, and rebuild all exports.
make refresh

# Translate only new or changed records, then check translation coverage.
make translations
make translation-check
```

The discovery date can be overridden:

```bash
python3 scripts/update_candidates.py --since 2025-01-01
```

Review decisions are stored separately in `data/candidate_reviews.json`, so rerunning discovery does not overwrite them. Detailed verification packets are stored in `data/candidate_verifications.json`; they explicitly distinguish full-text checks from publisher-page or abstract-only checks. `data/candidate_archive.json` preserves records that disappear from a later bounded search or are promoted into the curated collection. Candidate identifiers are reused across refreshes by DOI or normalized title, and the discovery script records first-seen, last-seen, and discovery-run provenance. `dist/candidate-review.csv` is the sortable review sheet and `dist/candidate-review-summary.md` is the human-readable audit. Newly discovered records appear as unreviewed until a corresponding ledger entry is added.

Before committing an updated release, regenerate and check the rights-conscious public snapshots:

```bash
make public-snapshot
make public-check
```

The public files retain bibliographic and discovery provenance but omit publisher-supplied abstracts and full text. A public clone automatically falls back to `data/public/` when the private working caches are absent.

When adding a paper:

1. Use the candidate metadata to create a new record in `data/sources.json`, then complete every curation field from the paper itself.
2. Add only claims that can be defended from the paper. Use `reported` for direct measurements, `inferred` for genome/network/proxy-derived interpretation, `modeled` for numerical or statistical model results, and `synthesized` for review-level conclusions.
3. Add missing controlled concepts to `data/concepts.json`; do not create near-duplicate labels.
4. Record a section, figure, table, or abstract locator and state the study's spatial/temporal scope.
5. Add a concise `cite_for` and `do_not_overcite` note.
6. Run `make translations` to add Chinese reading translations for new or changed records. Review scientific terminology and any translated title before publication.
7. Run `make refresh`.

The translation ledger fingerprints every source, claim, and concept. When an English record changes, validation marks its Chinese counterpart stale until `make translations` is run. Published titles, DOI links, generated BibTeX, and citation text always retain the original bibliographic language; Chinese is a terminology-normalized reading layer and can be updated independently.

## Evidence model

The graph distinguishes four layers:

1. **Source metadata** — title, DOI, authors, publication date, journal, study type, open-data links.
2. **Study profile** — sampling design, environment, methods, variables, taxa, processes, and limitations.
3. **Atomic claim** — one defensible statement with provenance, scope, evidence basis, and confidence.
4. **Semantic edge** — a subject–predicate–object relationship backed by one or more atomic claims.

This prevents a common knowledge-graph failure: attaching a DOI to a broad edge that the cited paper did not actually test.

Confidence is about support within the cited study, not universal truth:

- `high` — direct measurement or replicated synthesis closely matching the claim.
- `moderate` — robust genomic, network, proxy, or model inference with explicit assumptions.
- `low` — exploratory or hypothesis-generating result retained for discovery, not strong citation.

## Scope and caveats

This is a high-detail seed graph, not a completed systematic review. Polar literature is too large and changes too quickly for a static claim of completeness. Candidate discovery is intentionally broad; curated evidence remains conservative. Coordinates are representative study locations when available, not substitutes for cruise tracks, polygons, or complete sampling metadata. Taxonomy follows the terminology used by each source unless a current normalized label is explicitly recorded.

## Licensing and citation

Original software is available under the [MIT License](LICENSE). Original editorial content and curated data are available under [CC BY 4.0](LICENSE-CONTENT.md), excluding third-party bibliographic material. See [third-party notices](THIRD_PARTY_NOTICES.md) and [`CITATION.cff`](CITATION.cff). Always cite the primary paper behind a scientific claim as well as the atlas when appropriate.

## Repository map

```text
article/      Citation-keyed narrative synthesis
config/       Search queries and update settings
data/         Curated records plus abstract-free public discovery snapshots
dist/         Generated interactive and machine-readable exports
references/   Generated BibTeX
schema/       Ontology and JSON Schemas
scripts/      Discovery, metadata enrichment, validation, and build tools
web/          Explorer template
```
