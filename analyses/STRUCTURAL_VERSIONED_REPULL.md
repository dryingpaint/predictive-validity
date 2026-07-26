# Structural evidence — versioned re-pull (real-time vs. hindsight)

**Follow-up to PR #9 / `analyses/MODEL_SYSTEM_PREDICTIVENESS.md`, "Tier 3 — structural".**
That section flagged the top TODO explicitly:

> The full per-gene versioned re-pull of dated DepMap/IMPC/OT releases — the rigorous
> treatment — is specified but not run here … It is the top follow-up.

This is that re-pull.

## The question

Melissa's structural dimensions in `preclin.v_target_evidence_wide`
— Open Targets `ot_genetic_max` / `ot_animal_model_max` / `ot_overall_max`,
IMPC `impc_n_phenotypes`, DepMap `depmap_pan_essential` — are **present-day snapshots**
applied to **historical** programs. A gene that scores well *today* may have earned that
score *after* a program's trial began, so any apparent predictive power is partly
**hindsight**. Here we pin each Phase-2+ program's structural evidence to the source
release actually available **at its `first_trial_date`**, and re-measure Relative Success
(RS) real-time vs. present-day to quantify how much of each structural signal is real
vs. retrofit.

## What builds on Melissa's constructs

- **Cohort:** same program grain and filters as `benchmark/runner.py::load_cohort` and
  the PR #9 nuance script — Phase ≥ 2, primary target, has `first_trial_date` + outcome.
  10,624 programs, 951 targets, 17.3% approved, first-trial years 2015–2025.
- **Relative Success:** her exact `rs_ci` from `analyses/nuance_drug_and_structural.py`
  — RS = P(approved | support) / P(approved | not), 2,000-sample bootstrap CIs.
- **Support thresholds:** her `v_relative_success` / analysis-view cuts —
  `ot_genetic_max≥0.3`, `ot_animal_model_max≥0.3`, `ot_overall_max≥0.5`,
  `impc_n_phenotypes≥3`, `depmap_pan_essential IS TRUE`.
- **Present-day snapshot** values read straight from `v_target_evidence_wide`.

## Sources pulled (availability + size assessed first, per the mandate)

| Source | Releases pulled | Format / size | Datable from | Note |
|---|---|---|---|---|
| **Open Targets** | 21.06, 22.06, 23.06, 24.06, **25.06** (Era B, parquet) | ~100 MB/release, 200 parts; read **remotely** with duckdb httpfs (column-projected, nothing kept on disk) | **2021-06** | scale-matched to present day |
| | 18.06, 19.06, 20.06 (Era A, legacy JSON) | 57 MB / 283 MB / **805 MB** `association_data.json.gz`, **streamed** + discarded | 2018-06 | legacy scoring — see caveat |
| **IMPC** | DR-12, 14, 16, 18, 19, 20, **21** | `phenotypeHitsPerGene.csv.gz`, ~1 MB each | **2020-10** | mouse→human by upper-case |
| **DepMap** | 20Q1, 21Q2, 22Q2, **23Q2** (figshare) | common-essentials list, ~25 KB each | **2020-05** | pan-essential only (see caveat) |

**Method (identical across every release):** per Ensembl gene, MAX over diseases of
`association…overall_indirect.score` → `ot_overall_max`; and of
`association…datatype_indirect` for `genetic_association` / `animal_model` →
`ot_genetic_max` / `ot_animal_model_max`. Present-day is measured **two ways**:
*present-self* = our own extraction of the newest release (OT 25.06 / IMPC DR-21 /
DepMap 23Q2), so real-time-vs-present-self is a clean within-method delta attributable
purely to date; *present-DB* = Melissa's `v_target_evidence_wide` at her thresholds
(the reference the task names). Each program is pinned to the newest release with
`release_date ≤ first_trial_date`; a gene absent from that release counts as *no evidence
yet*. Programs older than a source's earliest dated release are **undatable** for that
source and excluded (coverage reported below).

Reproduce:
```bash
python3 analyses/fetch_versioned_structural.py          # downloads → lean data/versioned/*.csv
DATABASE_URL=... python3 analyses/structural_versioned_repull.py
python3 analyses/plot_structural_versioned.py           # data/structural_versioned_repull.png
```

## Headline result

Scale-comparable measures (OT Era B, IMPC, DepMap). RS with 95% bootstrap CIs.

| Dimension | n datable | support prev. real-time → present | **RS real-time** | **RS present (self)** | RS present (DB) |
|---|---|---|---|---|---|
| **OT genetic** | 2,407 | 89.4% → 95.3% | **1.17** [0.89, 1.69] | **2.07** [1.26, 4.77] | 1.08 |
| OT overall | 2,407 | 78.4% → 87.7% | 1.31 [1.05, 1.69] | 1.16 [0.90, 1.59] | 0.95 |
| OT animal-model | 2,407 | 76.5% → 77.8% | 1.05 [0.86, 1.29] | 1.29 [1.04, 1.64] | 1.61 |
| IMPC KO phenotypes | 3,287 | 19.7% → 19.7% | 0.86 [0.70, 1.04] | 0.69 [0.56, 0.85] | 0.88 |
| DepMap essentiality | 3,864 | 8.9% → 8.3% | 0.57 [0.41, 0.77] | 0.63 [0.45, 0.83] | 0.28 |

