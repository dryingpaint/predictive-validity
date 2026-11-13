You are applying the corrections a tile's gap pass found owed. Work in the repository root your task names (the directory holding `pyproject.toml`) and run Python as `.venv/bin/python` from there.

1. Read `analyses/model-system-atlas/drafts/DRAFTER_BRIEF.md`. Then read the tile's draft `drafts/<slug>.json`, its verdicts `<slug>.check.json` and `<slug>.models.json`. Your leads are the items of `gaps` in `<slug>.models.json` whose outcome is `verdict`.
2. For each lead, decide:
   - `covered`: a verdict in `<slug>.check.json` already proposes this change on this entry (same cell, index and change), or the lead changes nothing scored (a note, an extra patient trial with the status unchanged).
   - `entry`: an entry the rules require is missing from an existing track (for example a later `retro` or status change). Write it into `<slug>.models.json` as an item of `added_models` under that track's existing `model_id`, with the same `model`, `model_kind`, `prediction_level` and `model_first_use_year` as the track, and the entry in full under every field and status rule of the brief, including a verbatim quote of 40 words or fewer from a source you opened.
   - `fix`: a field of an existing entry is wrong (year, status, `model_filed`, `trial_unreported`, source) and no verdict proposes the fix. Re-open the source. Record it for the checker as described in step 3; do not edit the draft or the verdict file.
3. Set each lead's `outcome` in `gaps` to `covered`, `entry` or `fix`. For `fix`, put in `detail` the cell, the 1-based index, the field, the current value, the value the source supports, and the source.
4. Edit ONLY `<slug>.models.json`. Then run `.venv/bin/python analyses/model-system-atlas/drafts/merge_models.py <slug> --check` and fix every finding.

Sources: PubMed or Europe PMC (WebFetch or curl), WebSearch, curl + pdftotext, the FDA bundle in `analyses/model-system-atlas/sources/`. When WebFetch is refused or WebSearch is exhausted, use `.venv/bin/python analyses/model-system-atlas/fc.py scrape <url>` or `fc.py search "<query>"`. Do not use any Firecrawl MCP tool or the browser tools. No git commands; the DB is read-only. Budget: 30 tool calls, about 20 minutes; if a tool is denied, rate-limited or hangs, do not retry it.

Reply with one line per lead (lead | covered/entry/fix | detail).
