"""Target-disease hypotheses: one row per primary target and program disease that reached Phase 2, and what first
proposed each (issue #146).

    python -m pipeline.target_disease build        # preclin.target_disease from programs, targets and approvals
    python -m pipeline.target_disease provisional  # preclin.target_disease_origin, basis provisional

A pair is a human primary target of an entity (preclin.moiety_target) and the disease of one of the entity's programs
that entered Phase 2 or 3 with an industry trial (report.section1.phase_rows, any year). Its first entry is the
earliest such entry of any program on the target in the disease. It was validated at entry when an entity on the
target was FDA-approved for the disease, or a term within MONDO Lin 0.8 of it, before that date.

The provisional origin is the earliest evidence item for the pair that became public before the year of first entry,
from the same dated evidence and disease matching the report's evidence lines use (report.section3.evidence_index,
Lin >= 0.8), plus an approval of an entity on the target for another disease. It is a first answer: what first
proposed a target is often in a paper these sources do not cover, which the labelled origin reads.
"""
from __future__ import annotations

import argparse
from datetime import date

import pandas as pd
from psycopg2.extras import execute_values

from pipeline import llm
from pipeline.target_history import targets
from report import frame
from report.section1 import phase_rows
from report.section3 import ABSENT, CLOSE, evidence_index, neighbourhood

# Evidence families of report.section3.evidence_index -> origin, in the order that breaks a tie within one year
FAMILY_ORIGIN = {"mendelian": "human_genetics", "burden": "human_genetics", "gwas": "human_genetics",
                 "somatic": "tumour_genetics", "reactome": "curated_pathway", "impc": "mouse_genetics",
                 "mgi": "mouse_genetics", "expression": "diseased_tissue", "crispr": "cell_line_perturbation"}
EARLY = date(1990, 1, 1)  # phase entries are read from this date, before which the registry holds almost nothing

BUILD_METHOD = "target_disease@v1"
BUILD_DESCRIPTION = """Pairs: every (Ensembl gene of a human primary target in preclin.moiety_target, MONDO disease of
a program of that entity) where the program entered Phase 2 or 3 with an industry trial (report.section1.phase_rows,
window from 1990, skipped phases not counted). first_entry: the earliest such entry for the pair. programs: distinct
programs. validated_at_entry: an entity with a primary target on the gene has an FDA approval for a MONDO term within
Lin 0.8 of the disease (report.section3.neighbourhood) dated before first_entry (preclin.dev_program_approval)."""
PROVISIONAL_METHOD = "target_disease_provisional@v1"
PROVISIONAL_DESCRIPTION = """For each pair in preclin.target_disease: the first year each evidence family of
report.section3.evidence_index has the gene for a MONDO term within Lin 0.8 of the disease, and the first year an
entity on the gene was FDA-approved for a disease outside that neighbourhood. The origin is the earliest of these
before the year of first_entry (ties in the order of FAMILY_ORIGIN, then the approval); the secondary origin is the
next distinct one. No evidence before entry: unclear, with no year."""


def entries() -> pd.DataFrame:
    """program_id -> date of its first Phase 2 or Phase 3 entry, entered rather than skipped."""
    snap = frame.snapshot()
    rows = phase_rows(frame.programs(), frame.program_trials(), snap, window=(EARLY, snap))
    rows = rows[rows.phase.isin([2, 3]) & ~rows.credited]
    return rows.groupby("program_id").entry.min().rename("entry").reset_index()


def approvals() -> pd.DataFrame:
    """(moiety_id, mondo_id, approved_on) for every approved program with a date."""
    p = frame.programs()
    p = p[p.approved.eq("yes") & p.first_approval_date.notna()]
    return p.assign(approved_on=pd.to_datetime(p.first_approval_date))[["moiety_id", "mondo_id", "approved_on"]]


def pairs() -> pd.DataFrame:
    """One row per (ensembl_id, mondo_id): symbol, first_entry, programs, validated_at_entry."""
    progs = frame.programs()[["program_id", "moiety_id", "mondo_id"]].dropna()
    e = progs.merge(entries(), on="program_id")
    t = targets()[["moiety_id", "ens"]].drop_duplicates()
    d = e.merge(t, on="moiety_id")
    out = d.groupby(["ens", "mondo_id"]).agg(first_entry=("entry", "min"), programs=("program_id", "nunique")) \
        .reset_index().rename(columns={"ens": "ensembl_id"})
    out["first_entry"] = pd.to_datetime(out.first_entry)
    nb = neighbourhood()
    approved = approvals().merge(t, on="moiety_id")
    by_gene = {g: list(zip(x.mondo_id, x.approved_on)) for g, x in approved.groupby("ens")}
    out["validated_at_entry"] = [any(m in nb.terms(d_, CLOSE) and when < first
                                     for m, when in by_gene.get(g, ()))
                                 for g, d_, first in zip(out.ensembl_id, out.mondo_id, out.first_entry)]
    sym = frame.query("SELECT ensembl_id, min(symbol) AS symbol FROM public.targets WHERE ensembl_id IS NOT NULL "
                      "GROUP BY 1").set_index("ensembl_id").symbol
    out["symbol"] = out.ensembl_id.map(sym)
    return out


