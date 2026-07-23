# Predictive Validity — a benchmark for preclinical evidence → clinical drug approval

**Core question:** how much does each kind of preclinical evidence lift the probability that a target–indication pair yields an approved drug?

**Cohort:** every industry-sponsored Phase 1–3 drug/biological trial from ClinicalTrials.gov 2015–2025, joined against 40+ evidence dimensions from public sources (genetics, tissue expression, cell essentiality, animal models, pathway biology, safety, landscape). All data lives in a Postgres schema; every analysis is a SQL query.

**Novel angles vs. published work in this area:**

- **Sponsor-euphemism-corrected failure classification** — Haiku + Sonnet re-labeled 5,510 clinical failures whose stated reasons systematically euphemize efficacy fails as "commercial/strategic."
- **Silent-kill audit** — 25,877 programs completed a Phase 2/3 without approval; publication cross-reference recovers their true failure reasons.
- **Pathway-wrongness** — even with strong Line C/D/E evidence, ~50% of Phase 3 attempts fail for efficacy. Answers "given positive evidence, how often is the pathway still wrong."
- **Pluggable benchmark** — any target-scoring model plugs in via Python callable or CSV; leaderboard compares AUC / Recall@k / RS / calibration.

## Quick start

```bash
git clone https://github.com/dryingpaint/predictive-validity.git
cd predictive-validity

# 1. Environment
cp .env.example .env
# Edit .env — add DATABASE_URL

# 2. Python deps
pip install psycopg2-binary scikit-learn numpy lightgbm

# 3. Explore
psql "$DATABASE_URL" -c "SELECT * FROM preclin.v_benchmark_leaderboard"
psql "$DATABASE_URL" -c "SELECT * FROM preclin.v_relative_success_clean ORDER BY relative_success DESC NULLS LAST"
```

## What's in the box

```
predictive-validity/
├── README.md                       ← you are here
├── .env.example                    ← credential template
├── db/                             ← canonical SQL layer
│   ├── 01_schema.sql                 DDL for preclin.* tables
│   ├── 02_ingest.py                  Big-bang JSONL/CSV → Postgres
│   ├── 03_views.sql                  Analysis views
│   ├── 04_effect_size_ci.py          Bootstrap CIs
│   ├── 05_ingest_extra.py            Untapped genome-browser tables
│   ├── 06_ti_views.sql               Target-indication unit + Relative Success
│   ├── 07_ingest_more.py             Single-cell Tau + GO annotations
│   ├── 08_analysis_views.sql         Clean views (placebos filtered)
│   ├── 09_benchmark_schema.sql       Benchmark run + prediction tables
│   ├── 10_benchmark_scorers.py       5 rule-based scorers
│   ├── 11_benchmark_runner.py        Cohort loader + metrics + storage
│   ├── 12_external_scorer_template.py Wire external models
│   ├── 13_ml_scorers.py              LogReg / RandomForest / LightGBM
│   ├── 14_calibrate_rs_composite.py  Platt scaling
│   ├── 15_llm_agent_scorer.py        Sonnet reads evidence, predicts
│   ├── BENCHMARK.md                  Benchmark methodology
│   ├── COVERAGE_STATE.md             What we have vs what's missing
│   ├── QUESTIONS.md                  25 example SQL queries
│   ├── RUNBOOK.md                    Operational runbook
│   └── data_approvals.csv            544 FDA approvals 2015-2025
└── docs/
    ├── STATE_OF_ANALYSIS.md          ← start here
    ├── ANSWERS.md                    Direct answers to 5 core questions
    ├── PRECLINICAL_EVIDENCE_SPEC.md  40-dim evidence taxonomy
    ├── PATHWAY_WRONGNESS.md          "78% Rule" analysis
    ├── REPORT_FDA_APPROVALS.md       FDA approvals landscape
    ├── CASE_STUDIES.md               6 preclinical-strong / clinical-fail cases
    ├── DB_SCHEMA_DESIGN.md           Schema design rationale
    └── EFFECT_SIZES_*.md             Bootstrap CI effect-size tables
```

## Where the data lives

**Postgres schema `preclin.*` in a hosted Neon instance.** Contains:

- 52,694 canonical drugs
- 76,974 programs (drug × indication × sponsor)
- 88,999 program → trial links (mapped to CT.gov)
- 250,000+ evidence facts (long-form: subject × dimension × source)
- 13,000+ LLM classifications (Haiku + Sonnet failure reasons, target resolutions, silent-kill verifications)
- 40 evidence dimensions across Categories A–I

