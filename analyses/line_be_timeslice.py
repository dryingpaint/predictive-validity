#!/usr/bin/env python3
"""
Full time-slice of the LLM literature evidence lines B-E (Section 5, extension).

PR #9 (analyses/nuance_literature_dateclean.py, MODEL_SYSTEM_PREDICTIVENESS.md)
date-cleaned only the CELL (line_c_lit) and ANIMAL (line_d_lit) literature lines.
This script does the same treatment RIGOROUSLY for ALL FOUR LLM literature lines:

    line_b_lit  = mechanistic literature
    line_c_lit  = cell / in-vitro literature
    line_d_lit  = animal / in-vivo literature
    line_e_lit  = pharmacodynamic (PD) literature

WHY DATE-CLEAN (the enemy is leakage): each line_*_lit score carries a
`citation_pmids` array (the papers behind the score) and an `extracted_at` of
2026-07-23 -- the CLASSIFICATION-JOB date, NOT publication date. Approved drugs
accrue confirmatory papers AFTER the fact, so the raw scores are hindsight-
contaminated. We resolve each PMID's real publication date via NCBI eutils and
recompute a time-sliced score that only counts papers published before the trial.

BUILDS ON MELISSA'S CONSTRUCTS:
  - "High" support threshold = score >= 2, exactly as in her RS view
    preclin.v_relative_success_clean (db/07_analysis_views.sql: "Line C/D/E lit
    high (>=2)"). NB her published view does NOT contain a line_b_lit row -- its
    "B_mechanistic" rows are tractability/tau/PPI. line_b_lit is added here.
  - Relative Success RS = P(approve|support) / P(approve|no support), her metric.

BUILDS ON PR #9's CONSTRUCTS (reused, not re-derived):
  - eutils esummary date-resolution + regex-year fallback for polluted citations,
    cached to data/pmid_pubyear.csv (this run seeds from #9's cache).
  - Two-cutoff design: strict = pre-first-trial, loose = pre-last-trial.
  - Program unit + bootstrap-CI rs_ci(). Trial dates live on programs, not on
    T-I pairs, so date-cleaning is only possible at the program unit -- this is
    the same operationalization of "the Phase-2+ T-I cohort" #9 used.

IMPROVEMENT over #9: the evidence_score table stores ~4 IDENTICAL duplicate rows
per (target, dimension) (same job re-inserted; different evidence_id/extracted_at).
#9 merged without deduping, fanning programs out ~4x non-uniformly. We dedup to
one row per (target, dimension) first.

DATA-QUALITY FINDINGS reported by this script (not hidden):
  1. citation_pmids are POLLUTED -- a mix of real PMIDs, raw DOIs, and free-text.
     Only PMIDs are eutils-datable; DOIs/free-text get a year only if one is
     embedded (regex). We report the datable fraction PER LINE (no silent drops).
  2. For every target, all four lines B/C/D/E carry the IDENTICAL citation array
     (the LLM attached a target-level paper set, then scored each line off it).
     So the lines differ only in which targets clear score>=2 and, given the
     shared paper pool, share the same earliest-datable-paper year per target.
  3. line_b_lit is near-saturated (>=2 for ~99% of targets), so its raw
     support-vs-no-support contrast is degenerate; reported honestly.

Writes: data/line_be_timeslice.csv, data/line_be_datable_fraction.csv,
        updates data/pmid_pubyear.csv.
"""
from __future__ import annotations
import os, sys, time, json, re, urllib.request
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
os.makedirs(DATA, exist_ok=True)
PMID_CACHE = os.path.join(DATA, "pmid_pubyear.csv")
DB = os.environ.get("DATABASE_URL")

LINES = [
    ("line_b_lit", "Mechanistic literature (line_b)"),
    ("line_c_lit", "Cell literature (line_c)"),
    ("line_d_lit", "Animal literature (line_d)"),
    ("line_e_lit", "PD literature (line_e)"),
]

YEAR_RE = re.compile(r"\b(19[6-9]\d|20[0-2]\d)\b")


def _is_pmid(s: str) -> bool:
    return s.isdigit() and 4 <= len(s) <= 9


# ---------------------------------------------------------------- DB pull
def pull_cohort():
    import psycopg2, psycopg2.extras
    conn = psycopg2.connect(DB)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    # program-level cohort: primary target, dates, approval, phase (== PR #9)
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
    # all four LLM literature lines: score + cited PMIDs, at target level
    cur.execute("""
        SELECT subject_id AS target_id, dimension,
               value_numeric AS score, citation_pmids
        FROM preclin.evidence_score
        WHERE subject_type='target'
          AND dimension IN ('line_b_lit','line_c_lit','line_d_lit','line_e_lit')
    """)
    ev = pd.DataFrame(cur.fetchall())
    conn.close()
    return progs, ev


