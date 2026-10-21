# Rebuild the data from source, in dependency order.
# Every step is idempotent: LLM steps reuse earlier validated decisions whose
# inputs are unchanged (intervention names: whatever their trial context; pipeline/llm.py),
# loaders upsert, and builds replace.
# Requires DATABASE_URL and ANTHROPIC_API_KEY in .env, a venv from `uv sync`,
# and pdftoppm (poppler) and tesseract on PATH for OCR of scanned FDA letters. LLM steps use the
# Batches API above LLM_DIRECT_MAX new items (default 100); raise it to call the API directly,
# LLM_WORKERS (default 24) calls at a time.

PY := .venv/bin/python
RUN := $(PY) -m

.PHONY: all sources identity programs labels evidence migrate

all: migrate sources identity programs labels evidence

migrate:
	$(PY) db/migrate.py apply

# Raw sources: ClinicalTrials.gov snapshot and results papers, FDA approvals (CDER + CBER) and
# the uses each approval letter states, UNII substance names, ontologies.
sources:
	$(RUN) pipeline.ctgov fetch
	$(RUN) pipeline.ctgov load
	$(RUN) pipeline.outcomes results
	$(RUN) pipeline.outcomes publications
	$(RUN) pipeline.fda fetch
	$(RUN) pipeline.fda load
	$(RUN) pipeline.cber.enumerate_year_pages
	$(RUN) pipeline.cber.crawl_products
	$(RUN) pipeline.cber.historic_products
	$(RUN) pipeline.cber.download_letters
	$(RUN) pipeline.cber.build_letters
	$(RUN) pipeline.cber.find_missing
	$(RUN) pipeline.cber.find_missing2
	$(RUN) pipeline.cber.assemble
	$(RUN) pipeline.fda load-cber
	$(RUN) pipeline.fda extract
	$(RUN) pipeline.unii load
	$(RUN) pipeline.ontology load

# Identity: trial links, conditions -> MONDO, interventions -> molecular entities, FDA products -> entities,
# entities -> UNII substances (merging entities that are the same substance).
identity:
	$(RUN) pipeline.programs register
	$(RUN) pipeline.indications map
	$(RUN) pipeline.drugs canonicalize
	$(RUN) pipeline.fda link
	$(RUN) pipeline.drugs unii

# Programs: entity role and purpose of each trial, each entity's diseases grouped into indications,
# then (entity, indication) programs.
programs:
	$(RUN) pipeline.programs roles
	$(RUN) pipeline.programs purposes
	$(RUN) pipeline.programs indications
	$(RUN) pipeline.programs build

# Labels on programs: approval, modality, disease area, trial outcomes, targets.
labels:
	$(RUN) pipeline.approvals judge
	$(RUN) pipeline.drugs modality
	$(RUN) pipeline.indications areas
	$(RUN) pipeline.outcomes classify
	$(RUN) pipeline.targets resolve

evidence:
	$(RUN) pipeline.opentargets fetch
	$(RUN) pipeline.opentargets load
