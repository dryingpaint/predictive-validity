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

Every table and column carries a `COMMENT ON` saying what a row is, which step writes it, and what each
column means, its values and what null means (`\d+ preclin.<table>` in psql). Each group below is owned
by the step named; no other step writes it.

| Group | Tables | Written by |
|---|---|---|
| Trials | `preclin.ctgov_study`, `preclin.ctgov_result_summary` | `pipeline.ctgov`, `pipeline.outcomes results` |
| Trial interventions and conditions | `preclin.ctgov_study_drug`, `preclin.ctgov_study_indication`, `preclin.drug`, `preclin.indication` | `pipeline.programs register`; `pipeline.indications map` maps conditions to MONDO |
| Molecular entities | `preclin.moiety`, `preclin.drug_moiety`, `preclin.ctgov_study_moiety` | `pipeline.drugs`, `pipeline.programs roles` |
| Substances | `preclin.unii_substance`, `preclin.unii_name`, `preclin.unii_parent` | `pipeline.unii load` |
| Ontologies and disease areas | `preclin.ontology_*`, `preclin.mondo_bio_area` | `pipeline.ontology load`, `pipeline.indications areas` |
| Development programs | `preclin.dev_program`, `preclin.dev_program_trial`, `preclin.dev_program_build`, `preclin.program_indication`, `preclin.trial_purpose`, `preclin.trial_phase_role` | `pipeline.programs` |
| FDA approvals | `preclin.fda_*`, `preclin.dev_program_approval` | `pipeline.fda`, `pipeline.cber`, `pipeline.approvals judge` |
| Trial labels | `preclin.trial_outcome`, `preclin.trial_endpoint`, `preclin.trial_publication`, `preclin.trial_biomarker_selection` | `pipeline.outcomes` |
| Targets and their genetics | `preclin.moiety_target`, `preclin.gene_disease_mechanism`, `preclin.mouse_model_relation` | `pipeline.targets` |
| Open Targets evidence | `preclin.ot_*`, `preclin.evidence_known_year`, `preclin.clinvar_accession_calibration` | `pipeline.opentargets`, `pipeline.evidence_dates` |
| Drug pharmacology | `preclin.chembl_*`, `preclin.moiety_property` | `pipeline.chembl`, `pipeline.pubchem properties` |
| Cell screens | `preclin.depmap_common_essential`; `preclin.cell_dependency`, `preclin.cell_line`, `preclin.cell_screen` (being added) | `pipeline.depmap` |
| Gene reference | `preclin.hgnc_gene` | `pipeline.hgnc load` |
| Drug literature | `preclin.literature_*` (being consolidated into one set of tables), `preclin.moiety_publication`, `preclin.pubmed_search` | `pipeline.literature`, `pipeline.attribution literature` |
| Stops | `preclin.stop`, `preclin.stop_signal`, `preclin.stop_continuation`, `preclin.analysis_method` | `pipeline.stop_causes`, `pipeline.attribution` |
| Whether a disease term that contains another is one development indication or a grouping term (#185) | `pipeline.programs scope` | `preclin.disease_term_scope` |
| Target-disease hypotheses | `preclin.target_disease` (one row per primary target and disease that reached Phase 2: first entry, programs, whether already validated, read from the evidence chart's approval index), `preclin.target_disease_origin` (what first proposed each: provisional from dated evidence, or labelled from pre-entry sources, with the two checkers' outcome, disputed and not_reached as their own values, and the first drug's discovery route), `preclin.target_disease_search`, `preclin.target_disease_source` (pre-entry PubMed and Europe PMC records per pair, shared with #154) | `pipeline.target_disease` |
| Target-biology literature | `preclin.target_literature_search`, `preclin.target_literature_hit`, `preclin.target_literature_prefilter`, `preclin.target_literature_screen`, `preclin.target_literature_web_study` (each target-disease pair's searches, the records returned, each record's reading for the seven kinds of #154, and the studies the web-search arm and the yardstick named) | `pipeline.target_literature` |
| Why engaged drugs failed | `preclin.stop_target_history` (each engaged-without-benefit efficacy stop: what other drugs on its target did, and a verdict read from the sources where that leaves it open) | `pipeline.target_history` |
| Limits of single-target drugs (#197) | `preclin.mechanism_pathway` (the signalling pathways each atlas mechanism acts through, with spelling variants merged into canonical names), `preclin.combination_trial` (each shortlisted disease's randomised trials of two pathways against one, with how the pathways relate, the result and what limited it) | `pipeline.single_target pathways`, `pipeline.single_target combos` |
| Evidence dataset | `preclin.evidence_kind`, `preclin.evidence_fact`, `preclin.evidence_kind_fact`, `preclin.evidence_entry`, `preclin.evidence_entry_fact`, `preclin.evidence_entry_kind` (view), `preclin.evidence_line_build` | `report.evidence_lines store` (`check` says whether it is stale) |
| Model-system atlas | `preclin.atlas_*` (build, indication, moiety_review, mechanism, member, register view, track_entry, track_verdict, source_document) | `analyses/model-system-atlas/class_audit.py store`, `fetch_sources.py store`, `drafts/track_store.py` |
| Provenance | `preclin.evidence_source_release` (every source release read), `pv_evidence.llm_decision` and `pv_evidence.llm_decision_run` (every LLM decision and run), `preclin.schema_migration` (this runner) | the loaders, `pipeline.llm`, `db/migrate.py` |

`public.targets` (genes with Ensembl ids and symbols) and `public.gene_constraint` (gnomAD v4.1
LOEUF) come from an earlier genome-browser import and have no loader in this repository;
`public.publications` holds the PubMed articles `pipeline.outcomes publications`,
`pipeline.attribution literature`, `pipeline.literature` and `pipeline.target_literature` fetch. Columns of `preclin.drug`,
`preclin.indication` and `public.targets` from that earlier import that no step writes or reads say so
in their comments.
