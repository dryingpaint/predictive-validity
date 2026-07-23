"""Template for wiring an EXTERNAL scoring model into the benchmark.

Use this to evaluate:
- Pheiron RS-style composite predictions
- Insilico PandaOmics scores (if they publish them)
- Your own trained ML model
- Any other target-scoring approach

Two integration paths:

    Path 1 (in-process): implement the scorer as a Python callable
      matching the interface below, register it, then run
      `python3 11_benchmark_runner.py <name>`.

    Path 2 (score-first): produce scores externally and INSERT rows
      into preclin.benchmark_prediction directly. Metrics get computed
      by calling `compute_metrics_from_predictions(run_id)`.

Path 2 is best for models we don't have code for.
"""

import os
import sys
from typing import Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
_scorers = import_module("scorers_rule_based")
_runner = import_module("runner")


# ============================================================
# Path 1: implement a Python scorer with the standard interface
# ============================================================

def my_external_scorer(evidence: Dict, context: Dict) -> Dict:
    """
    Args:
      evidence: nested dict of A_genetics, B_mechanistic, C_cell, D_animal,
                E_pd, H_safety, I_landscape. Values may be None if missing.
      context:  {target_symbol, indication_name, therapeutic_area,
                 n_programs, n_drugs, highest_phase}

    Returns:
      {
        'predicted_p_approval': float in [0, 1],
        'predicted_tier': 'low' | 'medium' | 'high',
        'top_supporting_dims': [str] (human-readable),
        'top_concerning_dims': [str],
        'score_confidence': 'low' | 'medium' | 'high',
        'n_features_used': int,
      }
    """
    # Example: hardcoded rule (replace with actual model call)
    p = 0.25
    if evidence.get("A_genetics", {}).get("mendelian_n", 0) or 0 >= 5:
        p += 0.10
    if evidence.get("C_cell", {}).get("depmap_pan_essential"):
        p = 0.05  # essentiality is a killer
    return {
        "predicted_p_approval": p,
        "predicted_tier": "high" if p >= 0.35 else ("medium" if p >= 0.18 else "low"),
        "top_supporting_dims": [],
        "top_concerning_dims": [],
        "score_confidence": "medium",
        "n_features_used": 5,
    }


# Register
_scorers.register_scorer("my_external_scorer_v1", my_external_scorer, "v1")


# ============================================================
# Path 2: score externally, insert rows directly
# ============================================================

def wire_external_scores(scorer_name: str, scores_csv: str, version: str = "v1"):
    """
    Load a CSV of (target_id, indication_id, predicted_p_approval) rows,
    create a benchmark_run, insert predictions with ground truth,
    compute metrics.

    Expected CSV columns:
      target_id, indication_id, predicted_p_approval,
      [top_supporting_dims, top_concerning_dims, n_features_used]

    Args:
      scorer_name: identifier for this external scorer
      scores_csv:  path to CSV with above columns
    """
    import csv, psycopg2
    from psycopg2.extras import execute_values, Json, RealDictCursor

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Load external scores
        preds = {}
        with open(scores_csv) as f:
            for r in csv.DictReader(f):
                preds[(int(r["target_id"]), int(r["indication_id"]))] = float(r["predicted_p_approval"])

        # Load ground truth for the SAME T-I pairs
        cohort = _runner.load_cohort(conn, min_phase=2)
        matched = [row for row in cohort
                   if (row["target_id"], row["indication_id"]) in preds]
        print(f"External scorer {scorer_name}: {len(matched)}/{len(preds)} matched to cohort")

        # Predict + evaluate
        y_list = [bool(row["any_approved"]) for row in matched]
        p_list = [preds[(row["target_id"], row["indication_id"])] for row in matched]

        # Metrics
        auc, auc_lo, auc_hi = _runner.bootstrap_metric(y_list, p_list, _runner.auc_roc)
        brier, brier_lo, brier_hi = _runner.bootstrap_metric(y_list, p_list, _runner.brier_score)
        r10 = _runner.recall_at_top_k(y_list, p_list, 0.10)
        p10 = _runner.precision_at_top_k(y_list, p_list, 0.10)
        rs10 = _runner.rs_by_top_decile(y_list, p_list)
        rs25 = _runner.rs_by_top_quartile(y_list, p_list)
        ece = _runner.calibration_ece(y_list, p_list)

        cur.execute("""
            INSERT INTO preclin.benchmark_run
              (scoring_function, scoring_version, cohort_definition,
               n_ti_pairs, n_approved, n_failed,
               auc_roc, auc_roc_ci_lo, auc_roc_ci_hi,
               brier_score, brier_score_ci_lo, brier_score_ci_hi,
               recall_at_10pct, precision_at_10pct, rs_top_decile, rs_top_quartile,
               calibration_ece, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING benchmark_run_id
        """, (scorer_name, version, "ti_phase2plus", len(matched),
              sum(y_list), len(y_list) - sum(y_list),
              auc, auc_lo, auc_hi, brier, brier_lo, brier_hi,
              r10, p10, rs10, rs25, ece,
              f"external, source={scores_csv}"))
        run_id = cur.fetchone()[0]

        ranked = sorted(zip(matched, p_list, y_list), key=lambda t: t[1], reverse=True)
        rows = [(run_id, row["target_id"], row["indication_id"],
                 float(p), None, i+1, None, None, "external", 1,
                 bool(y), None, row["max_phase_reached"], row["n_programs"], None)
                for i, (row, p, y) in enumerate(ranked)]
        execute_values(cur, """
            INSERT INTO preclin.benchmark_prediction
              (benchmark_run_id, target_id, indication_id,
               predicted_p_approval, predicted_tier, predicted_rank,
               top_supporting_dims, top_concerning_dims, score_confidence, n_features_used,
               y_approved, y_realization_date, y_highest_phase, y_n_programs,
               evidence_snapshot)
            VALUES %s
        """, rows, page_size=1000)
        conn.commit()
        print(f"External benchmark_run_id={run_id}, AUC={auc:.3f}")
    conn.close()


if __name__ == "__main__":
    # Example: run the template external scorer via Path 1
    _runner.run_benchmark("my_external_scorer_v1")
    # Example Path 2:
    # wire_external_scores("pheiron_rs_composite", "/tmp/pheiron_scores.csv")
