"""Why Phase 2/3 programs stopped, after correcting and inferring the causes the registry leaves out.

    python -m report.stop_causes

Reads preclin.stop_cause (pipeline.stop_causes assemble), preclin.stop_signal and the held-out validation
decisions; writes report/output/stop_causes/numbers.json and programs.csv. Stops are traced for phase entries in
report.windows.TRACING; the numbers are for entries in the Section 1 headline window (report.windows.SECTION1),
with the recent window (RECENT) and each of SECTION1_PERIODS alongside. programs.csv holds every traced stop with its
phase entry, `headline`, and `shown`, the cause it takes in the figure (SHOWN), empty for a program whose development
continued.
"""
from __future__ import annotations

import json
import os

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from pipeline import llm
from pipeline.stop_causes import CAUSES, VALIDATE_METHOD
from pipeline.stops import REGISTRY_CAUSE, keys
from report import frame
from report.windows import RECENT, SECTION1, SECTION1_PERIODS
from report.section3 import jsonable

OUT = os.path.join(frame.REPO, "report", "output", "stop_causes")
MAIN_PHASES = (2, 3)  # the headline numbers; Phase 1 stops are reported apart
CAUSE_LABELS = {"efficacy": "Efficacy", "safety": "Safety", "pk_formulation": "PK or formulation",
                "business_strategic": "Business or strategic",
                "company_event": "Company acquired, merged, unfunded or closed",
                "operational": "Operational (enrollment, sites, supply, regulatory)",
                "positive_not_advanced": "Positive readout, not yet advanced",
                "development_continued": "Did not actually stop", "unknown": "Unknown"}
# The figure's categories: PK joins efficacy (an exposure failure is a failure to engage), company events join
# business, and a program whose development continued did not stop.
SHOWN = {"efficacy": "Efficacy or exposure (PK, dose, formulation)", "safety": CAUSE_LABELS["safety"],
         "business_strategic": "Business, strategic or company event", "operational": "Operational",
         "positive_not_advanced": CAUSE_LABELS["positive_not_advanced"], "unknown": CAUSE_LABELS["unknown"]}
SHOWN_AS = {"pk_formulation": "efficacy", "company_event": "business_strategic", "development_continued": None}


def load() -> pd.DataFrame:
    d = frame.query("""SELECT c.*, s.phase_entry, s.drug_continued_elsewhere, s.sponsor_active_after
                       FROM preclin.stop_cause c JOIN preclin.stop_signal s USING (moiety_id, mondo_id, phase)""")
    d["key"] = keys(d)
    d["phase_entry"] = pd.to_datetime(d.phase_entry)
    d["headline"] = within(d, SECTION1) & d.phase.isin(MAIN_PHASES)
    d["recorded_cause"] = d.recorded_reason.map(REGISTRY_CAUSE).fillna("unknown")
    d["likely"] = d.likely_cause.fillna(d.cause)
    d["shown"] = d.likely.map(lambda c: SHOWN_AS.get(c, c))
    return d


def within(d: pd.DataFrame, window) -> pd.Series:
    return d.phase_entry.between(pd.Timestamp(window[0]), pd.Timestamp(window[1]))


def distribution(d: pd.DataFrame, col: str, levels: list[str] = CAUSES) -> dict:
    counts = d[col].value_counts().reindex(levels, fill_value=0)
    return {c: {"n": int(n), "share": float(n / len(d))} for c, n in counts.items()}


