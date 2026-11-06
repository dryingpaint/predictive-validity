# Atlas lessons: what a preclinical "yes" was worth (design)

Branch `atlas-lessons`, off `atlas-named-contexts` (PR #81), downstream of the 119-tile store. Written 2026-11-06.

## Intent

The atlas records, per disease × mechanism and per question, every model system that was compared with
patients. The main figure says *whether* each class's models predicted the clinic. This analysis asks what
the record says about *kinds of model*: which families of preclinical system earned their "yes" when the
drug went into patients, which did not, where a reached engagement target still left efficacy unpredicted,
and which harms the safety species were silent on. The intended reader is a biologist deciding what to build
or trust; the output may go into the paper as a figure and a short section.

Why now: PR #81 completes the 119 tracked tiles (1,242 tracks, 849 with a compared outcome). Until that
store existed, the paper's REPORT.md (line 125) says drug-level animal-model and engagement testing "could
not be measured". Now it can, at the model-family level.

## Framing that every output carries

Every tile reached Phase 2. A model that said "no" and was believed is not in this dataset. So the atlas
cannot measure sensitivity or specificity of a model family; it can measure **what a yes was worth**: among
tracks whose model gave a positive prediction (efficacy will hold, this exposure is enough, no harm, target
reached), the share that patients contradicted. This is a positive predictive value under the selection of
having gone to the clinic. It is stated once in the figure legend and the note, before any number.

## Goals

1. A family taxonomy over the 744 model systems (one per tile × `model_id`): a keyword rule set over the
   model text, with a hand-reviewed override file. Every track is assigned; the bucket of hand overrides is
   listed, never silent.
2. Per family and question: the yes-PPV (matched / compared, among yes-predictions) with a 95 % interval
   from a cluster bootstrap over tiles (tracks in one tile share one trial outcome), beside the pooled rate
   of that question. Families with fewer than four tiles contributing a yes are listed, not ranked.
3. Engagement proxy held, disease failed: (a) the dose contras derived from efficacy ("target reached, not
   enough"), typed by what was reached (exposure, occupancy, PD biomarker, regimen); (b) the engagement ×
   efficacy headline crosstab per tile, by area and by engagement `readout_tier`.
4. Safety: the 76 compared safety contras, each typed by hand as **silent** (the model made no prediction on
   a harm its species could have shown and patients had it), **stated-safe** (the model said no harm,
   patients had it), **false alarm** (the model predicted a harm patients never had), or **untested** in the
   patient record; and by harm class (immune, liver, cardiovascular, metabolic/endocrine/bone,
   haematological, GI, CNS, skin, ocular, renal, musculoskeletal, other) and by the model's species or
   system. Output: harm class × type, and harm class × family.
5. One journal-format figure (`atlas_lessons.{png,pdf,svg}`, 183 mm, atlas palette) with three panels (a:
   family yes-PPV forest by question; b: engagement held × efficacy outcome by area; c: safety misses by
   harm class, split silent / stated-safe / false alarm) and `LESSONS.md` with the framing, the three
   findings with numbers, and the caveats.
6. Tests over synthetic rows for the family rules, the yes/no/harm prediction reading, the PPV and bootstrap
   math, and the safety typing merge. Database access stays read-only through `report.frame.query`.

## Non-goals and anti-goals

- No ranking of **model kinds** (animal vs genetics vs in silico): the paper owns the genetics claim at
  target level; this analysis is within-kind, at family level, and says so.
- No re-adjudication of any status. Statuses come from the store (adjudicated where the adjudicator decided).
- No claim about sensitivity, "models that would have stopped a failure", or how often a model said no.
- No cross-family head-to-head inside a cell as evidence of one family beating another (timing-confounded;
  the dissent pairs are reported descriptively in LESSONS.md, not drawn).
- Anti-goal: a figure that reads as "rodent models are bad". Every panel carries the base rate of its question.
- Anti-goal: numbers in prose without their n and interval.

## Data and definitions

Input: `preclin.atlas_track_entry` ⨝ `atlas_track_verdict` via `glance.load()` (so adjudicated statuses and
`final` are the atlas's own), `drafts/v3/tiles.json` (`furthest_phase`, `area`, `class_programs`), and the
figure's `glance.csv` for cell headlines.

- **Track**: (slug, question, modality, model_id). Its outcome is the latest non-drop `final` on the track.
- **Compared track**: latest final ∈ {same, neg, other, contra}. `untested` and `retro` are excluded from
  every rate (a retrodiction is not a prediction; decision 10).
- **Prediction direction** (`pred`): `yes` by default. `no` when the track's `final` is `neg` or the entry
  text records that the model's own data fell below the class bar (hand-flagged; 1 track). `harm` for safety
  tracks where the model predicted a harm (hand-typed in the safety review). Only `pred == yes` enters the
  yes-PPV; `no` and `harm` are reported in their own rows.
- **Yes-PPV**: matched / (matched + contradicted) over compared yes-tracks, where matched = {same, other}.
- **Interval**: percentile 95 % from 2,000 cluster-bootstrap resamples of tiles (seed 76), reported with
  n tracks and n tiles. Wilson on tracks is not used because tracks nest in tiles.
- **Rankable**: ≥ 4 tiles contribute a compared yes-track to that family × question. Others are listed
  with their n and no interval.
- **Reference line**: the pooled yes-PPV of the same question over all compared yes-tracks.
- **Class outcome** (context column, not a panel): `furthest_phase == 4` approved (53 tiles) vs never
  approved (66); the yes-PPV per family is also tabulated by this split in LESSONS.md.

## The family taxonomy

`lessons/families.py` holds an ordered list of (family, model_kind restriction, regex) rules applied to
`model text + model_id` per system; the first match wins; animal rules are restricted to `model_kind ==
animal` and run first, then unrestricted ex-vivo rules, then human-challenge, human-genetic, in-silico and
cross-indication rules keyed to their kind. `lessons/overrides.csv` (slug, model_id, family, note) is applied
on top and is the hand-review record; a rule change never silently moves an overridden system. The rules
and overrides must leave no system `unassigned`; the build fails loudly otherwise.

| code | family | typical members |
|---|---|---|
| `tox_repeat_dose` | repeat-dose toxicology in standard species | rat/dog/monkey GLP tox, carcinogenicity, EFD, local tolerance, juvenile |
| `tox_cv_safety_pharm` | cardiovascular safety pharmacology (animal) | hERG + dog/monkey telemetry, QTc, heart rate |
| `xenograft_cell_line` | human tumour cell-line xenograft | MCF-7, H1975, A431, MM.1S in nude/SCID/NSG mice |
| `xenograft_pdx` | patient-derived xenograft | PDX panels, avatars, primary-blast xenografts |
| `syngeneic_tumour` | syngeneic / immunocompetent mouse tumour | MC38, CT26, B16, A20, LLC |
| `gemm_tumour` | genetically engineered or autochthonous mouse tumour | KPC, Kras/p53 lung, RPM SCLC, K14cre Brca1 |
| `humanised_mouse` | humanised or knock-in mouse | hPD-1 knock-in, hCTLA4, hGnRHR, PBMC-NSG, human-cytokine challenge |
| `target_knockout` | target knockout or mutant animal (genetic proxy for the drug) | Gcgr-/-, PD-1-/-, S1P3-/-, Hsd11b1-/-, TrkA null, p110δ D910A |
| `genetic_disease_model` | transgenic or genetic disease model | Tg2576, P301S tau, HBV-tg, Mdr2-/-, IL-10-/- colitis, F8/F9 knockout as the disease |
| `infected_or_chimeric_liver` | infected animal or human-liver-chimeric mouse | uPA/SCID, PXB, TK-NOG, chimpanzee, woodchuck, duck, influenza, Mtb |
| `inflammatory_disease_model` | induced inflammatory, immune or joint disease model | OVA, CIA/AIA, K/BxN, colitis, imiquimod, MC903, oxazolone, LPS, MIA/MMT OA |
| `metabolic_disease_model` | rodent metabolic, renal or endocrine disease model | db/db, DIO, STZ, ZDF, NASH diets, Dahl, 5/6 Nx, HPG axis |
| `behaviour_cns_model` | rodent behaviour, cognition, pain or CNS pharmacology | water maze, NOR, PPI, hyperlocomotion, allodynia, EEG, microdialysis |
| `pkpd_occupancy_animal` | PK, occupancy, PET or PK-PD in animals | NHP PET, CSF PK/PD, brain penetration, allometric PK from animals |
| `organ_pharmacology_animal` | organ-level evoked-response pharmacology | guinea-pig airway, CIDV, organ bath, ocular outflow |
| `nonrodent_disease_model` | non-rodent disease or pharmacology model | haemophilia dogs, dog KCS, pig clamp, monkey eye, NHP AAV NAb |
| `patient_material_ex_vivo` | patient-derived cells, organoids or tissue | rectal organoids, PDO, patient blasts, lesional skin, patient PBMC |
| `donor_primary_human` | healthy-donor primary human cells, blood or tissue | whole blood, PBMC, islets, iPSC-CM, isolated bronchi/arteries |
| `cell_line_assay` | engineered or immortalised cell line, replicon, panel | Ba/F3, FRT, HEK biosensor, Huh-7 replicon, CCLE panels |
| `biochemical_assay` | biochemical, binding, enzyme or transporter assay | hERG, OCT2, CYP, SPR, recombinant enzyme |
| `allergen_challenge_human` | allergen challenge in people | chamber, nasal, skin, conjunctival, bronchial challenge |
| `pharmacological_challenge_human` | pharmacological challenge or physiology study in people | ketamine, scopolamine, LPS, histamine, infusion/clamp, VEP |
| `target_lof_genetics` | target loss-of-function carriers, Mendelian disease, MR | Mahvash, CRD, FRG, CIPA, C5 deficiency, IL23R R381Q |
| `pharmacogenetic_stratification` | pharmacogenetic or genomic responder stratification | ADRB2 genotype, TNFR1 rs1800693, CD33 splice, TMB rule |
| `pbpk_translational` | PBPK, allometric or translational PK/PD from preclinical data | Simcyp, GastroPlus, IVIVE, rabbit decay, xenograft-to-human PK/PD |
| `poppk_exposure_response` | population PK / exposure-response from clinical data | NONMEM phase 1/2 models, C-QTc, regimen simulation |
| `qsp_mechanistic` | QSP or mechanistic disease model | viral kinetics, 4GI, Aβ QSP, DILIsym, CFD |
| `expression_classifier` | gene-expression or structure-based classifier | PARPi-7, DRP, GFS, EGFR structural classes |
| `cross_indication` | cross-indication import | a model or trial from another disease applied to this one |

Hand review: the prototype rules leave 13 of 744 systems unassigned and misfile roughly 20 more
(kinase-dead knock-ins under humanised, hemophilia dogs under humanised, clinical-data PK models under PBPK,
retinal damage and reproductive-tox models under PK-PD). The override file records each with a one-line
reason. The reviewer is the builder, reading the model text and `model_id`; no new source reading.

As built: the rules run per **track** over the model text of that track's own entries plus the `model_id`
(a system can be a toxicology study on its safety track and an occupancy study on its engagement track);
an override is per system and applies to all its tracks. 70 systems (120 tracks) are overridden after a
read of every family's membership; two systems keep two families by question (`tori-cynomolgus-monkey`,
`rat-dog-sleep-eeg`) and `families.csv` shows it. No track is unassigned.

## Outputs

`lessons/lessons.py` (one script, read-only on the database):

- `families` → `lessons/families.csv`: slug, model_id, model_kind, model, family, source (rule | override),
  plus the unassigned list printed; exits non-zero if any remain.
- `rates` → `lessons/family_rates.csv`: family, question, pred, n_tracks, n_tiles, matched, contra, ppv,
  lo, hi, rankable, pooled; and `family_rates_by_outcome.csv` with the approved / never-approved split.
- `engagement` → `lessons/engagement_vs_efficacy.csv` (tile-level: area, engagement headline + readout_tier,
  efficacy headline) and `lessons/dose_derived.csv` (the 60 derived dose contras with their reached-target
  type from `lessons/dose_types.csv`, hand-typed).
- `safety` → `lessons/safety_misses.csv` from `lessons/safety_types.csv` (hand-typed: slug, model_id, type,
  harm_class, note) joined to the track table and the family.
- `figure` → `atlas_lessons.{png,pdf,svg}` beside the other atlas figures and `lessons/atlas_lessons_caption.md`.
- `all` runs them in order. `LESSONS.md` is written by hand from the CSVs and quotes their numbers.

Hand-typed CSVs (`safety_types.csv`, `dose_types.csv`, `overrides.csv`) are inputs, committed, and the
script refuses to run `safety` or `engagement` if a compared contra is missing from them.

## Figure

183 mm wide, Helvetica 5–7 pt, `glance_nature.RC` and its colours (CAPABLE blue for matched, coral for
contradicted, grey for untested, violet unused). Panel a: for efficacy, safety and dose (engagement's rate is
0.90 everywhere and goes to the supplement table), families sorted by yes-PPV, a dot with its interval and
the pooled line, n tiles printed at the right; non-rankable families below a rule, dot only. Panel b: one
bar per area, tiles whose engagement headline matched, split by efficacy headline (matched / contradicted /
not compared); n per bar. Panel c: harm class rows, stacked by miss type; the family of the silent model as
a small annotation where one family dominates. Labels wrapped with `glance_nature.wrap`, nothing cut.

## Tests (`tests/test_atlas_lessons.py`)

Synthetic rows, no database: a rule fires on its keyword and not on a sibling; an override wins over a rule;
`pred` reads `neg` as `no`; a retro or untested track never enters a rate; PPV and the cluster bootstrap on a
hand-computable toy (two tiles, four tracks) give the expected point and a wider interval than a track-level
Wilson; a safety contra missing from `safety_types.csv` raises.

## Repo layout, commands, PR

```
analyses/model-system-atlas/lessons/   DESIGN.md, LESSONS.md, lessons.py, families.py, overrides.csv,
                                        safety_types.csv, dose_types.csv, families.csv, *_rates.csv, ...
analyses/model-system-atlas/atlas_lessons.{png,pdf,svg}
tests/test_atlas_lessons.py
.venv/bin/python analyses/model-system-atlas/lessons/lessons.py all
PYTHONPATH=. uv run pytest tests/test_atlas_lessons.py
```

One PR from `atlas-lessons` into `atlas-named-contexts` (so it lands after #81), body: the framing sentence,
the figure, the three findings with n, what is not claimed. README of the atlas gains one row per output.

## Left to the builder

Exact regexes and their order; the bootstrap implementation; panel geometry; the wording of LESSONS.md;
whether `other` (platform-only safety match, 1 track) is shown as matched (it is counted as matched).

## Decisions taken here

- Unit of independence is the tile, hence the cluster bootstrap; tracks are the unit of counting.
- A family needs four tiles to be ranked; below that it is listed.
- `retro` is excluded from every rate, including the reference line.
- The analysis lives in `lessons/` under the atlas, not in a new top-level analysis.
- Hand-typed files are committed inputs with a `note` column, in the style of `lists/class_audit/reviews.csv`.

Settled after the builder check (2026-11-06):

- **Safety is not a yes-PPV.** A matched safety track is as often "the predicted harm appeared" as "the clean
  bill held", so the safety row in panel a is the share of safety predictions that held (matched / compared,
  every compared safety track), labelled so. The 76 contras are typed; matched tracks are not. Under the
  atlas's own rule (brief v3, safety) silence on a harm the species could have shown is a contradiction, so
  `silent` stays in the rate. Two further types exist for the hand review only: `no_comparison` (the entry
  says no admissible comparison was found, or the prediction was never tested in patients) leaves the rate
  and is listed as a caveat; `not_showable` (the species could not have shown the harm) keeps the stored
  status, is drawn with `silent`, and is noted. The hand review is 76 rows, not every safety track.
- **Derived dose contras leave the dose rate.** A dose contra with `derived_from == efficacy` is efficacy's
  failure counted on a second question (the atlas figure hatches it). The dose row in panel a and
  `family_rates.csv` use only dose tracks that are not derived; derived tracks are their own row
  (`question = dose (derived)`) in the CSV and the whole of `dose_derived.csv`.
- `pred` is therefore: `yes` for efficacy, engagement and non-derived dose tracks (except the `neg` track,
  `no`); `safety` for safety tracks; `derived` for derived dose tracks.
Rework after Stephen's review (2026-11-06, afternoon):

- **The family ranking leaves the main figure.** A family's rate follows the classes it served (in
  never-approved classes every large family's yes collapses), so a forest that ranks families reads as a
  model claim and is mostly a disease claim. The forests move to `atlas_lessons_families.*`, supplementary,
  with the by-outcome split as the control; the main figure is the two drug-level panels.
- **Panel a (engagement held, efficacy failed)** adds rows by class outcome, prints the contradicted share
  with a Wilson 95 % interval on every row, and the readout-tier contrast is reported with its test
  (chi-square p = 0.35; alternative tier definition p = 0.50): a point estimate, not a claim.
- **Panel b (safety misses)** counts each (model system, harm, type) once, because one toxicology package
  can serve several tiles (a monkey package serves three PD-1 tiles). Track counts stay in the label.
- **A second, blind coder** retypes the 76 safety contras from the entry text; agreement (kappa) and every
  disagreement are reported in `robustness.md`, disagreements resolved by re-reading the entry.
- **Sensitivity to adjudication:** every panel is recomputed on the drafters' statuses; the differences are
  reported in `robustness.md`.
- `lessons.py robust` writes `robustness.md` so the checks are reproducible, not asserted.
- The store holds all 119 tiles (2,428 entries, 1,242 tracks); `model_kind` is a key of each entry's
  `fields` JSON with six values (animal, ex_vivo, in_silico, human_challenge, human_genetic,
  cross_indication); the prototype rules and their misfile list are the builder's own scratch and are
  carried into `families.py` and `overrides.csv`.
