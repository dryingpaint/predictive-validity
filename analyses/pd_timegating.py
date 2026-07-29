#!/usr/bin/env python3
"""
Does human PD engagement still add ON TOP OF genetics once it is TIME-GATED?

`genetic_conditioning.py` found that the one non-genetic evidence type with an
independent positive signal in both genetics strata is human PD engagement
(line_e_lit) — but that score is present-day and LLM-extracted, so it may be
hindsight (approved drugs accrue confirmatory PD papers). PR #12
(line_be_timeslice.py) showed the MARGINAL line-E signal falls from RS ~2.3 raw to
~1.2–1.3 once date-cleaned. This script asks the CONDITIONING version: recompute
PD's within-stratum effect using a TIME-GATED PD flag and compare to present-day.

TIME-GATED PD := line_e_lit score >= 2 AND the earliest datable supporting citation
was published BEFORE the program's first trial. Citation dates come from PR #12's
cached data/pmid_pubyear.csv (eutils esummary; DOIs/free-text via regex year).
Reuses genetic_conditioning.py for the genetics strength score, evidence binarizing,
adjusted fit, and bootstrap RS — same cohort, so present-day vs time-gated is
apples-to-apples on the identical programs.

Conservative by construction: a high-support program whose citations are undatable
(#12: ~26% of high-support) or never LLM-scored falls to time-gated = 0. Reported.

Run:  DATABASE_URL='postgresql://...' python3 analyses/pd_timegating.py
Out:  data/pd_timegating.csv   (present-day vs time-gated PD: marginal RS + adjusted OR, per stratum)
"""
from __future__ import annotations
import os
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

import genetic_conditioning as gc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "pd_timegating.csv")

# same cohort as genetic_conditioning, plus program_id / target_id (both cheap columns
# off the same view). first_trial_date is pulled SEPARATELY and merged in pandas —
# joining preclin.program back onto this heavy view re-materializes it and is very slow.
SQL = f"""
SELECT w.program_id, w.target_id,
       w.outcome_broad, w.clingen_n_strong, w.mendelian_n, w.ot_genetic_max,
       tw.ot_somatic_score_max, w.nelson_tier, w.gwas_n_sig,
       w.line_c_lit, w.line_d_lit, w.line_e_lit, w.impc_n_phenotypes,
       w.ot_animal_model_max, w.tractability_sm, w.gnomad_loeuf, w.depmap_pan_essential,
       w.therapeutic_area, w.target_tdl, w.modality
FROM preclin.v_program_evidence_wide w
LEFT JOIN preclin.v_target_evidence_wide tw ON tw.target_id = w.target_id
JOIN preclin.drug d ON d.drug_id = w.drug_id
WHERE w.target_id IS NOT NULL AND w.outcome_broad IN {gc.BROAD_SET}
  AND w.highest_phase >= 2 AND d.is_placebo IS NOT TRUE
"""

DATES_SQL = "SELECT program_id, first_trial_date FROM preclin.program"

LINE_E_SQL = """
SELECT subject_id AS target_id, value_numeric AS score, citation_pmids
FROM preclin.evidence_score
WHERE subject_type='target' AND dimension='line_e_lit'
"""


def load():
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("Set DATABASE_URL.")
    import psycopg2
    import warnings
    warnings.filterwarnings("ignore")
    with psycopg2.connect(url) as conn:
        raw = pd.read_sql(SQL, conn)
        dates = pd.read_sql(DATES_SQL, conn)
        ev = pd.read_sql(LINE_E_SQL, conn)
    raw = raw.merge(dates, on="program_id", how="left")
    return raw, ev


def line_e_min_year(ev):
    """Dedup line_e evidence to one row per target; return {target_id: earliest datable
    citation year} using PR #12's cached pmid_pubyear.csv (+ eutils for any misses)."""
    ev = ev.copy()
    ev["cites"] = ev.citation_pmids.apply(
        lambda lst: tuple(str(x).strip() for x in (lst or []) if str(x).strip()))
    ev = (ev.sort_values(["target_id", "score"])
            .groupby("target_id", as_index=False)
            .agg(score=("score", "max"), cites=("cites", "last")))
    allc = set()
    for t in ev.cites:
        allc.update(t)
    yr = gc_resolve(allc)               # {raw cite -> year}
    def _min(t):
        ys = [yr[c] for c in t if c in yr]
        return min(ys) if ys else np.inf
    ev["min_year"] = ev.cites.apply(_min)
    ev["e_high"] = ev.score >= 2
    ev["datable"] = ev.cites.apply(lambda t: any(c in yr for c in t))
    return ev[["target_id", "e_high", "min_year", "datable"]]


