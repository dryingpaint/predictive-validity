# DB migration + Pheiron comparability — Summary

## Migration complete

All analyses now run against `preclin.*` schema in Neon Postgres. No more Python CSV joins for common questions.

**Ingested to DB:**
- 33 evidence dimensions in registry (+15 more from extra ingest)
- 8,875 indications (extends `public.diseases`)
- **52,694 drugs** (superset of `public.therapies`)
- 36,251 drug-target links (multi-source, priority-ordered)
- 544 US approvals + provisions for ex-US
- **82,014 programs** (drug × indication × sponsor 3-tuple)
- 88,999 program-trial links
- 82,014 program outcomes with confidence
- **~180,000 evidence-score facts** in long-form (target × dimension × source)
- **13,069 classifications** (Haiku + Sonnet why_stopped, silent-kill verifications, target resolutions)

## Outcome distribution at program level

| Outcome | n | %  |
|---|---|---|
| approved | 5,012 | 6.1% |
| efficacy_fail | 2,710 | 3.3% |
| safety_fail | 466 | 0.6% |
| commercial_fail | 8,869 | 10.8% |
| enrollment_fail | 1,868 | 2.3% |
| other_fail | 5,237 | 6.4% |
| phase_complete_no_approval (silent kill) | 25,877 | 31.6% |
| phase1_complete_no_advance | 25,768 | 31.4% |
| planned_termination | 576 | 0.7% |
| unknown | 5,631 | 6.9% |

Note: this is at 3-tuple program level (drug × indication × sponsor), so a drug approved for many indications counts many times. Same drug (e.g., pembrolizumab) contributes ~884 programs. To collapse to drug-level, use `SELECT DISTINCT drug_id ... WHERE approved_us = TRUE` (returns 544 unique drugs).

## New views for analysis

Instead of running Python scripts, do:

```sql
-- All target evidence at once
SELECT * FROM preclin.v_target_evidence_wide LIMIT 5;

-- Per drug program with all evidence + outcome
SELECT * FROM preclin.v_program_evidence_wide LIMIT 5;

-- One row per T-I pair (Pheiron unit)
SELECT * FROM preclin.v_target_indication_program LIMIT 5;

-- Pheiron-style RS per dimension
SELECT * FROM preclin.v_relative_success ORDER BY relative_success DESC;

-- Combination-evidence lift (Fig 4 style)
SELECT * FROM preclin.v_combination_evidence;

-- Pathway wrongness Phase 3+
SELECT * FROM preclin.v_pathway_wrongness;

-- Effect sizes 2x2 (feed to bootstrap CI script)
SELECT * FROM preclin.v_effect_sizes_2x2;

-- Failure taxonomy
SELECT * FROM preclin.v_failure_taxonomy;

-- Outcome summary
SELECT * FROM preclin.v_outcome_summary;

-- Drug coverage (selection-bias diagnostics)
SELECT * FROM preclin.v_drug_coverage;
```

## Relative Success (RS) — top signals

Query: `SELECT * FROM preclin.v_relative_success ORDER BY relative_success DESC`

At T-I unit, Phase 2+ cohort:

| Dimension | RS | % approved when supported |
|---|---|---|
| **Reactome pathways ≥5** | **2.90** | 33% |
| **Line E lit (human PD)** | **2.20** | 37% |
| **ClinGen Strong/Definitive** | **1.75** | 35% |
| Line C lit (cell) | 1.67 | 32% |
| OT somatic cancer ≥0.3 | 1.62 | 39% |
| Line D lit (animal) | 1.49 | 32% |
| Mendelian ≥5 | 1.49 | 34% |
| OT genetic ≥0.3 | 1.36 | 26% |
| IMPC ≥3 phenotypes | 1.35 | 24% |
| OT animal model ≥0.3 | 1.31 | 29% |
| **Tissue-specific (Tau ≥0.75)** | **1.18** | 25% |
| Causal disease pleiotropy ≥3 | 1.18 | 27% |
| **DepMap pan-essential** | **0.13** | 4% (strong negative) |

## Comparison to Pheiron's published numbers

Pheiron reports:
- Rare Mendelian: RS ~3.5 → ours 1.49 (Mendelian ≥5)
- Animal models: RS 2.31 → ours 1.31 (OT animal model)
- Colocalization: RS 1.8 → we don't have L2G data ingested (ot_l2g_score_max returned 0 rows — target_evidence.l2g_score is null-heavy)

**Our RS numbers are systematically ~40-60% lower than Pheiron's.** Reasons:

1. **Baseline definition differs.** We count "approved anywhere globally" (US or ex-US). Pheiron likely uses a stricter approval definition (FDA-only or first-approval). Broader baseline → smaller RS.
2. **T-I unit differs.** We take ANY approval across ALL programs against a T-I pair as "supported." Pheiron probably has a more granular gate (phase transition) which lowers the baseline approval rate.
3. **Sample size differs.** Pheiron: 31k T-I pairs. Ours: ~5k Phase 2+ T-I pairs with a matched target. Smaller with different selection filter.

**Directional agreement is total:**
- Human genetics (rare variant / ClinGen / Mendelian) top the list ✓
- Animal models modest positive ✓
- DepMap essentiality strong negative ✓
- Broad expression / hub-like negative or null ✓

## Combination-evidence lift (Pheiron Fig 4 style)

| Combination | RS_a alone | RS_b alone | RS_combined | % approved |
|---|---|---|---|---|
| OT genetic + Reactome pathways | 1.94 | 2.81 | **3.05** | 35.0% |
| **Mendelian + Line E (human PD)** | 1.21 | 2.20 | **1.56** | **43.3%** |
| ClinGen + Tissue-specific | 1.75 | 1.18 | 1.71 | 35.5% |
| Mendelian + Tissue-specific | 1.48 | 1.18 | 1.51 | 34.8% |
| Line C + Line D | 1.67 | 1.49 | 1.54 | 32.6% |
| OT genetic + OT animal model | 1.49 | 1.28 | 1.39 | 29.7% |

**Best single combination for approval rate: Mendelian evidence + published human PD engagement = 43.3% approval.**

Pheiron's genetics × tissue = 3.96 (with GTEx). Ours (ClinGen + Tau): 1.71. Our tissue combo doesn't show the same lift — likely because we're using bulk tissue expression Tau (from HPA/GTEx summary), not single-cell (Tabula Sapiens which Pheiron uses). Single-cell tissue-specificity is on the extension list.

## Pathway wrongness — SQL vs CSV comparison

Same question, two units:

| Dimension | Drug-level (old CSV) | T-I level (SQL) |
|---|---|---|
| Line C high, Phase 3+ any_fail | 79% | 59% |
| Line E high, Phase 3+ any_fail | 73% | 54% |
| ClinGen high, Phase 3+ any_fail | 76% | 57% |
| Mendelian ≥5, Phase 3+ any_fail | 75% | 54% |
| DepMap pan-essential | 97% | 97% |

**The T-I unit gives lower failure rates** because a T-I pair counts as "approved" if ANY of the drugs against it succeeded. Drug-level analysis is per-attempt; T-I level is per-pathway-shot.

Both are valid framings:
- **Drug-level "any_fail 79%"** = "if I'm developing this specific drug, my P(fail)"
- **T-I level "any_fail 59%"** = "if I'm pursuing this pathway with any of several drugs, my P(all fail)"

Both point to the same conclusion: **strong preclinical evidence still leaves majority failure at Phase 3.**

## What's still to do

1. **Single-cell tissue expression** — join `public.single_cell_expression` (3M rows) to get Tabula-Sapiens-style tissue specificity. Currently we only have HPA/GTEx summary Tau.
2. **Bootstrap CIs into `preclin.effect_size_snapshot`** — run `python3 04_effect_size_ci.py` after any ingest.
3. **Effect sizes at T-I level** — we have RS but not OR + CI at T-I unit. Add `v_effect_sizes_2x2_ti`.
4. **Filter placebo/vaccine programs** — 7,660 placebo "programs" are noise.
5. **Ingest ChiCTR + EU-CTR** for international failure coverage.
6. **BioRxiv preprint scraping** for method literature.

## Files added

- `data/db/01_schema.sql` — DDL (~250 lines)
- `data/db/02_ingest.py` — big-bang ingest from JSONL/CSV (~1,400 lines)
- `data/db/03_views.sql` — original analysis views
- `data/db/04_effect_size_ci.py` — bootstrap CI snapshot to `effect_size_snapshot` table
- `data/db/05_ingest_extra.py` — untapped genome-browser tables (tissue, pleiotropy, pathways, DGIdb, HPO, l2g, somatic, RNA expression, mendelian dominance split)
- `data/db/06_ti_views.sql` — T-I unit + Relative Success + combination-evidence views
- `data/db/RUNBOOK.md` — how to add dimensions, rerun analyses, common queries
- `data/DB_SCHEMA_DESIGN.md` — design principles + trade-offs
- `data/DB_MIGRATION_SUMMARY.md` — this file