def provisional_origin(family_years: dict[str, int], other_approval: int, entry_year: int) \
        -> tuple[str, int | None, str | None]:
    """The origin, its year and the secondary origin from the first year of each evidence family for the pair and of
    an approval on the target for another disease (ABSENT when there is none)."""
    order = [*FAMILY_ORIGIN, "earlier_drug_other_disease"]
    years = {**family_years, "earlier_drug_other_disease": other_approval}
    seen: list[tuple[int, int, str]] = []
    for rank, key in enumerate(order):
        y = years.get(key, ABSENT)
        if y < entry_year:
            seen.append((y, rank, FAMILY_ORIGIN.get(key, key)))
    distinct: list[tuple[int, str]] = []
    for y, _, origin in sorted(seen):
        if origin not in {o for _, o in distinct}:
            distinct.append((y, origin))
    if not distinct:
        return "unclear", None, None
    return distinct[0][1], distinct[0][0], distinct[1][1] if len(distinct) > 1 else None


def origins(hub: pd.DataFrame) -> pd.DataFrame:
    """The provisional origin of every pair in hub."""
    idx, _ = evidence_index()
    nb = neighbourhood()
    t = targets()[["moiety_id", "ens"]].drop_duplicates()
    approved = approvals().merge(t, on="moiety_id")
    by_gene = {g: list(zip(x.mondo_id, x.approved_on.dt.year)) for g, x in approved.groupby("ens")}
    out = []
    for g, d, first in zip(hub.ensembl_id, hub.mondo_id, pd.to_datetime(hub.first_entry)):
        close = nb.terms(d, CLOSE)
        fams = {}
        for fam, terms in idx.get(g, {}).items():
            ys = [years[0] for m, years in terms.items() if m in close]
            if ys:
                fams[fam] = min(ys)
        other = min((y for m, y in by_gene.get(g, ()) if m not in close), default=ABSENT)
        origin, year, secondary = provisional_origin(fams, other, first.year)
        out.append({"ensembl_id": g, "mondo_id": d, "origin": origin, "origin_year": year,
                    "secondary_origin": secondary})
    return pd.DataFrame(out)


def build(_args) -> None:
    hub = pairs()
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, BUILD_METHOD, "Target-disease hypotheses that reached Phase 2", BUILD_DESCRIPTION,
                          ["preclin.dev_program", "preclin.dev_program_trial", "preclin.moiety_target",
                           "preclin.dev_program_approval", "MONDO"], {"close": CLOSE, "from": str(EARLY)})
        execute_values(cur, """INSERT INTO preclin.target_disease AS t
                                 (ensembl_id, mondo_id, symbol, first_entry, programs, validated_at_entry, method_id)
                               VALUES %s
                               ON CONFLICT (ensembl_id, mondo_id) DO UPDATE SET symbol = EXCLUDED.symbol,
                                 first_entry = EXCLUDED.first_entry, programs = EXCLUDED.programs,
                                 validated_at_entry = EXCLUDED.validated_at_entry, method_id = EXCLUDED.method_id""",
                       [(r.ensembl_id, r.mondo_id, r.symbol, r.first_entry.date(), int(r.programs),
                         bool(r.validated_at_entry), BUILD_METHOD) for r in hub.itertuples()], page_size=2000)
        # a pair that no longer qualifies goes, with its provisional origin, unless it carries a labelled one
        cur.execute("CREATE TEMP TABLE keep (ensembl_id text, mondo_id text) ON COMMIT DROP")
        execute_values(cur, "INSERT INTO keep VALUES %s", list(zip(hub.ensembl_id, hub.mondo_id)), page_size=5000)
        cur.execute("""DELETE FROM preclin.target_disease_origin o WHERE basis = 'provisional'
                         AND NOT EXISTS (SELECT 1 FROM keep k WHERE (k.ensembl_id, k.mondo_id) = (o.ensembl_id, o.mondo_id))""")
        cur.execute("""DELETE FROM preclin.target_disease t
                       WHERE NOT EXISTS (SELECT 1 FROM keep k WHERE (k.ensembl_id, k.mondo_id) = (t.ensembl_id, t.mondo_id))
                         AND NOT EXISTS (SELECT 1 FROM preclin.target_disease_origin o
                                         WHERE (o.ensembl_id, o.mondo_id) = (t.ensembl_id, t.mondo_id))""")
        conn.commit()
    print(f"{len(hub):,} pairs; {int(hub.validated_at_entry.sum()):,} validated at entry", flush=True)


def provisional(_args) -> None:
    hub = frame.query("SELECT ensembl_id, mondo_id, first_entry FROM preclin.target_disease")
    o = origins(hub)
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, PROVISIONAL_METHOD, "Provisional origin of each target-disease hypothesis",
                          PROVISIONAL_DESCRIPTION, ["preclin.target_disease", "preclin.ot_evidence_tiers",
                                                    "preclin.dev_program_approval", "MONDO"],
                          {"close": CLOSE, "order": list(FAMILY_ORIGIN)})
        cur.execute("DELETE FROM preclin.target_disease_origin WHERE basis = 'provisional'")
        execute_values(cur, """INSERT INTO preclin.target_disease_origin
                                 (ensembl_id, mondo_id, basis, origin, origin_year, secondary_origin, method_id)
                               VALUES %s""",
                       [(r.ensembl_id, r.mondo_id, "provisional", r.origin,
                         None if pd.isna(r.origin_year) else int(r.origin_year), r.secondary_origin, PROVISIONAL_METHOD)
                        for r in o.itertuples()], page_size=2000)
        conn.commit()
    print(o.origin.value_counts().to_string(), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build").set_defaults(fn=build)
    sub.add_parser("provisional").set_defaults(fn=provisional)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