def gc_resolve(cites):
    """Port of line_be_timeslice.resolve_citation_years: cache-first PMID->year."""
    import re
    import json
    import time
    import urllib.request
    cache_path = os.path.join(HERE, "..", "data", "pmid_pubyear.csv")
    cache = {}
    if os.path.exists(cache_path):
        c = pd.read_csv(cache_path, dtype={"cite": str})
        cache = dict(zip(c.cite, c.year))
    YEAR_RE = re.compile(r"\b(19[6-9]\d|20[0-2]\d)\b")
    is_pmid = lambda s: s.isdigit() and 4 <= len(s) <= 9
    cites = {str(x).strip() for x in cites if str(x).strip()}
    need = sorted(c for c in cites if c not in cache)
    pmids = [c for c in need if is_pmid(c)]
    others = [c for c in need if not is_pmid(c)]
    print(f"  citations: {len(cites)} unique | {len(cache)} cached | "
          f"{len(pmids)} PMIDs to fetch | {len(others)} non-PMID")
    for i in range(0, len(pmids), 200):
        batch = pmids[i:i + 200]
        url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed"
               "&retmode=json&id=" + ",".join(batch))
        try:
            d = json.load(urllib.request.urlopen(url, timeout=30))["result"]
            for pid in batch:
                rec = d.get(pid, {})
                yv = None
                for f in ("epubdate", "pubdate", "sortpubdate"):
                    v = str(rec.get(f, ""))
                    if v[:4].isdigit():
                        yv = int(v[:4]); break
                cache[pid] = yv
        except Exception as e:
            print(f"    eutils batch {i} failed: {e}")
            for pid in batch:
                cache.setdefault(pid, None)
        time.sleep(0.34)
    for c in others:
        m = YEAR_RE.findall(c)
        cache[c] = int(m[0]) if m else None
    pd.DataFrame([{"cite": k, "year": v} for k, v in cache.items()]).to_csv(cache_path, index=False)
    return {k: int(v) for k, v in cache.items() if pd.notna(v)}


def stratum_pd(d, pdcol):
    """Marginal RS + adjusted OR for pdcol within each genetics-strength stratum.
    Adjusted model = full multivariate with pdcol swapped in for pd_lit."""
    others = [t for t in gc.EV_TERMS if t != "pd_lit"]
    ev = " + ".join(others + [pdcol])
    res = {}
    for gval, name in [(1, "Gpos"), (0, "Gneg")]:
        sub = d[d.gpres == gval]
        rec = {}
        r = gc.rs_ci(sub, pdcol)
        if r is not None:
            rec.update(rs=round(r[0], 3), rslo=round(r[1], 3), rshi=round(r[2], 3), nsup=r[3])
        m, conf = gc.fit_adj(f"approved ~ {ev}", sub)
        if m is not None and pdcol in m.params.index:
            OR = np.exp(m.params[pdcol]); ci = np.exp(m.conf_int().loc[pdcol])
            rec.update(aOR=round(OR, 3), lo=round(ci[0], 3), hi=round(ci[1], 3),
                       p=float(m.pvalues[pdcol]), adj=conf)
        res[name] = rec
    return res


def main():
    raw, ev = load()
    e = line_e_min_year(ev)
    raw = raw.merge(e, on="target_id", how="left")
    raw["fy"] = pd.to_datetime(raw["first_trial_date"], errors="coerce").dt.year

    # genetics score / strata / other-evidence binaries via gc.prep (index preserved),
    # then attach PD present-day (gc's pd_lit) + time-gated on the SAME index by join.
    base = gc.prep(raw)
    aux = pd.DataFrame(index=raw.index)
    aux["fy"] = raw["fy"]
    aux["e_datable"] = raw["datable"].fillna(False)
    aux["min_year"] = raw["min_year"].fillna(np.inf)
    base = base.join(aux)
    # time-gated PD := present-day PD support (gc pd_lit) AND earliest paper pre-first-trial.
    # (subset of present-day, so the comparison is on the identical programs)
    base["pd_tg"] = ((base.pd_lit == 1) & (base.min_year < base.fy)).astype(int)

    n_high = int((base.pd_lit == 1).sum())
    n_tg = int((base.pd_tg == 1).sum())
    n_datable_high = int(((base.pd_lit == 1) & base.e_datable).sum())
    print(f"Cohort: {len(base):,} Ph2+ non-placebo programs  base approval {base.approved.mean():.1%}")
    print(f"  PD present-day (line_e>=2): {n_high:,}  | datable citation: {n_datable_high:,} "
          f"({100*n_datable_high/max(n_high,1):.0f}%)  | TIME-GATED (paper<first-trial): {n_tg:,}")
    print(f"  G+ n={int(base.gpres.sum()):,}  G- n={int((1-base.gpres).sum()):,}")

    rows = []
    for lab, col in [("PD present-day", "pd_lit"), ("PD time-gated", "pd_tg")]:
        r = stratum_pd(base, col)
        print(f"\n{lab}:")
        for name in ("Gpos", "Gneg"):
            x = r[name]
            pstr = f"{x['p']:.1e}" if "p" in x else "n/a"
            print(f"  {name}: marginal RS={x.get('rs')} [{x.get('rslo')},{x.get('rshi')}] "
                  f"n+={x.get('nsup')} | adj OR={x.get('aOR')} [{x.get('lo')},{x.get('hi')}] p={pstr}")
            rows.append(dict(pd_def=lab, stratum=name, **x))
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
