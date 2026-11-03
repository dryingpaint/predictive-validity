# Model-system atlas (issue #76)

For each indication × drug class, whether the preclinical model the class relied on predicted what happened
in patients, on four questions (engagement, dose, efficacy, safety), as a dated strip of statuses.
`contexts/`, `figure.py` and `atlas.png` are the prototype from `atlas-prototype`. Everything else is the
first full run on 70 named contexts and the rules proposal that came out of it.

## What needs a decision

Every rule in `drafts/RULES_V3_PROPOSAL.md` is a proposal; `drafts/DECISIONS.md` gives the cases behind
each one. Ten are proposed as written (1, 3, 4, 5, 7, 8, 9, 11, 14, 15) and can be overruled. Six are
open and need a call:

| decision | question |
|---|---|
| 2 sources | admit meta-analyses, press releases or SEC filings as patient-side sources? (leaning no) |
| 6 `contra` recoverable | can a `contra` recover when a different model takes over, or a later source attenuates it? |
| 10 post-hoc models | a model built after the clinic knew the answer: excluded outright, or kept as `untested`? |
| 12 class boundaries | the DB label governs, no widening; modality splits safety and dose, shares efficacy |
| 13 `neg` / `other` | `neg` judged on what the model data showed, not the sponsor's reading; cross-class evidence set aside |
| 16 dose window | score the toxic end of the dose window when the model stated a margin, or keep dose as the effective-exposure floor only? |

Three choices sit outside the rules:

| choice | question |
|---|---|
| cohort | join the atlas to the issue's simple `ph2_start` count or the report's strict `phase_rows` cohort? 53 of 64 indications agree; `lists/swing_seats.csv` has the rest. The 70 contexts here follow the strict list |
| class share | print each tile's share of the indication's programs, so a reader sees how much of the indication it covers (decision 12) |
| DB writes | the κ re-draft (30 contexts under v3) through `pipeline/` needs writes to `pv_evidence.llm_decision` while #70 is open |

Once the calls are made: finalize `drafts/DRAFTER_BRIEF_v3.md`, re-score the 70 drafts where the recorded
fact fields allow (`matrix.py`), run the κ re-draft, then regenerate the strips with `render_pilot.py`.
The figure layout in `figure.py` is untouched until the rules are agreed.

## Layout

| path | contents |
|---|---|
| `lists.py` → `lists/` | the context list from the DB: indications ranked by Phase 2 entrants 2008–2019 (`report.section1.phase_rows` cohort), the most-developed novel drug class per indication, a 200-program long-tail sample, and `swing_seats.csv` (indications that enter or leave the list between the simple and strict cohorts) |
| `drafts/<id>.json`, `drafts/<id>.check.json` | 70 drafted contexts and their checker verdicts; `manifest.csv` tracks them |
| `drafts/DRAFTER_BRIEF.md`, `drafts/CHECKER_BRIEF.md` | the agent briefs used for the run (v2) |
| `drafts/RULE_QUESTIONS.md` | 151 cases the v2 rules did not decide |
| `drafts/RULES_V3_PROPOSAL.md`, `drafts/DECISIONS.md` | the questions collapsed into 16 decisions with a schema v3, and the decision record |
| `drafts/DRAFTER_BRIEF_v3.md` | the brief written to those decisions |
| `drafts/matrix.py` → `matrix_entries.csv`, `matrix_cells.csv` | one row per entry and per cell: drafter and checker status, all fact fields |
| `drafts/lint.py` | schema check on the drafts |
| `render_pilot.py` → `drafts/pilot_render/atlas.png` (not committed) | all drafts through `figure.py` with checker corrections applied |
| `drafts/engagement_outcomes.py` → `context_outcomes.csv` | Phase 2 and Phase 3 advancement of each context's class, from the DB |
| `drafts/engagement_kind_result.py` → `engagement_experiment.csv`, `ENGAGEMENT_KIND_RESULT.md` | whether the kind of engagement readout tracks the class's advancement |

## Running

```
uv sync
.venv/bin/python analyses/model-system-atlas/lists.py                         # DATABASE_URL in .env; read-only
.venv/bin/python analyses/model-system-atlas/drafts/matrix.py
.venv/bin/python analyses/model-system-atlas/drafts/lint.py
.venv/bin/python analyses/model-system-atlas/render_pilot.py
.venv/bin/python analyses/model-system-atlas/drafts/engagement_outcomes.py    # read-only
.venv/bin/python analyses/model-system-atlas/drafts/engagement_kind_result.py
```

Drafts stay in `drafts/`, never in `contexts/`. Nothing here writes to the DB.
