"""Apply the SAME date-cleaning filter to genetics that #9/#12 applied to literature and
#9/#13 applied to drug-efficacy: count a target's genetic support only if it was
established BEFORE the program's first trial, then recompute Relative Success
present vs. time-gated, per dimension.

Dimensions (the three source-datable ones; OT-genetic/OT-somatic are present-day
black-box aggregates and cannot be dated from source — the #14 wall):
  - GWAS >=50   : each genome-wide-sig association dated by its study PMID's pub year
                  (public.gwas_associations.study_pmid -> data/gwas_pmid_year.csv, eutils).
                  Time-gated support = (# hits with pub-year < first_trial_year) >= 50.
  - ClinGen >=1 : Strong/Definitive gene-disease validity classifications, dated by
                  clingen_validity.classified_date. NOTE this is the CURATION date
                  (ClinGen formed ~2015), so it dates genetics LATE -> a CONSERVATIVE
                  (genetics-unfavourable) bound. Time-gated = (# strong classifications
                  with classified-year < first_trial_year) >= 1.
  - Mendelian >=5: no date in the DB. Mendelian disease-gene links are positional-
                  cloning/exome era (mostly pre-2015), so assumed pre-trial; validated on
                  a random sample (genetics_timegating_mendelian_sample).

RS present vs time-gated computed on IDENTICAL rows (T-I pairs with a first_trial_date),
so the delta is the pure date-cleaning effect. Present RS should reproduce #2's
per-dimension values (GWAS 1.12 / ClinGen 1.74 / Mendelian 1.49) as a sanity check.
"""
import os, csv
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

DB = os.environ["DATABASE_URL"]
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def rs_ci(support, approved, n_boot=2000, seed=7):
    support = np.asarray(support, bool); approved = np.asarray(approved, bool)
    rng = np.random.default_rng(seed)
    def _rs(sup, appr):
        ps = appr[sup].mean() if sup.any() else np.nan
        pn = appr[~sup].mean() if (~sup).any() else np.nan
        return ps / pn if pn else np.nan
    pt = _rs(support, approved)
    idx = np.arange(len(support)); boots = []
    for _ in range(n_boot):
        b = rng.choice(idx, len(idx), replace=True)
        boots.append(_rs(support[b], approved[b]))
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    return dict(rs=round(float(pt), 2), lo=round(float(lo), 2), hi=round(float(hi), 2),
                n_sup=int(support.sum()), n_not=int((~support).sum()),
                pct_sup=round(100*approved[support].mean(), 1) if support.any() else None,
                pct_not=round(100*approved[~support].mean(), 1) if (~support).any() else None)


def main():
    conn = psycopg2.connect(DB); cur = conn.cursor(cursor_factory=RealDictCursor)

    # pmid -> year (GWAS study dates)
    pyr = {r["pmid"]: int(r["year"]) for r in csv.DictReader(open(os.path.join(DATA, "gwas_pmid_year.csv")))
           if r["year"].isdigit()}

    # cohort T-I with a first_trial_date + present component counts + approval
    cur.execute("""
      SELECT ti.target_id, ti.indication_id,
             (ti.any_approved) AS approved,
             extract(year FROM ti.first_trial_date)::int AS fty,
             tw.gwas_n_sig, tw.clingen_n_strong, tw.mendelian_n
      FROM preclin.v_target_indication_program ti
      JOIN preclin.v_target_evidence_wide tw ON tw.target_id = ti.target_id
      WHERE ti.max_phase_reached >= 2 AND ti.first_trial_date IS NOT NULL
        AND EXISTS (SELECT 1 FROM preclin.program p JOIN preclin.drug d ON d.drug_id=p.drug_id
          WHERE p.indication_id=ti.indication_id AND EXISTS(
            SELECT 1 FROM preclin.v_drug_target dt WHERE dt.drug_id=p.drug_id AND dt.target_id=ti.target_id))
    """)
    coh = cur.fetchall()
    tids = tuple(sorted({r["target_id"] for r in coh}))

    # GWAS association years per target (genome-wide-sig)
    cur.execute("""SELECT target_id, study_pmid FROM public.gwas_associations
                   WHERE target_id IN %s AND p_value<=5e-8 AND study_pmid ~ '^[0-9]+$'""", (tids,))
    gyears = {}
    for r in cur.fetchall():
        y = pyr.get(r["study_pmid"])
        if y: gyears.setdefault(r["target_id"], []).append(y)

    # ClinGen Strong/Definitive classification years per target
    cur.execute("""SELECT target_id, classified_date FROM public.clingen_validity
                   WHERE target_id IN %s AND classification IN ('Strong','Definitive')""", (tids,))
    cgyears = {}
    for r in cur.fetchall():
        d = (r["classified_date"] or "")[:4]
        if d.isdigit():
            cgyears.setdefault(r["target_id"], []).append(int(d))
    conn.close()

    appr = np.array([bool(r["approved"]) for r in coh])
    print(f"cohort (T-I with first_trial_date): n={len(coh)}  base approval={appr.mean():.1%}\n")

    def support_arrays(dim):
        pres, tg = [], []
        for r in coh:
            t, fty = r["target_id"], r["fty"]
            if dim == "GWAS":
                pres.append((r["gwas_n_sig"] or 0) >= 50)
                tg.append(sum(1 for y in gyears.get(t, []) if y < fty) >= 50)
            elif dim == "ClinGen":
                pres.append((r["clingen_n_strong"] or 0) >= 1)
                tg.append(sum(1 for y in cgyears.get(t, []) if y < fty) >= 1)
            elif dim == "Mendelian":
                s = (r["mendelian_n"] or 0) >= 5
                pres.append(s); tg.append(s)  # assumed pre-trial (validated separately)
        return np.array(pres), np.array(tg)

    rows = []
    print(f"{'dimension':11} {'present RS':>26}   {'time-gated RS':>26}")
    for dim in ["GWAS", "ClinGen", "Mendelian"]:
        p, t = support_arrays(dim)
        rp, rt = rs_ci(p, appr), rs_ci(t, appr)
        print(f"{dim:11}  {rp['rs']:.2f} [{rp['lo']},{rp['hi']}] n_sup={rp['n_sup']:<5}"
              f"   {rt['rs']:.2f} [{rt['lo']},{rt['hi']}] n_sup={rt['n_sup']:<5}")
        rows.append(dict(dimension=dim, present_rs=rp['rs'], present_lo=rp['lo'], present_hi=rp['hi'],
                         present_n_sup=rp['n_sup'], timegated_rs=rt['rs'], timegated_lo=rt['lo'],
                         timegated_hi=rt['hi'], timegated_n_sup=rt['n_sup']))
    out = os.path.join(DATA, "genetics_timegating.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
