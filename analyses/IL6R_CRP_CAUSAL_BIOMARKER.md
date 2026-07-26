# IL-6R vs CRP — the gate that separates a target from a marker

A causal-gates case study for the "which biomarker is causal for the outcome"
slot in the post. Companion to `analyses/PCSK9_VS_APP_CETP.md` (PR #6) and
`CASE_STUDIES.md` (PR #8); it reuses their gate chain verbatim:

> genetics → target→biomarker → **biomarker-causal-for-outcome** → drug engages
> target → safety → approval.

The head-to-head there (PCSK9/APP/CETP) used the causal gate to explain
*failures* of well-supported programs. This note runs the same gate on the
cleanest textbook pair in cardiovascular biology: two inflammation biomarkers,
both associated with CVD, both with human genetic support — where only one is
*causal*, and the causal one is the drug target.

## The punchline (and the honest part first)

**The repo's own genetics scorer cannot tell these three apart.**
`genetic_only_v1` (from `benchmark/scorers_rule_based.py::scorer_genetic_only`)
scores CRP, IL-6R, and IL-6 at the **same raw genetic score, 0.70 ("Weak")** —
identical `predicted_p_approval` = 0.273. All three have a Mendelian association,
an Open Targets genetic score ≥ 0.70, and (for IL-6R/IL-6) a large GWAS hit
count. On genetics alone they are indistinguishable.

(One caveat: this exact three-way tie is a current-DB snapshot. IL-6's Mendelian count
is 4 — one below the ≥5 threshold that would add +0.5 and push it to Moderate — so a data
refresh could break the *precise* 0.70/0.70/0.70. The point that genetics alone can't
cleanly separate a non-causal bystander marker from a validated causal target is robust
to that; the numbers just wouldn't be identical to the digit.)

That is the point, not a weakness of the exercise: **genetics gets you to the
door for all three; it is the *biomarker-causal-for-outcome* gate — answerable
only with Mendelian randomisation, not with an aggregate genetic score — that
splits the viable target (IL-6R) from the dead end (CRP).** MR is the tool that
does what the genetic score structurally cannot.

## The scorecard

Rows = the three players; columns = the gates. Colour = holds / breaks.
Figure: `data/il6r_crp_causal_biomarker_clean.png` (editable `.svg`). Regenerate
with `python3 analyses/il6r_crp_causal_biomarker.py` (re-pulls genetics from
`preclin.v_target_evidence_wide` via the repo scorer if `DATABASE_URL` is set;
otherwise uses the last-pulled values baked into the script). Provenance CSV:
`data/il6r_crp_causal_biomarker.csv`.

| Gate | CRP | IL-6R | IL-6 |
|---|---|---|---|
| **Human genetics** (`genetic_only_v1`) | Weak **0.70** | Weak **0.70** | Weak **0.70** |
| Target → biomarker | *is* the marker | validated (→ CRP/IL-6) | validated (→ CRP) |
| **Biomarker causal for outcome? (MR)** | **NO** | **YES** | **YES (axis)** |
| Drug engages target | no CV agent | yes (tocilizumab; ziltivekimab) | yes (ziltivekimab) |
| Safety | n/a | acceptable (approved in RA) | TBD (outcomes trial) |
| Approval / outcome | **dead end** | **APPROVED** (RA); CV: ZEUS ph3 | in dev (RESCUE → ZEUS) |

Every program clears genetics and (for the two ILs) target→biomarker and drug
engagement. They diverge at exactly one gate, and CRP dies there.

## The one gate that matters here — Mendelian randomisation

MR uses a germline variant as a lifelong "natural experiment" for perturbing one
node, then asks whether that perturbation moves the *hard outcome* (coronary
heart disease), not just a correlated marker.

**IL-6R passes.** The common coding variant *rs2228145* (Asp358Ala) partially
mimics pharmacological IL-6R blockade. Carriers show a downstream inflammatory
profile (lower CRP, lower fibrinogen) **and** a lower risk of coronary heart
disease — a dose-response consistent with IL-6R signalling being causal for CHD.
Two companion 2012 *Lancet* analyses established this:

- The IL6R Genetics Consortium / Mendelian Randomisation Analysis — *rs2228145*
  associates with lower CHD risk, mirroring IL-6R inhibition. **PMID 22421340**
  ("The interleukin-6 receptor as a target for prevention of coronary heart
  disease: a mendelian randomisation analysis", *Lancet* 2012).
- The collaborative meta-analysis of the IL-6R pathway in CHD across 82 studies.
  **PMID 22421339** ("Interleukin-6 receptor pathways in coronary heart disease:
  a collaborative meta-analysis of 82 studies", *Lancet* 2012).

**CRP fails.** Genetic instruments that raise CRP do **not** raise CHD / ischemic
vascular disease risk — CRP is a bystander marker of the inflammatory process,
downstream of the causal IL-6 axis, not on the causal path itself:

- **PMID 21325005** — C Reactive Protein Coronary Heart Disease Genetics
  Collaboration (CCGC), individual-participant MR: CRP-raising alleles not
  associated with CHD ("Association between C reactive protein and coronary heart
  disease: mendelian randomisation analysis based on individual participant
  data", *BMJ* 2011).
- **PMID 19567438** — Elliott et al., CRP loci vs CHD risk ("Genetic Loci
  associated with C-reactive protein levels and risk of coronary heart disease",
  *JAMA* 2009).
- **PMID 18971492** — Zacho et al., genetically elevated CRP and ischemic
  vascular disease ("Genetically elevated C-reactive protein and ischemic
  vascular disease", *N Engl J Med* 2008).

So: same disease, same "inflammation biomarker associated with CVD" story, same
genetic-support checkbox — **opposite answers at the causal gate.** That single
gate is the difference between a drug target and a lab value.

## Clinical corroboration — the axis is causal; CRP is just how you read it

The drugs close the loop the way the genetics predicts:

- **The inflammatory axis is causal.** CANTOS — canakinumab (anti-IL-1β, upstream
  of IL-6) — cut recurrent cardiovascular events, the first proof that lowering
  inflammation *per se* reduces CV risk. **PMID 28845751** ("Antiinflammatory
  Therapy with Canakinumab for Atherosclerotic Disease", *N Engl J Med* 2017).
- **Hitting IL-6 directly works on the biomarkers as designed.** RESCUE —
  ziltivekimab (anti-IL-6) — produced large, dose-dependent reductions in hsCRP
  and other inflammatory markers in high-CV-risk CKD patients, and launched the
  ZEUS phase-3 cardiovascular-outcomes trial. **PMID 34015342** ("IL-6 inhibition
  with ziltivekimab in patients at high atherosclerotic risk (RESCUE): a
  double-blind, randomised, placebo-controlled, phase 2 trial", *Lancet* 2021).
- **No CRP-lowering agent has ever improved CV outcomes.** Consistent with CRP
  being a readout, not a lever. You lower CRP *by* hitting the causal node
  (IL-1/IL-6/IL-6R); lowering CRP is not itself a therapeutic mechanism.

## The database corroborates the story on its own

Pulled from `preclin.v_target_evidence_wide` (target_ids IL6R 77 / IL6 406 /
CRP 1124; full row in the CSV):

- **Causal-disease pleiotropy.** IL6R `n_causal_diseases` = **3**; CRP = **0**.
  The repo's own evidence layer already "knows" IL-6R anchors causal disease
  links and CRP anchors none.
- **Constraint / LoF tolerance.** CRP `gnomad_loeuf` = **1.93** — extremely
  loss-of-function-*tolerant*, exactly what you expect of a passive downstream
  acute-phase marker that the organism can lose without consequence. IL-6R
  (0.965) and IL-6 (0.881) sit in the ordinary range.
- **Animal model.** IL6R `ot_animal_model_max` = 0.77, IL6 = 0.65; CRP has none.

These are *corroborating texture*, not the load-bearing evidence — the causal
call rests on the human MR papers above — but it's notable that the aggregate
genetic *score* washes the distinction out while two of the raw components
(`n_causal_diseases`, LOEUF) preserve it.

## Value-add / caveats (read this before quoting the piece)

- **Marginal on novelty; strong as a teaching case.** IL-6R-vs-CRP is the
  canonical MR example — it is *in the MR textbooks*. We are not discovering that
  IL-6R is causal and CRP isn't. The value here is (a) fitting a famous, clean
  example into this repo's exact causal-gates rubric, and (b) the genuinely
  useful methodological demonstration below.
- **The real finding is a scorer limitation, honestly surfaced.** `genetic_only_v1`
  scores CRP = IL-6R = IL-6 = 0.70. A genetics-only model — the kind the whole
  benchmark is built to test — would rank a non-causal bystander marker
  identically to a validated, approved-in-RA drug target. That is a concrete,
  reproducible illustration of *why* the "biomarker causal for outcome" gate has
  to be a separate step: **no aggregate genetic score can substitute for MR.**
  This is the same scorer-calibration point flagged in PR #6 (the PCSK9/CETP
  ClinGen gap), from the other direction.
- **"Weak 0.70" is the scorer's read, and it slightly *undersells* all three.**
  As in the CETP note, `genetic_only_v1` undervalues strong quantitative-trait /
  MR genetics (it has no term for "a variant that mimics the drug and tracks the
  hard outcome"). IL-6R's genetics is, in substance, strong and *correctly*
  interpreted; the score just can't express that.
- **Hindsight / present-day.** All genetics is pulled 2026 present-day — same
  disclosure as PRs #3, #4, #6. This is "even knowing what we know now, the
  genetic score can't separate them," not a time-frozen prediction.
- **IL-6 (the ligand) leans on the axis, not its own instrument.** The cleanest
  MR instrument is *rs2228145* in *IL6R*. IL-6's "causal" call rides the shared
  IL-6/IL-6R signalling axis plus the anti-IL-6 clinical data (RESCUE), and its
  CV-outcome evidence is still phase-3-pending (ZEUS). Marked "in dev / TBD"
  rather than a settled win — stated honestly on the card.

## Sources (verified against PubMed by PMID + title, 2026-07-25)

| PMID | Claim it supports |
|---|---|
| 22421340 | IL-6R MR — *rs2228145* mimics IL-6R blockade, lower CHD risk (*Lancet* 2012) |
| 22421339 | IL-6R pathway in CHD, 82-study collaborative meta-analysis (*Lancet* 2012) |
| 21325005 | CRP **not** causal for CHD — CCGC IPD MR (*BMJ* 2011) |
| 19567438 | CRP loci vs CHD risk — Elliott et al. (*JAMA* 2009) |
| 18971492 | Genetically elevated CRP not causal for ischemic vascular disease — Zacho et al. (*NEJM* 2008) |
| 28845751 | CANTOS — canakinumab cut CV events; inflammation axis causal (*NEJM* 2017) |
| 34015342 | RESCUE — ziltivekimab (anti-IL-6) lowered inflammation, launched ZEUS (*Lancet* 2021) |
