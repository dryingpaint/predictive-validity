"""Leave-one-category-out ablation on STRICT outcome.

Using LogReg (the top performer on strict) instead of LightGBM.
"""

import os
import sys
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'benchmark'))
from importlib import import_module
_runner = import_module("runner")
_ml = import_module("scorers_ml")
_robust = import_module("scorers_ml")
_stack = import_module("scorers_ensemble")
_ablate = import_module("ablation")

DB_URL = os.environ["DATABASE_URL"]


def main():
    rows = _robust.load_strict()
    X = np.stack([_ml.row_to_feature_vector(r) for r in rows])
    y = np.array([1 if r["y_strict"] else 0 for r in rows], dtype=np.int64)
    X_log = _stack.log_transform_features(X, _ml.FEATURE_NAMES)
    print(f"Cohort: {len(rows)}, positive: {y.mean():.4f}")

    # Full model
    oof_full = _robust.cv_predict_strict(_stack.make_logreg_l2, X_log, y, n_splits=5)
    auc_full = _runner.auc_roc(y.tolist(), oof_full.tolist())
    print(f"\nFull LogReg model AUC (strict): {auc_full:.3f}")

    categories = ["A_genetics", "B_mechanistic", "C_cell", "D_animal",
                  "E_pd", "H_safety", "I_landscape", "context"]

    print("\nLeave-one-category-out (LogReg, strict):")
    print(f"{'Category':<16} {'AUC':<8} {'ΔAUC':<10}")
    print("-" * 40)

    results = []
    for cat in categories:
        X_ab = X_log.copy()
        for i, name in enumerate(_ml.FEATURE_NAMES):
            cat_check = _ablate.CATEGORY_MAP.get(name)
            if name.startswith("nelson_"):
                cat_check = "A_genetics"
            elif name.startswith("ta_"):
                cat_check = "context"
            if cat_check == cat:
                X_ab[:, i] = np.nan
        oof_ab = _robust.cv_predict_strict(_stack.make_logreg_l2, X_ab, y)
        auc_ab = _runner.auc_roc(y.tolist(), oof_ab.tolist())
        delta = auc_ab - auc_full
        print(f"{cat:<16} {auc_ab:.3f}   {delta:+.4f}")
        results.append((cat, auc_ab, delta))

        # Store
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO preclin.benchmark_run
                  (scoring_function, scoring_version, cohort_definition,
                   n_ti_pairs, n_approved, n_failed, auc_roc, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (f"logreg_strict_ablate_no_{cat}", "v3_strict",
                  "ti_phase2plus_strict", len(rows), int(y.sum()),
                  int(len(y) - y.sum()), auc_ab,
                  f"Ablate {cat}, strict outcome, LogReg. Full AUC={auc_full:.3f}, delta={delta:+.4f}"))
            conn.commit()
        conn.close()

    print("\nSorted by AUC drop (most load-bearing first):")
    for cat, auc, delta in sorted(results, key=lambda x: x[2]):
        print(f"  {cat:<16} ΔAUC={delta:+.4f}")


if __name__ == "__main__":
    main()
