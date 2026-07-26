# Fully time-slicing the LLM literature evidence lines B–E — how much is hindsight?

**The question.** The four LLM-derived literature evidence lines score every target
0–3 on whether the published literature supports it as a drug target:

| line | dimension | what it scores |
|---|---|---|
| **B** | `line_b_lit` | **mechanistic** literature |
| **C** | `line_c_lit` | **cell / in-vitro** literature |
| **D** | `line_d_lit` | **animal / in-vivo** literature |
| **E** | `line_e_lit` | **pharmacodynamic (PD)** literature |

Raw, all four look like strong predictors of approval (Relative Success ≈ 1.9–2.3,
at or above the genetics benchmark of ~1.44–1.98). But the scores were produced by a
classification job on **2026-07-23** reading *today's* literature. Approved drugs
accrue confirmatory papers *after* they succeed, so the raw scores are
hindsight-contaminated. **How much of the apparent predictive power survives once we
require the supporting papers to have existed before the trial?**

This extends PR #9 (`analyses/MODEL_SYSTEM_PREDICTIVENESS.md`), which date-cleaned
only cell (line_c) and animal (line_d) — and, we find, without deduping the evidence
table. Here we do all four lines rigorously.

## Headline

**Two separate confounds inflate the raw literature signal, and together they account
for essentially all of it.**

1. **Temporal leakage (date):** requiring the cited papers to predate the first trial
   removes **a third to over half** of each line's excess RS. Figure:
   `data/line_be_timeslice_clean.png` / `.svg`.
2. **Selection leakage (which targets got scored at all):** the LLM scored only 579
   of the cohort's ~951 primary targets — the well-studied ones. Programs on
   never-scored targets fall into the "no-support" baseline, so the raw contrast is
   partly *"was this target studied enough to score"*, not *graded evidence*. Restrict
   to the scored subset and the date-cleaned signal **collapses to near-null** for B
   and D and to a modest ~1.2–1.3 for C and E — below the genetics band.

Net: after removing both confounds, **no literature line clears the genetics
benchmark**, and mechanistic (B) and animal (D) literature carry **no** residual
predictive signal at all. This *strengthens* PR #9's thesis (most apparent
cell/animal power is hindsight) and pins down the mechanism as time **plus** selection.

## Results

RS = P(approve | support) ÷ P(approve | no support); support = score ≥2 (Melissa's
"high" threshold from `preclin.v_relative_success_clean`). Program unit, Ph2+, dated
(n = 10,624). Bootstrap 95% CIs (3,000 resamples, pairs resampled together).
`raw` = any-date papers; `pre-trial` = ≥1 cited paper published before the trial.

### Full cohort (baseline includes never-scored targets)

| Line | Raw RS | Pre-first-trial (strict) | Pre-last-trial (loose) | % of excess removed (strict) |
|---|---|---|---|---|
| **B mechanistic** | 2.07 [1.89, 2.28] | **1.55** [1.41, 1.69] | 1.72 [1.58, 1.87] | 49% |
| **C cell** | 2.05 [1.88, 2.24] | **1.71** [1.56, 1.87] | 1.81 [1.66, 1.97] | 32% |
| **D animal** | 1.94 [1.79, 2.12] | **1.41** [1.27, 1.55] | 1.63 [1.50, 1.78] | 56% |
| **E PD** | 2.31 [2.14, 2.51] | **1.78** [1.62, 1.96] | 2.09 [1.93, 2.27] | 40% |

Loose sits between raw and strict, as expected. The strict points *look* like they
land in the genetics band — but that residual is itself confounded (next table).

### Scored subset only (removes the selection artifact)

| Line | Raw RS | Pre-first-trial (strict) | read |
|---|---|---|---|
| **B mechanistic** | 0.44 [0.31, 0.72] | **1.06** [0.96, 1.17] | null — no within-target signal |
| **C cell** | 1.40 [1.20, 1.67] | **1.22** [1.11, 1.34] | modest, below genetics |
| **D animal** | 1.25 [1.10, 1.43] | **0.98** [0.88, 1.09] | null |
| **E PD** | 1.89 [1.69, 2.15] | **1.30** [1.17, 1.43] | modest, below genetics |

B's raw RS of 0.44 is not a real liability — it's the degenerate flip side of
saturation: line_b scores ≥2 for ~99% of *scored* targets, so its "no-support" scored
group is only ~21 programs (unstable). The honest reading of B is simply: **no usable
contrast** within scored targets. Genetics (structural, hard to retrofit) is the
benchmark these do not reach.

Cross-reference to Melissa's published RS view (`v_relative_success_clean`, T-I unit,
raw): C = 1.43, D = 1.37, E = 2.02 (B not in her view). Our raw numbers differ because
of unit (program vs T-I) and deduping; the valid leakage estimate is the raw→clean
**delta at a fixed unit**, not the absolute level.

## Method (what's reused vs new)

