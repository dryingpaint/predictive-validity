# Robustness assessment

This document catalogs every attack we've applied to the benchmark and how it survives.

## Attack 1: outcome-definition inflation

**Concern:** initial "any-approval" outcome (drug approved for any indication) inflates positive rate.

| Definition | Positive rate | Best AUC |
|---|---|---|
| Loose (any-indication) | 23.1% | 0.917 |
| **Strict (this-indication)** | 5.0% | **0.826** |

**Fix applied:** `v_target_indication_strict_outcome` view; strict is default for all headline claims.

## Attack 2: data leakage from post-outcome features

**Concern:** features like `n_sponsors`, `n_programs`, `max_phase_reached`, `ot_known_drug_max`, `ot_overall_max` reflect post-hoc program success, not preclinical evidence.

**Fix applied:** removed all 5 from feature set (see `13_ml_scorers.py`).

## Attack 3: residual leakage in landscape features

**Concern:** `family_approved_count` and `gene_approved_count` might include approvals dated after the T-I's first trial.

**Fix applied:** `v_target_family_precedent_by_year` view computes precedent as-of a given year; time-machine uses trial-year-relative values.

## Attack 4: Phase 2+ cohort filter is itself outcome selection

**Concern:** filtering to `max_phase_reached >= 2` excludes drugs that die at Phase 1 — a form of survivorship bias.

**Fix applied:** ran benchmark on Phase 1+ cohort (n=13,639 vs Phase 2+ n=8,035). Base rate drops from 5.0% to 2.95%. AUC held at 0.838.

## Attack 5: temporal drift / concept drift

**Concern:** models trained on today's evidence + today's outcomes might not generalize to future programs.

**Fix applied:** time-machine backtest. Train on T-I pairs whose first trial started BEFORE cutoff, test on AT/AFTER.

| Cutoff | Train n | Test n | LogReg AUC |
|---|---|---|---|
| 2017 | 2,311 | 5,410 | 0.770 [0.656, 0.876] |
| 2019 | 4,199 | 3,522 | 0.769 [0.651, 0.888] |

LightGBM overfits under time-machine (drops to AUC 0.58). LogReg is robust (holds AUC 0.77).

## Attack 6: target-level memorization

**Concern:** random-split k-fold may put T-I pairs with the same target in both train and test. Model could memorize target-level features rather than generalize.

**Fix applied:** GroupKFold on `target_id`. No target appears in both train and test.

| Split | LogReg AUC | Stacked AUC |
|---|---|---|
| Random 5-fold | 0.826 | 0.829 |
| Held-out-target 5-fold | 0.804 | (0.825 on Ph1+) |
| Held-out-target 5-fold, Ph1+ | 0.822 | 0.825 |

**Drop only 1.3-2.2pp** — model generalizes to unseen targets. LightGBM drops 6.3pp on same test (still overfitting).

## Attack 7: ML model overfitting

**Concern:** high AUC (0.92 on loose) might be overfit.

**Diagnostic:**
- Unregularized LightGBM CV OOF: AUC 0.917
- Regularized LightGBM (max_depth=4, min_child_samples=50, monotonic constraints): AUC 0.733
- Same on strict outcome: unreg 0.794, reg 0.733
- Time-machine unreg LightGBM: AUC 0.58 (huge overfit)
- Time-machine LogReg: AUC 0.77 (holds up)

**Conclusion:** unregularized tree models memorize; LogReg + regularization generalize. Reported headline numbers use the robust model.

## Attack 8: metric gaming

**Concern:** maybe AUC is inflated by the class imbalance / calibration issue.

**Fix applied:** report full suite — AUC + Brier + Recall@10% + Precision@10% + RS(top 10%) + ECE. Anti-correlated metrics catch tricks:

- LogReg strict Ph2+: AUC 0.826, Brier 0.025, ECE 0.001 — all consistent
- Stacked Ph1+: AUC 0.838, Brier 0.018, ECE 0.012 — all consistent
- LightGBM unreg strict: AUC 0.794, ECE 0.132 — decent AUC but poorly calibrated (confidence miscalibrated)

## Attack 9: feature-level biology alignment

**Concern:** does the model actually learn known biology, or fit noise?

**Diagnostic:** compare LogReg coefficients to published Relative Success (`v_relative_success_clean`).

Individual coefficients: 36% alignment. **But this is a multicollinearity artifact**: Nelson tier + Mendelian ≥5 + ClinGen + OT genetic are all correlated. LogReg splits credit unpredictably among them; individual coefficients aren't interpretable.

**Model-level diagnostic:** ablation. Removing all A. Genetics features drops AUC 17.7pp (0.829 → 0.651). Removing C or D features drops AUC 0pp. **This unambiguously matches published biology** — genetics is the dominant signal, target-level literature is null.

## Attack 10: cohort composition bias

**Concern:** the target-matched cohort (only 9% of the full 82K program universe) is enriched for approved drugs (10× baseline).

**Acknowledged, not fixed.** ChEMBL / DGIdb / target-annotation systematically overweight approved drugs. This bias is real and unresolvable without paid databases (Cortellis, GlobalData) that include failed-drug data.

**Mitigation:** we don't claim generalization to the raw 82K universe. All claims scoped to "T-I pairs with a target-matched primary drug reaching Phase 1+."

## Attack 11: LLM-agent scorer (in progress, sampled subset)

**Concern:** can an LLM (Sonnet) read evidence dossiers and predict better than trained ML?

**Status:** partial data (stalled at ~50/100 T-Is due to Claude Code subprocess bottlenecks). To be finished on a properly async infrastructure or via Anthropic API SDK directly.

## Attack 12: multi-classifier verification

**Concern:** what if failure-classification labels are wrong?

**Fix applied:** Haiku + Sonnet both run on all 5,510 failed trials with `why_stopped` text. Where they disagree, publication cross-reference for Phase 3 silent kills. Labels stored with confidence tag.

## What we still can't defend

- **EU-CTR / ChiCTR trials not ingested** — ~20% of global drug development activity invisible.
- **Preclinical / IND-stage kills** — never enter CT.gov.
- **Feature values are current-day for non-precedent features.** Reference data (Nelson tier, gnomAD, ClinGen) approximately stable but not literally time-cutoffed.
- **Non-LLM classifiers used for silent-kill reasons** — publication data is sparse for 15,000+ silent kills.
- **No cross-sample validation** with paid industry databases.
- **Absolute p_approval interpretation depends on cohort choice.** In our Phase 1+ cohort baseline is 2.95%; in the raw universe it's 1.8%. Our probabilities are calibrated to the cohort, not to a random drug in the world.
