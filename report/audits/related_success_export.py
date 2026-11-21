"""Export the input of the related-success reading (report/audits/related_success_modes.md).

    python report/audits/related_success_export.py

Every headline Phase 2/3 efficacy stop whose drug engaged its target without benefit and whose target worked only in
a disease MONDO rates as related (preclin.stop_target_history target_fate worked_related), with the program's disease
and the related successes of other drugs on the target. Writes report/audits/related_success_pairs.csv. Needs the
stop-cause build (report/output/stop_causes/programs.csv).
"""
import os

import pandas as pd

from pipeline.stops import keys
from pipeline.target_history import History, cohort
from report import frame

OUT = os.path.join(frame.REPO, "report", "audits", "related_success_pairs.csv")


def main() -> None:
    p = pd.read_csv(os.path.join(frame.REPO, "report", "output", "stop_causes", "programs.csv"))
    c = cohort()
    c = c[c.key.isin(set(p.loc[p.headline, "key"]))]
    h = frame.query("SELECT moiety_id, mondo_id, phase, target_fate, verdict FROM preclin.stop_target_history")
    h["key"] = keys(h)
    c = c.merge(h[["key", "target_fate", "verdict"]], on="key")
    c = c[c.target_fate.eq("worked_related")]
    hist = History()
    names = frame.query("SELECT moiety_id, name FROM preclin.moiety").set_index("moiety_id").name.to_dict()
    label = frame.query("SELECT term_id, label FROM preclin.ontology_term WHERE ontology = 'MONDO'") \
        .set_index("term_id").label.to_dict()
    rows = []
    for r in c.itertuples():
        _, related, _, _ = hist.split(int(r.moiety_id), r.mondo_id)
        wins = sorted({(label.get(s.mondo_id, s.mondo_id), names.get(s.moiety_id, s.moiety_id), s.kind,
                        "biomarker-selected" if s.selected else "") for s in related})
        rows.append({"key": r.key, "drug": names.get(r.moiety_id), "phase": r.phase,
                     "disease": label.get(r.mondo_id, r.mondo_id), "verdict": r.verdict,
                     "related_successes": " | ".join(f"{d} ({m}, {k}{', ' + b if b else ''})"
                                                     for d, m, k, b in wins[:6])})
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"{len(rows)} pairs -> {OUT}")


if __name__ == "__main__":
    main()
