"""Robust time-machine v2 — features are time-cutoff-aware where possible.

Key fix vs 17_time_machine.py:
- family_approved_count and gene_approved_count are now computed AS OF the T-I's
  first_trial_date (via v_target_family_precedent_by_year), not today.

Other features (Nelson tier, gnomAD, ClinGen, Mendelian, GWAS, DepMap, IMPC, GO,
Reactome) are approximately stable over 5-10 years — most gnomAD data is from
v2/v4 releases (2019-2024), DepMap is continuously updated but composition-stable,
IMPC KO data slowly grows. Using current values for these is approximation.

We ALSO run a stricter variant: drop family/gene precedent entirely.

Reports both variants side-by-side.
"""

import os
import sys
from datetime import date

import numpy as np
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
_runner = import_module("11_benchmark_runner")
_ml = import_module("13_ml_scorers")

DB_URL = os.environ["DATABASE_URL"]


TIME_COHORT_SQL_V2 = """
    SELECT
      ti.target_id, ti.indication_id, ti.any_approved,
      ti.first_trial_date, ti.last_trial_date, ti.max_phase_reached,
      ti.n_programs, ti.n_drugs, ti.n_sponsors,
      t.symbol AS target_symbol,
      i.display_name AS indication_name, i.therapeutic_area,
      tw.*,
      -- Nelson tier
      (SELECT value_text FROM preclin.evidence_score
        WHERE subject_type='target_indication' AND subject_id = ti.target_id
          AND subject_id2 = ti.indication_id AND dimension = 'nelson_tier'
        LIMIT 1) AS nelson_tier,
      -- Time-cutoff family precedent: approvals BEFORE first_trial_date
      COALESCE(fp.family_approved_before_year, 0) AS family_approved_before,
      COALESCE(fp.gene_approved_before_year, 0) AS gene_approved_before
    FROM preclin.v_target_indication_program ti
    JOIN public.targets t ON t.id = ti.target_id
    JOIN preclin.indication i ON i.indication_id = ti.indication_id
    JOIN preclin.v_target_evidence_wide tw ON tw.target_id = ti.target_id
    LEFT JOIN preclin.v_target_family_precedent_by_year fp
      ON fp.target_id = ti.target_id
      AND fp.year = EXTRACT(YEAR FROM ti.first_trial_date)
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


def load_time_cohort_v2():
    conn = psycopg2.connect(DB_URL)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(TIME_COHORT_SQL_V2)
        rows = cur.fetchall()
    conn.close()
    return list(rows)


def row_to_features_v2(row, drop_landscape=False):
    """Feature vector variant — replaces family/gene counts with time-cutoff versions."""
    feats = []
    for f in _ml.NUMERIC_FEATURES:
        if f == "family_approved_count":
            v = row.get("family_approved_before")
        elif f == "gene_approved_count":
            v = row.get("gene_approved_before")
        else:
            v = row.get(f)
        if v is None:
            feats.append(np.nan)
        else:
            try:
                feats.append(float(v))
            except (TypeError, ValueError):
                feats.append(np.nan)
    for f in _ml.BOOL_FEATURES:
        v = row.get(f)
        if v is None:
            feats.append(np.nan)
        else:
            feats.append(1.0 if v else 0.0)
    # Nelson tier one-hot
    tier = row.get("nelson_tier")
    for t in _ml.NELSON_TIERS:
        feats.append(1.0 if tier == t else 0.0)
    # TA one-hot
    ta = row.get("therapeutic_area") or "other"
    for a in _ml.THERAPEUTIC_AREAS:
        feats.append(1.0 if ta == a else 0.0)

    arr = np.array(feats, dtype=np.float64)
    if drop_landscape:
        # Mask I_landscape features (family_approved_count, gene_approved_count,
        # n_causal_diseases, n_suggestive_diseases, n_dgidb_drugs)
        landscape_idx = [_ml.FEATURE_NAMES.index(f)
                         for f in ["family_approved_count", "gene_approved_count",
                                   "n_causal_diseases", "n_suggestive_diseases",
                                   "n_dgidb_drugs"]
                         if f in _ml.FEATURE_NAMES]
        arr[landscape_idx] = np.nan
    return arr


def run(cutoff: date, variant: str = "time_cutoff_precedent"):
    """variant: 'time_cutoff_precedent' | 'drop_landscape'"""
    print(f"\n== Time-Machine v2: cutoff={cutoff}, variant={variant} ==")
    rows = load_time_cohort_v2()

    train_rows = [r for r in rows if r["first_trial_date"] and r["first_trial_date"] < cutoff]
    test_rows  = [r for r in rows if r["first_trial_date"] and r["first_trial_date"] >= cutoff]
    print(f"  train: {len(train_rows)}, test: {len(test_rows)}")

    drop_landscape = (variant == "drop_landscape")
    X_train = np.stack([row_to_features_v2(r, drop_landscape) for r in train_rows])
    y_train = np.array([1 if r["any_approved"] else 0 for r in train_rows], dtype=np.int64)
    X_test  = np.stack([row_to_features_v2(r, drop_landscape) for r in test_rows])
    y_test  = np.array([1 if r["any_approved"] else 0 for r in test_rows], dtype=np.int64)

    model = _ml.make_lgb()
    model.fit(X_train, y_train)
    p_test = model.predict_proba(X_test)[:, 1]

    auc, auc_lo, auc_hi = _runner.bootstrap_metric(y_test.tolist(), p_test.tolist(), _runner.auc_roc)
    brier = _runner.brier_score(y_test.tolist(), p_test.tolist())
    r10 = _runner.recall_at_top_k(y_test.tolist(), p_test.tolist(), 0.10)
    p10 = _runner.precision_at_top_k(y_test.tolist(), p_test.tolist(), 0.10)
    rs10 = _runner.rs_by_top_decile(y_test.tolist(), p_test.tolist())
    ece = _runner.calibration_ece(y_test.tolist(), p_test.tolist())

    print(f"  AUC = {auc:.3f} [{auc_lo:.3f}, {auc_hi:.3f}]")
    print(f"  Brier = {brier:.3f}, R@10% = {r10:.3f}, P@10% = {p10:.3f}, RS10 = {rs10:.2f}, ECE = {ece:.3f}")

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
        """, (f"lightgbm_v2_{variant}", "v2", cutoff,
              f"ti_phase2plus_test_post_{cutoff.year}_{variant}", len(y_test),
              int(y_test.sum()), int(len(y_test) - y_test.sum()),
              auc, auc_lo, auc_hi, brier, r10, p10, rs10, ece,
              f"Time-machine v2, variant={variant}, cutoff={cutoff}, train n={len(train_rows)}"))
        conn.commit()
    conn.close()


if __name__ == "__main__":
    for cutoff in [date(2017, 1, 1), date(2019, 1, 1), date(2021, 1, 1)]:
        for variant in ["time_cutoff_precedent", "drop_landscape"]:
            run(cutoff, variant)
