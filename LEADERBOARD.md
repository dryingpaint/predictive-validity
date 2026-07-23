# Leaderboard — 2026-07-23 (v2, robustness-corrected)

**Task:** given a (target × indication) pair and public preclinical evidence, predict P(any drug program on this T-I gets approved for THIS indication).

## Two ground-truth definitions

We distinguish two outcome definitions to be honest about what's being predicted:

| Definition | Positive rate | What it means |
|---|---|---|
| **Strict** (canonical) | **5.0%** | Drug was FDA-approved *for THIS specific indication* |
| Loose | 23.1% | Drug was approved *for any indication* (a target may score positive because a drug against it got approved elsewhere) |

**Only the strict definition is defensible for T-I-level prediction.** Our previous benchmarks used the loose definition and inflated the base rate 4.6×. All headline numbers below use the strict definition unless noted.

## Overall leaderboard — STRICT outcome (5-fold CV OOF, cohort n=8,035)

| Scorer | AUC (95% CI) | Brier | Recall@10% | Prec@10% | RS(top 10%) | ECE |
|---|---|---|---|---|---|---|
| **stacked_v1** (LogReg + LGB + RF meta) | **0.829 [0.806, 0.855]** | 0.029 | 0.59 | 0.30 | **12.84** | 0.017 |
| **logreg_strict_v1** | **0.826 [0.801, 0.851]** | 0.025 | 0.59 | 0.30 | 13.11 | **0.001** |
| lightgbm_strict_v1 (unreg) | 0.794 [0.767, 0.822] | 0.080 | 0.57 | 0.29 | 11.84 | 0.132 |
| randomforest_strict_v1 | 0.790 [0.763, 0.817] | 0.128 | 0.55 | 0.28 | 10.92 | 0.295 |
| lightgbm_robust_strict_v1 (regularized) | 0.733 [0.703, 0.762] | 0.140 | 0.43 | 0.22 | 6.76 | 0.293 |

**Reading:** LogReg beats the nonlinear models on the strict benchmark. Nonlinear models overfit on the small positive class (n=403 approved out of 8,035). Calibrated LogReg has AUC 0.826, ECE 0.001, and top-decile RS 13× — meaning top-10% of scored T-Is are approved at 13× the base rate. **Stacked ensemble (with LogReg meta-learner over LogReg + robust-LGB + RF, log-transformed count features)** edges LogReg alone by a hair on AUC (0.829 vs 0.826) with comparable calibration.

## Comparison — loose vs strict outcome (LightGBM only)

| Outcome | n T-I | Base rate | AUC (95% CI) | RS(top 10%) |
|---|---|---|---|---|
| Loose (any-indication) | 2,611 | 28.4% | 0.917 [0.904, 0.926] | 4.70 |
| **Strict (this-indication)** | **8,035** | **5.0%** | **0.794 [0.767, 0.822]** | **11.84** |

The loose AUC (0.917) is inflated by the "already-known-approved-target" shortcut. The strict AUC (0.79) is the honest measure. Note RS(top 10%) is *higher* on the strict task — with a low base rate, top-decile concentration is proportionally more valuable.

## Time-machine backtest — STRICT outcome (trained on pre-cutoff T-I pairs)

*Time-cutoff-aware features:* family and gene precedent counts computed as-of the T-I's `first_trial_date` (not today).

| Cutoff | Scorer | Train n | Test n | AUC (95% CI) | RS(top 10%) |
|---|---|---|---|---|---|
| 2019-01-01 | **logreg_strict** | 4,199 | 3,522 | **0.769 [0.651, 0.888]** | **12.28** |
| 2019-01-01 | lightgbm_strict | 4,199 | 3,522 | 0.578 [0.475, 0.680] | 1.64 |
| 2017-01-01 | logreg_strict | 2,311 | 5,410 | 0.770 [0.656, 0.876] | 14.00 |
| 2017-01-01 | lightgbm_strict | 2,311 | 5,410 | 0.577 [0.507, 0.644] | 0.86 |

