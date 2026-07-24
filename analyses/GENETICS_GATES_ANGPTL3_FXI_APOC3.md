# Genetics guards the first gates — ANGPTL3, Factor XI, APOC3 vs. PCSK9

Extends the PCSK9/APP/CETP head-to-head. That note showed genetics can be strong
and a program still fail *on efficacy* (APP: right node, wrong stage; CETP:
biomarker misread). This one adds three cases that sharpen a complementary point:
**a drug program has to clear a chain of gates, and human genetics only guards the
first three** (is the target genetically implicated → does modulating it move a
biomarker → is that biomarker causal for the outcome). Two further gates —
**does the drug actually engage the target adequately** (dose, indication) and
**is it safe/tolerable** — are where genetically-validated targets still die, and
genetics says nothing about them.

Adds a **second success** alongside PCSK9 (ANGPTL3), and two "genetics held, a
later gate broke" cases (Factor XI, APOC3).

All scores are `genetic_only_v1` on `preclin.v_target_evidence_wide`, present-day
(2026) — **hindsight**, same caveat as the case-scorecard and genetics-mirror PRs.

## Figures

- **`data/causal_gates_scorecard_clean.png`** (editable `.svg`) — PCSK9, ANGPTL3,
  Factor XI, APOC3 across six gates. All four clear genetics + causal; PCSK9 and
  ANGPTL3 clear all six (approved); Factor XI breaks at drug-engagement; APOC3
  breaks at safety.
- **`data/genetics_vs_outcome_clean.png`** — genetic score for the whole case
  library, coloured by outcome. The approvals sit *among* the failures at equal or
  lower score (APP failed at a **higher** score than either approval): genetic
  strength is necessary-ish but does not decide the outcome.

Regenerate: `python3 analyses/plot_genetics_gates.py` (scores baked in; no DB
needed to plot). Supporting data: `data/genetics_gates_cases.csv`.

## ANGPTL3 / evinacumab — a second PCSK9-pattern success

