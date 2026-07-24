# Section 2, part 1 — predictive power of evidence (figure legend)

Data note for the three figures. Everything here uses **Melissa's own constructs**;
where a definition is hers vs. a presentation choice is flagged.

## The three figures

1. **`genetics_dose_response`** — approval rate binned by Melissa's **exact
   `genetic_only_v1` score** (her `benchmark/scorers_rule_based.py` additive rule:
   ClinGen ≥1 +0.6, Mendelian ≥5 +0.5 / ≥1 +0.2, OT-genetic ≥0.5 +0.5 / ≥0.3 +0.3,
   OT-somatic ≥0.3 +0.3, Nelson tiers when present). Observed approval:
   None (score 0) **8%** → Weak (0.1–0.9) **19%** → Moderate (1.0–1.3) **22%** →
   Strong (≥1.4) **45%**. Strong ≈ **6×** the no-evidence rate. (Score bins are my
   presentation; the score is hers. Numbers from a fresh live-DB pull, n=8,144.)

2. **`category_ablation`** — Melissa's **leave-one-category-out ablation**
   (`analyses/ablation.py`, strict Phase 2+ LogReg). AUC lost when a category is
   removed: **A. Genetics −17.7pp** · Context −1.8 · B. Mechanistic −0.6 ·
   E. Human PD −0.3 · H. Safety −0.2 · I. Landscape −0.1 · **C. Cell 0.0 · D. Animal 0.0**.
   This is the *multivariate* category-importance answer (genetics dominant; cell/animal
   literature add ~zero on top of genetics — publication-bias saturation). Her numbers.

   **On the base AUC (important):** the ablation is computed on the full model's
   **random-split** CV AUC of **0.829**, which is an *in-sample* number, not a
   forward-looking one. For the same strict Ph2+ cohort, `RESULTS.md` reports the
   honest generalization estimates: **held-out-target (GroupKFold) 0.804** and
   **time-machine (train pre-2019) 0.769**. Cite 0.804 as the headline model
   performance, or label 0.829 explicitly as random-split/in-sample — do not present
   0.829 as a predictive number. The **ablation *deltas* are robust to this**: per
   `RESULTS.md` the GroupKFold correction costs only ~2.2pp overall and does not change
   the category ranking (genetics still dominant, cell/animal still ~0).

3. **`predictive_power_by_evidence`** — per-dimension Relative Success from her
   `v_relative_success_clean` (RS = approval-with ÷ approval-without, 95% bootstrap CI).
   LLM-extracted literature lines (C/D/E) removed from this headline view; annotation-count
   dims (Reactome/GO/PPI) are study-depth proxies — read with care.

## What was wrong before (now fixed)

The earlier "category as a whole" figure and a hand-built genetics tier were **my
constructions and were misleading**:
- an "any genetic dimension" flag fired for 83% of pairs and collapsed toward the weakest
  criterion; and
- treating unscored targets as "not-supported" inflated RS.

Replaced by **her** genetic_only_v1 score (genetics figure) and **her** ablation (category
figure). Removed CSVs: `genetics_tiers`, `category_structured_compare`,
`relative_success_by_category`.

## On genetic coverage (the "sparse tiers" question)

The **Nelson categorical tier** (`nelson_tier`, T0–T4) is populated for only ~1% of pairs —
because only a small curated batch (~395 rows) was ever ingested, and it lives at the
program level. That is **not** the coverage of genetic support. The dimensions
`genetic_only_v1` actually uses are near-complete: **ClinGen 100%, Mendelian 100%,
OT-genetic 92%, OT-somatic 25%** (somatic is cancer-only) — ANY genetic dim present for
**100%** of pairs. So the scorer applies to the whole cohort; Nelson is just an optional bonus.

## Non-genetic categories (definitions, Melissa's taxonomy)

- **Landscape / precedent** (`I_landscape`) — causal-disease breadth (≥3 diseases with
  causal evidence; RS 1.27, populated for 3,107 pairs). The intended second sub-clause,
  drug precedent (DGIdb ≥5 known interacting drugs), is **inert**: `n_dgidb_drugs` is 0/NULL
  for **every** target in `v_target_evidence_wide` (never ingested with real values), so
  that dimension has n_supported = 0 and RS = NaN. The plot drops the NaN row; it is listed
  here so the gap is disclosed rather than silently hidden. This also neuters the
  `n_dgidb_drugs ≥5` term wherever it appears in the rule-based scorers.
- **Constraint / safety** (`H_safety`) — gnomAD LoF-intolerance (pLI ≥0.9 / LOEUF <0.35);
  a **liability** (constrained genes approve less), not evidence-for.
- **Cell** — only structured signal is DepMap pan-essentiality (a liability); positive cell
  evidence exists only as the LLM Line-C literature score. **No structured in-vitro efficacy
  measure exists in this dataset** — a genuine gap.
- **Animal** — OT animal-model (Phenodigm) / IMPC KO phenotypes; univariate RS ~1.25 but
  ~0 marginal in the ablation (rides on genetics).

## Cohort & reproduce

Phase 2+ T-I pairs (n = 8,144 as of the latest live-DB pull, base approval 23%), placebos
filtered, canonical sponsors. (This is a live, continuously-refreshed DB; expect ~0.4% churn
in n between pulls. Regenerate the CSVs immediately before publishing.)
`analyses/plot_predictive_power.py` reads cached CSVs in `data/` (no DB required):
`relative_success_by_dimension`, `genetics_dose_response`, `category_ablation`.

## Data generation (how each cached CSV is produced)

- **`relative_success_by_dimension.csv`** — direct dump of `preclin.v_relative_success_clean`.
- **`genetics_dose_response.csv`** — `analyses/genetics_dose_response.py` (needs `DATABASE_URL`).
  Applies Melissa's exact `genetic_only_v1` additive scorer (ported verbatim from
  `benchmark/scorers_rule_based.py`) to the Phase 2+ pool, then bins by score.
- **`category_ablation.csv`** — transcribed from the leave-one-category-out ablation in
  `RESULTS.md` (`analyses/ablation.py`; strict Ph2+ LogReg). Base model AUC is the
  random-split 0.829 (in-sample); the honest generalization AUCs for this cohort are
  0.804 held-out-target and 0.769 time-machine (see the ablation note above).