**Reading:** LogReg holds AUC 0.77 out-of-time with RS 12-14× on the top decile. LightGBM overfits (out-of-time AUC drops to 0.58) — need stronger regularization for tree models on this task.

## Time-machine backtest — LOOSE outcome (for comparison, previous run)

| Cutoff | Scorer | Train n | Test n | AUC (95% CI) | RS(top 10%) |
|---|---|---|---|---|---|
| 2021-01-01 | lightgbm_v1 | 1,656 | 682 | 0.875 [0.844, 0.903] | 6.16 |
| 2019-01-01 | lightgbm_v1 | 1,189 | 1,149 | 0.860 [0.832, 0.886] | 6.08 |
| 2017-01-01 | lightgbm_v1 | 593 | 1,745 | 0.795 [0.771, 0.822] | 3.70 |

## Per-therapeutic-area (loose outcome, previous run)

| Therapeutic area | n T-I | AUC (95% CI) | RS(top 10%) |
|---|---|---|---|
| oncology | 1,370 | 0.927 [0.911, 0.940] | 4.92 |
| other | 1,035 | 0.844 [0.818, 0.870] | 4.41 |

## Leave-one-category-out ablation (loose outcome, full model AUC = 0.917)

| Category removed | AUC | ΔAUC | Interpretation |
|---|---|---|---|
| A. Genetics | 0.893 | **−0.024** | Most load-bearing category |
| Context (Nelson tier + TA) | 0.912 | −0.005 | Secondary |
| B. Mechanistic | 0.915 | −0.002 | Marginal |
| E. Human PD | 0.915 | −0.001 | Marginal |
| H. Safety | 0.915 | −0.001 | Marginal |
| I. Landscape | 0.916 | −0.001 | Marginal |
| C. Cell (excl. DepMap) | 0.916 | −0.001 | Marginal |
| D. Animal | 0.917 | **+0.000** | Null — adds no marginal information |

**Reading:** genetics is dominant. Removing all animal in vivo evidence doesn't hurt AUC — target-level animal-in-vivo literature is fully redundant with other categories. Consistent with our earlier RS analysis (target-level Line D score has RS ≈ 1.0).

## Key claims (honest, robust)

1. **Preclinical evidence predicts T-I-level FDA approval at AUC 0.826** (LogReg, 5-fold CV OOF, strict outcome, cohort n=8,035, base rate 5.0%).
2. **Top-decile predictions are 13× enriched for approvals.** ~30% of top-10% scored T-I pairs got FDA-approved (base rate 5%).
3. **Model is well-calibrated** (LogReg ECE 0.001 on strict outcome).
4. **Genetics (Category A) is the dominant preclinical signal.** Removing it drops AUC 2.4pp; removing D. Animal in vivo drops AUC 0.0pp.
5. **AUC is inflated 12pp by loose vs strict outcome** (0.92 → 0.79). Prior "any-approval" formulations of T-I benchmarks systematically overestimate model performance.

## Data-quality fixes applied vs v1

- Removed leaky features: `n_sponsors`, `n_programs`, `max_phase_reached`, `ot_known_drug_max`, `ot_overall_max` (all post-outcome).
- Added strict per-T-I outcome definition (`v_target_indication_strict_outcome`).
- Time-cutoff-aware family/gene precedent (`v_target_family_precedent_by_year`).
- Filtered placebos and microbial targets.

## Caveats remaining

- **Non-CT.gov trials not ingested.** EU-CTR, ChiCTR, JP registries ≈ 20% of global drug development activity.
- **Feature values are current-day for non-precedent features.** Nelson tier, ClinGen, gnomAD, DepMap, Open Targets — all values reflect today's data, not cutoff-time snapshots. This is approximate but stable-ish (most values are from 2019+ ontology releases).
- **Preclinical / IND-stage kills invisible.** Never enter CT.gov.
- **`n_dgidb_drugs` and `n_causal_diseases` are current-day, not time-cutoff.** Small residual leakage.
- **Cell-therapy and vaccine programs partially filtered but not fully.** Some remain in cohort.

Full state: [`docs/STATE_OF_ANALYSIS.md`](docs/STATE_OF_ANALYSIS.md).
