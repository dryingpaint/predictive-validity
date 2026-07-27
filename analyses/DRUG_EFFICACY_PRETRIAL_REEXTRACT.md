# Drug-efficacy PRE-TRIAL re-extraction — the drug-efficacy deep-dive (Tier 2)

*Part of the Section-5 nuance PR (folded in from the former standalone PR #13). It is
the rigorous treatment of the drug-efficacy tier in `MODEL_SYSTEM_PREDICTIVENESS.md`.
"PR #9" / "#9" below refer to that same main analysis (its `nuance_*` scripts and the
originally-reported numbers), not a separate PR.*

**Question:** does *"the drug worked in a model"* carry real predictive signal for
approval once you re-score it using **only evidence that existed before the trial
started** — instead of present-day literature (hindsight)?

**Why this exists.** PR #9 showed the raw drug-efficacy rubric had the *highest*
apparent Relative Success of anything (RS ≈ 2.7–3.0, above genetics), and that a
date-clean collapsed it to **0.81**. But #9's date-clean was a **paper-presence
proxy** (does *any* pre-first-trial preclinical paper exist for the drug?), because
Melissa's drug-efficacy rubric **stores no PMIDs** and cannot be dated in place. The
2.70→0.81 was therefore a date change *and* a metric change at once. This analysis
replaces the proxy with the real thing: an **actual dated re-score on Melissa's own
0–3 rubric**, using only pre-first-trial PubMed abstracts.

Script: [`drug_efficacy_pretrial_reextract.py`](drug_efficacy_pretrial_reextract.py).

---

## Method

**Rubric — reused verbatim from Melissa's `db/SCHEMA.md`** (Categories C & D). The
scorer prompt (`RUBRIC` in the script) carries these anchors unchanged:

- **`drug_cell_efficacy`** (Category C, "Cell-pathway validation", drug-level).
  Anchor from **C1 Cell-line pharmacology: `0=none / 1=basic / 2=multiple / 3=full
  panel`**, extended with C2 iPSC / C3 organoid / C4 primary human cells / C6
  perturbation-rescue (all `0/1/2/3` in SCHEMA.md).
- **`drug_animal_efficacy`** (Category D, "Animal in vivo", drug-level). Anchors from
  **D2 "Drug tested in rodent disease model, effect size" `0/1/2/3`** and **D3
  "Dog, monkey, non-human primate efficacy" `0/1/2/3`** (rodent + non-rodent combined,
  matching the DB `drug_rodent_efficacy` / `drug_nonrodent_efficacy` pair).

**Cohort / scoping (no silent caps).** Assessed-drug universe = programs with
`highest_phase ≥ 2`, a resolvable `first_trial_date`, and an existing
`drug_cell/rodent/nonrodent_efficacy` rubric score. That is **425 unique drugs / 3,022
programs** (out of 13,902 drugs / 37,734 programs with a first-trial date — the other
~13.5k drugs were never assessed on this rubric and are *dropped*, not scored as 0).
Full LLM re-scoring is specified over these 425 (≤150 per run as instructed); it was
**not run** here for lack of an API key (see "What was actually run").

**Pipeline** (`--mode fetch|score|rs`): for each drug, `esearch` PubMed with a
date ceiling `("1900"[dp] : "{first_trial_year−1}"[dp])`, `efetch` the abstract text,
and score cell + animal efficacy on the rubric. `rs_ci()` (RS + 2,000× bootstrap CI)
is **copied verbatim** from PR #9's `nuance_drug_and_structural.py` so numbers are
directly comparable.

**Synonym fix (a real coverage improvement over #9).** Drug INNs are coined *late*;
pre-trial preclinical papers use the developmental **code name**. Name-only search
returned ~0 pre-trial hits for almost every drug. Searching code-name synonyms
(MK-8931, LY450139, ABT-199, PD-0332991, CP-690,550, PSI-7977, …) is what makes any
pre-trial evidence findable at all. #9's presence-proxy used `display_name` only and
would have under-counted pre-trial evidence for the same reason.

**Scorer backends.** `--scorer anthropic` uses **`claude-haiku-4-5-20251001`** (cheap)
and needs `ANTHROPIC_API_KEY`. `--scorer manual` reads hand scores from
`data/drug_efficacy_pretrial_manual_scores.csv`. **No API key was available in this
environment**, so the empirical run is the **manual proof-of-concept**: each score
below is from a careful reading of the fetched pre-trial abstracts against the rubric,
with a one-line rationale per drug in that CSV (fully hand-checkable).

---

## What was actually run vs. specified

| | Specified | Run here |
|---|---|---|
| Present-day raw rubric RS | full assessed cohort | **RUN** — 425 drugs / 3,022 programs (real DB) |
| PubMed date-restricted fetch | full cohort | **RUN** for the 12 POC drugs (real eutils) |
| LLM re-score (haiku) | ≤150 drugs | **NOT run — no API key.** Pipeline built + import-verified |
| Dated rubric re-score | full cohort | **RUN as manual POC on 12 hand-checkable drugs** |
| Time-sliced RS | full cohort | **RUN on the 12-drug POC** (directional; wide CI) |

---

## Results

### 1. Present-day rubric RS — and a correction to PR #9's raw number

`--mode present-rs`, `data/drug_efficacy_present_rs.csv`:

| Measure | RS [95% CI] | n_support | n_not |
|---|---|---|---|
| `drug_cell_efficacy` (present, **assessed-drug** cohort) | **1.77** [1.63, 1.92] | 365 | 2,657 |
| `drug_animal_efficacy` (present, **assessed-drug** cohort) | **1.32** [1.22, 1.44] | 824 | 2,198 |

PR #9 reported raw RS **2.70 / 2.98**. Those come from a **left-join onto all ~13.9k
drugs**, which lumps every *unscored* drug into "not supported." That conflates *"has a
high score"* with *"was even assessed on this rubric,"* inflating RS via a
scored-vs-unscored selection effect. Among drugs **actually assessed**, the present-day
raw RS is only **1.77 (cell) / 1.32 (animal)** — already far below genetics-band
framing and well under #9's headline.

(Two caveats to keep this honest as a before/after: 2.70/2.98 is not a clean
*same-cohort* baseline — it also carried PR #9's pre-dedup ~4× fan-out and its
primary-target cohort. On *this* PR's own 425-drug cohort, the left-join gives
**15.48 / 12.81** — that's the pure within-cohort selection artifact. And PR #9 has
since self-corrected within its own cohort to **1.54 / 1.82**, consistent with this.)

This is a real clarification the re-score
surfaces before any date-cleaning is applied.

### 2. Time-sliced re-score — FULL cohort (N = 425, Haiku-subagent scored) — the headline

The rigorous version. Re-score every assessed drug's cell/animal efficacy on the 0–3
rubric using **only PubMed abstracts published before its first trial**, then RS vs
approval. Fetch = `--mode fetch-all` (eutils, date-restricted; 259/425 drugs have ≥1
pre-trial abstract, 166 have none → 0/0). Scoring = **12 Haiku subagents** reading the
abstracts against the rubric (no external API key — the subagents are the LLM). RS =
`--mode rs-full`, **drug-level** (one score per drug),
`data/drug_efficacy_pretrial_comparison_full.csv`. Support = score ≥ 2.

| Measure (N=425; 216 approved / 209 failed) | RS [95% CI] | n_sup | n_not |
|---|---|---|---|
| present cell (drug-level) | 1.51 [1.25, 1.80] | 69 | 356 |
| present animal (drug-level) | 1.30 [1.08, 1.55] | 136 | 289 |
| **time-sliced cell** | **0.95** [0.72, 1.18] | 84 | 341 |
| **time-sliced animal** | **0.78** [0.59, 0.98] | 103 | 322 |
| **time-sliced max(cell, animal)** | **0.89** [0.70, 1.09] | 126 | 299 |

Figure: `data/nuance_drug_efficacy_collapse_clean.png` (present → pre-trial dumbbell);
also folded into `data/nuance_tier_overview_clean.png` alongside the literature/structural tiers.

**Present-day scored drug-efficacy is modestly predictive (1.3–1.5, CIs exclude 1); the
pre-trial re-score is null (0.8–1.0, CIs touch or cross 1).** The flagship deliverable —
"the drug worked in a model" — carries **no positive predictive signal for approval**
once restricted to evidence that existed before the trial. This is the properly-powered
confirmation of #9's collapse (vs the 0.81 presence-proxy and the N=12 POC below).

Two credibility checks:
- **Not a scorer-harshness artifact:** the Haiku subagents flagged *more* drugs cell≥2
  (84) than the DB present-day did (69) — the collapse is not from under-scoring; the
  pre-trial high-scorers simply don't preferentially get approved.
- **Grain:** drug-level (one score/drug), so the matched present anchor is 1.51/1.30;
  the 1.77/1.32 in §1 is program-level (over-weights drugs with many programs). Same
  present→dated collapse either way.

**Caveats:** (a) fetch searches `display_name`+`normalized_name` only (no hand-curated
code-name synonyms at 425-scale), so early code-named pre-trial papers are under-caught
— biasing *toward* under-counting pre-trial evidence, i.e. conservative against finding
a signal; (b) `first_trial_date` is the DB's 2015-window value, so for drugs whose true
first-in-human predates it the cutoff is too permissive (admits some hindsight), which
would *inflate* the dated RS — a null is again conservative; (c) retmax 15 abstracts/drug;
(d) 51% cohort base rate reflects the assessed-drug selection (RS is within-cohort, so
unaffected). Per-drug scores + rationales: `data/drug_efficacy_pretrial_scores_full_rationale.json`.

### 3. POC precursor (N = 12, hand-scored) — same direction

`--mode rs`, `data/drug_efficacy_pretrial_comparison.csv`. Support = time-sliced
score ≥ 2. Superseded by §2's full run; kept as the hand-checkable validation that
seeded the method.

| Time-sliced measure | RS [95% CI] | n_support | n_not |
|---|---|---|---|
| cell | **1.00** [0.0, 3.67] | 2 | 10 |
| animal | **1.00** [0.0, 3.66] | 4 | 8 |
| max(cell, animal) | **1.00** [0.0, 3.66] | 4 | 8 |

Time-sliced drug-efficacy **does not separate approved from failed** in this balanced
hand sample (6 approved, 6 failed). RS is a clean **1.0**, CI wide (N=12) — directional,
and confirmed by the full N=425 run above.

### 3. Per-drug: present-day score vs. time-sliced score

| Drug | Outcome | Present cell/animal | Time-sliced cell/animal | Pre-trial evidence? |
|---|---|---|---|---|
| verubecestat (BACE1/AD) | fail | 3 / 3 | **0 / 0** | none indexed < 2012 (efficacy pub 2016) |
| torcetrapib (CETP/CVD) | fail | 3 / 3 | **0 / 0** | 1 review only, no drug-specific result |
| semagacestat (γ-sec/AD) | fail | 3 / 3 | **0 / 0** | none indexed < 2005 |
| theralizumab / TGN1412 | fail | 3 / 3 | **0 / 0** | dossier data, not PubMed-indexed |
| solanezumab (anti-Aβ) | fail | 3 / 3 | 1 / 3 | **real**: m266 PDAPP-mouse studies |
| fialuridine / FIAU | fail | 2 / 3 | 2 / 2 | **real**: 2′-fluoro-nucleoside antiviral work |
| sofosbuvir (HCV) | appr | — | **0 / 0** | none indexed < 2010 (efficacy pub 2010) |
| sitagliptin (DPP4) | appr | — | **0 / 0** | none indexed < 2003 (pub 2005) |
| maraviroc (CCR5) | appr | — | **0 / 0** | none indexed < 2003 (pub 2005) |
| venetoclax (BCL2) | appr | — | **0 / 0** | none indexed < 2011 (pub 2013) |
| palbociclib (CDK4/6) | appr | — | 3 / 2 | **real**: PD-0332991 xenografts + panels |
| tofacitinib (JAK) | appr | — | 1 / 3 | **real**: mouse + cynomolgus transplant |

Two findings jump out:

- **The present-day "3/3" on the famous failures is largely hindsight.** Four of six
  CASE_STUDIES failures (verubecestat, torcetrapib, semagacestat, TGN1412) have a
  present-day cell/animal score of 3/3 but a time-sliced score of **0/0** — their
  drug-specific efficacy literature was indexed *at or after* first-in-human.
- **Coverage is the story.** **8 of 12** drugs (both winners and losers) had **no
  scoreable PubMed-indexed pre-trial drug-specific efficacy at all** — the "it worked
  in a model" paper is frequently published concurrent with or after the trial starts.
  Where genuine pre-trial evidence *does* exist (solanezumab, fialuridine, palbociclib,
  tofacitinib) it appears on **both** a failure and an approval, hence RS ≈ 1.

---

## Value-add / caveats (honest)

**What's solid**

- Replaces #9's presence-proxy with an **actual dated re-score on Melissa's verbatim
  0–3 rubric** — the metric-vs-date confound in the 2.70→0.81 story is removed.
- Surfaces a **real correction**: #9's raw 2.70/2.98 is partly a scored-vs-unscored
  selection artifact; among assessed drugs it's 1.77/1.32.
- The **synonym/code-name coverage fix** is a genuine, reusable improvement.
- Every POC score is **hand-checkable** (rationale + source PMIDs per drug in the CSV;
  raw abstracts cached in `data/drug_pretrial_abstracts.json`).

**What's a caveat**

- **This is a proof-of-concept, not a full result.** N = 12 hand-scored drugs; the
  time-sliced RS CI spans [0, ~3.7]. It is directional support for the thesis, not a
  new headline number. The full LLM run over the 425 assessed drugs is **built but not
  run** (no API key).
- **Absence of a PubMed hit ≠ absence of evidence.** The measure captures *published,
  PubMed-indexed, drug-specific* pre-trial efficacy. Preclinical work in the IND /
  patents / non-indexed venues is invisible to it — so time-sliced scores are a
  **lower bound** on what was actually known. (This is itself the point: the *public,
  citable* efficacy record is largely retrospective.)
- `first_trial_date` in the DB is bounded by the 2015–2025 CT.gov window, so it is
  wrong for pre-2015 drugs. The POC therefore uses **documented true first-in-human
  years** as cutoffs (logged in the `POC` table and per-drug notes), not the DB date.
- Manual scoring is one careful reader; an LLM or second reader would give inter-rater
  variance not quantified here.

## To scale to the full run

1. Set `ANTHROPIC_API_KEY`; run `--mode fetch` then `--mode score --scorer anthropic`
   over the 425 assessed drugs (est. well under the ≤150/run cap × ~3 batches, cheap on
   haiku). Pull real first-trial dates from source (not the windowed DB date) and drug
   synonyms from ChEMBL/DrugBank rather than the hand list here.
2. Compare the haiku time-sliced RS to the present-day 1.77/1.32 anchor on the *same*
   425 drugs — that is the definitive version of the number this POC estimates at ~1.0.
