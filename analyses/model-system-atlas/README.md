# Model-system atlas (issue #76)

For each disease × drug class, whether the preclinical model the class relied on predicted what happened
in patients, on four questions (engagement, dose, efficacy, safety), as a dated strip of statuses.
`contexts/`, `figure.py` and `atlas.png` are the prototype from `atlas-prototype`. Everything else is the
first full run on 70 named contexts and the rules proposal that came out of it.

A disease is a MONDO id. The database calls it an indication (`preclin.atlas_indication`, keyed by `mondo_id`);
prose and figures say disease.

## What needs a decision

Every rule in `drafts/RULES_V3_PROPOSAL.md` is a proposal; `drafts/DECISIONS.md` gives the cases behind
each one. Ten are proposed as written (1, 3, 4, 5, 7, 8, 9, 11, 14, 15) and can be overruled. The six that
were open were decided on 2026-11-04:

| decision | question | answer |
|---|---|---|
| 2 sources | admit meta-analyses, press releases or SEC filings as patient-side sources? | Yes: every source that gives an accurate picture of what happened in the trials. Tiers 4–5 are patient-side only, the model side is a tier 1–3 `model_src`, and a press-release cell carries `trial_unreported` |
| 6 `contra` recoverable | can a `contra` recover when a different model takes over, or a later source attenuates it? | A failed model stays failed in its own record (`matrix_models.csv`). The cell shows the best model at each date, so a newer model that beats the old one turns it green with a handover mark. An attenuated patient signal (dolutegravir) means the model was right: the red interval stays as what was believed, then the model is credited |
| 10 post-hoc models | a model built after the clinic knew the answer: excluded outright, or kept as `untested`? | Neither: tracked. A retrodiction that reproduces the human data takes its own status, `retro`, drawn with its own mark and counted apart from prospective matches; one that fails to reproduce them is `contra` |
| 12 class boundaries | the DB label governs, no widening; modality splits safety and dose, shares efficacy | Every mechanism (target, action) of every disease is registered from a reviewed per-drug class table, 1,693 rows; a mechanism with ≥ 3 programs counted across modalities is tracked and drafted (119 tiles in 48 indications). Efficacy and engagement pool the mechanism; dose and platform safety split by modality. Stored in `preclin.atlas_*` (migration 133) |
| 13 `neg` / `other` | `neg` judged on what the model data showed, not the sponsor's reading; cross-class evidence set aside | As proposed, with the model's number in `effect_size` and the class bar in `class_threshold` |
| 16 dose window | score the toxic end of the dose window when the model stated a margin, or keep dose as the effective-exposure floor only? | Score it: the atlas asks whether any model gives the toxic ceiling (`margin_stated`, `blocked_by: toxicity`) |

`drafts/lint.py` holds any draft that declares `"schema": 3` to these rules.

Three choices sit outside the rules:

| choice | question |
|---|---|
| cohort | join the atlas to the issue's simple `ph2_start` count or the report's strict `phase_rows` cohort? 53 of 64 diseases agree; `lists/swing_seats.csv` has the rest. The 70 contexts here follow the strict list |
| class share | print each tile's share of the disease's programs, so a reader sees how much of the disease it covers (decision 12) |
| DB writes | the κ re-draft (30 contexts under v3) through `pipeline/` needs writes to `pv_evidence.llm_decision` while #70 is open |

Next: audit the class table and regenerate the contexts from it, pre-fetch each context's source bundle,
run the κ re-draft under `DRAFTER_BRIEF_v3.md` and `CHECKER_BRIEF_v3.md` with adjudication, then regenerate
the strips with `render_pilot.py`.
The figure layout in `figure.py` is untouched until the rules are agreed.

## Layout

| path | contents |
|---|---|
| `lists.py` → `lists/` | the context list from the DB: diseases ranked by Phase 2 entrants 2008–2019 (`report.section1.phase_rows` cohort), a 200-program long-tail sample, and `swing_seats.csv` (indications that enter or leave the list between the simple and strict cohorts) |
| `class_audit.py` → `lists/class_audit/register.csv`, `lists/named_contexts.csv`, `preclin.atlas_*` | the register (every mechanism of every disease) and the tracked tiles under decision 12, from the hand-reviewed class table `lists/class_audit/reviews.csv`; `class_audit.py store` writes the build to `preclin.atlas_build`, `atlas_indication`, `atlas_moiety_review`, `atlas_mechanism` and `atlas_member` (view `atlas_register`). `AUDIT.md` lists where the DB disagrees. `named_contexts_v2.csv` is the list the v2 drafts were written against |
| `drafts/track_store.py` | stores a schema-3 draft that passes lint, and its verdicts, in `preclin.atlas_track_entry` and `atlas_track_verdict`, replacing the tile |
| `drafts/<id>.json`, `drafts/<id>.check.json` | 70 drafted contexts and their checker verdicts; `manifest.csv` tracks them |
| `drafts/DRAFTER_BRIEF.md`, `drafts/CHECKER_BRIEF.md` | the agent briefs used for the run (v2) |
| `drafts/RULE_QUESTIONS.md` | 151 cases the v2 rules did not decide |
| `drafts/RULES_V3_PROPOSAL.md`, `drafts/DECISIONS.md` | the questions collapsed into 16 decisions with a schema v3, and the decision record |
| `drafts/DRAFTER_BRIEF_v3.md`, `drafts/CHECKER_BRIEF_v3.md` | the briefs written to those decisions; the checker brief adds adjudication |
| `drafts/matrix.py` → `matrix_entries.csv`, `matrix_cells.csv`, `matrix_models.csv` | one row per entry, per cell and per model: drafter and checker status, all fact fields, each model's own record (decision 6) |
| `drafts/lint.py` | schema check on the drafts; v3 rules on drafts that declare `"schema": 3` |
| `fetch_sources.py` → `sources/manifest.csv`, `preclin.atlas_source_document` | the drafters' source bundle: the FDA review package of each tracked mechanism's approved members as text (OCR for scanned PDFs); `store` writes the text to the DB; the PDFs under `sources/<appl_no>/` are not committed |
| `render_pilot.py` → `drafts/pilot_render/atlas.png` (not committed) | all drafts through `figure.py` with checker corrections applied |
| `drafts/engagement_outcomes.py` → `context_outcomes.csv` | Phase 2 and Phase 3 advancement of each context's class, from the DB |
| `drafts/engagement_kind_result.py` → `engagement_experiment.csv`, `ENGAGEMENT_KIND_RESULT.md` | whether the kind of engagement readout tracks the class's advancement |

## Running

```
uv sync
.venv/bin/python analyses/model-system-atlas/lists.py                         # DATABASE_URL in .env; read-only
.venv/bin/python analyses/model-system-atlas/class_audit.py [store]           # register and tiles; store writes preclin.atlas_*
.venv/bin/python analyses/model-system-atlas/drafts/matrix.py
.venv/bin/python analyses/model-system-atlas/drafts/lint.py
.venv/bin/python analyses/model-system-atlas/render_pilot.py
.venv/bin/python analyses/model-system-atlas/drafts/engagement_outcomes.py    # read-only
.venv/bin/python analyses/model-system-atlas/drafts/engagement_kind_result.py
.venv/bin/python analyses/model-system-atlas/fetch_sources.py [store]         # tracked members from preclin.atlas_register; hours with OCR
```

Drafts stay in `drafts/`, never in `contexts/`. Only the three `store` commands write to the DB, each to its own `preclin.atlas_*` tables (migration 133).
