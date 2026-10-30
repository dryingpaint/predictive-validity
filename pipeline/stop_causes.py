"""Why each Phase 2/3 program stopped, where the registry does not say or says wrongly.

    python -m pipeline.stop_causes signals    # structured facts per stopped program -> preclin.stop_signal
    python -m pipeline.stop_causes infer      # LLM with web search: cause of each unexplained stop
    python -m pipeline.stop_causes validate   # the same on a seeded sample of stated stops, reason hidden
    python -m pipeline.stop_causes describe   # LLM: subcause of each stop, and explanations without codes
    python -m pipeline.stop_causes assemble   # final cause of every stop, and why efficacy failed -> preclin.stop

Section 1 gives each suspended program one reason from its own trials. For 40% of Phase 2/3
stops no reason is stated; a bare "sponsor decision" or an unspecified "other" reason says little
more; and the efficacy attribution (pipeline.attribution) found stops recorded as efficacy that
were not failed efficacy tests (codes F8, F9) or that toxicity ended (F6). Each of these is
inferred: the model reads the program's trials (records, posted results, linked papers), its
structured signals and the entity's other programs, then searches the web (company releases,
filings, pipeline updates, conference reports, news) and names the cause, how directly the
sources state it, and the sources. ClinicalTrials.gov is excluded from search, so the held-out
validation cannot read the reason it is scored against. Every URL a decision cites must be one
its searches returned. Each step records its method in preclin.analysis_method. The model names
causes in its own vocabulary (MODEL_CAUSES); preclin.stop holds them in pipeline.stops.CAUSES.
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict

import numpy as np
import pandas as pd
from psycopg2.extras import execute_values

from pipeline import llm
from pipeline.stops import (CAUSE, CODE_CAUSE, INFERENCE_TASK, INFERENCE_VERSION, PHASES, REGISTRY_CAUSE,
                            RELATED_DISEASE, SUBCAUSES, UNSTATED, SameTarget, detail, fate, inferred_causes, keys,
                            labels, pillar_code, settled, stops, subcause)
from report import frame
from report.disease_match import Mondo

MODEL_CAUSES = ["efficacy", "safety", "pk_formulation", "business_strategic", "company_event", "operational",
          "positive_not_advanced", "development_continued", "unknown"]
EVIDENCE = ["explicit_program", "explicit_drug", "results", "context", "none"]
SPONSOR_GAP_MONTHS = 12
PEER_WINDOW_MONTHS = 18
RESULTS_CHARS = 2500
ABSTRACT_CHARS = 1500
MAX_PAPERS = 6
VALIDATION_SAMPLE = 150
VALIDATION_SEED = 20261026
BLOCKED_DOMAINS = ["clinicaltrials.gov"]


SIGNALS_METHOD = "stop_signals@v1"
SIGNALS_DESCRIPTION = f"""For every program Section 1 records as suspended in Phase 2 or 3 (report.section1.failure_modes),
keyed by (entity, disease, phase), phase entries in report.windows.TRACING: phase_entry is the phase entry
date Section 1 assigns; stopped_on is the latest end (completion, else primary completion, else start)
of the program's own trials; drug_continued_elsewhere is true when another program of the entity had a trial start
after that date or has an active trial; drug_approved_anywhere is true when the entity has any FDA approval;
sponsor_active_after is true when a lead sponsor of the program's trials started any registered trial more than
{SPONSOR_GAP_MONTHS} months after stopped_on (null without a sponsor name); target_peers_stopped counts other entities
sharing a primary target whose programs in a related disease (MONDO Lin similarity >= {RELATED_DISEASE}) were suspended
within {PEER_WINDOW_MONTHS} months of this one. No LLM is involved."""


def program_trials(modes, trials):
    """Each stopped program's trials (any phase), with the phase it stopped in as stop_phase."""
    own = trials.merge(modes[["program_id", "phase", "key"]].rename(columns={"phase": "stop_phase"}), on="program_id")
    end = pd.to_datetime(own.completion_date).fillna(pd.to_datetime(own.primary_completion_date)) \
        .fillna(pd.to_datetime(own.start_date))
    return own.assign(end=end)


