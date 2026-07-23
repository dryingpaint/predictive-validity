"""LLM-agent scorer: Sonnet reads full evidence dossier, predicts P(approval).

Novel angle vs ML: LLM applies domain knowledge + can flag reasoning errors in
the evidence itself. Slower and costlier (~$0.02/prediction) but interpretable.

To keep cost bounded, we sample a stratified subset of T-I pairs (default 400).
For full production, run over all 2,611 T-I pairs (~$60, ~2 hours).
"""

import json
import os
import re
import subprocess
import sys
import time
from typing import Dict, List

import numpy as np
import psycopg2
from psycopg2.extras import execute_values, Json, RealDictCursor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
_scorers = import_module("10_benchmark_scorers")
_runner = import_module("11_benchmark_runner")

DB_URL = os.environ["DATABASE_URL"]


def compact_evidence(evidence: dict, context: dict) -> str:
    """Turn evidence into a concise Markdown block for Sonnet."""
    lines = [
        f"Target: **{context.get('target_symbol')}**  |  "
        f"Indication: **{context.get('indication_name')}**  |  "
        f"Therapeutic area: {context.get('therapeutic_area', 'unknown')}",
    ]
    for cat, dims in evidence.items():
        vals = {k: v for k, v in dims.items() if v is not None}
        if not vals:
            continue
        lines.append(f"- **{cat}**: " + ", ".join(f"{k}={v}" for k, v in vals.items()))
    return "\n".join(lines)


PROMPT_TEMPLATE = """You are evaluating whether a drug program targeting a specific
(target × indication) pair will lead to an FDA-approved drug.

Below is all publicly known evidence about this target and indication (before
clinical outcome). Assess the probability that ANY drug program on this
target-indication will succeed and yield an approval (US or ex-US).

**Base rate:** in our cohort of Phase 2+ target-indication pairs, ~28% get
approved. Use this as your anchor.

**Evidence:**
{evidence_block}

**Instructions:**
- Weight biology-driven signals (target genetics, tissue relevance, safety
  intolerance) most.
- Downweight evidence that reflects post-hoc program success (family precedent,
  DGIdb precedent) — these correlate with approval but are largely confounders.
- If DepMap pan-essential, expect very low approval odds.
- Return a single JSON object, no other text:

{{"p_approval": 0.XX, "confidence": "high|medium|low",
  "top_supporting": ["dim1", "dim2"], "top_concerning": ["dim3"],
  "one_sentence_rationale": "..."}}
"""


def sonnet_score(evidence: dict, context: dict) -> dict:
    prompt = PROMPT_TEMPLATE.format(evidence_block=compact_evidence(evidence, context))
    try:
        r = subprocess.run(
            ["claude", "--print", "--model", "sonnet", "--output-format", "json"],
            input=prompt, capture_output=True, text=True, timeout=90,
        )
        outer = json.loads(r.stdout)
        raw = outer.get("result", "")
        m = re.search(r"\{[^{}]*\"p_approval\"[^{}]*\}", raw) or re.search(r"\{.*?\}", raw, re.DOTALL)
        if m:
            parsed = json.loads(m.group(0))
            parsed["_cost"] = outer.get("total_cost_usd", 0)
            return parsed
    except Exception as e:
        return {"error": str(e)[:100]}
    return {"error": "no_json"}


def _tier_from_p(p):
    return "high" if p >= 0.35 else ("medium" if p >= 0.18 else "low")


