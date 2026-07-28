# Section 2, part 3 — does other evidence add anything *on top of* genetics?

Melissa's leave-one-category-out ablation (`category_ablation`) answers this
**backward**: dropping cell / animal literature from the full model costs ~0 AUC. This
analysis is the **forward / stratified complement** — the direct "conditional on
genetics" test that a reader intuitively wants to see.

**Question.** For each non-genetic evidence type, does it predict approval *within*
programs that already have genetic support, and *within* programs that don't? Evidence
that only predicts when genetics is present is a **genetics proxy**; evidence that
predicts in **both** strata is genuinely **additive**.

**Figure:** `genetic_conditioning_clean.png` / `.svg` (two panels, shared rows).
**Script:** `analyses/genetic_conditioning.py` → `data/genetic_conditioning.csv`
(+ `data/genetic_conditioning_interaction.csv`). Plotted by
`analyses/plot_predictive_power.py::plot_genetic_conditioning`.

## Method

- **Cohort:** 11,404 Phase 2+ **programs** (non-placebo), from
  `preclin.v_program_evidence_wide` joined to `v_target_evidence_wide` for OT-somatic.
  Base approval **29.7%**. (Program grain, not the T-I-pair grain of parts 1–2 — a
  regression on program approval needs the program-level confounders. Stated so the *n*
  isn't confused with the 8,144-pair dose-response cohort.)
- **Genetics strata — by STRENGTH, not "any dimension":** Melissa's own
  `genetic_only_v1` additive score (ported verbatim from
  `benchmark/scorers_rule_based.py`). **Genetics-present := score ≥ 1.0** (her
  Moderate+Strong tiers): n=4,335, approval 40.1%. **Genetics-absent := score < 1.0**:
  n=7,069, approval 23.3%.
  - This matters. The permissive **any-genetic-dimension** composite (OT-genetic≥0.3 *or*
    GWAS≥50 *or* …) fires for **84%** of programs and separates the strata only weakly
    (31.5% vs 20.1%) — the "any-dimension trap." The strength score separates cleanly
    (40.1% vs 23.3%). Permissive is kept only as a labeled sensitivity in the script.
- **Two metrics, side by side (this is the point of the figure):**
  - **Left — marginal Relative Success** (unadjusted; the same metric as the rest of
    Section 2): approval-rate *with* ÷ *without* the evidence, within each stratum,
    bootstrap 95% CI.
  - **Right — adjusted odds ratio:** one multivariate logistic per stratum, all
    non-genetic evidence entered together + therapeutic area + target class (TDL).
- **Formal flip test:** a pooled `evidence × gpres` interaction model; the `:gpres`
  p-value is reported per row (`***` p<0.001, `**` <0.01, `*` <0.05).
- **Drug-level LLM efficacy is excluded** (hindsight-contaminated for approved drugs).
  Target-level literature lines C/D/E are LLM-extracted and present-day (not time-gated);
  they are kept precisely because the finding is that they do **not** add — see caveats.

## The headline: marginal additivity is collinearity

**Read the two panels together.** Unadjusted, almost everything looks additive — cell,
animal, and PD literature are all RS > 1 in *both* strata. Adjust for the other evidence
+ area + target class and that apparent signal **collapses**:

| Evidence (non-genetic) | RS · genetics+ / − | adj OR · genetics+ / − | interaction | verdict |
|---|---|---|---|---|
| **Human PD engagement** † | 2.03 / 1.86 | **2.09*** / 3.52*** | *** | **adds in both strata** |
| Cell-pathway literature † | 1.90 / 1.44 | 0.99 / 1.05 | ns | rides on genetics → null |
| Animal in-vivo literature † | 1.86 / 1.44 | 1.52*** / **0.57*** | *** | rides on genetics → flips |
| OT animal-model | 1.39 / 1.37 | 1.02 / 1.34 | * | genetics-dependent |
| IMPC mouse phenotypes | 1.07 / 0.80 | 0.97 / 0.69 | *** | genetics-dependent |
| DepMap pan-essential | 0.40 / 0.21 | 0.35*** / 0.22*** | * | **adverse flag in both** |
| Constrained gene (LOEUF<0.35) | 0.86 / 0.41 | 0.80** / 0.59*** | ns | **adverse flag in both** |
| Small-molecule tractable | 0.99 / 1.00 | 0.91 / 0.91 | ns | no signal either way |

(† LLM-extracted literature. OR run larger than the corresponding rate ratio at this base
rate — compare panels for **direction**, not magnitude.)

Three things fall out, all consistent with the ablation (Cell 0.0 / Animal 0.0):

1. **The only non-genetic evidence with an independent *positive* signal on top of
   genetics is human PD (target) engagement** — RS and adjusted OR both > 1 in both
   strata (OR 2.09 with genetics, 3.52 without; the interaction says it matters *more*
   when genetics is absent, i.e. it's your best remaining read when you have no genetics).
   **Caveat:** PD here is the LLM-extracted, present-day `line_e_lit` score, so it is
   itself hindsight-prone and un-time-gated — the one apparently-additive signal is also
   the softest. See the Section 5 hindsight arc.
2. **Cell and animal literature only *look* additive.** Marginally both are RS ≈ 1.4–1.9
   in both strata; once you hold the co-occurring evidence constant, cell goes to null and
   animal literature's residual signal in genetics-absent programs **reverses to a failure
   association** (OR 0.57, interaction p=4.7e-7). This is *why* the ablation shows them
   adding ~0 AUC — their marginal signal is carried by what they co-occur with, not by
   independent information.
3. **DepMap pan-essentiality and gnomAD constraint are independent *adverse* flags** —
   they predict failure in both strata (no therapeutic window / hard-to-drug-safely).
   They add information, just adverse; already reflected in her rule-based scorer
   (`depmap_pan_essential` → RS 0.12).

**Bottom line for the write-up:** the marginal Relative Success *overstates* additivity;
the honest, adjusted answer is that essentially nothing non-genetic independently improves
the odds on top of genetics except human PD engagement — and even that is a soft,
literature-derived signal. This is the forward-direction confirmation of the ablation's
genetics-dominance.

## Caveats

- **OR ≠ RR.** At a ~30–40% base rate the odds ratio is inflated relative to the rate
  ratio, so the right-panel magnitudes read larger than the left-panel RS. The axis is
  labeled "adjusted odds"; compare the two panels for direction and for collapse, not for
  matched numbers.
- **The flip is adjustment-induced.** "Animal literature predicts failure without
  genetics" is a *multivariate residual*, not a raw fact (raw RS is 1.44). Stated that way
  in the figure — "rides on genetics (collapses / flips when adjusted)."
- **Program grain / live DB.** n≈11.4k as of this pull; expect small churn. Regenerate
  before publishing.
- **PD = LLM literature.** As above — the single additive signal is un-time-gated; don't
  oversell it.

## Reproduce

```bash
DATABASE_URL='postgresql://…' python3 analyses/genetic_conditioning.py     # writes the CSVs
python3 analyses/plot_predictive_power.py                                   # renders all Section-2 figures
```
