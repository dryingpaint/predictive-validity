# Steps 3 and 4: what tied the indirect readouts to their targets, and what it does to the headline

_Anchors researched 2026-11-03 for the 256 readout families in `step3_scope.csv` (37 batches of agents under
`ANCHOR_BRIEF.md`, one source read per family, mostly at abstract level; `anchors.csv`). Joined to the labels
by `analysis.py`; cohort and phase-entry dates from `cohort_pull.py`._

## The anchors

| anchor for the family | families | meaning |
|---|---|---|
| prior drug | 121 | an earlier drug on the target moved the readout in humans, with its own engagement shown directly or by approval |
| genetics | 64 | people carrying variants in the target gene show the readout change |
| direct assay | 11 | a human study related the readout to measured occupancy or activity |
| pathway only | 60 | the link rests on preclinical or in-vitro biology; no human anchor independent of the program |

Specificity as the researchers judged it: 4 of 256 readouts are specific to the target, 121 shared with a few
other mechanisms, 130 nonspecific. An anchored readout is therefore known class pharmacology, not proof that
this target and no other was hit.

## What the "engaged" verdicts rest on

| basis of the verdict | all labelled stops (1,260) | report cohort (771) |
|---|---|---|
| direct: the target itself, or a product only it makes | 820 (65 %) | 513 (67 %) |
| indirect readout, anchored in humans before the program's phase entry | 285 (23 %) | 161 (21 %) |
| indirect readout, anchored only after phase entry | 49 (4 %) | 37 (5 %) |
| indirect readout, pathway logic only | 84 (7 %) | 50 (6 %) |
| no usable readout | 22 (2 %) | 10 (1 %) |

So of the 440 verdicts that rest on an indirect marker, 285 (65 %) had a human anchor that predates the
program, 49 (11 %) were anchored only later, 84 (19 %) rest on the animal model or in-vitro biology alone,
and 22 name nothing. The circular case, a marker validated by the same biology the trial was testing, is
7 % of all measured-engaged verdicts and 11 % counting the late anchors.

## The report's number

Not engaged among mechanism-tested efficacy failures, Phase 2/3 entries 2008–2019, after the report's own
`pillar_code` and subcause mapping (n = 2,220; 238 not engaged):

| reading of "engaged" | engaged, no benefit | not engaged, of tested |
|---|---|---|
| report: measured or inferred from another disease | 1,030 | 19 % |
| measured only (the report's own "direct pillar evidence" variant) | 708 | 25 % |
| measured, and the readout direct or anchored in humans before phase entry | 622 | 28 % |
| measured, direct readouts only | 472 | 34 % |

The anchored reading is the defensible one: it keeps every verdict whose readout was known class pharmacology
when the trial was run and drops the rest to "no engagement data". It moves the share from 25 % to 28 %.
Sensitivity: counting the three families the researchers flagged as prior-drug under a looser rule, 28 %;
dropping the 29 families flagged as filed under the wrong target, 28 %; counting anchors at any date, 27 %.

## Within the cohort

| basis | engaged, no benefit (F2) | shown in this disease | shown before the index trial |
|---|---|---|---|
| direct (513) | 449 | 178 | 319 |
| anchored before entry (161) | 139 | 85 | 108 |
| anchored after entry (37) | 32 | 21 | 21 |
| pathway only (50) | 36 | 29 | 22 |

Pathway-only verdicts are more often shown in the disease itself (29 of 50) than direct ones (178 of 513):
the circular readouts are the ones the program invented for its own trial.

## Caveats

- One researcher per family, one source, mostly abstract level (236 of 256 medium confidence). The anchor
  kinds are defensible on the reports; the years are the earliest readable source, often later than the
  first disclosure.
- 29 families are filed under the wrong target by the first-symbol naming rule (a VEGFR2 readout under
  AURKA, a DAT occupancy under SLC6A2); the researchers anchored on the real mechanism and flagged it.
  Excluding them does not move the headline.
- `prior_drug` was read strictly: an earlier unapproved drug on the same target that moved the readout, with
  no direct engagement of its own, stays `pathway_only`. Three families flip under the looser reading.
- The brief's `anchored_after_entry` uses phase-entry date against anchor year; a 2012 anchor for a 2012
  entry counts as before.
- This classifies failed programs only. Whether the basis of engagement predicts anything needs the
  programs that advanced, which have no engagement label.
