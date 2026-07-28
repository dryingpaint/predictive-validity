# Case-study scorecard (Section 3)

Figures for the "strong preclinical evidence, still failed" case studies in
`CASE_STUDIES.md`. Two versions, each annotated + `_clean` (publication-grade),
600-dpi PNG + editable SVG, in `data/`:

- **`case_scorecard_dryingpaint`** — Melissa Du's (@dryingpaint) **original rubric** (Mechanistic /
  Cell-pathway / Animal in-vivo / Human PD). All near-maximal, all failed.
- **`case_scorecard_stephengoldstein`** — the same, **with a Genetics column added** (@StephenGoldstein).

Rows are split into **efficacy failures** (BACE1, γ-secretase, anti-Aβ, torcetrapib)
and **safety / species-specific failures** (TGN1412, fialuridine).

## What this adds to CASE_STUDIES.md

The original rubric scores mechanistic / cell / animal / PD but **omits human
genetics** — the category the benchmark finds most predictive (see `RESULTS.md`
ablation and `analyses/PREDICTIVE_POWER.md`). Genetics here is scored with the repo's
own `genetic_only_v1` scorer (`benchmark/scorers_rule_based.py`) at each target's
**lead indication**, which includes the per-indication Nelson-tier term. (Corrected
2026-07-26: an earlier version scored from `v_target_evidence_wide` alone, which omits
Nelson — APP was thereby understated 1.6→**1.9**; BACE1/PSEN1/CD28/CETP carry no Nelson
tier, so they are unchanged.)

| Drug (target) | genetic_only_v1 | tier |
|---|---|---|
| Anti-Aβ mAbs (APP) | 1.9 | Strong |
| BACE1 inhibitors (BACE1) | 1.0 | Moderate |
| γ-secretase / semagacestat (PSEN1) | 1.0 | Moderate |
| TGN1412 (CD28) | 1.0 | Moderate |
| Torcetrapib (CETP) | 0.7 | Weak |
| Fialuridine (HBV polymerase) | — | n/a (viral) |

## How to read the scores

`scorecard_legend_clean.png` (`analyses/plot_scorecard_legend.py`) is the key for the
0–3 evidence cells and the genetics tier. Each evidence column is 0–3 on directness
(0 none → 3 direct & reproduced; the 2-vs-3 line is whether the evidence is direct, e.g.
Mechanistic 3 = pharmacology + solved structure vs 2 = pharmacology without structure).
Genetics is `genetic_only_v1` mapped to the same scale — Absent (0) / Weak (0.1–0.9) /
Moderate (1.0–1.3) / Strong (≥1.4). The numeral is in every cell, so scores read
independent of colour.

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

**Hindsight caveat (read alongside the genetics-mirror PR).** The genetics column here is
scored from **present-day** (2026) DB values, not time-sliced to what was known when these
1990s–2000s programs started. That is deliberate — the point is "*even knowing everything we
know today*, genetics didn't save these programs" — but it is the same present-day-scoring
practice the companion `GENETICS_MIRROR.md` treats as hindsight leakage and specifically
avoids for exenatide. The two are consistent (there, the question is whether genetics that
*didn't exist yet* would be credited today; here, the genetics is real and long-established),
but since the PRs are meant to be read together, the different standard is called out rather
than left implicit.

The two **safety / species-specific** failures (TGN1412, fialuridine) are a different
failure mode entirely — human-vs-animal pharmacology, not predictable from any evidence
category — hence the visual split.

## Scope & reproduce

Most of these trials predate the 2015–2025 benchmark window, so the mechanistic / cell /
animal / PD scores are curated (from `CASE_STUDIES.md`); the **genetics values are live
from the DB**. Reproduce: `python3 analyses/plot_case_scorecard.py` (writes
`data/case_scorecard.csv` + the four figure variants; scores baked in, no DB needed to
plot — the genetic_only_v1 values were pulled once from `v_target_evidence_wide`).
