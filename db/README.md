# `preclin.*` schema — runbook

The `preclin.*` schema in Neon Postgres is the single source of truth for the analysis. This directory has schema DDL and ingest scripts.

## File taxonomy

The numeric prefixes predate the migration ledger and describe execution order,
not one uniform file type:

| Files | Role | Change policy |
|---|---|---|
| `01`–`11` | Ordered bootstrap schema, canonical views, and initial loaders | May evolve so a fresh database reaches the current state. Any change needed by an existing database must also have a new immutable migration. |
| `12`–`13` | Repeatable source/LLM ingestion applications | May evolve. Their runs are audited in source, ingest, and LLM provenance tables—not `schema_migration`. |
| `14` and later | Immutable one-time SQL or Python migrations | Never edit after the file is recorded. Add the next migration number instead. `db/migrate.py` reports any checksum change as drift. |
| Unnumbered utilities and `analyses/classifiers/` | Repeatable refresh programs, and the trial-stoppage rescore behind `preclin.classification` (compared in `report.quality`) | May evolve; outputs must carry their own source release/run provenance. |

The repository currently has no migration 15. Its absence is historical and is
not treated as a pending migration. Migration 14 was baselined after its
obsolete Relative Success view-recreation side effect was removed; its HPO
reference and evidence postconditions were verified unchanged. It is immutable
from that baseline onward.

## Connect

```bash
export DATABASE_URL='postgresql://...'   # ask a maintainer for credentials
psql "$DATABASE_URL"
\dt preclin.*                            # list tables
\dv preclin.*                            # list views
```

## First-time setup

From the repository root:

```bash
.venv/bin/dotenv run -- sh -c 'psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/01_schema.sql'
.venv/bin/dotenv run -- .venv/bin/python db/02_ingest.py
.venv/bin/dotenv run -- sh -c 'psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/03_views.sql'
.venv/bin/dotenv run -- .venv/bin/python db/04_ingest_extra.py
.venv/bin/dotenv run -- sh -c 'psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/05_ti_views.sql'
.venv/bin/dotenv run -- .venv/bin/python db/06_ingest_more.py
.venv/bin/dotenv run -- sh -c 'psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/07_analysis_views.sql'
.venv/bin/dotenv run -- sh -c 'psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/08_strict_outcome_view.sql'
.venv/bin/dotenv run -- sh -c 'psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/09_time_cutoff_features.sql'
.venv/bin/dotenv run -- sh -c 'psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/10_clinical_trial_source_audit.sql'
.venv/bin/dotenv run -- .venv/bin/python db/11_ingest_trial_sources.py --scope classified --limit 100
```

The core database setup takes ~15 minutes; source ingestion time depends on the
selected trial scope.

After the core bootstrap, apply every pending numbered migration with the
checksum-aware runner:

```bash
.venv/bin/dotenv run -- .venv/bin/python db/migrate.py status
.venv/bin/dotenv run -- .venv/bin/python db/migrate.py apply
```

The runner initializes `preclin.schema_migration` automatically, holds a
database advisory lock, executes migrations in numeric order, and records the
exact SHA-256 of each file. An applied file that is later edited is reported as
`drift` and is never silently rerun. Python migrations use the active
repository virtual environment.

`baseline` exists only for adopting the ledger on an already-migrated
database. It records—but does not execute—older files, requires an explicit
reason and `--yes`, and labels every resulting row as `baseline`:

```bash
.venv/bin/dotenv run -- .venv/bin/python db/migrate.py baseline \
  --through 25 \
  --reason 'Verified pre-ledger production state when migration 26 was adopted' \
  --yes
```

Do not use `baseline` on a fresh or uncertain database; use `apply` instead.
Recurring source refreshes are audited in `preclin.ingest_log` or dedicated
release tables.

## Immutable database migrations (14+)

Run migrations from the repository root through `db/migrate.py`. The individual
commands below document each transition and its validation path; they are not a
replacement for the ledger-managed runner on an established database.

