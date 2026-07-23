# State of the analysis

*Last updated: 2026-07-23*

**What this project is:** an audit + benchmark platform for how preclinical evidence predicts clinical drug approval. Every industry Phase 1–3 trial 2015–2025, every FDA approval, every evidence dimension we could pull from public sources, joined in one Neon Postgres schema and queryable via SQL.

**Core question:** how much do different kinds of preclinical evidence lift the probability that a target–indication pair yields an approved drug?

---

## Repo access

**Location:** `/Users/melissadu/Documents/projects/capable/data/`

**Layout:**
```
data/
  db/                              ← canonical SQL layer (see below)
    01_schema.sql                    DDL for preclin.* tables
    02_ingest.py                     Big-bang JSONL/CSV → Neon
    03_views.sql                     Original analysis views
    04_effect_size_ci.py             Bootstrap CIs → effect_size_snapshot
    05_ingest_extra.py               Untapped genome-browser tables (tissue, pleiotropy, DGIdb, ...)
    06_ti_views.sql                  Pheiron T-I unit + Relative Success views
    07_ingest_more.py                Single-cell Tau + GO annotations
    08_analysis_views.sql            Clean views (placebos filtered, canonical sponsors)
    09_benchmark_schema.sql          Benchmark run + prediction tables
    10_benchmark_scorers.py          5 scoring functions + plugin registry
    11_benchmark_runner.py           Cohort loader + metrics + bootstrap CI + storage
    12_external_scorer_template.py   Wire external models (Path 1 + Path 2)
    RUNBOOK.md                       Operational runbook
    QUESTIONS.md                     25 example queries
    COVERAGE_STATE.md                Honest coverage assessment
    BENCHMARK.md                     Benchmark methodology + results
    DB_MIGRATION_SUMMARY.md          What moved from CSV to DB

  fda_approvals/                   ← FDA approvals + case studies + report
    approvals.csv                    544 FDA CDER + CBER approvals 2015-2025
    REPORT.md                        Analytical takeaways
    CASE_STUDIES.md                  6 preclinical-strong / clinical-fail drugs
    figures/                         Generated charts

  clinical_trials/                 ← CT.gov pulls + failure classification
    trials_industry_drug.csv         28,301 industry Phase 1-3 trials
    why_stopped_haiku.jsonl          5,510 Haiku failure classifications
    why_stopped_sonnet.jsonl         5,510 Sonnet failure classifications (verified)

  target_evidence/                 ← Target-level evidence extraction
    literature_scores.jsonl          1,095 targets × Line B/C/D/E lit scores
    drug_evidence.jsonl              841+ drug-specific PubMed extractions (growing)
    resolved_targets.jsonl           963 drug→target LLM resolutions
    verified_targets.jsonl           391 Sonnet-verified drug→target labels

  silent_kill_verified.jsonl       476 publication-verified Phase 3 silent kills
  unresolved_targets_sonnet.jsonl  1,652 Sonnet-resolved unmatched drugs

  ANSWERS.md                       Direct answers to 5 core research questions
  PRECLINICAL_EVIDENCE_SPEC.md     Full 45-dimension evidence taxonomy
  PATHWAY_WRONGNESS.md             "Even with strong evidence, 78% of Phase 3 fail"
  EFFECT_SIZES_FINAL.md            Tight + Broad cohort effect sizes
  DB_SCHEMA_DESIGN.md              Schema design rationale
  STATE_OF_ANALYSIS.md             This file
```

**Git status:** repo is local, not on GitHub. Uncommitted work-in-progress.

**Environment:** Python 3.14 (`/opt/homebrew/bin/python3`), `psycopg2-binary`. No Node.js needed for the analysis layer.

---

## Database access

**Type:** Neon serverless Postgres.

**Connection string:** ask a maintainer for the `DATABASE_URL`. Format:
```
postgresql://<user>:<password>@<host>/<db>?sslmode=require
```

Set as `DATABASE_URL` env var. See `.env.example` in the repo root.

