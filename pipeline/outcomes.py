"""What happened in a trial: posted results and the stated reason for stopping.

    python -m pipeline.outcomes results    # cached CT.gov results sections -> preclin.ctgov_result_summary
    python -m pipeline.outcomes classify   # LLM: execution, stop reason and primary-endpoint outcome per trial

The results summary keeps, for up to three primary outcome measures, the
measured values per group and every statistical comparison (p-value, method,
estimate, confidence interval), plus deaths and serious adverse events per arm,
so an LLM can judge whether the primary endpoint was met.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os

from psycopg2.extras import Json, execute_values

from pipeline import llm
from pipeline.ctgov import CACHE as CTGOV_CACHE

MAX_PRIMARY = 3
MAX_CHARS = 6000


def summarize(results: dict) -> tuple[str, list[dict]]:
    lines, analyses = [], []
    measures = [m for m in (results.get("outcomeMeasuresModule") or {}).get("outcomeMeasures", [])
                if m.get("type") == "PRIMARY"]
    for m in measures[:MAX_PRIMARY]:
        groups = {g["id"]: g.get("title", "") for g in m.get("groups", [])}
        n = {c["groupId"]: c.get("value") for d in m.get("denoms", []) for c in d.get("counts", [])}
        lines.append(f"PRIMARY: {m.get('title')} [{m.get('timeFrame', '')}] "
                     f"({m.get('paramType', '')}, {m.get('unitOfMeasure', '')})")
        for cls in m.get("classes", [])[:4]:
            for cat in cls.get("categories", [])[:4]:
                vals = "; ".join(f"{groups.get(x['groupId'], x['groupId'])[:40]} (n={n.get(x['groupId'])}): "
                                 f"{x.get('value')}" + (f" ±{x['spread']}" if x.get("spread") else "")
                                 for x in cat.get("measurements", []))
                label = " / ".join(filter(None, [cls.get("title"), cat.get("title")]))
                lines.append(f"  {label + ': ' if label else ''}{vals}")
        for a in m.get("analyses", [])[:4]:
            row = {k: a.get(k) for k in ("pValue", "statisticalMethod", "paramType", "paramValue",
                                          "ciLowerLimit", "ciUpperLimit", "nonInferiorityType")}
            row["groups"] = [groups.get(g, g)[:40] for g in a.get("groupIds", [])]
            analyses.append(row)
            lines.append(f"  analysis {' vs '.join(row['groups'])}: p={row['pValue']} {row['statisticalMethod'] or ''} "
                         f"{row['paramType'] or ''} {row['paramValue'] or ''} "
                         f"[{row['ciLowerLimit']}, {row['ciUpperLimit']}] {row['nonInferiorityType'] or ''}")
    for g in (results.get("adverseEventsModule") or {}).get("eventGroups", [])[:6]:
        lines.append(f"AE {g.get('title', '')[:40]}: deaths {g.get('deathsNumAffected')}/{g.get('deathsNumAtRisk')}, "
                     f"serious {g.get('seriousNumAffected')}/{g.get('seriousNumAtRisk')}")
    return "\n".join(lines)[:MAX_CHARS], analyses


def results(_args) -> None:
    snap = sorted(glob.glob(os.path.join(CTGOV_CACHE, "*")))[-1]
    rows = []
    for path in sorted(glob.glob(os.path.join(snap, "page_*.json.gz"))):
        with gzip.open(path, "rt") as f:
            for study in json.load(f)["studies"]:
                if not study.get("resultsSection"):
                    continue
                text, analyses = summarize(study["resultsSection"])
                nct = study["protocolSection"]["identificationModule"]["nctId"]
                rows.append((nct, text, len(analyses), Json(analyses)))
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.ctgov_result_summary")
        execute_values(cur, """INSERT INTO preclin.ctgov_result_summary (nct_id, summary, n_analyses, analyses)
                               VALUES %s""", rows, page_size=2000)
        conn.commit()
    print(f"studies with results={len(rows)}")


STOP_REASONS = ["efficacy_futility", "safety_tolerability", "pk_pd_or_formulation", "business_portfolio",
                "sponsor_decision_unspecified", "competitive_landscape", "enrollment_feasibility",
                "operational_or_site", "regulatory", "manufacturing_supply", "covid19",
                "replaced_by_new_protocol", "objectives_met_or_early_success", "other", "not_stated"]

CLASSIFY_SYSTEM = """You read a clinical trial's registry record (title, phase, status, the sponsor's stated reason for stopping if any, and posted results if any) and record what happened. Keep four questions separate.

1. execution: withdrawn_before_enrollment (status WITHDRAWN or zero enrolled), stopped_early (terminated or suspended after enrolling), completed.
2. stop_reason (only when not completed; otherwise "not_applicable"): the sponsor's stated reason, by meaning not wording.
   efficacy_futility: lack of efficacy, futility, failed or negative interim/primary analysis.
   safety_tolerability: adverse events, safety signal, DSMB stop for harm, tolerability.
   pk_pd_or_formulation: pharmacokinetic, exposure, dose-finding or formulation problems.
   business_portfolio: an explicit business reason: portfolio prioritisation, strategic or commercial decision, funding, acquisition or merger, licence return, development programme discontinued for business reasons.
   sponsor_decision_unspecified: only "sponsor decision" (or equivalent) with no further reason.
   competitive_landscape: a competing therapy or changed standard of care made the trial unnecessary or unfeasible.
   enrollment_feasibility: slow or insufficient enrollment, recruitment difficulty.
   operational_or_site: site, investigator, logistics, contract or data-management problems.
   regulatory: regulator request, clinical hold, ethics/IRB issues, regulatory strategy change.
   manufacturing_supply: drug supply or manufacturing problems.
   covid19: stopped or paused because of COVID-19.
   replaced_by_new_protocol: superseded by another study or a protocol amendment.
   objectives_met_or_early_success: stopped because objectives were met, early efficacy, or planned completion.
   other / not_stated.
   secondary_reasons: other reasons stated (same vocabulary), possibly empty.
