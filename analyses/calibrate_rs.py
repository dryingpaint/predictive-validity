"""Calibrate rs_composite_v1 via Platt scaling (isotonic regression).

Fixes ECE 0.36 → target sub-0.10 without changing AUC.
Applies to rs_composite raw scores → maps to well-calibrated P(approval).
"""

import os
import sys
import numpy as np
import psycopg2
from psycopg2.extras import execute_values, Json, RealDictCursor
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import StratifiedKFold

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'benchmark'))
from importlib import import_module
_scorers = import_module("scorers_rule_based")
_runner = import_module("runner")

DB_URL = os.environ["DATABASE_URL"]


def main():
    conn = psycopg2.connect(DB_URL)
    print("Loading cohort ...")
    rows = _runner.load_cohort(conn, min_phase=2)
    print(f"  n = {len(rows)}")

    # Score with rs_composite
    raw_scores, y_labels = [], []
    for row in rows:
        evidence, context, y = _runner.row_to_evidence_context(row)
        result = _scorers.SCORERS["rs_composite_v1"][0](evidence, context)
        raw_scores.append(result["predicted_p_approval"])
        y_labels.append(int(y))
    raw = np.array(raw_scores)
    y = np.array(y_labels)

    # 5-fold CV: for each fold, fit isotonic regression on 4 folds → transform held-out
    kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    calibrated_oof = np.zeros(len(y), dtype=np.float64)
    for train_idx, test_idx in kf.split(raw, y):
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(raw[train_idx], y[train_idx])
        calibrated_oof[test_idx] = iso.predict(raw[test_idx])

    # Metrics
    y_list = y.tolist()
    p_list = calibrated_oof.tolist()
    auc, auc_lo, auc_hi = _runner.bootstrap_metric(y_list, p_list, _runner.auc_roc)
    brier = _runner.brier_score(y_list, p_list)
    r10 = _runner.recall_at_top_k(y_list, p_list, 0.10)
    p10 = _runner.precision_at_top_k(y_list, p_list, 0.10)
    rs10 = _runner.rs_by_top_decile(y_list, p_list)
    ece = _runner.calibration_ece(y_list, p_list)

    print(f"  AUC = {auc:.3f} [{auc_lo:.3f}, {auc_hi:.3f}]")
    print(f"  Brier = {brier:.3f}, R@10% = {r10:.3f}, P@10% = {p10:.3f}")
    print(f"  RS(top 10%) = {rs10:.2f}, ECE = {ece:.3f} (was 0.362 uncalibrated)")

    # Store
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
        """, ("rs_composite_calibrated_v1", "v1", "ti_phase2plus", len(rows),
              int(y.sum()), int(len(y) - y.sum()),
              auc, auc_lo, auc_hi, brier, r10, p10, rs10, ece,
              "Isotonic Platt scaling of rs_composite_v1 raw scores"))
        run_id = cur.fetchone()[0]

        ranked = np.argsort(-calibrated_oof)
        rank_map = {i: r + 1 for r, i in enumerate(ranked)}
        preds = [(run_id, row["target_id"], row["indication_id"],
                  float(calibrated_oof[i]),
                  "high" if calibrated_oof[i] >= 0.35 else ("medium" if calibrated_oof[i] >= 0.18 else "low"),
                  rank_map[i], None, None, "medium", 20,
                  bool(y[i]), None, row.get("max_phase_reached"), row.get("n_programs"),
                  None)
                 for i, row in enumerate(rows)]
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
    print(f"  Stored as benchmark_run_id={run_id}")


if __name__ == "__main__":
    main()
