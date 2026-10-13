# Earth and ocean knowledge-graph ontology

## Design principles

1. **Provenance before density.** Every asserted relationship must resolve to at least one curated claim and one source.
2. **Claims are scoped.** Location, habitat, depth, season, sampling period, and analytical basis are retained whenever the paper supplies them.
3. **Observation is not mechanism.** Direct results, genomic potential, statistical association, model projection, and review synthesis use different evidence labels.
4. **Candidate literature is quarantined.** Automated discovery creates metadata-only candidate records; it never creates claims.
5. **Stable identifiers.** Local identifiers remain stable even if labels or taxonomic names are revised.

## Node classes

| Class | Purpose | Examples |
|---|---|---|
| `Source` | A paper, review, or data descriptor | DOI-backed article |
| `Claim` | Atomic evidence statement | summer viral coverage exceeds cellular coverage |
| `Pole` | High-level polar scope | Arctic, Antarctic, Bipolar |
| `Region` | Ocean, sea, island, basin, shelf, or named site | Fram Strait, Ross Ice Shelf |
| Collection and filter taxonomy | Independent browsing axes stored in `config/collections.json` | polar systems; SCS cold seeps; water/sediment; research topic; study site |
| `Habitat` | Sampled ecological setting | sea ice, permafrost, subglacial lake |
| `Realm` | Broad biological grouping | Viruses, Bacteria, Archaea, Eukaryota |
| `Taxon` | Named lineage at any rank | Caudoviricetes, Nitrospira, diatoms |
| `Process` | Biological or Earth-system transformation | nitrification, carbon export, Atlantification |
| `Driver` | Environmental forcing or constraint | temperature, sea-ice cover, iron limitation |
| `Nutrient` | Element or chemical resource | nitrate, ammonium, iron, manganese |
| `WaterMass` | Named current, water mass, or overturning limb | Antarctic Bottom Water, Atlantic Water |
| `Method` | Sampling, laboratory, computational, or synthesis method | metagenomics, stable-isotope probing |
| `Dataset` | Reusable accession or data product | PRJEB95143, Arctic MAG catalogue |

## Claim predicates

Predicates are verbs in lower snake case. Their inverse is not automatically asserted.

- `harbours` — a region/habitat contains a taxon or realm.
- `associated_with` — a non-causal statistical or ecological association.
- `infects_or_targets` — host link supported by cultivation, genomic linkage, or explicit inference; the evidence basis must state which.
- `encodes_potential_for` — sequence-based metabolic potential, not measured process rate.
- `drives` — causal language used only when the study design supports it.
- `increases`, `decreases`, `shifts_to` — directional result with a defined comparison.
- `supplies`, `exports`, `transports`, `mixes_with` — material or water movement.
- `limits`, `co_limits` — experimental or synthesis-based resource limitation.
- `supports` — enables a process without claiming exclusivity.
- `formed_by`, `separates`, `connects` — geographical/geological relationships.
- `catalogues` — source or dataset enumerates entities.
- `projects` — model-based future statement.

## Evidence dimensions

`evidence_type` is one of:

- `reported` — observed or experimentally measured by the source.
- `inferred` — derived from genome content, co-occurrence, host prediction, proxy, or another inferential method.
- `modeled` — produced primarily by a numerical/statistical model.
- `synthesized` — conclusion assembled by a review or meta-analysis.

`confidence` is one of `high`, `moderate`, or `low`. A confidence value must be paired with `confidence_note`.

`locator` should be specific enough to retrieve the evidence: abstract, named Results/Methods section, figure, table, supplementary item, or page.

## Citation safety

Each source profile contains:

- `cite_for`: statements for which the paper is a good citation.
- `do_not_overcite`: claims that exceed its design or scope.
- `limitations`: sampling, analytical, geographic, temporal, or inferential constraints.
- `curation_basis`: whether the profile was checked against the abstract, full text, data descriptor, or review.

Paraphrases are used instead of copied abstracts. Quantitative values are retained only when citation value justifies them.

## Cold-seep collection

SCS sources use `collection=scs-cold-seeps`, region concept IDs, and an empty
`poles` array. South China Sea is represented as a region rather than a polar
class. `compartments`, `topics`, and `sites` are independent, overlapping filters.
Collection membership does not itself assert a biological relationship.

`data/public/cold_seep_candidates.json` is a discovery inventory. Its automatic
title/abstract tags remain provisional unless a source has a corresponding
curated profile. The inventory does not generate scientific claims. Comparative
global studies are included only when SCS sampling is explicit; global totals
must not be quoted as SCS totals.

The SCS publication window is a rolling ten years. The release of 12 October
2026 covers 12 October 2016 through 12 October 2026. Discovery uses first
publication dates; citations follow the version-of-record bibliographic year.

## JSON-LD mapping

The generated `kg.jsonld` uses a small local vocabulary rooted at `https://example.org/polar-kg/`. DOI URLs are retained as `sameAs`. This local context can later be replaced or aligned with PROV-O, schema.org, ENVO, NCBI Taxonomy, GO, ChEBI, and GeoNames identifiers without changing local IDs.

