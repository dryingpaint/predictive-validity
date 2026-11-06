# Drafter brief v3 — model-system atlas tile (issue dryingpaint/predictive-validity#76)

v3 (2026-11-04): written to the decisions in `DECISIONS.md` and `RULES_V3_PROPOSAL.md`, all sixteen taken.
`drafts/lint.py` checks every field below on a draft that declares `"schema": 3`. The rules v3 added over the first run's are marked **v3**.

You are drafting ONE entry for an atlas of preclinical models with a **track record**: predictions that
were compared with what happened in patients. Work in the repository root your task names.
Read `analyses/model-system-atlas/drafts/v3/cystic-fibrosis-cftr-potentiators.json` and
`drafts/v3/alzheimer-disease-bace1-inhibitors.json` first: they are the house style for a finished entry (one
success, one failure). Do not read any other draft.

## The unit
A **context** = disease (MONDO) × patient population (genotype / biomarker / pathogen, else "Unselected")
× drug class. Validity belongs to the context, not the model: the same mouse can be right for one drug
class and wrong for another. **v3:** the drug class is the mechanism (target, action) you are given,
with its member drugs from the reviewed class table; only those drugs score. Do not widen it: if every
patient datum is for a sibling target (A1 agonist when the class is A2A) or a non-selective drug outside
the member list, the context stays `untested` with a note. Copy the given `modality_groups` and
`class_share`, and the tile's `mechanism_key` (its key in `preclin.atlas_register`), into the output.
Efficacy and engagement pool every modality of the mechanism. When the
tile has more than one modality, dose is split by modality and so are platform or off-target harms in
safety (an on-target harm stays pooled): give each such entry `modality`, one of the tile's
`modality_groups`, and keep each modality's entries in year order.

## What "the model" is (v3)
Start by listing **every model system that has been compared with patients for this class**, not only
the one the class went into patients on. Search the pivotal preclinical papers and FDA/EMA reviews, and
also "<class or member> + <model type> + predicts / correlates with clinical response", regulator
reliance (label expansions on in-vitro data), and patient-level uses (patient-derived organoids or cells
used to choose who gets treated). Each model system is a **track**: its entries share one `model_id`
and are scored by the same rules within that track. The system the class went into patients on is one
track among them. Every entry
records `prediction_level`: `class` (does the drug class work) or `patient` (does the model pick which
patients or genotypes respond). Three cases that are all in scope:
- the animals were dosed with a sibling drug, not this one: allowed, `product_in_model: false`;
- the system was not an animal (allergen challenge chamber, UVB evoked pain, patient ex-vivo cells, people
  with a loss-of-function genotype): allowed, with `model_kind`;
- no disease model was relied on at all (the class went straight to patients on another indication's
  data): the cell is an **empty list**, which the figure draws blank. `untested` means a model existed
  and nobody compared it. Keep the two apart.
A model built or run after the clinic already knew the answer is a **retrodiction**: record it with
`retrodiction: true`. If it reproduced the human data its status is `retro`, never `same`; if it failed to
reproduce them, `contra`. Its first prospective prediction afterwards is a fresh entry scored as usual
(decision 10).

## Four questions, each gets its own cell (v3 definitions)
- **engagement**: did the PD readout the model used move in dosed humans? Record `readout_tier`:
  `direct` (occupancy, free target, ex-vivo blockade of a stimulus), `proximal` (the target's own product:
  transgene protein, viral load, acid, cGMP) or `downstream` (a biomarker or physiology further down).
  Healthy volunteers count.
- **dose**: was the model's exposure / occupancy / regimen target reached in humans, **and was it enough**?
  Dose is tied to efficacy so one failure is counted once:

  | what happened | dose | efficacy |
  |---|---|---|
  | target never reached in humans (PK) | `contra` | `untested` |
  | the model stated the effective exposure was tolerated, and patients were dosed to target without that toxicity (decision 16) | `same` with `margin_stated: true` | as the trial showed |
  | never reached because of toxicity; the model stated the effective exposure was tolerated (decision 16) | `contra` with `blocked_by: "toxicity"`, `margin_stated: true` | `untested` |
  | never reached because of toxicity; no stated margin | `untested` | `untested` |
  | reached, drug worked | `same` | `same` |
  | reached, failed, abandoned | `contra` with `derived_from: "efficacy"` | `contra` |
  | reached, failed, a higher dose later worked | `contra` (target too low; record `magnitude`) | `contra`, then `same` |

  Healthy-volunteer PK counts; a later patient PK/occupancy source is its own dated entry.
  Decision 16 scores the toxic end of the window: a stated tolerability margin (NOAEL, MTD, a
  tolerated dose at or above the effective one) that held is `same`; toxicity at or below the effective
  exposure is `contra` with `blocked_by: "toxicity"`, an independent dose failure. Count the harm once:
  here when the model predicted it but misplaced the margin, in safety when it did not predict it.
