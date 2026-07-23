"""ML-trained scorers with proper cross-validation.

- LogReg (L2-regularized, calibrated via CalibratedClassifierCV)
- LightGBM (nonlinear, handles NaN natively)
- RandomForest (robust baseline)

Each scorer trains via k-fold CV: predictions are held-out (out-of-fold) so
comparing against ground truth is not circular. Final scorer refits on all
data for storage in benchmark_prediction.

Features: all 40+ evidence dimensions from v_target_evidence_wide + T-I
context (Nelson tier, therapeutic area, n_programs).
"""

import os
import sys
import warnings
from typing import Dict, List, Tuple

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

warnings.filterwarnings("ignore")
np.random.seed(42)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
_scorers = import_module("10_benchmark_scorers")
_runner = import_module("11_benchmark_runner")

DB_URL = os.environ["DATABASE_URL"]


# ============================================================
# Feature engineering
# ============================================================

# Numeric features (float or int) — PRE-OUTCOME ONLY.
# Explicitly excluded (LEAKY):
#   n_sponsors / n_programs / n_drugs / max_phase_reached — reflect post-hoc
#                                                            program development
#   ot_known_drug_max — Open Targets score based on known drugs, i.e. approval
#   ot_overall_max — includes ot_known_drug_max as a component
# What remains: pre-outcome preclinical evidence + non-leaky landscape signals.
NUMERIC_FEATURES = [
    # A_genetics
    "mendelian_n", "mendelian_n_dominant", "mendelian_n_recessive",
    "clingen_n_strong", "gwas_n_sig",
    "ot_genetic_max", "ot_somatic_score_max", "ot_rna_expression_max",
    "ot_l2g_score_max",
    # B_mechanistic
    "line_b_lit", "tau_specificity", "sc_tau_specificity",
    "n_ppi_partners", "n_reactome_pathways",
    "n_go_biological_process", "n_go_molecular_function", "n_go_cellular_component",
    "max_tissue_tpm", "n_high_tissues", "sc_max_cell_value", "sc_n_cell_types_expressed",
    # C_cell
    "line_c_lit", "depmap_n_dep_lineages", "depmap_mean_effect",
    # D_animal
    "line_d_lit", "ot_animal_model_max", "impc_n_phenotypes", "n_hpo_phenotypes",
    # E_pd
    "line_e_lit",
    # H_safety
    "gnomad_pli", "gnomad_loeuf",
    # I_landscape (family precedent is arguably ok — was known pre-program-start)
    "family_approved_count", "gene_approved_count",
    "n_causal_diseases", "n_suggestive_diseases", "n_dgidb_drugs",
]

# Boolean features
BOOL_FEATURES = [
    "tractability_sm", "tractability_ab", "tractability_protac",
    "depmap_pan_essential", "ot_is_mendelian_any",
]

# Categorical: Nelson tier + therapeutic area
NELSON_TIERS = ["T0", "T1", "T2", "T3", "T4"]
THERAPEUTIC_AREAS = ["oncology", "neuro", "autoimmune", "cv", "metabolic",
                     "rare", "infectious", "other"]


def row_to_feature_vector(row: dict) -> np.ndarray:
    """Turn a cohort row into a numeric feature vector."""
    feats = []
    for f in NUMERIC_FEATURES:
        v = row.get(f)
        if v is None:
            feats.append(np.nan)
        else:
            try:
                feats.append(float(v))
            except (TypeError, ValueError):
                feats.append(np.nan)
    for f in BOOL_FEATURES:
        v = row.get(f)
        if v is None:
            feats.append(np.nan)
        else:
            feats.append(1.0 if v else 0.0)
    # Nelson tier one-hot
    tier = row.get("nelson_tier")
    for t in NELSON_TIERS:
        feats.append(1.0 if tier == t else 0.0)
    # TA one-hot
    ta = row.get("therapeutic_area") or "other"
    for a in THERAPEUTIC_AREAS:
        feats.append(1.0 if ta == a else 0.0)
    return np.array(feats, dtype=np.float64)


