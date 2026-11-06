# What a preclinical "yes" was worth

Built on the 119 tracked tiles of the atlas (1,242 tracks, 849 with a compared outcome; 744 model systems),
as stored on 2026-11-06. Main figure `atlas_lessons.*` (two panels), supplementary `atlas_lessons_families.*`,
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

The engagement headline matched in **105 of 119 tiles**: in 50 of 53 classes that were later approved and in
55 of 66 that never were (Fisher p = 0.09). A matched engagement readout did not separate the classes that
would succeed from the ones that would fail. Among the 105, efficacy was contradicted in 24: 23 of the 55
never-approved classes (42 %, 30–55) and 1 of the 50 approved (2 %, 0–10).

| engagement readout of the headline track | tiles held | efficacy contradicted | 95 % |
|---|---|---|---|
| direct (occupancy, free target) | 27 | 9 (33 %) | 19–52 |
| proximal (the target's own product) | 39 | 8 (20 %) | 11–36 |
| downstream biomarker | 37 | 7 (19 %) | 10–34 |

The tier did not matter (chi-square p = 0.35; with the best tier among a tile's matched engagement tracks
instead of the headline's, p = 0.50). The point estimate for direct occupancy is the worst, and that is all
it is. By area, the contradicted share runs from 0 of 4 in gastroenterology and 1 of 10 in infectious disease
to 3 of 6 in neurology and 3 of 3 in allergy (`engagement_summary.csv`).

The 60 dose tracks the atlas scored as "reached, not enough" (44 tiles; `dose_derived.csv`) say what had been
reached: the model's regimen in 20, its exposure in 20, its PD biomarker in 13, its occupancy in 7. Non-derived
dose predictions, which ask only whether the exposure or regimen target was reached, held in 105 of 111
(0.95, 0.90–0.98). Exposure is what preclinical work predicts well; a PD biomarker that moves in people is an
engagement result and the record shows it being read as a disease result.

## 2. What the safety models missed (figure, panel b)

Safety predictions held in 136 of 208 compared tracks (0.65, 0.59–0.72). A prediction is a stated finding or
silence on a harm the species could have shown (brief v3). The 76 contradicted tracks were typed from the
entry text by two coders, the second blind to the first: agreement on type 70 of 76 (kappa 0.87),
on primary harm class 71 of 76 (kappa 0.93), every row sharing at least one harm class; the six type
disagreements are listed in `robustness.md` and were resolved by re-reading the entry (three to the second
coder, three kept). Four tracks typed as having no admissible comparison leave the count.

| type | tracks | meaning |
|---|---|---|
| silent | 39 (+1 not showable) | no prediction on a harm the species could have shown; patients had it |
| stated safe | 23 | the model said there would be no such harm; patients had it |
| false alarm | 9 | the model predicted a harm patients never had |

Four of the 72 are one package serving several tiles (a cynomolgus toxicology package behind three PD-1
tiles, one behind two, a pamiparib xenograft behind two), so the figure counts each (system, harm) once:
**68 model systems, 86 unique system–harm pairs**. By harm: cardiovascular 13 (7 silent, 6 stated safe: QT
prolongation twice after a clean hERG and dog telemetry, hypertension after "no blood-pressure effect",
bradycardia after S1P3 sparing, heart failure, a blood-pressure rise the knockout said would not come),
metabolic, endocrine and bone 13 (5 silent, 5 stated safe, 3 false alarms), liver 11 (8 silent),
immune-mediated 9 (7 silent), CNS 8, haematological 6, gastrointestinal 6, skin 5.

Repeat-dose toxicology in standard species held in 47 of 80 tracks (70 tiles); its 33 misses were 24
silences, 4 explicit clean bills and 5 false alarms, and the silences fell on immune-mediated harms (8),
cardiovascular (5) and liver (5) first. Cardiovascular safety pharmacology held in 9 of 13. The human-derived safety
systems held more often but on few tracks (loss-of-function carriers 6 of 7, donor cells 3 of 4,
biochemical assays 5 of 5). The nine false alarms (adrenal hypertrophy, monkey skin necrosis, neural-tube
defects, gastric lesions, mouse bone loss, an LDL rise, alveolar proteinosis, nasal erosions, hepatocyte IL-31)
are the other cost: harms that shaped or stopped programmes and never appeared.

## 3. Families (supplementary figure and `family_rates*.csv`)

The 744 systems fall into 29 families (keyword rules in `families.py`, 70 hand overrides in `overrides.csv`).
The family forests are supplementary because a family's rate follows the classes it served: in never-approved
classes every large family's yes collapsed (induced inflammatory models 6 of 32, cell-line xenografts 7 of 19,
patient-derived cells 1 of 7), in approved classes most held. Read as "which yes to discount", not as a
ranking, the table says: allergen challenge in people 0 of 8 (seven tiles, none approved), rodent behaviour
and cognition 1 of 12, transgenic disease models 1 of 7, induced inflammatory and joint models 11 of 38;
patient-derived xenografts (7 of 15) and patient cells or organoids (9 of 15) did no better than cell-line
xenografts (21 of 38) and cell lines (17 of 25), inside approved classes too (PDX 6 of 13 against 14 of 19).
Intervals are cluster bootstraps over tiles; families under four tiles are listed, not ranked.

## What this adds to the paper

The paper's claims are at the target level (genetics, prior drugs). This note is at the drug level: whether a
matched engagement readout told classes apart (it did not), what a reached target was worth for efficacy,
and which harms the safety species were silent on. It ranks nothing against genetics and says nothing about
models that would have stopped a failure.

## Robustness (details in `robustness.md`)

- **Adjudication.** On the drafters' statuses instead of the adjudicated ones: engagement held in 103 tiles
  (105), efficacy contradicted among them in 25 (24); 78 compared safety contradictions (76), 71 in common.
- **Tier definition.** Headline track's tier or best matched tier on the tile: the same picture, neither significant.
- **Duplicate packages.** Counted once per (system, harm) in the figure; track counts stated beside them.
- **Second coder.** Blind retyping of the 76 safety contras: kappa 0.87 on type, 0.93 on primary harm; the six
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
