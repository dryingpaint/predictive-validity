# `preclin.*` Schema Design — Preclinical Evidence Analysis Layer

**Goal:** move the drug-outcome + preclinical-evidence analysis into Neon Postgres so that every data point has a **single source of truth**, every analysis is a straightforward SQL query, and the schema stays **as simple as possible while covering all necessary data**.

---

## Design principles (in priority order)

1. **Single source of truth per fact.** Each atomic claim (a score, a classification, an outcome) lives in exactly one row. Everything else is a view.
2. **Reuse `public.*` where authoritative.** `public.targets`, `public.trials`, `public.sponsors` cover our needs and are already ingested. Don't duplicate.
3. **Extend `public.*` where incomplete.** `public.approvals` (166 rows) and `public.diseases` (167 rows) are too sparse — we ingest our own approvals + indications.
4. **Long-form facts, wide-form views.** Extending evidence dimensions later means adding a row, not a column. Analyses read materialized views.
5. **Version every LLM output.** `source_model + source_version + extracted_at` on every LLM-produced row. Multiple extractions coexist; views pick the latest by default.
6. **No hidden joins.** Every FK explicit, every view definition < 50 lines. Anyone reading the schema can trace where a number came from.

---

## Entity model

```
        public.targets ────────────┐         public.sponsors
             │  (existing, 41K)    │              │  (existing, 42K)
             │                     │              │
             ▼                     │              ▼
     preclin.evidence_target ──────┼──────  preclin.drug
             │  (facts)            │              │  (extends public.therapies + trial-only drugs)
             ▼                     │              │
     preclin.evidence_target_indication          ▼
                                                 preclin.program
                                                        │  (drug × indication × sponsor — our analytical unit)
                                                        │
                     ┌──────────────────┬────────────────┼──────────────┐
                     ▼                  ▼                ▼              ▼
              preclin.program_    preclin.evidence_   preclin.       preclin.
              trial (junction)    drug (facts)        program_       classification
                     │                                outcome        (LLM outputs)
                     ▼
              public.trials  (existing, 441K)

              preclin.indication ─── links to public.diseases when a match exists
```

**Six new tables. Three reference existing `public.*` tables. Everything else is views.**

---

## Table specs

### Reference tables (existing `public.*` — read-only, use FKs to)
- `public.targets` — gene identity (`target_id`)
- `public.trials` — CT.gov trials (`nct_id`)
- `public.sponsors` — sponsor identity (`sponsor_id`)
- `public.gene_essentiality_summary`, `public.gene_constraint`, `public.clingen_validity`, `public.mendelian_associations`, `public.gwas_associations`, `public.target_evidence`, `public.adverse_events` — read for enrichment; no writes

### New: `preclin.drug`
Canonical drug identity. Superset of `public.therapies`.

```sql
CREATE TABLE preclin.drug (
  drug_id            SERIAL PRIMARY KEY,
  normalized_name    TEXT NOT NULL UNIQUE,          -- e.g., 'pembrolizumab'
  display_name       TEXT NOT NULL,                 -- e.g., 'Pembrolizumab'
  therapy_id         INTEGER REFERENCES public.therapies(id),  -- null if trial-only
  chembl_id          TEXT,
  drugbank_id        TEXT,
  modality           TEXT,                          -- small_molecule, mab, adc, car_t, etc.
  is_placebo         BOOLEAN DEFAULT FALSE,
  is_combination     BOOLEAN DEFAULT FALSE,
  resolved_via       TEXT,  -- 'public_therapy' | 'chembl_bulk' | 'llm_haiku' | 'llm_sonnet_verified' | 'unresolved'
  resolved_at        TIMESTAMPTZ,
  created_at         TIMESTAMPTZ DEFAULT now()
);
```

**Rationale:** one drug_id per canonical drug. `resolved_via` records provenance of the target-mapping (needed for selection-bias analysis).

### New: `preclin.drug_target`
Junction. A drug can have multiple targets (combinations, secondary targets).

