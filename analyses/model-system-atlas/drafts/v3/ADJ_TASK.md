You are the adjudicator for the model-system atlas. Work in /Users/melissadu/Documents/projects/capable/predictive-validity-atlas-v3 and run Python as `.venv/bin/python` from there.

1. Read `analyses/model-system-atlas/drafts/CHECKER_BRIEF_v3.md` (the Adjudication section) and `analyses/model-system-atlas/drafts/RULES_V3_PROPOSAL.md` (the rules).
2. For each slug in your task, open `drafts/v3/<slug>.json` (the draft) and `drafts/v3/<slug>.check.json` (the checker's verdicts). For every verdict with "verdict": "corrected":
   - read the drafter's entry, the checker's proposed_status and note, and the decision it cites in "rule";
   - re-open the sources only when the two disagree about what a source says;
   - decide the status the v3 rules require. Write `adjudicated_status` (one of untested/same/neg/other/contra/retro/drop) and a short `adjudication_note` (≤40 words, naming the rule) into that verdict object.
   - If the rules do not decide the case, set adjudicated_status to the drafter's status and start the note with "RULE QUESTION:", followed by the question.
3. Edit only the `.check.json` files, adding those two fields; change nothing else. Keep the JSON valid.
4. Do NOT use any Firecrawl tool. Use PubMed or Europe PMC (WebFetch or curl), WebSearch, and the FDA text in `analyses/model-system-atlas/sources/`. No git commands; the DB is read-only. Budget: 25 tool calls.

Reply with one line per corrected verdict (slug, cell, index, drafter → checker → adjudicated) and the rule questions.
