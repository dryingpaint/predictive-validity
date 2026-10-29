# Section 3 case verification protocol

Each case `python -m report.cases pending` lists is checked by separate agents that are not shown the pipeline's verdict: one runs the Evidence task, one the Outcome task, and for a program that did not advance a second coder runs the Failure-coding task. Where the two failure codes differ, an adjudicator reads both rationales, checks the sources and picks one code (it returns `{"failure_code", "rationale"}`). Each agent's JSON answer is saved as `<case_id with : replaced by _>__<evidence|outcome|failure_second|adjudication>.json` in one directory, which `python -m report.cases merge <dir>` folds into `report/audits/section3_cases.json`.

You verify one case study for a drug-development benchmark against primary sources:
ClinicalTrials.gov (use the API, e.g. https://clinicaltrials.gov/api/v2/studies/NCTxxxxxxxx),
FDA (Drugs@FDA, accessdata.fda.gov labels and letters), PubMed/PMC, sponsor press releases and
pipeline/financial reports, and reputable trade press. Use WebSearch and WebFetch. Cite URLs you
actually opened. Do not guess: say "unknown" when sources do not settle a point.

A *program* is one drug (molecular entity) developed for one disease. Its *Phase 2 entry* is the
start date of its first industry-sponsored Phase 2 trial in that disease (date given in the case).

## Evidence task (shown the claim, not the outcome)

The case gives the rule's claim (for rule B1: "Before the program entered Phase 2, the FDA had
approved a drug acting on the same target for this disease or a closely related one"). Check it:
- Is the drug's recorded target (gene symbols) and direction of action (increase/decrease function) right?
- Does the recorded disease (MONDO term) fit the program's Phase 2 trials?
- What is the earliest source that supports the claim (for B1, the FDA approval of a drug on the
  target: drug, application, date, approved use), and did it predate the Phase 2 entry date?
  claim_supported is "yes" if the source supports the claim for this disease, "partial" if only for
  a broader, neighbouring or clearly different disease, "no" otherwise.
- Is the source the sponsor's own work or drug (sponsor_authored)?
- If any recorded field is wrong (target, action, disease, entry date), start a line of notes with
  "DATA ERROR:" and say what is wrong.

Return only this JSON (no prose around it):
{"target_confirmed": "yes|no|partial", "action_confirmed": "yes|no|partial", "disease_mapping_ok": "yes|no|partial",
 "claim_supported": "yes|partial|no", "earliest_source": "<the earliest supporting source: citation, or for B1 the drug, application, date and approved use>",
 "earliest_year": <year or null>, "predates_entry": "yes|no|unknown", "sponsor_authored": "yes|no",
 "notes": "<numbered reasoning, 3-6 points>", "sources": ["<url>", ...]}

## Outcome task (shown neither the claim nor the pipeline's outcome)

Did the program *advance within 4 years* of its Phase 2 entry: a Phase 3 trial of this drug in this
disease (any sponsor) started, or the FDA approved the drug for this disease, within 4 years?
Confirm the Phase 2 entry trial and date; find what happened next and its current status. If it did
not advance, find why it stopped (stated reason, missed endpoint, safety, business) and give a
failure code:
- F1 exposure: adequate exposure or target engagement was never shown (dose, PK, formulation).
- F2 biology did not translate: target engaged, disease did not move.
- F3 wrong population: worked or plausibly works in a different population/subgroup than tested.
- F4 surrogate gap: a surrogate/biomarker moved but the clinical endpoint did not.
- F5 on-target toxicity. F6 off-target toxicity.
- F7 trial design: underpowered, placebo response, operational or enrolment problems.
- F8 commercial: strategic, portfolio or financial stop, including after positive results.
- unknown: sources do not show why. Use not_a_failure if it advanced.

Return only this JSON:
{"phase2_entry_confirmed": "yes|no|partial", "advanced_within_4y": "yes|no", "advance_event": "<the Phase 3 trial (NCT, actual start) or approval (date), or 'none; ...'>",
 "status_now": "<approved|in development|stopped|unknown>", "stop_reason": "<reason, or 'not stopped'>",
 "key_trial": "<NCT id of the decisive trial>", "primary_endpoint": "met|not_met|mixed|not_reported|not_applicable",
 "failure_code": "F1..F8|unknown|not_a_failure", "summary": "<2-4 short paragraphs: entry trial, what happened, why; start a line with DATA ERROR: if the recorded entry date or disease is wrong>",
 "sources": ["<url>", ...]}

## Failure-coding task (second coder)

The program did not advance. Independently decide why, using the codes above, from primary sources.
Return only: {"failure_code": "F1..F8|unknown", "rationale": "<what the trial showed and why this code>", "sources": ["<url>", ...]}
