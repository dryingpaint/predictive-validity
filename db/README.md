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
| Unnumbered utilities and `analyses/` | Repeatable refresh or analysis programs | May evolve; outputs must carry their own source release/run provenance. |

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

## Canonical PV evidence ingestion pilot

Migration 28 creates the `pv_source`, `pv_core`, and `pv_evidence` schemas. The
canonical adapter inventories ClinicalTrials.gov studies with an `ACTUAL` Study
Completion Date in a requested range. The active replacement pilot uses 2015;
the old first-posted-2025 pilot remains historical. The cohort requires
`INTERVENTIONAL` study type and at
least one intervention typed `DRUG` or `BIOLOGICAL`. Registration,
first-posted, start, and primary-completion dates do not determine cohort
membership:

```bash
.venv/bin/dotenv run -- .venv/bin/python db/migrate.py apply

# Network and parsing validation only; the default is also a dry run.
.venv/bin/dotenv run -- .venv/bin/python -m pv.ingest.clinicaltrials_gov \
  --from-date 2015-01-01 --through-date 2015-12-31 --limit 10 --dry-run

# Persist the immutable source versions and normalized trial/intervention rows.
.venv/bin/dotenv run -- .venv/bin/python -m pv.ingest.clinicaltrials_gov \
  --from-date 2015-01-01 --through-date 2015-12-31 --limit 10 --commit
```

The discovery query always records the complete ID/date/type manifest before
applying the limit. Day-, month-, and year-precision completion dates remain
literal; explicit lower and upper bounds support deterministic ordering without
inventing a day. The initial pilot retains exact JSON response bytes in Neon and
their SHA-256 hashes. `pv_source.object_blob` is ready for GCS-backed
representations, but no bucket is guessed or created when GCS is not configured.

An explicitly selected eligible trial uses the same immutable adapter and is
useful for bounded sentinel tests:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.clinicaltrials_gov --nct-id NCT02934698 --commit

.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.exact_trial_normalizer \
  --nct-id NCT02934698 --intervention Ivacaftor \
  --condition 'Cystic Fibrosis' \
  --cohort-id pv_cftr_organoid_sentinel_v1 --commit
```

The exact normalizer is deliberately narrower than the LLM path: it succeeds
only for a unique literal registry intervention, unique ChEMBL parent, complete
structured mechanism enumeration, and unique native OLS condition identifier.
It does not infer combination components or reinterpret ambiguous wording.

An immediate repeat can assert that every payload was reused:

```bash
.venv/bin/dotenv run -- .venv/bin/python -m pv.ingest.clinicaltrials_gov \
  --from-date 2015-01-01 --through-date 2015-12-31 --limit 10 --commit \
  --expect-no-new-versions
```

Migration 41 and the cohort adapter materialize the source-grounded five-trial
review pilot without deleting the five excluded candidates:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.pilot_cohort_2015 --commit
```

The rerun records a new acquisition observation but does not duplicate unchanged
source versions, trials, arms, intervention mentions, or condition mentions.
Future LLM enrichment commands must implement `--compare-decisions-to latest`
and explicit run-ID comparison against the decision ledger created by migration
28. Migration 29 adds complete persisted comparisons, including decisions that
were removed in the new run. The same comparison can be inspected without
calling a model:

```bash
.venv/bin/dotenv run -- .venv/bin/python -m pv.audit.llm_decisions \
  --run RUN_UUID --compare-decisions-to latest
```

Migration 33 retains exact per-trial LLM input packets and provider audit
metadata. Run the LLM-first semantic pass over the immutable ten-trial pilot:

```bash
.venv/bin/dotenv run -- .venv/bin/python -m pv.ingest.trial_semantic_llm \
  --limit 10 --model gpt-5.6-terra --workers 4 --confirm-paid --commit

# A later run compares canonical decision-bearing fields without overwriting.
.venv/bin/dotenv run -- .venv/bin/python -m pv.ingest.trial_semantic_llm \
  --limit 10 --model gpt-5.6-terra --workers 4 \
  --compare-decisions-to latest --confirm-paid --commit
```

The model proposes intervention/exposure semantics, compositional indications,
and target or broader-mechanism candidates. These rows remain LLM decisions;
they are not promoted to canonical asset/target/phenotype assertions until
deterministic identifier lookup and relationship verification succeed.

