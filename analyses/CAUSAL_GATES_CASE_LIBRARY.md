# Causal-gates case library (Section 3)

The case studies behind the Section-3 argument: **strong evidence — including strong
human genetics — does not guarantee a drug works.** All are organized around one model,
the chain of gates a program must clear:

> genetics → target→biomarker → **biomarker causal for the outcome** → drug engages
> target adequately → safety → approval

**Human genetics guards only the first ~3 gates.** The downstream gates (engagement,
safety, and above all whether the biomarker is *causal* for the human endpoint) are
where genetically-validated targets still die. Each case below is a gate illustration.

Read the shared scorecard key first: **`scorecard_legend_clean.png`** (the 0–3 evidence
scale + the `genetic_only_v1` tiers). Scores are canonical `genetic_only_v1` at each
target's lead indication (present-day — hindsight caveat noted in each case doc).

## The cases

1. **PCSK9 vs APP vs CETP** — `PCSK9_VS_APP_CETP.md`. The flagship contrast: PCSK9 (approved)
   is the clean genetics-to-hard-outcome success anchor; **APP failed at a *higher* genetic
   score** than PCSK9 (right node, wrong stage/population); **CETP failed because its
   biomarker (HDL) is non-causal by Mendelian randomization.** Establishes the frame and why
   BACE1 is *not* an evidence-matched comparator. *(These three are now rows in the unified
   `causal_gates_scorecard` — the former standalone head-to-head figure was folded in
   2026-07-29.)*
2. **ANGPTL3 · Factor XI · APOC3 vs PCSK9** — `GENETICS_GATES_ANGPTL3_FXI_APOC3.md`
   (figs `causal_gates_scorecard_clean.png`, `genetics_vs_outcome_clean.png`).
   Genetics guards only the early gates: **ANGPTL3** = a second genetics-driven success
   (mirrors PCSK9); **Factor XI** broke at drug-engagement (asundexian under-dosed for
   AF, not a genetics failure); **APOC3** broke at safety (thrombocytopenia; EMA yes /
   FDA no).
3. **IL-6R vs CRP** — `IL6R_CRP_CAUSAL_BIOMARKER.md`, now **tied to specific drug candidates
   and folded into the `causal_gates_scorecard`** (2026-07-29): **tocilizumab** (anti-IL-6R,
   approved in RA) and **ISIS-CRPRx** (anti-CRP antisense). This turns it from a
   target-selection concept case into two ordinary drug-outcome rows that fold in cleanly.
   It's now the sharpest row-pair in the library: genetics scores IL-6R and CRP *identically*
   (0.70, "Weak"), **both drugs hit their biomarker** (tocilizumab blocks IL-6R; ISIS-CRPRx
   cut CRP ~77%, PMID 25885521) — they split at exactly one gate (biomarker-causal-by-MR) and
   get **opposite outcomes** (IL-6R approved; CRP no clinical benefit).

## The cross-case scorecard

`CASE_SCORECARD.md` (fig `case_scorecard_stephengoldstein_clean.png`) — **seven**
efficacy/safety failures (BACE1, γ-secretase/semagacestat, anti-Aβ mAbs, torcetrapib,
**darapladib**, TGN1412, fialuridine) scored 0–3 on the preclinical rubric (mechanistic /
cell / animal / human-PD), plus a genetics column. **Near-maximal preclinical scores, all
failed** — the at-a-glance "strong evidence isn't enough" picture that the gate cases above
diagnose target-by-target. (Anti-Aβ = APP and torcetrapib = CETP also appear as gate cases;
the scorecard is the summary view, the gate cases the mechanism. The rubric-only
"dryingpaint" twin was retired 2026-07-29 — the genetics-column version is strictly more
informative.)

## How the figures relate (read this to orient)

**Four figures** after the 2026-07-29 consolidation. `scorecard_legend_clean.png` is the
shared 0–3 / genetics-tier key.

| Figure | Cases | Scored on | Answers |
|---|---|---|---|
| `case_scorecard_stephengoldstein` | 7 failures: BACE1, semagacestat, anti-Aβ (**APP**), torcetrapib (**CETP**), **darapladib**, TGN1412/CD28, fialuridine | preclinical rubric (mech/cell/animal/PD) **+ genetics** | strong preclinical evidence, still failed — and genetics doesn't rescue it |
| `causal_gates_scorecard` | 8: PCSK9, ANGPTL3, **tocilizumab** (approved) · **APP**, **CETP**, F11, APOC3, **ISIS-CRPRx** (failed/mixed) | causal-gate chain (6 gates) | which gate breaks — APP above PCSK9's score; and the IL-6R/CRP pair split only at the causality gate |
| `genetics_vs_outcome` | whole library (12: APP, PCSK9, ANGPTL3, F11, BACE1, **semagacestat**, LPA, CETP, **tocilizumab/IL6R**, **ISIS-CRPRx/CRP**, APOC3, PLA2G7) | genetic score vs. outcome | genetic *strength* doesn't separate approved from failed (three programs sit at 0.7 — one approved, two failed) |
| `scorecard_legend` | — | — | the shared 0–3 / tier key |

**Overlaps are deliberate, not redundant.** **APP** and **CETP** appear in both the case
scorecard (as "maxed out, still failed") and the gate scorecard (showing *which gate broke*).
`genetics_vs_outcome` is the single wide-angle scatter tying the whole library together. The
former head-to-head figure was folded into the gate scorecard; the IL-6R/CRP case was tied to
specific drug candidates (tocilizumab / ISIS-CRPRx) and folded in as two rows — keeping the set
to four figures.

## The through-line

The **biomarker-causality gate** is the sharpest recurring divider across the library:

- **Fail it:** CETP (HDL) and CRP (an inflammation marker) — genetics present, biomarker
  moved as designed, but the biomarker is a *bystander*, not on the causal path (MR).
- **Pass it:** PCSK9 (LDL) and IL-6R (IL-6 signaling) — the genetics validated the chain
  all the way to the hard clinical outcome.

And genetic *strength* does not decide the outcome: **APP failed at a higher
`genetic_only_v1` than PCSK9 and ANGPTL3 were approved at.** The score measures genetic
*support*, not therapeutic tractability — the downstream gates do the deciding.

*(Consolidated 2026-07-27 from the former standalone PRs for PCSK9/APP/CETP and IL-6R/CRP;
they are the same Section-3 causal-gates thread. Figure set consolidated to four 2026-07-29 —
head-to-head folded into `causal_gates_scorecard`; IL-6R/CRP tied to specific drug candidates
(tocilizumab / ISIS-CRPRx) and folded into the gate scorecard as two rows; the rubric-only
case-scorecard twin dropped; and darapladib added to the case scorecard. "Head-to-head" in the
case docs now refers to the PCSK9/APP/CETP rows of the unified gate scorecard.)*
