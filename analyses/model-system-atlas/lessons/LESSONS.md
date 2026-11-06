# What a preclinical "yes" was worth, by family of model system

Built on the 119 tracked tiles of the atlas (1,242 tracks, 849 with a compared outcome; 744 model systems), as
stored on 2026-11-06. Figure `atlas_lessons.*`, caption `atlas_lessons_caption.md`, design `DESIGN.md`,
numbers from `lessons.py all`. Statuses are the atlas's adjudicated statuses; nothing is re-adjudicated here.

## Read this first

Every tile reached Phase 2. A model that said no and was believed is not in this dataset, so the atlas cannot
say how often a model would have stopped a failure (sensitivity), nor how often a model said no. What it can
say is **what a yes was worth**: among tracks whose model gave a positive prediction, the share that patients
confirmed. That is a positive predictive value under the selection of having gone to the clinic, and every
number below is one. The reference is the pooled rate of the same question. Intervals are 95 % percentile
intervals from 2,000 cluster-bootstrap resamples of tiles, because the tracks of one tile share one trial
outcome; a family is ranked only when four or more tiles contribute. Families are keyword rules over the
model descriptions with 70 hand overrides (`families.py`, `overrides.csv`).

## 1. Which families' yes held, and which did not

Efficacy, 272 compared positive predictions, pooled **0.54 (0.46–0.62)**. Ranked families (four or more tiles):

| family | matched / compared | tiles (approved) | yes held | 95 % |
|---|---|---|---|---|
| Engineered mouse tumour (GEMM) | 4/4 | 4 (2) | 1.00 | – |
| Organ-level evoked pharmacology (guinea-pig airway, vascular, ocular) | 12/13 | 5 (4) | 0.92 | 0.77–1.00 |
| Humanised or knock-in mouse | 7/8 | 6 (1) | 0.88 | 0.57–1.00 |
| Toxicology in standard species (efficacy claims in the package) | 6/8 | 7 (2) | 0.75 | 0.43–1.00 |
| Rodent metabolic, renal or endocrine model | 16/23 | 16 (7) | 0.70 | 0.48–0.91 |
| Cell line, replicon or cell panel | 17/25 | 22 (15) | 0.68 | 0.46–0.88 |
| Infected or human-liver-chimeric animal | 4/6 | 6 (2) | 0.67 | 0.33–1.00 |
| Target loss-of-function carriers (human) | 4/6 | 6 (2) | 0.67 | 0.33–1.00 |
| Syngeneic mouse tumour | 5/8 | 6 (4) | 0.63 | 0.22–1.00 |
| Patient-derived cells, organoids or tissue | 9/15 | 13 (7) | 0.60 | 0.36–0.86 |
| Cross-indication import | 4/7 | 6 (1) | 0.57 | 0.17–0.89 |
| Cell-line xenograft | 21/38 | 27 (14) | 0.55 | 0.41–0.72 |
| Donor primary human cells or tissue | 2/4 | 4 (3) | 0.50 | 0.00–1.00 |
| Patient-derived xenograft | 7/15 | 12 (10) | 0.47 | 0.20–0.73 |
| Pharmacological challenge in people | 3/7 | 6 (1) | 0.43 | 0.14–0.71 |
| Target knockout or mutant animal | 2/6 | 6 (1) | 0.33 | 0.00–0.67 |
| Induced inflammatory or joint disease model | 11/38 | 23 (4) | 0.29 | 0.16–0.44 |
| Pharmacogenetic stratification | 1/4 | 4 (3) | 0.25 | 0.00–0.75 |
| Transgenic or genetic disease model | 1/7 | 7 (3) | 0.14 | 0.00–0.43 |
| Rodent behaviour, cognition or pain model | 1/12 | 6 (1) | 0.08 | 0.00–0.33 |
| Allergen challenge in people | 0/8 | 7 (0) | 0.00 | – |

Three families were worth nothing or close to it, and they are the ones the field leans on for whole areas:

- **Allergen challenge in people, 0 of 8** (seven tiles: allergen-immunotherapy peptides, PTGDR2 antagonists,
  anti-IL-13, inhaled steroid analogues, anti-IL-33). Chamber, nasal, conjunctival, skin and bronchial
  challenges all produced a positive proof-of-mechanism; every field trial then missed. The one track that
  predicted a null (`neg`, the LAR for a steroid) is excluded from the rate because it was not a yes.
- **Rodent behaviour, cognition and pain, 1 of 12** (six tiles; psychiatry four, neurology two). Cognition
  batteries, PCP and MK-801 reversal, prepulse inhibition and hyperlocomotion screens each said yes; the one
  match is the orexin antagonists' sleep EEG.
- **Transgenic disease models, 1 of 7**: APP, tau and PDAPP mice, Stat6VT and NC/Nga dermatitis, haemophilia
  mice. The match is a haemophilia B knockout.