```bash
# Validate against the pinned official HPO release without committing.
.venv/bin/dotenv run -- .venv/bin/python db/14_reclassify_hpo_evidence.py --dry-run

# Apply after review.
.venv/bin/dotenv run -- .venv/bin/python db/14_reclassify_hpo_evidence.py
```

Migration 14 verifies the published SHA-256 for HPO release 2026-06-23,
materializes the active descendants of `HP:0000118` as a positive allowlist,
and excludes explicit zero-frequency annotations. Relative Success views read
the fact table dynamically and are not recreated by this migration. Pass
`--ontology /path/to/hp.obo` to use an already downloaded copy; the digest is
still verified.

Migration 17 adds versioned study-level evidence dates. Populate them from the
official GWAS Catalog study release (no publication text or LLM calls):

```bash
.venv/bin/dotenv run -- sh -c \
  'psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/17_gwas_study_dates.sql'
.venv/bin/dotenv run -- .venv/bin/python db/18_ingest_gwas_study_dates.py --dry-run
.venv/bin/dotenv run -- .venv/bin/python db/18_ingest_gwas_study_dates.py
```

The loader stores one date per GWAS Catalog study accession and the release
URL, version, and SHA-256. All association rows inherit the date through
`preclin.v_gwas_study_date_latest`.

Migration 19 enables transparent LZ4 compression for large LLM audit columns.
Apply it before importing cohort-wide Nelson results; it changes storage for
future values without rewriting historical rows:

```bash
.venv/bin/dotenv run -- sh -c \
  'psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/19_llm_audit_compression.sql'
```

Migration 20 additionally compresses cohort-scale exact user prompts with zlib
before network transfer. The original UTF-8 byte length and SHA-256 remain in
`llm_run`; `restore_user_prompt()` in `13_ingest_llm_outputs.py` reads either
the compressed representation or legacy plain text.

Migration 21 removes arbitrary target attribution from target-level outcomes.
It excludes explicit FDA-approval target mappings, then selects a target only
when source priority, confidence, and independent-source corroboration leave
one uniquely strongest candidate; exact strongest ties remain unresolved. It
also excludes placebo, pathogen, and genomic targets from the strict outcome
view:

```bash
.venv/bin/dotenv run -- sh -c \
  'psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/21_consensus_target_outcomes.sql'
```

Migration 22 removes synthetic HPO and Open Targets somatic zero rows created
by the historical `fill_gaps` backfill. Raw absence remains absent in
`evidence_score`; model assembly interprets it as zero recorded qualifying
evidence without claiming that the source reported a literal zero:

```bash
.venv/bin/dotenv run -- sh -c \
  'psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/22_remove_synthetic_genetic_zeros.sql'
```

Migration 23 collapses repeated imports of each versioned target-level IMPC
summary and adds a partial unique index that makes future IMPC imports
idempotent despite their `NULL subject_id2`:

```bash
.venv/bin/dotenv run -- sh -c \
  'psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/23_deduplicate_impc_evidence.sql'
```

Migration 24 imports the pinned DR24 audit for Phase 1+ targets absent from the
2025 IMPC summary. It removes the blanket-zero backfill, records an explicit
phenotyping/mapping status for every audited target, and assigns numeric zero
only to one-to-one mappings with no significant MP term and at least 13
successful homozygous procedures:

```bash
# Validate the pinned CSV and show the exact transition without database writes.
.venv/bin/dotenv run -- .venv/bin/python db/24_ingest_impc_dr24.py --dry-run

# Apply the audited transition.
.venv/bin/dotenv run -- .venv/bin/python db/24_ingest_impc_dr24.py
```

The immutable target-level audit is `data/impc_missing_update_dr24.csv`; the
generated before/after ledger is `data/impc_dr24_feature_changes.csv`.

Migration 25 adds normalized ChEMBL release provenance, exact human
single-protein target mappings, and molecule-level first-approval events. Its
rows were loaded by the approval event study's fetch script, which was removed
with that study; the current pipeline reads ChEMBL mechanisms through
`pipeline.chembl` instead.

