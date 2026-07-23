# Results

## Headline

**Predicting FDA approval for a specific `(target × indication)` pair from public preclinical evidence:**

Best model: stacked ensemble (LogReg + regularized LightGBM + RandomForest), evaluated with 5-fold GroupKFold on `target_id` (no target appears in both train and test).

| Metric | Value |
|---|---|
| **AUC** | **0.825 [0.797, 0.849]** |
| **RS (top 10%)** | **13.67** (top decile enriched 13.7× for approvals) |
| **Recall @ top 10%** | 0.60 |
| ECE | 0.013 (well-calibrated) |
| Cohort | Phase 1+ target-matched T-I pairs, n=13,639 |
| Base rate | 2.95% |

## Full leaderboard — strict per-T-I outcome

Phase 1+ cohort (n=13,639), 5-fold GroupKFold on `target_id`:

| Rank | Scorer | AUC (95% CI) | RS(top 10%) | ECE | R@10% | P@10% |
|---|---|---|---|---|---|---|
| 1 | stacked_final_v1 | **0.825 [0.797, 0.849]** | **13.67** | 0.013 | 0.603 | 0.178 |
| 2 | logreg_final_v1 | 0.822 [0.796, 0.851] | 13.53 | 0.268 | 0.600 | 0.177 |
| 3 | stacked_family_v1 | 0.815 [0.790, 0.841] | 13.25 | 0.014 | 0.596 | 0.176 |
| 4 | logreg_interactions_v1 | 0.812 [0.786, 0.842] | 12.21 | 0.271 | 0.576 | 0.170 |
| 5 | xgboost_final_v1 | 0.803 [0.775, 0.830] | 11.96 | 0.107 | 0.571 | 0.169 |
| 6 | catboost_final_v1 | 0.795 [0.768, 0.824] | 12.21 | 0.216 | 0.576 | 0.170 |

**External-model comparisons (strict Ph2+, cohort n=8,035):**

| Scorer | Method | AUC (95% CI) | RS(top 10%) |
|---|---|---|---|
| logreg_strict_v1 | Trained LogReg | 0.826 [0.801, 0.851] | 13.11 |
| pheiron_rs_composite_v1 | Untrained published RS | 0.615 [0.589, 0.641] | 5.92 |
| sonnet_agent_sdk_v1 | LLM reads evidence | 0.633 [0.552, 0.707] | 1.84 |
| random_v1 | Uniform | 0.509 [0.485, 0.539] | 1.01 |

**Trained ML beats published rule-based methodology by 21pp AUC, LLM-agent by 19pp.**

## Cross-cohort robustness

Best model per variant:

| Cohort variant | n | Base rate | Best AUC | RS(top 10%) |
|---|---|---|---|---|
| Loose (any-indication), Ph2+, random-split | 2,611 | 28.4% | 0.917 (LGB) | 4.70 |
| Loose, Ph2+, held-out target | 2,611 | 28.4% | 0.804 (LogReg) | 12.08 |
| Loose, Ph2+ time-machine 2019 | 1,149 | 20.7% | 0.860 (LGB) | 6.08 |
| Strict, Ph2+, random-split | 8,035 | 5.0% | 0.829 (stack) | 12.84 |
| Strict, Ph2+, held-out target | 8,035 | 5.0% | 0.804 (LogReg) | 12.08 |
| Strict, Ph2+ time-machine 2019 | 3,522 | 0.7% | 0.769 (LogReg) | 12.28 |
| Strict, Ph1+, random-split | 13,639 | 2.95% | 0.838 (stack) | 13.81 |
| **Strict, Ph1+, held-out target** | **13,639** | **2.95%** | **0.825 (stack)** | **13.67** |

## Ablation — what makes the AUC

Full LogReg (strict Ph2+) = 0.829. Leave-one-category-out:

| Removed category | Remaining AUC | ΔAUC |
|---|---|---|
| **A. Genetics** | 0.651 | **−17.7pp** — dominant |
| Context (Nelson tier + TA) | 0.811 | −1.8pp |
| B. Mechanistic | 0.822 | −0.6pp |
| E. Human PD | 0.826 | −0.3pp |
| H. Safety | 0.827 | −0.2pp |
| I. Landscape | 0.827 | −0.1pp |
| **C. Cell** | 0.829 | **+0.0pp — no marginal signal** |
| **D. Animal** | 0.829 | **+0.0pp — no marginal signal** |

Genetics accounts for ~18pp of AUC. Target-level cell + animal literature contribute exactly zero on top of genetics — a clean measurement of publication-bias saturation.

## Per-modality (STRICT, LogReg)

| Modality | n | AUC (95% CI) | RS(top 10%) |
|---|---|---|---|
| biologic (mAb/protein/peptide) | 762 | 0.832 [0.778, 0.872] | 9.86 |
| small_molecule | 961 | 0.824 [0.792, 0.862] | 6.56 |

Small-mol and biologic predicted equally well. Genetic-medicine and cell-therapy cohorts too small for stable CV.

