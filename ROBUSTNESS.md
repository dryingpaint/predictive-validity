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

**Fix applied:** removed all 5 from feature set (see `benchmark/scorers_ml.py:NUMERIC_FEATURES`).

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

## Attack 11: LLM-agent scorer

**Concern:** can an LLM (Sonnet) read evidence dossiers and predict better than trained ML?

**Fix applied:** implemented via Anthropic SDK (`benchmark/scorers_llm_agent.py`) with parallel workers. Ran on 200 balanced T-I pairs.

**Result:** LLM significantly underperforms trained ML (AUC 0.633 vs 0.826 for LogReg). Trained models leverage patterns from thousands of examples; the LLM has broad biology knowledge but no task-specific fitting. Useful as an interpretable "second opinion" but not a headline model.

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


---


# Comprehensive coverage assessment — where we are + honest gaps

## What we have complete visibility on

**Trials (2015-2025):**
- ✅ Every industry-sponsored Phase 1-3 drug/biological trial from CT.gov (441,876 trials in `public.trials`; ~28K industry subset resolved into programs)
- ✅ Termination reasons for all trials with `why_stopped` text (5,510 Haiku + 5,510 Sonnet classified)
- ✅ Publication cross-reference for 476 Phase 3 silent kills

**Approvals:**
- ✅ All 544 FDA CDER+CBER novel drug approvals 2015-2025
- ✅ Nelson tier assigned per (target × indication) for 346 curated pairs
- ⚠️ Ex-US approvals inferred from ChEMBL max_phase=4 but not explicitly ingested per-agency

**Drugs:**
- ✅ 52,694 unique drugs from union of approvals + ChEMBL + LLM resolutions + CT.gov intervention names
- ⚠️ Only 2,770 (~5%) have a target-matched primary gene link — see selection-bias caveat

**Targets:**
- ✅ 41,681 targets in `public.targets` from genome-browser
- ✅ Evidence dimensions per target across A-I categories (see below)

## Evidence dimensions (50+ dimensions in `preclin.evidence_dimension`)

**A. Genetics:**
- Nelson tier T0-T4 (per T-I)
- ClinGen Strong/Definitive count
- Mendelian associations (Orphanet + OMIM)
- Mendelian dominant vs recessive split
- GWAS significant hits (p<5e-8)
- Open Targets genetic score
- Open Targets somatic (cancer) score
- Open Targets RNA expression score
- Open Targets L2G colocalization (schema ingested but source data is null-heavy)
- Open Targets is_mendelian aggregate

**B. Mechanistic biology:**
- Line B literature score (PubMed Haiku)
- Tractability flags (small molecule, antibody, PROTAC)
- Yanai Tau specificity (bulk tissue GTEx/HPA summary)
- **Single-cell Tau specificity** (HPA 154 cell types — Tabula Sapiens style)
- Single-cell max cell type + expression value
- Number of highly-expressed tissues
- STRING PPI hub-ness (n_ppi_partners)
- Reactome pathway membership count
- GO biological process / molecular function / cellular component term counts

**C. Cell:**
- Line C literature score
- DepMap pan-essential flag
- DepMap n_dependent_lineages
- DepMap mean effect
- Drug-specific cell efficacy (PubMed Sonnet, ~4,500 rows)

**D. Animal:**
- Line D literature score
- IMPC KO phenotype count (15,649 rows)
- IMPC top-level categories
- Open Targets animal model score (Phenodigm)
- HPO phenotype count per gene
- Drug-specific rodent + non-rodent efficacy (PubMed)

**E. Human PD engagement:**
- Line E literature score
- Drug-specific target engagement score

**F. Clinical outcome:**
- Every trial outcome + status
- Drug-specific Phase 2/3 endpoint outcomes (PubMed extraction)
- Sonnet publication-verified silent-kill reasons

**G. Pharmacology:**
- Drug modality + subtype
- Route of administration
- Half-life (partial coverage from `public.therapies`)
- Drug structural biology score (PubMed)

**H. Safety:**
- gnomAD pLI (18,164 targets)
- gnomAD LOEUF
- SIDER adverse event counts per drug
- Drug-specific preclinical tox signal

**I. Landscape:**
- Family precedent (approved count per family)
- Gene approved count
- DGIdb drug precedent (n_dgidb_drugs)
- Causal disease pleiotropy count
- Suggestive disease pleiotropy count

## Coverage matrix — every dimension × subject coverage