**`genetic_only_v1` = 1.3 (Moderate), same as PCSK9.** Loss-of-function carriers
have familial combined hypolipidemia — low LDL and triglycerides — and are
protected from coronary artery disease; genetic *and* pharmacologic inactivation
both point the same way (according to PubMed, Dewey et al., *NEJM* 2017;
[DOI](https://doi.org/10.1056/NEJMoa1612790)). Evinacumab (an anti-ANGPTL3 mAb) was
**FDA-approved 11 Feb 2021 (Evkeeza)** for homozygous familial hypercholesterolemia
on the ELIPSE HoFH trial (~49% LDL reduction; Raal et al., *NEJM* 2020). It works
even in receptor-negative HoFH, where LDL-receptor-dependent drugs can't — an LDL
pathway the genetics predicted. **Lesson: the lipid-LOF-genetics → approval pattern
is not a PCSK9 one-off; it reproduces.** This is the honest "possible 2nd success
example" to sit beside PCSK9.

## Factor XI / asundexian — genetics held, the drug (or dose) didn't

**`genetic_only_v1` = 1.3 (Moderate), same as PCSK9 — and ClinGen-curated.** The
genetic rationale is textbook: congenital Factor XI deficiency (hemophilia C)
protects against venous thrombosis and ischemic stroke with only mild, provoked
bleeding — the basis for a "hemostasis-sparing anticoagulant." All three early
gates hold: FXI is genetically implicated, inhibiting it reduces clotting, and less
clotting means fewer strokes.

Yet the Phase 3 **OCEANIC-AF trial was stopped early (Nov 2023) for inferior
efficacy vs. apixaban** — stroke/systemic embolism 1.3% vs. 0.4%, hazard ratio
~3.8 (Bayer announcement; Piccini et al., *NEJM* 2024). Crucially, the *safety*
half of the genetic thesis **held** — asundexian caused less bleeding. So the break
is at the **drug-engagement gate**: the most-cited interpretation is that
asundexian's tested dose did not inhibit FXI enough to prevent AF stroke, not that
the genetic hypothesis is wrong. The class is very much alive — **milvexian**
(LIBREXIA-AF) and **abelacimab** remain in Phase 3.

**Lesson (and rigor caveat): strong human genetics validates the *target*, not a
given *molecule, dose, or indication*.** Do not read OCEANIC-AF as "Factor XI
genetics was wrong" — read it as a failure at a gate genetics never covered.

## APOC3 / volanesorsen — genetics and efficacy held, safety split the regulators

Scored **0.7 (Weak) — but that is a scorer artifact.** APOC3's human genetics is
strong: loss-of-function carriers have low triglycerides and reduced coronary
disease (according to PubMed, TG and HDL Working Group of the Exome Sequencing
Project, *NEJM* 2014; [DOI](https://doi.org/10.1056/NEJMoa1307095)). The scorer
undervalues it for the same reason it undervalues CETP — no ClinGen gene-*disease*
curation for a quantitative-trait/protective phenotype (see the head-to-head PR's
calibration note). Every efficacy gate holds: APOC3 is genetically implicated,
inhibiting it lowers triglycerides, low triglycerides are protective, and
volanesorsen lowered TG ~70% (APPROACH trial; Witztum et al., *NEJM* 2019).

The break is at the **safety gate**: thrombocytopenia occurred in ~76% of treated
patients, with cases of severe platelet drops. **The EMA approved it (Waylivra,
2019); the FDA rejected it (2018)** over the bleeding/platelet risk — the same file,
two rigorous regulators, opposite calls. The follow-on APOC3 ASO **olezarsen**
(cleaner platelet profile) is the sequel and reached FDA approval for familial
chylomicronemia in 2024.

**Lesson: genetics can validate the target *and* the efficacy can be real, and the
program still dies on safety — a gate wholly outside the genetic signal — and two
expert regulators can weigh that gate oppositely.**

## What the three add up to

| Program | Genetics | Causal? | Drug engaged? | Safe? | Outcome | Gate that broke |
|---|---|---|---|---|---|---|
| PCSK9 (evolocumab) | 1.3 | yes | yes | yes | **approved** | — |
| ANGPTL3 (evinacumab) | 1.3 | yes | yes | yes | **approved** | — |
| Factor XI (asundexian) | 1.3 | yes | **no (dose/indication)** | yes (less bleeding) | halted | **drug engagement** |
| APOC3 (volanesorsen) | 0.7* | yes | yes | **no (thrombocytopenia)** | EMA yes / FDA no | **safety** |

Genetics guards gates 1–3 and it does its job in all four — the divergence is
entirely downstream. Combined with the `genetics_vs_outcome` figure (APP failed at
a *higher* score than PCSK9 or ANGPTL3 were approved at), the message is precise:
**genetic support raises the odds and is the single most informative category on
average (Section 2), but it is not the whole causal chain. Execution and safety are
separate gates it cannot see.**

## Scope, rigor caveats, and reproduce

- **Present-day genetics (hindsight)** — consistent with the PR #3 / #4 / #6
  disclosures.
- **Factor XI:** the efficacy failure is dose/indication-specific to asundexian in
  AF; the class (milvexian, abelacimab) is still in Phase 3. Not "FXI genetics was
  wrong."
- **APOC3:** the 0.7 score understates genuinely strong LOF-protective genetics —
  a `genetic_only_v1` calibration flag (quantitative-trait genetics without a
  ClinGen disease entry), same pattern as CETP.
- **Lp-PLA2 / darapladib** (in the `genetics_vs_outcome` figure, score 0.5) is the
  companion "weak genetics correctly predicted failure" case: two failed Phase 3s
  (STABILITY, *NEJM* 2014; SOLID-TIMI 52, *JAMA* 2014), and a loss-of-function
  natural experiment in ~91,000 adults showing lifelong low Lp-PLA2 gives no
  vascular benefit (according to PubMed, Millwood et al., *Int J Epidemiol* 2016;
  [DOI](https://doi.org/10.1093/ije/dyw087)). Rigor note: that genetic study
  postdated the trial failures, so it is confirmatory, not a prospective save.
- Reproduce: `python3 analyses/plot_genetics_gates.py`.

## Sources

- Dewey et al., *NEJM* 2017 — ANGPTL3 genetic + pharmacologic inactivation
  ([DOI](https://doi.org/10.1056/NEJMoa1612790)).
- TG & HDL Working Group of the Exome Sequencing Project, *NEJM* 2014 — APOC3
  LOF, triglycerides, coronary disease ([DOI](https://doi.org/10.1056/NEJMoa1307095)).
- Millwood et al., *Int J Epidemiol* 2016 — PLA2G7 LOF phenome-wide study
  ([DOI](https://doi.org/10.1093/ije/dyw087)).
- Evinacumab: FDA approval 2021; Raal et al., *NEJM* 2020 (ELIPSE HoFH).
- Asundexian: OCEANIC-AF halt, Bayer 2023; Piccini et al., *NEJM* 2024.
- Volanesorsen: Witztum et al., *NEJM* 2019 (APPROACH); EMA approval 2019 / FDA
  rejection 2018.
- Consistent with the CETP/amyloid write-ups in the repo's `CASE_STUDIES.md` and
  the `PCSK9_VS_APP_CETP.md` head-to-head.
