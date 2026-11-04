"""Step 4: what the "engaged" verdicts rest on once the readout kind (layer 1) and its anchor (layer 2) are
known, overall and within the report's cohort, and the report's not-engaged share under stricter readings.

    .venv/bin/python analyses/engagement-readouts/analysis.py

Reads labels.csv, readouts.csv, vocabulary.csv, step3_scope.csv, anchors.csv, cohort.csv. Prints the tables
recorded in RESULTS_STEP4.md.
"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from pipeline.stops import pillar_code, subcause  # noqa: E402  (the report's own failure-code reading)
ANCHORED = {"genetics", "direct_assay", "prior_drug"}
ENGAGED = ("adequate", "inferred_adequate")


def load() -> pd.DataFrame:
    l = pd.read_csv(os.path.join(HERE, "labels.csv"), dtype=str).fillna("")
    r = pd.read_csv(os.path.join(HERE, "readouts.csv"), dtype=str).fillna("")
    v = pd.read_csv(os.path.join(HERE, "vocabulary.csv"), dtype=str).fillna("")
    s = pd.read_csv(os.path.join(HERE, "step3_scope.csv"), dtype=str).fillna("")[["content_sha", "family"]]
    c = pd.read_csv(os.path.join(HERE, "cohort.csv"), dtype=str).fillna("")
    a = (pd.read_csv(os.path.join(HERE, "anchors.csv"), dtype=str).fillna("")
         if os.path.exists(os.path.join(HERE, "anchors.csv")) else pd.DataFrame(columns=["family", "anchor", "anchor_year", "specificity"]))
    kind = {x.readout_canonical: (x.kind_final or x.kind_majority) for x in v.itertuples()}
    d = l.merge(r.drop(columns=["key"]), on="content_sha", how="left").merge(s, on="content_sha", how="left")
    d = d.merge(a[["family", "anchor", "anchor_year", "specificity"]], on="family", how="left")
    d = d.merge(c.rename(columns={"phase": "cohort_phase"}), on="key", how="left")
    d["kind"] = [kind.get(cn, k) if cn else k for cn, k in zip(d.readout_canonical.fillna(""), d.readout_kind.fillna(""))]
    d["entry_year"] = pd.to_datetime(d.entry, errors="coerce").dt.year
    d["anchor_year_n"] = pd.to_numeric(d.anchor_year, errors="coerce")
    d["in_cohort"] = d.entry.ne("") & d.cohort_phase.isin(["2", "3"]) & d.entry_year.between(2008, 2019)
    d["dose_limited"] = d.dose_limited.eq("True")
    d["code"] = pillar_code(d)
    d["subcause"] = subcause(d.code, d.engagement)

    def basis(x):
        if x.engagement != "adequate":
            return ""
        if not isinstance(x.family, str) or x.family == "":
            return "no_readout" if x.kind in ("none", "exposure_only", "clinical_response", "") else "direct"
        if not isinstance(x.anchor, str) or x.anchor == "":
            return "pending"
        if x.anchor in ANCHORED:
            if pd.notna(x.anchor_year_n) and pd.notna(x.entry_year) and x.anchor_year_n > x.entry_year:
                return "anchored_after_entry"
            return "anchored"
        return x.anchor  # pathway_only / unknown
    d["basis"] = [basis(x) for x in d.itertuples()]
    return d


def table(d: pd.DataFrame, title: str) -> None:
    a = d[d.engagement == "adequate"]
    print(f"\n## {title}: {len(a)} measured-engaged programs by what the verdict rests on\n")
    order = ["direct", "anchored", "anchored_after_entry", "pathway_only", "unknown", "no_readout", "pending"]
    vc = a.basis.value_counts()
    print("| basis | n | share |\n|---|---|---|")
    for b in order:
        if vc.get(b, 0):
            print(f"| {b} | {vc[b]} | {100 * vc[b] / len(a):.0f}% |")


def not_engaged_share(d: pd.DataFrame) -> None:
    """The report's Section 1 number, not engaged among mechanism-tested efficacy failures (subcause not_engaged vs
    engaged_no_benefit after pillar_code), under stricter readings of what counts as engaged: programs whose
    'engaged' verdict rests on a weaker basis move to no_engagement_data, as the report's own 'direct pillar
    evidence only' variant does with inferred engagement."""
    c = d[d.in_cohort]
    ne = int((c.subcause == "not_engaged").sum())
    eng = c.subcause == "engaged_no_benefit"
    print(f"\n## Not-engaged share of mechanism-tested, report cohort (Phase 2/3 entries 2008–2019, n = {len(c)})\n")
    print("| reading of 'engaged' | engaged, no benefit | not engaged | not engaged, of tested | no engagement data |\n|---|---|---|---|---|")
    for name, keep in [("report: measured or inferred", pd.Series(True, index=c.index)),
                       ("measured only (inferred counted as no data)", c.engagement.eq("adequate")),
                       ("measured, direct or anchored before entry", c.basis.isin(["direct", "anchored"])),
                       ("measured, direct only", c.basis.eq("direct"))]:
        n_eng = int((eng & keep).sum())
        print(f"| {name} | {n_eng} | {ne} | {100 * ne / (n_eng + ne):.0f}% | {int((c.subcause == 'no_engagement_data').sum()) + int((eng & ~keep).sum())} |")


def main():
    d = load()
    table(d, "All labelled stops")
    table(d[d.in_cohort], "Report cohort")
    a = d[(d.engagement == "adequate") & d.in_cohort]
    print("\n## Report cohort: basis x failure code (after pillar_code)\n", pd.crosstab(a.basis, a.code))
    print("\n## Report cohort: basis x shown in this disease\n", pd.crosstab(a.basis, a.engagement_in_disease))
    print("\n## Report cohort: basis x shown before the index trial\n", pd.crosstab(a.basis, a.engagement_before_index))
    not_engaged_share(d)
    pending = int((d.basis == "pending").sum())
    if pending:
        print(f"\n({pending} measured-engaged programs await an anchor)")


if __name__ == "__main__":
    main()
