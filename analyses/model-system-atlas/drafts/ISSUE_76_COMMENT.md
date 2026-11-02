# Model-system atlas: 70 named contexts drafted and checked, rules v2 proposal (#76)

_Numbers from `matrix.py` over the finished run (71 contexts: the 70 named + the HF/SGLT2 pilot kept as the
repurposed-class example, rule question #24)._

## What this branch adds

`analyses/model-system-atlas/` on `atlas-named-contexts` (off `atlas-prototype`; Melissa's
`contexts/`, `figure.py`, `atlas.png` untouched):

| file | what it is |
|---|---|
| `lists.py` → `lists/` | reproduces the issue's indication table from the DB (`report.section1.phase_rows`, strict cohort), applies the 5 merges / 3 drops as code, ranks, samples 200 programs (seed 20261102), and derives the most-developed novel drug class per indication from `preclin.moiety_target` → `public.targets` with a ChEMBL mechanism fallback |
| `drafts/DRAFTER_BRIEF.md`, `drafts/CHECKER_BRIEF.md` | the two agent briefs (v2 adds rule-agnostic fact fields so every cell can be re-scored when the rules change) |
| `drafts/<id>.json`, `drafts/<id>.check.json` | 70 drafted contexts and their checker verdicts; `manifest.csv` tracks status |
| `drafts/RULE_QUESTIONS.md` | 151 cases the current rules did not decide, each with the context it bit and a proposed answer |
| `drafts/RULES_V2_PROPOSAL.md` | the 151 questions collapsed into 14 decisions + a schema v3; the thing to agree on |
| `drafts/matrix.py` → `matrix_entries.csv`, `matrix_cells.csv` | one row per entry / per cell, drafter and checker status side by side, all fact fields |
| `drafts/summary_figure.py` → `summary.png` | status by question, drafter vs checker, stated vs juxtaposed, by area |
| `drafts/render_pilot.py` → `drafts/pilot_render/atlas.png` | all 70 through `figure.py` with checker corrections applied |
| `drafts/lint.py` | schema check (empty cells, same-status entries, unknown keys) |

Nothing was written to the DB (#70 is open); `lists.py` is read-only.

## Headline

Across 71 contexts and 284 cells after the checker pass:

| question | matched | contradicted | never compared |
|---|---|---|---|
| engagement | 61 % | 4 % | 35 % |
| dose | 25 % | 7 % | 61 % |
| efficacy | 49 % | 30 % | 21 % |
| safety | 24 % | 34 % | 34 % |

- Checkers reversed 19 % of latest cell statuses, mostly `same` → `untested` where the drafter had
  paired a model paper with a trial paper and no source stated the comparison. That is the single
  biggest rules decision (proposal §1): read strictly, rule 1 greys 48 % of scored cells and both of
  the seed contexts.
- Safety is the reddest column, and half of its red is the model being *silent* on a harm rather
  than wrong about it; the proposal makes "askable silence" the test.
- The five colours cannot show the Scannell case (surrogate matched, hard-endpoint trial null: SHPT,
  HF, PBC all read green); proposal §9 adds an `outcome_tested` marker.
- `model_filed` is null on 193 of 523 entries because the agents could not read >10 MB FDA review PDFs; a
  checker then read one (Saxenda) with curl + pdftotext and found a safety `contra` the drafter had
  missed. Pre-fetching the reviews is the main production fix before the κ run.

## Two things to flag on the lists

1. **Cohort definition.** The issue's 15,759 Phase 2 entrants is the simple `ph2_start` count. The
   report's own `phase_rows` cohort (industry-sponsored entry, vaccines and lifecycle programs out)
   gives 5,825. After your merges and drops, 53 of your 64 indications reproduce; 11 leave the
   top-4-per-area list and 18 enter (`lists/swing_seats.csv`). The ones that leave are the big
   academic / repurposing indications (MS, ALS, sepsis, CKD, HNSCC), which is a real choice about
   what the atlas is for, not a data error:

| area | leaves (issue list, simple count) | enters (strict cohort, n) |
|---|---|---|
| allergy | food allergy (9) | allergic disease (7), eosinophilic esophagitis (5) |
| endocrine |  | secondary hyperparathyroidism (6) |
| gastroenterology | cirrhosis of liver (28) | primary biliary cholangitis (15), gastroesophageal reflux disease (11) |
| hematology |  | hemophilia B (10), paroxysmal nocturnal hemoglobinuria (9) |
| infectious_disease | infectious disease with sepsis (39) | chronic hepatitis B virus infection (18) |
| metabolic |  | Prader-Willi syndrome (6) |
| neurology | amyotrophic lateral sclerosis (53), multiple sclerosis (60) | diabetic neuropathy (32), migraine disorder (29) |
| oncology | head and neck squamous cell carcinoma (89) | follicular lymphoma (34) |
| ophthalmology | uveitis (20) | open-angle glaucoma (20) |
| other | chronic kidney disease (44) | acne (31), diabetic kidney disease (26) |
| psychiatry | post-traumatic stress disorder (36), alcohol dependence (35) | attention deficit-hyperactivity disorder (21), insomnia (11) |
| urology | erectile dysfunction (15) | premature ejaculation (5) |

   The 70 contexts drafted here follow the strict list. Which cohort should the atlas join to?
2. **"The" drug class is a thin plurality.** In most indications the most-developed novel class is
   2–5 of 20–80 programs. The context list is still the right unit, but the atlas should print the
   class's program share so a reader sees how little of the indication a green tile covers
   (proposal §12).

## What I'd like from you

- Read `RULES_V2_PROPOSAL.md` and mark each of the 14 decisions agree / change. Decisions 1, 4, 6
  and 9 move the most cells.
- Say which cohort the join uses.
- Whether writes to `pv_evidence.llm_decision` are acceptable during #70, so the two briefs can be
  ported into `pipeline/llm.py` `Task`s and the κ re-draft (30 contexts under v2 rules) runs through
  the pipeline rather than ad hoc agents.

## Not done

- Visualization is deliberately untouched. `drafts/summary.png` and `drafts/summary_v2.png` are working
  views of the latest status only; both drop the by-year strips that `figure.py` draws, which is the
  signal the atlas is for. The rendered strips for all 70 are in `drafts/pilot_render/atlas.png`
  (regenerate with `render_pilot.py`; not committed, 5 MB).

- Production port of the briefs into `pipeline/llm.py` (needs your `ANTHROPIC_API_KEY`).
- The 200-program long-tail sample is drawn (`lists/sample.csv`) but not drafted.