def compute_signals(modes, rows, progs, trials) -> pd.DataFrame:
    stopped = modes[modes.phase.isin(PHASES)].copy()
    own = program_trials(stopped, trials)
    stopped_on = own.groupby("key").end.max()
    stopped["stopped_on"] = stopped.key.map(stopped_on)

    t = trials.merge(progs[["program_id", "moiety_id"]], on="program_id")
    t["start"] = pd.to_datetime(t.start_date)
    active = t.overall_status.isin(("RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION",
                                    "NOT_YET_RECRUITING"))
    by_entity = {m: g for m, g in t.assign(active=active).groupby("moiety_id")}
    continued = []
    for pid, m, when in zip(stopped.program_id, stopped.moiety_id, stopped.stopped_on):
        g = by_entity.get(m)
        other = g[g.program_id != pid] if g is not None else pd.DataFrame()
        continued.append(bool(len(other)) and bool(((other.start > when) | other.active).any()))
    stopped["drug_continued_elsewhere"] = continued
    approved = set(progs[progs.approved.eq("yes") | progs.moiety_first_fda_approval.notna()].moiety_id)
    stopped["drug_approved_anywhere"] = stopped.moiety_id.isin(approved)

    last_start = frame.query("""SELECT lead_sponsor, max(start_date) AS start_date FROM preclin.ctgov_study
                                WHERE lead_sponsor IS NOT NULL AND start_date IS NOT NULL GROUP BY 1""")
    last_start = pd.to_datetime(last_start.set_index("lead_sponsor").start_date)
    sponsor = frame.query("""SELECT nct_id, lead_sponsor FROM preclin.ctgov_study
                             WHERE lead_sponsor IS NOT NULL AND start_date IS NOT NULL AND nct_id = ANY(%s)""",
                          (sorted(set(own.nct_id)),))
    lead = own.merge(sponsor, on="nct_id").groupby("key").lead_sponsor.agg(set)
    gap = pd.DateOffset(months=SPONSOR_GAP_MONTHS)
    stopped["sponsor_active_after"] = [
        None if not lead.get(k) else any(last_start.get(s, pd.Timestamp.min) > w + gap for s in lead[k])
        for k, w in zip(stopped.key, stopped.stopped_on)]

    susp = rows[(rows.event == "suspended") & ~rows.credited].merge(progs[["program_id", "mondo_id"]], on="program_id")
    susp_by_entity = defaultdict(list)
    for m, d, e in zip(susp.moiety_id, susp.mondo_id, pd.to_datetime(susp.event_date)):
        if isinstance(d, str):
            susp_by_entity[m].append((d, e))
    same, window_days = SameTarget(Mondo()), PEER_WINDOW_MONTHS * 30.44
    peers = []
    for m, d, when in zip(stopped.moiety_id, stopped.mondo_id, stopped.stopped_on):
        peers.append(sum(any(same.related(od, d) and abs((oe - when).days) <= window_days
                             for od, oe in susp_by_entity[o])
                         for o in same.others(m)) if pd.notna(when) else 0)
    stopped["target_peers_stopped"] = peers

    stopped["mondo_id"] = stopped.mondo_id.fillna("")
    return stopped


def signals(_args) -> None:
    modes, rows, progs, trials = stops()
    s = compute_signals(modes, rows, progs, trials)
    with llm.connect() as conn, conn.cursor() as cur:
        mid = llm.record_method(cur, SIGNALS_METHOD, "Structured signals of stopped programs", SIGNALS_DESCRIPTION,
                     ["preclin.dev_program", "preclin.dev_program_trial", "preclin.ctgov_study",
                      "preclin.moiety_target", "preclin.dev_program_approval"],
                     {"phases": list(PHASES), "sponsor_gap_months": SPONSOR_GAP_MONTHS,
                      "peer_window_months": PEER_WINDOW_MONTHS, "related_disease_lin": RELATED_DISEASE})
        cur.execute("DELETE FROM preclin.stop_signal")
        execute_values(cur, """INSERT INTO preclin.stop_signal (moiety_id, mondo_id, phase, phase_entry, stopped_on,
                                 drug_continued_elsewhere, drug_approved_anywhere, sponsor_active_after,
                                 target_peers_stopped, method_id) VALUES %s""",
                       [(int(r.moiety_id), r.mondo_id, int(r.phase), pd.Timestamp(r.entry).date(),
                         r.stopped_on.date() if pd.notna(r.stopped_on) else None,
                         bool(r.drug_continued_elsewhere), bool(r.drug_approved_anywhere),
                         None if r.sponsor_active_after is None else bool(r.sponsor_active_after),
                         int(r.target_peers_stopped), mid) for r in s.itertuples()])
        conn.commit()
    print(f"programs={len(s)} continued_elsewhere={int(s.drug_continued_elsewhere.sum())} "
          f"sponsor_inactive={int((s.sponsor_active_after == False).sum())}")  # noqa: E712


SYSTEM = """You find out why a drug development program stopped. A program is one drug developed for one disease; it stopped in the phase given, and its registry records state no reason, or only "sponsor decision", or a reason that turned out to be wrong. You are given the program's trials in that phase (records, posted results, linked papers), structured signals, and the drug's other programs.

Search the web for what happened: company press releases, quarterly and annual reports and SEC filings (10-K, 10-Q, 20-F, 8-K), pipeline updates, investor presentations, conference abstracts, publications and trade news (Fierce, Endpoints, BioSpace, Evaluate, company sites). Search for the drug's name and code names with the disease, and with words like discontinued, terminated, deprioritized, pipeline. ClinicalTrials.gov is not available to search. Use at most a handful of searches; stop when you have the answer or the trail is cold.

Give the cause of the stop:
- efficacy: no or insufficient efficacy, futility, a missed endpoint, or efficacy not competitive with standard of care.
- safety: adverse events, tolerability, a safety signal or clinical hold for safety (on- or off-target).
- pk_formulation: exposure, pharmacokinetics, dosing, formulation or manufacturability of the drug.
- business_strategic: portfolio prioritisation, commercial or competitive reasons, a partner returning rights, refocusing.
- company_event: the sponsor was acquired or merged and the program was dropped in integration, ran out of money, wound down or went bankrupt.
- operational: enrollment, site or supply problems, COVID-19, a regulatory or procedural hold not about safety.
- positive_not_advanced: the trial succeeded (met its endpoint) and the program still did not move on in this disease (e.g. approved outside the US, partnered and stalled, development moved to another formulation).
- development_continued: the program did not actually stop: it continued under another trial registry, region, name or combination.
- unknown: no source says or allows a reasoned inference.
evidence_kind: explicit_program (a source states the reason for this drug in this disease), explicit_drug (a source states why the drug as a whole was discontinued), results (published or posted results show the outcome, e.g. a missed endpoint, without a stated decision), context (an inference from circumstances, e.g. the company was acquired and the pipeline cut, or every program of the drug stopped together), none (unknown).
A cause other than unknown needs evidence_kind other than none. Quote the decisive sentence from a source in quote when evidence_kind is explicit_program or explicit_drug. Cite only URLs your searches returned, NCT ids and PMIDs from the bundle. Do not guess; prefer unknown to a cause no source supports.
confidence: high when a source states it for this program; medium when stated for the drug or strongly implied; low when inferred from context.
likely_cause: your best inference of the cause. When cause is known, likely_cause equals cause. When cause is unknown, reason from what the bundle and your searches show: e.g. the trial completed, results were never posted and every program of the drug stopped together (often efficacy or safety, judged by what else is known); the sponsor was a small private company that stopped all activity (company_event); the drug kept going in its other diseases and this indication was dropped quietly (business_strategic, unless results point to efficacy). Use unknown only when nothing tilts it. likely_basis: one sentence on what the likely cause rests on.
rationale: at most 100 words."""

