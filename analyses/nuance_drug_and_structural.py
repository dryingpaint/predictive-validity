#!/usr/bin/env python3
"""
Nuance / Section 5 — drug-efficacy tier + structural tier.

DRUG-EFFICACY TIER (the most "mechanistic": does THIS drug work in the model):
  - Raw RS from Melissa's existing drug_cell/rodent/nonrodent_efficacy scores
    (>=2 = high). These have NO stored PMIDs, so they cannot be date-cleaned in place.
  - Date-aware measure instead: for each program-linked drug, ask PubMed whether any
    preclinical (cell/animal) paper for that drug existed BEFORE the program's first
    trial. RS of that pre-trial-evidence presence. Different metric from the rubric,
    so reported as its own clean measure, not a "cleaned" rubric score.

STRUCTURAL TIER (causal perturbation, from screens not literature):
  - Raw RS for DepMap essentiality / IMPC KO phenotypes / OT animal-model.
  - Date treatment = resource-existence floor: DepMap CRISPR ~2016, IMPC ~2016 useful
    coverage (DB snapshot is a flat 2025 release), OT ~2016. Evidence is credited only
    if the program's first trial started after the resource plausibly existed.
    (Full per-gene versioned re-pull of dated DepMap/IMPC/OT releases is the specified
    heavier next increment — see MODEL_SYSTEM_PREDICTIVENESS.md. Not run here because
    it needs multi-hundred-MB historical downloads this environment can't safely hold.)

Writes data/nuance_drug_structural.csv.
"""
from __future__ import annotations
import os, sys, time, json, urllib.request, urllib.parse
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
PUBMED_CACHE = os.path.join(DATA, "drug_pretrial_pubmed.csv")
DB = os.environ.get("DATABASE_URL")

RESOURCE_FLOOR = {"DepMap essentiality": 2016, "IMPC KO phenotypes": 2016,
                  "OT animal-model": 2016}


def rs_ci(support, approved, n_boot=2000, seed=7):
    support = np.asarray(support, bool); approved = np.asarray(approved, bool)
    def _rs(sup, appr):
        s = appr[sup]; ns = appr[~sup]
        if s.size == 0 or ns.size == 0 or ns.mean() == 0:
            return np.nan
        return s.mean() / ns.mean()
    pt = _rs(support, approved)
    rng = np.random.default_rng(seed); idx = np.arange(support.size); boots = []
    for _ in range(n_boot):
        b = rng.choice(idx, idx.size, replace=True)
        boots.append(_rs(support[b], approved[b]))
    boots = np.array([x for x in boots if not np.isnan(x)])
    lo, hi = (np.percentile(boots, [2.5, 97.5]) if boots.size else (np.nan, np.nan))
    f = lambda x: round(x, 2) if x == x else np.nan
    return dict(rs=f(pt), lo=f(lo), hi=f(hi), n_support=int(support.sum()),
                n_not=int((~support).sum()),
                pct_appr_support=round(100*approved[support].mean(),1) if support.sum() else np.nan,
                pct_appr_not=round(100*approved[~support].mean(),1) if (~support).sum() else np.nan)


def esearch_count(term):
    url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json"
           "&rettype=count&term=" + urllib.parse.quote(term))
    try:
        d = json.load(urllib.request.urlopen(url, timeout=30))
        return int(d["esearchresult"]["count"])
    except Exception:
        return -1


def pretrial_pubmed(drugs):
    """drugs: DataFrame[drug_id, name, cutoff_year]. Returns {drug_id: has_pretrial_preclin(0/1/-1)}."""
    cache = {}
    if os.path.exists(PUBMED_CACHE):
        c = pd.read_csv(PUBMED_CACHE)
        cache = dict(zip(c.drug_id, c.n_pretrial))
    todo = drugs[~drugs.drug_id.isin(cache)]
    print(f"  PubMed pre-trial search: {len(cache)} cached, {len(todo)} to query")
    preclin = '(mice OR mouse OR "cell line" OR "in vitro" OR xenograft OR preclinical OR "animal model")'
    for j, (_, r) in enumerate(todo.iterrows()):
        nm = str(r["name"]).strip()
        cy = int(r["cutoff_year"]) if pd.notna(r["cutoff_year"]) else 9999
        if not nm or len(nm) < 3 or cy >= 9999:
            cache[r.drug_id] = -1; continue
        term = f'"{nm}"[tiab] AND {preclin} AND ("1900"[dp] : "{cy-1}"[dp])'
        cache[r.drug_id] = esearch_count(term)
        time.sleep(0.34)
        if j % 50 == 0:
            pd.DataFrame([{"drug_id": k, "n_pretrial": v} for k, v in cache.items()]).to_csv(PUBMED_CACHE, index=False)
    pd.DataFrame([{"drug_id": k, "n_pretrial": v} for k, v in cache.items()]).to_csv(PUBMED_CACHE, index=False)
    return cache