FEATURE_NAMES = (NUMERIC_FEATURES + BOOL_FEATURES +
                 [f"nelson_{t}" for t in NELSON_TIERS] +
                 [f"ta_{a}" for a in THERAPEUTIC_AREAS])


# ============================================================
# Load cohort
# ============================================================

def load_cohort_features() -> Tuple[List[dict], np.ndarray, np.ndarray]:
    """Returns (raw_rows, X_features, y_labels)."""
    conn = psycopg2.connect(DB_URL)
    rows = _runner.load_cohort(conn, min_phase=2)
    conn.close()
    X = np.stack([row_to_feature_vector(r) for r in rows])
    y = np.array([1 if r.get("any_approved") else 0 for r in rows], dtype=np.int64)
    return list(rows), X, y


# ============================================================
# CV trainer — returns out-of-fold predictions per row
# ============================================================

def cv_predict(model_ctor, X, y, n_splits=5, seed=42):
    """Fit model via stratified k-fold, return out-of-fold P(y=1)."""
    kf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    oof = np.zeros(len(y), dtype=np.float64)
    fold_aucs = []
    for train_idx, test_idx in kf.split(X, y):
        model = model_ctor()
        model.fit(X[train_idx], y[train_idx])
        oof[test_idx] = model.predict_proba(X[test_idx])[:, 1]
        auc = _runner.auc_roc(y[test_idx].tolist(), oof[test_idx].tolist())
        fold_aucs.append(auc)
    return oof, fold_aucs


# ============================================================
# Model factories
# ============================================================

def make_logreg():
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("clf", CalibratedClassifierCV(
            LogisticRegression(penalty="l2", C=1.0, max_iter=500, class_weight="balanced"),
            method="isotonic", cv=3)),
    ])


def make_rf():
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("clf", RandomForestClassifier(
            n_estimators=200, max_depth=8, min_samples_leaf=10,
            random_state=42, n_jobs=-1, class_weight="balanced")),
    ])


def make_lgb():
    if not HAS_LGB:
        return None
    return lgb.LGBMClassifier(
        n_estimators=300, learning_rate=0.05, max_depth=6, num_leaves=31,
        min_child_samples=20, subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.1, reg_lambda=0.1, class_weight="balanced",
        random_state=42, verbose=-1,
    )


# ============================================================
# Runner — trains, stores as benchmark run
# ============================================================

