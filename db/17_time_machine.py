"""Time-machine backtest — train on pre-cutoff T-I pairs, test on post-cutoff.

Uses first_trial_date on the T-I pair as the temporal split point.
- Train: T-I pairs whose FIRST trial started BEFORE cutoff_date (had time to resolve).
- Test:  T-I pairs whose FIRST trial started AT/AFTER cutoff_date (novel programs).

Note on caveats:
- Feature values are still current-day (evidence_as_of dates aren't retrofit).
  This is a partial time-machine — cohort split by time, features are current.
- Full time-machine requires retrofitting extracted_at per source.
"""

import os
import sys
from datetime import date
from typing import List

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
_runner = import_module("11_benchmark_runner")
_ml = import_module("13_ml_scorers")

DB_URL = os.environ["DATABASE_URL"]

DEFAULT_CUTOFF = date(2019, 1, 1)


TIME_COHORT_SQL = """
    SELECT
      ti.target_id, ti.indication_id, ti.any_approved,
      ti.first_trial_date, ti.last_trial_date, ti.max_phase_reached,
      ti.n_programs, ti.n_drugs, ti.n_sponsors,
      t.symbol AS target_symbol,
      i.display_name AS indication_name, i.therapeutic_area,
      tw.*,
      (SELECT value_text FROM preclin.evidence_score
        WHERE subject_type='target_indication' AND subject_id = ti.target_id
          AND subject_id2 = ti.indication_id AND dimension = 'nelson_tier'
        LIMIT 1) AS nelson_tier
    FROM preclin.v_target_indication_program ti
    JOIN public.targets t ON t.id = ti.target_id
    JOIN preclin.indication i ON i.indication_id = ti.indication_id
    JOIN preclin.v_target_evidence_wide tw ON tw.target_id = ti.target_id
    WHERE ti.max_phase_reached >= 2
      AND ti.first_trial_date IS NOT NULL
      AND (t.pathogen_type IS NULL OR t.pathogen_type = '')
      AND ti.outcomes_broad_all NOT SIMILAR TO 'in_dev%%'
      AND NOT EXISTS (
        SELECT 1 FROM preclin.program p
        JOIN preclin.drug d ON d.drug_id = p.drug_id
        WHERE p.indication_id = ti.indication_id AND d.is_placebo IS TRUE
      )
"""


def load_time_cohort():
    conn = psycopg2.connect(DB_URL)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(TIME_COHORT_SQL)
        rows = cur.fetchall()
    conn.close()
    return list(rows)


def train_test_split_by_date(rows, cutoff: date):
    train, test = [], []
    for r in rows:
        fd = r["first_trial_date"]
        if fd is None:
            continue
        if fd < cutoff:
            train.append(r)
        else:
            test.append(r)
    return train, test


def run_time_machine(cutoff=DEFAULT_CUTOFF, model_ctor=_ml.make_lgb, scorer_name="lightgbm_v1"):
    print(f"\n== Time-Machine: {scorer_name}, cutoff={cutoff} ==")
    rows = load_time_cohort()
    train_rows, test_rows = train_test_split_by_date(rows, cutoff)
    print(f"  train: {len(train_rows)} T-I (started before {cutoff})")
    print(f"  test:  {len(test_rows)} T-I (started at/after {cutoff})")

    if len(train_rows) < 50 or len(test_rows) < 50:
        print("  Insufficient data.")
        return

    X_train = np.stack([_ml.row_to_feature_vector(r) for r in train_rows])
    y_train = np.array([1 if r["any_approved"] else 0 for r in train_rows], dtype=np.int64)
    X_test = np.stack([_ml.row_to_feature_vector(r) for r in test_rows])
    y_test = np.array([1 if r["any_approved"] else 0 for r in test_rows], dtype=np.int64)

    print(f"  train positive rate: {y_train.mean():.3f}")
    print(f"  test  positive rate: {y_test.mean():.3f}")

    model = model_ctor()
    model.fit(X_train, y_train)
    p_test = model.predict_proba(X_test)[:, 1]

    y_list = y_test.tolist()
    p_list = p_test.tolist()
    auc, auc_lo, auc_hi = _runner.bootstrap_metric(y_list, p_list, _runner.auc_roc)
    brier = _runner.brier_score(y_list, p_list)
    r10 = _runner.recall_at_top_k(y_list, p_list, 0.10)
    p10 = _runner.precision_at_top_k(y_list, p_list, 0.10)
    rs10 = _runner.rs_by_top_decile(y_list, p_list)
    ece = _runner.calibration_ece(y_list, p_list)

    print(f"  AUC = {auc:.3f} [{auc_lo:.3f}, {auc_hi:.3f}]")
    print(f"  Brier = {brier:.3f}, R@10% = {r10:.3f}, P@10% = {p10:.3f}")
    print(f"  RS(top 10%) = {rs10:.2f}, ECE = {ece:.3f}")

    conn = psycopg2.connect(DB_URL)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO preclin.benchmark_run
              (scoring_function, scoring_version, cutoff_date, cohort_definition,
               n_ti_pairs, n_approved, n_failed,
               auc_roc, auc_roc_ci_lo, auc_roc_ci_hi, brier_score,
               recall_at_10pct, precision_at_10pct, rs_top_decile,
               calibration_ece, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING benchmark_run_id
        """, (scorer_name + "_timemachine", "v1", cutoff,
              f"ti_phase2plus_test_post_{cutoff.year}", len(y_test),
              int(y_test.sum()), int(len(y_test) - y_test.sum()),
              auc, auc_lo, auc_hi, brier, r10, p10, rs10, ece,
              f"Trained on pre-{cutoff} T-I pairs (n={len(train_rows)}), tested on post-{cutoff}"))
        run_id = cur.fetchone()[0]

        ranked_idx = np.argsort(-p_test)
        rank_map = {i: r + 1 for r, i in enumerate(ranked_idx)}
        rows_to_insert = []
        for i, (row, p, y) in enumerate(zip(test_rows, p_test, y_test)):
            tier = "high" if p >= 0.35 else ("medium" if p >= 0.18 else "low")
            rows_to_insert.append((run_id, row["target_id"], row["indication_id"],
                                  float(p), tier, rank_map[i],
                                  None, None, "medium", 20,
                                  bool(y), None, row.get("max_phase_reached"), row.get("n_programs"),
                                  None))
        execute_values(cur, """
            INSERT INTO preclin.benchmark_prediction
              (benchmark_run_id, target_id, indication_id, predicted_p_approval,
               predicted_tier, predicted_rank, top_supporting_dims, top_concerning_dims,
               score_confidence, n_features_used, y_approved, y_realization_date,
               y_highest_phase, y_n_programs, evidence_snapshot)
            VALUES %s
        """, rows_to_insert, page_size=1000)
        conn.commit()
    conn.close()
    print(f"  Stored as benchmark_run_id={run_id}")


if __name__ == "__main__":
    for cutoff in [date(2017, 1, 1), date(2019, 1, 1), date(2021, 1, 1)]:
        run_time_machine(cutoff, _ml.make_lgb, "lightgbm_v1")
        run_time_machine(cutoff, _ml.make_rf, "randomforest_v1")
