# Case-study scorecard (Section 3)

One figure for the "strong preclinical evidence, still failed" case studies in
`CASE_STUDIES.md` — `case_scorecard_stephengoldstein` (annotated + `_clean`
publication-grade, 600-dpi PNG + editable SVG in `data/`): Melissa Du's original rubric
(Mechanistic / Cell-pathway / Animal in-vivo / Human PD) **with a Genetics column added**.
*(The rubric-only "dryingpaint" twin was retired 2026-07-29 — the genetics-column version is
strictly more informative. `plot(with_genetics=False)` still generates it if ever wanted.)*

Rows are split into **efficacy failures** (BACE1, γ-secretase, anti-Aβ, torcetrapib,
**darapladib**) and **safety / species-specific failures** (TGN1412, fialuridine).

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
| Darapladib (PLA2G7) | 0.5 | Weak |
| Fialuridine (HBV polymerase) | — | n/a (viral) |

**Darapladib (PLA2G7 / Lp-PLA2), added 2026-07-29** — the cleanest modern efficacy failure of
this kind: maxed preclinical evidence (mechanism, structure, atherosclerosis models, human
Lp-PLA2 PD all 3/3), Lp-PLA2 fully engaged, yet STABILITY and SOLID-TIMI 52 showed **no
reduction in cardiovascular events** — because Lp-PLA2 is a non-causal bystander (MR), the
same "wrong causal lever" failure as CETP. Genetics weak (0.5).

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
> or the biomarker is a *non-causal bystander* — as with **CETP** (HDL not causal by MR;
> benefit was LDL) and **darapladib** (Lp-PLA2 engaged, no CV benefit — Lp-PLA2 not causal).

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

## Safety failures — was the target hypothesis actually right?

A safety failure kills the *drug*; it does not, by itself, indict the *target*. For both
safety cases here the underlying biology was later **validated** — the failure was the
molecule and the dose, not the hypothesis. That is the mirror image of the efficacy
failures above, where the causal hypothesis itself was often wrong (CETP / darapladib / CRP:
biomarker non-causal; amyloid: right node, wrong stage). Worth stating explicitly, because
"strong preclinical evidence, still failed" means something different in each bucket.

- **TGN1412 (CD28 superagonist) — target validated; a dose + species-translation failure.**
  The 2006 first-in-human trial caused a near-fatal cytokine storm in all six volunteers
  (Suntharalingam et al., *NEJM* 2006). The lesson is *not* that CD28 costimulation is a bad
  target: (1) the tox species (cynomolgus macaque) structurally could not predict it —
  macaque CD4⁺ effector-memory T cells are **CD28-negative** where the human cells are
  **CD28-positive** (a 4-aa species difference incl. G68E in the binding loop; Eastwood et
  al., *Br J Pharmacol* 2010, PMID 20880392), so the superagonist engaged a human cell
  population absent from the model; and (2) the *same antibody*, redeveloped as **TAB08 /
  theralizumab** at about 1000× lower dose, selectively activates regulatory T cells (IL-10
  signature) with no cytokine storm and re-entered rheumatoid-arthritis trials (Tabares et
  al., *Eur J Immunol* 2014, PMID 24374661; Hünig, *FEBS J* 2016). The Treg-activation-via-
  CD28 hypothesis held; the first-in-human dose and the animal model did not.
- **Fialuridine (HBV polymerase) — target validated; a molecule-specific mitochondrial
  toxicity.** The 1993 NIH trial caused fatal hepatic failure and lactic acidosis (5 of 15
  died; 2 more survived only after liver transplant; McKenzie et al., *NEJM* 1995). Yet HBV
  polymerase is arguably **the most validated target in hepatitis B** — the nucleos(t)ide-
  analog class (lamivudine, entecavir, tenofovir) is the backbone of modern HBV therapy.
  Fialuridine failed on a molecule-specific liability: its triphosphate inhibits
  **mitochondrial DNA polymerase-γ** and is incorporated into mtDNA, depleting it and
  destroying mitochondria (PMID 8622980) — a chemistry problem the later, mitochondrially
  gentler analogs do not share. Right target, wrong molecule.

**So the two failure modes sit on opposite sides of the target-validity question:** efficacy
failures frequently indict the *biology* (biomarker not causal, or right node / wrong stage);
these safety catastrophes indict the *molecule / dose / model*, with the target hypothesis
vindicated by later drugs. (Hence the visual split in the scorecard — but the deeper reason
is this validity asymmetry, not just "safety vs efficacy.")

## Scope & reproduce

Most of these trials predate the 2015–2025 benchmark window, so the mechanistic / cell /
animal / PD scores are curated (from `CASE_STUDIES.md`); the **genetics values are live
from the DB**. Reproduce: `python3 analyses/plot_case_scorecard.py` (writes
`data/case_scorecard.csv` + the annotated & `_clean` variants of the single scorecard;
scores baked in, no DB needed to plot — the genetic_only_v1 values were pulled once from
`v_target_evidence_wide`).
