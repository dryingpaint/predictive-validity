#!/usr/bin/env python3
"""
Nuance / Section 5 — literature-tier date-cleaning.

Tests how much of the apparent predictive power of target-level cell (line_c_lit)
and animal (line_d_lit) LITERATURE evidence survives once we require the supporting
papers to predate the trial. These are the only cell/animal dims with stored PMIDs,
so they're the one tier we can date-clean directly from the DB.

Unit = program (drug x target x indication; has first/last_trial_date + outcome).
A target's "high" literature support (score >= 2) is kept in the cleaned versions
only if at least one cited paper was published before the program's cutoff:
  - strict cutoff  = program first_trial_date  (what was known before humans)
  - loose  cutoff  = program last_trial_date   (pre-final-readout)
Programs whose target's support is entirely post-cutoff are reclassified as
not-supported. We then compare Relative Success (RS = P(approved|support) /
P(approved|no support)) raw vs. cleaned, with bootstrap CIs.

PMID publication years come from NCBI eutils (cached to data/pmid_pubyear.csv).
Writes data/nuance_literature_dateclean.csv.
"""
from __future__ import annotations
import os, sys, time, json, urllib.request, urllib.parse
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
os.makedirs(DATA, exist_ok=True)
PMID_CACHE = os.path.join(DATA, "pmid_pubyear.csv")

DB = os.environ.get("DATABASE_URL")


def pull_cohort():
    import psycopg2, psycopg2.extras
    conn = psycopg2.connect(DB)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    # program-level cohort: primary target, dates, approval, phase
    cur.execute("""
        SELECT p.program_id, dt.target_id, p.first_trial_date, p.last_trial_date,
               p.highest_phase,
               (po.approved_us OR po.approved_ex_us) AS approved
        FROM preclin.program p
        JOIN preclin.v_drug_target dt ON dt.drug_id = p.drug_id AND dt.role = 'primary'
        JOIN preclin.program_outcome po ON po.program_id = p.program_id
        WHERE p.highest_phase >= 2 AND p.first_trial_date IS NOT NULL
    """)
    progs = pd.DataFrame(cur.fetchall())
    # target-level line_c / line_d scores + cited PMIDs
    cur.execute("""
        SELECT subject_id AS target_id, dimension, value_numeric AS score, citation_pmids
        FROM preclin.evidence_score
        WHERE subject_type='target' AND dimension IN ('line_c_lit','line_d_lit')
    """)
    ev = pd.DataFrame(cur.fetchall())
    # DEDUP (fix 2026-07-25, cf. PR #12): preclin.evidence_score holds ~4 identical
    # rows per (subject, dimension) from repeated ingest jobs. Without deduping, the
    # downstream left-merge on target_id fans out ~4x and distorts RS. Duplicates are
    # identical, so keep-first is exact.
    ev = ev.drop_duplicates(subset=["target_id", "dimension"], keep="first").reset_index(drop=True)
    conn.close()
    return progs, ev


import re
YEAR_RE = re.compile(r"\b(19[6-9]\d|20[0-2]\d)\b")


def _is_pmid(s):
    return s.isdigit() and 4 <= len(s) <= 9


def resolve_citation_years(cites):
    """Map each raw citation string -> publication year.

    The stored citation_pmids arrays are polluted: a mix of real PMIDs, raw DOIs,
    and free-text citations. Real PMIDs -> eutils; everything else -> regex the year
    out of the string (text citations and many DOIs carry a 4-digit year).
    Cached to data/pmid_pubyear.csv keyed by the raw string.
    """
    cache = {}
    if os.path.exists(PMID_CACHE):
        c = pd.read_csv(PMID_CACHE, dtype={"cite": str})
        cache = dict(zip(c.cite, c.year))
    cites = {str(x).strip() for x in cites if str(x).strip()}
    need = sorted(c for c in cites if c not in cache)
    pmids = [c for c in need if _is_pmid(c)]
    others = [c for c in need if not _is_pmid(c)]
    print(f"  citations: {len(cites)} unique | {len(cache)} cached | "
          f"{len(pmids)} PMIDs to fetch | {len(others)} non-PMID (regex year)")
    # PMIDs via eutils
    for i in range(0, len(pmids), 200):
        batch = pmids[i:i+200]
        url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed"
               "&retmode=json&id=" + ",".join(batch))
        try:
            d = json.load(urllib.request.urlopen(url, timeout=30))["result"]
            for pid in batch:
                rec = d.get(pid, {})
                yr = None
                for f in ("epubdate", "pubdate", "sortpubdate"):
                    v = str(rec.get(f, ""))
                    if v[:4].isdigit():
                        yr = int(v[:4]); break
                cache[pid] = yr
        except Exception as e:
            print(f"    eutils batch {i} failed: {e}")
            for pid in batch:
                cache.setdefault(pid, None)
        time.sleep(0.34)
    # non-PMIDs: regex a plausible year out of the string
    for c in others:
        m = YEAR_RE.findall(c)
        cache[c] = int(m[0]) if m else None
    pd.DataFrame([{"cite": k, "year": v} for k, v in cache.items()]).to_csv(PMID_CACHE, index=False)
    return {k: int(v) for k, v in cache.items() if pd.notna(v)}