## Pathway wrongness — how often does strong evidence still fail?

Conditional-failure view: for T-I pairs with strong evidence in each dimension, what fraction of Phase 3+ attempts still fail?

**Phase 3+ T-I pairs (n=1,182):**

| Evidence dimension | high-ev n | Approved | Efficacy fail | **Any fail** |
|---|---|---|---|---|
| Line C lit high (target cell) | 1,053 | 21% | 50% | **79%** |
| Line D lit high (target animal) | 1,004 | 22% | 51% | **78%** |
| OT genetic ≥0.3 | 986 | 17% | 54% | **83%** |
| OT animal model ≥0.3 | 955 | 15% | 54% | **85%** |
| Line E lit high (human PD) | 855 | 27% | 47% | **73%** |
| ClinGen Strong/Def ≥1 | 380 | 24% | 47% | **76%** |
| IMPC ≥3 KO phenotypes | 351 | 17% | 54% | **83%** |
| Mendelian ≥5 | 213 | 25% | 41% | **75%** |

**Even at strong-evidence Phase 3, 73-85% of attempts still fail.** Multi-line convergence helps but doesn't break the ceiling:

| Convergent evidence | n | Approved | Efficacy fail |
|---|---|---|---|
| C ∧ D ∧ E all high | 1,011 | 14.5% | 35.7% |
| C ∧ D ∧ E ∧ (Mendelian≥5 OR ClinGen) | 422 | 22.0% | 32.2% |

Best possible preclinical profile → **22% approval rate** at Phase 3. The 78% failure rate is the "pathway wrongness" — biology confirms the mechanism works but doesn't confirm the mechanism drives the clinical outcome.

## Robustness — 12 attacks

Every attack we applied to the benchmark. Each row is a challenge to the AUC 0.825 claim; every one has a fix or acknowledged trade-off.

### Attacks fixed

| # | Concern | Fix |
|---|---|---|
| 1 | Loose "any-approval" outcome inflates base rate | `v_target_indication_strict_outcome` — strict per-T-I approval; base rate 5.0% not 23.1% |
| 2 | Post-outcome features leak (n_sponsors, n_programs, max_phase, ot_known_drug, ot_overall) | Removed from feature set |
| 3 | family_approved_count could include post-cutoff approvals | `v_target_family_precedent_by_year` — time-cutoff-aware precedent |
| 4 | Phase 2+ cohort filter = survivorship bias | Also run on Phase 1+ cohort (n=13,639, base rate 2.95%) |
| 5 | Concept drift / temporal generalization | Time-machine backtest: train pre-2019, test post-2019. LogReg holds AUC 0.77; LightGBM drops to 0.58 |
| 6 | Random-split K-fold may leak targets | GroupKFold on `target_id`: LogReg drops only 2.2pp; LightGBM drops 6.3pp (overfits) |
| 7 | ML overfitting | Regularized LightGBM with monotonic constraints; report multiple models; unregularized version marked as such |
| 8 | Metric gaming (AUC alone) | Report AUC + Brier + Recall@10% + Precision@10% + RS(top 10%) + ECE. Cross-checks catch tricks |
| 9 | Do features match known biology? | Ablation: removing genetics drops AUC 17.7pp; removing cell/animal drops 0pp. Matches published RS direction |
| 12 | Failure-label errors | Haiku + Sonnet dual classification on all 5,510 failed trials with `why_stopped` text; Sonnet-verified for Phase 3 silent kills |

### Attacks acknowledged (not fixed)

- **Cohort composition bias** — target-matched cohort enriched 10× for approved drugs vs raw 82k program universe (ChEMBL/DGIdb select for approved). Claims scoped to "T-I pairs with a target-matched primary drug reaching Phase 1+."
- **Non-CT.gov trials not ingested** — EU-CTR, ChiCTR, JP registries ≈ 20% of global drug development activity.
- **Preclinical / IND-stage kills invisible** — never enter CT.gov.
- **Feature values are current-day for non-precedent features** — Nelson tier, ClinGen, gnomAD, DepMap, Open Targets values are today's snapshots, not cutoff-time. Time-machine tests temporal split but not feature-freeze.
- **`n_dgidb_drugs` and `n_causal_diseases`** — current-day, not time-cutoff. Small residual leakage.
- **Absolute p_approval interpretation is cohort-scoped** — calibrated to 2.95% base rate in Phase 1+ target-matched cohort; not directly comparable to a random drug in the world.

## Files

- `data/leaderboard.csv` — snapshot of all benchmark runs
- `data/approvals.csv` — 544 FDA approvals 2015-2025
- `benchmark/README.md` — benchmark framework methodology + how to plug in a scorer
- `db/README.md` — schema runbook
- `db/QUESTIONS.md` — 25 example SQL queries
- `db/SCHEMA.md` — evidence taxonomy + database design (reference)
- `analyses/final_benchmark.py` — reproduces the headline AUC 0.825