def main():
    if not DB:
        sys.exit("Set DATABASE_URL")
    import psycopg2, psycopg2.extras
    conn = psycopg2.connect(DB)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # program cohort with drug + target + first-trial + approval
    cur.execute("""
        SELECT p.program_id, p.drug_id, dt.target_id, d.display_name, d.normalized_name,
               p.first_trial_date, (po.approved_us OR po.approved_ex_us) AS approved
        FROM preclin.program p
        JOIN preclin.v_drug_target dt ON dt.drug_id = p.drug_id AND dt.role='primary'
        JOIN preclin.drug d ON d.drug_id = p.drug_id
        JOIN preclin.program_outcome po ON po.program_id = p.program_id
        WHERE p.highest_phase >= 2 AND p.first_trial_date IS NOT NULL
    """)
    progs = pd.DataFrame(cur.fetchall())
    progs["fy"] = pd.to_datetime(progs.first_trial_date).dt.year

    # drug-efficacy raw scores
    cur.execute("""SELECT subject_id AS drug_id, dimension, value_numeric AS score
                   FROM preclin.evidence_score WHERE subject_type='drug'
                   AND dimension IN ('drug_cell_efficacy','drug_rodent_efficacy','drug_nonrodent_efficacy')""")
    drugeff = pd.DataFrame(cur.fetchall())
    # structural raw RS straight from the clean view
    cur.execute("""SELECT dimension, n_supported, relative_success
                   FROM preclin.v_relative_success_clean
                   WHERE dimension ~ 'DepMap|IMPC|animal model'""")
    struct_raw = cur.fetchall()
    conn.close()

    rows = []

    # ---- drug-efficacy: raw RS from rubric ----
    for dim, lab in [("drug_cell_efficacy","Drug cell efficacy (rubric, raw)"),
                     ("drug_rodent_efficacy","Drug rodent efficacy (rubric, raw)"),
                     ("drug_nonrodent_efficacy","Drug non-rodent efficacy (rubric, raw)")]:
        e = drugeff[drugeff.dimension==dim][["drug_id","score"]]
        m = progs.merge(e, on="drug_id", how="left")
        sup = (m.score.fillna(0) >= 2).to_numpy()
        r = rs_ci(sup, m.approved.fillna(False).to_numpy(bool)); r.update(tier="drug_efficacy", measure=lab)
        rows.append(r)
        print(f"  {lab:38s} RS={r['rs']} [{r['lo']},{r['hi']}] n_sup={r['n_support']}")

    # ---- drug-efficacy: date-aware pre-trial PubMed presence ----
    # restrict to drugs that HAVE a rubric efficacy score, so the date-clean measure
    # is on the same ~hundreds of drugs as the raw rubric (comparable, and bounded).
    scored_drugs = set(drugeff.drug_id)
    dcohort = progs[progs.drug_id.isin(scored_drugs)].dropna(subset=["fy"]).copy()
    dcohort["name"] = dcohort.display_name.fillna(dcohort.normalized_name)
    dref = dcohort[["drug_id","name","fy"]].drop_duplicates("drug_id").rename(columns={"fy":"cutoff_year"})
    counts = pretrial_pubmed(dref)
    dcohort["n_pretrial"] = dcohort.drug_id.map(counts)
    ok = dcohort[dcohort.n_pretrial >= 0]
    sup = (ok.n_pretrial >= 1).to_numpy()
    r = rs_ci(sup, ok.approved.fillna(False).to_numpy(bool))
    r.update(tier="drug_efficacy", measure="Drug preclinical evidence PRE-first-trial (PubMed, date-clean)")
    rows.append(r)
    print(f"  {'Drug pre-trial preclinical (date-clean)':38s} RS={r['rs']} [{r['lo']},{r['hi']}] "
          f"n_sup={r['n_support']} (searchable n={len(ok)})")

    # ---- structural: raw RS (from view) + existence-floor coverage ----
    for rec in struct_raw:
        dim = rec["dimension"]
        lab = ("DepMap essentiality" if "DepMap" in dim else
               "IMPC KO phenotypes" if "IMPC" in dim else "OT animal-model")
        rows.append(dict(tier="structural", measure=f"{lab} (raw)",
                         rs=round(float(rec["relative_success"]),2) if rec["relative_success"] else np.nan,
                         lo=np.nan, hi=np.nan, n_support=int(rec["n_supported"]),
                         n_not=np.nan, pct_appr_support=np.nan, pct_appr_not=np.nan))
        floor = RESOURCE_FLOOR[lab]
        frac_post = (progs.fy >= floor).mean()
        print(f"  {lab+' (raw)':38s} RS={rec['relative_success']}  "
              f"| {100*frac_post:.0f}% of programs started >= {floor} (resource-existence floor)")

    out = pd.DataFrame(rows)[["tier","measure","rs","lo","hi","n_support","n_not",
                              "pct_appr_support","pct_appr_not"]]
    out.to_csv(os.path.join(DATA, "nuance_drug_structural.csv"), index=False)
    print("wrote data/nuance_drug_structural.csv")


if __name__ == "__main__":
    main()