def rs_ci(support, approved, n_boot=3000, seed=7):
    """Relative Success = P(appr|support) / P(appr|~support), with bootstrap CI."""
    support = np.asarray(support, bool); approved = np.asarray(approved, bool)
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
        b = rng.choice(idx, idx.size, replace=True)      # resample PAIRS together
        boots.append(_rs(support[b], approved[b]))
    boots = np.array([x for x in boots if not np.isnan(x)])
    lo, hi = (np.percentile(boots, [2.5, 97.5]) if boots.size else (np.nan, np.nan))
    return dict(rs=round(pt, 2) if pt==pt else np.nan,
                lo=round(lo, 2) if lo==lo else np.nan,
                hi=round(hi, 2) if hi==hi else np.nan,
                n_support=int(support.sum()), n_not=int((~support).sum()),
                pct_appr_support=round(100*approved[support].mean(),1) if support.sum() else np.nan,
                pct_appr_not=round(100*approved[~support].mean(),1) if (~support).sum() else np.nan)


def main():
    if not DB:
        sys.exit("Set DATABASE_URL")
    print("pulling cohort + evidence...")
    progs, ev = pull_cohort()
    print(f"  programs (Ph2+): {len(progs)}  | evidence rows: {len(ev)}")

    all_cites = set()
    for lst in ev.citation_pmids.dropna():
        all_cites.update(str(x).strip() for x in lst)
    print("resolving citation publication years...")
    yr = resolve_citation_years(all_cites)

    # per target x dimension: score, earliest datable cited-paper year (else +inf)
    ev = ev.copy()
    def _min_year(lst):
        ys = [yr[str(x).strip()] for x in (lst or []) if str(x).strip() in yr]
        return min(ys) if ys else np.inf
    ev["min_year"] = ev.citation_pmids.apply(_min_year)
    ev["has_paper"] = ev.citation_pmids.apply(lambda lst: bool(lst))
    ev["datable"] = ev.citation_pmids.apply(
        lambda lst: any(str(x).strip() in yr for x in (lst or [])))
    print(f"  targets with score>=2 & any datable citation: "
          f"{int(((ev.score>=2) & ev.datable).sum())} / {int((ev.score>=2).sum())}")

    rows = []
    progs["fy"] = pd.to_datetime(progs.first_trial_date).dt.year
    progs["ly"] = pd.to_datetime(progs.last_trial_date).dt.year
    for dim, label in [("line_c_lit", "Cell literature (line_c)"),
                       ("line_d_lit", "Animal literature (line_d)")]:
        e = ev[ev.dimension == dim][["target_id", "score", "min_year", "has_paper"]]
        m = progs.merge(e, on="target_id", how="left")
        score = m.score.fillna(0).to_numpy()
        miny = m.min_year.fillna(np.inf).to_numpy()                  # no datable paper -> +inf
        fy = m.fy.fillna(9999).to_numpy(); ly = m.ly.fillna(9999).to_numpy()
        appr = m.approved.fillna(False).to_numpy(bool)
        raw = score >= 2                                             # "high" support, any date
        clean_strict = raw & (miny < fy)                            # datable paper before first trial
        clean_loose  = raw & (miny < ly)                            # datable paper before last trial
        for cut, sup in [("raw (any date)", raw), ("clean_strict (pre-first-trial)", clean_strict),
                         ("clean_loose (pre-last-trial)", clean_loose)]:
            r = rs_ci(sup, appr); r.update(dimension=label, cutoff=cut)
            rows.append(r)
            print(f"  {label:26s} {cut:32s} RS={r['rs']} [{r['lo']},{r['hi']}] "
                  f"support n={r['n_support']} appr {r['pct_appr_support']}% vs {r['pct_appr_not']}%")

    out = pd.DataFrame(rows)[["dimension","cutoff","rs","lo","hi","n_support","n_not",
                              "pct_appr_support","pct_appr_not"]]
    out.to_csv(os.path.join(DATA, "nuance_literature_dateclean.csv"), index=False)
    print("wrote data/nuance_literature_dateclean.csv")


if __name__ == "__main__":
    main()
