#!/usr/bin/env python3
"""
Section 2, part 3 — does any OTHER evidence add predictive value ON TOP OF genetics?

Melissa's leave-one-category-out ablation (analyses/ablation.py, the category_ablation
figure) answers this BACKWARD: dropping cell / animal literature from the full model
costs ~0 AUC. This script is the FORWARD / stratified complement — the direct
"conditional on genetics" test:

  Split Phase 2+ programs into GENETICS-PRESENT vs GENETICS-ABSENT, then within each
  stratum fit a multivariate logistic regression of approval on every non-genetic
  evidence type at once (adjusted for each other + therapeutic area + target
  development level). If an evidence type only predicts approval WHEN genetics is
  already present, it is a genetics PROXY, not independent signal. If it predicts in
  BOTH strata, it is genuinely additive.

  A pooled evidence x genetics INTERACTION model gives the formal test of the flip.

Genetics strata use Melissa's OWN strength score `genetic_only_v1` (ClinGen /
Mendelian / OT-genetic / OT-somatic / Nelson), reproduced verbatim from
benchmark/scorers_rule_based.py. GENETICS-PRESENT := score >= 1.0 (her Moderate+Strong
tiers). This is the STRENGTH definition, not "any genetic dimension" — the permissive
any-dimension composite fires for ~84% of programs and dilutes the contrast to noise
(reported as a labeled sensitivity below, PERMISSIVE_SENSITIVITY).

Drug-level LLM-extracted efficacy is EXCLUDED (hindsight-contaminated for approved
drugs, per db/SCHEMA.md). Target-level literature lines (C/D/E) are LLM-extracted too
and present-day (not time-gated); they are kept here precisely because the finding is
that they FLIP / do not add — see caveat in the printout.

Run:  DATABASE_URL='postgresql://...' python3 analyses/genetic_conditioning.py
Out:  data/genetic_conditioning.csv     (per-evidence aOR in each stratum + interaction p)
      data/genetic_conditioning_interaction.csv  (full pooled interaction model)
"""
from __future__ import annotations
import os
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "genetic_conditioning.csv")
OUT_INT = os.path.join(HERE, "..", "data", "genetic_conditioning_interaction.csv")

BROAD_SET = ("approved", "efficacy_fail", "safety_fail", "commercial_fail",
             "enrollment_fail", "presumptive_efficacy_fail_ph3", "presumptive_fail_ph2")

SQL = f"""
SELECT w.outcome_broad, w.clingen_n_strong, w.mendelian_n, w.ot_genetic_max,
       tw.ot_somatic_score_max, w.nelson_tier, w.gwas_n_sig,
       w.line_c_lit, w.line_d_lit, w.line_e_lit, w.impc_n_phenotypes,
       w.ot_animal_model_max, w.tractability_sm, w.gnomad_loeuf, w.depmap_pan_essential,
       w.therapeutic_area, w.target_tdl, w.modality
FROM preclin.v_program_evidence_wide w
LEFT JOIN preclin.v_target_evidence_wide tw ON tw.target_id = w.target_id
JOIN preclin.drug d ON d.drug_id = w.drug_id
WHERE w.target_id IS NOT NULL AND w.outcome_broad IN {BROAD_SET}
  AND w.highest_phase >= 2 AND d.is_placebo IS NOT TRUE
"""

# non-genetic evidence -> clean model var (thresholds verbatim from v_effect_sizes_2x2)
EVIDENCE = {
    "cell_lit":   ("line_c_lit",          ">=", 2),
    "animal_lit": ("line_d_lit",          ">=", 2),
    "pd_lit":     ("line_e_lit",          ">=", 2),
    "impc3":      ("impc_n_phenotypes",   ">=", 3),
    "ot_animal":  ("ot_animal_model_max", ">=", 0.3),
    "tract_sm":   ("tractability_sm",     "truthy", None),
    "loeuf_lo":   ("gnomad_loeuf",        "<", 0.35),
    "depmap_ess": ("depmap_pan_essential", "truthy", None),
}
EV_TERMS = list(EVIDENCE)
# display label + whether the source is LLM-extracted literature (hindsight-prone)
LABELS = {
    "cell_lit": ("Cell-pathway literature ≥2", True),
    "animal_lit": ("Animal in-vivo literature ≥2", True),
    "pd_lit": ("Human PD-engagement lit ≥2", True),
    "impc3": ("IMPC mouse phenotypes ≥3", False),
    "ot_animal": ("OT animal-model ≥0.3", False),
    "tract_sm": ("Small-molecule tractable", False),
    "loeuf_lo": ("Constrained gene (LOEUF<0.35)", False),
    "depmap_ess": ("DepMap pan-essential", False),
}

