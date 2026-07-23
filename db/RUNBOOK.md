# preclin.* runbook

The `preclin.*` schema in Neon is the single source of truth for all preclinical-evidence + drug-outcome analysis. This runbook covers the common operations.

## Connection

```bash
export DATABASE_URL='postgresql://.../neondb?sslmode=require&channel_binding=require'
```

`DATABASE_URL` is not in the repo. Get from Neon dashboard or from local `.env`.

## Directory layout

- `01_schema.sql` — DDL for all `preclin.*` tables. Idempotent (uses `IF NOT EXISTS`).
- `02_ingest.py` — big-bang ingest from every local JSONL/CSV. Idempotent (uses `ON CONFLICT DO UPDATE`). Logs each stage to `preclin.ingest_log`.
- `03_views.sql` — analysis views: `v_program_evidence_wide`, `v_pathway_wrongness`, `v_effect_sizes_2x2`, `v_failure_taxonomy`, `v_outcome_summary`, `v_drug_coverage`.
- `04_effect_size_ci.py` — computes bootstrap CIs for effect sizes, writes to `preclin.effect_size_snapshot`.
- `RUNBOOK.md` — this file.

## First-time setup

```bash
cd data/db
psql "$DATABASE_URL" -f 01_schema.sql
python3 02_ingest.py
psql "$DATABASE_URL" -f 03_views.sql
python3 04_effect_size_ci.py
```

Total ~10 min for a fresh ingest.

## Common queries

### Q1. Outcome distribution
```sql
SELECT * FROM preclin.v_outcome_summary;
```

### Q2. Pathway wrongness — Phase 3 fail rates by evidence dimension
```sql
SELECT * FROM preclin.v_pathway_wrongness
ORDER BY dimension, is_high_evidence DESC;
```

### Q3. Effect sizes with bootstrap CIs
```sql
SELECT dimension, odds_ratio, ci_lo, ci_hi, n_covered
FROM preclin.effect_size_snapshot
WHERE cohort = 'tight'
ORDER BY odds_ratio DESC;
```

### Q4. Failure reason distribution across trials
```sql
SELECT * FROM preclin.v_failure_taxonomy;
```

### Q5. Selection-bias check — approval rate by drug resolution provenance
```sql
SELECT resolved_via,
       COUNT(*) AS n,
       COUNT(*) FILTER (WHERE approved_us OR approved_ex_us) AS n_approved,
       ROUND(100.0 * COUNT(*) FILTER (WHERE approved_us OR approved_ex_us) / COUNT(*), 1) AS approval_pct
FROM preclin.v_drug_coverage
GROUP BY resolved_via
ORDER BY n DESC;
```

### Q6. For a specific drug, all evidence claims
```sql
SELECT dimension, category, value_numeric, value_text, source, source_version, extracted_at, extracted_by
FROM preclin.evidence_score es
JOIN preclin.drug d ON
  (es.subject_type = 'drug' AND es.subject_id = d.drug_id) OR
  (es.subject_type = 'target' AND es.subject_id IN (
     SELECT target_id FROM preclin.v_drug_target WHERE drug_id = d.drug_id))
WHERE d.normalized_name = 'pembrolizumab'
ORDER BY category, dimension;
```

## Adding a new evidence dimension

1. Insert to registry:
```sql
INSERT INTO preclin.evidence_dimension
  (dimension, category, subject_type, data_type, description, source_primary)
VALUES ('my_new_metric', 'C_cell', 'target', 'numeric_0_3',
        'New metric description', 'my_source');
```

2. Insert facts:
```sql
INSERT INTO preclin.evidence_score
  (subject_type, subject_id, dimension, category, value_numeric, source, source_version, extracted_by)
VALUES ('target', 12345, 'my_new_metric', 'C_cell', 2.5, 'my_source', '2026-07', 'script:my_script');
```

3. Add to `v_program_evidence_wide` if it should appear in the master view (edit `03_views.sql`, re-run).

4. Add to `v_effect_sizes_2x2` if it should get an effect size (edit `03_views.sql`).

## Adding a new failure-classifier output

