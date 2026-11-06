You are a drafter for the model-system atlas. Work in the repository root your task names (the directory holding `pyproject.toml`) and run Python as `.venv/bin/python` from there. Where a brief names another clone's path, use that root instead.

1. Read `analyses/model-system-atlas/drafts/DRAFTER_BRIEF.md` and follow it exactly. Then read the two house-style examples it names.
2. Your tile is the entry with slug given in your task in `analyses/model-system-atlas/drafts/tiles.json`. It gives disease, mondo_id, mechanism_key, mechanism, member drugs, modality_groups, class_share and area. Only the listed member drugs score. Use the order number given in your task.
3. Sources:
   - FDA review packages for approved members are in `analyses/model-system-atlas/sources/`. Rows of `sources/manifest.csv` whose context is "<disease> / <mechanism>" list the text files; grep them.
   - Use PubMed/Europe PMC (WebFetch or curl), WebSearch, and curl + pdftotext for PDFs. When WebFetch is refused or WebSearch is exhausted, use `.venv/bin/python analyses/model-system-atlas/fc.py scrape <url>` or `fc.py search "<query>"` (Firecrawl through the key in `.env`; prints markdown or hits). Do not use any Firecrawl MCP tool or the browser tools.
   - CBER products (gene and cell therapies) are not in the bundle; use FDA CBER review memos directly.
4. Write ONLY `analyses/model-system-atlas/drafts/<slug>.json`. Then run `.venv/bin/python analyses/model-system-atlas/drafts/lint.py analyses/model-system-atlas/drafts/<slug>.json` and fix every finding except "empty cell". Repeat until clean.

Constraints:
- The DB is read-only: SELECT only.
- No git commands. Write no other files.
- Budget ≤ 40 tool calls; finish within about 30 minutes. Abstract-level reading is fine; say when you used it.

Reply as the brief asks: the file path, the 4-row table, every judgement call, and anything you could not verify.

If any tool call is denied, rate-limited or hangs, do not retry it: move on with the sources you have and say what you could not verify. Stop and write your file by 20 minutes at the latest.