```sql
CREATE TABLE preclin.drug_target (
  drug_id       INTEGER NOT NULL REFERENCES preclin.drug(drug_id),
  target_id     INTEGER NOT NULL REFERENCES public.targets(id),
  role          TEXT NOT NULL,   -- 'primary' | 'secondary' | 'off_target' | 'component_of_combo'
  mechanism     TEXT,            -- 'agonist' | 'antagonist' | 'inhibitor' | 'degrader' | 'other'
  source        TEXT NOT NULL,   -- 'chembl' | 'llm_sonnet' | 'therapy_targets' | 'llm_haiku'
  confidence    TEXT,            -- 'high' | 'medium' | 'low'
  citation_pmid TEXT,
  extracted_at  TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (drug_id, target_id, role, source)
);
```

**Rationale:** multi-target support without WIDE nullable columns. Multiple sources of the same (drug, target) can coexist; latest-confidence rules in views.

### New: `preclin.indication`
Canonical indications. Superset of `public.diseases` (which is too small).

```sql
CREATE TABLE preclin.indication (
  indication_id      SERIAL PRIMARY KEY,
  normalized_name    TEXT NOT NULL UNIQUE,  -- lowercased, punctuation-stripped
  display_name       TEXT NOT NULL,
  disease_id         INTEGER REFERENCES public.diseases(id),  -- when curated match exists
  mondo_id           TEXT,     -- ontology anchor
  therapeutic_area   TEXT,     -- 'oncology' | 'neuro' | 'autoimmune' | ...
  ct_gov_conditions  TEXT[],   -- variant strings seen in CT.gov
  created_at         TIMESTAMPTZ DEFAULT now()
);
```

### New: `preclin.program`
**The core analytical unit.** One row per (drug × indication × sponsor) developed together.

```sql
CREATE TABLE preclin.program (
  program_id      SERIAL PRIMARY KEY,
  drug_id         INTEGER NOT NULL REFERENCES preclin.drug(drug_id),
  indication_id   INTEGER NOT NULL REFERENCES preclin.indication(indication_id),
  sponsor_id      INTEGER REFERENCES public.sponsors(id),
  first_trial_date DATE,
  last_trial_date  DATE,
  highest_phase    INTEGER,   -- 0-4
  n_trials         INTEGER,
  created_at       TIMESTAMPTZ DEFAULT now(),
  UNIQUE (drug_id, indication_id, sponsor_id)
);
```

**Rationale:** program is the level at which "approval," "efficacy failure," etc., have meaning. A drug developed in oncology + autoimmune is two programs.

### New: `preclin.program_trial`
Junction (program × trial).

```sql
CREATE TABLE preclin.program_trial (
  program_id  INTEGER NOT NULL REFERENCES preclin.program(program_id),
  nct_id      TEXT NOT NULL REFERENCES public.trials(nct_id),
  PRIMARY KEY (program_id, nct_id)
);
```

### New: `preclin.program_outcome`
Computed rollup — the "did this program succeed or fail" atom.

```sql
CREATE TABLE preclin.program_outcome (
  program_id       INTEGER PRIMARY KEY REFERENCES preclin.program(program_id),
  outcome          TEXT NOT NULL,  -- see enum below
  outcome_broad    TEXT NOT NULL,  -- coarsened: 'approved' | 'efficacy_fail' | 'safety_fail' | 'silent_kill' | 'in_dev' | 'planned'
  confidence       TEXT NOT NULL,  -- 'high' | 'medium' | 'low'
  approval_id      INTEGER REFERENCES preclin.approval(approval_id),
  failure_reasons  JSONB,  -- {"efficacy": 2, "safety": 0, "commercial": 1}
  computed_at      TIMESTAMPTZ DEFAULT now()
);
```

Outcome enum: `approved`, `efficacy_fail`, `safety_fail`, `commercial_fail`, `enrollment_fail`, `other_fail`, `phase_complete_no_approval`, `phase1_only`, `in_development`, `planned_termination`, `unknown`.

