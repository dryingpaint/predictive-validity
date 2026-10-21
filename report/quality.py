"""Quality of the LLM-built labels the report rests on.

    python -m report.quality

1. Independent re-derivation of seeded samples by agents working from the
   primary sources, committed in report/audits/ (labels: label_audit.json
   before the pipeline fixes, and label_audit_post_fix.json with fresh samples
   after them, which replaces a label's pre-fix result; trial outcomes from
   posted results and from results papers: outcome_audit.json and
   publication_outcome_audit.json; program approvals by stratum:
   approval_audit.json): accuracy with Wilson 95% intervals, counting correct
   and acceptable verdicts as agreement.
2. Items the model declined to answer, per LLM task, and agreement of tasks
   re-decided under a prompt revision (RETEST) with their earlier decisions.
3. Agreement of the trial stop reasons (preclin.trial_outcome) with the two
   earlier classifications of the same trials: the Sonnet why_stopped labels
   and the GPT-5.6 multi-axis rescore (preclin.classification), on a common
   coarse taxonomy, as Cohen's kappa.
"""
from __future__ import annotations

import json
import math
import os

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from report import frame

OUT = os.path.join(frame.REPO, "report", "output", "quality")
AUDITS = os.path.join(frame.REPO, "report", "audits")
LABEL_AUDITS = ("label_audit.json", "label_audit_post_fix.json")  # before the pipeline fixes, fresh samples after them
OUTCOME_AUDITS = {"outcome_audit": "outcome_audit.json", "publication_audit": "publication_outcome_audit.json"}
OUTCOME_AXES = ("stop_reason", "primary_endpoint", "safety_signal", "efficacy_failure")
APPROVAL_AUDIT = "approval_audit.json"

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


def agreement(ok: int, n: int, z: float = 1.96) -> dict:
    """Share of n audited verdicts in agreement, with its Wilson interval."""
    p = ok / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return {"accuracy": p, "lo": centre - half, "hi": centre + half}


def stop_reason_agreement() -> dict:
    new = frame.query("""SELECT nct_id, stop_reason FROM preclin.trial_outcome
                         WHERE execution <> 'completed'""").set_index("nct_id").stop_reason
    old = frame.query("""SELECT subject_key AS nct_id, classifier_model, category, extracted_at, classification_id,
                                coalesce(raw_output ? 'error', false) AS failed
                         FROM preclin.classification
                         WHERE classifier_task IN ('why_stopped', 'trial_stoppage_rescore')""") \
        .sort_values(["nct_id", "extracted_at", "classification_id"], ascending=[True, False, False])  # latest first
    out = {}
    for model, mapping in [("claude-sonnet", SONNET), ("gpt-5.6-terra", GPT)]:
        o = old[(old.classifier_model == model) & ~old.failed].drop_duplicates("nct_id").set_index("nct_id").category
        both = new.index.drop_duplicates().intersection(o.index)
        for unspecified in ("business", "unknown"):
            a = new.loc[both].map(NEW).replace("unspecified", unspecified).to_numpy()
            b = o.loc[both].map(mapping).to_numpy()
            keep = pd.notna(a) & pd.notna(b)
            a, b = pd.Series(a[keep]), pd.Series(b[keep])
            out[f"{model}|unspecified_as_{unspecified}"] = {
                "n": int(len(a)), "agreement": float((a == b).mean()), "kappa": float(cohen_kappa_score(a, b)),
                "efficacy_kappa": float(cohen_kappa_score(a == "efficacy", b == "efficacy"))}
    return out


# Tasks re-decided under a prompt revision that changed only how lists are shown to the model:
# task -> (earlier version, later version, the part of the output compared).
RETEST = {"trial_purpose": ("v1", "v2", lambda o: o["purpose"]),
          "trial_moiety_role": ("v2", "v3", lambda o: sorted((r["moiety"], r["role"]) for r in o["roles"]))}


def retest() -> dict:
    """Share of subjects decided the same way under both prompt versions (latest validated decision of each)."""
    out = {}
    for task, (a, b, key) in RETEST.items():
        df = frame.query("""
            SELECT DISTINCT ON (r.prompt_version, d.subject_key) r.prompt_version, d.subject_key, d.parsed_output
            FROM pv_evidence.llm_decision d JOIN pv_evidence.llm_decision_run r USING (decision_run_id)
            WHERE d.task = %s AND r.prompt_version IN (%s, %s) AND d.validation_status = 'validated'
            ORDER BY r.prompt_version, d.subject_key, d.created_at DESC""", (task, a, b))
        old = {k: key(o) for v, k, o in df.itertuples(index=False) if v == a}
        new = {k: key(o) for v, k, o in df.itertuples(index=False) if v == b}
        both = old.keys() & new.keys()
        out[task] = sum(old[k] == new[k] for k in both) / len(both)
        out[f"{task}_n"] = len(both)
    return out


def refusals() -> dict:
    """Items the model declined to answer in the latest completed run of each LLM task."""
    return dict(frame.query("""
        SELECT r.task, count(*) FILTER (WHERE d.validation_detail ? 'refusal')::int AS n
        FROM pv_evidence.llm_decision d
        JOIN (SELECT DISTINCT ON (task) task, decision_run_id FROM pv_evidence.llm_decision_run
              WHERE status = 'completed' ORDER BY task, completed_at DESC) r USING (decision_run_id)
        GROUP BY r.task""").itertuples(index=False))


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    numbers = {"stop_reason_agreement": stop_reason_agreement(), "refusals": refusals(), "retest": retest()}
    audits = {}
    for name in LABEL_AUDITS:  # a post-fix audit of a label replaces its pre-fix audit
        for r in json.load(open(os.path.join(AUDITS, name))):
            audits[r["task"]] = {"n": r["n"], "correct": r["n_correct"], "acceptable": r["n_acceptable"],
                                 "wrong": r["n_wrong"], **agreement(r["n_correct"] + r["n_acceptable"], r["n"])}
    numbers["label_audit"] = audits
    for name, path in OUTCOME_AUDITS.items():
        trials = json.load(open(os.path.join(AUDITS, path)))["trials"]
        audits = {}
        for axis in OUTCOME_AXES:
            if not any(f"{axis}_verdict" in t for t in trials):
                continue
            verdicts = [t[f"{axis}_verdict"] for t in trials if t[f"{axis}_verdict"] != "not_applicable"]
            audits[axis] = {"n": len(verdicts), "correct": verdicts.count("correct"),
                            "acceptable": verdicts.count("acceptable"), "wrong": verdicts.count("wrong"),
                            **agreement(sum(v in ("correct", "acceptable") for v in verdicts), len(verdicts))}
        numbers[name] = audits
    programs = json.load(open(os.path.join(AUDITS, APPROVAL_AUDIT)))["programs"]
    audits = {}
    for stratum in sorted({p["stratum"] for p in programs}) + ["all"]:
        group = [p for p in programs if stratum in ("all", p["stratum"])]
        for axis in ("approved", "date"):
            verdicts = [p[f"{axis}_verdict"] for p in group if p[f"{axis}_verdict"] != "not_applicable"]
            if not verdicts:
                continue
            audits[f"{stratum}.{axis}"] = {"n": len(verdicts), "wrong": verdicts.count("wrong"),
                                           **agreement(sum(v in ("correct", "acceptable") for v in verdicts),
                                                       len(verdicts))}
    numbers["approval_audit"] = audits
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(numbers, f, indent=1, default=float)
    print(json.dumps(numbers, indent=1, default=float))


if __name__ == "__main__":
    main()
