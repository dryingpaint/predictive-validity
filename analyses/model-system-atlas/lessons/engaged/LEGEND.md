# Reasons recorded for efficacy failure after confirmed target engagement

## Figure legend

**Reasons recorded for efficacy failure after confirmed target engagement.** The 27 drug classes in the atlas
whose engagement headline matched (the drug's effect on its target was demonstrated in people) and whose efficacy
headline was contradicted (the class failed its primary endpoint in that disease), each placed under the primary
reason the atlas's own record supports for the failure. Reasons are grouped in three layers. *Target hypothesis*: the
target, together with the direction of the intended effect, was wrong for the disease: the target's output moved in
patients but the disease did not (not causal); the target is causal at another disease stage; causal only in a
definable subgroup; causal but compensated or bypassed; causal but with an effect too small to matter; or the
direction of modulation was wrong. *Modulation*: the target was right but the drug did not act on it as the biology
needs: insufficient degree or duration of engagement, wrong schedule, engagement shown outside the disease site, or an
unsuitable modality. *Trial*: the test could not show the effect: the endpoint, trial size or duration, the population
or its placebo response, or the combination or comparator context. *Not stated in the record*: the class failed with
target engagement confirmed and the record gives no reason that the evidence supports; a candidate reason, where the
coders proposed one, is kept as a secondary code. A class is placed under a specific reason only when the record
states that reason or contains the observation that defines it; receptor occupancy or exposure alone is engagement,
not an output, and does not by itself support any reason. Filled chips are classes never approved in that disease;
hollow chips are classes approved in that disease, where the contradicted entry concerns a disease stage, a population
or a single member. The diamond marks the three categories already present in the manuscript draft; the remaining
categories are added here. Each class has one primary code; secondary codes, the evidence grade and the supporting
text are in `codes.csv`. Every class in the atlas entered Phase 2, so the figure describes what a positive engagement
result was worth once the drug was in patients; it is not a sensitivity. Statuses are the atlas's adjudicated statuses.

## Definitions

| term | meaning here |
|---|---|
| class (tile) | one mechanism (target and action) in one disease, tracked in the atlas because at least three programs entered Phase 2 for it in 2008–2019 |
| engagement headline matched | at least one model system's prediction that the drug would act on its target in people (occupancy, free target, the target's own product, or a downstream marker) was confirmed in dosed humans, under the atlas headline rule (decision 6) |
| efficacy headline contradicted | the best prospective model prediction of clinical benefit in that disease was contradicted by the primary endpoint of a member drug's trial; a later success by another member does not reverse it (one drug's contradiction outranks another's match on the same track) |
| approved class | a member of the class was approved in that disease (`furthest_phase` 4 in `cases_tiles.csv`); its contradicted entry is a stage, a population or one member, not the class |
| primary reason | the one code the record supports for why efficacy failed; `secondary` is a second code the text also supports, or, for a class coded not stated, the candidate the coders proposed |
| evidence grade | `stated`: the record names the reason (a source, sponsor, regulator or the atlas judgement); `pattern`: the code's defining observation is in the record; `none`: the code would rest on inference alone, so the class is coded not stated |
| confidence | the coder's confidence in the primary code after reading every entry: high, medium or low |
| resolution | how the final code was reached: `agree` (both coders), `coder1` or `coder2` (the disagreement resolved against the dossier text), `evidence` (changed at the evidence pass) |
| not causal | a named output of the target beyond engagement itself (a biomarker, pathway readout or pharmacodynamic marker) moved in patients and the disease did not respond |
| compensated or bypassed | the target is causal but a feedback loop, a parallel pathway, resistance or another source of the same signal removed the benefit |
| insufficient degree or duration of engagement | the level, completeness or persistence of target engagement declared sufficient on preclinical grounds was not sufficient in patients, as the record states |
| population or placebo response | the enrolled population, its placebo response or its background therapy prevented a readout, without a claim that the target is causal only in a subgroup |
| combination or comparator context | the drug was tested in a combination or against a comparator in which its contribution could not show |

## Results

Of the 27 classes, 13 fail at the target hypothesis (9 not causal, 1 wrong stage, 1 compensated, 2 effect too
small, 0 subgroup-only), 1 at modulation (insufficient degree or duration of engagement), 4 at the trial (3 population
or placebo response, 1 combination context), and 9 carry no reason the record supports. The three categories present
in the manuscript draft (not causal, wrong stage, subgroup-only) hold 10 of the 27; the added categories hold 8; 9
are not stated. By evidence grade, 10 of the 18 coded classes rest on a reason the record states and 8 on the code's
defining observation.

Four of the 27 are approved classes (CDK4/6 inhibitors in breast cancer, anti-CGRP antibodies in migraine, MEK
inhibitors in pancreatic cancer, proteasome inhibitors in myeloma) whose contradicted entry is a stage, a population
or one member; excluding them leaves 23 never-approved classes (target hypothesis 12, modulation 1, trial 2, not
stated 8).

