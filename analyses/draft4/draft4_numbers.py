"""Numbers Draft 4 and the target-selection issues quote that python -m report does not produce.

    .venv/bin/python analyses/draft4/draft4_numbers.py

Read-only. Needs a report build first (report/output/stop_causes/programs.csv). Each section prints one claim's numbers:

1. multi_target: drugs acting on more than one primary target against single-target drugs, relative success to
   approval and adjusted Phase 2 advance (S4), US-developed entries 2008-2019 (Draft 4 Discussion; #148).
2. misreporting: of headline Phase 2/3 stops, the traced cause behind each registry reason (Draft 4, "The registry
   misreports why programs stop").
3. atlas_burden: diseases of the model-system atlas with no tracked mechanism whose efficacy model matched before the
   patient result, and their 2021 WHO DALYs (Draft 4 abstract and model-systems section).
4. pre_entry_sources: for novel small molecules entering Phase 2, the share with a PubMed paper or a name-matched
   patent dated before entry, approved against never approved (#146, #151).
5. chembl_coverage: how many distinct targets ChEMBL measured each Phase 2 small molecule against (#148).
"""
import os

import pandas as pd

from report import frame
from report.evidence_analysis import loa_rows
from report.evidence_lines import build
from report.section1 import phase_rows
from report.section2 import relative_success
from report.section3 import COVARS, estimate
from report.windows import SECTION1

ATLAS = os.path.join(frame.REPO, "analyses", "model-system-atlas")


def multi_target() -> None:
    mt = frame.query("SELECT moiety_id, count(DISTINCT target_id) n FROM preclin.moiety_target WHERE is_primary GROUP BY 1")
    d = build()
    d = d.assign(precedent=d.precedent.fillna(0), target=d.target.fillna("entity " + d.moiety_id.astype(str)))
    d = d.merge(mt, on="moiety_id")
    d["multi"] = (d.n > 1).astype(float)
    rows = phase_rows(frame.programs(), frame.program_trials(), frame.snapshot(), window=SECTION1)
    keys = d[["program_id", "entry_date", "multi"]].drop_duplicates(["program_id", "entry_date"]).rename(
        columns={"multi": "x"})
    rs = relative_success(loa_rows(d, rows[rows.us_site]).merge(keys, on=["program_id", "entry_date"]), "x")
    s4 = estimate(d[d.phase == 2], "s4", "multi", COVARS)
    print(f"multi_target: share {d.multi.mean():.3f}; small molecules "
          f"{d.loc[d.modality.eq('small_molecule'), 'multi'].mean():.3f}; relative success {rs['rs']:.2f} "
          f"({rs['rs_lo']:.2f}-{rs['rs_hi']:.2f}); Phase 2 S4 RR {s4['rr']:.2f} ({s4['lo']:.2f}-{s4['hi']:.2f})")


def misreporting() -> None:
    p = pd.read_csv(os.path.join(frame.REPO, "report", "output", "stop_causes", "programs.csv"))
    h = p[p.headline & p.phase.isin([2, 3]) & p.shown.notna()]
    for reason in ("sponsor decision, unspecified", "business or strategic (explicit)",
                   "completed, no results posted, no reason stated"):
        x = h[h.registry_reason.eq(reason)]
        print(f"misreporting: {reason}: {len(x)} stops; traced cause "
              f"{(x.shown.value_counts(normalize=True).round(2)).to_dict()}")


def atlas_burden() -> None:
    g = pd.read_csv(os.path.join(ATLAS, "glance.csv"))
    b = pd.read_csv(os.path.join(ATLAS, "lists", "burden.csv"))
    eff = g[g.question == "efficacy"].groupby("mondo_id").status.apply(lambda s: (s == "same").any()) \
        .rename("has_eff").reset_index().merge(b, on="mondo_id")
    total = eff.dropna(subset=["who_codes"]).drop_duplicates("who_codes")
    covered = set(eff.loc[eff.has_eff, "who_codes"].dropna())
    lacking = eff[~eff.has_eff & ~eff.who_codes.isin(covered)].dropna(subset=["who_codes"]).drop_duplicates("who_codes")
    print(f"atlas_burden: {(~eff.has_eff).sum()} of {len(eff)} diseases lack a matched efficacy model; "
          f"{lacking.dalys_2021.sum() / 1e6:.0f}M of {total.dalys_2021.sum() / 1e6:.0f}M DALYs "
          f"({lacking.dalys_2021.sum() / total.dalys_2021.sum():.0%})")


def pre_entry_sources() -> None:
    e = frame.query("""SELECT moiety_id, min(entry_year) y, bool_or(novel) novel FROM preclin.evidence_entry
                       WHERE phase = 2 AND modality = 'small_molecule' GROUP BY 1""")
    e = e[e.novel.fillna(False)]
    progs = frame.programs()
    e["approved"] = e.moiety_id.isin(set(progs.loc[progs.approved.eq("yes"), "moiety_id"]))
    ids = tuple(int(x) for x in e.moiety_id)
    pat = frame.query("""SELECT h.moiety_id, min(r.year) pat_y FROM preclin.literature_hit h
                         JOIN preclin.literature_record r USING (record_id)
                         WHERE r.source = 'PAT' AND h.moiety_id IN %s GROUP BY 1""", (ids,))
    pm = frame.query("""SELECT h.moiety_id, min(p.year) pm_y FROM preclin.literature_hit h
                        JOIN public.publications p ON p.pmid::text = h.record_id::text
                        WHERE h.source = 'pubmed' AND h.moiety_id IN %s GROUP BY 1""", (ids,))
    d = e.merge(pat, on="moiety_id", how="left").merge(pm, on="moiety_id", how="left")
    d["patent"], d["pubmed"] = d.pat_y.lt(d.y), d.pm_y.lt(d.y)
    d["either"] = d.patent | d.pubmed
    print(f"pre_entry_sources: {len(d)} novel small molecules; share before entry by approval\n"
          f"{d.groupby('approved')[['pubmed', 'patent', 'either']].mean().round(2).to_string()}")


def chembl_coverage() -> None:
    d = frame.query("""
        WITH sm AS (SELECT DISTINCT moiety_id FROM preclin.evidence_entry WHERE modality = 'small_molecule' AND phase = 2),
        prof AS (SELECT cm.moiety_id, count(DISTINCT a.target_chembl_id) n FROM preclin.chembl_moiety cm
                 JOIN preclin.chembl_activity a ON a.parent_chembl_id = cm.parent_chembl_id GROUP BY 1)
        SELECT count(*) entities, count(p.n) any_data, sum((p.n >= 10)::int) ge10, sum((p.n >= 50)::int) ge50,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY coalesce(p.n, 0)) median_targets
        FROM sm LEFT JOIN prof p USING (moiety_id)""")
    print(f"chembl_coverage: {d.iloc[0].to_dict()}")


if __name__ == "__main__":
    for step in (multi_target, misreporting, atlas_burden, pre_entry_sources, chembl_coverage):
        step()