### New: `preclin.approval`
Our approvals table. Extends `public.approvals` (166 rows too sparse).

```sql
CREATE TABLE preclin.approval (
  approval_id      SERIAL PRIMARY KEY,
  drug_id          INTEGER NOT NULL REFERENCES preclin.drug(drug_id),
  indication_id    INTEGER REFERENCES preclin.indication(indication_id),
  agency           TEXT NOT NULL,   -- 'FDA_CDER' | 'FDA_CBER' | 'EMA' | ...
  approval_date    DATE,
  approval_year    INTEGER,
  nelson_tier      TEXT,            -- 'T0' | 'T1' | 'T2' | 'T3' | 'T4'
  first_in_class   BOOLEAN,
  orphan           BOOLEAN,
  breakthrough     BOOLEAN,
  accelerated      BOOLEAN,
  priority_review  BOOLEAN,
  source_url       TEXT,
  public_approval_id INTEGER REFERENCES public.approvals(id),  -- link when overlap
  created_at       TIMESTAMPTZ DEFAULT now()
);
```

### New: `preclin.evidence_score` (the fact table)
**One row per (subject × dimension × source × extraction).**

```sql
CREATE TABLE preclin.evidence_score (
  evidence_id     BIGSERIAL PRIMARY KEY,
  subject_type    TEXT NOT NULL,  -- 'target' | 'target_indication' | 'drug' | 'program'
  subject_id      INTEGER NOT NULL,
  dimension       TEXT NOT NULL,  -- e.g., 'line_c_lit' | 'line_e_lit' | 'nelson_tier' | 'depmap_pan_essential'
  category        TEXT NOT NULL,  -- 'A_genetics' | 'B_mechanistic' | 'C_cell' | 'D_animal' | 'E_pd' | 'H_safety' | 'I_landscape'
  value_numeric   DOUBLE PRECISION,
  value_text      TEXT,
  value_boolean   BOOLEAN,
  source          TEXT NOT NULL,  -- 'pubmed_haiku' | 'depmap' | 'gnomad' | 'clingen' | 'impc' | ...
  source_version  TEXT,           -- '2026-01' | 'v1.2'
  confidence      TEXT,           -- 'high' | 'medium' | 'low'
  citation_pmids  TEXT[],
  extracted_at    TIMESTAMPTZ DEFAULT now(),
  extracted_by    TEXT,           -- 'claude-haiku' | 'claude-sonnet' | 'manual'
  UNIQUE (subject_type, subject_id, dimension, source, source_version)
);
CREATE INDEX ON preclin.evidence_score (subject_type, subject_id);
CREATE INDEX ON preclin.evidence_score (dimension, source);
```

**Rationale:** the ONE table that holds every evidence claim. Adding a new evidence type = new dimension string, no schema change. Multiple sources per (subject, dimension) coexist; views resolve.

### New: `preclin.classification` (the classifier output table)
Failure reasons + silent-kill verifications + drug-target resolutions.

```sql
CREATE TABLE preclin.classification (
  classification_id  BIGSERIAL PRIMARY KEY,
  subject_type       TEXT NOT NULL,   -- 'trial' | 'program' | 'drug'
  subject_key        TEXT NOT NULL,   -- nct_id, program_id-as-text, drug_id-as-text
  classifier_task    TEXT NOT NULL,   -- 'why_stopped' | 'silent_kill_verify' | 'target_resolution'
  category           TEXT NOT NULL,   -- e.g., 'efficacy' | 'safety' | 'commercial_strategic'
  confidence         TEXT,
  rationale          TEXT,
  citation_pmids     TEXT[],
  classifier_model   TEXT NOT NULL,   -- 'claude-haiku' | 'claude-sonnet' | 'regex_v1'
  classifier_version TEXT,
  extracted_at       TIMESTAMPTZ DEFAULT now(),
  UNIQUE (subject_type, subject_key, classifier_task, classifier_model, classifier_version)
);
CREATE INDEX ON preclin.classification (subject_type, subject_key);
```

