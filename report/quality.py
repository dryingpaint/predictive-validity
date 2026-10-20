"""Quality of the LLM-built labels the report rests on.

    python -m report.quality

1. Independent re-derivation of seeded samples by agents working from the
   primary sources (label audit: .cache/label_audit/results.json; trial
   outcomes: .cache/outcome_audit/results.json; program approvals by stratum:
   .cache/approval_audit/results.json): accuracy with Wilson 95% intervals,
   counting correct and acceptable verdicts as agreement.
2. Agreement of the trial stop reasons (preclin.trial_outcome) with the two
   earlier classifications of the same trials: the Sonnet why_stopped labels
   and the GPT-5.6 multi-axis rescore (preclin.classification), on a common
   coarse taxonomy, as Cohen's kappa.
"""
from __future__ import annotations

import json
import math
import os

from sklearn.metrics import cohen_kappa_score

from report import frame

OUT = os.path.join(frame.REPO, "report", "output", "quality")
AUDIT = os.path.join(frame.REPO, ".cache", "label_audit", "results.json")
OUTCOME_AUDIT = os.path.join(frame.REPO, ".cache", "outcome_audit", "results.json")
OUTCOME_AXES = ("stop_reason", "primary_endpoint", "safety_signal", "efficacy_failure")
APPROVAL_AUDIT = os.path.join(frame.REPO, ".cache", "approval_audit", "results.json")

NEW = {"efficacy_futility": "efficacy", "safety_tolerability": "safety", "pk_pd_or_formulation": "pk_formulation",
       "business_portfolio": "business", "competitive_landscape": "business",
       "sponsor_decision_unspecified": "unspecified", "enrollment_feasibility": "enrollment_operational",
       "operational_or_site": "enrollment_operational", "regulatory": "regulatory",
       "manufacturing_supply": "manufacturing", "covid19": "covid", "replaced_by_new_protocol": "planned_other",
       "objectives_met_or_early_success": "planned_other", "other": "unknown", "not_stated": "unknown"}
SONNET = {"efficacy": "efficacy", "safety": "safety", "pk_pd_formulation": "pk_formulation",
          "commercial_strategic": "business", "competitive_landscape": "business",
          "enrollment_operational": "enrollment_operational", "regulatory_admin": "regulatory",
          "manufacturing_supply": "manufacturing", "covid": "covid", "planned_termination": "planned_other",
          "unclear": "unknown"}
GPT = {"efficacy": "efficacy", "unfavorable_benefit_risk": "efficacy", "safety": "safety",
       "pk_pd_formulation": "pk_formulation", "commercial_strategic": "business", "competitive_landscape": "business",
       "enrollment_operational": "enrollment_operational", "regulatory_administrative": "regulatory",
       "manufacturing_supply": "manufacturing", "pandemic_external": "covid",
       "planned_or_not_applicable": "planned_other", "positive_efficacy_progression": "planned_other",
       "unknown": "unknown"}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return math.nan, math.nan
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def stop_reason_agreement() -> dict:
    new = frame.query("""SELECT nct_id, stop_reason FROM preclin.trial_outcome
                         WHERE execution <> 'completed'""").set_index("nct_id").stop_reason
    old = frame.query("""SELECT subject_key AS nct_id, classifier_model, category,
                                coalesce(raw_output ? 'error', false) AS failed
                         FROM preclin.classification
                         WHERE classifier_task IN ('why_stopped', 'trial_stoppage_rescore')""")
    out = {}
    for model, mapping in [("claude-sonnet", SONNET), ("gpt-5.6-terra", GPT)]:
        o = old[(old.classifier_model == model) & ~old.failed].set_index("nct_id").category
        both = new.index.intersection(o.index)
        for unspecified in ("business", "unknown"):
            a = new[both].map(NEW).replace("unspecified", unspecified)
            b = o[both].map(mapping)
            keep = a.notna() & b.notna()
            a, b = a[keep], b[keep]
            out[f"{model}|unspecified_as_{unspecified}"] = {
                "n": int(len(a)), "agreement": float((a == b).mean()), "kappa": float(cohen_kappa_score(a, b)),
                "efficacy_kappa": float(cohen_kappa_score(a == "efficacy", b == "efficacy"))}
    return out


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    numbers = {"stop_reason_agreement": stop_reason_agreement()}
    if os.path.exists(AUDIT):
        audits = {}
        for r in json.load(open(AUDIT)):
            ok = r["n_correct"] + r["n_acceptable"]
            lo, hi = wilson(ok, r["n"])
            audits[r["task"]] = {"n": r["n"], "correct": r["n_correct"], "acceptable": r["n_acceptable"],
                                 "wrong": r["n_wrong"], "accuracy": ok / r["n"], "lo": lo, "hi": hi}
        numbers["label_audit"] = audits
    if os.path.exists(OUTCOME_AUDIT):
        trials = json.load(open(OUTCOME_AUDIT))["trials"]
        audits = {}
        for axis in OUTCOME_AXES:
            verdicts = [t[f"{axis}_verdict"] for t in trials if t[f"{axis}_verdict"] != "not_applicable"]
            ok = sum(v in ("correct", "acceptable") for v in verdicts)
            lo, hi = wilson(ok, len(verdicts))
            audits[axis] = {"n": len(verdicts), "correct": verdicts.count("correct"),
                            "acceptable": verdicts.count("acceptable"), "wrong": verdicts.count("wrong"),
                            "accuracy": ok / len(verdicts), "lo": lo, "hi": hi}
        numbers["outcome_audit"] = audits
    if os.path.exists(APPROVAL_AUDIT):
        programs = json.load(open(APPROVAL_AUDIT))["programs"]
        audits = {}
        for stratum in sorted({p["stratum"] for p in programs}) + ["all"]:
            group = [p for p in programs if stratum in ("all", p["stratum"])]
            for axis in ("approved", "date"):
                verdicts = [p[f"{axis}_verdict"] for p in group if p[f"{axis}_verdict"] != "not_applicable"]
                if not verdicts:
                    continue
                ok = sum(v in ("correct", "acceptable") for v in verdicts)
                lo, hi = wilson(ok, len(verdicts))
                audits[f"{stratum}.{axis}"] = {"n": len(verdicts), "wrong": verdicts.count("wrong"),
                                               "accuracy": ok / len(verdicts), "lo": lo, "hi": hi}
        numbers["approval_audit"] = audits
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(numbers, f, indent=1, default=float)
    print(json.dumps(numbers, indent=1, default=float))


if __name__ == "__main__":
    main()
