-- Benchmark framework — evaluate any target-scoring model against historical outcomes.
-- Any scoring function (ours or external) writes predictions into benchmark_prediction.
-- Metrics computed by 11_benchmark_runner.py, stored in benchmark_run.

BEGIN;

-- ============================================================
-- benchmark_run — one row per (scoring_function × cutoff × realization) run
-- ============================================================
CREATE TABLE IF NOT EXISTS preclin.benchmark_run (
  benchmark_run_id   BIGSERIAL PRIMARY KEY,
  scoring_function   TEXT NOT NULL,          -- 'random_v1' | 'family_precedent_v1' | 'genetic_only_v1' | 'nelson_only_v1' | 'rs_composite_v1' | 'external_<name>'
  scoring_version    TEXT NOT NULL,
  cutoff_date        DATE NOT NULL,          -- information cutoff (NULL means "use all current evidence")
  realization_years  INTEGER,                -- years post-cutoff for outcome realization (NULL if using current outcomes)
  cohort_definition  TEXT NOT NULL,          -- 'ti_phase2plus' | 'ti_phase3plus' | 'all_ti'
  n_ti_pairs         INTEGER,
  n_approved         INTEGER,                -- positives in ground truth
  n_failed           INTEGER,                -- negatives
  n_excluded_indev   INTEGER,                -- excluded due to still-in-development
  -- Overall metrics
  auc_roc            NUMERIC,
  auc_roc_ci_lo      NUMERIC,
  auc_roc_ci_hi      NUMERIC,
  brier_score        NUMERIC,
  brier_score_ci_lo  NUMERIC,
  brier_score_ci_hi  NUMERIC,
  -- Ranking metrics
  recall_at_5pct     NUMERIC,
  recall_at_10pct    NUMERIC,
  recall_at_20pct    NUMERIC,
  precision_at_10pct NUMERIC,
  mrr                NUMERIC,                -- mean reciprocal rank of approved T-Is
  -- Pheiron-style RS by predicted decile
  rs_top_decile      NUMERIC,
  rs_top_quartile    NUMERIC,
  -- Calibration
  calibration_slope  NUMERIC,
  calibration_ece    NUMERIC,                -- expected calibration error
  -- Metadata
  notes              TEXT,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_bmk_run_fn ON preclin.benchmark_run(scoring_function);
CREATE INDEX IF NOT EXISTS idx_bmk_run_cutoff ON preclin.benchmark_run(cutoff_date);

COMMENT ON TABLE preclin.benchmark_run IS 'One row per benchmark run: (scoring function × cutoff × cohort). Stores computed metrics with bootstrap CIs.';

-- ============================================================
-- benchmark_prediction — one row per T-I × run
-- ============================================================
CREATE TABLE IF NOT EXISTS preclin.benchmark_prediction (
  benchmark_run_id      BIGINT NOT NULL REFERENCES preclin.benchmark_run(benchmark_run_id) ON DELETE CASCADE,
  target_id             INTEGER NOT NULL,
  indication_id         INTEGER NOT NULL,
  -- Prediction
  predicted_p_approval  NUMERIC,             -- calibrated probability, [0, 1]
  predicted_tier        TEXT,                -- 'low' | 'medium' | 'high'
  predicted_rank        INTEGER,             -- rank within this benchmark run
  top_supporting_dims   TEXT[],              -- top explanatory positive dimensions
  top_concerning_dims   TEXT[],              -- top explanatory negative dimensions
  score_confidence      TEXT,                -- 'high' | 'medium' | 'low' | based on n_dimensions non-null
  n_features_used       INTEGER,             -- how many dimensions were non-null for this row
  -- Ground truth
  y_approved            BOOLEAN,             -- did any program on this T-I get approved
  y_realization_date    DATE,
  y_highest_phase       INTEGER,             -- highest phase reached across all programs on this T-I
  y_n_programs          INTEGER,             -- number of programs on this T-I
  -- Snapshot (for reproducibility)
  evidence_snapshot     JSONB,               -- feature vector used
  PRIMARY KEY (benchmark_run_id, target_id, indication_id)
);
CREATE INDEX IF NOT EXISTS idx_bmk_pred_run ON preclin.benchmark_prediction(benchmark_run_id);
CREATE INDEX IF NOT EXISTS idx_bmk_pred_target ON preclin.benchmark_prediction(target_id);

COMMENT ON TABLE preclin.benchmark_prediction IS 'One row per (T-I, run). Stores prediction + ground truth + evidence snapshot for reproducibility.';

-- ============================================================
-- v_benchmark_leaderboard — pretty-printed leaderboard
-- ============================================================
DROP VIEW IF EXISTS preclin.v_benchmark_leaderboard CASCADE;
CREATE VIEW preclin.v_benchmark_leaderboard AS
SELECT
  scoring_function, scoring_version, cutoff_date, cohort_definition,
  n_ti_pairs, n_approved,
  ROUND(100.0 * n_approved / NULLIF(n_ti_pairs, 0), 1) AS baseline_approval_pct,
  ROUND(auc_roc, 3) AS auc,
  '[' || ROUND(auc_roc_ci_lo, 3) || ', ' || ROUND(auc_roc_ci_hi, 3) || ']' AS auc_ci,
  ROUND(brier_score, 3) AS brier,
  ROUND(recall_at_10pct, 3) AS r_at_10pct,
  ROUND(precision_at_10pct, 3) AS p_at_10pct,
  ROUND(rs_top_decile, 2) AS rs_top10pct,
  ROUND(calibration_ece, 3) AS calib_err,
  created_at
FROM preclin.benchmark_run
ORDER BY cutoff_date DESC, auc_roc DESC;

COMMENT ON VIEW preclin.v_benchmark_leaderboard IS
'Ranked leaderboard of all scoring functions across all benchmark runs.';

-- ============================================================
-- v_benchmark_ablation — per-dimension marginal contribution
-- ============================================================
DROP VIEW IF EXISTS preclin.v_benchmark_calibration CASCADE;
CREATE VIEW preclin.v_benchmark_calibration AS
WITH bins AS (
  SELECT
    bp.benchmark_run_id,
    WIDTH_BUCKET(bp.predicted_p_approval, 0, 1, 10) AS bin,
    COUNT(*) AS n,
    AVG(bp.predicted_p_approval) AS mean_predicted,
    AVG(CASE WHEN bp.y_approved THEN 1.0 ELSE 0.0 END) AS observed_rate
  FROM preclin.benchmark_prediction bp
  WHERE bp.predicted_p_approval IS NOT NULL
  GROUP BY bp.benchmark_run_id, bin
)
SELECT
  br.scoring_function, br.scoring_version, br.cutoff_date, b.bin,
  b.n, b.mean_predicted, b.observed_rate,
  ROUND((b.observed_rate - b.mean_predicted)::numeric, 3) AS calibration_gap
FROM bins b
JOIN preclin.benchmark_run br ON br.benchmark_run_id = b.benchmark_run_id
ORDER BY br.scoring_function, br.cutoff_date, b.bin;

COMMENT ON VIEW preclin.v_benchmark_calibration IS
'Calibration curves per benchmark run: predicted probability bin × observed approval rate.';

COMMIT;