These records are target–molecule history, not exact target–indication
regulatory outcomes, and therefore remain separate from `preclin.approval`.

Migration 26 adds the append-only `preclin.schema_migration` ledger used by
`db/migrate.py`. Existing installations are explicitly baselined once;
subsequent numbered migrations must be applied through the runner.

Migration 27 makes target-literature version selection explicit. It projects
one Line B--E fact per target and dimension, preferring `v2_proper` and falling
back to the latest v1 row only when v2 is absent. Both target- and program-wide
analytical views consume that projection instead of taking the maximum score
across every stored scorer version. Activating a future literature scorer
version requires a new migration.

## Cohort-wide genetics tiers

Cohort-wide Nelson tiers are frozen result files (`nelson_tiers_*.jsonl`,
kept in the git-ignored `data/target_evidence/`). Each row is a
`nelson_tier_result_v5` tier (T0-T3) for one non-placebo human
target-indication pair of the program and drug-target tables, judged without
outcomes or approvals from genetics-only Open Targets input and immutable
PubMed `source_document` rows, and carries the standard exact-audit fields.
The repository does not generate these files; `13_ingest_llm_outputs.py
--task nelson-tier` ingests them and does not create source documents. Each
row names its dossier by `dossier_source_document_id` and `dossier_sha256`,
and the ingest rejects the file unless that dossier already exists as a
`preclin.source_document` row with `source_name = 'nelson_dossier'`,
`external_id` equal to the row's `pair_key` (`target_id:indication_id`) and
`content_sha256` equal to `dossier_sha256`, linked exactly once in
`_source_documents` as a `dossier_snapshot`. Every other linked source
document must already exist too. The ingest atomically stores the `llm_run`,
`llm_run_source`, `evidence_score`, and immutable fact snapshot. The exact
prompt, response, and source excerpts live only in their dedicated audit
columns/tables; `parsed_output` omits those redundant envelope fields.
`03_views.sql` exposes only the newest cohort-wide `nelson_llm` row; the
approval-derived (`fda_approval`) and hand-curated (`manual_curation`) tiers
that `02_ingest.py` loads remain in the long table for audit but cannot
populate the canonical view.

For an incremental ingest, validate first and then commit only these rows:

```bash
.venv/bin/dotenv run -- .venv/bin/python db/13_ingest_llm_outputs.py \
  --task nelson-tier --preflight data/target_evidence/nelson_tiers_all_v7.jsonl
.venv/bin/dotenv run -- sh -c \
  'psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/19_llm_audit_compression.sql'
.venv/bin/dotenv run -- sh -c \
  'psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/20_llm_prompt_transfer_compression.sql'
.venv/bin/dotenv run -- .venv/bin/python db/13_ingest_llm_outputs.py \
  --direct-db --task nelson-tier data/target_evidence/nelson_tiers_all_v7.jsonl
.venv/bin/dotenv run -- sh -c \
  'psql "$DATABASE_URL" -f db/16_nelson_tier_view.sql'
```

The Nelson `--preflight` path validates every JSON audit field locally, copies
only compact identifiers and hashes into temporary PostgreSQL tables, and uses
set-based joins to verify targets, indications, dossier snapshots, source
documents, and any pre-existing run IDs or source links. It rolls back the
temporary staging transaction and does not execute persistent inserts. The
generic `--dry-run` executes the real task-specific write path and rolls it
back; Nelson uses the same streaming COPY path as a committed import.
`--direct-db` derives the matching direct Neon endpoint without logging the URL;
use it for the bulk COPY to avoid pooler buffering.

Migration 16 uses `CREATE OR REPLACE VIEW`, preserving all dependent views. It
must be used for an established database instead of rerunning the bootstrap
`03_views.sql`, whose `DROP VIEW ... CASCADE` is intended only for a full setup.

## Tables written by the current pipeline

