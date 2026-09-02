"""Reproducing diagnostic for the nelson_tier leakage documented in
NELSON_TIER_LEAKAGE.md.

Shows two things:
  1. The training-cohort approval rate by nelson_tier — every populated tier
     (T0 included) sits at ~90-100% vs. ~2.5% for the null majority, i.e.
     "has a tier at all" is a near-perfect known-drug flag.
  2. That assigning ANY tier to a novel target (SIK3, fully credited with its
     real genetics) inflates the predicted probability from ~0.05-0.31 to
     ~0.6-0.99 across models — the leak, not the biology.

Read-only against the DB. Run:  python3 analyses/nelson_tier_leakage_demo.py
"""
import os
import sys
from collections import Counter

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "benchmark"))
from importlib import import_module
_ml = import_module("scorers_ml")
_ens = import_module("scorers_ensemble")

DB_URL = os.environ["DATABASE_URL"]


def approval_rate_by_tier(rows):
    y = np.array([1 if r.get("y_strict") else 0 for r in rows])
    tiers = [r.get("nelson_tier") for r in rows]
    print("\n(1) Training-cohort approval rate by nelson_tier")
    print(f"    {'tier':8} {'n':>6} {'approval_rate':>14}")
    for t in [None, "T0", "T1", "T2", "T3", "T4"]:
        mask = np.array([tt == t for tt in tiers])
        if mask.sum():
            print(f"    {str(t):8} {int(mask.sum()):6d} {y[mask].mean():14.3f}")
    print("    -> every populated tier (T0 included) is a near-perfect known-drug flag.")


def novel_target_impact(rows, conn):
    """SIK3 x Insomnia, credited with its real curated genetics, scored with
    nelson_tier unset vs. set to T0, across models."""
    Xtr = np.stack([_ml.row_to_feature_vector(r) for r in rows])
    ytr = np.array([1 if r.get("y_strict") else 0 for r in rows], dtype=np.int64)
    Xtr_log = _ens.log_transform_features(Xtr, _ml.FEATURE_NAMES)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM preclin.v_target_evidence_wide WHERE target_id=5743")  # SIK3
        wide = dict(cur.fetchone())
        cur.execute("""SELECT genetic_score, animal_model_score, is_mendelian
                       FROM public.target_evidence te JOIN public.diseases d ON d.id=te.disease_id
                       WHERE te.target_id=5743 AND d.name='Insomnia'""")
        ev = cur.fetchone()

    row = dict(wide)
    row["therapeutic_area"] = "other"
    row["ot_genetic_max"] = ev["genetic_score"] if ev else 0.9
    row["ot_animal_model_max"] = ev["animal_model_score"] if ev else 0.75
    row["ot_is_mendelian_any"] = ev["is_mendelian"] if ev else True
    for k in ["mendelian_n", "gwas_n_sig", "clingen_n_strong"]:
        row[k] = 0

    def vec(tier):
        r = dict(row); r["nelson_tier"] = tier
        return _ens.log_transform_features(_ml.row_to_feature_vector(r).reshape(1, -1), _ml.FEATURE_NAMES)

    x_unset, x_t0 = vec(None), vec("T0")
    print("\n(2) Novel target (SIK3 x Insomnia, genetics credited) — impact of setting a tier")
    print(f"    {'model':28} {'tier unset':>11} {'tier=T0':>9}")
    for name, ctor in [("logreg_l2", _ens.make_logreg_l2),
                       ("logreg_calibrated", _ml.make_logreg),
                       ("randomforest", _ml.make_rf)]:
        m = ctor(); m.fit(Xtr_log, ytr)
        p0 = float(m.predict_proba(x_unset)[0, 1])
        p1 = float(m.predict_proba(x_t0)[0, 1])
        print(f"    {name:28} {p0:11.4f} {p1:9.4f}")
    print("    -> setting T0 (the 'conservative' choice) is what inflates the score.")


def main():
    conn = psycopg2.connect(DB_URL)
    rows = _ml.load_strict()
    print(f"Strict Phase 2+ cohort: n={len(rows)}, "
          f"tier distribution: {dict(Counter(r.get('nelson_tier') for r in rows))}")
    approval_rate_by_tier(rows)
    novel_target_impact(rows, conn)
    conn.close()


if __name__ == "__main__":
    main()
