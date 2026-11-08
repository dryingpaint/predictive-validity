# Step 1 result: what "engaged" rests on, by readout kind

_Pull of 2026-11-02 (`labels.csv`, 3,845 labelled stops; every labelled stop, all phases and years, not only
the report's cohort). 2,067 rows with a human-data verdict were extracted from the rationale text by 19
independent extractors under `EXTRACTION_BRIEF.md`; `readouts.csv` is the record, `vocabulary.csv` the
canonical names. A 21-row stratified hand check found 21 defensible calls, two of them borderline
(apoA-I replacement coded as target level; a PK/PD-modelled occupancy coded as measured)._

## The split

| readout kind | engaged, shown in humans (1,260) | not engaged (193) | engaged by inference from another disease (614) |
|---|---|---|---|
| occupancy: PET/SPECT, free or total target, target activity in blood cells, ex-vivo blockade of a stimulus, target-cell depletion | 598 (47 %) | 75 | 56 |
| target's own product: enzyme product or substrate, ligand accumulation, viral load, transgene protein, target phosphorylation in tissue | 382 (30 %) | 72 | 74 |
| downstream biomarker or physiology | 257 (20 %) | 28 | 197 |
| clinical response used as the engagement evidence | 1 | 3 | 286 |
| exposure only | 9 | 11 | 0 |
| no readout named | 13 | 4 | 1 |

Within the 598 occupancy rows, 90 are PET or SPECT occupancy (7 % of all measured-engaged programs);
382 are blood assays (receptor occupancy on circulating cells, free or total target, ex-vivo blockade);
37 are tissue assays; 52 do not state the compartment.

## Specificity, as the extractor read it

Among the 914 programs whose engagement was measured with this drug (not inferred from another
disease), the extractor judged whether anything other than this target could move the readout:

| readout kind | specific to the target | not specific | unsure |
|---|---|---|---|
| occupancy | 398 | 15 | 25 |
| target's product | 155 | 60 | 58 |
| downstream biomarker | 1 | 149 | 41 |

So the 20 % of "engaged" verdicts that rest on a downstream marker rest almost entirely on markers that
other mechanisms also move. That is the population the anchor question (step 3) is about: for those
programs, what tied the marker to the target in humans, and when.

## Where the evidence came from

Of the 1,260 measured-engaged programs, 914 were measured with this drug in healthy volunteers or in the
disease, 333 in patients of another disease, 2 with another drug on the target. The report's own flags
say 533 of 910 (today's run) were shown before the failed trial started; step 4 crosses the readout kind
with those flags and with the failure code (918 of the 1,260 carry F2, "engaged, disease did not respond").

## Vocabulary

1,326 canonical names over 2,067 rows; 936 used once; 699 distinct target prefixes. The names are
inflated by the first-symbol rule (a DAT occupancy study filed under SLC6A2 because that symbol came
first) and by free coining (`BTK:occupancy`, `BTK:pbmc_occupancy`, `BTK:peripheral_b_cell_occupancy`).
Layer 2 is therefore sized by targets, about 700 before synonym collapse, and the collapse is the first
job of step 3. Only two canonical names carry conflicting kinds across rows; the batches disagreed more
at the level of naming than of kind.

## Caveats

- The extractors read rule 3 two ways for programs whose engagement was inferred from efficacy elsewhere:
  some took the measured marker from the other disease, some took the clinical response. The 614
  inferred rows are therefore reported as their own group and not pooled with the measured ones. Rule 3
  is to be sharpened before any re-run.
- Kind boundaries were applied consistently within a batch but not always across batches at the margins
  (ligand accumulation, target-cell depletion, modelled occupancy). `vocabulary.csv` is where those get
  one answer each; `kind_final` survives re-runs.
- The extractor's specificity call is a face-value judgement from the rationale, not research. Step 3
  replaces it with an anchor and a date per (target, readout).
- 720 stops have no primary target in the DB; their names are keyed by drug.
