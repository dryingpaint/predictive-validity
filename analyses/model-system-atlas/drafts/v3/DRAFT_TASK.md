You are a drafter for the model-system atlas. Work in /Users/melissadu/Documents/projects/capable/predictive-validity-atlas-v3 and run Python as `.venv/bin/python` from there.

1. Read `analyses/model-system-atlas/drafts/DRAFTER_BRIEF_v3.md` and follow it exactly. Then read the two house-style examples it names.
2. Your tile is the entry with slug given in your task in `analyses/model-system-atlas/drafts/v3/tiles.json`. It gives disease, mondo_id, mechanism_key, mechanism, member drugs, modality_groups, class_share and area. Only the listed member drugs score. Use the order number given in your task.
3. Sources:
   - FDA review packages for approved members are in `analyses/model-system-atlas/sources/`. Rows of `sources/manifest.csv` whose context is "<disease> / <mechanism>" list the text files; grep them.
   - Do NOT use any Firecrawl tool. Use PubMed/Europe PMC (WebFetch or curl), WebSearch, and curl + pdftotext for PDFs.
   - CBER products (gene and cell therapies) are not in the bundle; use FDA CBER review memos directly.
4. If the tile's v2_draft is set, it is an earlier draft under the v2 rules for this or a related class. Use it as leads only: re-verify every source and re-score under v3, and check that each drug is a member.
5. Write ONLY `analyses/model-system-atlas/drafts/v3/<slug>.json`. Then run `.venv/bin/python analyses/model-system-atlas/drafts/lint.py analyses/model-system-atlas/drafts/v3/<slug>.json` and fix every finding except "empty cell". Repeat until clean.

Constraints:
- The DB is read-only: SELECT only.
- No git commands. Write no other files.
- Budget ≤ 40 tool calls; finish within about 30 minutes. Abstract-level reading is fine; say when you used it.

Reply as the brief asks: the file path, the 4-row table, every judgement call, and anything you could not verify.
