# What a preclinical "yes" was worth

Built on the 166 tracked tiles of the atlas (1,735 tracks, 1,137 with a compared outcome; 1,045 model systems),
as stored on 2026-11-09. Main figure `atlas_lessons.*` (two panels), supplementary `atlas_lessons_families.*`,
caption `atlas_lessons_caption.md`, design and decisions `DESIGN.md`, checks `robustness.md`; everything from
`lessons.py all`. Statuses are the atlas's adjudicated statuses; nothing is re-adjudicated here.

## Read this first

Every tile reached Phase 2. A model that said no and was believed is not in this dataset, so nothing here is a
sensitivity: the atlas cannot say how often a model would have stopped a failure. What it can say is what a
positive prediction was worth once the drug was in patients, and, for engagement, whether a matched readout
distinguished classes that went on to approval from classes that did not (both outcomes are present, so that
one is a real discrimination test). Intervals are Wilson 95 % on tiles where tiles are the unit, and
cluster-bootstrap 95 % over tiles where tracks are counted. Every test and sensitivity run is in
`robustness.md`, written by the script.

## 1. A reached target is not a disease prediction (figure, panel a)

The engagement headline matched in **146 of 166 tiles**: in 73 of 78 classes that were later approved and in
73 of 88 that never were (Fisher p = 0.054). A matched engagement readout did not separate the classes that
would succeed from the ones that would fail. Among the 146, efficacy was contradicted in 35: 29 of the 73
never-approved classes (40 %, 29–51) and 6 of the 73 approved (8 %, 4–17).

