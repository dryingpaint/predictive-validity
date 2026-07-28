# Does genetics survive the same date-cleaning? Causal yes, GWAS-association no

**The question.** We time-gated cell/animal **literature** (PR #9/#12) and **drug-efficacy**
(#9/#13) — require the evidence to predate the trial — and both **collapsed toward the
null**. Genetics is the benchmark those analyses lean on (it's the category that
*survives*, per Section 2's ablation). So the honest test: **apply the identical filter to
genetics.** If it also collapses, the "genetics dominates" headline is partly hindsight
too. If it holds, the headline is real.

**The answer: it splits cleanly along the causal-vs-associational line.** Causal, curated
genetics survives; the weak GWAS-*association* end does not.

| genetics dimension | type | present RS | time-gated RS (pre-first-trial) | verdict |
|---|---|---|---|---|
| **Mendelian ≥5** | causal | 1.42 | **1.42** (unchanged) | **survives** |
| **ClinGen ≥1** | causal | 1.80 | **1.87** [1.61, 2.17] | **survives** (even higher) |
| **GWAS ≥50** | association | 1.12 | **0.97** [0.76, 1.21] | **collapses → null** |

Figure: `genetics_timegating_clean.png`. Cohort: Ph2+ T-I pairs with a first-trial date
(n=7,836, base approval 19.9%); present-day RS reproduces Section 2's per-dimension values
(GWAS 1.12 exact; ClinGen/Mendelian ~1.8/1.4 on this first-trial-date subset).

## Why this is the expected — and important — result

The dividing line across the **entire** hindsight arc turns out to be **causal /
structural vs. associational / accretive**, not "genetics vs. everything else":

- **Causal genetics is old and structural.** A Mendelian disease-gene link (positional
  cloning / exome era) or a ClinGen-curated gene-disease validity existed long before a
  2015–2025 trial — you cannot retrofit it after the drug works. It therefore passes a
  date filter that literature (which accretes confirmatory papers *after* success) fails.
- **GWAS-*association* is accretive.** The GWAS Catalogue keeps adding hits — the study
  PMIDs behind these targets are **median 2020, only 17% pre-2015** — so the "≥50
  genome-wide-significant hits" threshold is often only crossed *after* the trial starts.
  Time-gated, only 298 of 2,505 targets still clear it, and their signal is null (0.97).
  This is exactly the permissive, dilutive genetics the project's methodology rule warns
  against ("measure genetics by strength/convergence, not any-dimension").

So this **confirms the Section-2 result where it matters** (causal genetics is genuinely
predictive, not a hindsight artifact) **and** adds the honest qualification (the weak
GWAS-association end carries hindsight, like literature). It's the "strength, not
any-dimension" rule — now *demonstrated under date-cleaning*, not just asserted.

## Method

Date each genetic evidence item by when it was first established; count it toward a
target's support only if that predates the program's first-trial year; recompute RS.

- **GWAS** — each genome-wide-significant association (`public.gwas_associations`,
  p≤5e-8) dated by its `study_pmid` publication year via NCBI eutils
  (`genetics_timegating_fetch.py` → `data/gwas_pmid_year.csv`, 1,981/1,982 dated). This is
  the *same* eutils-PMID method used for the literature date-cleaning — clean and fair.
- **ClinGen** — Strong/Definitive classifications dated by `clingen_validity.classified_date`.
  **Caveat (conservative):** that's the *curation* date, and ClinGen only formed ~2015, so
  it dates the underlying gene-disease link **too late** — it *handicaps* genetics. ClinGen
  survives (1.80→1.87) **despite** this handicap, which makes the result stronger, not weaker.
- **Mendelian** — no date/PMID in the DB. Mendelian disease-gene links are structural and
  old; **validated on a random 25-target sample — 25/25 have gene-disease literature before
  2015** (dozens to thousands of papers each), i.e. all predate the 2015+ trials. Treated as
  pre-trial.

Present vs. time-gated RS computed on **identical rows** (same T-I pairs), so the delta is
the pure date-cleaning effect. Bootstrap 95% CIs (2,000 resamples).

## Scope / limitations

- **OT-genetic / OT-somatic are NOT time-gated** — they are present-day Open Targets
  black-box aggregate scores with no per-evidence dates in source. Dating them needs
  versioned OT releases, which are coverage-capped for a 2015–2025 cohort (the wall PR #14
  hit and was closed for). So this covers the three **source-datable** genetics dimensions,
  which are also the ones with their own Section-2 per-dimension RS.
- The cutoff is `first_trial_date`, bounded to the 2015–2025 CT.gov window. It's the *same*
  cutoff literature/drug-efficacy faced — literature collapsed at it, causal genetics didn't.
- Present-day RS on the first-trial-date subset (base 19.9%) runs slightly below Section 2's
  full-cohort values (base 23%); the within-row present→time-gated delta is the point.

## Reproduce
```
DATABASE_URL=... python3 analyses/genetics_timegating_fetch.py   # date GWAS study PMIDs (eutils)
DATABASE_URL=... python3 analyses/genetics_timegating.py         # present vs time-gated RS
python3 analyses/plot_genetics_timegating.py                     # figure
```