```sql
SELECT ed.category, ed.dimension,
       COUNT(DISTINCT es.subject_id) AS n_targets_or_drugs
FROM preclin.evidence_dimension ed
LEFT JOIN preclin.evidence_score es ON es.dimension = ed.dimension
GROUP BY ed.category, ed.dimension
ORDER BY ed.category, ed.dimension;
```

## Honest remaining gaps

### 1. Non-CT.gov trials (biggest coverage gap)
- **EU-CTR** (~35K trials in EudraCT) — not ingested
- **ChiCTR** (~70K Chinese trials) — not ingested
- **JapicCTI** (JP) — not ingested
- **CTIS** (new EU replacement for EudraCT) — not ingested

Impact: some ex-US-approved drugs may look "silent kill" in our data because their late-stage trials happened outside CT.gov. Estimated 5-15% of the failure classification bucket.

### 2. Trials without `why_stopped` text (~50% of terminations)
Our audit only classified trials that had a stated reason. The other ~5,000 terminated trials sit in `unclassified_termination`. Fix: publication cross-reference for each (would take ~$200 Sonnet cost, ~24 hours).

### 3. Preclinical / IND-stage kills
Drugs that were killed before Phase 1 or in IND-enabling never appear in CT.gov. Fully invisible. Fix requires paid databases (Cortellis, GlobalData, BioMedTracker).

### 4. Full-text PubMed / BioRxiv preprints
Our literature scoring uses abstract-only Haiku extraction. Full-text via PMC and preprints from BioRxiv/MedRxiv are untapped. Would add:
- More granular Methods/Results/Discussion signal
- Preprint methods (novel modalities, first-in-human)

### 5. Foundation-model in-silico predictions
No AlphaFold/ESM/Anthropic-model target scoring is in the schema. Pheiron mentions using foundation models; we could add embedding-based similarity as a feature.

### 6. Drug-specific evidence extraction
Only 4,510 drug-specific PubMed extractions completed (of ~1,541 drugs the pipeline targets). Pipeline running in background, ~50 hours to full coverage.

### 7. Combination trial deconvolution
Combination drugs (methotrexate+adalimumab, olanzapine+samidorphan, etc.) get treated as one drug program per component. Doesn't fully deconvolve combo-vs-mono efficacy.

### 8. Placebo/vehicle filtering
7,660 "programs" have `placebo` as their drug. Analysis views should exclude but we don't systematically filter. Fix: `WHERE d.is_placebo IS NOT TRUE`.

### 9. Sponsor canonicalization
`sponsor_name` field has variants like "GlaxoSmithKline" vs "GSK" vs "GSK plc" as different rows. Fix: canonical mapping via `public.sponsors.canonical_name`.

### 10. Trial-outcome integration for CT.gov results
Some trials post `resultsSection` with efficacy p-values and outcomes. We haven't parsed these into per-trial outcome features.

## Comprehensiveness score (subjective)

| Aspect | Coverage | Notes |
|---|---|---|
| **CT.gov industry Phase 1-3 trials 2015-2025** | 100% | All 28K trials in `program_trial` |
| FDA approvals 2015-2025 | 100% | All 544 in `preclin.approval` |
| Target-mapped drugs (analysis-usable) | ~9% | 2,770 / 30,517 — the selection-bias cohort |
| Evidence dimensions (A-I taxonomy) | ~85% | 50 dimensions ingested; most Pheiron dimensions present |
| Failure classification | ~55% | 5,510 with why_stopped text; 5,000 without unclassified; 476 silent kills verified |
| Non-CT.gov trials | 0% | EU-CTR, ChiCTR, JP untapped |
| Drug-specific literature extraction | 0.3% | Pipeline running |
| Foundation model in-silico | 0% | Not started |

## What "fully comprehensive" would take

Ordered by effort/value:

1. **Fix placebo/sponsor filters** in views — 30 min, high value (cleans all downstream numbers)
2. **Sonnet publication cross-ref for the 5K unclassified terminations** — $150, 24 hours background
3. **EU-CTR ingest** via EudraCT API — 6 hours coding + 12 hours pull
4. **ChiCTR ingest** — 8 hours coding (Chinese-language records need translation for full failure reason)
5. **BioRxiv preprint scraping** — 4 hours coding + long-tail full-text extraction
6. **Full-text PMC extraction for Phase 3 fail cases** — 12 hours + ~$300 Sonnet
7. **Foundation model target-scoring layer** — days of development
8. **Cortellis/BioMedTracker subscription** — $$$$, gives clean silent-kill labels
