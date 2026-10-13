# Earth & Ocean Evidence Atlas

[Open the bilingual atlas / 打开双语图谱](https://skate-debug.github.io/polar-evidence-atlas/) · [South China Sea cold seeps / 南海冷泉](https://skate-debug.github.io/polar-evidence-atlas/?collection=scs-cold-seeps)

[Cold seeps across regions / 全球冷泉比较](https://skate-debug.github.io/polar-evidence-atlas/?collection=global-cold-seeps) · [Discussion comparison guide / 讨论比较指南](article/cold-seep-discussion-comparisons.md)

Formerly **Polar Evidence Atlas**. The broader name covers the new South China Sea cold-seep collection alongside the original polar research. The existing repository URL and legacy explorer file remain available.

An updateable, citation-first knowledge graph for:

- Antarctic viruses
- Arctic viruses
- Antarctic prokaryotes
- Arctic prokaryotes
- Arctic and Antarctic eukaryotes
- Polar geography, geology, geochemistry, nutrients, and hydrological/ocean circulation
- South China Sea cold-seep microorganisms in water, sediments, interfaces, and host-associated communities
- Cold-seep comparisons from other ocean regions for manuscript discussion, with explicitly labeled mechanistic and habitat context

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
- `config/collections.json` — bilingual collection, compartment, topic, and site taxonomy.
- `data/public/cold_seep_candidates.json` — abstract-free ten-year SCS literature inventory; automatic tags remain provisional until source review.
- `dist/cold-seep-literature.csv` — sortable literature inventory with DOI, site, compartment, topic, publication stage, and review status.
- `data/cold_seep_reviews.json` — persistent SCS screening and source-review decisions, with access level, rationale, evidence link, and next action.
- `dist/cold-seep-review-summary.md` and `dist/cold-seep-review.csv` — the source-review audit and remaining work queue.
- `dist/cold-seep-evidence-profiles.md` — all curated SCS profiles in bilingual Markdown, with study-specific citation limits.
- `references/cold-seep-curated-apa7.md` — APA 7 references for curated SCS studies; `references/cold-seep-literature-apa7.md` also includes the screened inventory, notices, and preprints.
- `article/south-china-sea-cold-seep-guide.md` — bilingual scope, classification, evidence guide, and update instructions.
- `config/global_cold_seep_reviewed.json` — explicit bilingual comparison packets; shared DOI sources retain their original IDs.
- `data/global_cold_seep_reviews.json` — persistent international screening, version and evidence decisions.
- `dist/global-cold-seep-evidence-profiles.md` and `references/global-cold-seep-curated-apa7.md` — comparison profiles and their APA 7 references.
- `dist/global-cold-seep-literature.csv` and `dist/global-cold-seep-review-summary.md` — international discovery inventory and remaining review work.
- `article/cold-seep-discussion-comparisons.md` — thematic SCS/international comparison guide with sampling and citation limits.

The polar collection prioritizes 2024–2026 literature and retains older mechanistic baselines. The SCS collection covers a rolling ten years: 12 October 2016 through 12 October 2026 for this release. Discovery uses first publication date; citations use the version-of-record bibliographic year. Global comparison studies enter the SCS collection only when SCS sampling is documented.

## Current snapshot

Source-review update: **13 October 2026**. SCS discovery window: **12 October 2016–12 October 2026**; international discovery window: **13 October 2016–13 October 2026**.

- 277 unique curated source profiles: 72 polar papers, 160 SCS studies and 45 newly added international comparison sources
- 296 evidence claims, with every curated paper represented
- 327 controlled concepts; exact generated node and edge totals are available in `dist/graph.json`
- 301 unique SCS inventory DOI records with independently retrieved bibliographic metadata, including 9 labeled preprints and 3 correction notices; DOI records are not a count of independent studies
- All 301 inventory records have a screening or review decision: 160 curated, 49 awaiting supporting source text, 70 screened as context, 12 excluded, 3 linked correction notices, and 7 awaiting publication-version checks
- Of the 160 curated SCS profiles, 122 are limited to abstract evidence and 38 draw on inspected full-text passages; full-text passages do not imply every figure or supplement was reviewed
- The international view contains 49 curated comparisons: 45 new sources and four shared SCS/global sources. Twenty-six use abstract evidence and 23 use inspected full-text passages, including reused verification records
- 461 international inventory DOI records with verified bibliographic metadata: 49 curated, 356 awaiting source review, 55 awaiting version checks and one withdrawn preprint excluded from evidence
- SCS/international inventory overlap is 17 DOIs: 301 + 461 − 17 = 745 unique cold-seep inventory DOI records. This includes preprints and notices and is not an independent-study total
- 155 inventory records have a provisional microbial-priority tag; thematic tags overlap and are not additive paper counts
- Nine compartment labels, including explicit categories for unreported sampling medium, wood/organic substrates and terrestrial seep water/ice, and fourteen microbial/environmental themes
- The original polar queue remains separate: 161 screened current candidates, with 12 retained for verification, 10 background/methods references, 12 deferred, and 127 excluded
- Across the polar current-and-archived review ledger, 27 retained candidates have verification packets: 14 full-text checked and promoted, 1 publisher page checked, and 12 DOI/abstract checked

Domain labels intentionally overlap: a paper about viruses beneath an ice shelf can contribute simultaneously to the Antarctic-virus, Antarctic-prokaryote, and polar-Earth-system views.

The SCS inventory combines five Europe PMC queries, thirteen Crossref searches, and an explicit supplementary DOI list for studies whose SCS sampling is documented in the paper. It is a cumulative discovery inventory, not a completed systematic review. Uncurated discovery tags remain provisional; curated classifications follow inspected source material. Month/year-only publication dates retain their original precision and are accepted only when their entire possible date interval falls inside the window.

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

# Discover SCS seep papers in a rolling ten-year window.
make update-cold-seeps

# Discover international cold-seep comparisons in a rolling ten-year window.
make update-global-cold-seeps

# After inspecting source material and editing explicit international packets:
python3 scripts/curate_global_cold_seep_reviews.py
make global-cold-seep-report

# Independently refresh DOI metadata and regenerate the APA 7 inventory.
python3 scripts/export_cold_seep_references.py --verify

# Export the SCS review queue and bilingual evidence profiles.
make cold-seep-review-report

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
python3 scripts/update_cold_seep_candidates.py --since 2016-10-12 --until 2026-10-12
```

Review decisions are stored separately in `data/candidate_reviews.json`, so rerunning discovery does not overwrite them. Detailed verification packets are stored in `data/candidate_verifications.json`; they explicitly distinguish full-text checks from publisher-page or abstract-only checks. `data/candidate_archive.json` preserves records that disappear from a later bounded search or are promoted into the curated collection. Candidate identifiers are reused across refreshes by DOI or normalized title, and the discovery script records first-seen, last-seen, and discovery-run provenance. `dist/candidate-review.csv` is the sortable review sheet and `dist/candidate-review-summary.md` is the human-readable audit. Newly discovered records appear as unreviewed until a corresponding ledger entry is added.

For SCS reviews, edit explicit bilingual evidence packets in `config/cold_seep_reviewed.json` and non-curated decisions in `config/cold_seep_review_decisions.json` after inspecting the relevant source. `python3 scripts/inspect_cold_seep_sources.py --pending --skip-cached` retrieves available material into the ignored local research cache; retrieval itself is not a review. `python3 scripts/curate_cold_seep_reviews.py` materializes new packets and persistent decisions. Use `--refresh` only when intentionally updating the existing packet-derived profiles. Then run `python3 scripts/update_cold_seep_candidates.py --reclassify`, `make translations`, and `make all`. Cumulative discovery retains previously found records within the window, even if a later bounded search ranks them below its retrieval limit. Correction notices and unresolved preprints retain separate audit statuses.

International comparisons use `config/global_cold_seep_reviewed.json` and `scripts/curate_global_cold_seep_reviews.py`. Each packet records the exact sampled scope, design, supported finding, citation limit and discussion use in English and Chinese. `existing_source_id` reuses a previously verified source without duplicating its DOI or graph claim. The builder exposes shared collection membership and collection-specific tags. Abstract-based source profiles remain abstract-based after metadata refresh. Preprint and withdrawal states are derived from explicit bibliographic status and remain separate from evidence review. Successful same-day query responses are cached locally so interrupted discovery can resume; the complete successful query set is required before replacing the inventory.

International records that age out of the moving window are retained in `data/public/global_cold_seep_archive.json`. Their reviewed profiles and decisions remain available for historical or mechanistic citation, while the active discovery inventory continues to satisfy the ten-year window. Expanding the window can restore archived records without changing IDs.

Use `--review-date YYYY-MM-DD` when materializing newly inspected international packets. Existing source verification dates persist; explicitly change a packet's `reviewed_at` only after another evidence check.

Before committing an updated release, regenerate and check the rights-conscious public snapshots:

```bash
make public-snapshot
make public-check
git add .
git commit -m "Update evidence atlas"
git push
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

For seeps, water depth, height above seabed, sediment depth, porewater, and host tissue are distinct sampling dimensions. RNA, gene annotations, metabolic models, isotope-incubation rates, and direct in situ measurements retain separate evidence limits. See the [cold-seep guide](article/south-china-sea-cold-seep-guide.md).

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