**The single structural dimension that looks predictive in the present-day snapshot —
OT genetic association (RS 2.07) — is the one that does not survive dating: real-time
RS collapses to 1.17 (CI spans 1.0).** Genetic support *accretes* (89.4% → 95.3% of
these targets clear the 0.3 cut over time), and the late-added support is enriched for
eventual approvals — the textbook hindsight signature. Roughly
(2.07 − 1.17)/(2.07 − 1.0) ≈ **84% of OT-genetic's above-baseline signal is hindsight**
in this window.

**The structurally *stable* screens are not hindsight.** IMPC KO-phenotype support is
identical real-time vs. present (19.7% → 19.7%) and DepMap essentiality is near-identical
(8.9% → 8.3%); their RS is unchanged by dating. Their signal is genuinely real-time — it
is just weak (IMPC ≈ null, 0.69–0.88) or a *liability* (DepMap essential genes fail more,
0.28–0.63, echoing PR #9's 0.24). This makes mechanistic sense: a mouse-KO phenotype or a
CRISPR essentiality call is a structural fact that, once measured, does not drift; a
genetic *association* accumulates as GWAS/burden evidence piles up.

**OT overall and animal-model** show little hindsight inflation (real-time ≈ or above
present), but are weak/near-null real-time either way.

Figure: `data/structural_versioned_repull.png` (dumbbell, all five dimensions).

## Value-add / caveats (read before citing)

**What this adds over PR #9.** PR #9 could only offer a resource-existence *floor*
argument for the structural tier ("DepMap/IMPC/OT ≈ 2016; 86% of programs started ≥2016")
and left the true versioned re-pull as the open TODO. This runs it: per-gene, per-release,
date-pinned. The payoff is a *split verdict* the floor argument couldn't reach — OT
genetic is substantially hindsight; IMPC/DepMap are not.

**Honest limitations:**

1. **Resource-existence floor still bites the coverage, hard.** The dated releases only
   go back to ~2020–2021 (OT Era B 2021-06; IMPC DR-12 2020-10; DepMap 20Q1 2020-05),
   so only the **recent** slice of the cohort is datable: OT Era B **2,407 / 10,624
   programs (23%)**, IMPC 3,287 (31%), DepMap 3,864 (36%). ~86% of programs started ≥2016
   but the *resources' dated snapshots* don't reach back that far, so pre-2020 programs
   are excluded rather than mis-dated. The datable subset skews to 2021+ starts (lower
   outcome maturity), though its approval rate (17.7%) matches the full cohort (17.3%),
   so it is not badly biased *on the outcome*.
2. **OT is a weak discriminator inside a Phase-2+ cohort.** These are already-drugged
   targets, so 76–95% clear the OT cuts — the "not supported" reference group is tiny,
   which is why the OT RS CIs are wide (present-self genetic CI runs to 4.77). The
   *direction* (present ≫ real-time for genetic) is robust; the point estimate is not
   precise.
3. **Era A (2018–2020) is a scale-caveated coverage extension, not a headline.** OT's
   21.02 harmonic-sum rewrite means legacy scores are on a different scale (overall
   *median = 1.0* — saturated with ties). Prevalence-matched thresholds partly fix
   *overall* (real-time RS 2.32, n=5,945) but **genetic/animal saturate to 100% support →
   RS undefined**. Era A is reported in the CSV for transparency but should not be mixed
   with Era B.
4. **Present-DB ≠ present-self for OT.** The DB snapshot's absolute OT scores use a
   different/unknown aggregation (higher-scaled for top genes: DB overall 0.96 vs. our
   25.06 indirect 0.47 for the same gene), so *present-self* (our own 25.06 extraction) is
   the rigorous within-method comparator; *present-DB* is the external reference. Their RS
   agree in sign for every dimension.
5. **DepMap = pan-essentiality only.** `depmap_n_dep_lineages` / `depmap_mean_effect`
   require the multi-hundred-MB Chronos gene-effect matrix per release and are **out of
   scope** here (disk-discipline). Pan-essentiality is the dim the RS view thresholds on,
   and it is temporally stable — so the leakage risk it carries is inherently low. DepMap's
   inferred-common-essentials definition also changed (`Achilles_common_essentials` →
   `CRISPRInferredCommonEssentials`) between 22Q2 and 23Q2, a minor methodology seam.
6. **IMPC mouse→human = upper-case ortholog approximation**, and our
   `phenotypeHitsPerGene` "# Phenotype Hits" is a slightly narrower count than the DB's
   `impc_n_phenotypes` (support prevalence 19.7% ours vs. 31.4% DB at the same ≥3 cut) —
   the real-time-vs-present *self* comparison is internally consistent regardless.
7. **Present-day genetics/outcome benchmark is itself hindsight**, per prior-PR
   disclosures.

## Bottom line

The PR #9 leakage worry is **confirmed for the one structural signal that mattered**
(OT genetic association: ~84% hindsight in the datable window) and **refuted for the
structurally-stable screens** (IMPC, DepMap: real-time ≈ present). Net: once you require
structural evidence to have existed before the trial, none of these dimensions is a
positive real-time predictor of approval in this cohort — genetic loses its apparent
edge to dating, and IMPC/DepMap were never positive to begin with. Coverage is partial
(23–36% of programs, recent-skewed) and honestly bounded by when the resources' dated
releases begin.
