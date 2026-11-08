You are closing the open leads of one tile of the model-system atlas. Work in the repository root your task names (the directory holding `pyproject.toml`) and run Python as `.venv/bin/python` from there.

1. Read `analyses/model-system-atlas/drafts/DRAFTER_BRIEF.md` (especially "What the model is"). Then read the tile's draft `drafts/<slug>.json`, its verdicts `<slug>.check.json`, its `<slug>.models.json` and its spec in `drafts/tiles.json`. Do not edit the draft or the verdict file.
2. Your leads are:
   - every item of the `missing` list in `<slug>.check.json`;
   - every member drug your task names as never mentioned in the draft or the models file.
3. Settle each lead as one of:
   - `tracked`: the draft already holds it (name the `model_id` and cell);
   - `verdict`: it corrects an existing entry (a date, a status) rather than adding a system, and a checker verdict already covers it, or it needs one (say which entry);
   - `added`: a model system compared with patient results for a member drug that has no track. Add it as a new item of `added_models` in `<slug>.models.json`, in the shape and under the field and status rules that `MODELS_TASK.md` gives (own `model_id`, `prediction_level`, an opening `untested` entry at first use, a ≤40-word verbatim quote, `retro` for a model run after the patient result was known);
   - `none`: searched and no such comparison exists, or the item is outside the rules (say which rule).
   For a never-mentioned member drug, search its preclinical models and its patient results (PubMed/Europe PMC, the FDA text bundle in `analyses/model-system-atlas/sources/`, sponsor publications, ClinicalTrials.gov). A drug with no published model-to-patient comparison is `none`, with what you searched.
4. Edit ONLY `<slug>.models.json`: append new systems to `added_models` (keep every existing item) and add a key `"gaps"`: [{"lead": "<the item or drug>", "outcome": "tracked|verdict|added|none", "detail": "<model_id, entry, or why, one line>"}], one per lead. Then run `.venv/bin/python analyses/model-system-atlas/drafts/merge_models.py <slug> --check` and fix every finding.

Sources: PubMed or Europe PMC (WebFetch or curl), WebSearch, curl + pdftotext, the FDA bundle. When WebFetch is refused or WebSearch is exhausted, use `.venv/bin/python analyses/model-system-atlas/fc.py scrape <url>` or `fc.py search "<query>"`. Do not use any Firecrawl MCP tool or the browser tools. No git commands; the DB is read-only. Budget: 35 tool calls, about 25 minutes; if a tool is denied, rate-limited or hangs, do not retry it.

Reply with one line per lead (lead | outcome | detail) and the number of systems added.
