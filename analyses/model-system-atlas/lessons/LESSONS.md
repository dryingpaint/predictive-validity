# What a preclinical "yes" was worth

Built on the 166 tracked tiles of the atlas (1,386 tracks, 753 with a compared outcome; 1,050 model systems),
as stored on 2026-11-15. A track is one model system for one member drug by one route; a prediction published
after the patient result it is scored against is a retrodiction and is not counted. Main figure
`atlas_lessons.*` (two panels), supplementary `atlas_lessons_families.*`, caption `atlas_lessons_caption.md`,
design and decisions `DESIGN.md`, checks `robustness.md`; everything from `lessons.py all`. Statuses are the atlas's
adjudicated statuses; nothing is re-adjudicated here.

## Read this first

Every tile reached Phase 2. A model that said no and was believed is not in this dataset, so nothing here is a
sensitivity: the atlas cannot say how often a model would have stopped a failure. What it can say is what a
positive prediction was worth once the drug was in patients, and, for engagement, whether a matched readout
distinguished classes that went on to approval from classes that did not (both outcomes are present, so that
one is a real discrimination test). Intervals are Wilson 95 % on tiles where tiles are the unit, and
cluster-bootstrap 95 % over tiles where tracks are counted. Every test and sensitivity run is in
`robustness.md`, written by the script. A track is one model system for one member drug by one route, and a
prediction counts only if it came before the patient result, each dated by its earliest public report (congress
abstracts and press releases included): for engagement and efficacy, before any patient result on the same
target; for dose and safety, before the same drug's own result. A later one is a retrodiction and is left out
of every count.

## 1. A reached target is not a disease prediction (figure, panel a)

The engagement headline matched in **78 of 166 tiles**: in 37 of 78 classes that were later approved and in
41 of 88 that never were (Fisher p = 1.00). A matched engagement readout did not separate the classes that
would succeed from the ones that would fail. Among the 78, efficacy was contradicted in 20: 18 of the 41
never-approved classes (44 %, 30–59) and 2 of the 37 approved (5 %, 2–18).