**Provisioning your own:** if you don't have access to the shared Neon DB, you
can set up your own by running `db/01_schema.sql` against an empty Postgres.
The ingest scripts (`db/02_ingest.py`, `05_ingest_extra.py`, `07_ingest_more.py`)
will populate it. Note: some tables in the `public.*` schema
(targets, gene_essentiality, gnomAD constraint, etc.) come from the sibling
[genome-browser](https://github.com/dryingpaint/genome-browser) project's Neon
ingestion pipeline — those are needed as read-only prerequisites.

**Schemas:**
- `public.*` — genome-browser's canonical schema (67 tables). Read-only for us. Contains: targets, trials, therapies, sponsors, DepMap, gnomAD, ClinGen, Mendelian, GWAS, IMPC, tissue expression, single-cell expression, Open Targets, adverse events, GO, Reactome, etc.
- `preclin.*` — our analysis schema (12 tables + 10 views). Read + write. Contains: drug, drug_target, indication, program, program_outcome, approval, evidence_score (long-form facts), classification (LLM outputs), benchmark_run, benchmark_prediction.

**Connect:**
```bash
export DATABASE_URL='postgresql://...'
psql "$DATABASE_URL"
# Then explore:
\dt preclin.*                    -- list tables
\dv preclin.*                    -- list views
```

**Quick tour of the tables:**
| Table | Rows | What |
|---|---|---|
| `preclin.drug` | 52,694 | Canonical drug identity |
| `preclin.drug_target` | 36,686 | Drug→target multi-source junction |
| `preclin.indication` | 8,875 | Canonical indications |
| `preclin.program` | 76,974 | (drug × indication × sponsor) — analytical unit |
| `preclin.program_trial` | 88,999 | Program → CT.gov trial junction |
| `preclin.program_outcome` | 76,974 | Rollup: approved / efficacy_fail / silent_kill / etc. |
| `preclin.approval` | 544 | FDA approvals with Nelson tier |
| `preclin.evidence_score` | ~250,000 | LONG-form facts (subject × dimension × source) |
| `preclin.classification` | ~13,000 | LLM why_stopped + silent_kill_verify + target_resolution |
| `preclin.evidence_dimension` | 40 | Registry of every evidence dimension |
| `preclin.benchmark_run` | 5 | Benchmark leaderboard rows |
| `preclin.benchmark_prediction` | 13,055 | Per-(scorer × T-I) predictions |

**Key views** (queryable directly):
- `preclin.v_program_evidence_wide` — flat master, one row per program with all evidence + outcome
- `preclin.v_target_indication_program` — Pheiron-style T-I unit
- `preclin.v_target_evidence_wide` — all evidence per target (wide-form)
- `preclin.v_relative_success_clean` — Pheiron RS metric per dimension (placebos filtered)
- `preclin.v_pathway_wrongness` — Phase 3 failure rate per evidence tier
- `preclin.v_combination_evidence` — pairwise RS(A ∧ B) lift (Fig-4 style)
- `preclin.v_benchmark_leaderboard` — scorer comparison
- `preclin.v_benchmark_calibration` — calibration curves per scorer
- `preclin.v_failure_taxonomy` — trial-level failure reason distribution
- `preclin.v_outcome_summary` — program-level outcome distribution
- `preclin.v_dimension_coverage` — coverage per dimension × subject

---

## Current state of the analysis

### Coverage (past 10 years of trials)

- ✅ **CT.gov industry Phase 1–3 drug/biological trials 2015–2025**: 100% captured (441,876 in `public.trials`, ~88K programs)
- ✅ **FDA CDER + CBER approvals 2015–2025**: 100% (544)
- ✅ **40 evidence dimensions across A–I taxonomy**: single-cell Tau, GO, Reactome, ClinGen, Mendelian, GWAS, DepMap, gnomAD, IMPC, HPO, PPI, DGIdb, Open Targets composites, target-level and drug-specific literature scores
- ⚠️ **Non-CT.gov trials (EU-CTR, ChiCTR)**: 0% — not yet ingested. Genuine gap.
- ⚠️ **Trials without why_stopped text**: unclassified (~5K of ~10K terminations)
- ⚠️ **Drug-specific evidence extraction**: 55% (841 of 1,541 target drugs; pipeline running)
- ⚠️ **Sonnet unmatched-drug target resolution**: still running, 1,652 done
- ❌ **Preclinical / IND kills**: structurally invisible in public sources

### Analysis findings (headline numbers)

**Pheiron-style Relative Success (RS) per evidence dimension** (Phase 2+ T-I pairs):

| Dimension | RS |
|---|---|
| Reactome pathways ≥5 | **2.90** |
| Line E lit (human PD engagement) high | **2.20** |
| ClinGen Strong/Definitive | **1.75** |
| Line C lit (cell) high | 1.67 |
| Mendelian ≥5 | 1.49 |
| OT genetic ≥0.3 | 1.36 |
| OT animal model ≥0.3 | 1.28 |
| Tissue-specific (single-cell Tau ≥0.75) | 0.67 |
| **DepMap pan-essential** | **0.13** (strong negative) |

**Pathway-wrongness (Phase 3+ with strong evidence):**
- Even at strong evidence tier: **~50% still fail for efficacy**
- Line C high: 79% any-fail; Line E high: 73%; Mendelian ≥5: 75%
- DepMap pan-essential: 97% any-fail
- **Best combination (Mendelian + human PD): 43% approval** (still 57% fail)

**Benchmark leaderboard** (5 scoring functions, cohort n=2,611):

| Scorer | AUC (95% CI) | Recall@10% | Prec@10% | RS(top 10%) | Best for |
|---|---|---|---|---|---|
| **rs_composite_v1** | **0.714 [0.694, 0.738]** | 0.19 | 0.55 | 2.17 | Overall discrimination |
| genetic_only_v1 | 0.629 [0.608, 0.659] | 0.27 | 0.75 | 3.24 | Calibration |
| family_precedent_v1 | 0.606 [0.590, 0.628] | 0.11 | 0.31 | 1.12 | Simple heuristic |
| nelson_only_v1 | 0.532 [0.518, 0.548] | 0.35 | **1.00** | 4.90 | High-precision flagging |
| random_v1 | 0.509 [0.485, 0.539] | 0.10 | 0.29 | 1.01 | Sanity check |

**Key methodological claim we can now defend:**
> Our full-schema scorer adds ~9pp of AUC over human-genetics-alone (rs_composite 0.714 vs genetic_only 0.629, non-overlapping CIs). Adding evidence beyond genetics is worth it.

---

## How to run the analyses

**From scratch (fresh Neon → fully loaded):**
```bash
cd data/db
export DATABASE_URL='postgresql://...'
psql "$DATABASE_URL" -f 01_schema.sql
python3 02_ingest.py                          # ~10 min
python3 05_ingest_extra.py                    # ~2 min
python3 07_ingest_more.py                     # ~3 min
psql "$DATABASE_URL" -f 03_views.sql
psql "$DATABASE_URL" -f 06_ti_views.sql
psql "$DATABASE_URL" -f 08_analysis_views.sql
psql "$DATABASE_URL" -f 09_benchmark_schema.sql
python3 04_effect_size_ci.py                  # bootstrap CIs
python3 11_benchmark_runner.py                # all 5 baseline scorers
```

**Add a new evidence dimension:**
```sql
INSERT INTO preclin.evidence_dimension (dimension, category, subject_type, data_type, description)
VALUES ('my_new_dim', 'C_cell', 'target', 'numeric_float', 'What this measures');

INSERT INTO preclin.evidence_score
  (subject_type, subject_id, dimension, category, value_numeric, source, source_version, extracted_by)
SELECT 'target', target_id, 'my_new_dim', 'C_cell', <value>, 'my_source', '2026-07', 'script:mine'
FROM ...;
```
Then re-run `06_ti_views.sql` and `08_analysis_views.sql` (they're `DROP + CREATE`).

**Evaluate an external scoring model:**
- **Path 1 (in-process)**: implement the Python interface in `12_external_scorer_template.py`, `register_scorer(...)`, run `python3 11_benchmark_runner.py <name>`
- **Path 2 (external CSV)**: produce `(target_id, indication_id, predicted_p_approval)` CSV, call `wire_external_scores(name, path)` from `12_external_scorer_template.py`

Either way, results appear in `preclin.v_benchmark_leaderboard`.

**Query the leaderboard:**
```sql
SELECT * FROM preclin.v_benchmark_leaderboard;
SELECT * FROM preclin.v_relative_success_clean ORDER BY relative_success DESC NULLS LAST;
SELECT * FROM preclin.v_pathway_wrongness;
```

25 more query patterns in `data/db/QUESTIONS.md`.

---

## Background pipelines still running

| Pipeline | Progress | Cost so far | Time remaining |
|---|---|---|---|
| `extract_drug_evidence.py` | 841 / 1,541 drugs | ~$8 | ~15–20 hours |
| `resolve_unresolved.py` | 1,652 drugs | ~$15 | ~2 hours |
| `verify_silent_kills.py` | 476 / 476 (done) | ~$25 | Complete |
| `audit_targets.py` (Sonnet drug→target verify) | ~380 / 621 | ~$16 | ~4 hours |
| `audit_failures.py` (Sonnet why_stopped) | 5,510 / 5,510 (done) | ~$14 | Complete |

Re-run `02_ingest.py` any time to pick up new rows (idempotent).

---

## Next high-value work (in priority order)

1. **Sponsor-canonical name mapping** — 30 min. `preclin.v_program_clean.sponsor_canonical` exists; propagate through all downstream.
2. **Platt-scale rs_composite_v1** — 1 hr. Fixes ECE 0.36. Bumps calibration to genetic_only quality.
3. **Time-machine backtest** — 2–3 days. Retrofit `evidence_as_of` dates. Unlocks real predictive-validity claim.
4. **Per-TA leaderboards** — 4 hr. Signal quality varies (oncology vs neuro).
5. **EU-CTR ingest** — 6–8 hr. Non-CT.gov trial coverage.
6. **PPI community detection (MCODE)** — 1 hr. Adds a new evidence dimension.
7. **ML-trained scorer (GBM)** — 4 hr. Baseline for whether hand-weights are near-optimal.
8. **Full-text PubMed / BioRxiv** — 4 hr + long-tail extraction.

---

## Reference documents

Ordered by importance for someone new coming in:

1. **`STATE_OF_ANALYSIS.md`** (this file) — start here
2. **`db/RUNBOOK.md`** — how to operate the DB
3. **`db/QUESTIONS.md`** — 25 example queries answering common questions
4. **`db/BENCHMARK.md`** — benchmark methodology + leaderboard
5. **`db/COVERAGE_STATE.md`** — what we have vs what's missing
6. **`ANSWERS.md`** — direct answers to the 5 core research questions
7. **`PRECLINICAL_EVIDENCE_SPEC.md`** — the evidence taxonomy
8. **`db/DB_MIGRATION_SUMMARY.md`** — CSV→DB migration overview
9. **`DB_SCHEMA_DESIGN.md`** — schema design rationale (why long-form, why T-I, etc.)
10. **`PATHWAY_WRONGNESS.md`** — the "even strong evidence fails 50% at Phase 3" analysis
