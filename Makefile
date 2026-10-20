# Rebuild the report's data and numbers from source, in dependency order.
# Every step is idempotent: LLM steps reuse earlier validated decisions whose
# inputs are unchanged (pipeline/llm.py), loaders upsert, and builds replace.
# Requires DATABASE_URL (and ANTHROPIC_API_KEY or LLM_PROVIDER) in .env.

PY := .venv/bin/python
RUN := $(PY) -m

.PHONY: all sources identity programs labels evidence report migrate

all: migrate sources identity programs labels evidence report

migrate:
	$(PY) db/migrate.py apply

# Raw sources: ClinicalTrials.gov snapshot, FDA approvals (CDER + CBER), ontologies.
sources:
	$(RUN) pipeline.ctgov fetch
	$(RUN) pipeline.ctgov load
	$(RUN) pipeline.ctgov countries
	$(RUN) pipeline.outcomes results
	$(RUN) pipeline.fda fetch
	$(RUN) pipeline.fda load
	$(RUN) pipeline.fda load-cber
	$(RUN) pipeline.ontology load

# Identity: trial links, conditions -> MONDO, interventions -> molecular entities, FDA products -> entities.
identity:
	$(RUN) pipeline.programs register
	$(RUN) pipeline.indications map
	$(RUN) pipeline.drugs canonicalize --scope industry
	$(RUN) pipeline.fda extract
	$(RUN) pipeline.fda link

# Programs: entity role in each trial, then (entity, disease) programs.
programs:
	$(RUN) pipeline.programs roles
	$(RUN) pipeline.programs build

# Labels on programs: approval, modality, disease area, trial outcomes, targets.
labels:
	$(RUN) pipeline.approvals judge
	$(RUN) pipeline.drugs modality
	$(RUN) pipeline.indications areas
	$(RUN) pipeline.outcomes classify
	$(RUN) pipeline.targets resolve

evidence:
	$(RUN) pipeline.opentargets load

report:
	$(RUN) report.section1
	$(RUN) report.section2
	$(RUN) report.quality
	$(RUN) report.figures
	$(RUN) report.render
