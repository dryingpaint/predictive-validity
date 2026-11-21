"""Which preclinical evidence prevents which failure mode of a drug that reached the clinic.

    python -m report.failure_modes

Cohort: the evidence-line entries of report.evidence_analysis (US-developed phase entries 2008-2019), Phase 1-3. Each
entry's traced stop (report.evidence_analysis.traced_stops) is split into failure modes:

- never reached: tolerability capped the dose, toxicity offset the benefit, a PK, dose or formulation reason, or human
  evidence shows exposure or engagement too low (stop_not_reached);
- and the drug engaged its target without benefit (stop_no_benefit), split into the failure modes of
  report.engaged_modes: the target not causal, the wrong time, the wrong patients, the drug fell short, the
  trial could not answer, unresolved.

For each evidence area line and its tiers (report.evidence_lines.AREAS), the adjusted risk ratio of each mode among
the entries the line applies to (report.section3.estimate, covariates as in the stop-risk figure), in three cohorts
(VARIANTS): every Phase 1-3 entry; the same without entries that stopped for a reason other than efficacy or safety,
which competes with the modes (a cause-specific comparison); and Phase 2 entries only. The precedent lines are left
out of the target-layer modes: the target's record that defines them is the approvals the precedent lines count.
Writes report/output/failure_modes/modes_<variant>.csv and numbers.json.
"""
from __future__ import annotations

import json
import os

import pandas as pd

from pipeline.stops import keys
from report import frame, stop_causes
from report.evidence_analysis import COVARS_23, exposed_enough, traced_stops
from report.evidence_lines import APPLIES, AREAS, build
from report.section3 import COVARS, describe, estimate, jsonable
from report.engaged_modes import ENGAGED_MODES, engaged_modes

OUT = os.path.join(frame.REPO, "report", "output", "failure_modes")
MODES = ["stop_not_reached", *(f"mode_{m}" for m in ENGAGED_MODES)]
BY_RECORD = ("mode_not_causal", "mode_wrong_time", "mode_wrong_patients")  # modes the target's approval record defines


def with_modes(d: pd.DataFrame) -> pd.DataFrame:
    """d with one 0/1 column per engaged-without-benefit mode (report.engaged_modes), and `competing`: 1
    where the entry's traced stop is for a reason other than efficacy or safety."""
    t = stop_causes.load()
    other = dict(zip(t.key, t.likely.notna() & ~t.likely.isin(("efficacy", "safety"))))
    d = d.assign(competing=pd.Series(keys(d), index=d.index).map(other).fillna(False).astype(bool))
    h = engaged_modes()
    m = pd.Series(keys(d), index=d.index).map(dict(zip(h.key, h["mode"]))).where(d.stop_no_benefit > 0, None)
    m = m.where(m.notna() | (d.stop_no_benefit <= 0), "unresolved")  # no target-history row
    return d.assign(**{f"mode_{c}": m.eq(c).astype(float) for c in ENGAGED_MODES})


def rows(d: pd.DataFrame) -> pd.DataFrame:
    out = []
    for area, (line, tiers) in AREAS.items():
        for level, ln in (("area", line), *(("tier", t) for t in tiers)):
            if not ln.column:
                continue
            elig = d[ln.column].notna() & APPLIES[ln.applies](d)
            x = d.loc[elig].assign(x=d.loc[elig, ln.column].astype(float))
            desc = describe(x.assign(any_outcome=1.0), "any_outcome", "x")
            row = {"area": area, "level": level, "label": ln.label, "column": ln.column, "exposed": desc["n"],
                   "eligible": int(elig.sum()), "estimated": exposed_enough(desc)}
            covars = tuple(c for c in COVARS_23 if not (area == "precedent" and c == "precedent"))
            for outcome in MODES if row["estimated"] else ():
                if area == "precedent" and outcome in BY_RECORD:
                    continue
                r = estimate(x, outcome, "x", covars)
                row |= {f"{outcome}_{k}": r.get(k) for k in ("ppv", "rate_without", "rr", "lo", "hi", "p")}
            out.append(row)
    return pd.DataFrame(out)


VARIANTS = {"all": lambda d: d, "cause_specific": lambda d: d[~d.competing], "phase2": lambda d: d[d.phase.eq(2)]}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    d = build()
    d = d.assign(precedent=d.precedent.fillna(0), target=d.target.fillna("entity " + d.moiety_id.astype(str)))
    d = with_modes(traced_stops(d[d.phase.between(1, 3)]))
    tables = {name: rows(pick(d)) for name, pick in VARIANTS.items()}
    for name, t in tables.items():
        t.to_csv(os.path.join(OUT, f"modes_{name}.csv"), index=False)
    n = {"entries": {name: int(len(pick(d))) for name, pick in VARIANTS.items()},
         "lines": {name: {r["column"]: {k: v for k, v in r.items() if k.endswith(("_rr", "_lo", "_hi"))}
                          for r in t.to_dict("records")} for name, t in tables.items()},
         "covariates": list(COVARS_23), "base_covariates": list(COVARS),
         "events": {c: int(d[c].sum()) for c in MODES},
         "events_phase23": {c: int(d.loc[d.phase >= 2, c].sum()) for c in MODES},
         "rate": {c: float(d[c].mean()) for c in MODES}}
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(jsonable(n), f, indent=1)
    print(json.dumps(n["events"]), flush=True)


if __name__ == "__main__":
    main()
