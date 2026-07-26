#!/usr/bin/env python3
"""
STRUCTURAL VERSIONED RE-PULL  (top follow-up flagged for PR #9 /
analyses/MODEL_SYSTEM_PREDICTIVENESS.md, "Tier 3 — structural").

WHY
---
Melissa's structural-evidence dimensions in `preclin.v_target_evidence_wide`
(DepMap depmap_pan_essential; IMPC impc_n_phenotypes; Open Targets ot_genetic_max /
ot_animal_model_max / ot_overall_max) are PRESENT-DAY snapshots applied to HISTORICAL
programs. A gene that looks well-supported today may have accumulated that support
*after* a program's trial started -- so any apparent predictive power is partly
hindsight. This script pins every Phase-2+ program's structural evidence to the source
release that was actually available AT its `first_trial_date`, and re-measures Relative
Success (RS) real-time vs. present-day to quantify how much of the structural signal is
real-time vs. hindsight.

BUILDS ON MELISSA'S CONSTRUCTS
------------------------------
* Cohort: same program grain + filters as benchmark/runner.py::load_cohort and the
  PR #9 nuance script (Phase >= 2, primary target, has first_trial_date + outcome).
* Relative Success: her definition RS = P(approved | support) / P(approved | not),
  with bootstrap CIs -- the exact `rs_ci` used in analyses/nuance_drug_and_structural.py.
* Support thresholds: her v_relative_success / analysis-view definitions
  ot_genetic_max>=0.3, ot_animal_model_max>=0.3, ot_overall_max>=0.5,
  impc_n_phenotypes>=3, depmap_pan_essential IS TRUE.
* Present-day snapshot values read straight from v_target_evidence_wide.

METHOD
------
Present-day is measured TWO ways, both reported:
  (P1) present-day-self  = OUR extraction of the newest OT release (25.06) / newest
       IMPC (DR-21) / newest DepMap (23Q2). Same extraction code as the dated releases,
       so real-time vs. present-day-self is a clean within-method delta attributable
       purely to DATE.
  (P2) present-day-DB    = Melissa's v_target_evidence_wide snapshot at her thresholds
       (the reference the task names). Absolute OT scores in the DB use a different/
       unknown aggregation (higher-scaled for top genes) so P1 is the rigorous internal
       comparator and P2 is the external reference.
Real-time = for each program, newest release with release_date <= first_trial_date;
the gene's evidence in THAT release (gene absent from the release => no evidence yet =>
not supported). Programs older than a source's earliest dated release are "undatable"
for that source and excluded from its comparison (coverage reported honestly).

OT Era A (<=20.06) legacy scores predate OT's 21.02 harmonic-sum rewrite and are NOT
on the present-day scale, so for Era A we use PREVALENCE-MATCHED thresholds (per release,
the score cut reproducing the present-day-self support prevalence) -- reported as a
scale-caveated coverage extension, never mixed into the Era B headline.

Outputs (lean, committed):
  data/structural_versioned_repull.csv          -- per-source RS summary
  data/structural_versioned_repull_programs.csv -- per-program dated vs present evidence
"""
from __future__ import annotations
import glob
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
VDIR = os.path.join(DATA, "versioned")
DB = os.environ.get("DATABASE_URL")

# Melissa's support thresholds (v_relative_success / analysis views)
THRESH = {
    "ot_genetic_max": ("ge", 0.3),
    "ot_animal_model_max": ("ge", 0.3),
    "ot_overall_max": ("ge", 0.5),
    "impc_n_phenotypes": ("ge", 3),
    "depmap_pan_essential": ("truthy", None),
}

# newest release per source = "present-day (self)"
PRESENT_OT = "25.06"
PRESENT_IMPC = "21.0"
PRESENT_DEPMAP = "23Q2"


