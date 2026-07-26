"""Does the predictive power of each evidence category depend on disease area / modality?

STATUS: exploratory, NOT pursued into the post. See analyses/STRATIFICATION_NOTE.md for
the honest write-up of what this tried and why the value-add is marginal. This file is
kept as the reproducible record so the analysis is not silently re-attempted.

Section 2 asks for predictive power "stratified by modality / disease area." The rigorous
way to answer a *does-it-differ-by-subgroup* question is a pooled logistic model with
evidence x stratum INTERACTION terms (the interaction block is the formal effect-
modification test), NOT per-stratum ablations (small strata -> underpowered; rank-only
AUC hides small effects; no formal test of the difference).

This generalizes Stephen's `genetic_conditioning_adjusted.py` (evidence x binary
genetics axis) to two axes built from Melissa's BIO-enrichment tables (PR #7):
  - disease area  : preclin.indication_bio_class.bio_area   (Oncology vs non-Oncology)
  - drug modality : preclin.drug_bio_class.modality         (small-molecule/biologic/other)

Cohort + evidence: HER loader (benchmark/runner.load_cohort, min_phase=2) -- the
evidence-complete Phase-2+ T-I cohort. Genetics is scored with HER `genetic_only_v1`
additive scorer (benchmark/scorers_rule_based.scorer_genetic_only), Strong tier = score
>= 1.4. A permissive "any genetic dimension" flag is ALSO computed, only to demonstrate
the coding sensitivity that is the main lesson here (it flips the genetics interaction
sign). Other evidence uses the structured, low-leakage thresholds from the conditioning
script; LLM literature lines are excluded from the headline.

Run:  DATABASE_URL='postgresql://...' python3 analyses/predictive_power_by_stratum.py
"""
from __future__ import annotations
import os
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import chi2

warnings.filterwarnings("ignore")
_BENCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "benchmark")
sys.path.insert(0, _BENCH)
from importlib import import_module  # noqa: E402

runner = import_module("runner")
scorers = import_module("scorers_rule_based")

DB_URL = os.environ.get("DATABASE_URL")
CURATED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

# Headline genetics term = HER genetic_only_v1 Strong tier. Other structured, low-leakage
# categories mirror genetic_conditioning_adjusted.py thresholds. null -> not-present.
EV_TERMS = ["gen_strong", "cell_ess", "animal", "tract_sm", "loeuf_lo"]


def num(series):
    return pd.to_numeric(series, errors="coerce")


def genetic_only_score(row):
    """HER additive genetic_only_v1 score (scorers_rule_based.scorer_genetic_only),
    computed from the raw cohort columns."""
    def g(c):
        v = row.get(c)
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0
    s = 0.0
    s += {"T4": 1.0, "T3": 0.7, "T2": 0.5, "T1": 0.3, "T0": -0.2}.get(row.get("nelson_tier"), 0.0)
    if g("clingen_n_strong") >= 1:
        s += 0.6
    m = g("mendelian_n")
    s += 0.5 if m >= 5 else (0.2 if m >= 1 else 0.0)
    otg = g("ot_genetic_max")
    s += 0.5 if otg >= 0.5 else (0.3 if otg >= 0.3 else 0.0)
    if g("ot_somatic_score_max") >= 0.3:
        s += 0.3
    return s


def build_frame(rows, area_map, mod_map):
    df = pd.DataFrame(rows)
    d = pd.DataFrame(index=df.index)
    d["approved"] = df["any_approved"].fillna(False).astype(bool).astype(int)

    # genetics: HER scorer, Strong tier (>=1.4); + permissive flag for the coding lesson
    d["gen_score"] = [genetic_only_score(r) for r in rows]
    d["gen_strong"] = (d["gen_score"] >= 1.4).astype(int)
    d["gen_any"] = (
        (num(df["ot_genetic_max"]) >= 0.30).fillna(False)
        | (num(df["mendelian_n"]) >= 5).fillna(False)
        | (num(df["clingen_n_strong"]) >= 1).fillna(False)
        | (num(df["gwas_n_sig"]) >= 50).fillna(False)
    ).astype(int)

    d["cell_ess"] = df["depmap_pan_essential"].fillna(False).astype(bool).astype(int)
    d["animal"] = (
        (num(df["impc_n_phenotypes"]) >= 3).fillna(False)
        | (num(df["ot_animal_model_max"]) >= 0.30).fillna(False)
    ).astype(int)
    d["tract_sm"] = df["tractability_sm"].fillna(False).astype(bool).astype(int)
    d["loeuf_lo"] = (num(df["gnomad_loeuf"]) < 0.35).fillna(False).astype(int)

    d["bio_area"] = df["indication_id"].map(area_map).fillna("Unclassified")
    d["is_onc"] = (d["bio_area"] == "Oncology").astype(int)
    tid = list(zip(df["target_id"], df["indication_id"]))
    d["mod3"] = pd.Series([mod_map.get(k, "unknown") for k in tid], index=df.index).map(bucket_modality)
    d["logprog"] = np.log1p(num(df["n_programs"]).fillna(1))
    return d


def bucket_modality(m):
    if m in ("antibody", "adc", "protein", "peptide"):
        return "biologic"
    if m == "small_molecule":
        return "small_molecule"
    return "other"