Migration 34 adds promoted, source-backed trial relationships and normalized
trial-indication links. Extract explicit related sponsor protocols from the
archived trial records without guessing NCT mappings:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.trial_relationships --dry-run
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.trial_relationships --commit
```

The initial run stores `NCT06754553 reuses_data_from PHRC 2015-HUS 6398
(PIMPARK)` with two exact ClinicalTrials.gov passages. Resolve the sponsor
protocol through an archived ClinicalTrials.gov ID search and exact
`orgStudyIdInfo.id` match:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.related_trial_resolver --commit
```

For the pilot this resolves the supporting record to `NCT03947216` without
adding it to the ten-trial focal cohort.

Migrations 35--37 add deterministic LLM-proposal verification, typed target
kinds, preclinical document/experiment inventory tables, and explicit abstract
availability. Verify every exact ChEMBL parent by enumerating its complete
parent/form mechanism set, then normalize exact OLS indication concepts:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.semantic_verifier --commit
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.indication_normalizer --commit
```

Migrations 38--39 and 43 add the versioned `human_therapeutics_v2` development-scope
policy. It retains every selected raw trial while allowing literature expansion
only for assets with verified human therapeutic targets. Antibiotics and assets
with therapeutic-primary non-human targets are excluded, vaccines are routed to
a separate track, a verified drug asset can qualify a mixed drug/behavioral
study, and unknown target domains are held unresolved. Materialize
the idempotent scope decisions after semantic and structured verification:

```bash
.venv/bin/dotenv run -- .venv/bin/python db/migrate.py apply
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.development_scope --dry-run
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.development_scope --commit
```

Both literature adapters read the scope views created by migration 38; they do
not accept an excluded, vaccine, non-molecular, or unresolved subject merely
because its raw trial record exists. Migration 39 makes the materialized keys
policy-versioned and retains an append-only row for every distinct scope
decision hash.

Migrations 42 and 45 bridge the existing genetics/phenotype databases without
copying or deleting their raw rows. They expose target--phenotype evidence and
non-causal target context separately:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.legacy_evidence_bridge --dry-run
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.legacy_evidence_bridge --commit
```

The bridge refuses silent legacy-table drift, uses stable source-native keys,
and labels unknown releases `legacy_release_unknown`. Migration 44 adds the
durable literature queue. Plan is idempotent; workers lease one item at a time;
interrupted leases can be recovered without duplicating canonical papers:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.literature_orchestrator plan --commit
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.literature_orchestrator validate-resume --commit
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.literature_orchestrator run --max-jobs 24
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.literature_orchestrator audit
```

The model does not bound structured retrieval. For example, the azacitidine
projection contains all four current ChEMBL mechanism rows (DNMT1, DNMT3A,
DNA, and RNA) even though the LLM did not propose all four.

### Target-to-phenotype literature pilot

Migrations 30 and 31 add explicit asset-target, asset-mechanism,
target-phenotype, and mechanism-phenotype assertions; scholarly works; and
deduplicated literature candidates with run-specific query observations.

The first end-to-end molecular case resolves the registered salbutamol
interventions through PubChem, an FDA label, HGNC, and UniProt. It does not call
an LLM:

```bash
.venv/bin/dotenv run -- .venv/bin/python -m pv.ingest.pilot_asset_targets --dry-run
.venv/bin/dotenv run -- .venv/bin/python -m pv.ingest.pilot_asset_targets --commit
```

Then run the target-wide and indication-scoped Europe PMC searches. The default
stores every returned metadata record; a positive `--limit-per-query` is only a
debugging option. Search pages, complete manifests, provider ranks, and
canonical candidate observations are all retained:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.target_phenotype_literature \
  --target ADRB2 --phenotype asthma --dry-run

.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.target_phenotype_literature \
  --target ADRB2 --phenotype asthma --commit
```

A query hit is stored as an `unreviewed` document candidate, not as a biological
assertion. `pv_evidence.target_phenotype_assertion` remains empty until a source
span or structured database row actually supports the relationship. Repeated
searches reuse scholarly works and canonical candidates; only the acquisition
run and query-observation rows are new.

The superseded first-posted-2025 pilot also ran DNMT1--AML, DNMT3A--AML, and
HTR2A--impulse-control-disorder searches. Its counts remain useful as replay
fixtures, but the active checkpoint is the completion-date-selected 2015 pilot
documented in `data/pv/2015_pilot/PILOT_REVIEW.md`.

Migration 51 activates `pv_literature_v2`. It plans only asset + normalized
indication provider queries and effective-target-only provider queries. It does
not put assay or generic preclinical vocabulary into retrieval; target +
indication is a local title/abstract projection of the completed target corpus.
Plan idempotent work for a cohort:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.literature_orchestrator \
  --cohort-id pv_2015_actual_completed_drug_biological_pilot5_v1 \
  plan --commit
