"""Why a drug that engaged its target and failed for efficacy did so: one failure mode per stop, under one of three
top-level groups (GROUPS, GROUP_OF):

- **Not causal** (`not_causal`): the target goes along with the disease but does not drive it.
- **Causal**: the target drives the disease, but the drug could not be dosed well enough (`drug_fell_short`), or the
  trial treated the wrong patients (`wrong_patients`) or at the wrong time (`wrong_time`). One primary reason per stop:
  a drug that fell short comes before wrong patients or wrong time.
- **Unclear**: the trial could not answer (`trial_could_not_answer`), or nothing settles it (`unresolved`).

The mode comes first from the target's record, what other drugs on it went on to do (preclin.stop_target_history,
pipeline.target_history), and where that record leaves the question open, from the verdict read from the program's
sources. A target that worked only in a related disease is split by RELATED_MODES, a reading of whether that disease
is a subgroup of this one (wrong patients), a stage of it (wrong time) or a different disease (not causal here).
"""
from __future__ import annotations

import os

import pandas as pd

from pipeline.stops import keys
from report import frame

ENGAGED_MODES = ["not_causal", "wrong_time", "wrong_patients", "drug_fell_short", "trial_could_not_answer",
                 "unresolved"]
GROUPS = {
    "not_causal": "The target goes along with the disease but does not drive it: a biomarker, readout or surrogate, or "
                  "the biology routes around it.",
    "causal": "The target drives the disease, but the drug could not be dosed well enough (too little engagement, or a "
              "therapeutic window capped by effects elsewhere), or the trial treated the wrong patients or at the "
              "wrong time.",
    "unclear": "The trial could not answer, or nothing settles whether the target drives the disease."}
GROUP_OF = {"not_causal": "not_causal", "drug_fell_short": "causal", "wrong_patients": "causal",
            "wrong_time": "causal", "trial_could_not_answer": "unclear", "unresolved": "unclear"}
# What a not_causal call rests on: the verdict read from the stop's own sources, or else the target's later record
NOT_CAUSAL_BASES = ("stop_evidence", "history")
RELATED_MODES = os.path.join(frame.REPO, "report", "audits", "related_success_modes.csv")


def engaged_mode(fate: str | None, verdict: str | None, related: str | None) -> str:
    """The failure mode of one engaged-without-benefit stop from its target fate, its verdict and, for a target that
    worked only in a related disease, the reading of that disease (RELATED_MODES)."""
    if fate in ("worked_elsewhere_only", "never_worked_tried_again"):
        return "not_causal"
    if verdict == "drug_inadequate":  # the drug falling short is the primary reason, before wrong patients or time
        return "drug_fell_short"
    if fate == "worked_related":
        return {"different_disease": "not_causal", "wrong_time": "wrong_time",
                "wrong_patients": "wrong_patients"}.get(related, "unresolved")
    if fate == "worked_here_selected":  # it worked here only in biomarker-selected patients, and this program did not select
        return "wrong_patients"
    by_verdict = {"wrong_patients": "wrong_patients", "wrong_stage_or_timing": "wrong_time",
                  "trial_inadequate": "trial_could_not_answer"}
    if verdict in by_verdict:
        return by_verdict[verdict]
    if verdict == "target_not_causal" and fate == "never_worked_single":
        return "not_causal"
    return "unresolved"  # no target, an unclear verdict, or "not causal" where another drug on the target worked here


def not_causal_basis(mode: str, verdict: str | None) -> str | None:
    """What a not_causal call rests on: "stop_evidence" when the stop's own sources read the target as not causal,
    else "history" (no drug on the target went on to work in this disease); None for any other mode."""
    if mode != "not_causal":
        return None
    return "stop_evidence" if verdict == "target_not_causal" else "history"


def engaged_modes() -> pd.DataFrame:
    """Every stop in preclin.stop_target_history with its key, target fate, verdict, failure mode, top-level group and,
    for a not_causal stop, the basis of the call."""
    h = frame.query("SELECT moiety_id, mondo_id, phase, target_fate, verdict FROM preclin.stop_target_history")
    h["key"] = keys(h)
    related = pd.read_csv(RELATED_MODES).set_index("key").category.to_dict()
    h["mode"] = [engaged_mode(f, v, related.get(k)) for f, v, k in zip(h.target_fate, h.verdict, h.key)]
    h["group"] = h["mode"].map(GROUP_OF)
    h["not_causal_basis"] = [not_causal_basis(m, v) for m, v in zip(h["mode"], h.verdict)]
    return h
