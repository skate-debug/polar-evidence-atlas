#!/usr/bin/env python3
"""Materialize inspected SCS source profiles without modifying polar records."""
from __future__ import annotations
import html
import argparse
import json
import re
from datetime import date
from pathlib import Path
from citation_utils import bibliographic_date_parts

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHECKED = "2026-10-12"
CONCEPTS = [
    ("region:south-china-sea", "Region", "South China Sea", "Named marginal-sea scope for the cold-seep collection.", ""),
    ("region:haima-seep", "Region", "Haima cold seep", "Haima seep field and associated sampling areas in the South China Sea.", "region:south-china-sea"),
    ("region:site-f-seep", "Region", "Site F / Formosa Ridge seep", "Site F, also described as the Formosa cold seep, with study-specific stations retained in profiles.", "region:south-china-sea"),
    ("region:lingshui-seep", "Region", "Lingshui cold seep", "Lingshui seep sampling area used in interface-water comparisons.", "region:south-china-sea"),
    ("region:haiyang4-seep", "Region", "Haiyang 4 seep", "Named SCS seep area represented in comparative metagenomic datasets.", "region:south-china-sea"),
    ("region:dongsha-hydrates", "Region", "Dongsha / GMGS2 sites", "Northern SCS hydrate-expedition sites; exact drilling stations are source-specific.", "region:south-china-sea"),
    ("region:shenhu", "Region", "Shenhu area", "SCS gas-hydrate drilling area represented in subseafloor microbial studies.", "region:south-china-sea"),
    ("region:qiongdongnan", "Region", "Qiongdongnan Basin", "SCS basin represented in hydrate and seep microbial datasets.", "region:south-china-sea"),
    ("region:newborn-scs-seep", "Region", "Newborn SCS seep", "Human-induced methane seep monitored during ecosystem development; retain station-specific metadata.", "region:south-china-sea"),
    ("habitat:cold-seep", "Habitat", "Cold seep", "Operational collection class for seabed fluid-seepage ecosystems.", ""),
    ("habitat:seep-water-column", "Habitat", "Seep water column", "Water-depth profiles sampled above a seep; distinct from sediment profiles.", "habitat:marine-water-column"),
    ("habitat:seep-bottom-water", "Habitat", "Seep bottom water", "Near-seabed water; exact height above bottom must be taken from the study.", "habitat:seep-water-column"),
    ("habitat:seep-interface", "Habitat", "Seep sediment–water interface", "Water and sediment boundary layer at a seep, as operationally sampled by each study.", "habitat:cold-seep"),
    ("habitat:seep-sediment", "Habitat", "Seep sediment", "Sediment depth intervals collected in seep-affected areas.", "habitat:cold-seep"),
    ("habitat:hydrate-bearing-sediment", "Habitat", "Hydrate-bearing sediment", "Sediment containing gas hydrates, with present and buried seep contexts recorded separately.", "habitat:seep-sediment"),
    ("habitat:seep-symbiosis", "Habitat", "Seep host-associated microbiome", "Microorganisms sampled from animal hosts such as sponges, mussels, or clams.", "habitat:cold-seep"),
    ("habitat:seep-carbonate", "Habitat", "Seep carbonates and mats", "Carbonate or mat habitats represented in seep sampling designs.", "habitat:cold-seep"),
    ("taxon:anme", "Taxon", "Anaerobic methanotrophic archaea (ANME)", "Operational archaeal groups associated with anaerobic methane oxidation; clade assignments follow the source.", "realm:archaea"),
    ("taxon:methylococcales", "Taxon", "Methylococcales", "Bacterial order containing methanotrophic populations profiled in seep water and sediment.", "realm:bacteria"),
    ("taxon:campylobacterota", "Taxon", "Campylobacterota", "Bacterial phylum including Sulfurovum and Sulfurimonas in the curated seep studies.", "realm:bacteria"),
    ("process:anaerobic-methane-oxidation", "Process", "Anaerobic methane oxidation", "Methane oxidation under anoxic conditions; electron-acceptor pathways are recorded separately.", ""),
    ("process:aerobic-methane-oxidation", "Process", "Aerobic methane oxidation", "Methane oxidation associated with oxygen availability.", ""),
    ("process:metal-dependent-aom", "Process", "Metal-dependent AOM", "Methane oxidation linked to metal reduction; support may be geochemical, genomic, or model-derived.", "process:anaerobic-methane-oxidation"),
    ("process:nitrogen-methane-coupling", "Process", "Nitrogen-coupled methane oxidation", "Methane transformations coupled with nitrate or nitrite metabolism in the inspected studies.", ""),
    ("process:fermentation", "Process", "Macromolecule fermentation", "Anaerobic conversion of organic substrates, represented by genomic and transcript evidence.", ""),
    ("process:community-assembly", "Process", "Microbial community assembly", "Observed community patterns and statistical estimates of ecological assembly.", ""),
    ("process:microbial-evolution", "Process", "Microbial population evolution", "Population-genomic variation, recombination, and selection analyses.", ""),
    ("process:viral-defense", "Process", "Microbial defense and viral counter-defense", "Genes and experiments addressing microbial protection and viral anti-defense.", ""),
    ("process:organic-matter-degradation", "Process", "Organic-matter degradation", "Microbial use or transformation of organic compounds.", ""),
    ("process:mercury-transformation", "Process", "Mercury transformations", "Mercury methylation, demethylation, and reduction evidence recorded with assay limits.", ""),
    ("process:phosphorus-cycling", "Process", "Microbial phosphorus cycling", "Genetic and biochemical pathways for phosphorus acquisition and transformation.", ""),
    ("process:reductive-dehalogenation", "Process", "Reductive dehalogenation", "Reduction-associated removal of halogens from organohalides; genes and experiments are distinguished.", ""),
    ("process:quorum-sensing", "Process", "Quorum sensing", "Chemical signaling systems examined using sequence, expression, and experimental evidence.", ""),
    ("process:chemosynthetic-symbiosis", "Process", "Chemosynthetic symbiosis", "Host–microbe associations involving chemically fueled microbial metabolism.", ""),
    ("process:methane-biofilter", "Process", "Seep methane biofilter", "Methane-removal functions attributed to microbial and animal-associated processes within a defined study.", ""),
    ("method:q-pcr", "Method", "Quantitative PCR", "Targeted amplification used to estimate marker-gene abundance.", ""),
    ("method:geochemistry", "Method", "Porewater and water geochemistry", "Chemical and isotopic characterization of water, sediment, or porewater.", ""),
    ("method:size-fractionation", "Method", "Particle-attached/free-living fractionation", "Operational size separation of water microbial fractions; filter cutoffs are study-specific.", ""),
    ("method:reactive-transport-model", "Method", "Reactive-transport modeling", "Model-based estimates of sediment reactions and material transport.", ""),
    ("method:cultivation", "Method", "Microbial cultivation", "Isolation and physiological examination of cultivable microorganisms.", ""),
    ("method:in-situ-incubation", "Method", "In situ incubation", "Incubation deployed within the sampled marine environment.", ""),
    ("method:laboratory-incubation", "Method", "Laboratory incubation", "Controlled experimental exposure outside the original environment.", ""),
    ("method:metabolic-model", "Method", "Genome-scale metabolic modeling", "Computational metabolic predictions from reconstructed genomes.", ""),
    ("method:protein-language-model", "Method", "Protein language model", "Machine-learning representation of protein sequences for functional prediction.", ""),
    ("method:heterologous-expression", "Method", "Heterologous expression", "Expression of selected genes in a surrogate host for functional testing.", ""),
    ("method:isotope-rate-assay", "Method", "Isotope-based process-rate assay", "Labeled-substrate experiments used to quantify defined transformations.", ""),
    ("method:in-situ-monitoring", "Method", "In situ seabed monitoring", "Repeated ecosystem and chemical observations in the original seabed setting.", ""),
    ("method:in-situ-transplant", "Method", "In situ transplant experiment", "Transplantation within the seabed environment to compare ecological responses.", ""),
]
SITE_REGION = {"haima": "region:haima-seep", "site-f": "region:site-f-seep", "lingshui": "region:lingshui-seep", "haiyang4": "region:haiyang4-seep", "dongsha": "region:dongsha-hydrates", "shenhu": "region:shenhu", "qiongdongnan": "region:qiongdongnan", "newborn": "region:newborn-scs-seep"}
HABITATS = {"water-column": "habitat:seep-water-column", "bottom-water": "habitat:seep-bottom-water", "sediment": "habitat:seep-sediment", "interface": "habitat:seep-interface", "symbiosis": "habitat:seep-symbiosis", "carbonate": "habitat:seep-carbonate"}
VARIABLES = {
    "haima-anme-zonation": ["archaeal marker-gene diversity and abundance", "mcrA phylogeny", "sulfate and dissolved inorganic carbon profiles"],
    "gmgs2-hydrate-diversity": ["qPCR marker-gene abundance", "16S community diversity", "hydrate/carbonate zonation"],
    "water-particle-fractions": ["particle-attached/free-living marker-gene abundance", "community diversity", "water chemistry"],
    "new-seep-dna-rna": ["paired DNA/RNA community composition", "ANME marker abundance", "geochemical gradients"],
    "sulfur-smtz-genomes": ["sulfur-cycling MAG inventories", "pathway genes and transcripts", "sulfate–methane zonation"],
    "haima-bottom-water-intensity": ["16S diversity", "methane and nutrient concentrations", "community associations"],
    "site-f-mag-resource": ["MAG counts and completeness", "taxonomic assignments", "water and sediment genome inventories"],
    "methane-supply-assembly": ["methane-supply classes", "ANME relative abundance", "assembly and network metrics"],
    "deep-hydrate-fermentation": ["MAG metabolic pathways", "transcript abundance", "sulfate–methane zonation"],
    "seep-population-evolution": ["within-species nucleotide diversity", "homologous recombination", "selection on pmoA, mcrA, and dsrA"],
    "metal-dependent-aom": ["porewater iron and manganese", "ANME genes and transcripts", "model-estimated metal-linked methane consumption"],
    "active-aom-pathways": ["13CH4-based potential methane oxidation rates", "electron-acceptor consumption", "functional gene transcripts"],
    "campylobacterota-interface": ["isolate growth physiology", "hydrogen/sulfur/nitrogen genes and transcripts", "nitrate changes"],
    "haima-viral-evolution": ["viral operational taxonomic units", "predicted host links", "viral nucleotide diversity and defense genes"],
    "haima-fungal-networks": ["fungal/prokaryotic network metrics", "fungal functional genes", "fungal transcript signals"],
    "haima-water-sediment-networks": ["bacterial community composition", "network metrics", "elemental distributions"],
    "haima-water-assembly": ["depth-dependent community diversity", "hydrochemistry", "modeled assembly processes"],
    "lingshui-sitef-interface": ["16S community composition", "predicted methane-cycle functions", "interface-water geochemistry"],
    "haima-mercury": ["Hg and methylmercury concentrations", "mercury isotope composition", "hgcA, merA, and merB genes"],
    "haima-water-nitrogen-fixation": ["nitrogen-fixation rates", "nifH community profiles", "sulfur-oxidation and diazotrophy genes"],
    "haima-microeukaryote-dna-rna": ["DNA/RNA diversity across microbial domains", "environmental parameters", "assembly estimates"],
    "site-f-water-metabolism": ["water-column MAG inventories", "metabolic module coverage", "predicted microbial exchanges"],
    "phosphorus-lucapcycle": ["phosphorus-cycling protein families", "model classification performance", "selected phosphatase activity"],
    "seep-dehalogenation": ["RdhA-like gene diversity and expression", "organohalide chemistry", "incubation/metabolomic evidence"],
    "seep-quorum-sensing": ["quorum-sensing genes and transcripts", "LuxI–LuxR heterologous activity", "candidate signaling metabolites"],
    "site-f-sponge-partitioning": ["taxonomic diversity", "MAG features", "sulfur/methane-associated gene inventories"],
    "seep-defense-systems": ["microbial defense and viral anti-defense systems", "candidate-defense assay outcomes", "gene/transcript distributions"],
    "site-f-water-spatial-2026": ["vertical/horizontal community abundance", "pmoA distribution", "sulfur-oxidation genes"],
    "haima-domains-water-sediment-2026": ["prokaryotic/microeukaryotic diversity", "habitat-specific networks", "assembly estimates"],
    "seep-nitrogen-methane-n2o": ["14C-based potential methane-oxidation rates", "net N2O production", "methane/nitrogen pathway genes"],
    "newborn-seep-biofilter": ["seep-community succession", "methane removal", "sediment/porewater chemistry"],
    "haima-anme1-hotspots": ["circular ANME-1 genomes", "genomic hotspots", "hicAB heterologous phenotypes"],
    "haima-clam-sulfide-2026": ["symbiont abundance", "host/symbiont gene expression", "sulfur-metabolism proteins"],
    "site-f-sponge-host-specificity": ["16S community composition", "taxonomic diversity", "host-associated bacterial phylogeny"],
}