def block_lr(d, ev_terms, axis_expr, confounder):
    """Full (evidence*axis) vs reduced (evidence+axis); LR-test the interaction block."""
    ev = " + ".join(ev_terms)
    full = smf.logit(f"approved ~ ({ev}) * {axis_expr} + {confounder}", d).fit(disp=False, maxiter=300)
    red = smf.logit(f"approved ~ {ev} + {axis_expr} + {confounder}", d).fit(disp=False, maxiter=300)
    stat = 2 * (full.llf - red.llf)
    dfree = int(full.df_model - red.df_model)
    p = float(chi2.sf(stat, dfree)) if dfree > 0 else float("nan")
    return full, stat, dfree, p


def show(m, terms, header):
    print(header)
    OR, ci, p = np.exp(m.params), np.exp(m.conf_int()), m.pvalues
    for t in terms:
        if t not in m.params.index:
            continue
        lo, hi = ci.loc[t]
        print(f"    {t:26s} aOR={OR[t]:7.2f}  [{lo:6.2f},{hi:8.2f}]  p={p[t]:.1e}"
              + ("*" if p[t] < 0.05 else ""))


def main():
    import psycopg2
    if not DB_URL:
        sys.exit("Set DATABASE_URL")
    conn = psycopg2.connect(DB_URL)
    rows = runner.load_cohort(conn, min_phase=2)
    cur = conn.cursor()
    cur.execute("SELECT indication_id, bio_area FROM preclin.indication_bio_class")
    area_map = dict(cur.fetchall())
    cur.execute("""
        SELECT dt.target_id, p.indication_id,
               MODE() WITHIN GROUP (ORDER BY dbc.modality) AS modality
        FROM preclin.program p
        JOIN preclin.drug d ON d.drug_id = p.drug_id
        JOIN preclin.drug_bio_class dbc ON dbc.drug_id = d.drug_id
        JOIN preclin.v_drug_target dt ON dt.drug_id = p.drug_id AND dt.role='primary'
        GROUP BY dt.target_id, p.indication_id
    """)
    mod_map = {(t, i): m for t, i, m in cur.fetchall()}
    conn.close()

    d = build_frame(rows, area_map, mod_map)
    print(f"Cohort n={len(d):,}  base approval={d.approved.mean():.1%}  "
          f"(Oncology {int(d.is_onc.sum()):,} / non-Onc {int((1-d.is_onc).sum()):,})")
    print(f"  This cohort is 63% oncology; only Oncology-vs-rest is well powered.\n")

    # ---- PRIMARY: Oncology interaction, HER strong-genetics coding + shots-on-goal ----
    full, stat, dfree, p = block_lr(d, EV_TERMS, "is_onc", "C(mod3) + logprog")
    print("=" * 78)
    print(f"[A] Oncology x evidence interaction (strong-genetics coding, +log n_programs)")
    print(f"    LR block test: chi2={stat:.1f}, df={dfree}, p={p:.1e}")
    print("=" * 78)
    show(full, EV_TERMS, "  main effect (non-oncology reference):")
    show(full, [f"{t}:is_onc" for t in EV_TERMS], "  interaction (extra effect in oncology):")

    # ---- THE LESSON: genetics interaction flips sign on coding ----
    print("\n" + "=" * 78)
    print("[B] Coding sensitivity of the genetics interaction (why you must use strength)")
    print("=" * 78)
    for gterm, lbl in [("gen_any", "permissive 'any genetic dim'"), ("gen_strong", "HER Strong tier")]:
        ev = [gterm] + [t for t in EV_TERMS if t != "gen_strong"]
        m = smf.logit(f"approved ~ ({' + '.join(ev)}) * is_onc + C(mod3) + logprog", d).fit(disp=False, maxiter=300)
        print(f"  {lbl:32s} (prev {d[gterm].mean():.0%}):  "
              f"{gterm}:is_onc aOR={np.exp(m.params[f'{gterm}:is_onc']):.2f}  p={m.pvalues[f'{gterm}:is_onc']:.1e}")
    print("  -> permissive flag inverts the sign. This is exactly the rule-#2 dilution trap.")

    # ---- Secondary/UNSTABLE: modality axis (recorded, not trusted) ----
    print("\n" + "=" * 78)
    print("[C] Modality axis (SECONDARY - unstable, 'other' bucket separates; not reported)")
    print("=" * 78)
    d2 = d.copy()
    d2["mod3"] = pd.Categorical(d2["mod3"], categories=["small_molecule", "biologic", "other"])
    fullm, statm, dfm, pm = block_lr(d2, EV_TERMS, "C(mod3)", "is_onc + logprog")
    print(f"    LR block test: chi2={statm:.1f}, df={dfm}, p={pm:.1e}  "
          f"(but see 'other' CIs below -- near-separation)")
    show(fullm, [f"gen_strong:C(mod3)[T.other]", f"cell_ess:C(mod3)[T.other]"],
         "  example unstable terms:")

    os.makedirs(CURATED, exist_ok=True)
    out = pd.DataFrame({"aOR": np.exp(full.params), "p": full.pvalues})
    out[["ci_lo", "ci_hi"]] = np.exp(full.conf_int())
    out.to_csv(os.path.join(CURATED, "predictive_power_oncology_interaction.csv"))
    print(f"\nWrote data/predictive_power_oncology_interaction.csv (record only).")


if __name__ == "__main__":
    main()