SCHEMA = {
    "type": "object",
    "properties": {
        "cause": {"type": "string", "enum": MODEL_CAUSES},
        "secondary_causes": {"type": "array", "items": {"type": "string", "enum": MODEL_CAUSES}},
        "evidence_kind": {"type": "string", "enum": EVIDENCE},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "stop_year": {"type": ["integer", "null"]},
        "quote": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
        "likely_cause": {"type": "string", "enum": MODEL_CAUSES},
        "likely_basis": {"type": "string"},
        "rationale": {"type": "string"},
    },
    "required": ["cause", "secondary_causes", "evidence_kind", "confidence", "stop_year", "quote", "sources",
                 "likely_cause", "likely_basis", "rationale"],
    "additionalProperties": False,
}


def validate(p: dict, out: dict) -> None:
    allowed = {t["nct_id"] for t in p["trials"]} | {f"PMID:{a['pmid']}" for a in p["papers"]}
    retrieved = {llm.norm_url(u) for u in out.get("retrieved_urls", [])}
    unknown = [s for s in out["sources"] if s not in allowed and llm.norm_url(s) not in retrieved]
    if unknown:
        raise ValueError(f"cites sources it did not retrieve: {unknown[:3]}")
    if (out["cause"] == "unknown") != (out["evidence_kind"] == "none"):
        raise ValueError(f"cause {out['cause']} with evidence {out['evidence_kind']}")
    if out["evidence_kind"].startswith("explicit") and not (out["quote"].strip() and out["sources"]):
        raise ValueError("explicit evidence without a quote and a source")
    if out["cause"] != "unknown" and out["likely_cause"] != out["cause"]:
        raise ValueError(f"likely cause {out['likely_cause']} differs from the known cause {out['cause']}")


def render(p: dict) -> str:
    sig = p["signals"]
    out = [f"Drug: {p['drug']} (codes: {', '.join(p['codes']) or 'none'}; modality: {p['modality']})",
           f"Primary targets: {'; '.join(p['targets']) or 'none recorded'}",
           f"Disease: {p['disease']}", f"Phase the program stopped in: {p['phase']}",
           f"Sponsors: {'; '.join(p['sponsors']) or 'unknown'}",
           "",
           "STRUCTURED SIGNALS:",
           f"- program's last trial ended: {sig['stopped_on'] or 'unknown'}",
           f"- the drug's other programs continued after this one stopped: {'yes' if sig['drug_continued_elsewhere'] else 'no'}",
           f"- the drug is FDA-approved for some disease: {'yes' if sig['drug_approved_anywhere'] else 'no'}",
           f"- a lead sponsor started any trial more than {SPONSOR_GAP_MONTHS} months later: "
           f"{'unknown' if sig['sponsor_active_after'] is None else 'yes' if sig['sponsor_active_after'] else 'no'}",
           f"- other drugs on the same target stopped in a related disease within {PEER_WINDOW_MONTHS} months: "
           f"{sig['target_peers_stopped']}",
           "",
           f"THE PROGRAM'S TRIALS IN PHASE {p['phase']}:"]
    for t in p["trials"]:
        out += [f"[{t['nct_id']}] {t['title']}",
                f"  status {t['status']}; start {t['start']}; end {t['end']}; enrollment {t['enrollment']}",
                f"  stated reason for stopping: {t['why_stopped'] or '(none)'}",
                f"  primary outcomes: {t['primary_outcomes']}",
                f"  posted results: {t['results'] or '(none)'}"]
    out += ["", "THE DRUG'S OTHER PROGRAMS:"]
    out += [f"- {o}" for o in p["other_programs"]] or ["(none)"]
    out += ["", "PAPERS:"]
    out += [f"[PMID:{a['pmid']}] ({a['year']}) {a['title']}\n{a['abstract']}" for a in p["papers"]] or ["(none)"]
    return "\n".join(out)


TOOLS = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 6, "blocked_domains": BLOCKED_DOMAINS},
         {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 3, "blocked_domains": BLOCKED_DOMAINS}]