# --------------------------------------------------------------------------- #
# Melissa's Relative Success (verbatim from analyses/nuance_drug_and_structural.py)
# --------------------------------------------------------------------------- #
def rs_ci(support, approved, n_boot=2000, seed=7):
    support = np.asarray(support, bool)
    approved = np.asarray(approved, bool)

    def _rs(sup, appr):
        s = appr[sup]; ns = appr[~sup]
        if s.size == 0 or ns.size == 0 or ns.mean() == 0:
            return np.nan
        return s.mean() / ns.mean()

    pt = _rs(support, approved)
    rng = np.random.default_rng(seed)
    idx = np.arange(support.size)
    boots = []
    for _ in range(n_boot):
        b = rng.choice(idx, idx.size, replace=True)
        boots.append(_rs(support[b], approved[b]))
    boots = np.array([x for x in boots if not np.isnan(x)])
    lo, hi = (np.percentile(boots, [2.5, 97.5]) if boots.size else (np.nan, np.nan))
    f = lambda x: round(float(x), 3) if x == x else np.nan
    return dict(rs=f(pt), lo=f(lo), hi=f(hi),
                n_support=int(support.sum()), n_not=int((~support).sum()),
                pct_appr_support=round(100 * approved[support].mean(), 1) if support.sum() else np.nan,
                pct_appr_not=round(100 * approved[~support].mean(), 1) if (~support).sum() else np.nan)


def supported(series, dim):
    kind, thr = THRESH[dim]
    if kind == "truthy":
        return series.fillna(0).astype(float) > 0
    return series.fillna(-1e9) >= thr


