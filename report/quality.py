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
   The registry's own MeSH indexing of conditions, carried to MONDO, against the
   LLM disease mapping (mesh_crosswalk.json, from scripts.mesh_crosswalk_check).
2. Items the model declined to answer, per LLM task, and agreement of tasks
   re-decided under a prompt revision (RETEST) with their earlier decisions.
"""
from __future__ import annotations

import json
import math
import os


from report import frame

OUT = os.path.join(frame.REPO, "report", "output", "quality")
AUDITS = os.path.join(frame.REPO, "report", "audits")
LABEL_AUDITS = ("label_audit.json", "label_audit_post_fix.json")  # before the pipeline fixes, fresh samples after them
OUTCOME_AUDITS = {"outcome_audit": "outcome_audit.json", "publication_audit": "publication_outcome_audit.json"}
OUTCOME_AXES = ("stop_reason", "primary_endpoint", "safety_signal", "efficacy_failure")
APPROVAL_AUDIT = "approval_audit.json"
MESH_CROSSWALK = "mesh_crosswalk.json"  # ClinicalTrials.gov's MeSH indexing against the LLM disease mapping
COMPARABLE = {"same disease": "same", "MeSH broader": "broader", "MeSH narrower": "narrower",
              "different disease": "different"}  # statuses where both routes name a disease, by number key



def agreement(ok: int, n: int, z: float = 1.96) -> dict:
    """Share of n audited verdicts in agreement, with its Wilson interval."""
    p = ok / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return {"accuracy": p, "lo": centre - half, "hi": centre + half}


# Tasks decided twice: under a prompt revision that changed only how lists are shown to the
# model, or (same version) again after their payload order changed. task -> (earlier version,
# later version, the part of the output compared).
# Each label's current prompt version against the one it replaced: how much a revision changed the labels.
# The optional fourth entry gives what must be equal for two decisions to be compared at all: a trial whose
# entities were renamed between the two decisions says nothing about whether its roles changed.
RETEST = {"trial_purpose": ("v2", "v4", lambda o: o["purpose"], None),
          "trial_moiety_role": ("v2", "v3", lambda o: sorted((r["moiety"], r["role"]) for r in o["roles"]),
                                lambda o: sorted(r["moiety"] for r in o["roles"])),
          "indication_mondo": ("v2", "v4", lambda o: o["mondo_id"], None)}


def retest() -> dict:
    """Share of subjects decided the same way the two times (the two latest model calls,
    one per version when the versions differ; reused copies are not calls)."""
    out = {}
    for task, (a, b, key, same) in RETEST.items():
        df = frame.query("""
            SELECT r.prompt_version, d.subject_key, d.parsed_output
            FROM pv_evidence.llm_decision d JOIN pv_evidence.llm_decision_run r USING (decision_run_id)
            WHERE d.task = %s AND r.prompt_version IN (%s, %s) AND d.validation_status = 'validated'
              AND d.prior_decision_id IS NULL
            ORDER BY d.subject_key, d.created_at DESC""", (task, a, b))
        later, earlier = {}, {}
        for v, k, o in df.itertuples(index=False):
            if k not in later and v == b:
                later[k] = o
            elif k in later and k not in earlier and v == a and (same is None or same(o) == same(later[k])):
                earlier[k] = o
        out[task] = sum(key(earlier[k]) == key(later[k]) for k in earlier) / len(earlier)
        out[f"{task}_n"] = len(earlier)
    return out


def refusals() -> dict:
    """Items the model declined to answer in the latest completed run of each LLM task."""
    return dict(frame.query("""
        SELECT r.task, count(*) FILTER (WHERE d.validation_detail ? 'refusal')::int AS n
        FROM pv_evidence.llm_decision d
        JOIN (SELECT DISTINCT ON (task) task, decision_run_id FROM pv_evidence.llm_decision_run
              WHERE status = 'completed' ORDER BY task, completed_at DESC) r USING (decision_run_id)
        GROUP BY r.task""").itertuples(index=False))


def mesh_crosswalk() -> dict:
    """Shares of the MeSH-route comparison: of all condition strings, and of those both routes map."""
    m = json.load(open(os.path.join(AUDITS, MESH_CROSSWALK)))
    st = m["statuses"]
    comparable = sum(st[s]["conditions"] for s in COMPARABLE)
    comparable_links = sum(st[s]["links"] for s in COMPARABLE)
    return {"conditions": m["conditions"], "comparable": comparable,
            "attributable_share": 1 - st["only in multi-condition studies"]["conditions"] / m["conditions"],
            "same_share_of_all": st["same disease"]["conditions"] / m["conditions"],
            "same_links_share_of_all": st["same disease"]["links"] / m["study_condition_links"],
            **{f"{key}_share": st[s]["conditions"] / comparable for s, key in COMPARABLE.items()},
            "same_links_share": st["same disease"]["links"] / comparable_links,
            "non_disease": st["MeSH names a disease, the LLM none"]["conditions"], "review": m["review"]}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    numbers = {"refusals": refusals(), "retest": retest()}
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
    numbers["mesh_crosswalk"] = mesh_crosswalk()
    with open(os.path.join(OUT, "numbers.json"), "w") as f:
        json.dump(numbers, f, indent=1, default=float)
    print(json.dumps(numbers, indent=1, default=float))


if __name__ == "__main__":
    main()