TASK = llm.Task(name=INFERENCE_TASK, prompt_version=INFERENCE_VERSION, schema_version="v2", system=SYSTEM,
                schema=SCHEMA, render=render, validate=validate, subject_type="program_phase",
                model="claude-opus-5-5", effort="medium", max_tokens=16000, tools=TOOLS)

INFER_METHOD = "stop_cause_inference@v2"
INFER_DESCRIPTION = f"""Cohort: Phase 2/3 programs Section 1 records as suspended whose reason is unstated
({'; '.join(UNSTATED)}), plus registry efficacy stops the efficacy attribution coded F9 (not an efficacy test) and
positive readouts whose index trial's primary endpoint is not an efficacy endpoint. Input per program (task
{TASK.name} {TASK.prompt_version}, model {TASK.model}, effort {TASK.effort}): the drug, its primary targets, the
disease, the program's trials in the phase (record, stated reason if any, primary outcomes, posted results up to
{RESULTS_CHARS} characters), up to {MAX_PAPERS} linked or retrieved papers, the stop_signals@v1 facts, and the drug's
other programs. The model searches the web (web_search up to 6 queries, web_fetch up to 3 pages;
{', '.join(BLOCKED_DOMAINS)} blocked) for releases, filings, pipeline updates, conference reports and news, then
returns a cause ({', '.join(MODEL_CAUSES)}), how directly sources state it ({', '.join(EVIDENCE)}), confidence, a
supporting quote and its sources, and separately a likely cause: its best inference from context and signals when no
source states the cause (equal to the cause when one is known), with a one-sentence basis. Validation rejects a decision that cites a URL its own searches did not return,
names a cause without evidence, or claims explicit evidence without a quote. Prompt, schema, inputs, raw output and
the retrieved URLs are stored per decision in pv_evidence.llm_decision."""


def text(x) -> str:
    """A text field from a frame, '' when missing."""
    return x if isinstance(x, str) else ""


def bundles(cohort: pd.DataFrame, sig: pd.DataFrame, hide_reason: bool = False) -> dict[str, dict]:
    """Inference input of each cohort program, keyed by subject_key; hide_reason drops stated reasons."""
    moieties = sorted({int(m) for m in cohort.moiety_id})
    pids = sorted({int(p) for p in cohort.program_id})
    drug = frame.query("""SELECT moiety_id, name, code_names, coalesce(modality, 'unknown') AS modality
                          FROM preclin.moiety WHERE moiety_id = ANY(%s)""", (moieties,)).set_index("moiety_id")
    targets = frame.query("""SELECT mt.moiety_id, string_agg(t.symbol || ' (' || mt.action || ')', '; '
                                     ORDER BY t.symbol) AS t
                             FROM preclin.moiety_target mt JOIN public.targets t ON t.id = mt.target_id
                             WHERE mt.is_primary AND mt.moiety_id = ANY(%s) GROUP BY 1""", (moieties,)) \
        .set_index("moiety_id").t
    label = frame.query("SELECT term_id, label FROM preclin.ontology_term WHERE ontology = 'MONDO'") \
        .set_index("term_id").label
    trials = frame.query("""
        SELECT dt.program_id, dt.phase, s.nct_id, s.brief_title, s.overall_status, s.start_date,
               coalesce(s.completion_date, s.primary_completion_date) AS end_date, s.enrollment, s.why_stopped,
               s.lead_sponsor, s.primary_outcomes, r.summary
        FROM preclin.dev_program_trial dt JOIN preclin.ctgov_study s USING (nct_id)
        LEFT JOIN preclin.ctgov_result_summary r USING (nct_id)
        WHERE dt.program_id = ANY(%s) AND dt.attach IN ('disease', 'non_disease_condition')
        ORDER BY s.start_date, s.nct_id""", (pids,))
    papers = frame.query("""
        SELECT dt.program_id, a.pmid, a.year, a.title, a.abstract FROM preclin.dev_program_trial dt
        JOIN preclin.trial_publication tp USING (nct_id) JOIN public.publications a USING (pmid)
        WHERE dt.program_id = ANY(%s)
        UNION
        SELECT p.program_id, a.pmid, a.year, a.title, a.abstract FROM preclin.dev_program p
        JOIN preclin.moiety_publication mp ON mp.moiety_id = p.moiety_id AND mp.mondo_id = p.mondo_id
             AND mp.query_kind = 'disease' AND mp.rank <= 4
        JOIN public.publications a USING (pmid) WHERE p.program_id = ANY(%s)
        ORDER BY 1, 3 DESC NULLS LAST, 2""", (pids, pids))
    other = frame.query("""
        SELECT p.moiety_id, p.program_id, p.mondo_id, p.highest_phase, p.last_activity, ap.approved
        FROM preclin.dev_program p LEFT JOIN preclin.dev_program_approval ap USING (program_id)
        WHERE p.moiety_id = ANY(%s) ORDER BY p.last_activity DESC, p.program_id""", (moieties,))
    trials_of = {k: g for k, g in trials.groupby(["program_id", "phase"])}
    papers_of = {k: g.head(MAX_PAPERS) for k, g in papers.groupby("program_id")}
    other_of = {k: g for k, g in other.groupby("moiety_id")}
    sig = sig.set_index("key")
    items = {}
    for r in cohort.itertuples():
        m = int(r.moiety_id)
        tr = trials_of.get((r.program_id, r.phase), trials.iloc[:0])
        o = other_of.get(m, other.iloc[:0])
        o = o[o.program_id != r.program_id].head(12)
        s = sig.loc[r.key]
        items[r.key] = {
            "drug": drug.at[m, "name"], "codes": list(drug.at[m, "code_names"])[:6], "modality": drug.at[m, "modality"],
            "targets": [targets[m]] if m in targets.index else [],
            "disease": label.get(r.mondo_id, "unspecified") if isinstance(r.mondo_id, str) else "unspecified",
            "phase": int(r.phase), "sponsors": sorted({x for x in tr.lead_sponsor if isinstance(x, str)}),
            "signals": {"stopped_on": str(s.stopped_on.date()) if pd.notna(s.stopped_on) else None,
                        "drug_continued_elsewhere": bool(s.drug_continued_elsewhere),
                        "drug_approved_anywhere": bool(s.drug_approved_anywhere),
                        "sponsor_active_after": None if pd.isna(s.sponsor_active_after) else bool(s.sponsor_active_after),
                        "target_peers_stopped": int(s.target_peers_stopped)},
            "trials": [{"nct_id": t.nct_id, "title": t.brief_title, "status": t.overall_status,
                        "start": str(t.start_date), "end": str(t.end_date), "enrollment": None if pd.isna(t.enrollment) else int(t.enrollment),
                        "why_stopped": None if hide_reason else text(t.why_stopped) or None,
                        "primary_outcomes": "; ".join(x.get("measure", "") for x in (t.primary_outcomes or [])),
                        "results": text(t.summary)[:RESULTS_CHARS]} for t in tr.itertuples()],
            "papers": [{"pmid": a.pmid, "title": text(a.title), "abstract": text(a.abstract)[:ABSTRACT_CHARS],
                        "year": None if pd.isna(a.year) else int(a.year)}
                       for a in papers_of.get(r.program_id, papers.iloc[:0]).itertuples()],
            "other_programs": [f"{label.get(x.mondo_id, x.mondo_id) if isinstance(x.mondo_id, str) else 'unspecified'}: "
                               f"furthest phase {x.highest_phase}, last activity {x.last_activity}"
                               f"{', FDA-approved' if x.approved == 'yes' else ''}" for x in o.itertuples()],
        }
    return items


