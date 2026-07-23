# Target-scoring benchmark

Evaluates any target-scoring model — ours or external — against historical (target × indication) approval outcomes.

## Task definition

**Given:** a (target × indication) pair and evidence known at time T
**Predict:** P(any drug on this T-I gets approved)
**Ground truth:** `preclin.v_target_indication_program.any_approved` (across all programs on this T-I)
**Cohort:** T-I pairs where ≥1 program reached Phase 2+ (n=2,611 currently)

## Baseline results (2026-07-23 run)

Cohort: T-I pairs Phase 2+, placebos+microbial targets filtered. Baseline approval rate = **28.4%**.

| Scorer | AUC (95% CI) | Brier | Recall@10% | Prec@10% | RS(top 10%) | ECE |
|---|---|---|---|---|---|---|
| **rs_composite_v1** | **0.714 [0.694, 0.738]** | 0.327 | 0.19 | 0.55 | 2.17 | 0.362 |
| genetic_only_v1 | 0.629 [0.608, 0.659] | 0.194 | 0.27 | 0.75 | **3.24** | **0.050** |
| family_precedent_v1 | 0.606 [0.590, 0.628] | 0.219 | 0.11 | 0.31 | 1.12 | 0.147 |
| nelson_only_v1 | 0.532 [0.518, 0.548] | 0.210 | **0.35** | **1.00** | **4.90** | 0.101 |
| random_v1 | 0.509 [0.485, 0.539] | 0.330 | 0.10 | 0.29 | 1.01 | 0.292 |

### Reading the leaderboard

- **rs_composite_v1 wins on AUC (0.714)** — best overall discrimination. Uses all 40+ dimensions weighted by observed RS.
- **nelson_only_v1 wins on precision (1.00 @ 10%)** — when it flags T3/T4, it's always right, but its coverage is tiny (only 139 T-I pairs have Nelson tier assigned).
- **genetic_only_v1 wins on calibration (ECE 0.05)** — predicted probabilities match observed rates well.
- **rs_composite_v1 has poor calibration (ECE 0.36)** — overconfident. Would benefit from Platt scaling or isotonic regression.

## Framework capabilities

**Any scorer plugs in via one of two paths:**

### Path 1 — In-process Python scorer

```python
def my_scorer(evidence: dict, context: dict) -> dict:
    return {
        'predicted_p_approval': ...,
        'predicted_tier': 'low' | 'medium' | 'high',
        'top_supporting_dims': [str],
        'top_concerning_dims': [str],
        'score_confidence': 'low' | 'medium' | 'high',
        'n_features_used': int,
    }

register_scorer("my_scorer_v1", my_scorer, "v1")
```

Then `python3 11_benchmark_runner.py my_scorer_v1`.

### Path 2 — External score CSV

For models we don't have code for (Pheiron, Insilico public predictions, etc.). CSV columns: `target_id, indication_id, predicted_p_approval`. Wire in via `wire_external_scores()` in `12_external_scorer_template.py`.

## Metrics

- **AUC-ROC** — probability that a random approved T-I outranks a random failed T-I. 0.5 = random.
- **Brier score** — mean squared error of probability predictions. Lower is better.
- **Recall @ top-k%** — of top-scored k% of T-I pairs, what fraction of all approved T-Is are captured
- **Precision @ top-k%** — of top-scored k%, what fraction actually approved
- **RS (top decile)** — P(approved | top 10%) / P(approved | rest). Direct Pheiron-comparable metric.
- **ECE (Expected Calibration Error)** — mean absolute gap between predicted probability and observed rate across bins. Lower is better.
- All with bootstrap 95% CIs (200 resamples).

## Views

```sql
-- Overall leaderboard
SELECT * FROM preclin.v_benchmark_leaderboard;

-- Calibration per scorer (predicted bin vs observed rate)
SELECT * FROM preclin.v_benchmark_calibration WHERE scoring_function='rs_composite_v1';

-- Top-scored predictions from any run
SELECT * FROM preclin.benchmark_prediction
WHERE benchmark_run_id = 6 ORDER BY predicted_rank
LIMIT 20;

-- Where our best scorer disagrees with ground truth
SELECT t.symbol, i.display_name, bp.predicted_p_approval, bp.y_approved,
       bp.top_supporting_dims, bp.top_concerning_dims
FROM preclin.benchmark_prediction bp
JOIN preclin.benchmark_run br USING (benchmark_run_id)
JOIN public.targets t ON t.id = bp.target_id
JOIN preclin.indication i ON i.indication_id = bp.indication_id
WHERE br.scoring_function = 'rs_composite_v1'
  AND bp.predicted_p_approval >= 0.6
  AND bp.y_approved = FALSE
ORDER BY bp.predicted_p_approval DESC
LIMIT 20;
```

## Cohort filters applied

Included:
- T-I pairs with ≥1 program reaching Phase 2+
- Target must be a human protein (`ip_type != 'Genomic'`, `pathogen_type IS NULL`)

Excluded:
- Placebos (`d.is_placebo = TRUE`)
- Microbial targets
- Combination-only interventions (no primary single target)
- T-I pairs still fully in development (undetermined outcome)

## Key caveats

1. **No time-machine yet.** All scorers use current-day evidence. Real predictive validity requires evidence_as_of dates and train-before-cutoff evaluation.
2. **Cohort is target-matched.** 2,611 T-I pairs from the ChEMBL-catalogued cohort. Selection bias: matched drugs are 10× more likely to be approved than the full 82k program universe.
3. **Base rate is 28.4%** in this cohort (vs 1.8% overall). All metrics must be interpreted against this baseline.
4. **No therapeutic-area stratification.** Signal quality varies by TA (oncology cell-lines work, neuro cell-lines don't).
5. **RS-composite is Bernoulli-fit on the same data it's evaluated on** — mild overfitting. Time-machine would fix.

## Extension ideas

- **Time-machine backtest** (biggest lift). Retrofit `evidence_as_of` dates → train scorers on pre-cutoff evidence → predict post-cutoff outcomes.
- **Per-therapeutic-area leaderboards** — cell evidence matters more in some TAs.
- **Ensemble/stacked scorer** combining strengths (nelson_only for precision + rs_composite for recall).
- **Calibration layer** — Platt scaling on rs_composite_v1 to fix ECE 0.36.
- **Multi-modal ML model** — train a real classifier on all 40 dimensions, benchmark against rs_composite hand-weights.
- **Compare against Nelson 2015 / Minikel 2024** on their T-I subset.

## Files

- `09_benchmark_schema.sql` — DDL for benchmark_run + benchmark_prediction tables + leaderboard views
- `10_benchmark_scorers.py` — 5 baseline scorers + plugin registry
- `11_benchmark_runner.py` — cohort loader, metrics, bootstrap CI, storage
- `12_external_scorer_template.py` — how to wire an external model
- `BENCHMARK.md` — this file

## Regenerate leaderboard

```bash
cd data/db
export DATABASE_URL='...'
python3 11_benchmark_runner.py             # all baselines
python3 11_benchmark_runner.py rs_composite_v1  # just one
psql "$DATABASE_URL" -c "SELECT * FROM preclin.v_benchmark_leaderboard"
```
