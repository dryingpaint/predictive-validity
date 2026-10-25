# Database

Neon Postgres holds the data the report is built from. This directory has the schema and the
migration runner; the pipeline that fills the tables is `pipeline/` (see the root README and
Makefile).

## Files

| File | Role |
|---|---|
| `schema.sql` | The whole schema as of migration 92: tables, functions and comments in `preclin`, `public` and `pv_evidence`. Earlier migrations are squashed into it; their rows stay in `preclin.schema_migration` as history. |
| `NN_name.sql` / `NN_name.py` (NN > 92) | Migrations after the schema, applied in order. Never edit one once applied: the runner records its SHA-256 and treats a change as drift. Add the next number instead. |
| `migrate.py` | Creates the schema and applies migrations. |

## Setup

```bash
export DATABASE_URL='postgresql://...'   # ask a maintainer for credentials
.venv/bin/python db/migrate.py init      # empty database -> schema.sql
.venv/bin/python db/migrate.py apply     # migrations after it
.venv/bin/python db/migrate.py status
make all                                  # fill the tables and build the report
```

`init` refuses a database that already has a schema. `apply` holds an advisory lock, runs each
pending migration and records it in `preclin.schema_migration`, which rejects updates and deletes.
Migrations that alter busy tables set `SET LOCAL lock_timeout = '3s'`.

## Tables

Each table's columns are described by its `COMMENT ON` statements (`\d+ preclin.<table>` in psql).
The pipeline steps own their tables: ClinicalTrials.gov studies (`preclin.ctgov_study*`), FDA
approvals (`preclin.fda_*`), molecular entities (`preclin.moiety`, `preclin.drug`,
`preclin.drug_moiety`, `preclin.unii_*`), diseases and ontologies (`preclin.indication`,
`preclin.ontology_*`, `preclin.mondo_bio_area`), development programs (`preclin.dev_program*`,
`preclin.program_indication`, `preclin.trial_purpose`, `preclin.trial_phase_role`), labels
(`preclin.dev_program_approval`, `preclin.trial_outcome`, `preclin.trial_endpoint`,
`preclin.trial_publication`, `preclin.moiety_target`, `preclin.gene_disease_mechanism`,
`preclin.mouse_model_relation`), Open Targets evidence (`preclin.ot_*`,
`preclin.evidence_known_year`, `preclin.clinvar_accession_calibration`), and reference genes
(`preclin.hgnc_gene`, `preclin.depmap_common_essential`, `preclin.chembl_*`). Source releases are
recorded in `preclin.evidence_source_release` and every LLM decision in
`pv_evidence.llm_decision` (with its run in `pv_evidence.llm_decision_run`).

`public.targets` (genes with Ensembl ids and symbols) and `public.gene_constraint` (gnomAD v4.1
LOEUF) come from an earlier genome-browser import and have no loader in this repository;
`public.publications` is filled by `pipeline.outcomes publications`.