- **efficacy**: did the trial's **primary endpoint** respond as predicted? When the sponsor pre-specified a
  secondary as the proof-of-concept gate, that endpoint governs, with `endpoint_role: "poc_gate"`;
  otherwise `"primary"`. Patients of the context's disease only. A biomarker-unselected trial counts for a
  biomarker context when the biomarker is ≥ 80 % of the trial population. If the model predicted a
  surrogate and an outcome trial was later run, set `outcome_tested`: null / positive / negative /
  negative_confounded; the status still follows the surrogate.
- **safety**: did the model's stated prediction hold, or was its silence contradicted on a harm the
  species could have shown? A mouse cannot show cytokine release, so its silence on CRS is not a miss. A
  predicted harm that never appeared in patients is a wrong prediction: `contra`, `magnitude: "opposite"`.
  Safety comparisons made in another indication or population transfer, flagged `imported_from`.

## Status of one track, as of a year (one entry per change of status on that track)
| key | status | rule (v3) |
|---|---|---|
| untested | Never compared | a model exists and was used for this class, but no admissible comparison of its prediction with patient results |
| same | Matched | a comparison shows the model's prediction agreed with patient results for ≥1 drug of this class, in direction; record how far off in `magnitude`; partial agreement is `same` + `source_calls_it: "partial"` |
| neg | Matched, incl. a known failure | `same`, AND the model's own data for a drug of this class fell below the class's usual effect bar and that drug failed in patients. Record the model's number in `effect_size` and the bar in `class_threshold`. Judged on what the data showed, not on what the sponsor said about them (decision 13) |
| other | Matched, same platform only | safety only: another molecule on the same platform showed the same harm. Evidence from another drug class is set aside, not scored (decision 13) |
| contra | Contradicted | the model predicted wrongly for a drug in this context. A failed model stays failed on its track; a newer model that did better is its own track. A later entry turns the track back only when a tier 1–4 source shows the early patient signal attenuated to background, so the model was right (`patient_signal_reversed: true`). One drug's `contra` still beats another drug's `same` on the same track |
| retro | Reproduces the known result | a retrodiction (`retrodiction: true`) that reproduced the human data; drawn with its own mark and counted apart from `same` (decision 10) |

## Evidence rules (v3)
1. **Two kinds of comparison.** Either the source itself puts model and patient results side by side
   (`comparison_stated: true`), or you put a model paper and a trial paper side by side yourself
   (`comparison_stated: false`). Both colour the cell; the figure hatches the second. A trial paper that
   merely cites the model paper is a pairing, not a statement.
2. **Admissible sources, in tiers** (`source_tier`): 1 peer-reviewed paper with DOI or PMID; 2 regulator
   document (FDA review or label, EMA EPAR, Health Canada, AdCom briefing or transcript); 3 registry results
   record; 4 meta-analysis of patient trials; 5 sponsor press release or SEC filing. Use every one of them
   to get what happened in the trials right: a Phase 3 failure known only from a press release must be
   found. Tiers 4–5 are patient-side only: name the model side in `model_src` with `model_src_tier` 1–3. A
   tier 5 entry carries `trial_unreported: true`. Where a higher-tier record of the same trial exists it
   sets the status. Reviews may point you to a source but are not one. "Data not shown" scores at low
   confidence. A paired comparison (`comparison_stated: false`) also names its model side in `model_src`.
3. Every entry carries `quote`: the sentence (≤40 words, verbatim) from the source that supports the
   status. If you cannot quote it, the status is `untested`.