**Rationale:** allows Haiku + Sonnet classifications to coexist per NCT id; disagreements are queryable directly.

---

## Views (analysis surface)

### `preclin.v_drug_target` — latest resolved target per drug
Picks the highest-confidence resolution per drug.

### `preclin.v_program_evidence_wide` — the flat master
The `drug_evidence_master_v2_broad.csv` equivalent. Pivots evidence_score into wide columns for one row per program.

```sql
CREATE VIEW preclin.v_program_evidence_wide AS
SELECT p.program_id, d.normalized_name AS drug, i.display_name AS indication,
       t.symbol AS target_symbol, po.outcome, po.outcome_broad,
       MAX(CASE WHEN es.dimension = 'line_c_lit'  THEN es.value_numeric END) AS line_c_lit,
       MAX(CASE WHEN es.dimension = 'line_d_lit'  THEN es.value_numeric END) AS line_d_lit,
       MAX(CASE WHEN es.dimension = 'line_e_lit'  THEN es.value_numeric END) AS line_e_lit,
       -- ... etc for all 20 dims
       ...
FROM preclin.program p
JOIN preclin.drug d ON d.drug_id = p.drug_id
JOIN preclin.indication i ON i.indication_id = p.indication_id
JOIN preclin.program_outcome po ON po.program_id = p.program_id
LEFT JOIN preclin.v_drug_target dt ON dt.drug_id = p.drug_id
LEFT JOIN public.targets t ON t.id = dt.target_id
LEFT JOIN preclin.evidence_score es ON
    (es.subject_type = 'target' AND es.subject_id = t.id) OR
    (es.subject_type = 'drug' AND es.subject_id = p.drug_id)
GROUP BY p.program_id, d.normalized_name, i.display_name, t.symbol, po.outcome, po.outcome_broad;
```

### `preclin.v_pathway_wrongness`
The Phase 3 pathway-fail-rate analysis. One query, ~30 lines.

```sql
CREATE VIEW preclin.v_pathway_wrongness AS
WITH ph3 AS (
  SELECT * FROM preclin.v_program_evidence_wide WHERE highest_phase >= 3
)
SELECT
  'Line C (cell lit)' AS dimension,
  COUNT(*) FILTER (WHERE line_c_lit >= 2) AS high_ev_n,
  COUNT(*) FILTER (WHERE line_c_lit >= 2 AND outcome_broad = 'approved') AS high_approved,
  COUNT(*) FILTER (WHERE line_c_lit >= 2 AND outcome_broad IN ('efficacy_fail', 'presumptive_efficacy_fail_ph3')) AS high_eff_fail,
  ROUND(100.0 * COUNT(*) FILTER (WHERE line_c_lit >= 2 AND outcome_broad != 'approved') /
         NULLIF(COUNT(*) FILTER (WHERE line_c_lit >= 2), 0), 1) AS high_fail_pct
FROM ph3
UNION ALL
-- one row per evidence dimension
SELECT 'Line E (human PD lit)', ...;
```

### `preclin.v_effect_sizes_tight`, `preclin.v_effect_sizes_broad`
OR + CI per dimension (bootstrap CI computed offline; the view has n_high_approved / n_high_failed / etc. — CIs added by a nightly Python job to a separate table `preclin.effect_size_snapshot`).

### `preclin.v_failure_taxonomy`
Distribution of failure reasons across all classified trials.

---

## Migration map (JSONL → schema)