```

The pilot plan is 15 asset--indication items and 9 effective-target items.
Replanning inserts zero rows. To run a bounded number of complete work items:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.literature_orchestrator \
  --cohort-id pv_2015_actual_completed_drug_biological_pilot5_v1 \
  run --max-jobs 1
```

Each Europe PMC page is archived and committed before retrieval advances;
canonical projection commits in 200-record batches. A direct adapter `--limit`
is validation-only and marks the query `truncated`, which excludes it from the
active views. The prior `asset_preclinical_literature` and `asset_mention`
outputs remain immutable historical query-version data. This is raw candidate
acquisition, not result interpretation. The
`preclinical_experiment` tables are populated only by a later passage-backed
enrichment that preserves positive, negative, null, mixed, and unclear results.

Audit a proposed Europe PMC relevance top-N cutoff without changing Neon:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.audit.top100_asset_relevance \
  --asset rituximab --asset nicotine --top-n 100 --scan-n 1000
```

The 2026-09-18 five-asset audit rejected relevance top 100 as a standalone
retention policy for broad assets; important older mechanistic papers were
outside both the first 100 and, in several cases, the first 1,000. The audit
uses text rules only to surface review probes and never treats them as evidence
labels or ingestion filters.

Count the proposed asset--indication and target-only replacement queries for a
cohort without writing to Neon:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.audit.literature_search_policy_pilot \
  --cohort-id pv_2015_actual_completed_drug_biological_pilot5_v1 \
  --json-output data/pv/2015_pilot/LITERATURE_SEARCH_POLICY_HIT_COUNTS.json \
  --markdown-output data/pv/2015_pilot/LITERATURE_SEARCH_POLICY_HIT_COUNTS.md
```

This command performs count-only Europe PMC requests. It does not create
acquisition runs or scholarly-work rows. Target--indication is intentionally a
later local projection of the target-only corpus rather than another provider
query. Its query builder uses the source-aware alias projection: ChEMBL names
are typed, unsafe class labels are excluded, OLS exact synonyms are eligible,
and family/complex component membership is not treated as a set of asserted
target aliases.

Rebuild typed search aliases from the immutable raw ChEMBL and OLS records
without making new network requests. Both commands are dry-run by default and
idempotent under `--commit`:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.backfill_chembl_aliases --commit
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.backfill_ols_aliases --commit
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.backfill_chembl_mechanism_context --commit
```

After deterministic ChEMBL asset resolution and complete mechanism
enumeration, structure free-text target qualifiers in a separate, explicitly
approved LLM stage:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.chembl_mechanism_context_llm \
  --cohort-id pv_2015_actual_completed_drug_biological_pilot5_v1 \
  --model gpt-5.6-terra --workers 4 --confirm-paid --commit
```

The model sees only archived ChEMBL fields and supplied component candidates.
Mechanical validation requires exact source paths and quotes, forbids component
membership from becoming target evidence, and rejects identifiers not present
in the packet. Migration 49 stores exact-source contexts; migration 50 exposes
only the latest validated decision per asset through
`pv_evidence.v_latest_asset_target_context` while retaining all earlier runs.
Use `--compare-decisions-to latest` to persist field-level rerun differences.

Enrich records for which Europe PMC did not provide an abstract from archived
PubMed XML:

```bash
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.pubmed_abstracts --commit
```

Migration 32 adds canonical full-text representations. Fetch and validate the
open-access JATS candidates without writes, then commit them:

```bash
.venv/bin/dotenv run -- .venv/bin/python db/migrate.py apply
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.europe_pmc_fulltext --dry-run
.venv/bin/dotenv run -- .venv/bin/python \
  -m pv.ingest.europe_pmc_fulltext --commit
```

The full-text adapter continues past unavailable or unsupported-license items
and records each failure in the acquisition run. The review pilot currently has
seven rights-reviewed, checksummed JATS representations in Neon. With
`PV_GCS_BUCKET` set the adapter uploads licensed JATS and tries
provider-advertised free PDFs, storing immutable object coordinates and
generations. Without a configured bucket it retains permitted JATS in Neon but
never guesses a bucket or stores binary PDFs there.

Export the review checkpoint before enlarging the trial cohort:

```bash
.venv/bin/dotenv run -- .venv/bin/python -m pv.audit.pilot_readiness
```