def sample_stratified(rows: List[dict], n: int, seed: int = 42) -> List[int]:
    """Stratified sample balancing approved and failed T-I pairs."""
    rng = np.random.default_rng(seed)
    approved = [i for i, r in enumerate(rows) if r.get("any_approved")]
    failed = [i for i, r in enumerate(rows) if not r.get("any_approved")]
    n_appr = min(len(approved), n // 2)
    n_fail = min(len(failed), n - n_appr)
    if n_appr < n // 2:
        n_fail = min(len(failed), n - n_appr)
    idx = np.concatenate([
        rng.choice(approved, size=n_appr, replace=False),
        rng.choice(failed, size=n_fail, replace=False),
    ])
    rng.shuffle(idx)
    return idx.tolist()


def main(limit: int = 400):
    conn = psycopg2.connect(DB_URL)
    print("Loading cohort ...")
    rows = _runner.load_cohort(conn, min_phase=2)
    print(f"  Full cohort n = {len(rows)}")
    print(f"  Sampling {limit} T-I pairs (stratified 50/50)")

    idx = sample_stratified(rows, limit)
    sampled = [rows[i] for i in idx]

    predictions = []
    total_cost = 0.0
    for i, row in enumerate(sampled):
        evidence, context, y = _runner.row_to_evidence_context(row)
        result = sonnet_score(evidence, context)
        if "error" in result:
            p = 0.28  # fall back to base rate
        else:
            try:
                p = float(result.get("p_approval", 0.28))
                p = max(0.0, min(1.0, p))
            except (TypeError, ValueError):
                p = 0.28
        total_cost += result.get("_cost", 0)
        predictions.append({
            "target_id": row["target_id"],
            "indication_id": row["indication_id"],
            "predicted_p_approval": p,
            "predicted_tier": _tier_from_p(p),
            "top_supporting": result.get("top_supporting", []),
            "top_concerning": result.get("top_concerning", []),
            "y_approved": bool(y),
            "y_highest_phase": row.get("max_phase_reached"),
            "y_n_programs": row.get("n_programs"),
            "rationale": (result.get("one_sentence_rationale") or "")[:400],
        })
        if (i + 1) % 25 == 0:
            print(f"  [{i+1}/{len(sampled)}] cost ${total_cost:.2f}")

    predictions.sort(key=lambda r: r["predicted_p_approval"], reverse=True)
    for r, p in enumerate(predictions):
        p["predicted_rank"] = r + 1

    y_list = [p["y_approved"] for p in predictions]
    p_list = [p["predicted_p_approval"] for p in predictions]
    n_approved = sum(y_list)

    print(f"\n== Sonnet Agent Scorer — Results ==")
    print(f"n_evaluated = {len(y_list)}, n_approved = {n_approved}")
    auc, auc_lo, auc_hi = _runner.bootstrap_metric(y_list, p_list, _runner.auc_roc)
    brier = _runner.brier_score(y_list, p_list)
    r10 = _runner.recall_at_top_k(y_list, p_list, 0.10)
    p10 = _runner.precision_at_top_k(y_list, p_list, 0.10)
    rs10 = _runner.rs_by_top_decile(y_list, p_list)
    ece = _runner.calibration_ece(y_list, p_list)
    print(f"AUC = {auc:.3f} [{auc_lo:.3f}, {auc_hi:.3f}]")
    print(f"Brier = {brier:.3f}, R@10% = {r10:.3f}, P@10% = {p10:.3f}")
    print(f"RS(top 10%) = {rs10:.2f}, ECE = {ece:.3f}")
    print(f"Total LLM cost: ${total_cost:.2f}")

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
        """, ("sonnet_agent_v1", "v1", "ti_phase2plus_sample400", len(y_list),
              n_approved, len(y_list) - n_approved,
              auc, auc_lo, auc_hi, brier, r10, p10, rs10, ece,
              f"Sonnet agent scorer, ${total_cost:.2f} total cost"))
        run_id = cur.fetchone()[0]
        rows = [(run_id, p["target_id"], p["indication_id"],
                 float(p["predicted_p_approval"]), p["predicted_tier"],
                 p["predicted_rank"], p["top_supporting"], p["top_concerning"],
                 "medium", 20,
                 p["y_approved"], None, p["y_highest_phase"], p["y_n_programs"],
                 Json({"rationale": p["rationale"]}))
                for p in predictions]
        execute_values(cur, """
            INSERT INTO preclin.benchmark_prediction
              (benchmark_run_id, target_id, indication_id, predicted_p_approval,
               predicted_tier, predicted_rank, top_supporting_dims, top_concerning_dims,
               score_confidence, n_features_used, y_approved, y_realization_date,
               y_highest_phase, y_n_programs, evidence_snapshot)
            VALUES %s
        """, rows, page_size=500)
        conn.commit()
    conn.close()
    print(f"Stored as benchmark_run_id={run_id}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    main(n)
