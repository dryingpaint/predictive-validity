# Drafter brief v2 — model-system atlas context (issue dryingpaint/predictive-validity#76)

v2 (2026-11-02): adds the fact fields below so entries can be re-scored when the rules change.

You are drafting ONE entry for an atlas of preclinical models with a **track record**: predictions that
were compared with what happened in patients. Repo: ~/code/predictive-validity (branch atlas-named-contexts).
Read `analyses/model-system-atlas/contexts/cf-cftr.json` and `contexts/ad-amyloid.json` first: they are the
house style for a finished entry (one success, one failure).

## The unit
A **context** = disease (MONDO) × patient population (genotype / biomarker / pathogen, else "Unselected")
× drug class. Validity belongs to the context, not the model: the same mouse can be right for one drug
class and wrong for another.

## Four questions, each gets its own cell
- engagement: does the drug hit its target in patients the way the model said?
- dose: did the model's exposure/occupancy target hold in patients?
- efficacy: did the disease respond in patients the way the model said?
- safety: did the model's safety prediction (or its silence) hold in patients?

## Status of the BEST model in the context, as of a year (one entry per change of status)
| key | status | rule |
|---|---|---|
| untested | Never compared | model exists and was used for this class, but no PUBLISHED comparison of its prediction with patient results |
| same | Matched, same mechanism | a published comparison shows the model's prediction agreed with patient results for ≥1 drug of this class |
| neg | Matched, incl. a known failure | `same`, AND the model also flagged a drug of this class that went on to fail in patients |
| other | Matched, other mechanism only | the only published agreement is for drugs that work by a different mechanism |
| contra | Contradicted | the model predicted wrongly for a drug in this context; overrides every matched status |

"Best model" = the model this drug class actually relied on for that question (the one in the pivotal
preclinical papers / FDA pharmacology review), not the best model that exists in principle.

## Evidence rules (strict)
1. A status other than `untested` needs a PRIMARY source that makes the comparison: a peer-reviewed paper
   with a DOI, an FDA label/review (accessdata.fda.gov or dailymed URL), or a registry record. Reviews
   may point you to it but are not the source.
2. Every entry carries `quote`: the sentence (≤40 words, verbatim) from the source that supports the status.
   If you cannot quote it, the status is `untested`.
3. Verify every DOI resolves to the paper you mean (use the PubMed tools `mcp__plugin_bio-research_pubmed__search_articles`
   / `get_article_metadata`, or WebFetch). Never invent a citation. If a source is paywalled and you only
   have the abstract, say so in `confidence`.
4. Finding nothing is a finding. Do not stretch: if nobody published the comparison, write `untested` and
   say in `note` what model was used and that no comparison was found.
5. Do NOT use drug approval status or later knowledge to decide a status; use the year the comparison was
   published. The strip is drawn from the years.
6. Each cell starts with the first year the model was used for this class (status `untested`), so the
   strip shows when a model existed before it was tested.
7. Budget: ≤20 sources, ≤40 tool calls (raised from 15/25 after batch 1, 2026-11-02). Abstract-level reading is
   acceptable; say so. The registry lookup for `registry_date` (ClinicalTrials.gov results-first-posted date of
   each comparison trial) is mandatory, not optional — spend calls on it before widening the search.

## Facts every entry must carry (so statuses can be re-scored under revised rules)
Record these as fields on each entry, with null when unknown. Do not let them change your status
call; they exist so the status can be recomputed later without repeating the research.
- `subjects`: who the patient-side comparison was in — "patients" | "healthy_volunteers" | "mixed" | null
- `comparison_stated`: true if the cited source itself puts model and patient results side by side;
  false if you juxtaposed two sources yourself
- `epub_year` and `print_year` of the source (year = print_year by house convention)
- `registry_date`: ISO date results were first posted on a registry for the comparison trial, if any
- `model_filed`: true if an FDA/EMA review or label names this model as submitted for this class
- `product_in_model`: true if the model was dosed with the drug being compared, false if a class
  proxy (e.g. canine FVIII in dogs, not the clinical product)
- `magnitude`: for a comparison, "direction_only" | "within_2x" | "off_by_2-5x" | "off_by_>5x" | null,
  and `source_calls_it`: "scaling" | "miss" | "match" | null — the source's own characterisation
- `population`: the biomarker/genotype the drug class is prescribed by, else "Unselected"; set the
  context's `population` field from the class (e.g. EGFR inhibitors -> "EGFR-mutant")
- `model_first_use_year`: earliest year you found the model used for this drug class (opens the strip)

## Output: write ONE file, then report
Write JSON to the path given below, exactly this shape (extra keys `quote`, `confidence`, `judgement`
are ours; the figure ignores them):
{
 "order": <int>, "area": "<Area>", "disease": "<name>", "mondo_id": "MONDO:...",
 "population": "<...>", "mechanism": "<drug class>", "note": "<1 sentence on the context>",
 "programs": null, "loa": null, "label": "<short tile label>",
 "cells": {
  "engagement": [ {"year": 2009, "status": "untested", "model": "<model>", "note": "<≤25 words>",
                   "short": "<≤8 words>", "src": "https://doi.org/...", "srcLabel": "Author Year",
                   "quote": "<verbatim sentence>", "confidence": "high|medium|low",
                   "reason": "<≤8 words, only on the latest entry>", "judgement": "<optional: why this was a call>"} ],
  "dose": [...], "efficacy": [...], "safety": [...]
 }
}
Empty list for a question with no model/comparison at all. Then reply with: the file path, a 4-row table
(question | status | year | source), every judgement call you made, and anything you could not verify.
