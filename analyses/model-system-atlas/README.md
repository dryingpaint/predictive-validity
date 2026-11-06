# Model-system atlas (issue #76)

For each disease × mechanism, whether the preclinical models the drug class relied on predicted what happened in
patients, on four questions (target engagement, dose, efficacy, safety), judged entry by entry from published
comparisons and stored as dated tracks.

A disease is a MONDO id. The database calls it an indication (`preclin.atlas_indication`, keyed by `mondo_id`);
prose and figures say disease. A **tile** is one mechanism (target, action) in one disease, tracked when at least
three programs entered Phase 2 for it in 2008–2019. Every model system compared with patients for the class is a
**track**; a cell's **headline** is the best latest status among its tracks that predicted before the patient
result, never compared when none did, and a retrodiction never sets it (decision 6).

## State

- Register: 1,693 disease × mechanism rows; 119 tracked tiles in 48 of the 71 diseases (atlas build 428a6a37).
- Rules v3: 16 decisions, all taken (`drafts/DECISIONS.md`); `drafts/lint.py` enforces them on every draft.
- All 119 tracked tiles drafted under v3 through the five passes and stored: 1,236 tracks, 2,424 entries, 476
  cells (κ 0.86 drafter–checker on the cell headline).
- Figures. **The main paper figure is `atlas_glance_main.*`** (the top 15 diseases by burden, one tile each; PNG,
  PDF and SVG). `atlas_glance_supplement_p1..p4.*` (every drafted tile) is the supplementary figure. Both journal
  format. `disease_indications.*` is a working figure, not a paper figure; the interactive page is
  `report/atlas.html` from `report_page.py`.
- The v2 run (70 contexts under the v2 rules and briefs) is in git history at 4d478a3.

## Data in, data out

Everything reads the database through `report.frame.query`, which is read-only. Four commands write, each to its
own `preclin.atlas_*` tables (migrations `db/133_atlas.sql`, `db/135_atlas_tracks.sql`), and each replaces its own
unit (a build, a document, a tile) so a re-run is safe. Nothing else writes.

| step | reads: database | reads: files, web | writes: files | writes: database |
|---|---|---|---|---|
| `lists.py` | `dev_program`, `ontology_term`; the program and trial frames of `report.frame` under `report.section1.phase_rows` | — | `lists/named_indications.csv`, `volumes.json`, `sample.csv`, `swing_seats.csv`, `provenance.json` | — |
| `class_audit.py [store]` | `dev_program`, `moiety`, `moiety_target`, `chembl_moiety`, `chembl_mechanism`, `atlas_register` | `lists/named_indications.csv`; `lists/class_audit/reviews.csv`, the hand-reviewed class table | `lists/class_audit/register.csv`, `class_members.csv`, `AUDIT.md`; `lists/named_contexts.csv` | `store`: `atlas_build`, `atlas_indication`, `atlas_moiety_review`, `atlas_mechanism`, `atlas_member` (view `atlas_register`) |
| `fetch_sources.py [store]` | `atlas_register`, `atlas_indication`, `atlas_mechanism`, `atlas_member`, `fda_application`, `fda_application_moiety` | openFDA `drugsfda`; the review PDFs and label on accessdata.fda.gov (pdftotext, OCR for scanned ones) | `sources/manifest.csv`; `sources/<appl_no>/*.pdf`, `*.txt` (ignored) | `store`: `atlas_source_document` |
| the agent passes: drafter, checker, adjudicator, model sweep, sweep checker (`drafts/v3/*_TASK.md`) | SELECT only | `sources/` texts; PubMed and Europe PMC; WebSearch; Firecrawl through `fc.py` (key in `.env`); `drafts/v3/tiles.json`; the briefs | `drafts/v3/<slug>.json`, `.check.json`, `.models.json` | — |
| `drafts/v3/merge_models.py`, `collect_questions.py` | — | `drafts/v3/` | the merged `<slug>.json`; `RULE_QUESTIONS_v3.md` | — |
| `drafts/v3/route_store.py` → `drafts/track_store.py` | `atlas_register`, `atlas_track_entry` | a lint-clean `<slug>.json` whose verdicts are settled | — | `atlas_track_entry`, `atlas_track_verdict`: the tile is replaced |
| `report_page.py` | `atlas_build`, `atlas_indication`, `atlas_mechanism`, `atlas_register`, `atlas_track_entry`, `atlas_track_verdict` | `report/template.html` | `report/atlas.html` (ignored) | — |
| `glance.py`, `glance_nature.py` | `atlas_track_entry`, `atlas_track_verdict` | `drafts/v3/tiles.json`, `drafts/v3/short_labels.json`, `lists/burden.csv` | `glance.csv`; `atlas_glance_main.*`, `atlas_glance_supplement*.*` | — |
| `burden.py` | — | `lists/who_ghe_2021_global_dalys.csv` (WHO Global Health Estimates 2021, global DALYs by cause); `lists/named_contexts.csv` | `lists/burden.csv`: each tracked disease's WHO cause, match grade, 2021 DALYs and rank | — |
| `indications.py` | `dev_program_trial`, `ctgov_study_indication`, `indication`, `ontology_ancestor`; the cohort frames | `lists/named_indications.csv` | `lists/indications.csv`, `indications_by_disease.csv`; `disease_indications.png`, `.svg` | — |

