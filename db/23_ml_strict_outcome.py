"""ML scorers on STRICT per-(target × indication) outcome.

Previous benchmarks used 'approved for any indication' as ground truth. This
inflated the positive rate to 23% when the honest per-T-I approval rate is 5%.

This rerun applies the strict outcome and expects lower but honest AUC.
"""

import os
import sys
import numpy as np
import psycopg2
from psycopg2.extras import execute_values, Json, RealDictCursor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
_runner = import_module("11_benchmark_runner")
_ml = import_module("13_ml_scorers")

DB_URL = os.environ["DATABASE_URL"]


STRICT_COHORT_SQL = """
    SELECT
      s.target_id, s.indication_id,
      s.strict_approved_this_ti AS any_approved,     -- strict ground truth
      s.loose_approved_any_indication AS loose_approved,
      s.first_trial_date, s.last_trial_date, s.max_phase_reached,
      s.n_programs, s.n_sponsors, s.outcomes_broad_all,
      t.symbol AS target_symbol, i.display_name AS indication_name,
      i.therapeutic_area,
      tw.*,
      (SELECT value_text FROM preclin.evidence_score
        WHERE subject_type='target_indication' AND subject_id = s.target_id
          AND subject_id2 = s.indication_id AND dimension = 'nelson_tier'
        LIMIT 1) AS nelson_tier
    FROM preclin.v_target_indication_strict_outcome s
    JOIN public.targets t ON t.id = s.target_id
    JOIN preclin.indication i ON i.indication_id = s.indication_id
    JOIN preclin.v_target_evidence_wide tw ON tw.target_id = s.target_id
    WHERE s.max_phase_reached >= 2
      AND (t.pathogen_type IS NULL OR t.pathogen_type = '')
      AND s.outcomes_broad_all NOT SIMILAR TO 'in_dev%%'
"""


def load_strict_cohort():
    conn = psycopg2.connect(DB_URL)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(STRICT_COHORT_SQL)
        rows = cur.fetchall()
    conn.close()
    return list(rows)


def run(scorer_name, model_ctor, cohort_label="strict"):
    print(f"\n== {scorer_name} on STRICT per-T-I outcome ==")
    rows = load_strict_cohort()
    X = np.stack([_ml.row_to_feature_vector(r) for r in rows])
    y = np.array([1 if r["any_approved"] else 0 for r in rows], dtype=np.int64)
    print(f"  cohort n={len(rows)}, positive rate: {y.mean():.4f} ({y.sum()} approved)")

    oof, fold_aucs = _ml.cv_predict(model_ctor, X, y, n_splits=5)
    print(f"  Per-fold AUCs: {[f'{a:.3f}' for a in fold_aucs]}")

    y_list, p_list = y.tolist(), oof.tolist()
    auc, auc_lo, auc_hi = _runner.bootstrap_metric(y_list, p_list, _runner.auc_roc)
    brier = _runner.brier_score(y_list, p_list)
    r10 = _runner.recall_at_top_k(y_list, p_list, 0.10)
    p10 = _runner.precision_at_top_k(y_list, p_list, 0.10)
    rs10 = _runner.rs_by_top_decile(y_list, p_list)
    ece = _runner.calibration_ece(y_list, p_list)
    print(f"  AUC = {auc:.3f} [{auc_lo:.3f}, {auc_hi:.3f}]")
    print(f"  Brier = {brier:.3f}, R@10% = {r10:.3f}, P@10% = {p10:.3f}, RS10 = {rs10:.2f}, ECE = {ece:.3f}")

    conn = psycopg2.connect(DB_URL)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO preclin.benchmark_run
              (scoring_function, scoring_version, cohort_definition,
               n_ti_pairs, n_approved, n_failed,
               auc_roc, auc_roc_ci_lo, auc_roc_ci_hi, brier_score,
               recall_at_10pct, precision_at_10pct, rs_top_decile,
               calibration_ece, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING benchmark_run_id
        """, (scorer_name, "v2_strict", "ti_phase2plus_strict", len(rows),
              int(y.sum()), int(len(y) - y.sum()),
              auc, auc_lo, auc_hi, brier, r10, p10, rs10, ece,
              "STRICT per-T-I approval — approved for THIS indication specifically. Fixes loose/loose ground-truth caveat."))
        run_id = cur.fetchone()[0]

        ranked_idx = np.argsort(-oof)
        rank_map = {i: r + 1 for r, i in enumerate(ranked_idx)}
        preds = [(run_id, r["target_id"], r["indication_id"],
                  float(p), "high" if p >= 0.35 else ("medium" if p >= 0.18 else "low"),
                  rank_map[i], None, None, "medium", 20,
                  bool(yi), None, r.get("max_phase_reached"), r.get("n_programs"),
                  None)
                 for i, (r, p, yi) in enumerate(zip(rows, oof, y))]
        execute_values(cur, """
            INSERT INTO preclin.benchmark_prediction
              (benchmark_run_id, target_id, indication_id, predicted_p_approval,
               predicted_tier, predicted_rank, top_supporting_dims, top_concerning_dims,
               score_confidence, n_features_used, y_approved, y_realization_date,
               y_highest_phase, y_n_programs, evidence_snapshot)
            VALUES %s
        """, preds, page_size=1000)
        conn.commit()
    conn.close()


if __name__ == "__main__":
    run("lightgbm_strict_v1", _ml.make_lgb)
    run("randomforest_strict_v1", _ml.make_rf)
    run("logreg_strict_v1", _ml.make_logreg)
