"""Robust ML scorers — more regularization, monotonic constraints, calibration.

Key changes vs 13_ml_scorers.py:
- LightGBM: shallower trees, higher min_child_samples, monotonic constraints on
  known-directional features (genetics positive, essentiality negative).
- Isotonic calibration wrapper on all tree models.
- Trained + evaluated on STRICT outcome by default.
- Uses `y_strict` from v_target_indication_strict_outcome.

These changes should:
- Reduce LightGBM overfitting on time-machine.
- Improve calibration.
- Retain most of the ranking performance.
"""

import os
import sys
from datetime import date
import numpy as np
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from sklearn.model_selection import StratifiedKFold
from sklearn.calibration import CalibratedClassifierCV

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
_runner = import_module("11_benchmark_runner")
_ml = import_module("13_ml_scorers")

DB_URL = os.environ["DATABASE_URL"]

STRICT_COHORT_SQL = """
    SELECT s.target_id, s.indication_id,
      s.strict_approved_this_ti AS y_strict,
      s.first_trial_date, s.max_phase_reached,
      s.n_programs, s.n_sponsors,
      i.therapeutic_area, tw.*,
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


def load_strict():
    conn = psycopg2.connect(DB_URL)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(STRICT_COHORT_SQL)
        rows = cur.fetchall()
    conn.close()
    return list(rows)


# Monotonic constraints per feature (LightGBM convention: 1=increasing, -1=decreasing, 0=none)
# Positive direction: more of X → more likely approved
# Negative direction: more of X → less likely approved
MONO_CONSTRAINTS = {
    # Positive
    "mendelian_n": 1, "mendelian_n_dominant": 1, "mendelian_n_recessive": 1,
    "clingen_n_strong": 1,
    "ot_genetic_max": 1, "ot_somatic_score_max": 1,
    "family_approved_count": 1, "gene_approved_count": 1,
    # Negative — biology-driven risk
    "depmap_pan_essential": -1, "gnomad_pli": -1,
    # Rest unconstrained (let data speak)
}


def make_lgb_robust():
    if not HAS_LGB:
        return None
    mc = [MONO_CONSTRAINTS.get(name, 0) for name in _ml.FEATURE_NAMES]
    return lgb.LGBMClassifier(
        n_estimators=200, learning_rate=0.03,
        max_depth=4, num_leaves=15,
        min_child_samples=50, subsample=0.7, colsample_bytree=0.6,
        reg_alpha=1.0, reg_lambda=1.0,
        class_weight="balanced",
        monotone_constraints=mc, monotone_constraints_method="advanced",
        random_state=42, verbose=-1,
    )


def make_lgb_isotonic():
    """Robust LightGBM with post-hoc isotonic calibration."""
    if not HAS_LGB:
        return None
    return CalibratedClassifierCV(
        lgb.LGBMClassifier(
            n_estimators=200, learning_rate=0.03,
            max_depth=4, num_leaves=15,
            min_child_samples=50, subsample=0.7, colsample_bytree=0.6,
            reg_alpha=1.0, reg_lambda=1.0,
            class_weight="balanced", random_state=42, verbose=-1),
        method="isotonic", cv=3,
    )


def cv_predict_strict(model_ctor, X, y, n_splits=5):
    kf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    oof = np.zeros(len(y), dtype=np.float64)
    for train_idx, test_idx in kf.split(X, y):
        model = model_ctor()
        model.fit(X[train_idx], y[train_idx])
        oof[test_idx] = model.predict_proba(X[test_idx])[:, 1]
    return oof


def eval_and_store(scorer_name, oof, y, rows, cohort_def, notes):
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
        """, (scorer_name, "v3_robust", cohort_def, len(y),
              int(y.sum()), int(len(y) - y.sum()),
              auc, auc_lo, auc_hi, brier, r10, p10, rs10, ece, notes))
        conn.commit()
    conn.close()


def main():
    rows = load_strict()
    X = np.stack([_ml.row_to_feature_vector(r) for r in rows])
    y = np.array([1 if r["y_strict"] else 0 for r in rows], dtype=np.int64)
    print(f"Strict cohort: n={len(rows)}, pos_rate={y.mean():.4f}")

    if HAS_LGB:
        print("\n== lightgbm_robust_strict_v1 (regularized + monotonic) ==")
        oof = cv_predict_strict(make_lgb_robust, X, y)
        eval_and_store("lightgbm_robust_strict_v1", oof, y, rows,
                       "ti_phase2plus_strict", "Regularized LightGBM + monotonic constraints")

        print("\n== lightgbm_robust_iso_strict_v1 (regularized + isotonic calibration) ==")
        oof = cv_predict_strict(make_lgb_isotonic, X, y)
        eval_and_store("lightgbm_robust_iso_strict_v1", oof, y, rows,
                       "ti_phase2plus_strict", "Regularized LightGBM + isotonic calibration")


if __name__ == "__main__":
    main()