Secrets: `DATABASE_URL` and `FIRECRAWL_API_KEY` live in `.env`, which is ignored. The source PDFs and texts are
ignored too; `fetch_sources.py store` keeps the texts in `atlas_source_document`, from which a fresh clone can
materialise them.

## What needs a decision

Every rule in `drafts/RULES_V3_PROPOSAL.md` is a proposal; `drafts/DECISIONS.md` gives the cases behind
each one. Ten are proposed as written (1, 3, 4, 5, 7, 8, 9, 11, 14, 15) and can be overruled. The six that
were open were decided on 2026-11-04:

| decision | question | answer |
|---|---|---|
| 2 sources | admit meta-analyses, press releases or SEC filings as patient-side sources? | Yes: every source that gives an accurate picture of what happened in the trials. Tiers 4–5 are patient-side only, the model side is a tier 1–3 `model_src`, and a press-release cell carries `trial_unreported` |
| 6 `contra` recoverable | can a `contra` recover when a different model takes over, or a later source attenuates it? | A failed model stays failed on its own track. Every model system is a track, and the cell headline is the best latest status among tracks that predicted before the patient result, so a newer model that beats the old one turns the headline green. An attenuated patient signal (dolutegravir) means the model was right: the red interval stays as what was believed, then the model is credited |
| 10 post-hoc models | a model built after the clinic knew the answer: excluded outright, or kept as `untested`? | Neither: tracked. A retrodiction that reproduces the human data takes its own status, `retro`, drawn with its own mark and counted apart from prospective matches; one that fails to reproduce them is `contra` |
| 12 class boundaries | the DB label governs, no widening; modality splits safety and dose, shares efficacy | Every mechanism (target, action) of every disease is registered from a reviewed per-drug class table, 1,693 rows; a mechanism with ≥ 3 programs counted across modalities is tracked and drafted (119 tiles in 48 indications). Efficacy and engagement pool the mechanism; dose and platform safety split by modality. Stored in `preclin.atlas_*` (migration 133) |
| 13 `neg` / `other` | `neg` judged on what the model data showed, not the sponsor's reading; cross-class evidence set aside | As proposed, with the model's number in `effect_size` and the class bar in `class_threshold` |
| 16 dose window | score the toxic end of the dose window when the model stated a margin, or keep dose as the effective-exposure floor only? | Score it: the atlas asks whether any model gives the toxic ceiling (`margin_stated`, `blocked_by: toxicity`) |

`drafts/lint.py` holds every draft to these rules.

Two choices sit outside the rules:

| choice | question |
|---|---|
| cohort | join the atlas to the issue's simple `ph2_start` count or the report's strict `phase_rows` cohort? 53 of 64 diseases agree; `lists/swing_seats.csv` has the rest. The tiles follow the strict list |
| DB writes | only the writers in *Data in, data out* below touch the database, all into `preclin.atlas_*`; issue #70 (the rebuild) is still open, so a rebuild re-runs `class_audit.py store` and the tile stores |

Open calls are listed in PR #81: whether the headline follows the main model or all tracks (the figures follow decision 6: all tracks), where patient-level tracks are shown, how a model published after a public result but not prompted by it is scored, the cohort, and the rule questions in `drafts/v3/RULE_QUESTIONS_v3.md`.

## Layout

