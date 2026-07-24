#!/usr/bin/env python3
"""
Generate data/genetics_dose_response.csv — approval rate binned by genetic strength.

Genetic strength is Melissa's OWN `genetic_only_v1` additive score, reproduced exactly
from benchmark/scorers_rule_based.py (scorer_genetic_only):
    ClinGen >=1        +0.6
    Mendelian >=5      +0.5   (>=1 -> +0.2)
    OT-genetic >=0.5   +0.5   (>=0.3 -> +0.3)
    OT-somatic >=0.3   +0.3
    Nelson tier        T4 +1.0 / T3 +0.7 / T2 +0.5 / T1 +0.3 / T0 -0.2  (when present)
Nelson tier is null for ~99% of pairs (a small curated batch), so in practice the score
runs off ClinGen / Mendelian / OT-genetic / OT-somatic, which are ~100% populated.

Cohort matches v_relative_success_clean: Phase 2+ target-indication pairs, non-placebo.

Usage:  DATABASE_URL='postgresql://...' python3 analyses/genetics_dose_response.py
Output: data/genetics_dose_response.csv  (tier, approval, lo, hi, n)  -> plotted by
        analyses/plot_predictive_power.py
"""
from __future__ import annotations
import os
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "genetics_dose_response.csv")

TI_POOL_SQL = """
SELECT ti.any_approved, tw.clingen_n_strong, tw.mendelian_n, tw.ot_genetic_max,
       tw.ot_somatic_score_max
FROM preclin.v_target_indication_program ti
JOIN preclin.v_target_evidence_wide tw ON tw.target_id = ti.target_id
WHERE ti.max_phase_reached >= 2 AND EXISTS (
    SELECT 1 FROM preclin.program p JOIN preclin.drug d ON d.drug_id = p.drug_id
    WHERE p.indication_id = ti.indication_id
      AND EXISTS (SELECT 1 FROM preclin.v_drug_target dt
                  WHERE dt.drug_id = p.drug_id AND dt.target_id = ti.target_id)
      AND d.is_placebo IS NOT TRUE)
"""


def genetic_only_v1_score(r) -> float:
    """Verbatim port of benchmark/scorers_rule_based.py::scorer_genetic_only (score only)."""
    s = 0.0
    cg = r["clingen_n_strong"]
    if pd.notna(cg) and cg >= 1:
        s += 0.6
    md = r["mendelian_n"]
    if pd.notna(md):
        s += 0.5 if md >= 5 else (0.2 if md >= 1 else 0.0)
    og = r["ot_genetic_max"]
    if pd.notna(og):
        s += 0.5 if og >= 0.5 else (0.3 if og >= 0.3 else 0.0)
    osm = r["ot_somatic_score_max"]
    if pd.notna(osm) and osm >= 0.3:
        s += 0.3
    return s


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("Set DATABASE_URL (Neon connection string; see db/README.md).")
    import psycopg2
    import warnings
    warnings.filterwarnings("ignore")
    with psycopg2.connect(url) as conn:
        df = pd.read_sql(TI_POOL_SQL, conn)

    df["gscore"] = df.apply(genetic_only_v1_score, axis=1)
    y = df["any_approved"].fillna(False).astype(bool).to_numpy()
    rng = np.random.default_rng(7)

    bins = [-0.01, 0.001, 0.95, 1.35, 3.1]
    labs = ["None\n(score 0)", "Weak\n(0.1–0.9)", "Moderate\n(1.0–1.3)", "Strong\n(≥1.4)"]
    df["b"] = pd.cut(df.gscore, bins=bins, labels=labs)
    rows = []
    for lab in labs:
        m = (df.b == lab).to_numpy()
        yy = y[m]
        p = yy.mean()
        boot = rng.binomial(len(yy), p, 3000) / len(yy)
        rows.append(dict(tier=lab, approval=round(100 * p, 1),
                         lo=round(100 * np.percentile(boot, 2.5), 1),
                         hi=round(100 * np.percentile(boot, 97.5), 1), n=int(len(yy))))
    out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"n={len(df)}  base approval {y.mean():.1%}")
    print(out.to_string(index=False))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