def validation() -> dict:
    """Held-out agreement on the sample of the latest validation run (pipeline.stop_causes validate)."""
    run = frame.query("SELECT parameters->>'run' AS run FROM preclin.analysis_method WHERE method_id = %s",
                      (VALIDATE_METHOD,))
    if run.empty or run.run[0] is None:
        return {"n": 0}
    v = pd.DataFrame(llm.decisions(run.run[0]), columns=["key", "llm_decision_id", "parsed_output"])
    v["key"] = v.key.str.removesuffix("|heldout")
    reasons = frame.query("SELECT moiety_id, mondo_id, phase, recorded_reason FROM preclin.stop_cause "
                          "WHERE cause_source = 'registry'")
    reasons["key"] = keys(reasons)
    v = v.merge(reasons[["key", "recorded_reason"]], on="key")
    v["truth"] = v.recorded_reason.map(REGISTRY_CAUSE)
    v["cause"] = [o["cause"] for o in v.parsed_output]
    v["likely"] = [o["likely_cause"] for o in v.parsed_output]
    known = v[v.cause != "unknown"]
    return {"n": int(len(v)), "resolved": float((v.cause != "unknown").mean()),
            "cause_accuracy_resolved": float((known.cause == known.truth).mean()) if len(known) else None,
            "cause_kappa_resolved": float(cohen_kappa_score(known.truth, known.cause)) if len(known) > 1 else None,
            "likely_accuracy": float((v.likely == v.truth).mean()),
            "likely_kappa": float(cohen_kappa_score(v.truth, v.likely)),
            "by_truth": {t: {"n": int(len(g)), "likely_correct": float((g.likely == t).mean())}
                         for t, g in v.groupby("truth")},
            "precision_likely": {c: {"called": int(len(g)), "correct": float((g.truth == c).mean())}
                                 for c, g in v.groupby("likely") if c != "unknown"}}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    traced = load()
    traced.drop(columns=["sources"]).to_csv(os.path.join(OUT, "programs.csv"), index=False)
    main = traced[traced.phase.isin(MAIN_PHASES)]
    d = traced[traced.headline]
    infer = d[d.cause_source != "registry"]
    stopped = lambda x: x[x.shown.notna()]
    p1 = traced[within(traced, SECTION1) & traced.phase.eq(1)]
    p1_infer = p1[p1.cause_source != "registry"]
    n = {"traced": {"stops": int(len(main)), "phase1": int(traced.phase.eq(1).sum()),
                    "from": int(traced.phase_entry.min().year), "to": int(traced.phase_entry.max().year)},
         "window": {"from": SECTION1[0].year, "to": SECTION1[1].year},
         "recent": {"from": RECENT[0].year, "to": RECENT[1].year,
                    "stops": int(within(main, RECENT).sum()),
                    "shown": distribution(stopped(main[within(main, RECENT)]), "shown", list(SHOWN))},
         "by_period": {f"{lo.year}-{hi.year}": {"stops": int(len(stopped(x := main[within(main, (lo, hi))]))),
                                               "shown": distribution(stopped(x), "shown", list(SHOWN))}
                       for lo, hi in SECTION1_PERIODS},
         "shown": distribution(stopped(d), "shown", list(SHOWN)),
         "phase1": {"stops": int(len(p1)), "shown": distribution(stopped(p1), "shown", list(SHOWN)),
                    "recorded": distribution(p1, "recorded_cause"),
                    "inferred": {"programs": int(len(p1_infer)), "resolved": float((p1_infer.cause != "unknown").mean()),
                                 "likely_resolved": float((p1_infer.likely != "unknown").mean())}},
         "stops": int(len(d)),
         "recorded": distribution(d, "recorded_cause"), "evidence": distribution(d, "cause"),
         "likely": distribution(d, "likely"),
         "inferred": {"programs": int(len(infer)), "resolved": float((infer.cause != "unknown").mean()),
                      "resolved_n": int((infer.cause != "unknown").sum()),
                      "likely_resolved": float((infer.likely != "unknown").mean()),
                      "cause": infer.cause.value_counts().to_dict()},
         "signals": {c: {"sponsor_inactive": float((g.sponsor_active_after == False).mean())}  # noqa: E712
                     for c, g in infer.groupby("likely")},
         "validation": validation()}
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(n, f, indent=1, default=jsonable)


if __name__ == "__main__":
    main()