`make all` (see the root Makefile and README) builds the report from
`pipeline.*` modules, each owning its tables: ClinicalTrials.gov studies
(`preclin.ctgov_study*`), FDA approvals (`preclin.fda_*`), molecular entities
(`preclin.moiety`, `preclin.drug_moiety`, `preclin.unii_*`), ontologies
(`preclin.ontology_*`), development programs (`preclin.dev_program*`,
`preclin.program_indication`, `preclin.trial_purpose`), labels
(`preclin.dev_program_approval`, `preclin.trial_outcome`, `preclin.trial_endpoint`,
`preclin.moiety_target`, `preclin.gene_disease_mechanism`,
`preclin.mouse_model_relation`), Open Targets evidence (`preclin.ot_*`,
`preclin.evidence_known_year`, `preclin.clinvar_accession_calibration`), and
reference genes (`preclin.hgnc_gene`, `preclin.depmap_common_essential`,
`preclin.chembl_*`). Every LLM decision is stored in
`pv_evidence.llm_decision`. Each table's columns are described by the `COMMENT ON` statements in the migration that creates it
(`\d+ preclin.<table>` in psql shows them).

## Legacy tables and views

The tables below come from the bootstrap scripts (`01`–`13`) and the earlier
benchmark. The report does not read them, except `public.targets`,
`public.gene_constraint` and `public.publications`, which the pipeline still
uses, and `preclin.classification`, which `report.quality` compares against.
They stay in the database as the record of the audited draft (AUDIT.md).

| Table | Purpose |
|---|---|
| `preclin.drug`, `preclin.drug_target`, `preclin.indication` | Drug, target-link and indication tables of the earlier benchmark |
| `preclin.program`, `preclin.program_trial`, `preclin.program_outcome` | (drug × indication × sponsor) programs and outcomes, replaced by `preclin.dev_program` |
| `preclin.approval` | 544 FDA approvals with Nelson tier, replaced by `preclin.dev_program_approval` |
| `preclin.evidence_score`, `preclin.evidence_dimension` | Long-form evidence facts, including the literature scores invalidated in AUDIT C29 and D66 |
| `preclin.classification`, `preclin.llm_run*`, `preclin.source_document*` | Earlier LLM outputs and their audit records |
| `preclin.chembl_target_*` | ChEMBL first-approval history (migration 25) |
| `preclin.schema_migration` | Append-only numbered-migration checksums (current) |

Their views (`v_program_evidence_wide`, `v_target_indication_*`,
`v_relative_success_clean` and the others in `03`, `05`, `07`–`09`) serve
only those tables.

## Ingest and audit clinical-trial sources

Apply the source/audit migration, then start with only trials that already have
LLM verdicts:

```bash
.venv/bin/dotenv run -- sh -c 'psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/10_clinical_trial_source_audit.sql'

# NCBI asks E-utilities clients to identify themselves with an email.
# Put NCBI_EMAIL (and optionally NCBI_API_KEY) in .env.
.venv/bin/dotenv run -- .venv/bin/python db/11_ingest_trial_sources.py \
  --scope classified --limit 100
```

Add `--search-pubmed-by-nct` to supplement ClinicalTrials.gov references with
an exact NCT-ID PubMed search. This requires `NCBI_EMAIL` and records the
relationship as `nct_indexed_publication`; it does not use fuzzy title matching.
Use `--nct-id-file path/to/nct_ids.txt` to refresh an explicit frozen cohort.
Exact-ID discovery does not make a source result-bearing; inspect the source
and trial relationship before using it for classification.

The default 30-day freshness window makes the command resumable. Identical
payloads deduplicate by SHA-256 and advance `last_seen_at`; changed upstream
records create a new immutable version. After validating the first batch, use
`--limit 0` for the whole scope.
ClinicalTrials.gov fetches use four workers by default, with request starts
globally capped at five per second and transient HTTP errors retried with
backoff; use `--workers 1` for a fully sequential run.
`--scope program` covers all trials linked to benchmark programs. Avoid
`--scope all` unless a complete ClinicalTrials.gov mirror is intentional.

No LLM is called by this ingest. PubMed abstracts are stored with an explicit
rights notice because some abstract text may be third-party copyrighted.

