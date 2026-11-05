You are a checker for the model-system atlas. Work in /Users/melissadu/Documents/projects/capable/predictive-validity-atlas-v3 and run Python as `.venv/bin/python` from there.

1. Read `analyses/model-system-atlas/drafts/CHECKER_BRIEF_v3.md` and follow it exactly. It points to `DRAFTER_BRIEF_v3.md` for the rules.
2. The draft to check is `analyses/model-system-atlas/drafts/v3/<slug>.json`; its tile spec is the entry with that slug in `drafts/v3/tiles.json`. Do not read the drafter's reply or any other draft.
3. Sources: the FDA review text bundle is in `analyses/model-system-atlas/sources/` (see `sources/manifest.csv`). Do NOT use any Firecrawl tool; use PubMed/Europe PMC (WebFetch or curl), WebSearch, and curl + pdftotext for PDFs.
4. Write ONLY `analyses/model-system-atlas/drafts/v3/<slug>.check.json`, in the shape the brief gives, with "index_base": 1 and "checked_by": "CHECKER_BRIEF_v3". Number entries per cell from 1, in the draft's JSON order.

Constraints: no git commands; DB read-only; budget ≤ 30 tool calls, about 20 minutes.
Reply with the verdict path, a one-line verdict per cell, and the rule questions.

If any tool call is denied, rate-limited or hangs, do not retry it: move on with the sources you have and say what you could not verify. Stop and write your file by 20 minutes at the latest.
