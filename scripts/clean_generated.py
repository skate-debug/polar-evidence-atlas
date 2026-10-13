#!/usr/bin/env python3
"""Remove only the explicit generated files produced by scripts/build.py."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "dist" / "polar-knowledge-graph.html",
    ROOT / "dist" / "earth-ocean-evidence-atlas.html",
    ROOT / "dist" / "graph.json",
    ROOT / "dist" / "nodes.csv",
    ROOT / "dist" / "edges.csv",
    ROOT / "dist" / "graph.graphml",
    ROOT / "dist" / "kg.jsonld",
    ROOT / "references" / "polar-kg.bib",
    ROOT / "references" / "earth-ocean-kg.bib",
    ROOT / "dist" / "candidate-review.csv",
    ROOT / "dist" / "candidate-review-summary.md",
]

removed = 0
for target in TARGETS:
    if target.is_file():
        target.unlink()
        removed += 1
print(f"Removed {removed} generated file(s).")
