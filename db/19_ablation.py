"""Leave-one-category-out ablation.

For each evidence category A-I, retrain LightGBM with that category's features
removed, measure AUC drop vs full model.

Tells us which categories are load-bearing.
"""

import os
import sys
from collections import defaultdict

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
_runner = import_module("11_benchmark_runner")
_ml = import_module("13_ml_scorers")

DB_URL = os.environ["DATABASE_URL"]


# Map each ML feature name → category (from evidence_dimension registry)
CATEGORY_MAP = {
    # A_genetics
    "mendelian_n": "A_genetics", "mendelian_n_dominant": "A_genetics", "mendelian_n_recessive": "A_genetics",
    "clingen_n_strong": "A_genetics", "gwas_n_sig": "A_genetics",
    "ot_genetic_max": "A_genetics", "ot_somatic_score_max": "A_genetics",
    "ot_rna_expression_max": "A_genetics", "ot_l2g_score_max": "A_genetics",
    "ot_is_mendelian_any": "A_genetics",
    # B_mechanistic
    "line_b_lit": "B_mechanistic", "tractability_sm": "B_mechanistic",
    "tractability_ab": "B_mechanistic", "tractability_protac": "B_mechanistic",
    "tau_specificity": "B_mechanistic", "sc_tau_specificity": "B_mechanistic",
    "n_ppi_partners": "B_mechanistic", "n_reactome_pathways": "B_mechanistic",
    "n_go_biological_process": "B_mechanistic", "n_go_molecular_function": "B_mechanistic",
    "n_go_cellular_component": "B_mechanistic",
    "max_tissue_tpm": "B_mechanistic", "n_high_tissues": "B_mechanistic",
    "sc_max_cell_value": "B_mechanistic", "sc_n_cell_types_expressed": "B_mechanistic",
    # C_cell
    "line_c_lit": "C_cell", "depmap_n_dep_lineages": "C_cell",
    "depmap_mean_effect": "C_cell", "depmap_pan_essential": "C_cell",
    # D_animal
    "line_d_lit": "D_animal", "ot_animal_model_max": "D_animal",
    "impc_n_phenotypes": "D_animal", "n_hpo_phenotypes": "D_animal",
    # E_pd
    "line_e_lit": "E_pd",
    # H_safety
    "gnomad_pli": "H_safety", "gnomad_loeuf": "H_safety",
    # I_landscape
    "family_approved_count": "I_landscape", "gene_approved_count": "I_landscape",
    "n_causal_diseases": "I_landscape", "n_suggestive_diseases": "I_landscape",
    "n_dgidb_drugs": "I_landscape",
}


def ablate(feature_names, X, y, exclude_category):
    """Return AUC when features in exclude_category are set to NaN (masked)."""
    X_ablate = X.copy()
    for i, name in enumerate(feature_names):
        base = name  # simple names (nelson_/ta_ prefixed ones aren't in CATEGORY_MAP)
        cat = CATEGORY_MAP.get(base)
        if base.startswith("nelson_"):
            cat = "A_genetics"
        elif base.startswith("ta_"):
            cat = "context"  # therapeutic area
        if cat == exclude_category:
            X_ablate[:, i] = np.nan
    oof, fold_aucs = _ml.cv_predict(_ml.make_lgb, X_ablate, y, n_splits=5)
    return _runner.auc_roc(y.tolist(), oof.tolist()), np.mean(fold_aucs)


def main():
    conn = psycopg2.connect(DB_URL)
    rows = _runner.load_cohort(conn, min_phase=2)
    X = np.stack([_ml.row_to_feature_vector(r) for r in rows])
    y = np.array([1 if r.get("any_approved") else 0 for r in rows], dtype=np.int64)
    print(f"Cohort: {len(rows)}, positive: {y.mean():.3f}")

    # Full model
    oof_full, _ = _ml.cv_predict(_ml.make_lgb, X, y, n_splits=5)
    auc_full = _runner.auc_roc(y.tolist(), oof_full.tolist())
    print(f"\nFull model AUC: {auc_full:.3f}")

    categories = ["A_genetics", "B_mechanistic", "C_cell", "D_animal", "E_pd",
                  "H_safety", "I_landscape", "context"]
    print("\nLeave-one-category-out ablation:")
    print(f"{'Category':<16} {'AUC':<8} {'ΔAUC (vs full)':<18}")
    print("-" * 46)

    results = []
    for cat in categories:
        auc_ab, fold_auc = ablate(_ml.FEATURE_NAMES, X, y, cat)
        delta = auc_ab - auc_full
        print(f"{cat:<16} {auc_ab:.3f}   {delta:+.4f}")
        results.append((cat, auc_ab, delta))

    with conn.cursor() as cur:
        for cat, auc, delta in results:
            cur.execute("""
                INSERT INTO preclin.benchmark_run
                  (scoring_function, scoring_version, cohort_definition,
                   n_ti_pairs, n_approved, n_failed, auc_roc, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (f"lightgbm_ablate_no_{cat}", "v1", "ti_phase2plus", len(rows),
                  int(y.sum()), int(len(y) - y.sum()), auc,
                  f"Leave-out={cat}. Full AUC={auc_full:.3f}, delta={delta:+.4f}"))
        conn.commit()
    conn.close()

    print("\nMost load-bearing categories (biggest AUC drop when removed):")
    for cat, auc, delta in sorted(results, key=lambda x: x[2]):
        print(f"  {cat:<16} ΔAUC={delta:+.4f}")


if __name__ == "__main__":
    main()