def run_ml_benchmark(scorer_name: str, model_ctor, cohort_name="ti_phase2plus"):
    from psycopg2.extras import execute_values, Json
    print(f"\n== ML Benchmark: {scorer_name} ==")

    rows, X, y = load_cohort_features()
    print(f"  cohort: {len(rows)}, features: {X.shape[1]}, positive rate: {y.mean():.3f}")

    oof, fold_aucs = cv_predict(model_ctor, X, y, n_splits=5)
    print(f"  Per-fold AUCs: {[f'{a:.3f}' for a in fold_aucs]}")
    print(f"  Mean fold AUC: {np.mean(fold_aucs):.3f}")

    # Compute overall metrics on OOF predictions
    y_list = y.tolist()
    p_list = oof.tolist()

    auc, auc_lo, auc_hi = _runner.bootstrap_metric(y_list, p_list, _runner.auc_roc)
    brier, brier_lo, brier_hi = _runner.bootstrap_metric(y_list, p_list, _runner.brier_score)
    r5 = _runner.recall_at_top_k(y_list, p_list, 0.05)
    r10 = _runner.recall_at_top_k(y_list, p_list, 0.10)
    r20 = _runner.recall_at_top_k(y_list, p_list, 0.20)
    p10 = _runner.precision_at_top_k(y_list, p_list, 0.10)
    rs10 = _runner.rs_by_top_decile(y_list, p_list)
    rs25 = _runner.rs_by_top_quartile(y_list, p_list)
    ece = _runner.calibration_ece(y_list, p_list)

    print(f"  AUC = {auc:.3f} [{auc_lo:.3f}, {auc_hi:.3f}]")
    print(f"  Brier = {brier:.3f}, R@10% = {r10:.3f}, P@10% = {p10:.3f}")
    print(f"  RS(top 10%) = {rs10:.2f}, ECE = {ece:.3f}")

    # Store
    conn = psycopg2.connect(DB_URL)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO preclin.benchmark_run
              (scoring_function, scoring_version, cohort_definition,
               n_ti_pairs, n_approved, n_failed,
               auc_roc, auc_roc_ci_lo, auc_roc_ci_hi,
               brier_score, brier_score_ci_lo, brier_score_ci_hi,
               recall_at_5pct, recall_at_10pct, recall_at_20pct,
               precision_at_10pct, rs_top_decile, rs_top_quartile, calibration_ece,
               notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING benchmark_run_id
        """, (scorer_name, "v1", cohort_name, len(rows), int(y.sum()), int(len(y) - y.sum()),
              auc, auc_lo, auc_hi, brier, brier_lo, brier_hi,
              r5, r10, r20, p10, rs10, rs25, ece,
              f"5-fold CV OOF, mean fold AUC={np.mean(fold_aucs):.3f}"))
        run_id = cur.fetchone()[0]

        # Predictions
        ranked_idx = np.argsort(-oof)
        rank_map = {i: r + 1 for r, i in enumerate(ranked_idx)}
        pred_rows = []
        for i, (row, p, yi) in enumerate(zip(rows, oof, y)):
            def tier(pp):
                return "high" if pp >= 0.35 else ("medium" if pp >= 0.18 else "low")
            pred_rows.append((
                run_id, row["target_id"], row["indication_id"],
                float(p), tier(p), rank_map[i],
                None, None, "medium", int(np.sum(~np.isnan(X[i]))),
                bool(yi), None, row.get("max_phase_reached"), row.get("n_programs"),
                None
            ))
        execute_values(cur, """
            INSERT INTO preclin.benchmark_prediction
              (benchmark_run_id, target_id, indication_id,
               predicted_p_approval, predicted_tier, predicted_rank,
               top_supporting_dims, top_concerning_dims, score_confidence, n_features_used,
               y_approved, y_realization_date, y_highest_phase, y_n_programs,
               evidence_snapshot)
            VALUES %s
        """, pred_rows, page_size=1000)

        # Feature importance (train once on all data)
        model_full = model_ctor()
        model_full.fit(X, y)
        importance_info = None
        try:
            if hasattr(model_full, "feature_importances_"):
                importance_info = model_full.feature_importances_
            elif hasattr(model_full, "named_steps") and "clf" in model_full.named_steps:
                clf = model_full.named_steps["clf"]
                if hasattr(clf, "feature_importances_"):
                    importance_info = clf.feature_importances_
                elif hasattr(clf, "coef_"):
                    importance_info = np.abs(clf.coef_[0])
        except Exception:
            pass
        if importance_info is not None:
            top_features = sorted(zip(FEATURE_NAMES, importance_info), key=lambda t: -t[1])[:15]
            print(f"  Top-15 features:")
            for name, imp in top_features:
                print(f"    {name:38} {imp:.3f}")
        conn.commit()
    conn.close()
    print(f"  benchmark_run_id={run_id}")
    return run_id


if __name__ == "__main__":
    print("Running ML scorers ...")
    run_ml_benchmark("logreg_l2_v1", make_logreg)
    run_ml_benchmark("randomforest_v1", make_rf)
    if HAS_LGB:
        run_ml_benchmark("lightgbm_v1", make_lgb)
    else:
        print("Skipping LightGBM (not installed)")
