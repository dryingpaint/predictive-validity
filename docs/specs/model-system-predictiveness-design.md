# Design: What kinds of preclinical models predict — mechanistic vs. proxy, temporally cleaned

**Project:** clinical-trial-predictors Substack, Section 5 ("nuance")
**Date:** 2026-07-24
**Status:** design (awaiting spec review → writing-plans)
**Builds on:** PRs #1–#8 on `dryingpaint/predictive-validity`; Melissa's `preclin.*` DB.

## 1. Research question

Which *kinds* of in vitro (cell) and in vivo (animal) evidence actually predict
clinical approval — and how much of any apparent predictive power survives once we
strip out hindsight (evidence that only existed *after* the trial)?

## 2. Thesis being tested

Preclinical models certify **mechanism engagement** ("the drug does the expected
thing to the biology"), not **disease causality** ("that mechanism is the right
lever for the human endpoint"). Predictiveness therefore tracks how *mechanism-
proximal* the disease is — highest for monogenic, mechanism-is-the-disease cases
(CF: CFTR channelopathy → organoid swelling assay is near-deterministic), and it
collapses for diseases where the molecular mechanism is far from the clinical
endpoint (Alzheimer's, most complex disease), at any level of model sophistication.

Corollary being measured: on her data, cell/animal evidence adds ~0 marginal over
genetics *on average* (Section 2 ablation) — the thesis predicts this is because
most models are proxies, and that the little real signal there is (a) does not beat
genetics and (b) shrinks further under a strict date filter.

**We are NOT trying to produce a universal ranking of model types** (organoid >
primary > immortalized). The data doesn't support that and it's disease-dependent.
The deliverable is the mechanism-proximity thesis + the tier measurement, not a
league table.

## 3. Cohort and unit of analysis

- **Unit: program** (has a `first_trial_date`, an outcome, one drug, one primary
  target). Program-level is required because the temporal cutoff is defined by when
  a *program* went into humans. Roll up to target-indication only for comparison
  against the existing Section-2 RS numbers.
- **Base cohort:** Phase 2+ programs, mirroring PR #2's strict cohort where
  possible. The drug-efficacy tier is limited to the ~553 programs whose drug has a
  `drug_*_efficacy` score and maps to a `first_trial_date`; the structural and
  literature tiers cover the broader target-level cohort.
- **Metric:** Melissa's Relative Success (RS = P(approved | evidence) ÷
  P(approved | no evidence)) + bootstrap CI, reused verbatim. Every dimension gets
  a **raw RS** and a **date-cleaned RS**; the delta between them is the headline
  leakage measurement. Genetics RS (~1.5–2.0) is the fixed benchmark.

## 4. Temporal cutoff — run two, strict and loose

We compute every date-cleaned number at **two cutoffs** and report both, so we can
see how sensitive the result is to where we draw the line:

- **Strict (primary): before `first_trial_date`.** Evidence counts only if it
  demonstrably existed before the drug entered human trials. Stricter than the
  repo's pre-2019 time-machine; the most decision-relevant line ("what was known at
  the go-to-clinic decision").
- **Loose (sensitivity): before `last_trial_date` (≈ pre-final-readout).** Evidence
  generated any time *during* development counts, but anything after the program's
  last trial (post-outcome / post-approval fame) is still excluded. This captures
  mid-development preclinical work that a strict pre-first-trial cut discards.

Under either cutoff, evidence we cannot positively date to before the line is
treated as **not available** (conservative: absence beats assumption). The gap
between strict and loose RS is itself informative — if a tier only looks predictive
under the loose cut, that's a sign its signal accrues during/after development.

## 5. Three tiers, each date-cleaned

| Tier | Dimensions | Raw source | How it's date-cleaned |
|---|---|---|---|
| **1. Structural causal-perturbation** | DepMap essentiality, IMPC KO phenotypes, OT animal-model (Phenodigm) | present-day snapshot (IMPC=2025 flat; DepMap/OT undated) | **External versioned re-pull** — pull dated releases (DepMap quarterly, IMPC data-releases, OT versioned) and pin each gene to the release available at the program's `first_trial_date` |
| **2. Literature validation** | `line_c_lit`, `line_d_lit` (target-level) | PubMed (has `citation_pmids`) | Resolve PMID → publication date; re-score from only pre-cutoff papers |
| **3. Drug-specific efficacy** | `drug_cell_efficacy`, `drug_rodent_efficacy`, `drug_nonrodent_efficacy` | PubMed (NO stored PMIDs) | **PubMed re-extraction** — per drug, search PubMed (drug + synonyms + preclinical terms), restrict to pre-`first_trial_date`, LLM-score efficacy on Melissa's rubric from surviving abstracts |

Key honesty point baked in: no tier is exempt. The structural tier's hindsight is
subtler (the *screen* postdates the trial), which is exactly why it also gets a
dated re-pull rather than a pass.

## 6. Pipelines (the two heavy workstreams)

**A. Drug-efficacy PubMed re-extraction (Tier 3).**
For each of ~553 program-linked drugs: assemble drug name + synonyms; query PubMed
restricted to `< first_trial_date`; fetch abstracts; LLM-score cell / rodent /
non-rodent efficacy on Melissa's existing 0–3 rubric; store PMIDs + dates + scores.
Main risk: drug↔PubMed disambiguation — handle via synonym list, and flag/exclude
low-confidence matches rather than guess. Best run as a background batch job.

**B. Structural versioned re-pull (Tier 1).**
Pull dated/versioned data from DepMap (quarterly release archives), IMPC (dated
data-releases / statistical-results with timestamps), and Open Targets (versioned
releases). For each gene × program, use the value from the latest release ≤
`first_trial_date`. Where a resource did not yet exist at that date, the evidence is
definitionally absent (this subsumes the coarse "resource-existence floor").

**Literature cleaning (Tier 2)** is lighter: ~3,700 stored PMIDs → PubMed dates →
per-program re-score from pre-cutoff subset.

## 7. Literature synthesis (the "nuance" narrative)

Curated, rigorously-cited examples of where a model genuinely is predictive, tied to
the mechanism-proximity thesis:
- **CF lung organoids** — forskolin-swelling predicts individual-patient CFTR-
  modulator response (used for access decisions for ultra-rare mutations).
- **Oncology patient-derived organoids / PDX** — mechanism-matched, context-dependent.
- **iPSC-cardiomyocytes** — predictive for a *specific safety* readout (proarrhythmia/CiPA), not efficacy.
- **Primary human hepatocytes / MPS** — hepatotoxicity.
- The **species-specific failures** (fialuridine → hENT1 transporter; TGN1412 → human
  CD28 effector-memory biology) as the boundary condition: models fail at
  identifiable human-specific discontinuities, not randomly.

## 8. Deliverables (→ new PR on the fork)

- Re-extraction + re-pull scripts (Tier 1 versioned puller; Tier 3 PubMed extractor),
  each reproducible and documented.
- Analysis script: raw vs. date-cleaned RS per dimension/tier, vs. genetics benchmark.
- Method doc (`analyses/MODEL_SYSTEM_PREDICTIVENESS.md`): thesis, method, the
  leakage deltas, the CF-organoid synthesis, caveats.
- Figure(s): RS-by-tier **raw vs. date-cleaned** (the leakage collapse), plus a
  mechanism-proximity schematic.
- Supporting CSVs. Present-day-vs-cleaned clearly labeled. Lean assets (200-dpi PNG + SVG).

## 9. Success criteria

- Every cell/animal dimension has a raw RS and a defensibly date-cleaned RS with the
  cutoff = program first-trial-date.
- The leakage delta (raw − cleaned) is quantified per tier, with the drug-efficacy
  and literature tiers expected to shrink most, structural least.
- A clear, honest statement of how much *clean* cell/animal evidence predicts
  approval relative to genetics — and the CF-organoid exception explained by the
  mechanism-proximity thesis.

## 10. Risks / limitations

- **Drug↔PubMed disambiguation** (Tier 3) — the main accuracy risk; mitigated by
  synonyms + low-confidence exclusion, reported as coverage.
- **Per-gene screen dates** (Tier 1) — DepMap/IMPC release archives give release-level
  dates, not the exact date a given gene's data was generated within a release; we
  pin to release date, which is conservative (a gene in release R was available no
  earlier than R). Acceptable.
- **Abstract-only scoring** — re-extraction scores from abstracts, not full text
  (matches Melissa's original method).
- **Small cleaned-cohort n** — after restricting to pre-first-trial evidence, some
  tiers may thin out; report n and CIs, don't over-read small bins.
- **Literature synthesis is curated, not from her data** — clearly framed as such.

## 11. Out of scope

- **Universal model-type ranking (organoid vs. primary vs. immortalized as a league
  table) — and here is why it's excluded, not just skipped:**
  1. **The data can't support it.** Her DB has no structured tag for assay system
     type; those distinctions live only in free-text abstracts. A ranking would be
     manufactured from data that mostly isn't there — the tidy-but-fabricated answer.
  2. **It's conceptually wrong.** Predictive power is disease-specific: CF organoids
     are near-deterministic *for CF* and useless for Alzheimer's. A universal ranking
     averages across incommensurable disease–model pairings and produces a league
     table that is misleading in every specific case — it would tell a CF team and an
     AD team the same thing when the truth is opposite.
  3. **It contradicts the thesis.** The whole point (§2) is that predictiveness comes
     from model–disease *mechanistic proximity*, not from the model's type or
     sophistication. Ranking types would smuggle back in the "fancier model = more
     predictive" heuristic the analysis is built to refute.
- Building new wet-lab-style predictive models.
- Re-litigating Section 2's genetics-dominance finding (this bounds/explains it, doesn't relitigate).
