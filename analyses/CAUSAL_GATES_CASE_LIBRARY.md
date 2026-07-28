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

1. **PCSK9 vs APP vs CETP** — `PCSK9_VS_APP_CETP.md` (fig `headtohead_scorecard_clean.png`).
   The flagship head-to-head. PCSK9 (approved) is the clean genetics-to-hard-outcome
   success anchor; **APP failed at a *higher* genetic score** than PCSK9 (right node,
   wrong stage/population); **CETP failed because its biomarker (HDL) is non-causal by
   Mendelian randomization.** Establishes the frame and why BACE1 is *not* an
   evidence-matched comparator (scores below PCSK9 and is non-causal).
2. **ANGPTL3 · Factor XI · APOC3 vs PCSK9** — `GENETICS_GATES_ANGPTL3_FXI_APOC3.md`
   (figs `causal_gates_scorecard_clean.png`, `genetics_vs_outcome_clean.png`).
   Genetics guards only the early gates: **ANGPTL3** = a second genetics-driven success
   (mirrors PCSK9); **Factor XI** broke at drug-engagement (asundexian under-dosed for
   AF, not a genetics failure); **APOC3** broke at safety (thrombocytopenia; EMA yes /
   FDA no).
3. **IL-6R vs CRP** — `IL6R_CRP_CAUSAL_BIOMARKER.md` (fig `il6r_crp_causal_biomarker_clean.png`).
   A close-up on the **biomarker-causality gate.** Genetics scores CRP, IL-6R, and IL-6
   *identically* (0.70, "Weak"); only MR separates the dead-end **bystander marker (CRP)**
   from the causal, approved target (**IL-6R**). **⚠ Proposed addition / odd-one-out:**
   this is *our* proposal (not Melissa's) and a *target-selection concept* case, not a
   drug-outcome story — and IL-6R's CVD payoff is still in trials. See its doc's "Why this
   case is here — and whether to keep it" note. Melissa's call to keep or cut.

## The cross-case scorecard

`CASE_SCORECARD.md` (figs `case_scorecard_dryingpaint_clean.png` + `case_scorecard_stephengoldstein_clean.png`)
— six efficacy/safety failures (BACE1, γ-secretase/semagacestat, anti-Aβ mAbs, torcetrapib,
TGN1412, fialuridine) scored 0–3 on the preclinical rubric (mechanistic / cell / animal /
human-PD), plus a genetics column. **Near-maximal preclinical scores, all failed** — the
at-a-glance "strong evidence isn't enough" picture that the gate cases above diagnose
target-by-target. (Anti-Aβ = APP and torcetrapib = CETP also appear as gate cases above;
the scorecard is the summary view, the gate cases the mechanism.)

## How the figures relate (read this to orient)

Seven figures, **two lenses over an overlapping case set** plus an overview — none is a
subset of another. `scorecard_legend_clean.png` is the shared 0–3 / genetics-tier key.

| Figure | Cases | Scored on | Answers |
|---|---|---|---|
| `case_scorecard_dryingpaint` | 6 failures: BACE1, semagacestat, anti-Aβ (**APP**), torcetrapib (**CETP**), TGN1412/CD28, fialuridine | preclinical rubric (mech/cell/animal/PD) | strong preclinical evidence, still failed |
| `case_scorecard_stephengoldstein` | same 6 | rubric **+ genetics column** | …and genetics doesn't rescue the story |
| `headtohead_scorecard` | PCSK9, **APP**, **CETP** | causal-gate chain | 1 success vs 2 evidence-matched failures |
| `causal_gates_scorecard` | PCSK9, ANGPTL3, F11, APOC3 | causal-gate chain | genetics guards only the first ~3 gates |
| `il6r_crp_causal_biomarker` | IL-6R, CRP | the causality gate alone | a genetics-tied pair split only by MR |
| `genetics_vs_outcome` | whole library (9: APP, PCSK9, ANGPTL3, F11, BACE1, LPA, CETP, APOC3, PLA2G7) | genetic score vs. outcome | genetic *strength* doesn't separate approved from failed |

**Overlaps are deliberate, not redundant.** **APP** and **CETP** appear in both lenses —
they're the bridge (failures that are *also* evidence-matched to the PCSK9 success), so the
preclinical-rubric view shows "maxed out, still failed" and the gate view shows *which gate
broke* for the same drug. The two `case_scorecard_*` figures are the same 6 rows ±the
genetics column; the three gate scorecards are different case slices of the gate chain; and
`genetics_vs_outcome` is the single wide-angle scatter tying the whole library together.

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
they are the same Section-3 causal-gates thread. "Head-to-head" / "the head-to-head PR"
in the case docs refers to the sibling `PCSK9_VS_APP_CETP.md` in this PR.)*
