# Model-system atlas (issue #76)

For each disease × mechanism (a tile), whether the preclinical models the drug class relied on predicted what
happened in patients, on four questions (engagement, dose, efficacy, safety), stored as dated tracks in
`preclin.atlas_*` (migrations `db/133_atlas.sql`, `db/135_atlas_tracks.sql`, `db/137_atlas_comments.sql`). The main paper figure is
`atlas_glance_main.*`; the supplementary figure is `atlas_glance_supplement_p1..p4.*`. `lessons/` is an exploratory
drill-down over the stored tiles (model families, engagement held against efficacy, the safety contradictions typed
by hand; `lessons/LESSONS.md`, `lessons/robustness.md`); its figures are not paper figures. `lessons/engaged/` codes the
reasons recorded for efficacy failure in the classes whose target engagement was confirmed (`lessons/engaged/LEGEND.md`).

`DATABASE_URL` and `FIRECRAWL_API_KEY` live in `.env`. Only `class_audit.py store`, `fetch_sources.py store` and
`drafts/route_store.py` (through `drafts/track_store.py`) write to the database, each replacing its own unit.

```
.venv/bin/python analyses/model-system-atlas/lists.py                      # named indications
.venv/bin/python analyses/model-system-atlas/class_audit.py [store]        # register and tracked tiles
.venv/bin/python analyses/model-system-atlas/fetch_sources.py [store]      # FDA review texts
# per tile, the agent passes in drafts/{DRAFT,CHECK,ADJ,MODELS,MODELS_CHECK}_TASK.md, then:
.venv/bin/python analyses/model-system-atlas/drafts/merge_models.py <slug>
.venv/bin/python analyses/model-system-atlas/drafts/lint.py
.venv/bin/python analyses/model-system-atlas/drafts/route_store.py [slug ...]
.venv/bin/python analyses/model-system-atlas/drafts/collect_questions.py   # open rule questions
.venv/bin/python analyses/model-system-atlas/glance.py
.venv/bin/python analyses/model-system-atlas/glance_nature.py main
.venv/bin/python analyses/model-system-atlas/glance_nature.py supplement
.venv/bin/python analyses/model-system-atlas/indications.py
.venv/bin/python analyses/model-system-atlas/burden.py
.venv/bin/python analyses/model-system-atlas/lessons/lessons.py all        # exploratory; read-only
```
