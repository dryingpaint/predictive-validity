"""Which preclinical evidence prevents which failure mode of a drug that reached the clinic.

    python -m report.failure_modes

Cohort: the evidence-line entries of report.evidence_analysis (US-developed phase entries 2008-2019), Phase 1-3. Each
entry's traced stop (report.evidence_analysis.traced_stops) is split into failure modes:

- never engaged: human evidence shows exposure or engagement too low (stop_engagement);
- dose: tolerability capped the dose, toxicity offset the benefit, or a PK, dose or formulation reason (stop_dose);
- and the drug engaged its target without benefit (stop_no_benefit), split by the target's later record and, where
  that record leaves the explanation open, the sourced verdict (preclin.stop_target_history):
    A not causal: drugs on the target worked only in unrelated diseases, or never worked though others were tried
      again, or the only attempt was judged not causal;
    B wrong patients or stage: the target worked in a related subtype or stage, or the verdict says so;
    C drug fell short: the verdict says the drug was inadequate where the target is sound;
    D trial could not answer: the verdict says the trial was inadequate;
    unresolved: no resolved target, an unclear verdict, no verdict, or a "not causal" verdict where another drug on
      the target worked in this disease, which the record contradicts.

For each evidence area line and its tiers (report.evidence_lines.AREAS), the adjusted risk ratio of each mode among
the entries the line applies to (report.section3.estimate, covariates as in the stop-risk figure), in three cohorts
(VARIANTS): every Phase 1-3 entry; the same without entries that stopped for a reason other than efficacy or safety,
which competes with the modes (a cause-specific comparison); and Phase 2 entries only. The precedent lines are left
out of modes A and B: the target's record that defines those modes is the approvals the precedent lines count.
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

OUT = os.path.join(frame.REPO, "report", "output", "failure_modes")
NOT_CAUSAL_FATES = ("worked_elsewhere_only", "never_worked_tried_again")
OPEN_FATES = ("worked_here", "worked_here_selected", "never_worked_single")
MODES = ["stop_engagement", "stop_dose", "mode_a", "mode_b", "mode_c", "mode_d", "mode_unresolved"]
MODE_NAMES = {"stop_engagement": "Never engaged", "stop_dose": "Dose or tolerability",
              "mode_a": "A. Target not causal here", "mode_b": "B. Wrong patients or stage",
              "mode_c": "C. Drug fell short", "mode_d": "D. Trial could not answer",
              "mode_unresolved": "Unresolved"}
BY_RECORD = ("mode_a", "mode_b")  # modes the target's approval record defines


def mode(fate: str | None, verdict: str | None) -> str:
    """The failure mode of one engaged-without-benefit stop from its target fate and verdict."""
    if fate in NOT_CAUSAL_FATES:
        return "mode_a"
    if fate == "worked_related" or verdict in ("wrong_patients", "wrong_stage_or_timing"):
        return "mode_b"
    if verdict == "drug_inadequate":
        return "mode_c"
    if verdict == "trial_inadequate":
        return "mode_d"
    if verdict == "target_not_causal" and fate == "never_worked_single":
        return "mode_a"
    return "mode_unresolved"


def with_modes(d: pd.DataFrame) -> pd.DataFrame:
    """d with one 0/1 column per engaged-without-benefit mode, and `competing`: 1 where the entry's traced stop is
    for a reason other than efficacy or safety."""
    t = stop_causes.load()
    other = dict(zip(t.key, t.likely.notna() & ~t.likely.isin(("efficacy", "safety"))))
    d = d.assign(competing=pd.Series(keys(d), index=d.index).map(other).fillna(False).astype(bool))
    h = frame.query("SELECT moiety_id, mondo_id, phase, target_fate, verdict FROM preclin.stop_target_history")
    of = dict(zip(keys(h), (mode(f, v) for f, v in zip(h.target_fate, h.verdict))))
    m = pd.Series(keys(d), index=d.index).map(of).where(d.stop_no_benefit > 0, None)
    m = m.where(m.notna() | (d.stop_no_benefit <= 0), "mode_unresolved")  # no target-history row
    return d.assign(**{c: m.eq(c).astype(float) for c in MODES if c.startswith("mode_")})


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
    for name, pick in VARIANTS.items():
        rows(pick(d)).to_csv(os.path.join(OUT, f"modes_{name}.csv"), index=False)
    n = {"entries": {name: int(len(pick(d))) for name, pick in VARIANTS.items()},
         "covariates": list(COVARS_23), "base_covariates": list(COVARS),
         "events": {c: int(d[c].sum()) for c in MODES},
         "events_phase23": {c: int(d.loc[d.phase >= 2, c].sum()) for c in MODES},
         "rate": {c: float(d[c].mean()) for c in MODES}}
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(jsonable(n), f, indent=1)
    print(json.dumps(n["events"]), flush=True)


if __name__ == "__main__":
    main()