def read(path, fallback=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def write(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="replace only this release's explicit seed IDs from the inspected seed specifications")
    args = parser.parse_args()
    specs = read(ROOT / "config" / "cold_seep_seed.json")
    sources = read(DATA / "sources.json")
    claims = read(DATA / "claims.json")
    concepts = read(DATA / "concepts.json")
    metadata = read(DATA / "metadata.json", read(DATA / "public" / "metadata.json", {"records": {}}))
    if args.refresh:
        seed_source_ids = {"src:scs-" + spec["slug"] for spec in specs}
        seed_claim_ids = {"claim:scs-" + spec["slug"] for spec in specs}
        sources = [source for source in sources if source["id"] not in seed_source_ids]
        claims = [claim for claim in claims if claim["id"] not in seed_claim_ids]
    checked_metadata = read(DATA / "cold_seep_metadata.json", {}).get("records", {})
    known_concepts = {item["id"] for item in concepts}
    for cid, kind, label, description, broader in CONCEPTS:
        if cid not in known_concepts:
            concept = {"id": cid, "type": kind, "label": label, "description": description}
            if broader:
                concept["broader"] = broader
            concepts.append(concept)
    by_doi = {source["doi"].lower(): source for source in sources}
    known_claim_ids = {claim["id"] for claim in claims}
    for spec in specs:
        doi = spec["doi"]
        cached = read(ROOT / ".research-cache" / (re.sub(r"[^a-z0-9]+", "-", doi) + ".json"), {})
        record = cached.get("csl") or checked_metadata.get(doi)
        if not record:
            raise SystemExit(f"Missing independently resolved DOI metadata: {doi}")
        title = record.get("title", "")
        if isinstance(title, list):
            title = title[0]
        title = " ".join(re.sub(r"<[^>]+>", "", html.unescape(title)).split())
        title = re.sub(r"N\s*2\s*O", "N2O", title)
        parts = bibliographic_date_parts(record)
        if not parts:
            raise SystemExit(f"Missing verified year: {doi}")
        source_id = "src:scs-" + spec["slug"]
        if doi not in by_doi:
            regions = ["region:south-china-sea"] + [SITE_REGION[site] for site in spec["sites"] if site in SITE_REGION]
            access = spec.get("access") or ("full_text_extracts" if cached.get("sections") else "abstract")
            profile = {
                "id": source_id, "citation_key": "SCS" + "".join(part.title() for part in spec["slug"].split("-")),
                "doi": doi, "title": title, "year": int(parts[0]), "poles": [], "regions": regions,
                "collection": "scs-cold-seeps", "compartments": spec["compartments"], "topics": spec["topics"], "sites": spec["sites"],
                "domains": spec.get("domains", ["Cold-seep prokaryotes", "Cold-seep biogeochemistry"]),
                "study_type": spec["type"],
                "study_profile": {"spatial_scope": spec["space"], "temporal_scope": spec["time"],
                    "habitats": [HABITATS[compartment] for compartment in spec["compartments"]],
                    "methods": ["method:" + method for method in spec["methods"]], "sample_design": spec["design"],
                    "measured_or_derived": VARIABLES[spec["slug"]],
                    "focal_taxa": ["taxon:" + taxon for taxon in spec["taxa"]],
                    "focal_processes": ["process:" + process for process in spec["processes"]], "environmental_drivers": []},
                "key_findings": [spec["finding"]], "limitations": [spec["limit"]],
                "cite_for": [spec["type"] + " in the stated sampling scope", spec["finding"]],
                "do_not_overcite": ["Causal mechanisms, in situ rates, or geographic generality beyond the evidence described in this profile."],
                "data_accessions": sorted({accession for section in cached.get("sections", []) if re.search(r"data|availability", section["section"], re.I) for paragraph in section["paragraphs"] for accession in re.findall(r"\bPRJ(?:NA|EB|DB)\d+\b", paragraph)}),
                "curation": {"status": "curated", "basis": "Independently resolved DOI metadata; inspected abstract and the evidence locators listed in claims. Access level: " + access + ".", "last_verified": CHECKED, "access_level": access},
            }
            if spec.get("correction_doi"):
                profile["curation"]["correction_doi"] = spec["correction_doi"]
            sources.append(profile)
            by_doi[doi] = profile
        metadata["records"][doi] = record
        claim_id = "claim:scs-" + spec["slug"]
        if claim_id not in known_claim_ids:
            claims.append({"id": claim_id, "source_id": source_id, "subject": source_id,
                "predicate": spec.get("predicate", "associated_with"), "object": spec["object"], "statement": spec["finding"], "scope": spec["space"],
                "evidence_type": spec["claim_type"], "evidence_basis": spec["design"], "locator": spec["locator"],
                "confidence": "moderate", "confidence_note": spec["limit"]})
    write(DATA / "sources.json", sources)
    write(DATA / "claims.json", claims)
    write(DATA / "concepts.json", concepts)
    write(DATA / "metadata.json", metadata)
    locations = read(DATA / "locations.geojson")
    existing_locations = {item["id"] for item in locations["features"]}
    for cid, kind, label, _, _ in CONCEPTS:
        if kind == "Region" and cid not in existing_locations:
            locations["features"].append({"type": "Feature", "id": cid, "geometry": None, "properties": {"label": label, "coordinate_status": "Named study area; use source-specific station coordinates and cruise metadata"}})
    write(DATA / "locations.geojson", locations)
    print(f"Cold-seep seed: {len(specs)} profiles and claims. Total: {len(sources)} sources, {len(claims)} claims, {len(concepts)} concepts.")


if __name__ == "__main__":
    main()