def load_signals() -> pd.DataFrame:
    s = frame.query("SELECT * FROM preclin.stop_signal")
    s["stopped_on"] = pd.to_datetime(s.stopped_on)
    s["key"] = keys(s)
    return s


def inference_cohort(modes: pd.DataFrame) -> pd.DataFrame:
    """Phase 2/3 stops with no usable registry reason, and those whose registry reason the evidence sends back."""
    m = modes[modes.phase.isin(PHASES)]
    back = {k for k, how in settled(modes, labels()).items() if how == "infer"}
    return m[m.reason.isin(UNSTATED) | m.key.isin(back)]


def infer(_args) -> None:
    modes = stops()[0]
    cohort = inference_cohort(modes)
    items = bundles(cohort, load_signals())
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, INFER_METHOD, "Cause of stops the registry does not explain", INFER_DESCRIPTION,
               ["preclin.ctgov_study", "preclin.ctgov_result_summary", "preclin.trial_publication",
                "preclin.moiety_publication", "preclin.stop_signal",
                "pv_evidence.llm_decision (efficacy attribution)", "web search"], {"task": TASK.name, "prompt_version": TASK.prompt_version, "model": TASK.model,
                                "effort": TASK.effort, "tools": TOOLS, "causes": MODEL_CAUSES, "evidence": EVIDENCE})
        conn.commit()
    run_id = llm.run(TASK, items)
    print(f"programs={len(items)} decided={len(llm.decisions(run_id))} run={run_id}")


VALIDATE_METHOD = "stop_cause_validation@v2"
VALIDATE_DESCRIPTION = f"""Held-out check of stop_cause_inference@v2. A seeded random sample (seed {VALIDATION_SEED},
up to {VALIDATION_SAMPLE}, stratified evenly across causes) of Phase 2/3 stops whose registry states a reason
Section 1 maps to a cause ({', '.join(sorted(set(REGISTRY_CAUSE.values())))}) is run through the same task with the
stated reason removed from the bundle and ClinicalTrials.gov blocked from search. The inferred cause is compared with
the registry cause, for the evidence-backed cause and for the likely cause: agreement, Cohen's kappa and recall
per cause (report.stop_causes). The decisions are stored
under the task's subject keys with the suffix |heldout."""


def validate_run(_args) -> None:
    modes = stops()[0]
    contradicted = settled(modes, labels())
    stated = modes[modes.phase.isin(PHASES) & modes.reason.isin(list(REGISTRY_CAUSE))
                   & ~modes.key.isin(contradicted)].copy()
    stated["cause"] = stated.reason.map(REGISTRY_CAUSE)
    rng = np.random.default_rng(VALIDATION_SEED)
    per = VALIDATION_SAMPLE // stated.cause.nunique()
    picks = []
    for _, g in stated.sort_values("key").groupby("cause"):
        picks += list(rng.choice(g.key.to_numpy(), size=min(per, len(g)), replace=False))
    items = {f"{k}|heldout": v for k, v in bundles(stated[stated.key.isin(set(picks))], load_signals(),
                                                    hide_reason=True).items()}
    run_id = llm.run(TASK, items)
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, VALIDATE_METHOD, "Held-out validation of stop-cause inference", VALIDATE_DESCRIPTION,
                          ["preclin.ctgov_study", "preclin.stop_signal", "web search"],
                          {"seed": VALIDATION_SEED, "sample": VALIDATION_SAMPLE, "per_cause": per, "run": str(run_id)})
        conn.commit()
    print(f"sample={len(items)} decided={len(llm.decisions(run_id))} run={run_id}")