def dedup_evidence(ev: pd.DataFrame) -> pd.DataFrame:
    """One row per (target_id, dimension). The table stores ~4 identical dup rows
    per (target, dimension) (same score + citation array, different evidence_id).
    Take max score (defensive; dups agree) and the citation list from the max row."""
    ev = ev.copy()
    ev["_cites_tuple"] = ev.citation_pmids.apply(
        lambda lst: tuple(str(x).strip() for x in (lst or []) if str(x).strip()))
    ev = ev.sort_values(["target_id", "dimension", "score"])
    out = (ev.groupby(["target_id", "dimension"], as_index=False)
             .agg(score=("score", "max"), cites=("_cites_tuple", "last")))
    return out


# ---------------------------------------------------------------- date resolution
def resolve_citation_years(cites):
    """Map each raw citation string -> publication year. (Reused from PR #9.)
    Real PMIDs -> NCBI eutils esummary; DOIs / free-text -> regex a 4-digit year.
    Cached to data/pmid_pubyear.csv keyed by the raw string."""
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
    for c in others:  # DOI / free-text: regex a plausible year out of the string
        m = YEAR_RE.findall(c)
        cache[c] = int(m[0]) if m else None
    pd.DataFrame([{"cite": k, "year": v} for k, v in cache.items()]).to_csv(
        PMID_CACHE, index=False)
    return {k: int(v) for k, v in cache.items() if pd.notna(v)}


# ---------------------------------------------------------------- RS + bootstrap
def rs_ci(support, approved, n_boot=3000, seed=7):
    """Relative Success = P(appr|support) / P(appr|~support), bootstrap CI.
    (Reused verbatim from PR #9 for comparability.)"""
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
    return dict(rs=round(pt, 2) if pt == pt else np.nan,
                lo=round(lo, 2) if lo == lo else np.nan,
                hi=round(hi, 2) if hi == hi else np.nan,
                n_support=int(support.sum()), n_not=int((~support).sum()),
                pct_appr_support=round(100*approved[support].mean(), 1) if support.sum() else np.nan,
                pct_appr_not=round(100*approved[~support].mean(), 1) if (~support).sum() else np.nan)