| engagement readout of the headline track | tiles held | efficacy contradicted | 95 % |
|---|---|---|---|
| direct (occupancy, free target) | 40 | 14 (35 %) | 22–51 |
| proximal (the target's own product) | 55 | 10 (18 %) | 10–30 |
| downstream biomarker | 49 | 11 (22 %) | 13–36 |

The tier did not matter (chi-square p = 0.16; with the best tier among a tile's matched engagement tracks
instead of the headline's, p = 0.29). The point estimate for direct occupancy is the worst, and that is all
it is. By area, the contradicted share runs from 0 of 5 in gastroenterology and 0 of 4 in ophthalmology
to 5 of 10 in neurology and 3 of 3 in allergy (`engagement_summary.csv`).

Dose predictions, which ask only whether the exposure, occupancy or regimen target the model stated was reached
in people and its stated tolerability margin held, held in 175 of 190 compared tracks (0.92, 0.89–0.96). A drug
that reached its target and still failed is an efficacy failure, counted once. Exposure is what preclinical work
predicts well; a PD biomarker that moves in people is an engagement result and the record shows it being read
as a disease result.

## 2. What the safety models missed (figure, panel b)

Safety predictions held in 191 of 287 compared tracks (0.67, 0.61–0.72). A prediction is a stated finding or
silence on a harm the species could have shown (brief v3). The 100 contradicted tracks were typed from the
entry text by two coders, the second blind to the first: agreement on type 92 of 100 (kappa 0.87),
on primary harm class 94 of 100 (kappa 0.93), every row sharing at least one harm class; the eight type
disagreements are listed in `robustness.md` and were resolved by re-reading the entry (three to the second
coder, five kept). Four tracks typed as having no admissible comparison leave the count.

| type | tracks | meaning |
|---|---|---|
| silent | 48 (+1 not showable) | no prediction on a harm the species could have shown; patients had it |
| stated safe | 34 | the model said there would be no such harm; patients had it |
| false alarm | 13 | the model predicted a harm patients never had |

Four of the 96 are one package serving several tiles (a cynomolgus toxicology package behind three PD-1
tiles, one behind two, a pamiparib xenograft behind two), so the figure counts each (system, harm) once:
**92 model systems, 117 unique system–harm pairs**. By harm: cardiovascular 20 (10 silent, 10 stated safe: QT
prolongation twice after a clean hERG and dog telemetry, hypertension after "no blood-pressure effect",
bradycardia after S1P3 sparing, heart failure, atrial fibrillation after clean dog telemetry, a serious
cardiovascular-event imbalance three human systems had cleared, a blood-pressure rise the knockout said would
not come), metabolic, endocrine and bone 15 (5 silent, 7 stated safe, 3 false alarms), immune-mediated 14
(10 silent), CNS 13, liver 12 (9 silent), haematological 11, gastrointestinal 7, skin 6.

Repeat-dose toxicology in standard species held in 74 of 121 tracks (98 tiles); its 47 misses were 32
silences, 7 explicit clean bills and 8 false alarms, and the silences fell on immune-mediated harms (10),
cardiovascular (8) and liver (6) first. Cardiovascular safety pharmacology held in 9 of 13. The human-derived safety
systems held more often but on few tracks (loss-of-function carriers 8 of 9, donor cells 7 of 10,
biochemical assays 6 of 7). The thirteen false alarms (adrenal hypertrophy, monkey skin necrosis, neural-tube
defects twice, gastric lesions, mouse bone loss, an LDL rise, alveolar proteinosis, nasal erosions, hepatocyte
IL-31, woodchuck thrombocytopenia, animal kidney toxicity, mouse brain and skin pathology) are the other cost:
harms that shaped or stopped programmes and never appeared.

## 3. Families (supplementary figure and `family_rates*.csv`)

The 1,045 systems fall into 29 families (keyword rules in `families.py`, 93 hand overrides in `overrides.csv`).
The family forests are supplementary because a family's rate follows the classes it served: in never-approved
classes every large family's yes collapsed (induced inflammatory models 8 of 34, cell-line xenografts 9 of 22,
patient-derived cells 3 of 12), in approved classes most held. Read as "which yes to discount", not as a
ranking, the table says: transgenic disease models 1 of 14, rodent behaviour and cognition 1 of 13, allergen
challenge in people 2 of 9 (seven tiles, none approved), induced inflammatory and joint models 15 of 43;
patient-derived xenografts (7 of 16) and patient cells or organoids (15 of 25) did no better than cell-line
xenografts (33 of 53) and cell lines (20 of 30), inside approved classes too (PDX 6 of 13 against 24 of 31).
Intervals are cluster bootstraps over tiles; families under four tiles are listed, not ranked.

## What this adds to the paper

The paper's claims are at the target level (genetics, prior drugs). This note is at the drug level: whether a
matched engagement readout told classes apart (it did not), what a reached target was worth for efficacy,
and which harms the safety species were silent on. It ranks nothing against genetics and says nothing about
models that would have stopped a failure.

## Robustness (details in `robustness.md`)

- **Adjudication.** On the drafters' statuses instead of the adjudicated ones: engagement held in 146 tiles
  (146), efficacy contradicted among them in 34 (35); 100 compared safety contradictions (100), 92 in common.
- **Tier definition.** Headline track's tier or best matched tier on the tile: the same picture, neither significant.
- **Duplicate packages.** Counted once per (system, harm) in the figure; track counts stated beside them.
- **Second coder.** Blind retyping of the 100 safety contras: kappa 0.87 on type, 0.93 on primary harm; the eight
  disagreements and their resolution in `robustness.md`; the first coding is frozen as `safety_types_coder1.csv`.
- **Units.** Tiles are independent in panel a (Wilson); tracks nest in tiles in the family rates (cluster
  bootstrap).

## Caveats

- Statuses were drafted and checked by language-model agents under the v3 rules (drafter–checker kappa 0.93
  on the first 30 tiles) and adjudicated where they disagreed; the sensitivity run above bounds what
  adjudication changed, not what the coding itself might have missed.
- Families are keyword rules over free-text descriptions with hand overrides; `families.csv` lists every
  assignment.
- Panel a's by-area rows and several families rest on a handful of tiles; the intervals say so.
- A family's rate follows the classes it served; the by-outcome split is the control, not a cure.
- Only positive predictive values and one discrimination test (engagement held versus class outcome) are
  measurable here. Nothing in this note is a sensitivity.

## Rebuild

```
.venv/bin/python analyses/model-system-atlas/lessons/lessons.py all
PYTHONPATH=. uv run pytest tests/test_atlas_lessons.py
```
