# Why an engaged target still failed

**Figure.** The 27 drug classes in the atlas whose engagement headline matched (the drug demonstrably hit its target in
people) and whose efficacy headline was contradicted, one chip per class, placed under the primary reason the atlas's
own written record gives for the failure. Rows 1–3 are the three reasons in Melissa's draft reply to Jack Scannell
(a surrogate or non-translating target; a causal target acted on at the wrong time; a target causal only in some
patients). Rows marked + are additions. Filled chips are classes never approved in that disease; hollow chips are
classes that were approved, where the contradiction is a stage, a population or one weak member. Every class here
went into patients, so this is what a positive engagement result was worth, never a sensitivity.

**Counts (resolved coding).** Target hypothesis 16 of 27, modulation 6, trial 4, unclear 1. Melissa's three reasons
hold 14 of 27 (12 not causal, 2 wrong stage, 0 subgroup-only). The additions hold 13: engagement not deep or long
enough 6, population or placebo response 3, compensated 1, effect too small 1, combination context 1, unclear 1.

**What that says to Jack.** About half of "engaged the target, no benefit" is a target-hypothesis failure in the
strict sense. The other half is dosing that was declared sufficient on preclinical grounds and was not (six classes,
including a proteasome inhibitor at 45 % PBMC inhibition and a BTK inhibitor whose rat-CIA occupancy target did not
hold), and trials whose placebo arm or population swallowed the effect (three). None of the 27 is a subgroup story in
the record, although several biomarker-selection predictions failed inside other rows. The 60 dose tracks the atlas
scored "reached the model's target, not enough" point the same way: what had been reached was the regimen (20), the
exposure (20), a PD biomarker (13) or occupancy (7). Exposure prediction held; the level declared sufficient did not.

## Method

- **Cases.** `extract.py` pulls every tile whose engagement headline is matched and efficacy headline contradicted
  (adjudicated statuses; `glance.cells`, decision 6), with every engagement, efficacy and dose entry: reason, note,
  judgement, quote. 27 classes, 437 entries, written to `cases_dossier.txt`. Store as of 2026-11-09 (3,294 entries).
- **Codebook.** `CODEBOOK.md`: three layers, 14 codes plus unclear; one primary and an optional secondary per class;
  code what the entries say, not what the coder believes about the class.
- **Two coders.** Coder 1 (`codes_coder1.csv`) and a second coder blind to the first (`codes_coder2.csv`, a separate
  Claude agent given only the codebook and the dossier). Agreement on the primary code 16 of 27 (kappa 0.52), on the
  layer 19 of 27 (kappa 0.52); in 19 of 27 one coder's primary was the other's primary or secondary. Moderate, and
  reported as such. Kappa between two language-model coders measures consistency of reading, not validity.
- **Main disagreement.** Coder 2 read saturating receptor occupancy with no disease effect as unclear (occupancy is
  engagement, not an output); coder 1 read it as not causal. The codebook now says A1 covers saturating engagement
  when the trial could have detected an effect, and that rule decided H3 and 5-HT6 antagonists in Alzheimer's and
  PDE10A inhibitors in schizophrenia (plus HDAC inhibitors in MDS, where acetylation rose and 0 of 26 responded).
- **Other resolutions** (`codes.csv`, column `resolution`): 16 agreed; 6 to coder 2 (DP2 antagonists in rhinitis to
  unclear; allergen immunotherapy in rhinitis to population; PI3K/mTOR to thin engagement; MEK in pancreatic cancer,
  anti-IL-13 and p38 to not causal with effect-size secondary); 1 to coder 1 (new NRTIs in HIV, degree before
  resistance, both low confidence); 4 by the refined rule.

## Caveats

- 27 classes. The counts describe the atlas, not the industry; Melissa's 42 % bar is 2,490 programmes.
- Statuses were drafted and checked by language-model agents and adjudicated where they disagreed; the coding here
  is a second layer on top of that record.
- Ten classes carry a low or medium confidence with a secondary code that another reader could promote; the largest
  movable block is not causal versus effect too small (anti-IL-13, p38, pan-PI3K, MEK).
- Four approved classes are in the set because one stage, population or member failed; they are drawn hollow and are
  not failures of target selection.

## Files

`extract.py` (database, read-only) · `cases_tiles.csv`, `cases_entries.csv`, `cases_dossier.txt` · `CODEBOOK.md` ·
`codes_coder1.csv`, `codes_coder2.csv`, `codes.csv` · `figure.py` → `engaged_no_benefit.{png,pdf,svg}` · this file.