And one large family sat well under the pooled rate: **induced inflammatory and joint models, 11 of 38** on 23
tiles (OVA airway, CIA and AIA, colitis, imiquimod, MC903 and hapten dermatitis, LPS, MIA and meniscal OA).
Patient-derived xenografts (7 of 15) did no better than cell-line xenografts (21 of 38), and that holds
inside approved classes too (6 of 13 versus 14 of 19); patient-derived cells and organoids (9 of 15) did no
better than cell lines and replicons (17 of 25). Human material did not buy prediction on its own.

The confound to carry: the rate of a family follows the fate of the classes it served. Allergen challenge
served no approved class, inflammatory models four of 23. `family_rates_by_outcome.csv` splits every family;
in never-approved classes the yes of every large family collapsed (inflammatory 6 of 32, xenograft 7 of 19,
patient material 1 of 7), in approved classes most held. So the table says which families' yes a biologist
should discount, not that one family causes failure.

Dose, non-derived (was the model's exposure, occupancy or regimen target reached?): **105 of 111 held
(0.95, 0.90–0.98)**; the six misses are a 5-fold bioavailability error from allometric PK, an exposure
plateau, a 2–5× underestimate of the clinical dose from a primate PD model, a stated tolerability margin that
collapsed, a GI-limited dose and an unverified target. Exposure prediction is the thing preclinical work does
well. Engagement: 174 of 193 (0.90).

## 2. A reached target is not a disease prediction

Engagement held in **105 of 119 tiles**. In 24 of those (23 %) the efficacy headline was contradicted, and
the readout that was closest to the target was the least informative:

| engagement readout | tiles with engagement held | efficacy contradicted |
|---|---|---|
| direct (occupancy, free target) | 27 | 9 (33 %) |
| proximal (the target's own product) | 39 | 8 (21 %) |
| downstream biomarker | 37 | 7 (19 %) |

By area: neurology 3 of 6, allergy 3 of 3, respiratory 3 of 9, psychiatry 1 of 3, oncology 7 of 37
(`engagement_vs_efficacy.csv`). Of the 60 dose tracks the atlas scored as "reached, not enough" (derived from
efficacy; 44 tiles), what had been reached was the model's regimen in 20, its exposure in 20, its PD biomarker
in 13 and its occupancy in 7 (`dose_derived.csv`). A PD biomarker that moves in people is an engagement
result; the atlas's record says it has been read as a disease prediction and was not one, most of all in
CNS and in allergy and airways.

## 3. What the safety models missed

Safety, 209 compared predictions, pooled **0.65 (0.59–0.72)**. Three contradictions typed as having no
admissible comparison are left out. The 73 remaining contradictions (`safety_types.csv`, `safety_misses.csv`):

| type | tracks | meaning |
|---|---|---|
| silent | 40 (+1 not showable) | the model made no prediction on a harm its species could have shown; patients had it |
| stated safe | 23 | the model said there would be no such harm; patients had it |
| false alarm | 9 | the model predicted a harm patients never had |

By harm (each counted once per track): cardiovascular 12 (QT prolongation twice after clean hERG and
telemetry, hypertension, bradycardia, heart failure), metabolic, endocrine and bone 13, liver 11, immune 10,
CNS 8, haematological 7, gastrointestinal 6, skin 6. **Repeat-dose toxicology in standard species** held in
47 of 80 tracks (70 tiles); its 33 misses were 23 silences, 5 explicit clean bills and 5 false alarms, and
the silences were on immune-mediated harms (7), liver (5) and cardiovascular (5) first. Cardiovascular safety
pharmacology held in 9 of 13, a target-knockout animal in 9 of 13, a cell-line xenograft in 5 of 13. The
human-derived systems held more often but on few tracks: loss-of-function carriers 6 of 7, donor cells 3 of
4, biochemical assays 5 of 5. The nine false alarms (adrenal hypertrophy, monkey skin necrosis, neural-tube
defects, gastric lesions, bone loss, an LDL rise, alveolar proteinosis, nasal erosions, IL-31) are the other
cost: harms that shaped or stopped programmes and never appeared.

## What this adds to the paper

The paper's claims are at the target level (genetics, prior drugs). This note is at the drug level and within
kind: which families of preclinical system earned their yes. It does not rank animal against genetics against
in silico, and it does not say any family would have stopped a failure.

## Caveats

- Statuses were drafted and checked by language-model agents under the v3 rules (drafter–checker κ 0.93 on
  the first 30 tiles) and adjudicated where they disagreed; a family's rate inherits any bias in that coding.
- Families are keyword rules over free-text model descriptions with 70 hand overrides; two systems keep
  two families by question. Another reviewer would draw some lines differently; `families.csv` lists every
  assignment.
- The unit of independence is the tile; several families rest on five or six tiles and their intervals say so.
- A family's rate follows the classes it served; the outcome split above is the control, not a cure.
- Only a positive predictive value is measurable here. Nothing in this note is a sensitivity.

## Rebuild

```
.venv/bin/python analyses/model-system-atlas/lessons/lessons.py all
PYTHONPATH=. uv run pytest tests/test_atlas_lessons.py
```
