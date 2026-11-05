You are filling a gap in one tile of the model-system atlas: model systems that were compared with patients but have no track in the draft. Work in /Users/melissadu/Documents/projects/capable/predictive-validity-atlas-v3 and run Python as `.venv/bin/python` from there.

1. Read `analyses/model-system-atlas/drafts/DRAFTER_BRIEF_v3.md` (especially "What the model is"). Then read the tile's draft `analyses/model-system-atlas/drafts/v3/<slug>.json`, its checker verdicts `<slug>.check.json` (the `missing` list is a lead), and its spec in `drafts/v3/tiles.json`. Do not edit any of those files.
2. List every model system that has been compared with patient results for this class's member drugs. Search:
   - member drugs' FDA/EMA reviews (`analyses/model-system-atlas/sources/manifest.csv`);
   - "<class or member> + <model type> + predicts / correlates with clinical response";
   - regulator reliance on in-vitro or model data;
   - patient-level uses: patient-derived organoids or cells, PDX co-clinical trials, ex-vivo drug sensitivity;
   - human challenge or genetic models;
   - in-silico / QSP models used to choose doses;
   - each member drug's own model where it differs from the draft's.
   Skip systems the draft already tracks (same `model_id` or the same system).
3. For each missing system with at least one comparison, write schema-3 entries for the cells it bears on:
   - `parallel: true`, its own `model_id`;
   - `prediction_level` (`class` or `patient`);
   - an opening `untested` entry at its first use, then a status per change.
   Follow every field and status rule in the brief: source tier, a verbatim quote of ≤40 words, dating, `comparison_stated`, and `retro` for a model run after the patient result was known.
4. Write ONLY `analyses/model-system-atlas/drafts/v3/<slug>.models.json`, shaped as {"tile": "<slug>", "searched": ["<each search you ran, one line>"], "added_models": [{"model_id", "model", "model_kind", "model_first_use_year", "prediction_level", "cells": {"<question>": [entries]}}], "considered_not_added": ["<system: why not added, e.g. no patient comparison found>"]}. An empty added_models list is a valid result when nothing is missing, but say what you searched.
5. Check the entries by merging them in memory and linting: `.venv/bin/python analyses/model-system-atlas/drafts/v3/merge_models.py <slug> --check`. Fix every finding.

Constraints:
- Do NOT use any Firecrawl tool. Use PubMed or Europe PMC (WebFetch or curl), WebSearch, curl + pdftotext, and the FDA text bundle.
- No git commands; the DB is read-only.
- Budget: 30 tool calls, about 20 minutes. If a tool is denied, rate-limited or hangs, do not retry it: move on and say what you could not verify.

Reply with: the file path; a table (model | cell | prediction level | latest status | year | source); and what was considered but not added.