Curated non-CT.gov evidence is ingested separately and atomically. Omission of
`--commit` runs the full transaction and rolls it back:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  db/ingest_trial_external_sources.py data/clinical_trials/curated_sources.jsonl

.venv/bin/dotenv run -- .venv/bin/python \
  db/ingest_trial_external_sources.py --commit \
  data/clinical_trials/curated_sources.jsonl
```

The importer requires an existing canonical registry source, explicit
trial/source identity, provenance-inclusive immutable hashing, source-text
kind, controlled support types, and three independent support flags. Probable
multi-field matches remain explicitly labeled. Program evidence carries its
target-indication, protocol-family, or asset-global scope. Parent-, sibling-,
and program-level evidence is rejected if it is incorrectly marked as the
target trial's scientific result.

The source tables are the canonical abstract store going forward; a separate
local abstract cache is not required. Classifiers still write resumable JSONL
so paid calls survive interruption. Load those completed runs with the narrow
incremental importer rather than rerunning the big-bang `02_ingest.py`:

```bash
# Evidence-enriched, multi-axis stoppage rescores (kept as a separate task)
.venv/bin/dotenv run -- .venv/bin/python db/13_ingest_llm_outputs.py \
  --task trial-stoppage-rescore data/clinical_trials/stoppage_rescore_2026.jsonl
```

The importer also accepts `--task why-stopped`, `--task target-literature`,
`--task silent-kill`, `--task drug-evidence`, and `--task nelson-tier` result
files.
It requires the exact audit fields emitted by `analyses/classifiers/common.py`,
commits all supplied files atomically, and supports `--dry-run`. It never calls
an LLM or retrieves a source. `02_ingest.py` remains unchanged as the manual
bootstrap loader for the historical local data bundle.

Backfill abstracts used for target/drug evidence extraction separately:

```bash
# Refetch every PMID that historical evidence rows retained (start with 100).
.venv/bin/dotenv run -- .venv/bin/python db/12_ingest_evidence_abstracts.py \
  --from-citations --limit 100

# Prefer this when the original per-target cache still exists: it includes
# abstracts supplied to the model that were not selected as notable citations.
.venv/bin/dotenv run -- .venv/bin/python db/12_ingest_evidence_abstracts.py \
  --cache-dir /path/to/per-target-jsonl --subject-type target
```

All full abstracts go in `preclin.source_document.abstract_text`; raw PubMed XML
or cache payloads remain in `raw_content_text` / `raw_content`. The exact
possibly-truncated string sent to a model goes in
`preclin.llm_run_source.excerpt_text`. This distinction lets an auditor compare
the complete source with precisely what the model saw. Each evidence link also
stores `fact_snapshot`, so rerunning the same prompt version may update the
current `evidence_score` projection without rewriting what an older run
produced.

Migration 10 groups existing PubMed-derived facts into synthetic legacy runs,
but marks them `exact_input_unavailable`. `--from-citations` can recover and
link the PMIDs retained by old target-level outputs as `reported_citation`;
those links are useful provenance, not a claim that the full abstract was
definitely present in the discarded prompt. For complete historical recovery,
import the original abstract caches. Drug-specific facts retained no PMIDs, so
their old source set requires the original cache or a rerun.

Audit a verdict with:

```sql
SELECT subject_key, category, confidence, has_exact_input,
       system_prompt, user_prompt, raw_response,
       exact_input_sources, available_trial_sources
FROM preclin.v_classification_audit
WHERE classifier_task = 'why_stopped' AND subject_key = 'NCT01234567';
```

Rows created before this migration have `has_exact_input = false`: the parsed
legacy JSON is preserved, but the old prompt cannot be reconstructed honestly.
For source-level inspection, `preclin.v_trial_source_latest.why_stopped_text`
is the verbatim registry field and `.abstract_text` is the PubMed abstract;
`raw_content` / `raw_content_text` retain the complete JSON/XML payloads.

## Reset

```sql
DROP SCHEMA preclin CASCADE;
CREATE SCHEMA preclin;
-- then re-run 01_schema.sql onwards
```