ASSEMBLE_METHOD = "stop_cause_assembly@v3"
ASSEMBLE_DESCRIPTION = f"""Why every stop Section 1 counts happened, one row per (entity, disease, phase) in
preclin.stop. A stated registry reason is kept and mapped to a cause ({'; '.join(f'{k} -> {CAUSE[v]}' for k, v in
REGISTRY_CAUSE.items())}). A stop for efficacy or exposure whose final efficacy-attribution label (the web-search
label where the bundle label was U) is {' or '.join(f'{c} takes {v}' for c, v in CODE_CAUSE.items())}. A registry
efficacy stop labelled F9 and a positive readout whose index trial's primary endpoint is not an efficacy endpoint
take the inferred cause, as does an unstated, bare sponsor-decision or unspecified other reason; the inferred cause
maps to preclin.stop's vocabulary ({'; '.join(f'{k} -> {v}' for k, v in CAUSE.items() if k != v)}), and is unknown
where no source states it, with the model's likely cause as the guess. If inference produced no validated decision
the cause is unknown with no guess. Subcause: for an efficacy stop, why efficacy failed from its label (F9 coded by
its pillars; not_attributed without a label); off_target_toxicity for a stop the label settles as safety; for
safety, sponsor decision, operational and positive-readout stops, the stop_description@v2 subcause; for an unknown
cause, what the drug and sponsor did next
(preclin.stop_signal). Explanation: the label's rationale where it gives the subcause, else the source quote or the
model's basis (in stop_description@v2's plain wording where it used failure codes), else what the trial that
gave Section 1 its reason states (its stated reason for stopping, else
the result Section 1 read), with the trial in the sources. Traced: the cause did not come straight from the registry (no usable reason, or the label overturned
it)."""


def first_text(*xs) -> str | None:
    """The first non-empty string, None if there is none."""
    return next((x.strip() for x in xs if isinstance(x, str) and x.strip()), None)


def stop_row(reason: str, settle: str | None, inferred: dict | None, label: dict | None, fate: str | None,
             trial: dict) -> dict:
    """What preclin.stop records for one stop. settle is None where the registry reason stands, a cause where the
    efficacy-attribution label settles it, or 'infer'; inferred is the validated inference decision
    (llm_decision_id, parsed_output) of a stop sent to inference, label its efficacy-attribution label with its
    subcause and detail, fate what the drug and sponsor did next, and trial the trial that gave Section 1 its
    reason (nct_id, and stated: the sponsor's stated reason, else the result Section 1 read)."""
    o = inferred["parsed_output"] if inferred else None
    if settle is None:
        cause = CAUSE[REGISTRY_CAUSE[reason]]
    elif settle != "infer":
        cause = settle
    else:
        cause = CAUSE[o["cause"]] if o else "unknown"
    guess = CAUSE[o["likely_cause"]] if o and cause == "unknown" else "unknown"
    sub = det = None
    if cause == "efficacy":
        sub, det = (label["subcause"], label["detail"]) if label else ("not_attributed", None)
    elif cause == "safety" and settle == "safety":
        sub = "off_target_toxicity"
    elif cause == "unknown":
        sub = fate
    explains = label is not None and (cause == "efficacy" or settle in CODE_CAUSE.values())
    explanation = first_text(label["quote"], label["rationale"]) if explains else \
        first_text(o["quote"], o["likely_basis"], o["rationale"]) if o else None
    from_trial = explanation is None and first_text(trial["stated"]) is not None
    return {"cause": cause, "subcause": None if pd.isna(sub) else sub, "detail": None if pd.isna(det) else det,
            "guess": None if guess == "unknown" else guess,
            "explanation": first_text(trial["stated"]) if from_trial else explanation,
            "sources": list(dict.fromkeys((o["sources"] if o else []) + (list(label["sources"]) if explains else [])
                                          + ([trial["nct_id"]] if from_trial else []))),
            "decision_ids": ([int(inferred["llm_decision_id"])] if o else [])
                            + ([int(label["llm_decision_id"])] if explains else []),
            "traced": settle is not None}


COLUMNS = ["cause", "subcause", "detail", "guess", "explanation", "sources", "decision_ids", "traced"]


def stop_rows() -> list[tuple]:
    """(key, moiety_id, mondo_id, phase, registry reason, stop_row) of every stop, before describe's decisions."""
    modes = stops()[0]
    modes = modes[modes.phase.isin(PHASES)]
    dec = inferred_causes().set_index("key")
    lab = labels()
    how = settled(modes, lab)
    lab = lab.assign(subcause=subcause(pillar_code(lab), lab.engagement),
                     detail=detail(pillar_code(lab), lab.dose_limited)).set_index("key")
    fates = fate(load_signals().set_index("key"))
    stated = frame.query("""SELECT s.nct_id, coalesce(nullif(trim(s.why_stopped), ''), o.evidence) AS stated
                            FROM preclin.ctgov_study s LEFT JOIN preclin.trial_outcome o USING (nct_id)
                            WHERE s.nct_id = ANY(%s)""", (sorted(set(modes.nct_id.dropna())),))
    stated = dict(zip(stated.nct_id, stated.stated))
    out = []
    for r in modes.itertuples():
        settle = how.get(r.key, "infer" if r.reason in UNSTATED else None)
        inferred = dec.loc[r.key].to_dict() if settle == "infer" and r.key in dec.index else None
        label = lab.loc[r.key].to_dict() if r.key in lab.index else None
        out.append((r.key, int(r.moiety_id), r.mondo_id if isinstance(r.mondo_id, str) else "", int(r.phase),
                    r.reason, stop_row(r.reason, settle, inferred, label, fates.get(r.key),
                                       {"nct_id": r.nct_id, "stated": stated.get(r.nct_id)})))
    return out


