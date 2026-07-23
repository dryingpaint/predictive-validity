# Predictive Validity

**Benchmark for how well public preclinical evidence predicts clinical drug approval.**

Given a `(target × indication)` hypothesis and 40+ public evidence dimensions (human genetics, tissue expression, cell essentiality, animal models, safety, landscape), predict `P(any drug on this T-I gets FDA-approved for THIS indication)`. Comparable across models — trained ML, rule-based composites (Nelson/Pheiron RS), LLM agents.

## Headline result

Best model: **stacked ensemble (LogReg + regularized LightGBM + RandomForest)** on Phase 1+ target-matched T-I pairs, strict per-indication outcome, held-out-target GroupKFold.

| Metric | Value |
|---|---|
| **AUC** | **0.825 [0.797, 0.849]** |
| **RS(top 10%)** | **13.67** (top decile enriched 13.7× for approvals) |
| Cohort | n=13,639, base rate 2.95% |
| ECE | 0.013 (well-calibrated) |
| Recall @ top 10% | 0.60 |

Compare against:
- **Untrained Pheiron RS composite** (published methodology): AUC 0.615
- **Sonnet LLM agent** (reads evidence dossier, predicts): AUC 0.633
- **Random baseline**: AUC 0.500

**Trained ML extracts ~21pp more signal than published rule-based composites, ~19pp more than LLM.**

Full leaderboard across 8 scorers × 3 cohorts × 3 CV strategies: [`RESULTS.md`](RESULTS.md).

## Key finding

**Genetic evidence alone accounts for ~18pp of AUC.** Removing all A. Genetics features drops LogReg from 0.829 to 0.651. Removing target-level C (cell) or D (animal) literature drops AUC by exactly 0.0pp — target-level publication saturates due to publication bias.

See [`ANALYSIS.md`](ANALYSIS.md) for the full "pathway-wrongness" analysis (even strong evidence still fails 50-78% at Phase 3).

## Quick start

```bash
git clone git@github.com:dryingpaint/predictive-validity.git
cd predictive-validity
cp .env.example .env       # add DATABASE_URL

pip install psycopg2-binary scikit-learn numpy lightgbm anthropic

# Explore live leaderboard
psql "$DATABASE_URL" -c "SELECT * FROM preclin.v_benchmark_leaderboard"

# Run the honest final benchmark (~5 min)
python3 analyses/final_benchmark.py
```

## Repo structure

```
predictive-validity/
├── README.md            ← you are here
├── RESULTS.md           ← full leaderboard + interpretation
├── ROBUSTNESS.md        ← 12 attacks vs benchmark + how each survives
├── ANALYSIS.md          ← pathway wrongness, ablation, RS metric
├── SCHEMA.md            ← evidence taxonomy + database design
├── CASE_STUDIES.md      ← 6 preclinical-strong / clinical-fail drugs
├── CONTEXT_FDA.md       ← FDA approvals landscape 2015-2025
├── data/
│   ├── approvals.csv       544 FDA approvals
│   └── leaderboard.csv     Live snapshot of all benchmark runs
├── db/                  ← schema + ingest (SQL + Python)
│   ├── 01_schema.sql       preclin.* DDL
│   ├── 02_ingest.py        Big-bang JSONL/CSV → Postgres
│   ├── 03_views.sql
│   ├── 04_ingest_extra.py    Tissue, pleiotropy, pathways, DGIdb, HPO
│   ├── 05_ti_views.sql       Target-indication unit + RS metric
│   ├── 06_ingest_more.py     Single-cell Tau + GO annotations
│   ├── 07_analysis_views.sql
│   ├── 08_strict_outcome_view.sql   Per-T-I approval
│   ├── 09_time_cutoff_features.sql  Time-aware family precedent
│   ├── README.md              How to operate the DB
│   └── QUESTIONS.md           25 SQL example queries
├── benchmark/           ← benchmark framework
│   ├── schema.sql          benchmark_run + benchmark_prediction tables
│   ├── runner.py           Cohort loader, metrics, bootstrap CIs
│   ├── scorers_rule_based.py   5 baselines (random, family, nelson, genetic, rs_composite)
│   ├── scorers_ml.py       LogReg, LightGBM, RF + robust variants
│   ├── scorers_ensemble.py    Stacked LogReg meta-learner
│   ├── scorers_pheiron.py     Untrained Pheiron RS composite
│   ├── scorers_llm_agent.py   Sonnet reads evidence, predicts
│   ├── external_template.py   How to wire an external model
│   └── README.md              Benchmark methodology
└── analyses/            ← one-off analysis scripts
    ├── final_benchmark.py     Ph1+ strict held-out-target (headline)
    ├── ablation.py            Leave-one-category-out
    ├── time_machine.py        Pre-cutoff train, post-cutoff test
    ├── held_out_target.py     GroupKFold on target_id
    ├── phase1_cohort.py       Broader Ph1+ cohort
    ├── per_ta_loose_deprecated.py    Per therapeutic area
    ├── per_modality.py        Small-mol vs biologic
    ├── feature_importance.py  Coefficients vs published RS
    ├── calibrate_rs.py        Platt scaling
    ├── effect_sizes_ci.py     Bootstrap CIs on evidence dimensions
    ├── negative_result_xgb_catboost.py    Tried, didn't help
    └── negative_result_family_features.py  Tried, didn't help
```

## How to plug in your own model

Two paths (see [`benchmark/external_template.py`](benchmark/external_template.py)):

**Path 1 — in-process:** implement a Python callable matching the standard interface, register it, run `python3 benchmark/runner.py <your_scorer_name>`.

**Path 2 — external CSV:** produce `(target_id, indication_id, predicted_p_approval)` CSV, wire in via `wire_external_scores()`. Same benchmark, same leaderboard, direct comparison.

Either way, results appear in `preclin.v_benchmark_leaderboard`.

## What we CAN claim (with statistical support)

1. Public preclinical evidence predicts strict per-T-I FDA approval at **AUC 0.825** on Phase 1+ target-matched cohort, held-out-target CV.
2. **Top-decile predictions are 13.7× enriched** for approvals.
3. Model is well-calibrated (**ECE 0.013**).
4. **Human genetic evidence is dominant** (17.7pp of AUC by itself).
5. **Target-level cell + animal literature contribute zero marginal signal** on top of genetics + safety.
6. Model **generalizes to unseen targets** (2pp drop between random-split and held-out-target for LogReg).
7. Model **generalizes out-of-time** (LogReg trained pre-2019 predicts 2019+ outcomes at AUC 0.77, RS 12.3).
8. **Trained ML beats published rule-based methodology by 21pp AUC** (0.826 vs 0.615) and beats LLM-agent scoring by 19pp (0.826 vs 0.633).

## What we CANNOT claim

- Absolute `p_approval` interpretation is cohort-scoped (base rate 2.95% in Phase 1+ target-matched; not directly comparable to a random drug in the world).
- Non-CT.gov trials (EU-CTR, ChiCTR) not covered — ~20% of global drug development invisible.
- Preclinical / IND-stage kills never enter CT.gov, invisible entirely.
- Full temporal validity would require retrofit `evidence_as_of` per fact; feature values are current-day even in time-machine splits.

Full caveats: [`ROBUSTNESS.md`](ROBUSTNESS.md).

## License

MIT. If you build something on top, please cite / link back.
