# Case-study scorecard (Section 3)

Figures for the "strong preclinical evidence, still failed" case studies in
`CASE_STUDIES.md`. Two versions, each annotated + `_clean` (publication-grade),
600-dpi PNG + editable SVG, in `data/`:

- **`case_scorecard_hers`** — the six cases on the **original rubric** (Mechanistic /
  Cell-pathway / Animal in-vivo / Human PD). All near-maximal, all failed.
- **`case_scorecard_genetics`** — the same, **with a Genetics column added**.

Rows are split into **efficacy failures** (BACE1, γ-secretase, anti-Aβ, torcetrapib)
and **safety / species-specific failures** (TGN1412, fialuridine).

## What this adds to CASE_STUDIES.md

The original rubric scores mechanistic / cell / animal / PD but **omits human
genetics** — the category the benchmark finds most predictive (see `RESULTS.md`
ablation and `analyses/PREDICTIVE_POWER.md`). Genetics here is scored from the DB
using the repo's own `genetic_only_v1` scorer (`benchmark/scorers_rule_based.py`) on
each target (`v_target_evidence_wide`, target-level):

| Drug (target) | genetic_only_v1 | tier |
|---|---|---|
| Anti-Aβ mAbs (APP) | 1.6 | Strong |
| BACE1 inhibitors (BACE1) | 1.0 | Moderate |
| γ-secretase / semagacestat (PSEN1) | 1.0 | Moderate |
| TGN1412 (CD28) | 1.0 | Moderate |
| Torcetrapib (CETP) | 0.7 | Weak |
| Fialuridine (HBV polymerase) | — | n/a (viral) |

## The honest takeaway (which the genetics column makes visible)

Adding genetics does **not** simply show "these failed because they lacked genetics."
The amyloid targets *have* genetic support (APP strong; BACE1/PSEN moderate — familial-AD
Mendelian) and still failed. So the lesson is sharper and more defensible:

> **Human genetics improves the odds but is not sufficient.** A genetically supported
> target can still fail if the causal hypothesis is wrong (Aβ→cognition), the node is
> pleiotropic (BACE1 beyond APP; γ-secretase / Notch), the stage is too late (anti-Aβ),
> or the genetics is *misread* — as with **CETP**, where LoF genetics existed but
> Mendelian randomization later showed HDL is not causal (the benefit was LDL).

This tempers the Section-2 "genetics leads" message rather than overclaiming it.

The two **safety / species-specific** failures (TGN1412, fialuridine) are a different
failure mode entirely — human-vs-animal pharmacology, not predictable from any evidence
category — hence the visual split.

## Scope & reproduce

Most of these trials predate the 2015–2025 benchmark window, so the mechanistic / cell /
animal / PD scores are curated (from `CASE_STUDIES.md`); the **genetics values are live
from the DB**. Reproduce: `python3 analyses/plot_case_scorecard.py` (writes
`data/case_scorecard.csv` + the four figure variants; scores baked in, no DB needed to
plot — the genetic_only_v1 values were pulled once from `v_target_evidence_wide`).
