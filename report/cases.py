"""Section 3 case studies awaiting verification, and folding verified cases into the audit.

    python -m report.cases pending       # the picked cases report/audits/section3_cases.json lacks
    python -m report.cases merge <dir>   # agent answers in <dir> -> report/audits/section3_cases.json

report.section3 picks the cases (report/output/section3/cases.csv) and lists those the audit does
not cover as section3.case_audit.pending. Each is verified by agents following
report/audits/case_protocol.md; `merge` assembles their JSON answers, one file per case and task
(`<case_id with : as _>__<evidence|outcome|failure_second|adjudication>.json`), and rewrites the
audit with exactly the picked cases.
"""
from __future__ import annotations

import argparse
import json
import os

import pandas as pd

from report.section3 import CASE_AUDIT, OUT, RULES

PROTOCOL = os.path.join(os.path.dirname(CASE_AUDIT), "case_protocol.md")
CLAIMS = {
    "M3": "Curated Mendelian / ClinVar-pathogenic germline evidence links the target gene to this disease (or a subtype "
          "or very similar disease), and it was published before the program entered Phase 2.",
    "M10": "Before the program entered Phase 2, Reactome had curated a disease reaction or pathway in which the target's "
           "gene product is perturbed in this disease (or a subtype or very similar disease).",
    "B1": "Before the program entered Phase 2, the FDA had approved a drug acting on the same target for this disease "
          "or a closely related one.",
    "P2": "Human germline genetics established, before the program entered Phase 2, a mechanism for this target in "
          "this disease that the drug's action opposes (e.g. risk variants raise the gene's function and the drug "
          "lowers it, or loss-of-function variants are protective and the drug lowers function, or loss-of-function "
          "causes the disease and the drug raises function).",
}
TASKS = ("evidence", "outcome", "failure_second", "adjudication")


def claim(rule: str) -> str:
    return CLAIMS.get(rule, f"Before the program entered Phase 2: {RULES[rule][0]}.")


def picked() -> pd.DataFrame:
    return pd.read_csv(os.path.join(OUT, "cases.csv"))


def audit() -> dict[str, dict]:
    return {c["case_id"]: c for c in json.load(open(CASE_AUDIT))}


def pending(_args) -> None:
    done = audit()
    rows = [{"case_id": r.case_id, "rule": r.rule_key, "claim": claim(r.rule_key), "drug": r.entity,
             "targets": r.target, "action": r.sign, "disease": r.disease, "mondo_id": r.mondo_id,
             "phase2_entry": str(pd.Timestamp(r.entry).date())}
            for r in picked().itertuples()
            if r.case_id not in done or int(done[r.case_id]["pipeline_s4"]) != int(r.s4 > 0)]
    print(json.dumps({"protocol": PROTOCOL, "cases": rows}, indent=1))


def data_error(*texts) -> str:
    """The first line an agent marked as a data error, or 'none'."""
    for t in texts:
        for line in (t or "").split("\n"):
            if "DATA ERROR" in line:
                return line[line.index("DATA ERROR"):].strip()
    return "none"


def record(r, answers: dict) -> dict:
    ev, oc, second, adj = (answers.get(t) for t in TASKS)
    advanced = oc["advanced_within_4y"]
    if advanced == "no" and adj is None and (second is None or second["failure_code"] != oc["failure_code"]):
        raise ValueError(f"{r.case_id}: failure codes differ or lack a second coder, and no adjudication")
    code = "not_a_failure" if advanced == "yes" else (adj or oc)["failure_code"]
    return {"case_id": r.case_id, "rule": r.rule_key, "why": r.why, "status": r.status, "program_id": int(r.program_id),
            "moiety_id": int(r.moiety_id), "mondo_id": r.mondo_id, "entity": r.entity, "targets": r.target.split("+"),
            "disease": r.disease, "phase2_entry": str(pd.Timestamp(r.entry).date()), "claim": claim(r.rule_key),
            "pipeline_s4": int(r.s4 > 0), "advanced_within_4y": advanced,
            "pipeline_correct": "yes" if (advanced == "yes") == (r.s4 > 0) else "no",
            "claim_supported": ev["claim_supported"], "predates_entry": ev["predates_entry"], "failure_code": code,
            "error_source": data_error(ev.get("notes"), oc.get("summary")),
            "evidence_source": ev["earliest_source"], "evidence_year": ev["earliest_year"],
            "key_trial": oc["key_trial"], "primary_endpoint": oc["primary_endpoint"], "stop_reason": oc["stop_reason"],
            "outcome_summary": oc["summary"],
            "agents": {"evidence": ev, "outcome": oc, "failure_second": second if advanced == "no" else None,
                       "adjudication": adj}}


def merge(args) -> None:
    done = audit()
    out, added = [], 0
    for r in picked().itertuples():
        stem = os.path.join(args.dir, r.case_id.replace(":", "_"))
        answers = {t: json.load(open(f"{stem}__{t}.json")) for t in TASKS if os.path.exists(f"{stem}__{t}.json")}
        if "evidence" in answers and "outcome" in answers:
            out.append(record(r, answers))
            added += 1
        elif r.case_id in done:
            out.append(done[r.case_id])
    with open(CASE_AUDIT, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"{CASE_AUDIT}: {len(out)} cases ({added} from {args.dir}); {len(picked()) - len(out)} picked cases still pending")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pending").set_defaults(fn=pending)
    m = sub.add_parser("merge")
    m.add_argument("dir")
    m.set_defaults(fn=merge)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