Some tables live in the `public.*` schema (targets, gene_essentiality, gnomAD constraint, ClinGen, Mendelian, GWAS, IMPC, tissue expression, single-cell, Open Targets composites, adverse events, GO, Reactome). These come from the sibling [genome-browser](https://github.com/dryingpaint/genome-browser) project's Neon ingestion pipeline.

## Benchmark headline (see [LEADERBOARD.md](LEADERBOARD.md) for full detail)

**Task:** given a (target × indication) pair and public preclinical evidence, predict P(any drug on this T-I gets FDA-approved for THIS specific indication).

**Cohort:** 13,639 T-I pairs at Phase 1+, strict per-T-I outcome, base rate 2.95%.

**Top of leaderboard (5-fold CV OOF, STRICT outcome):**

| Scorer | AUC (95% CI) | RS(top 10%) | ECE |
|---|---|---|---|
| **stacked_ph1_strict_v1** | **0.838 [0.815, 0.861]** | **13.81** | 0.012 |
| logreg_ph1_strict_v1 | 0.837 [0.813, 0.859] | 13.95 | 0.257 |
| stacked_v1 (Ph2+) | 0.829 [0.806, 0.855] | 12.84 | 0.017 |
| logreg_strict_v1 (Ph2+) | 0.826 [0.801, 0.851] | 13.11 | **0.001** |
| lightgbm_robust_strict (Ph2+, regularized) | 0.733 | 6.76 | 0.29 |

**Time-machine (STRICT, LogReg, out-of-time):**

| Cutoff | Train n | Test n | AUC | RS(top 10%) |
|---|---|---|---|---|
| 2019-01-01 | 4,199 | 3,522 | 0.769 [0.651, 0.888] | 12.28 |
| 2017-01-01 | 2,311 | 5,410 | 0.770 [0.656, 0.876] | 14.00 |

LightGBM overfits on strict time-machine (drops to AUC 0.58) — LogReg is robust.

**Per-modality (STRICT):**

| Modality | n | AUC | RS(top 10%) |
|---|---|---|---|
| biologic (mAb/protein/peptide) | 762 | 0.832 | 9.86 |
| small_molecule | 961 | 0.824 | 6.56 |

**Ablation (STRICT outcome, LogReg full = 0.829):**

| Removed | AUC | ΔAUC |
|---|---|---|
| A. Genetics | 0.651 | **−0.177** (dominant) |
| Context (Nelson tier + TA) | 0.811 | −0.018 |
| C. Cell | 0.829 | **+0.000** (null) |
| D. Animal | 0.829 | **+0.000** (null) |

**Key finding: on strict outcome, human genetic evidence contributes ~18pp of AUC. Target-level cell + animal literature contribute exactly zero.**

Live leaderboard: `SELECT * FROM preclin.v_benchmark_leaderboard`.

## How to plug in your own model

**Option 1 — in-process Python scorer.** Implement the standard interface in `db/12_external_scorer_template.py`, register it, run `python3 11_benchmark_runner.py <your_scorer_name>`.

**Option 2 — external CSV.** Produce `(target_id, indication_id, predicted_p_approval)` CSV, wire in via `wire_external_scores()` in `12_external_scorer_template.py`.

Either way, results land in `preclin.v_benchmark_leaderboard` alongside our baselines.

## Honest caveats

- **Cohort has selection bias.** 2,611 Phase 2+ T-I pairs are enriched for approved drugs (28.4% base rate vs 1.8% across all 82,014 programs).
- **No time-machine backtest yet.** All scorers use current-day evidence (not "what was known in 2018"). Real predictive-validity requires retrofitting `evidence_as_of` dates.
- **Publication bias saturates target-level literature.** Line B/C/D/E scores are collinear at the top; DepMap essentiality gives cleaner negative signal.
- **Non-CT.gov trials (EU-CTR, ChiCTR, JP) not ingested.** ~20% coverage gap for global drug development.
- **Preclinical / IND kills are invisible.** Never enter CT.gov.

Full caveats: [`docs/STATE_OF_ANALYSIS.md`](docs/STATE_OF_ANALYSIS.md), [`db/COVERAGE_STATE.md`](db/COVERAGE_STATE.md).

## License

MIT — do what you want. If you build something interesting on top, please let us know.
