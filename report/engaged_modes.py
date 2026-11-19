"""Why a drug that engaged its target and failed for efficacy did so: one failure mode per stop, in three layers.

- **Target:** the target is not causal for the disease (`not_causal`), or it is causal but the program treated at the
  wrong time (`wrong_time`) or in the wrong patients (`wrong_patients`).
- **Drug:** the target is sound and the drug fell short (`drug_fell_short`).
- **Trial:** the trial could not answer (`trial_could_not_answer`).
- Otherwise `unresolved`.

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
MODE_LAYER = {"not_causal": "target", "wrong_time": "target", "wrong_patients": "target", "drug_fell_short": "drug",
              "trial_could_not_answer": "trial", "unresolved": "unresolved"}
RELATED_MODES = os.path.join(frame.REPO, "report", "audits", "related_success_modes.csv")


def engaged_mode(fate: str | None, verdict: str | None, related: str | None) -> str:
    """The failure mode of one engaged-without-benefit stop from its target fate, its verdict and, for a target that
    worked only in a related disease, the reading of that disease (RELATED_MODES)."""
    if fate in ("worked_elsewhere_only", "never_worked_tried_again"):
        return "not_causal"
    if fate == "worked_related":
        return {"different_disease": "not_causal", "wrong_time": "wrong_time",
                "wrong_patients": "wrong_patients"}.get(related, "unresolved")
    if fate == "worked_here_selected":  # it worked here only in biomarker-selected patients, and this program did not select
        return "wrong_patients"
    by_verdict = {"wrong_patients": "wrong_patients", "wrong_stage_or_timing": "wrong_time",
                  "drug_inadequate": "drug_fell_short", "trial_inadequate": "trial_could_not_answer"}
    if verdict in by_verdict:
        return by_verdict[verdict]
    if verdict == "target_not_causal" and fate == "never_worked_single":
        return "not_causal"
    return "unresolved"  # no target, an unclear verdict, or "not causal" where another drug on the target worked here


def engaged_modes() -> pd.DataFrame:
    """Every stop in preclin.stop_target_history with its key, target fate, verdict and failure mode."""
    h = frame.query("SELECT moiety_id, mondo_id, phase, target_fate, verdict FROM preclin.stop_target_history")
    h["key"] = keys(h)
    related = pd.read_csv(RELATED_MODES).set_index("key").category.to_dict()
    h["mode"] = [engaged_mode(f, v, related.get(k)) for f, v, k in zip(h.target_fate, h.verdict, h.key)]
    return h
