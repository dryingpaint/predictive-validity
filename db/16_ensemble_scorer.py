"""Ensemble scorer — stack the best scorers by held-out AUC weight.

Reads predictions from preclin.benchmark_prediction across specified scorers,
combines them by softmax-weighted average of probabilities where weights are
proportional to log(AUC / (1 - AUC)) — i.e., inverse-variance ensemble.

Only uses predictions from scorers that share the same cohort (2,611 T-I pairs).
"""

import os
import sys
import math
import numpy as np
import psycopg2
from psycopg2.extras import execute_values, Json, RealDictCursor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
_runner = import_module("11_benchmark_runner")

DB_URL = os.environ["DATABASE_URL"]


DEFAULT_ENSEMBLE_MEMBERS = [
    "lightgbm_v1",
    "randomforest_v1",
    "rs_composite_calibrated_v1",
]


def load_predictions(conn, scorer_names):
    """Return {scorer_name: {(target_id, indication_id): (p, y)}}"""
    out = {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Use latest run per scorer_name
        cur.execute("""
            SELECT scoring_function, MAX(benchmark_run_id) AS run_id
            FROM preclin.benchmark_run
            WHERE scoring_function = ANY(%s)
              AND cohort_definition = 'ti_phase2plus'
            GROUP BY scoring_function
        """, (scorer_names,))
        runs = {r["scoring_function"]: r["run_id"] for r in cur.fetchall()}
        for name, run_id in runs.items():
            cur.execute("""
                SELECT target_id, indication_id, predicted_p_approval, y_approved
                FROM preclin.benchmark_prediction WHERE benchmark_run_id = %s
            """, (run_id,))
            out[name] = {(r["target_id"], r["indication_id"]):
                         (float(r["predicted_p_approval"]), bool(r["y_approved"]))
                         for r in cur.fetchall()}
    return out


def load_scorer_aucs(conn, scorer_names):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT DISTINCT ON (scoring_function)
              scoring_function, auc_roc
            FROM preclin.benchmark_run
            WHERE scoring_function = ANY(%s)
              AND cohort_definition = 'ti_phase2plus'
            ORDER BY scoring_function, benchmark_run_id DESC
        """, (scorer_names,))
        return {r["scoring_function"]: float(r["auc_roc"]) for r in cur.fetchall()}


def main(members=DEFAULT_ENSEMBLE_MEMBERS):
    conn = psycopg2.connect(DB_URL)
    print("Loading member predictions ...")
    preds_by_scorer = load_predictions(conn, members)
    aucs = load_scorer_aucs(conn, members)
    print(f"  Members: {list(preds_by_scorer.keys())}")
    print(f"  AUCs: {aucs}")

    # Intersection of T-I keys (all members must have a prediction)
    common = set.intersection(*[set(d.keys()) for d in preds_by_scorer.values()])
    keys = sorted(common)
    print(f"  Common T-I pairs: {len(keys)}")

    # Weight ∝ log-odds of AUC
    def logodds(auc):
        auc = max(0.51, min(0.99, auc))  # avoid extreme
        return math.log(auc / (1 - auc))
    raw_w = {name: logodds(aucs[name]) for name in preds_by_scorer}
    total = sum(raw_w.values())
    weights = {name: w / total for name, w in raw_w.items()}
    print("  Weights:")
    for name, w in weights.items():
        print(f"    {name:32} w={w:.3f} (AUC={aucs[name]:.3f})")

    # Ensemble average
    ensemble_p = []
    y_list = []
    for k in keys:
        # Use first scorer's y (all should agree)
        _, y = list(preds_by_scorer.values())[0][k]
        # Weighted mean of p
        p = sum(weights[name] * preds_by_scorer[name][k][0] for name in preds_by_scorer)
        ensemble_p.append(p)
        y_list.append(y)

    # Metrics
    auc, auc_lo, auc_hi = _runner.bootstrap_metric(y_list, ensemble_p, _runner.auc_roc)
    brier = _runner.brier_score(y_list, ensemble_p)
    r10 = _runner.recall_at_top_k(y_list, ensemble_p, 0.10)
    p10 = _runner.precision_at_top_k(y_list, ensemble_p, 0.10)
    rs10 = _runner.rs_by_top_decile(y_list, ensemble_p)
    ece = _runner.calibration_ece(y_list, ensemble_p)

    print(f"\n== Ensemble ({len(members)} members) ==")
    print(f"AUC = {auc:.3f} [{auc_lo:.3f}, {auc_hi:.3f}]")
    print(f"Brier = {brier:.3f}, R@10% = {r10:.3f}, P@10% = {p10:.3f}")
    print(f"RS(top 10%) = {rs10:.2f}, ECE = {ece:.3f}")

    # Store
    n_approved = sum(y_list)
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
        """, ("ensemble_top3_v1", "v1", "ti_phase2plus", len(y_list),
              n_approved, len(y_list) - n_approved,
              auc, auc_lo, auc_hi, brier, r10, p10, rs10, ece,
              f"AUC-weighted ensemble: {', '.join(members)}"))
        run_id = cur.fetchone()[0]

        ranked = sorted(zip(keys, ensemble_p, y_list), key=lambda t: t[1], reverse=True)
        rank_map = {(k[0], k[1]): r + 1 for r, (k, _, _) in enumerate(ranked)}

        rows = []
        for (tid, iid), p, y in zip(keys, ensemble_p, y_list):
            tier = "high" if p >= 0.35 else ("medium" if p >= 0.18 else "low")
            rows.append((run_id, tid, iid, float(p), tier, rank_map[(tid, iid)],
                         None, None, "high", len(members),
                         bool(y), None, None, None, None))
        execute_values(cur, """
            INSERT INTO preclin.benchmark_prediction
              (benchmark_run_id, target_id, indication_id, predicted_p_approval,
               predicted_tier, predicted_rank, top_supporting_dims, top_concerning_dims,
               score_confidence, n_features_used, y_approved, y_realization_date,
               y_highest_phase, y_n_programs, evidence_snapshot)
            VALUES %s
        """, rows, page_size=1000)
        conn.commit()
    conn.close()
    print(f"Stored as benchmark_run_id={run_id}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        members = sys.argv[1].split(",")
    else:
        members = DEFAULT_ENSEMBLE_MEMBERS
    main(members)