| Current artifact | Rows | Target table | Notes |
|---|---|---|---|
| `approvals.csv` | 544 | `preclin.approval` + `preclin.drug` + `preclin.indication` | Extend `public.approvals` (only 166 rows) |
| `drug_master_lookup.csv` | 24,887 | `preclin.drug` + `preclin.drug_target` | Source='chembl_bulk'; `resolved_via='chembl_bulk'` |
| `resolved_targets.jsonl` | 963 | `preclin.drug_target` | Source='llm_haiku', `resolved_via='llm_haiku'` |
| `verified_targets.jsonl` | 391 | `preclin.drug_target` | Source='llm_sonnet_verified' (overrides Haiku) |
| `unresolved_targets_sonnet.jsonl` | growing | `preclin.drug_target` | Source='llm_sonnet' |
| `literature_scores.jsonl` | 1,095 | `preclin.evidence_score` | subject_type='target', dimension=`line_{b,c,d,e}_lit` |
| `drug_evidence.jsonl` | 81 | `preclin.evidence_score` | subject_type='drug', dimension=`drug_*` (cell_efficacy, rodent_efficacy, etc.) |
| `nelson_tiers_batch_*.csv` | 395 | `preclin.evidence_score` | subject_type='target_indication', dimension='nelson_tier' |
| `gene_impc_summary.csv` | 8,429 | `preclin.evidence_score` | subject_type='target', dimension='impc_n_phenotypes' |
| `family_precedent.csv` | 537 | `preclin.evidence_score` | subject_type='target', dimension='family_approved_count' |
| `opentargets_associations.jsonl` | 1,052 | `preclin.evidence_score` | subject_type='target_indication', dimension='ot_association' |
| `why_stopped_haiku.jsonl` | 5,510 | `preclin.classification` | classifier_task='why_stopped', model='claude-haiku' |
| `why_stopped_sonnet.jsonl` | ~7,000 | `preclin.classification` | model='claude-sonnet' |
| `silent_kill_verified.jsonl` | growing | `preclin.classification` | classifier_task='silent_kill_verify' |
| `trials_industry_drug.csv` | 28,301 | (already in `public.trials`) — filter via view |

**Everything else** (`programs_with_lit_scores.csv`, `drug_evidence_master_v2*.csv`, `program_master.csv`) is a *derived* artifact — becomes a materialized view, not a stored table.

---

## Example: pathway-wrongness query today vs after

**Today (Python, 200 lines):**
```python
python3 pathway_wrongness.py
# reads drug_evidence_master_v2_broad.csv (7 MB)
# python pandas-like joins
# outputs PATHWAY_WRONGNESS.md
```

**After migration (SQL, 5 lines):**
```sql
SELECT * FROM preclin.v_pathway_wrongness ORDER BY dimension;
-- returns pathway-fail rate per evidence dimension in one query
-- reproducible: same query gives same answer forever
-- discoverable: someone browsing schema can find + rerun
```

---

## Design decisions I made and why

**Long-form `evidence_score` fact table** — a single wide `drug_evidence_full` table (67 columns and growing) makes ALTER TABLE painful and hides the provenance of each column. Long-form: adding a new dimension = one INSERT, no migration. Views handle the wide-form for analysis.

**Separate `preclin.approval` instead of extending `public.approvals`** — genome-browser's is 166 rows and appears agency-specific. Ours is broader (544 across CDER + CBER + planned to include EMA). Link with `public_approval_id` FK for the 166 that overlap.

**`preclin.indication` instead of using `public.diseases`** — public.diseases has 167 rows and is a curated shortlist for the dashboard. Our indications come from arbitrary CT.gov `conditions` strings (~5,000 unique). We can still link via `disease_id` FK when a curated match exists.

**Program = (drug × indication × sponsor)** — this is the level at which "approved" or "failed for efficacy" is a valid statement. A drug developed for two indications is two programs with independent outcomes.

**`resolved_via` on `drug`** — critical for selection-bias analysis. Someone can filter to "only look at drugs resolved via public.therapies" (ChEMBL-catalogued, systemic winner bias) vs "resolved via LLM" (fills in the failed-drug gap).

**Version every LLM output** — `source_version` + `extracted_at`. When we re-run Haiku next month with a better prompt, old rows stay, new rows overlay, view picks max(extracted_at). Never lose a decision.

