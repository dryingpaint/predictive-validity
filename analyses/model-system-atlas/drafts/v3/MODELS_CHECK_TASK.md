You are checking the added model tracks of one tile of the model-system atlas. Work in the repository root your task names (the directory holding `pyproject.toml`) and run Python as `.venv/bin/python` from there. Where a brief names another clone's path, use that root instead.

1. Read `analyses/model-system-atlas/drafts/CHECKER_BRIEF_v3.md` and follow it, but check ONLY the entries of the tracks listed in `<slug>.models.json` (their `model_id`s) in `analyses/model-system-atlas/drafts/v3/<slug>.json`. The other entries already have verdicts.
2. For each such entry:
   - re-open its source and its `model_src`;
   - confirm the quote;
   - confirm the status, the year and `prediction_level` under the v3 rules. In particular, a model run after the patient result was known is `retro`, never `same`.
3. Append one verdict per such entry to the "entries" list of `analyses/model-system-atlas/drafts/v3/<slug>.check.json`. Use the entry's 1-based position in its cell's JSON list as "index", in the same verdict shape the brief gives, with "checked_by": "CHECKER_BRIEF_v3 / models". Do not change or remove any existing verdict, and keep the JSON valid. Add any model system still missing to the file's "missing" list.
4. Use PubMed or Europe PMC (WebFetch or curl), WebSearch, curl + pdftotext, and the FDA bundle. When WebFetch is refused or WebSearch is exhausted, use `.venv/bin/python analyses/model-system-atlas/fc.py scrape <url>` or `fc.py search "<query>"` (Firecrawl through the key in `.env`; prints markdown or hits). Do not use any Firecrawl MCP tool or the browser tools. No git commands; the DB is read-only. Budget: 20 tool calls, about 15 minutes. If a tool is denied or hangs, move on.

Reply with one line per entry (cell, index, verdict, and the proposed status if you corrected it).