3. primary_endpoint (from posted results; "no_results" when none are posted): met (the prespecified primary comparison favoured the drug with statistical significance, or a single-arm primary objective was achieved), not_met (no significant difference, or a negative result on the primary objective), mixed (some primary endpoints met, others not, or significant only in a subgroup), not_assessable (results posted but the primary analysis was not performed or is uninterpretable, e.g. stopped early, purely descriptive PK/safety outcomes).
4. safety_signal: notable (the record shows a safety problem: stated in the stop reason, or a clear excess of deaths or serious adverse events in the drug arm), none_evident, unknown.
Then efficacy_failure: true when the record shows the drug failed to show efficacy (an efficacy_futility stop reason, or primary_endpoint not_met in a trial designed to test efficacy); false otherwise.
evidence: a short quote from the record supporting the stop reason or the endpoint judgement."""

CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "execution": {"type": "string", "enum": ["withdrawn_before_enrollment", "stopped_early", "completed"]},
        "stop_reason": {"type": "string", "enum": STOP_REASONS + ["not_applicable"]},
        "secondary_reasons": {"type": "array", "items": {"type": "string", "enum": STOP_REASONS}},
        "primary_endpoint": {"type": "string", "enum": ["met", "not_met", "mixed", "not_assessable", "no_results"]},
        "safety_signal": {"type": "string", "enum": ["notable", "none_evident", "unknown"]},
        "efficacy_failure": {"type": "boolean"},
        "evidence": {"type": "string"},
    },
    "required": ["execution", "stop_reason", "secondary_reasons", "primary_endpoint", "safety_signal",
                 "efficacy_failure", "evidence"],
    "additionalProperties": False,
}


def render_trial(p: dict) -> str:
    return (f"Trial {p['nct_id']}: {p['title']}\nPhases: {', '.join(p['phases'])}; status: {p['status']}; "
            f"enrollment: {p['enrollment']}; start {p['start']}; completion {p['completion']}\n"
            f"Conditions: {'; '.join(p['conditions'][:6])}\nInterventions: {'; '.join(p['interventions'][:8])}\n"
            f"Stated reason for stopping: {p['why_stopped'] or '(none)'}\n\n"
            f"Posted results:\n{p['results'] or '(no results posted)'}")


CLASSIFY_TASK = llm.Task(name="trial_outcome", prompt_version="v1", schema_version="v1", system=CLASSIFY_SYSTEM,
                         schema=CLASSIFY_SCHEMA, render=render_trial, subject_type="trial",
                         model="claude-opus-5-5", effort="medium", max_tokens=2000)


def classify(_args) -> None:
    """Industry-sponsored in-scope trials started since 2010 that stopped early,
    or completed Phase 2/3 trials with posted results."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT s.nct_id, s.brief_title, s.phases, s.overall_status, s.enrollment, s.start_date,
                   s.completion_date, s.conditions,
                   (SELECT array_agg(i->>'name') FROM jsonb_array_elements(s.interventions) i),
                   s.why_stopped, r.summary
            FROM preclin.ctgov_study s LEFT JOIN preclin.ctgov_result_summary r USING (nct_id)
            WHERE s.lead_sponsor_class = 'INDUSTRY' AND s.start_date >= '2010-01-01'
              AND s.phases && ARRAY['EARLY_PHASE1','PHASE1','PHASE2','PHASE3']
              AND (s.overall_status IN ('TERMINATED', 'WITHDRAWN', 'SUSPENDED')
                   OR (s.overall_status = 'COMPLETED' AND s.has_results
                       AND s.phases && ARRAY['PHASE2','PHASE3']))""")
        items = {nct: {"nct_id": nct, "title": title, "phases": phases, "status": status, "enrollment": enr,
                       "start": str(start), "completion": str(comp), "conditions": conds or [],
                       "interventions": ivs or [], "why_stopped": why, "results": summary}
                 for nct, title, phases, status, enr, start, comp, conds, ivs, why, summary in cur.fetchall()}
    run_id = llm.run(CLASSIFY_TASK, items)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.trial_outcome")
        cur.execute("""INSERT INTO preclin.trial_outcome
              (nct_id, execution, stop_reason, secondary_reasons, primary_endpoint, safety_signal,
               efficacy_failure, evidence, llm_decision_id)
            SELECT subject_key, o->>'execution', o->>'stop_reason',
                   ARRAY(SELECT jsonb_array_elements_text(o->'secondary_reasons')),
                   o->>'primary_endpoint', o->>'safety_signal', (o->>'efficacy_failure')::boolean,
                   o->>'evidence', llm_decision_id
            FROM (SELECT subject_key, parsed_output o, llm_decision_id FROM pv_evidence.llm_decision
                  WHERE decision_run_id = %s AND validation_status = 'validated') d""", (str(run_id),))
        conn.commit()
    print(f"trials={len(items)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("results").set_defaults(fn=results)
    sub.add_parser("classify").set_defaults(fn=classify)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