NELSON = {"T4": 1.0, "T3": 0.7, "T2": 0.5, "T1": 0.3, "T0": -0.2}


def load():
    csv = os.environ.get("EVIDENCE_CSV")
    if csv:
        return pd.read_csv(csv)
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("Set DATABASE_URL (Neon connection string; see db/README.md).")
    import psycopg2
    import warnings
    warnings.filterwarnings("ignore")
    with psycopg2.connect(url) as conn:
        return pd.read_sql(SQL, conn)


def genetic_only_v1(r) -> float:
    """Verbatim port of benchmark/scorers_rule_based.py::scorer_genetic_only (score only)."""
    s = 0.0
    n = r["nelson_tier"]
    if n in NELSON:
        s += NELSON[n]
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


def binarize(df, col, op, thr):
    if op == "truthy":
        return df[col].fillna(False).astype(bool).astype(int)
    v = pd.to_numeric(df[col], errors="coerce")
    return ((v >= thr) if op == ">=" else (v < thr)).fillna(False).astype(int)


def prep(raw):
    raw = raw[raw["outcome_broad"].isin(BROAD_SET)].copy()
    d = pd.DataFrame(index=raw.index)
    d["approved"] = raw["outcome_broad"].eq("approved").astype(int)
    for var, (col, op, thr) in EVIDENCE.items():
        d[var] = binarize(raw, col, op, thr)
    g = raw.apply(genetic_only_v1, axis=1)
    d["gscore"] = g
    d["gpres"] = (g >= 1.0).astype(int)                       # STRENGTH: Moderate+Strong
    num = lambda c: pd.to_numeric(raw[c], errors="coerce")
    d["gperm"] = ((num("ot_genetic_max") >= 0.30).fillna(False)   # permissive any-dimension
                  | (num("mendelian_n") >= 5).fillna(False)
                  | (num("clingen_n_strong") >= 1).fillna(False)
                  | (num("gwas_n_sig") >= 50).fillna(False)).astype(int)
    d["ta"] = raw["therapeutic_area"].fillna("unknown").astype(str)
    d["tdl"] = raw["target_tdl"].fillna("unknown").astype(str)
    return d


def fit(formula, data):
    try:
        m = smf.logit(formula, data=data).fit(disp=False, maxiter=300)
        if not np.isfinite(m.bse).all():
            return None
        return m
    except Exception as e:
        print(f"  fit failed: {str(e)[:80]}")
        return None


# confounder blocks, strongest-first; step down if singular
CONF = ["+ C(ta) + C(tdl)", "+ C(ta)", ""]


def fit_adj(base, data):
    for c in CONF:
        m = fit(f"{base} {c}".strip(), data)
        if m is not None:
            return m, (c.replace("+ ", "").strip() or "none")
    return None, None


RNG = np.random.default_rng(7)


def rs_ci(sub, t, n_boot=4000):
    """Unadjusted within-stratum relative success = P(appr|evidence) / P(appr|no evidence),
    with a bootstrap 95% CI over the 2x2. Returns None if either arm is too thin."""
    a = sub.approved[sub[t] == 1].to_numpy(); b = sub.approved[sub[t] == 0].to_numpy()
    if len(a) < 15 or len(b) < 15 or b.mean() == 0:
        return None
    rs = a.mean() / b.mean()
    boot = np.array([RNG.choice(a, len(a)).mean() / max(RNG.choice(b, len(b)).mean(), 1e-9)
                     for _ in range(n_boot)])
    return rs, float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)), len(a)