The exact implemented-versus-planned status and unresolved review queue are maintained in
[`../docs/pv/PV_CANONICAL_EVIDENCE_LEDGER.md`](../docs/pv/PV_CANONICAL_EVIDENCE_LEDGER.md#21-implemented-pilot-status-as-of-2026-09-16).

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
single-protein target mappings, and molecule-level first-approval events. The
latest-release view retains mapped targets without qualifying approval events
as explicit `NULL` controls. Refreshing is deliberate and writes directly to
PostgreSQL; no analysis-side JSON cache is required:

```bash
.venv/bin/dotenv run -- sh -c \
  'psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f db/25_chembl_target_approval_history.sql'
.venv/bin/dotenv run -- .venv/bin/python \
  analyses/approval-evidence-effect/fetch_chembl_target_approval_history.py --dry-run
.venv/bin/dotenv run -- .venv/bin/python \
  analyses/approval-evidence-effect/fetch_chembl_target_approval_history.py
```

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

## Tables

| Table | Rows | Purpose |
|---|---|---|
| `preclin.drug` | 52,694 | Canonical drug identity |
| `preclin.drug_target` | 36,686 | Drug→target multi-source junction |
| `preclin.indication` | 8,875 | Canonical indications |
| `preclin.program` | 76,974 | (drug × indication × sponsor) — analytical unit |
| `preclin.program_trial` | 88,999 | Program → CT.gov trial junction |
| `preclin.program_outcome` | 76,974 | Rollup: approved / efficacy_fail / silent_kill / etc. |
| `preclin.approval` | 544 | FDA approvals with Nelson tier |
| `preclin.chembl_target_approval_release` | 1 | Versioned ChEMBL import provenance |
| `preclin.chembl_target_mapping` | 513 | ChEMBL human single-protein mappings for clinical targets |
| `preclin.chembl_target_approval_event` | 1,442 | Distinct direct approved molecule–target mechanisms |
| `preclin.schema_migration` | varies | Append-only numbered-migration checksums and application provenance |
| `preclin.evidence_score` | ~250,000 | LONG-form evidence facts |
| `preclin.classification` | ~13,000 | LLM outputs (why_stopped, silent-kill, target resolution) |
| `preclin.llm_run` | varies | Append-only exact prompt/response records behind classifications and evidence facts |
| `preclin.source_document` | varies | Immutable CT.gov, PubMed, and other source snapshots |
| `preclin.source_document_subject` | varies | Trial/target/drug→source provenance links |
| `preclin.llm_run_source` | varies | Exact source excerpts supplied to each model call |
| `preclin.llm_run_evidence_score` | varies | Model run→current fact link plus immutable run-produced value snapshot |
| `preclin.evidence_dimension` | 40 | Registry of every evidence dimension |

## Views

- `v_program_evidence_wide` — flat master, one row per program with all evidence + outcome
- `v_target_indication_program` — Pheiron-style T-I unit (loose outcome)
- `v_target_indication_strict_outcome` — strict per-T-I outcome (approved for THIS indication)
- `v_target_evidence_wide` — all evidence per target (wide-form)
- `v_target_family_precedent_by_year` — time-cutoff-aware family/gene precedent
- `v_relative_success_clean` — Pheiron RS metric per dimension (placebos filtered)
- `v_pathway_wrongness` — Phase 3 fail rate per evidence tier
- `v_combination_evidence` — pairwise RS(A ∧ B) lift
- `v_dimension_coverage` — coverage per dimension × subject
- `v_trial_source_latest` — latest full registry/publication text linked to each NCT id
- `v_classification_audit` — verdict + exact model input/output + exact/available source links
- `v_evidence_score_audit` — current fact, immutable run-produced value, extraction run, and exact abstract excerpts

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

## Add a new evidence dimension

```sql
INSERT INTO preclin.evidence_dimension (dimension, category, subject_type, data_type, description)
VALUES ('my_new_dim', 'C_cell', 'target', 'numeric_float', 'What this measures');

INSERT INTO preclin.evidence_score
  (subject_type, subject_id, dimension, category, value_numeric, source, source_version, extracted_by)
SELECT 'target', target_id, 'my_new_dim', 'C_cell', <value>, 'my_source', '2026-07', 'script:mine'
FROM ...;
```

Then rebuild views to include it in `v_target_evidence_wide` (edit `05_ti_views.sql`, re-run).

## Reset

```sql
DROP SCHEMA preclin CASCADE;
CREATE SCHEMA preclin;
-- then re-run 01_schema.sql onwards
```