| path | contents |
|---|---|
| `lists.py` → `lists/` | the context list from the DB: diseases ranked by Phase 2 entrants 2008–2019 (`report.section1.phase_rows` cohort), a 200-program long-tail sample, and `swing_seats.csv` (indications that enter or leave the list between the simple and strict cohorts) |
| `class_audit.py` → `lists/class_audit/register.csv`, `lists/named_contexts.csv`, `preclin.atlas_*` | the register (every mechanism of every disease) and the tracked tiles under decision 12, from the hand-reviewed class table `lists/class_audit/reviews.csv`; `class_audit.py store` writes the build to `preclin.atlas_build`, `atlas_indication`, `atlas_moiety_review`, `atlas_mechanism` and `atlas_member` (view `atlas_register`). `AUDIT.md` lists where the DB disagrees |
| `indications.py` → `lists/indications.csv`, `lists/indications_by_disease.csv`, `disease_indications.png` | each named disease's programs and the indications (stage, subtype, line of therapy) those programs were tested in, from the trials' condition rows; read-only |
| `burden.py` → `lists/burden.csv` | the 48 tracked diseases mapped by hand to WHO Global Health Estimates causes with a match grade (exact, broader, shared, none) and ranked by global DALYs in 2021; the ordering for the main-paper cut and for the drafting waves |
| `glance.py` → `glance.csv` | the atlas at a glance, as data: one headline per drafted cell under decision 6 (`report_page.headline`, adjudicated statuses), with the year, the model, the reason on a failure, and the dissenting track when another model contradicted; read-only |
| `glance_nature.py main` → `atlas_glance_main.*`; `glance_nature.py supplement` → `atlas_glance_supplement*.*`; `atlas_glance_caption.md` | the figures: 183 mm wide, Helvetica 5–8 pt, the Capable palette. Main: the top 15 diseases by WHO 2021 DALYs, one tile each (most programs). Supplement: every drafted tile, paginated, diseases by DALY rank then by area. Panel a is over every drafted tile on both. Labels that do not fit a cell are shortened by hand in `drafts/v3/short_labels.json`, never cut; the caption file carries both captions |
| `drafts/track_store.py`, `drafts/v3/route_store.py` | store a schema-3 draft that passes lint, and its verdicts, in `preclin.atlas_track_entry` and `atlas_track_verdict`, replacing the tile; `route_store.py` stores every tile whose verdicts are settled and lists the ones waiting for adjudication |
| `drafts/v3/tiles.json`, `drafts/v3/*_TASK.md`, `merge_models.py`, `collect_questions.py` | the 119 tile specs (members, modality groups, class share), the five agent task prompts, the model-sweep merge, and the rule-question collector |
| `fc.py` | `scrape <url>` and `search "<query>"` through Firecrawl, the agents' fallback when WebFetch is refused or the search budget is spent |
| `tests/test_atlas_glance.py`, `tests/test_atlas_indications.py` (repo `tests/`) | the headline rule, dissent and label wrapping; the stage and subtype reading of condition rows; synthetic inputs, no database |
| `drafts/ENGAGEMENT_KIND_RESULT.md` | the v2 run's result on engagement readouts that decision 15 cites |
| `drafts/RULES_V3_PROPOSAL.md`, `drafts/DECISIONS.md` | the v2 run's 151 rule questions collapsed into 16 decisions with a schema v3, and the decision record |
| `drafts/DRAFTER_BRIEF_v3.md`, `drafts/CHECKER_BRIEF_v3.md` | the briefs written to those decisions; the checker brief adds adjudication |
| `drafts/lint.py` | the v3 schema and rules on every draft; with no arguments, every tile in `drafts/v3/` |
| `fetch_sources.py` → `sources/manifest.csv`, `preclin.atlas_source_document` | the drafters' source bundle: the FDA review package of each tracked mechanism's approved members as text (OCR for scanned PDFs); `store` writes the text to the DB; the PDFs under `sources/<appl_no>/` are not committed |

## Running

```
uv sync
.venv/bin/python analyses/model-system-atlas/lists.py                              # read-only
.venv/bin/python analyses/model-system-atlas/class_audit.py [store]                # register and tiles; store writes preclin.atlas_*
.venv/bin/python analyses/model-system-atlas/fetch_sources.py [store]              # FDA review texts; hours with OCR; store writes atlas_source_document
# per tile, the five agent passes in drafts/v3/{DRAFT,CHECK,ADJ,MODELS,MODELS_CHECK}_TASK.md, then:
.venv/bin/python analyses/model-system-atlas/drafts/v3/merge_models.py <slug>
.venv/bin/python analyses/model-system-atlas/drafts/lint.py analyses/model-system-atlas/drafts/v3/<slug>.json
.venv/bin/python analyses/model-system-atlas/drafts/v3/route_store.py [slug ...]   # writes atlas_track_entry / atlas_track_verdict
.venv/bin/python analyses/model-system-atlas/drafts/v3/collect_questions.py
.venv/bin/python analyses/model-system-atlas/report_page.py
.venv/bin/python analyses/model-system-atlas/glance.py
.venv/bin/python analyses/model-system-atlas/glance_nature.py main && .venv/bin/python analyses/model-system-atlas/glance_nature.py supplement
.venv/bin/python analyses/model-system-atlas/indications.py
.venv/bin/python analyses/model-system-atlas/burden.py                            # WHO DALYs per tracked disease
uv run pytest tests/test_atlas_glance.py tests/test_atlas_indications.py
```

Drafts stay in `drafts/v3/`. The only database writers are the ones in *Data in, data out*.
