# Drafter brief v3 (proposed) — model-system atlas context (issue dryingpaint/predictive-validity#76)

v3 (2026-11-02): the rules as Stephen called them in `RULES_WALKTHROUGH.md`, pending Melissa's review; she
can overrule any of them, and the brief changes where she does. v2 is kept as `DRAFTER_BRIEF.md` for the
record of the first run. Everything v2 asked for is still asked for; what changed is marked **v3**.

You are drafting ONE entry for an atlas of preclinical models with a **track record**: predictions that
were compared with what happened in patients. Repo: ~/code/predictive-validity (branch atlas-named-contexts).
Read `analyses/model-system-atlas/contexts/cf-cftr.json` and `contexts/ad-amyloid.json` first: they are the
house style for a finished entry (one success, one failure). Do not read any other draft.

## The unit
A **context** = disease (MONDO) × patient population (genotype / biomarker / pathogen, else "Unselected")
× drug class. Validity belongs to the context, not the model: the same mouse can be right for one drug
class and wrong for another. **v3:** the drug class is the DB's (target, action) label you are given. Do
not widen it: if every patient datum is for a sibling target (A1 agonist when the class is A2A), the
context stays `untested` with a note.

## What "the model" is (v3)
The model is whatever system the class actually relied on to go into patients: the pivotal preclinical
papers, the FDA/EMA pharmacology review. Three cases that are all in scope:
- the animals were dosed with a sibling drug, not this one: allowed, `product_in_model: false`;
- the system was not an animal (allergen challenge chamber, UVB evoked pain, patient ex-vivo cells, people
  with a loss-of-function genotype): allowed, with `model_kind`;
- no disease model was relied on at all (the class went straight to patients on another indication's
  data): the cell is an **empty list**, which the figure draws blank. `untested` means a model existed
  and nobody compared it. Keep the two apart.
A model built after the clinic already knew the answer is **not a model**: record it with
`retrodiction: true` and `status: null` so the checker can see it, but it earns nothing (pending Melissa).

## Four questions, each gets its own cell (v3 definitions)
- **engagement**: did the PD readout the model used move in dosed humans? Record `readout_tier`:
  `direct` (occupancy, free target, ex-vivo blockade of a stimulus), `proximal` (the target's own product:
  transgene protein, viral load, acid, cGMP) or `downstream` (a biomarker or physiology further down).
  Healthy volunteers count.
- **dose**: was the model's exposure / occupancy / regimen target reached in humans, **and was it enough**?
  Dose is tied to efficacy so one failure is counted once:

  | what happened | dose | efficacy |
  |---|---|---|
  | target never reached in humans (PK, tolerability) | `contra` | `untested` |
  | reached, drug worked | `same` | `same` |
  | reached, failed, abandoned | `contra` with `derived_from: "efficacy"` | `contra` |
  | reached, failed, a higher dose later worked | `contra` (target too low; record `magnitude`) | `contra`, then `same` |

  Healthy-volunteer PK counts; a later patient PK/occupancy source is its own dated entry.
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

## Status of the BEST model in the context, as of a year (one entry per change of status)
| key | status | rule (v3) |
|---|---|---|
| untested | Never compared | a model exists and was used for this class, but no admissible comparison of its prediction with patient results |
| same | Matched | a comparison shows the model's prediction agreed with patient results for ≥1 drug of this class, in direction; record how far off in `magnitude`; partial agreement is `same` + `source_calls_it: "partial"` |
| neg | Matched, incl. a known failure | `same`, AND the model's own data for a drug of this class fell below the class's usual effect bar (record the number in `judgement`) and that drug failed in patients. Judged on what the data showed, not on what the sponsor said about them (pending Melissa) |
| other | Matched, same platform only | safety only: another molecule on the same platform showed the same harm. Evidence from another drug class is set aside, not scored (pending Melissa) |
| contra | Contradicted | the model predicted wrongly for a drug in this context. Per model and per time point: a later entry may recover the cell when a different model took over (`model_change: true`) or a primary source reports the contradiction attenuated. One drug's `contra` still beats another drug's `same` on the same model |

## Evidence rules (v3)
1. **Two kinds of comparison.** Either the source itself puts model and patient results side by side
   (`comparison_stated: true`), or you put a model paper and a trial paper side by side yourself
   (`comparison_stated: false`). Both colour the cell; the figure hatches the second. A trial paper that
   merely cites the model paper is a pairing, not a statement.
2. **Admissible sources, in tiers** (`source_tier`): 1 peer-reviewed paper with DOI or PMID; 2 regulator
   document (FDA review or label, EMA EPAR, Health Canada, AdCom briefing or transcript); 3 registry results
   record. Tiers 4 (meta-analysis) and 5 (press release or SEC filing) are pending Melissa; if admitted they
   are patient-side only, never model-side, and the entry carries `trial_unreported: true`. Reviews may
   point you to a source but are not one. "Data not shown" scores at low confidence.
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
8. **FDA review PDFs.** WebFetch fails above 10 MB. Use the local cache if one is given, else
   `curl -L -o review.pdf <url> && pdftotext review.pdf -` and search the text. `model_filed` is the field
   that depends on this; do not leave it null because the PDF was large.
9. Budget: ≤20 sources, ≤40 tool calls. Abstract-level reading is acceptable; say so. The registry lookup
   for `registry_date` is mandatory.

## Fields on every entry (schema v3)
Record with null when unknown. They do not change your status call; they let the status be recomputed.
`subjects` (patients | healthy_volunteers | mixed) · `comparison_stated` · `source_tier` (1–5) ·
`trial_unreported` · `epub_year` · `print_year` · `registry_date` · `model_filed` · `product_in_model` ·
`model_kind` (animal | human_challenge | ex_vivo | in_silico | human_genetic | cross_indication) ·
`model_change` · `retrodiction` · `imported_from` (MONDO id) · `magnitude` (within_2x | off_by_2-5x |
off_by_>5x | direction_only | null | opposite) · `magnitude_basis` (the quantity it is computed on) ·
`source_calls_it` (match | miss | scaling | partial | unresolved | over_predicted) · `population` ·
`model_first_use_year` · `confidence` (high | medium | low, enum) · `confidence_note` (free text) ·
engagement only: `readout_tier` · dose only: `derived_from` · efficacy only: `endpoint_role`,
`outcome_tested`, `patient_trials` (list of {nct, registry_date, doi, quote} that change no status).
Context-level: `regulatory_reliance: true` when a regulator accepted model data in lieu of a trial.

## Output: write ONE file, then report
Write JSON to the path given below, exactly this shape (extra keys are ours; the figure ignores them):
{
 "order": <int>, "area": "<Area>", "disease": "<name>", "mondo_id": "MONDO:...",
 "population": "<...>", "mechanism": "<drug class>", "note": "<1 sentence on the context>",
 "programs": null, "loa": null, "label": "<short tile label>", "regulatory_reliance": false,
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