# ---------------------------------------------------------------- main
def main():
    if not DB:
        sys.exit("Set DATABASE_URL")
    print("pulling cohort + evidence...")
    progs, ev = pull_cohort()
    print(f"  programs (Ph2+, dated): {len(progs)}  | raw evidence rows: {len(ev)}")
    ev = dedup_evidence(ev)
    print(f"  deduped evidence rows (1 per target x line): {len(ev)}  "
          f"| distinct targets: {ev.target_id.nunique()}")

    # cross-line citation identity (data-quality finding #2)
    piv = ev.pivot_table(index="target_id", columns="dimension",
                         values="cites", aggfunc="first")
    ident = 0; tot = 0
    for _, row in piv.iterrows():
        vals = [row.get(d) for d, _ in LINES if isinstance(row.get(d), tuple)]
        if len(vals) == 4:
            tot += 1
            if len(set(vals)) == 1:
                ident += 1
    print(f"  targets where all 4 lines share IDENTICAL citations: {ident}/{tot}")

    all_cites = set()
    for t in ev.cites:
        all_cites.update(t)
    print("resolving citation publication years...")
    yr = resolve_citation_years(all_cites)

    n_pmid = sum(1 for c in all_cites if _is_pmid(c))
    n_other = len(all_cites) - n_pmid
    n_pmid_dated = sum(1 for c in all_cites if _is_pmid(c) and c in yr)
    n_other_dated = sum(1 for c in all_cites if not _is_pmid(c) and c in yr)
    print(f"  citation datability overall: {len(all_cites)} unique | "
          f"PMIDs {n_pmid_dated}/{n_pmid} datable | "
          f"non-PMID {n_other_dated}/{n_other} datable (regex year)")

    def _min_year(t):
        ys = [yr[c] for c in (t or ()) if c in yr]
        return min(ys) if ys else np.inf
    def _datable(t):
        return any(c in yr for c in (t or ()))
    ev["min_year"] = ev.cites.apply(_min_year)
    ev["datable"] = ev.cites.apply(_datable)
    ev["has_paper"] = ev.cites.apply(lambda t: len(t) > 0)

    progs["fy"] = pd.to_datetime(progs.first_trial_date).dt.year
    progs["ly"] = pd.to_datetime(progs.last_trial_date).dt.year

    # SELECTION-CONFOUND accounting: only 579 of the cohort's ~951 primary targets
    # were LLM-scored at all. Programs whose target was never scored fall into the
    # "not supported" baseline by fillna(0), so raw RS partly measures "was this
    # target studied enough to be scored" (a popularity/selection artifact), not
    # graded evidence. We therefore ALSO report RS restricted to the scored subset.
    scored_targets = set(ev.target_id.unique())
    n_scored_prog = int(progs.target_id.isin(scored_targets).sum())
    print(f"\n  selection check: {n_scored_prog}/{len(progs)} programs "
          f"({100*n_scored_prog/len(progs):.0f}%) have a primary target in the "
          f"LLM-scored set; the other {len(progs)-n_scored_prog} auto-fall into "
          f"'not supported'.")

    rows, frac_rows = [], []
    for dim, label in LINES:
        e = ev[ev.dimension == dim][["target_id", "score", "min_year",
                                     "has_paper", "datable"]]
        m = progs.merge(e, on="target_id", how="left")
        in_scored = m.target_id.isin(scored_targets).to_numpy()
        score = m.score.fillna(0).to_numpy()
        miny = m.min_year.fillna(np.inf).to_numpy()        # no datable paper -> +inf
        fy = m.fy.fillna(9999).to_numpy()
        ly = m.ly.fillna(9999).to_numpy()
        appr = m.approved.fillna(False).to_numpy(bool)
        has_paper = m.has_paper.fillna(False).to_numpy(bool)
        datable = m.datable.fillna(False).to_numpy(bool)

        raw = score >= 2                                   # "high" support, any date
        clean_strict = raw & (miny < fy)                   # datable paper pre-first-trial
        clean_loose = raw & (miny < ly)                    # datable paper pre-last-trial

        # datable fraction, at the PROGRAM level of this cohort (reported, no silent drop)
        n_high = int(raw.sum())
        n_high_haspaper = int((raw & has_paper).sum())
        n_high_datable = int((raw & datable).sum())
        n_not = int((~raw).sum())
        n_not_neverscored = int(((~raw) & (~in_scored)).sum())
        frac_rows.append(dict(
            dimension=label, n_programs=len(m), n_high_support=n_high,
            n_high_with_any_paper=n_high_haspaper,
            n_high_datable=n_high_datable,
            pct_high_datable=round(100*n_high_datable/n_high, 1) if n_high else np.nan,
            n_not_support=n_not, n_not_never_scored=n_not_neverscored,
            pct_not_never_scored=round(100*n_not_neverscored/n_not, 1) if n_not else np.nan))
        print(f"\n  {label}: high-support programs={n_high} | "
              f"with a paper={n_high_haspaper} | datable={n_high_datable} "
              f"({round(100*n_high_datable/max(n_high,1),1)}%) | "
              f"not-support={n_not} of which never-scored={n_not_neverscored} "
              f"({round(100*n_not_neverscored/max(n_not,1),1)}%)")

        for cut, sup in [("raw (any date)", raw),
                         ("clean_strict (pre-first-trial)", clean_strict),
                         ("clean_loose (pre-last-trial)", clean_loose)]:
            # (a) full cohort (baseline includes never-scored targets)
            r = rs_ci(sup, appr); r.update(dimension=label, cutoff=cut,
                                           population="full_cohort")
            rows.append(r)
            print(f"    {cut:32s} [full ] RS={r['rs']} [{r['lo']},{r['hi']}] "
                  f"support n={r['n_support']} appr {r['pct_appr_support']}% "
                  f"vs {r['pct_appr_not']}%")
            # (b) scored-subset only (removes the selection artifact)
            rs2 = rs_ci(sup[in_scored], appr[in_scored])
            rs2.update(dimension=label, cutoff=cut, population="scored_subset")
            rows.append(rs2)
            print(f"    {cut:32s} [scr'd] RS={rs2['rs']} [{rs2['lo']},{rs2['hi']}] "
                  f"support n={rs2['n_support']} appr {rs2['pct_appr_support']}% "
                  f"vs {rs2['pct_appr_not']}%")

    out = pd.DataFrame(rows)[["dimension", "cutoff", "population", "rs", "lo", "hi",
                              "n_support", "n_not",
                              "pct_appr_support", "pct_appr_not"]]
    out.to_csv(os.path.join(DATA, "line_be_timeslice.csv"), index=False)
    frac = pd.DataFrame(frac_rows)
    frac.to_csv(os.path.join(DATA, "line_be_datable_fraction.csv"), index=False)
    print("\nwrote data/line_be_timeslice.csv + data/line_be_datable_fraction.csv")


if __name__ == "__main__":
    main()
