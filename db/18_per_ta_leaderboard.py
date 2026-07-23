"""Per-therapeutic-area leaderboard.

Trains LightGBM per TA. Some TAs are harder to predict than others; some
evidence types matter more in some TAs (e.g. cell essentiality dominates
in oncology, genetics dominates in rare disease).
"""

import os
import sys
from collections import defaultdict

import numpy as np
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
_runner = import_module("11_benchmark_runner")
_ml = import_module("13_ml_scorers")

DB_URL = os.environ["DATABASE_URL"]


def run_per_ta():
    conn = psycopg2.connect(DB_URL)
    rows = _runner.load_cohort(conn, min_phase=2)

    # Group by TA
    by_ta = defaultdict(list)
    for r in rows:
        ta = r.get("therapeutic_area") or "other"
        by_ta[ta].append(r)

    print("Per-TA cohort sizes:")
    for ta in sorted(by_ta):
        n = len(by_ta[ta])
        pos = sum(1 for r in by_ta[ta] if r.get("any_approved"))
        print(f"  {ta:14} n={n:5} approved={pos:4} ({100*pos/n:.1f}%)")

    print("\nPer-TA LightGBM (5-fold CV where n>=100):")
    results = []
    for ta in sorted(by_ta):
        sub = by_ta[ta]
        if len(sub) < 100:
            continue
        X = np.stack([_ml.row_to_feature_vector(r) for r in sub])
        y = np.array([1 if r.get("any_approved") else 0 for r in sub], dtype=np.int64)
        if y.sum() < 10 or (len(y) - y.sum()) < 10:
            print(f"  {ta:14} SKIP (needs both classes)")
            continue

        try:
            oof, fold_aucs = _ml.cv_predict(_ml.make_lgb, X, y, n_splits=min(5, y.sum()))
        except Exception as e:
            print(f"  {ta:14} FAIL: {e}")
            continue

        auc, auc_lo, auc_hi = _runner.bootstrap_metric(y.tolist(), oof.tolist(), _runner.auc_roc)
        rs10 = _runner.rs_by_top_decile(y.tolist(), oof.tolist())
        print(f"  {ta:14} n={len(sub):5} approved={y.sum():4}  AUC={auc:.3f} [{auc_lo:.3f}, {auc_hi:.3f}]  RS(top10%)={rs10:.2f}")

        results.append({
            "ta": ta, "n": len(sub), "n_approved": int(y.sum()),
            "auc": auc, "auc_lo": auc_lo, "auc_hi": auc_hi, "rs10": rs10,
        })

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO preclin.benchmark_run
                  (scoring_function, scoring_version, cohort_definition,
                   n_ti_pairs, n_approved, n_failed,
                   auc_roc, auc_roc_ci_lo, auc_roc_ci_hi,
                   rs_top_decile, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (f"lightgbm_ta_{ta}_v1", "v1", f"ti_phase2plus_ta_{ta}",
                  len(sub), int(y.sum()), int(len(y) - y.sum()),
                  auc, auc_lo, auc_hi, rs10,
                  f"Per-TA LightGBM 5-fold CV OOF, TA={ta}"))
        conn.commit()

    print("\nSummary (sorted by AUC):")
    for r in sorted(results, key=lambda x: -x["auc"]):
        print(f"  {r['ta']:14} AUC={r['auc']:.3f}  n={r['n']:5}  RS10={r['rs10']:.2f}")
    conn.close()


if __name__ == "__main__":
    run_per_ta()
