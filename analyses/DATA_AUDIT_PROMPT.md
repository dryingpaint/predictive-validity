# Data audit prompt — clinical-trial-predictors Substack (PRs #1-#4)

Paste this whole file as the prompt to a **fresh** Claude Code / Claude
session with **no prior context on this project**, and give it access to
this repo (`dryingpaint/predictive-validity` or the fork
`StephenGoldstein/predictive-validity`) plus, if available, a read-only
`DATABASE_URL` for the Neon Postgres instance backing `preclin.*`. The goal
is an independent check on data sufficiency and accuracy, not a rewrite —
run this from someone (or some session) that didn't produce the analysis.

---

## Your task

Four open PRs on this repo build the analysis + figures for a Substack post
on what data predicts clinical trial success. Your job is to **independently
verify the data underneath every quantitative claim** — not to critique
writing or design. For each claim: is the query/computation correct, is the
underlying data comprehensive enough to support it, and is the claim stated
without overreach relative to what the data actually shows?

Do not trust the committed CSVs at face value — recompute from the live
database wherever `DATABASE_URL` is available, and diff against what's
committed. If no DB access is available, fall back to static review (§5)
and say so explicitly in your report.

## The four PRs to audit

- **#1** `section-1-failure-modes` — `analyses/FAILURE_MODES.md` +
  `analyses/plot_failure_modes.py`. Source: `preclin.v_failure_taxonomy`.
  Claim: of 5,510 terminated industry Phase 1-3 trials (2015-2025),
  ~61% stopped for business/operational reasons, ~21% other/undisclosed,
  ~18% biology (efficacy/safety/PK).
- **#2** `section-2-predictive-power` — `analyses/PREDICTIVE_POWER.md` +
  `analyses/plot_predictive_power.py` + `analyses/genetics_dose_response.py`.
  Three sub-claims:
  - Dose-response: binning Phase 2+ target-indication pairs by the repo's
    `genetic_only_v1` scorer (`benchmark/scorers_rule_based.py`,
    `scorer_genetic_only`) into None/Weak/Moderate/Strong yields
    8% / 19% / 22% / 44% approval.
  - Ablation: leave-one-category-out logistic regression
    (`analyses/ablation.py`, numbers also in `RESULTS.md`) — full-model
    AUC 0.829, genetics removal costs -17.7pp, next largest is context
    at -1.8pp, cell and animal literature ~0.
  - Per-dimension Relative Success chart from `preclin.v_relative_success_clean`,
    LLM-extracted literature dimensions (lines C/D/E) excluded as
    leakage-prone.
- **#3** `section-3-case-scorecard` — `analyses/CASE_SCORECARD.md` +
  `analyses/plot_case_scorecard.py`. Six case studies from
  `CASE_STUDIES.md` (BACE1, semagacestat, anti-Aβ mAbs, torcetrapib,
  TGN1412, fialuridine), scored 0-3 on mechanistic/cell/animal/PD, plus a
  genetics column added from `genetic_only_v1` applied to each target via
  `preclin.v_target_evidence_wide`: APP 1.6 (Strong), BACE1/PSEN1/CD28 1.0
  (Moderate), CETP 0.7 (Weak).
- **#4** `genetics-mirror-case-study` — `analyses/GENETICS_MIRROR.md` +
  `analyses/plot_genetics_mirror.py`. Claims PCSK9 and semaglutide are
  *not* good "succeeded on thin evidence" examples (genetics precedes/drove
  PCSK9's program; semaglutide inherited an already-validated GLP1R target),
  and substitutes exenatide (GLP1R, 1990s program, scored genetics=0
  because GWAS didn't exist yet, mechanistic=2/cell=2/animal=3/PD=3),
  contrasted against the anti-Aβ mAb case from #3. This PR's evidence
  scores are **not** DB-derived — they're historical/literature claims with
  citations in the doc (Cohen/Hobbs 2003 & Cohen 2006 for PCSK9; Eng 1992,
  Thorens 1992, Gutniak 1992, Nauck 1993 for exenatide). Verify the
  citations actually say what the doc claims, and check the dates against
  primary sources, not just secondary summaries.

## What "comprehensive and accurate" means here — check specifically

1. **Coverage, not just headline numbers.** For every dimension used in a
   claim (ClinGen, Mendelian, OT-genetic, OT-somatic, Nelson tier, cell/
   animal/PD lines), what fraction of the relevant cohort has that field
   populated? A statistic computed on a well-populated field means
   something different from one computed on a field that's 90% null. Flag
   any headline number built on a dimension with <50% coverage without that
   caveat being stated.
2. **Null handling.** Confirm nulls are excluded from denominators (not
   silently coded as "0"/absent) wherever that matters — an unscored
   target and a genetics-absent target are not the same thing, and
   conflating them was a real bug caught earlier in this project (see
   git history / PR discussion if visible). Check every RS/ablation/dose-
   response computation for this.
3. **Small-n bins.** Any bin (e.g. genetics "None" or "Strong" tier, any
   per-modality or per-TA stratum) under ~30 pairs should have its n
   reported alongside the rate, and conclusions shouldn't lean on bins
   that small without a CI.
4. **Sample overlap / leakage.** For the ablation AUC (0.829) — is this
   the retrospective number or the time-machine (pre-2019 train) backtest
   number (0.77 per project notes)? If the PR cites the retrospective
   number as if it were predictive, that's a real overclaim to flag.
   Check whether target-indication pairs used for scoring case studies
   (e.g., CETP, APP) overlap with pairs used to fit `genetic_only_v1`'s
   calibration.
5. **Static review (fallback, if no `DATABASE_URL`).** Read
   `benchmark/scorers_rule_based.py::scorer_genetic_only` and confirm the
   worked genetics values quoted in PR #3 and #4's docs are arithmetically
   correct given the formula (score thresholds, sigmoid calibration,
   tier labels) — recompute by hand from whatever raw feature values are
   stated or discoverable. Read `preclin` view definitions if accessible
   in a `sql/` or migrations directory and confirm the docs' description
   of each view (`v_failure_taxonomy`, `v_relative_success_clean`,
   `v_target_evidence_wide`) matches what the SQL actually computes.
6. **Historical claims (#4 specifically).** Independently verify: (a)
   Cohen/Hobbs 2003 and Cohen et al. 2006 predate the first anti-PCSK9
   antibody IND filings; (b) exenatide's IND/program start date and
   whether any GWAS technology existed before it; (c) that GLP1R-specific
   genetic associations postdate exenatide's approval, not just T2D GWAS
   in general (the claim is about the *specific gene*, not the disease).
7. **Overreach in prose.** Flag any sentence in the four `.md` docs that
   states a causal claim ("X drives Y", "X is why Y failed") where the
   underlying data only supports an associational one, and any place a
   single case study is generalized beyond n=1.

## Deliverable

A findings report, one section per PR (#1-#4), each finding tagged:
- **CONFIRMED** — you recomputed and it doesn't match, or found a real gap
- **PLAUSIBLE CONCERN** — couldn't fully verify (e.g., no DB access) but
  there's a specific reason to doubt it
- **NO ISSUE** — checked and it holds

End with an overall verdict: is the current data sufficient to support the
claims as written in each of the four docs, and if not, what specific
additional pull or caveat would fix it. Do not soften findings to be
diplomatic — this is explicitly meant to be a skeptical, independent pass;
Stephen and Melissa want the strongest available counter-check before
publishing, not reassurance.