# --------------------------------------------------------------------------- #
# Load cohort (program grain) + present-day DB snapshot
# --------------------------------------------------------------------------- #
def load_cohort_and_snapshot():
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(DB)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT p.program_id, dt.target_id, t.symbol, t.ensembl_id,
               p.first_trial_date,
               (po.approved_us OR po.approved_ex_us) AS approved
        FROM preclin.program p
        JOIN preclin.v_drug_target dt ON dt.drug_id = p.drug_id AND dt.role='primary'
        JOIN public.targets t ON t.id = dt.target_id
        JOIN preclin.program_outcome po ON po.program_id = p.program_id
        WHERE p.highest_phase >= 2 AND p.first_trial_date IS NOT NULL
    """)
    prog = pd.DataFrame(cur.fetchall())
    cur.execute("""
        SELECT target_id, ot_genetic_max, ot_animal_model_max, ot_overall_max,
               impc_n_phenotypes, depmap_pan_essential
        FROM preclin.v_target_evidence_wide
    """)
    snap = pd.DataFrame(cur.fetchall())
    conn.close()
    prog["approved"] = prog.approved.fillna(False).astype(bool)
    prog["first_trial_date"] = pd.to_datetime(prog.first_trial_date)
    snap["depmap_pan_essential"] = snap.depmap_pan_essential.map(
        {True: 1.0, False: 0.0}).astype(float)
    return prog, snap


# --------------------------------------------------------------------------- #
# Load versioned per-release tables
# --------------------------------------------------------------------------- #
def load_releases(prefix, key_cols):
    frames = []
    for f in sorted(glob.glob(os.path.join(VDIR, f"{prefix}_*.csv"))):
        df = pd.read_csv(f, dtype={"release": str})  # keep "24.06"/"21.0" exact
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def pin_release(prog, rel, join_key, value_cols):
    """For each program pick newest release with release_date <= first_trial_date.
    Returns prog rows (join_key present) with value_cols from the pinned release + a
    'datable' flag. Gene absent in the pinned release => value 0 (no evidence yet)."""
    rel = rel.copy()
    rel["release_date"] = pd.to_datetime(rel["release_date"])
    rel_dates = sorted(rel["release_date"].unique())
    earliest = rel_dates[0]

    p = prog.dropna(subset=[join_key]).copy()
    p["datable"] = p.first_trial_date >= earliest

    def pick(row):
        cand = [d for d in rel_dates if d <= row.first_trial_date]
        return cand[-1] if cand else pd.NaT
    p["pinned_date"] = p.apply(pick, axis=1)

    rel_idx = rel.set_index([join_key, "release_date"])
    out_vals = {c: [] for c in value_cols}
    for _, row in p.iterrows():
        if pd.isna(row.pinned_date):
            for c in value_cols:
                out_vals[c].append(np.nan)
            continue
        try:
            r = rel_idx.loc[(row[join_key], row.pinned_date)]
            if isinstance(r, pd.DataFrame):
                r = r.iloc[0]
            for c in value_cols:
                out_vals[c].append(r[c])
        except KeyError:
            for c in value_cols:  # datable but gene not yet in this release => 0
                out_vals[c].append(0.0)
    for c in value_cols:
        p["rt_" + c] = out_vals[c]
    return p


def prevalence_matched_threshold(scores, target_prevalence):
    """Return the score cut c such that P(score >= c) ~= target_prevalence."""
    s = np.sort(scores.dropna().values)
    if s.size == 0 or target_prevalence <= 0:
        return np.inf
    q = np.quantile(s, max(0.0, 1.0 - target_prevalence))
    return q


# --------------------------------------------------------------------------- #
# Per-source analysis
# --------------------------------------------------------------------------- #
def analyse_ot(prog, snap):
    rel = load_releases("ot", ["ensembl_id"])
    rel = rel.dropna(subset=["ensembl_id"])
    dims = ["ot_overall_max", "ot_genetic_max", "ot_animal_model_max"]
    # present-day-self = newest release (Era B2)
    present = rel[rel.release == PRESENT_OT].set_index("ensembl_id")[dims]

    prog_ot = prog.dropna(subset=["ensembl_id"]).merge(
        snap[["target_id", "ot_genetic_max", "ot_animal_model_max", "ot_overall_max"]],
        on="target_id", how="left", suffixes=("", "_db"))

    rows = []
    per_prog = []

    for era_label, era_tags in [("EraB", ["21.06", "22.06", "23.06", "24.06", "25.06"]),
                                ("EraA", ["18.06", "19.06", "20.06"])]:
        subrel = rel[rel.release.isin(era_tags)]
        if subrel.empty:
            continue
        pinned = pin_release(prog_ot, subrel, "ensembl_id", dims)
        datable = pinned[pinned.datable].copy()
        # attach present-day-self
        for d in dims:
            datable["pd_" + d] = datable.ensembl_id.map(present[d])
        for d in dims:
            kind, thr = THRESH[d]
            if era_label == "EraA":
                # prevalence-matched threshold per dim (legacy scale)
                pd_prev = supported(datable["pd_" + d], d).mean()
                cut = prevalence_matched_threshold(datable["rt_" + d], pd_prev)
                rt_sup = datable["rt_" + d].fillna(0) >= cut
                thr_note = f"prevalence-matched cut={cut:.3f} (legacy scale)"
            else:
                rt_sup = supported(datable["rt_" + d], d)
                thr_note = f">= {thr}"
            pd_sup = supported(datable["pd_" + d], d)
            db_sup = supported(datable[d], d)  # present-day-DB (Melissa snapshot)
            appr = datable.approved.values
            r_rt = rs_ci(rt_sup, appr)
            r_pd = rs_ci(pd_sup, appr)
            r_db = rs_ci(db_sup, appr)
            rows.append(dict(source="OpenTargets", era=era_label, dimension=d,
                             threshold=thr_note,
                             n_datable=len(datable),
                             rt_support_prev=round(100 * rt_sup.mean(), 1),
                             pd_support_prev=round(100 * pd_sup.mean(), 1),
                             db_support_prev=round(100 * db_sup.mean(), 1),
                             rs_realtime=r_rt["rs"], rt_lo=r_rt["lo"], rt_hi=r_rt["hi"],
                             rs_present_self=r_pd["rs"], pd_lo=r_pd["lo"], pd_hi=r_pd["hi"],
                             rs_present_db=r_db["rs"]))
        if era_label == "EraB":
            keep = datable[["program_id", "target_id", "symbol", "ensembl_id",
                            "first_trial_date", "pinned_date", "approved"]].copy()
            for d in dims:
                keep["rt_" + d] = datable["rt_" + d].values
                keep["pd_" + d] = datable["pd_" + d].values
            keep["source"] = "OpenTargets"
            per_prog.append(keep)
    return rows, per_prog


def analyse_impc(prog, snap):
    rel = load_releases("impc", ["symbol"])
    present = rel[rel.release.astype(str) == PRESENT_IMPC].set_index("symbol")["n_phenotypes"]
    prog_i = prog.merge(snap[["target_id", "impc_n_phenotypes"]], on="target_id", how="left")
    pinned = pin_release(prog_i, rel, "symbol", ["n_phenotypes"])
    datable = pinned[pinned.datable].copy()
    datable["pd_n_phenotypes"] = datable.symbol.map(present)
    d = "impc_n_phenotypes"
    rt_sup = datable["rt_n_phenotypes"].fillna(0) >= THRESH[d][1]
    pd_sup = datable["pd_n_phenotypes"].fillna(0) >= THRESH[d][1]
    db_sup = supported(datable["impc_n_phenotypes"], d)
    appr = datable.approved.values
    r_rt = rs_ci(rt_sup, appr); r_pd = rs_ci(pd_sup, appr); r_db = rs_ci(db_sup, appr)
    row = dict(source="IMPC", era="dated", dimension=d, threshold=">= 3",
               n_datable=len(datable),
               rt_support_prev=round(100 * rt_sup.mean(), 1),
               pd_support_prev=round(100 * pd_sup.mean(), 1),
               db_support_prev=round(100 * db_sup.mean(), 1),
               rs_realtime=r_rt["rs"], rt_lo=r_rt["lo"], rt_hi=r_rt["hi"],
               rs_present_self=r_pd["rs"], pd_lo=r_pd["lo"], pd_hi=r_pd["hi"],
               rs_present_db=r_db["rs"])
    keep = datable[["program_id", "target_id", "symbol", "first_trial_date",
                    "pinned_date", "approved"]].copy()
    keep["rt_impc_n_phenotypes"] = datable["rt_n_phenotypes"].values
    keep["pd_impc_n_phenotypes"] = datable["pd_n_phenotypes"].values
    keep["source"] = "IMPC"
    return [row], [keep]


def analyse_depmap(prog, snap):
    rel = load_releases("depmap", ["symbol"])
    present_genes = set(rel[rel.release.astype(str) == PRESENT_DEPMAP].symbol)
    prog_d = prog.merge(snap[["target_id", "depmap_pan_essential"]], on="target_id", how="left")
    pinned = pin_release(prog_d, rel, "symbol", ["pan_essential"])
    datable = pinned[pinned.datable].copy()
    d = "depmap_pan_essential"
    rt_sup = datable["rt_pan_essential"].fillna(0).astype(float) > 0
    pd_sup = datable.symbol.isin(present_genes)
    db_sup = supported(datable["depmap_pan_essential"], d)
    appr = datable.approved.values
    r_rt = rs_ci(rt_sup, appr); r_pd = rs_ci(pd_sup, appr); r_db = rs_ci(db_sup, appr)
    row = dict(source="DepMap", era="dated", dimension=d, threshold="pan-essential",
               n_datable=len(datable),
               rt_support_prev=round(100 * rt_sup.mean(), 1),
               pd_support_prev=round(100 * pd_sup.mean(), 1),
               db_support_prev=round(100 * db_sup.mean(), 1),
               rs_realtime=r_rt["rs"], rt_lo=r_rt["lo"], rt_hi=r_rt["hi"],
               rs_present_self=r_pd["rs"], pd_lo=r_pd["lo"], pd_hi=r_pd["hi"],
               rs_present_db=r_db["rs"])
    keep = datable[["program_id", "target_id", "symbol", "first_trial_date",
                    "pinned_date", "approved"]].copy()
    keep["rt_depmap_pan_essential"] = rt_sup.astype(int).values
    keep["pd_depmap_pan_essential"] = pd_sup.astype(int).values
    keep["source"] = "DepMap"
    return [row], [keep]


def main():
    if not DB:
        sys.exit("Set DATABASE_URL")
    prog, snap = load_cohort_and_snapshot()
    print(f"cohort: {len(prog)} Phase-2+ programs, {prog.target_id.nunique()} targets, "
          f"{prog.approved.mean()*100:.1f}% approved, "
          f"first_trial {prog.first_trial_date.dt.year.min()}-{prog.first_trial_date.dt.year.max()}")

    rows, pp = [], []
    for fn in (analyse_ot, analyse_impc, analyse_depmap):
        r, p = fn(prog, snap)
        rows += r; pp += p

    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(DATA, "structural_versioned_repull.csv"), index=False)
    pd.concat(pp, ignore_index=True).to_csv(
        os.path.join(DATA, "structural_versioned_repull_programs.csv"), index=False)

    pd.set_option("display.width", 200, "display.max_columns", 30)
    print("\n=== RS: real-time vs present-day (self) vs present-day (DB snapshot) ===")
    show = ["source", "era", "dimension", "n_datable", "rt_support_prev", "pd_support_prev",
            "rs_realtime", "rs_present_self", "rs_present_db"]
    print(out[show].to_string(index=False))
    print("\nwrote data/structural_versioned_repull.csv (+ _programs.csv)")


if __name__ == "__main__":
    main()