SUBCAUSE_MEANING = {
    "on_target_toxicity": "harm that follows from hitting the target itself (the mechanism's expected toxicity)",
    "off_target_toxicity": "harm from the molecule rather than the target (off-target binding, metabolites, the formulation)",
    "tolerability": "side effects patients would not tolerate, without a stated mechanism",
    "preclinical_toxicity": "a finding in animal or laboratory toxicology studies",
    "clinical_hold": "a regulator's clinical hold or a safety board's recommendation to stop",
    "portfolio_prioritisation": "the sponsor chose to put its resources into other programs",
    "commercial_or_competitive": "the market, pricing, reimbursement or a competing drug made it not worth pursuing",
    "partner_exit": "a licensing or development partner ended the deal or handed the rights back, or the sponsor was "
                    "looking for a partner to take it forward and none did",
    "acquisition_or_merger": "the sponsor was acquired or merged and the program was dropped",
    "funding_or_closure": "the sponsor ran out of money, wound down, went bankrupt or closed",
    "enrollment": "patients could not be recruited or retained fast enough",
    "site_or_supply": "trial sites, drug supply, manufacturing for the trial or other logistics",
    "covid_19": "the COVID-19 pandemic disrupted the trial",
    "regulatory": "a regulatory or procedural requirement or hold not about safety",
    "replaced_by_successor": "development moved to another formulation, dose form, combination or follow-on drug",
    "approved_outside_us": "the drug was approved, or filed, outside the United States",
    "fda_declined": "the FDA declined to approve it (a complete response letter)",
    "not_stated": "the text gives no more detail than the cause",
}
SUBCAUSE_SYSTEM = f"""You read why a drug development program stopped and name the subcause. The cause is already decided and is given; so is the text it rests on (the sponsor's stated reason, a quote from a source, a posted result, or an analyst's reasoning).

Choose the one subcause, from the list for the given cause, that the text states or directly implies. Use not_stated when the text says no more than the cause. For a positive readout that went no further, name why development did not go on after the good result. Judge only from the text; do not use what you know about the drug or the company.

Subcauses for each cause:
{chr(10).join(f"- {c}: {', '.join(v)}" for c, v in SUBCAUSES.items())}

What each subcause means:
{chr(10).join(f"- {k}: {v}" for k, v in SUBCAUSE_MEANING.items())}

basis: the words in the text the subcause rests on, or empty for not_stated."""
SUBCAUSE_SCHEMA = {
    "type": "object",
    "properties": {"subcause": {"type": "string", "enum": list(SUBCAUSE_MEANING)}, "basis": {"type": "string"}},
    "required": ["subcause", "basis"],
    "additionalProperties": False,
}


def validate_subcause(p: dict, out: dict) -> None:
    if out["subcause"] not in SUBCAUSES[p["cause"]]:
        raise ValueError(f"subcause {out['subcause']} is not one of {p['cause']}'s")


SUBCAUSE_TASK = llm.Task(name="stop_subcause", prompt_version="v2", schema_version="v1", system=SUBCAUSE_SYSTEM,
                         schema=SUBCAUSE_SCHEMA, subject_type="program_phase", validate=validate_subcause,
                         render=lambda p: f"Cause: {p['cause']}\nRegistry reason: {p['registry_reason']}\n\n"
                                          f"Text:\n{p['explanation']}",
                         model="claude-sonnet-5", effort="low", max_tokens=1000)

F_CODE = r"\bF(?:1a|1b|[1-9])\b"  # the efficacy attribution's failure codes, as the labeller wrote them
CODE = re.compile(F_CODE + r"|\bU\b")  # with U, which may also be a unit: the rewording tells them apart
CITATION = re.compile(r"NCT\d{8}|PMID:?\s?\d+|https?://\S+")
CODE_NAMES = {"F1a": "exposure or engagement too low, or dose capped", "F1b": "another drug on the target worked",
              "F2": "engaged, no benefit", "F3": "wrong population", "F4": "wrong endpoint or timing",
              "F5": "toxicity offset efficacy", "F6": "off-target toxicity", "F7": "the trial could not answer the question",
              "F8": "a business stop", "F9": "not an efficacy test", "U": "no engagement data"}
PLAIN_SYSTEM = f"""You edit an analyst's note about why a drug's efficacy failed so that a reader who does not know its codes can follow it. The note uses failure codes; replace each with its meaning, rewording the sentence only as much as that needs:
{chr(10).join(f"- {k} (also written F1 for F1a or F1b): {v}" if k == "F1a" else f"- {k}: {v}" for k, v in CODE_NAMES.items())}
Phrases like "the code is U" or "secondary F1a" become plain statements ("engagement is unknown", "it may also be that exposure was too low"). "U" in a dose or unit (e.g. "16 U") is not a code; keep it. Keep every fact, number, hedge, trial id, PMID and URL exactly; add nothing."""
PLAIN_SCHEMA = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"],
                "additionalProperties": False}