**Reused from PR #9** (cited, not re-derived): NCBI eutils `esummary` date-resolution
with a regex-year fallback for non-PMID citations, cached to `data/pmid_pubyear.csv`;
the two-cutoff design (strict = `first_trial_date`, loose = `last_trial_date`); the
program unit (trial dates live on programs, not T-I pairs — the only unit where
date-cleaning is possible, same operationalization #9 used); and `rs_ci()` verbatim.

**Reused from Melissa:** the score ≥2 "high" support threshold and the RS metric from
`v_relative_success_clean`.

**New / improved here:**
- All **four** lines (B–E), not just C/D.
- **Dedup.** `evidence_score` stores ~4 *near-duplicate* rows per (target, dimension)
  from repeated ingest — **mostly** identical (same score + citation array, different
  `evidence_id`/`extracted_at`), but ~12/579 targets per line carry a genuinely
  *divergent* (score, citation) variant; we resolve those with `max` score / keep-first
  citations (a small, documented tie-break). PR #9 merged without deduping, fanning programs out
  ~4× non-uniformly; this shifts its reported numbers (its cell strict 1.40 / animal
  1.21 become 1.71 / 1.41 once deduped). We dedup to one row per (target, dimension).
- The **scored-subset** sensitivity that isolates the selection confound.

Reproduce:
```bash
DATABASE_URL=... ~/miniforge3/bin/python3.13 analyses/line_be_timeslice.py
~/miniforge3/bin/python3.13 analyses/plot_line_be_timeslice.py
```
Outputs: `data/line_be_timeslice.csv` (RS, both populations),
`data/line_be_datable_fraction.csv`, `data/line_be_timeslice_clean.{png,svg}`.

## Datable fraction (reported, no silent drops)

`citation_pmids` are **polluted** — a mix of real PMIDs, raw DOIs, and free-text.
Overall, of 913 unique citation strings: 620 are PMIDs (617 datable via eutils) and
293 are non-PMID (149 got a year by regex; 144 undatable). At the **program** level,
the fraction of high-support programs with ≥1 *datable* citation is ~74% per line:

| Line | high-support programs | with any paper | datable | % datable |
|---|---|---|---|---|
| B mechanistic | 5,561 | 4,307 | 4,162 | 74.8% |
| C cell | 4,815 | 3,718 | 3,573 | 74.2% |
| D animal | 4,503 | 3,506 | 3,366 | 74.8% |
| E PD | 3,661 | 2,860 | 2,718 | 74.2% |

Undatable high-support programs are conservatively treated as **not** pre-trial
(pushed into "no support" in the clean versions). This biases clean RS **downward**
— the true temporal-leakage-corrected value could be modestly higher, but not enough
to change the conclusion given the scored-subset result.

## Data-quality finding: the four lines share one citation set

For 576 of 579 scored targets, **all four lines B/C/D/E carry the identical
`citation_pmids` array.** The classifier attached a single target-level paper set,
then scored each line off it. So the lines are *not* independently evidenced — they
differ only in which targets clear score ≥2 and, given the shared pool, share the same
earliest-datable-paper year per target. Any apparent line-to-line differences in
predictiveness are differences in the *scoring*, not in distinct bodies of literature.

## Value-add / caveats (read before citing)

- **Residual leakage remains even in the clean numbers.** Date-cleaning only checks
  that *one cited paper* predates the trial; the LLM's 0–3 **score magnitude** was
  still assigned in 2026 with full hindsight. A target with an old paper can still be
  scored ≥2 for reasons that only became clear later. So even the strict RS is an
  **upper bound** on the causal predictive value.
- **The selection confound is the bigger story.** The full-cohort strict RS looks
  respectable only because the "no-support" baseline is ~half never-scored targets
  (47% of programs). Within scored targets the clean signal is near-null. Which of
  the two views is "right" depends on the use case: full-cohort answers "does a target
  having pre-trial lit-support predict approval across all targets" (yes, weakly,
  partly for selection reasons); scored-subset answers "among comparably-studied
  targets, does *more/dated* lit-support predict approval" (essentially no for B/D).
- **~26% of high-support programs are undatable** (non-PMID citations); treated
  conservatively as not-pre-trial. No silent drops — counts reported above.
- **Program vs T-I unit.** RS levels are not directly comparable to Melissa's T-I
  view; only the within-unit raw→clean delta is the leakage estimate.
- **Not a model-type ranking** — same scope note as PR #9.

## Honest self-assessment

The rigorous, double-controlled result (scored subset + date-clean) is the one to
trust, and it says the LLM literature lines B–E have little-to-no genuine,
non-hindsight, non-selection predictive power — with C and E retaining a modest
edge and B and D essentially null. This is a cleaner and slightly *more negative*
verdict than PR #9's full-cohort framing suggested, and it corrects a dedup artifact
in #9. The main thing I could not remove is score-magnitude hindsight (the score
itself is a 2026 judgement); a truly clean version would require re-scoring each line
from *only* pre-trial abstracts, which is out of scope here.
