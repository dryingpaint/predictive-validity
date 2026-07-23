# Results — final honest benchmark

*Last updated: 2026-07-23*

## Headline result

**Predicting FDA approval for a specific (target × indication) pair from public preclinical evidence:**

**Best model: stacked ensemble (LogReg + regularized LightGBM + RandomForest)**
- **AUC 0.825 [0.797, 0.849]**
- **RS(top 10%) = 13.67** (top-scored 10% of T-I pairs are approved at 13.67× the base rate)
- ECE 0.013 (well-calibrated)
- Cohort: **Phase 1+ target-matched T-I pairs (n=13,639)**, base rate 2.95%
- Evaluation: **5-fold GroupKFold on `target_id`** (no target in both train and test)

## Final leaderboard — Phase 1+ strict, held-out targets

| Rank | Scorer | AUC (95% CI) | RS(top 10%) | ECE | R@10% | P@10% |
|---|---|---|---|---|---|---|
| 1 | stacked_final_v1 | 0.825 [0.797, 0.849] | **13.67** | 0.013 | 0.603 | 0.178 |
| 2 | logreg_final_v1 | 0.822 [0.796, 0.851] | 13.53 | 0.268 | 0.600 | 0.177 |
| 3 | stacked_family_v1 | 0.815 [0.790, 0.841] | 13.25 | 0.014 | 0.596 | 0.176 |
| 4 | logreg_family_v1 | 0.813 [0.783, 0.838] | 13.25 | 0.263 | 0.596 | 0.176 |
| 5 | logreg_interactions_v1 | 0.812 [0.786, 0.842] | 12.21 | 0.271 | 0.576 | 0.170 |
| 6 | xgboost_final_v1 | 0.803 [0.775, 0.830] | 11.96 | 0.107 | 0.571 | 0.169 |
| 7 | catboost_final_v1 | 0.795 [0.768, 0.824] | 12.21 | 0.216 | 0.576 | 0.170 |

**Ranked-difference observations:**
- Stacked (LogReg + LGB-robust + RF) slightly beats LogReg alone (+0.3pp AUC).
- Target-family features didn't help (dropped AUC 1pp).
- Hand-crafted interactions didn't help (dropped AUC 1.3pp).
- XGBoost / CatBoost underperformed both stack and LogReg.

**Interpretation:** the current features have a ceiling around AUC 0.82-0.83 on strict held-out-target evaluation. Model architecture is not the bottleneck — **new evidence sources** are.

## Cross-cohort summary

Nine variants of the benchmark. Best model per variant:

| Cohort variant | n | Base rate | Best AUC | RS(top 10%) |
|---|---|---|---|---|
| Loose outcome, Ph2+, random-split | 2,611 | 28.4% | 0.917 (LGB) | 4.70 |
| Loose outcome, Ph2+, held-out target | 2,611 | 28.4% | 0.804 (LogReg) | 12.08 |
| **Loose, Ph2+ time-machine 2019** | 1,149 | 20.7% | 0.860 (LGB) | 6.08 |
| **Strict outcome, Ph2+, random-split** | 8,035 | 5.0% | 0.829 (Stack) | 12.84 |
| Strict, Ph2+, held-out target | 8,035 | 5.0% | 0.804 (LogReg) | 12.08 |
| **Strict, Ph2+ time-machine 2019** | 3,522 | 0.7% | 0.769 (LogReg) | 12.28 |
| **Strict, Ph1+, random-split** | 13,639 | 2.95% | 0.838 (Stack) | 13.81 |
| **Strict, Ph1+, held-out target** | **13,639** | **2.95%** | **0.825 (Stack)** | **13.67** |

**Robustness checks holding up:**
- Loose→strict: AUC drops 9pp but RS jumps 3× (predictive gain concentrates in top decile with rare positives)
- Random-split→held-out-target: AUC drops 1-2pp (linear models); 6pp (unregularized trees)
- Same-cohort→time-machine 2017/2019: AUC drops 5-10pp (real out-of-time is harder)

## Ablation — what makes the AUC

Full LogReg strict Ph2+ = 0.829. Leave-one-category-out:

| Removed category | Remaining AUC | ΔAUC | Interpretation |
|---|---|---|---|
| **A. Genetics** | 0.651 | **−17.7pp** | Dominant category |
| Context (Nelson tier + TA) | 0.811 | −1.8pp | Secondary |
| B. Mechanistic | 0.822 | −0.6pp | Marginal |
| E. Human PD | 0.826 | −0.3pp | Marginal |
| H. Safety | 0.827 | −0.2pp | Marginal |
| I. Landscape | 0.827 | −0.1pp | Marginal |
| C. Cell | 0.829 | **+0.0pp** | **No marginal signal** |
| D. Animal | 0.829 | **+0.0pp** | **No marginal signal** |

**Genetics contributes ~18pp of AUC by itself.** Target-level cell + animal literature contribute exactly zero on top of genetics.

## Per-modality

Small-molecule and biologic programs are predicted equally well (AUC ~0.83). Genetic medicine and cell therapy cohorts too small for stable CV.

## Time-machine robustness

Trained on T-I pairs whose first trial started before 2019, tested on 2019+:

| Model | AUC 2019+ | RS(top 10%) |
|---|---|---|
| **LogReg** | **0.769 [0.651, 0.888]** | **12.28** |
| LightGBM unregularized | 0.578 [0.475, 0.680] | 1.64 |

LightGBM overfits and doesn't generalize temporally. LogReg with L2 + calibration is robust.

## What we CANNOT claim

- **Absolute p_approval interpretation is cohort-scoped.** Our probabilities are calibrated to Phase 1+ target-matched T-I pairs (base rate 2.95%). A random drug in the world has base rate ~1.8% (approvals ÷ programs).
- **No time-machine on features.** Feature values are current-day; only the temporal split is out-of-time. True predictive validity requires retrofit `evidence_as_of` per fact.
- **Non-CT.gov trials (EU-CTR, ChiCTR) not covered.** ~20% coverage gap.
- **Preclinical / IND-stage kills invisible.**

## What we CAN claim (with statistical support)

1. **Public preclinical evidence predicts strict per-T-I FDA approval at AUC 0.825** on Phase 1+ target-matched cohort, held-out-target CV.
2. **Top-decile predictions are 13.7× enriched** for approvals.
3. **Model is well-calibrated** (ECE 0.013).
4. **Human genetic evidence is dominant** (17.7pp of AUC by itself).
5. **Target-level cell + animal literature contribute zero marginal signal** (ΔAUC = 0.000 when either is removed on top of genetics + safety).
6. **Model generalizes to unseen targets** (2pp drop between random-split and held-out-target for LogReg; unregularized tree models overfit and drop 6pp).
7. **Model generalizes out-of-time** (LogReg trained pre-2019 predicts 2019+ outcomes at AUC 0.77, RS 12.3).

## Files (see repo)

- [`ROBUSTNESS.md`](ROBUSTNESS.md) — 12 attacks vs benchmark and how each survives
- [`ANALYSIS.md`](ANALYSIS.md) — pathway wrongness analysis and effect sizes
- [`SCHEMA.md`](SCHEMA.md) — evidence taxonomy + database schema design
- [`CASE_STUDIES.md`](CASE_STUDIES.md) — 6 preclinical-strong / clinical-fail drugs
- [`benchmark/README.md`](benchmark/README.md) — benchmark methodology
- [`db/QUESTIONS.md`](db/QUESTIONS.md) — 25 example SQL queries
- [`data/leaderboard.csv`](data/leaderboard.csv) — snapshot of all benchmark runs