**Full audit trail** — every fact has `extracted_by` (which agent/model), `citation_pmids` (source publications), `confidence`. If someone asks "why does this drug have Line C=3", the SQL shows the exact PMIDs and the extractor.

---

## Not doing (deliberately)

**No wide flat "master" table on disk.** The wide form is a materialized view rebuilt nightly. This kills the temptation to write straight to a wide table and skip provenance.

**No `preclin.trials` copy.** `public.trials` (441K rows) is authoritative. We just filter via a view.

**No hierarchical dimension enum.** Category ('A_genetics', 'C_cell', etc.) is a text column, not a foreign key to a dimension table. Simple > normalized-to-death.

**No incremental refresh of materialized views.** Nightly full rebuild. If we scale to millions of programs (won't happen), revisit.

**No time-series of evidence scores.** Every LLM output is a new row per `extracted_at`, but we don't track scoring history per dimension. The latest wins; older rows stay for audit.

**No PubMed abstracts stored.** They exist in `pubmed_abstracts.jsonl` locally. If we want them queryable, add later — for now, cite via PMID array, users fetch full text externally.

---

## Open questions before I implement

1. **Should `preclin.program` be by unique (drug, indication, sponsor) or (drug, indication) with sponsor as attribute?** I proposed 3-tuple. Rationale: same drug developed by 2 sponsors for same indication is 2 programs (they had independent outcomes). Alternative: 2-tuple (drug, indication) with primary_sponsor, list of co-sponsors. Simpler but loses info.

2. **How to handle drugs approved via ChEMBL max_phase=4 outside FDA?** Our current "approved anywhere ever" definition. Should this be a separate outcome tag (`approved_ex_us`)? Or one `approved` bucket?

3. **Does `preclin.evidence_score` become huge?** Estimate: 30k programs × 15 dimensions × 2-3 sources = ~1.2M rows. Well within Neon's capacity (compare `public.gwas_associations` at 1M). Postgres handles it fine.

4. **Do we want `preclin.raw_ingestion_proposal` matching your Iris pattern?** Your `MEMORY.md` mentions propose-then-promote 24h cadence. If yes, I add a proposal table + promotion trigger. Otherwise direct-write.

5. **Migration cutover strategy.** Two options:
   - **Big-bang**: write ingest script, drop schema, reload, cut over analyses to SQL. 4-6 hours, all-or-nothing.
   - **Dual-write**: keep JSONL as the write path, add nightly job that syncs to DB. Analyses can run either way during transition.
   
   I recommend big-bang given data volume is modest and this is one-off setup.

---

## Estimated size

- 7 new tables
- 4-5 materialized views (rebuilt nightly)
- ~1.5M rows total across all preclin tables (dominated by `evidence_score`)
- ~500 MB storage on Neon (well within any tier)

---

## Recommended next steps

1. **You review this design** — key questions in §"Open questions" above
2. **I write the DDL** — one SQL file, ~250 lines, creates all tables + indexes + FKs
3. **I write the ingest script** — one Python file, ~500 lines, loads every JSONL/CSV listed above
4. **I write the view definitions** — one SQL file, ~200 lines, creates the 4-5 analysis views
5. **I rewrite `pathway_wrongness.py` and `effect_sizes_final.py` as SQL queries** so we have proof this works
6. **I document in a runbook** — how to add a new evidence dimension, how to promote an experimental classifier, etc.

Total: ~6 hours end-to-end.

---

## Alternative I considered and rejected

**Just use JSONL + DuckDB.** DuckDB reads CSV/JSON natively, no schema needed. Would work today. Rejected because: (a) not shared with Iris / other apps, (b) not accessible from claude.ai/code or phone, (c) no single source of truth for evidence — each file remains authoritative for its slice.

**Push everything to `public.*` in genome-browser.** Rejected because: (a) affects dashboard schema, (b) genome-browser's tables are curated for target-search, not drug-outcome analysis. Our workload is different shape.