The nine classes coded not stated, with the candidate reason the coders proposed: BTK inhibitors in rheumatoid
arthritis (degree of engagement: one member worked only at higher doses, another was fully engaged at every dose and
matched placebo); H3 antagonists and 5-HT6 antagonists in Alzheimer's disease (occupancy saturating, no effect, no
reason given); HSP90 inhibitors, PI3K/mTOR inhibitors and CDK4/6 inhibitors in breast cancer; new NRTIs in HIV;
proteasome inhibitors in myeloma; DP2 antagonists in allergic rhinitis.

## Methods

**Cases.** `extract.py` selects every tile whose engagement headline is matched and whose efficacy headline is
contradicted under the atlas headline rule (decision 6, `glance.cells`), and writes every engagement, efficacy and dose
entry of those tiles with its reason, note, judgement and quote (`cases_entries.csv`; `cases_dossier.txt` is the same
material as text). Store as of 2026-11-09 (after #81 and #130 merged): 27 classes, 437 entries. Database access is
read-only.

**Codebook.** `CODEBOOK.md` defines three layers and fourteen codes plus "not stated", one primary code per class and
an optional secondary, with the rule that coders record what the entries state rather than what they believe about the
class, and the evidence grade every primary code must carry.

**Coding.** Two coders coded all 27 classes from the dossier alone; the second was blind to the first
(`codes_coder1.csv`, `codes_coder2.csv`; both are language-model coders, so agreement measures consistency of
reading, not validity). Agreement on the primary code was 16 of 27 (Cohen's kappa 0.52) and on the layer 19 of 27
(kappa 0.52); in 19 of 27 one coder's primary code was the other's primary or secondary. The one systematic
disagreement concerned saturating receptor occupancy with no disease effect, which the first coder read as not
causal and the second as not stated. The eleven disagreements were first resolved against the dossier text: six to
the second coder, one to the first, and four by a rule reading saturating occupancy as not causal, later withdrawn.

**Evidence pass.** Every primary code was then graded by what the record supports: `stated`, `pattern` or `none`
(definitions above). Nine classes whose code rested on inference alone were recoded not stated, with the candidate
kept as secondary: this withdrew the occupancy rule (H3 and 5-HT6 antagonists), the degree-of-engagement inferences
(BTK inhibitors, HSP90 inhibitors, PI3K/mTOR inhibitors, proteasome inhibitors, new NRTIs) and the stage reading for
adjuvant CDK4/6 inhibitors (adjuvant abemaciclib succeeded where adjuvant palbociclib failed, so stage alone does not
explain it). MEK inhibitors in pancreatic cancer moved from not causal to effect too small on the retrodiction
model's own statement. `codes.csv` records each class's resolution, evidence grade and rationale.

**Figure.** `figure.py`; 183 mm wide, Helvetica 4.5–7 pt, the atlas palette (`glance_nature`).

## Relation to the program-level analysis

`pipeline.target_history` (#134) asks the same question of every Phase 2/3 efficacy stop with target engagement
(1,035 stops) and reads a verdict from the sources with five categories: target not causal, drug inadequate, trial
inadequate, wrong patients, wrong stage. The three layers here map onto them (target hypothesis: not causal, wrong
stage, subgroup-only; modulation: drug inadequate; trial: trial inadequate, wrong patients) and add the finer
reasons the atlas's model-level record supports (direction, compensation, effect size; degree, schedule, site,
modality; endpoint, power, placebo, context). The unit differs: a class and its model record here, a stopped program
and its target history there. The two readings are complementary, not a replication. The share coded not stated
here (9 of 27) is the counterpart of the caution in #134 that a blind reading over-calls "not causal".

## Limitations

- Twenty-seven classes from one atlas. The counts describe the atlas's record, not the industry-wide denominator.
- The atlas statuses were drafted and checked by language-model agents under the atlas rules and adjudicated where
  they disagreed; this coding is a further layer of reading on that record.
- A third of the classes carry no reason the record supports. Their candidate codes (mostly degree of engagement)
  are recorded as secondary and are hypotheses, not findings.
- Eight of the 18 coded classes rest on the code's defining observation rather than a stated reason; the largest
  such block is not causal, where a moved output and an unchanged disease are read as evidence against causality.
- Several classes also carry a failed biomarker-selection prediction (anti-IGF-1R, pan-PI3K, MEK inhibitors,
  anti-IL-13), recorded in the entries but not as a primary reason.

## Files

`extract.py` · `cases_tiles.csv`, `cases_entries.csv`, `cases_dossier.txt` · `CODEBOOK.md` · `codes_coder1.csv`,
`codes_coder2.csv`, `codes.csv` · `figure.py` → `engaged_no_benefit.{png,pdf,svg}` · this file.