4. Verify every DOI resolves to the paper you mean (PubMed tools or WebFetch). Never invent a citation.
   Paywalled abstract only: say so in `confidence_note`.
5. Finding nothing is a finding. If nobody compared, write `untested` and say in `note` what model was used.
6. **Dating.** The entry's `year` is the earliest date the comparison was public: registry results posting,
   online publication, label, or print. Record all of `registry_date`, `epub_year`, `print_year`. Each cell
   opens at `model_first_use_year` with status `untested`, proxy allowed, so the strip shows when a model
   existed before it was tested.
7. Do NOT use approval status or later knowledge to decide a status; use what was known at the entry's date.
8. **FDA review PDFs.** WebFetch fails above 10 MB. Start from the source bundle: the rows of
   `analyses/model-system-atlas/sources/manifest.csv` for your context list each class member's FDA review
   package (non-clinical, medical, clinical pharmacology, summary reviews and label) as text in `txt`, OCRed
   where the PDF was scanned; grep them. The FDA review URL is the `url` column, which is what `src` cites.
   For a document not in the bundle (EMA EPAR, CBER review, AdCom transcript),
   `curl -L -o review.pdf <url> && pdftotext review.pdf -` and search the text. `model_filed` is the field
   that depends on this; do not leave it null because the PDF was large.
9. Budget: ≤20 sources, ≤40 tool calls. Abstract-level reading is acceptable; say so. The registry lookup
   for `registry_date` is mandatory.

## Fields on every entry (schema v3)
Record with null when unknown. They do not change your status call; they let the status be recomputed.
`model_id` (a short slug for the system, e.g. `hemb-dog-chapel-hill`; the same system keeps the same slug
in every entry and cell, a different system gets a new one) · `subjects` (patients | healthy_volunteers | mixed) · `comparison_stated` · `source_tier` (1–5) ·
`model_src` · `model_src_tier` (1–3) · `trial_unreported` · `patient_signal_reversed` · `epub_year` · `print_year` · `registry_date` · `model_filed` · `product_in_model` ·
`model_kind` (animal | human_challenge | ex_vivo | in_silico | human_genetic | cross_indication) ·
`retrodiction` · `imported_from` (MONDO id) · `magnitude` (within_2x | off_by_2-5x |
off_by_>5x | direction_only | null | opposite) · `magnitude_basis` (the quantity it is computed on) ·
`source_calls_it` (match | miss | scaling | partial | unresolved | over_predicted) · `population` ·
`model_first_use_year` · `confidence` (high | medium | low, enum) · `confidence_note` (free text) ·
engagement only: `readout_tier` · dose only: `derived_from`, `blocked_by`, `margin_stated` · `neg` only:
`effect_size`, `class_threshold` · efficacy only: `endpoint_role`,
`outcome_tested`, `patient_trials` (list of {nct, registry_date, doi, quote} that change no status).
Context-level: `regulatory_reliance: true` when a regulator accepted model data in lieu of a trial;
`modality_groups` (list) and `class_share` as given.

## Output: write ONE file, then report
Write JSON to the path given below, exactly this shape (extra keys are ours; the figure ignores them):
{
 "schema": 3, "mechanism_key": "<as given>", "order": <int>, "area": "<Area>", "disease": "<name>", "mondo_id": "MONDO:...",
 "population": "<...>", "mechanism": "<drug class>", "note": "<1 sentence on the context>",
 "programs": null, "loa": null, "label": "<short tile label>", "regulatory_reliance": false,
 "modality_groups": [<as given>], "class_share": <as given>,
 "cells": {
  "engagement": [ {"year": 2009, "status": "untested", "model": "<model>", "note": "<≤25 words>",
                   "short": "<≤8 words>", "src": "https://doi.org/...", "srcLabel": "Author Year",
                   "quote": "<verbatim sentence>", "confidence": "high|medium|low", "confidence_note": null,
                   "reason": "<≤8 words, only on the latest entry>", "judgement": "<why this was a call>",
                   ...schema v3 fields... } ],
  "dose": [...], "efficacy": [...], "safety": [...]
 }
}
Empty list for a question where no model was relied on. Then reply with: the file path, a 4-row table
(question | status | year | source), every judgement call you made, and anything you could not verify.