```sql
INSERT INTO preclin.classification
  (subject_type, subject_key, classifier_task, category, confidence,
   rationale, classifier_model, classifier_version, raw_output)
VALUES
  ('trial', 'NCT01234567', 'why_stopped', 'efficacy', 'high',
   'Primary endpoint missed per NEJM 2024', 'claude-opus', 'v2', '{"raw":"..."}'::jsonb);
```

The next `v_failure_taxonomy` refresh will pick it up (view already resolves to latest Sonnet > Haiku).

## Adding a new classifier model

1. Just insert into `preclin.classification` with new `classifier_model` string.
2. If you want it to override existing preferences, edit the `ORDER BY CASE classifier_model` in `v_failure_taxonomy` and `program_outcome` rollup query (`02_ingest.py`).

## Rebuild after ingest

```bash
python3 02_ingest.py             # idempotent: adds new + updates existing
psql "$DATABASE_URL" -f 03_views.sql   # views are drop-and-recreate, always safe
python3 04_effect_size_ci.py     # recomputes CI snapshot
```

## Reset (nuclear)

```sql
DROP SCHEMA preclin CASCADE;
CREATE SCHEMA preclin;
-- then re-run 01_schema.sql + 02_ingest.py + 03_views.sql
```

## Data model quick reference

- **`preclin.drug`** — canonical drug identity. `normalized_name` unique. `resolved_via` tracks provenance.
- **`preclin.drug_target`** — junction, multi-source. Views take highest-priority source.
- **`preclin.indication`** — canonical indications. May link to `public.diseases` when curated.
- **`preclin.approval`** — one row per (drug, indication, agency, region). Region ∈ {US, EU, ...}.
- **`preclin.program`** — analytical unit: (drug × indication × sponsor). One row per developing program.
- **`preclin.program_trial`** — program × NCT junction. Trial rows in `public.trials`.
- **`preclin.program_outcome`** — computed rollup. `outcome` fine-grained, `outcome_broad` coarsened with presumptive silent-kill labels.
- **`preclin.evidence_score`** — LONG-form facts. Every dimension × subject × source is one row.
- **`preclin.classification`** — LONG-form LLM outputs. Every task × subject × model version is one row.
- **`preclin.evidence_dimension`** — registry of every dimension we track.
- **`preclin.ingest_log`** — provenance of every ingest run.
- **`preclin.effect_size_snapshot`** — bootstrap-CI OR values (rebuilt by `04_effect_size_ci.py`).

## Views

- **`preclin.v_drug_target`** — best target per (drug, role). Applies priority ordering.
- **`preclin.v_program_evidence_wide`** — flat master. Replaces `drug_evidence_master_v2_broad.csv`.
- **`preclin.v_pathway_wrongness`** — Phase 3 fail rate per evidence tier. Replaces `pathway_wrongness.py`.
- **`preclin.v_effect_sizes_2x2`** — 2x2 counts + point OR per dimension. Bootstrap CIs come from `04_effect_size_ci.py`.
- **`preclin.v_failure_taxonomy`** — trial-level failure reason distribution.
- **`preclin.v_outcome_summary`** — program-level outcome distribution.
- **`preclin.v_drug_coverage`** — per-drug: n_targets, n_trials, approved flag.

## Selection-bias caveats to remember

- `preclin.drug` includes drugs at very different resolution qualities (see `resolved_via`). When computing effect sizes, filter by `resolved_via` to test bias sensitivity.
- Effect-size analyses restrict to programs with a matched primary `target_id`. ChEMBL-catalogued drugs are enriched for approved (~19% approval vs 1.8% overall).
- Presumptive silent-kill labels (`presumptive_efficacy_fail_ph3`, `presumptive_fail_ph2`) are heuristic; verified subset in `preclin.classification` where `classifier_task = 'silent_kill_verify'`.

## Reproducing the audit numbers

The main analysis outputs are:
- `PATHWAY_WRONGNESS.md` → `SELECT * FROM preclin.v_pathway_wrongness`
- `EFFECT_SIZES_FINAL.md` → `SELECT * FROM preclin.effect_size_snapshot`
- `EFFECT_SIZES_V3.md` → same as above but filter cohort
- `ANSWERS.md` → mix of the above

If a number moves between runs, check `preclin.ingest_log` — the most recent ingest may have added new data.
