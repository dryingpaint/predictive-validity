# Reasons recorded for efficacy failure after confirmed target engagement

## Figure legend

**Reasons recorded for efficacy failure after confirmed target engagement.** **a**, The 27 drug classes in the atlas
whose engagement headline matched (the drug's effect on its target was demonstrated in people) and whose efficacy
headline was contradicted (the class failed its primary endpoint in that disease), each placed under the primary
reason the atlas's own record gives for the failure. Reasons are grouped in three layers. *Target hypothesis*: the
target, together with the direction of the intended effect, was wrong for the disease: the target's output moved in
patients but the disease did not (not causal); the target is causal at another disease stage; causal only in a
definable subgroup; causal but compensated or bypassed; causal but with an effect too small to matter; or the
direction of modulation was wrong. *Modulation*: the target was right but the drug did not act on it as the biology
needs: insufficient degree or duration of engagement, wrong schedule, engagement shown outside the disease site, or an
unsuitable modality. *Trial*: the test could not show the effect: the endpoint, trial size or duration, the population
or its placebo response, or the combination or comparator context. Filled chips are classes never approved in that
disease; hollow chips are classes approved in that disease, where the contradicted entry concerns a disease stage, a
population or a single member. The diamond marks the three categories already present in the manuscript draft; the
remaining categories are added here. Each class has one primary code; secondary codes and the supporting text are in
`codes.csv`. **b**, The 60 dose tracks the atlas scored as "target reached, not enough" (the exposure, occupancy or
regimen the preclinical model declared sufficient was reached in patients and the disease did not respond), by the
kind of target that had been reached. Every class in the atlas entered Phase 2, so both panels describe what a
positive engagement or dose result was worth once the drug was in patients; neither is a sensitivity. Statuses are the
atlas's adjudicated statuses.

## Results

Of the 27 classes, 16 fail at the target hypothesis (12 not causal, 2 wrong stage, 1 compensated, 1 effect too
small, 0 subgroup-only), 6 at modulation (all insufficient degree or duration of engagement), 4 at the trial
(3 population or placebo response, 1 combination context), and 1 is not stated in the record. The three categories
present in the manuscript draft (not causal, wrong stage, subgroup-only) hold 14 of the 27; the added categories hold
13. Four of the 27 are approved classes (CDK4/6 inhibitors in breast cancer, anti-CGRP antibodies in migraine, MEK
inhibitors in pancreatic cancer, proteasome inhibitors in myeloma) whose contradicted entry is a stage, a population or
one member; excluding them leaves 23 never-approved classes with the same ordering (target hypothesis 14, modulation
5, trial 3, not stated 1).

In the 60 dose tracks, the target that had been reached was the model's regimen in 20, its exposure in 20, a PD
biomarker in 13 and receptor occupancy in 7. Dose predictions that asked only whether the target was reached held in
105 of 111 compared tracks in the atlas (`../family_rates.csv`, question dose).

## Methods

**Cases.** `extract.py` selects every tile whose engagement headline is matched and whose efficacy headline is
contradicted under the atlas headline rule (decision 6, `glance.cells`), and writes every engagement, efficacy and dose
entry of those tiles with its reason, note, judgement and quote (`cases_entries.csv`; `cases_dossier.txt` is the same
material as text). Store as of 2026-11-09: 27 classes, 437 entries. Database access is read-only.

**Codebook.** `CODEBOOK.md` defines three layers and fourteen codes plus "not stated", one primary code per class and
an optional secondary, with the rule that coders record what the entries state rather than what they believe about the
class.

**Coding.** Two coders coded all 27 classes from the dossier alone; the second was blind to the first
(`codes_coder1.csv`, `codes_coder2.csv`; both are language-model coders, so agreement measures consistency of
reading, not validity). Agreement on the primary code was 16 of 27 (Cohen's kappa 0.52) and on the layer 19 of 27
(kappa 0.52); in 19 of 27 one coder's primary code was the other's primary or secondary. The one systematic
disagreement concerned saturating receptor occupancy with no disease effect, which the first codebook left ambiguous
(occupancy is engagement, not an output): the codebook was amended so that saturating or near-complete engagement
with no disease effect, in a trial able to detect one, codes as not causal. That amendment decided four classes
(H3 antagonists, 5-HT6 antagonists and PDE10A inhibitors; HDAC inhibitors in MDS, where acetylation rose and no
patient responded). Of the remaining seven disagreements, six were resolved to the second coder and one to the first,
each against the dossier text; `codes.csv` records the resolution of every class (`agree`, `coder1`, `coder2`,
`rule`) with its rationale.

**Figure.** `figure.py`; 183 mm wide, Helvetica 4.5–8 pt, the atlas palette (`glance_nature`).

## Limitations

- Twenty-seven classes from one atlas. The counts describe the atlas's record, not the industry-wide denominator.
- The atlas statuses were drafted and checked by language-model agents under the atlas rules and adjudicated where
  they disagreed; this coding is a further layer of reading on that record.
- Ten classes carry a low or medium confidence with a secondary code another reader could promote; the largest
  movable block is between not causal and effect too small (anti-IL-13, p38, pan-PI3K, MEK inhibitors).
- Primary codes are one per class. Several classes also carry a failed biomarker-selection prediction (anti-IGF-1R,
  pan-PI3K, MEK inhibitors, anti-IL-13), recorded in the entries but not as a primary reason.

## Files

`extract.py` · `cases_tiles.csv`, `cases_entries.csv`, `cases_dossier.txt` · `CODEBOOK.md` · `codes_coder1.csv`,
`codes_coder2.csv`, `codes.csv` · `figure.py` → `engaged_no_benefit.{png,pdf,svg}` · this file.