| engagement readout of the headline track | tiles held | efficacy contradicted | 95 % |
|---|---|---|---|
| direct (occupancy, free target) | 21 | 7 (33 %) | 17–55 |
| proximal (the target's own product) | 27 | 5 (19 %) | 8–37 |
| downstream biomarker | 28 | 6 (21 %) | 10–40 |

The tier did not matter (chi-square p = 0.46; with the best tier among a tile's matched engagement tracks
instead of the headline's, p = 0.43). The point estimate for direct occupancy is the worst, and that is all
it is. By area, the contradicted share runs from 0 of 5 in endocrine and 0 of 3 in metabolic
to 2 of 4 in respiratory and 2 of 3 in allergy (`engagement_summary.csv`).

Dose predictions, which ask only whether the exposure, occupancy or regimen target the model stated was reached
in people and its stated tolerability margin held, held in 117 of 133 compared tracks (0.88, 0.82–0.93). A drug
that reached its target and still failed is an efficacy failure, counted once. Exposure is what preclinical work
predicts well; a PD biomarker that moves in people is an engagement result and the record shows it being read
as a disease result.

## 2. What the safety models missed (figure, panel b)

Safety predictions held in 176 of 303 compared tracks (0.58, 0.53–0.64). A prediction is a stated finding or
silence on a harm the species could have shown (brief v3). The 127 contradicted tracks (113 system–tile rows) were
typed from the entry text by two coders, the second blind to the first: agreement on type 107 of 113 (kappa 0.92),
on primary harm class 107 of 113 (kappa 0.94), all but one row sharing at least one harm class; the six type
disagreements are listed in `robustness.md` and were resolved by re-reading the entry (two to the second
coder, four kept). No track was typed as having no admissible comparison.

| type | tracks | meaning |
|---|---|---|
| silent | 51 (+2 not showable) | no prediction on a harm the species could have shown; patients had it |
| stated safe | 52 | the model said there would be no such harm; patients had it |
| false alarm | 22 | the model predicted a harm patients never had |

Twenty of the 127 repeat a system: one package serving several tiles (a cynomolgus toxicology package behind
three PD-1 tiles, four behind two, a pamiparib xenograft among them) or several drugs of one tile, so the figure
counts each (system, harm) once: **107 model systems, 137 unique system–harm pairs**. By harm: cardiovascular 23
(9 silent, 12 stated safe: QT prolongation twice after a clean hERG and dog telemetry, hypertension after "no
blood-pressure effect", bradycardia after S1P3 sparing and after clean dog telemetry, heart failure, atrial
fibrillation after clean dog telemetry, a serious cardiovascular-event imbalance three human systems had cleared,
a blood-pressure rise the knockout said would not come, hypertension after a xenograft "well tolerated"; 2 false
alarms), metabolic, endocrine and bone 20 (3 silent, 13 stated safe, 4 false alarms), immune-mediated 14
(10 silent), haematological 14, CNS 13, liver 11 (8 silent), gastrointestinal 11, skin 8.

Repeat-dose toxicology in standard species held in 62 of 118 tracks (86 tiles); its 56 misses were 37
silences, 6 explicit clean bills and 13 false alarms, and the silences fell on immune-mediated harms (10),
cardiovascular (9) and liver (6) first. Cardiovascular safety pharmacology held in 9 of 17. The human-derived safety
systems held more often but on few tracks (loss-of-function carriers 11 of 13, donor cells 8 of 11,
biochemical assays 7 of 8). The 22 false alarms (adrenal hypertrophy, monkey skin necrosis, neural-tube
defects twice, gastric lesions, mouse bone loss, rat bone accretion, an LDL rise, alveolar proteinosis three
times, nasal erosions, hepatocyte IL-31, woodchuck thrombocytopenia, animal kidney toxicity twice, mouse brain and
skin pathology, a beta-2 heart-rate rise, heart and pancreas harm, rat joint destruction, dog retinal harm,
bleeding) are the other cost: harms that shaped or stopped programmes and never appeared.

## 3. Families (supplementary figure and `family_rates*.csv`)

The 1,050 systems fall into 29 families (keyword rules in `families.py`, 93 hand overrides in `overrides.csv`).
The family forests are supplementary because a family's rate follows the classes it served: in never-approved
classes every large family's yes collapsed (induced inflammatory models 9 of 57, cell-line xenografts 4 of 21,
patient-derived cells 3 of 12), in approved classes most held. Read as "which yes to discount", not as a
ranking, the table says: transgenic disease models 1 of 23, rodent behaviour and cognition 0 of 15, allergen
challenge in people 1 of 10 (six tiles, none approved), induced inflammatory and joint models 12 of 62;
patient-derived xenografts (7 of 21) did no better than cell-line xenografts (20 of 45), inside approved classes
too (PDX 6 of 17 against 16 of 24), and patient cells or organoids (16 of 26) only matched cell lines (17 of 29).
Intervals are cluster bootstraps over tiles; families under four tiles are listed, not ranked.

## What this adds to the paper

The paper's claims are at the target level (genetics, prior drugs). This note is at the drug level: whether a
matched engagement readout told classes apart (it did not), what a reached target was worth for efficacy,
and which harms the safety species were silent on. It ranks nothing against genetics and says nothing about
models that would have stopped a failure.

## Robustness (details in `robustness.md`)

- **Adjudication.** On the drafters' statuses instead of the adjudicated ones: engagement held in 96 tiles
  (78), efficacy contradicted among them in 20 (20); 111 compared safety contradictions by system and tile (113),
  110 in common.
- **Tier definition.** Headline track's tier or best matched tier on the tile: the same picture, neither significant.
- **Duplicate packages.** Counted once per (system, harm) in the figure; track counts stated beside them.
- **Second coder.** Blind retyping of the 113 safety contras: kappa 0.92 on type, 0.94 on primary harm; the six
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