def validate_plain(p: dict, out: dict) -> None:
    left = re.findall(F_CODE, out["text"])
    if left:
        raise ValueError(f"codes left: {left}")
    lost = set(CITATION.findall(p["text"])) - set(CITATION.findall(out["text"]))
    if lost:
        raise ValueError(f"citations lost: {sorted(lost)[:3]}")


PLAIN_TASK = llm.Task(name="stop_explanation_plain", prompt_version="v1", schema_version="v1", system=PLAIN_SYSTEM,
                      schema=PLAIN_SCHEMA, subject_type="program_phase", validate=validate_plain,
                      render=lambda p: p["text"], model="claude-sonnet-5", effort="low", max_tokens=3000)


def describe_items(rows: list[tuple]) -> tuple[dict, dict]:
    """The stops each describe task decides: a subcause for a cause with SUBCAUSES that its row leaves open, and a
    plain rewording of an explanation that uses failure codes."""
    sub, plain = {}, {}
    for key, *_, reason, row in rows:
        if row["cause"] in SUBCAUSES and row["subcause"] is None and row["explanation"]:
            sub[key] = {"cause": row["cause"], "registry_reason": reason, "explanation": row["explanation"]}
        if row["explanation"] and CODE.search(row["explanation"]):
            plain[key] = {"text": row["explanation"]}
    return sub, plain


DESCRIBE_METHOD = "stop_description@v2"
DESCRIBE_DESCRIPTION = f"""Two passes over the rows stop_cause_assembly writes, without web search (model
{SUBCAUSE_TASK.model}, effort {SUBCAUSE_TASK.effort}). {SUBCAUSE_TASK.name}: for every stop whose cause is
{', '.join(SUBCAUSES)} and whose subcause the efficacy label does not set, the model reads the cause, the registry
reason and the explanation (the trial's stated reason, the traced source quote or the model's reasoning) and picks
the subcause the text states or directly implies from the cause's list, not_stated where it says no more; validation
rejects a subcause outside the cause's list. {PLAIN_TASK.name}: every explanation that uses an efficacy-attribution
failure code is reworded with the code's meaning; validation rejects a rewording that keeps a code or drops a trial
id, PMID or URL. The original text stays in the decision it came from."""


def describe(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, DESCRIBE_METHOD, "Subcause and plain explanation of each stop", DESCRIBE_DESCRIPTION,
                          ["stop_cause_assembly rows (pipeline.stop_causes.stop_rows)"],
                          {"subcause_task": SUBCAUSE_TASK.name, "plain_task": PLAIN_TASK.name,
                           "model": SUBCAUSE_TASK.model, "subcauses": SUBCAUSES})
        conn.commit()
    sub, plain = describe_items(stop_rows())
    for task, items in ((SUBCAUSE_TASK, sub), (PLAIN_TASK, plain)):
        run_id = llm.run(task, items)
        print(f"{task.name}: items={len(items)} decided={len(llm.decisions(run_id))} run={run_id}")


def assemble(_args) -> None:
    rows = stop_rows()
    sub, plain = describe_items(rows)
    sub, plain = llm.current_decisions(SUBCAUSE_TASK, sub), llm.current_decisions(PLAIN_TASK, plain)
    out = []
    with llm.connect() as conn, conn.cursor() as cur:
        mid = llm.record_method(cur, ASSEMBLE_METHOD, "Why each program stopped", ASSEMBLE_DESCRIPTION,
                                ["report.section1.failure_modes", "preclin.stop_signal",
                                 f"pv_evidence.llm_decision ({TASK.name}, efficacy attribution, "
                                 f"{SUBCAUSE_TASK.name}, {PLAIN_TASK.name})"],
                                {"registry_cause": REGISTRY_CAUSE, "cause": CAUSE, "code_cause": CODE_CAUSE,
                                 "unstated": list(UNSTATED), "subcauses": SUBCAUSES})
        for key, moiety, mondo, phase, reason, row in rows:
            if key in sub:
                row["subcause"] = sub[key][1]["subcause"]
                row["decision_ids"].append(int(sub[key][0]))
            if key in plain:
                row["explanation"] = plain[key][1]["text"]
                row["decision_ids"].append(int(plain[key][0]))
            out.append((moiety, mondo, phase, reason, *(row[c] for c in COLUMNS), mid))
        cur.execute("DELETE FROM preclin.stop")
        execute_values(cur, f"""INSERT INTO preclin.stop (moiety_id, mondo_id, phase, registry_reason,
                                  {', '.join(COLUMNS)}, method_id) VALUES %s""", out)
        conn.commit()
    print(pd.Series([f"{r[4]} / {r[5] or '-'}" for r in out]).value_counts().sort_index().to_string())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("signals").set_defaults(fn=signals)
    sub.add_parser("infer").set_defaults(fn=infer)
    sub.add_parser("validate").set_defaults(fn=validate_run)
    sub.add_parser("describe").set_defaults(fn=describe)
    sub.add_parser("assemble").set_defaults(fn=assemble)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
