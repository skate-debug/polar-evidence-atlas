.PHONY: all build validate metadata candidate-metadata update update-cold-seeps cold-seep-inventory update-dry-run review-report translations translation-check public-snapshot public-check refresh serve clean

all: validate build review-report cold-seep-inventory cold-seep-references

validate:
	python3 scripts/validate.py

build:
	python3 scripts/build.py

metadata:
	python3 scripts/enrich_metadata.py

candidate-metadata:
	python3 scripts/enrich_candidate_metadata.py

update:
	python3 scripts/update_candidates.py --since 2024-01-01

update-cold-seeps:
	python3 scripts/update_cold_seep_candidates.py

cold-seep-inventory:
	python3 scripts/update_cold_seep_candidates.py --export-only

cold-seep-references:
	python3 scripts/export_cold_seep_references.py

update-dry-run:
	python3 scripts/update_candidates.py --since 2024-01-01 --dry-run

review-report:
	python3 scripts/review_candidates.py

translations:
	python3 scripts/update_zh_translations.py --generate

translation-check:
	python3 scripts/update_zh_translations.py

public-snapshot:
	python3 scripts/prepare_public_data.py

public-check:
	python3 scripts/prepare_public_data.py --check

refresh: metadata validate build review-report

serve:
	python3 -m http.server 8000

clean:
	python3 scripts/clean_generated.py
