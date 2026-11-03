# Model-system atlas (issue #76)

For each indication × drug class, whether the preclinical model the class relied on predicted what happened
in patients, on four questions (engagement, dose, efficacy, safety), as a dated strip of statuses.
`contexts/`, `figure.py` and `atlas.png` are the prototype from `atlas-prototype`. Everything else is the
first full run on 70 named contexts and the rules proposal that came out of it.

## Layout

| path | contents |
|---|---|
| `lists.py` → `lists/` | the context list from the DB: indications ranked by Phase 2 entrants 2008–2019 (`report.section1.phase_rows` cohort), the most-developed novel drug class per indication, a 200-program long-tail sample, and `swing_seats.csv` (indications that enter or leave the list between the simple and strict cohorts) |
| `drafts/<id>.json`, `drafts/<id>.check.json` | 70 drafted contexts and their checker verdicts; `manifest.csv` tracks them |
| `drafts/DRAFTER_BRIEF.md`, `drafts/CHECKER_BRIEF.md` | the agent briefs used for the run (v2) |
| `drafts/RULE_QUESTIONS.md` | 151 cases the v2 rules did not decide |
| `drafts/RULES_V3_PROPOSAL.md`, `drafts/DECISIONS.md` | the questions collapsed into 15 decisions with a schema v3, and the decision record |
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