def stratum_ors(d, gcol, label, with_rs=False):
    ev = " + ".join(EV_TERMS)
    print(f"\n{'='*72}\nSTRATA by {label}  ({gcol})")
    ors, rss = {}, {}
    for gval, name in [(1, "Gpos"), (0, "Gneg")]:
        sub = d[d[gcol] == gval]
        m, conf = fit_adj(f"approved ~ {ev}", sub)
        print(f"  {name}: n={len(sub):,}  approval={sub.approved.mean():.1%}  [adj: {conf}]")
        if m is not None:
            OR = np.exp(m.params); ci = np.exp(m.conf_int()); p = m.pvalues
            for t in EV_TERMS:
                if t in OR.index:
                    ors[(t, name)] = (OR[t], ci.loc[t, 0], ci.loc[t, 1], p[t])
        if with_rs:
            for t in EV_TERMS:
                r = rs_ci(sub, t)
                if r is not None:
                    rss[(t, name)] = r
    return ors, rss


def main():
    d = prep(load())
    print(f"Cohort: {len(d):,} Phase 2+ non-placebo programs  base approval {d.approved.mean():.1%}")
    print(f"  STRENGTH  G+ (score>=1.0): {int(d.gpres.sum()):,}  |  G- : {int((1-d.gpres).sum()):,}")
    print(f"  PERMISSIVE G+ (any dim)  : {int(d.gperm.sum()):,} ({d.gperm.mean():.0%})  |  G- : {int((1-d.gperm).sum()):,}")

    ors, rss = stratum_ors(d, "gpres", "STRENGTH genetic_only_v1>=1.0  [PRIMARY]", with_rs=True)
    stratum_ors(d, "gperm", "PERMISSIVE any-genetic-dimension  [SENSITIVITY]")

    # pooled interaction model (strength strata): evidence * gpres, adjusted
    ev_x = " + ".join(f"{t}*gpres" for t in EV_TERMS)
    mi, conf = fit_adj(f"approved ~ {ev_x}", d)
    print(f"\n{'='*72}\nPOOLED INTERACTION (strength strata; adj: {conf})")
    inter_p = {}
    if mi is not None:
        OR = np.exp(mi.params); ci = np.exp(mi.conf_int()); p = mi.pvalues
        print(f"  {'term':22s} {'aOR':>7s} {'p':>10s}")
        for t in EV_TERMS:
            it = f"{t}:gpres"
            if it in p.index:
                inter_p[t] = p[it]
                star = "*" if p[it] < 0.05 else " "
                print(f"  {t+':gpres':22s} {OR[it]:7.2f} {p[it]:10.1e}{star}")
        outi = pd.DataFrame({"term": mi.params.index, "aOR": np.exp(mi.params).values,
                             "p": mi.pvalues.values,
                             "ci_lo": np.exp(mi.conf_int()).iloc[:, 0].values,
                             "ci_hi": np.exp(mi.conf_int()).iloc[:, 1].values})
        os.makedirs(os.path.dirname(OUT_INT), exist_ok=True)
        outi.to_csv(OUT_INT, index=False)

    # tidy per-evidence CSV for plotting: aOR in each stratum + interaction p
    recs = []
    for t in EV_TERMS:
        lab, is_lit = LABELS[t]
        rec = dict(term=t, label=lab, llm_literature=is_lit,
                   interaction_p=inter_p.get(t, np.nan))
        for name in ("Gpos", "Gneg"):
            if (t, name) in ors:
                o, lo, hi, pv = ors[(t, name)]
                rec[f"aOR_{name}"] = round(o, 3)
                rec[f"lo_{name}"] = round(lo, 3)
                rec[f"hi_{name}"] = round(hi, 3)
                rec[f"p_{name}"] = pv
            if (t, name) in rss:
                rs, rlo, rhi, na = rss[(t, name)]
                rec[f"rs_{name}"] = round(rs, 3)
                rec[f"rslo_{name}"] = round(rlo, 3)
                rec[f"rshi_{name}"] = round(rhi, 3)
                rec[f"nsup_{name}"] = na
        recs.append(rec)
    out = pd.DataFrame(recs)
    out.to_csv(OUT, index=False)
    print(f"\nwrote {OUT}")
    print(out[["label", "aOR_Gpos", "aOR_Gneg", "interaction_p"]].to_string(index=False))


if __name__ == "__main__":
    main()
