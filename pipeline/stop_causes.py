"""Why each Phase 2/3 program stopped, where the registry does not say or says wrongly.

    python -m pipeline.stop_causes signals    # structured facts per stopped program -> preclin.stop_signal
    python -m pipeline.stop_causes infer      # LLM with web search: cause of each unexplained stop
    python -m pipeline.stop_causes validate   # the same on a seeded sample of stated stops, reason hidden
    python -m pipeline.stop_causes assemble   # final cause of every stop -> preclin.stop_cause

Section 1 gives each suspended program one reason from its own trials. For 40% of Phase 2/3
stops no reason is stated; a bare "sponsor decision" or an unspecified "other" reason says little
more; and the efficacy attribution (pipeline.attribution) found stops recorded as efficacy that
were not failed efficacy tests (codes F8, F9) or that toxicity ended (F6). Each of these is
inferred: the model reads the program's trials (records, posted results, linked papers), its
structured signals and the entity's other programs, then searches the web (company releases,
filings, pipeline updates, conference reports, news) and names the cause, how directly the
sources state it, and the sources. ClinicalTrials.gov is excluded from search, so the held-out
validation cannot read the reason it is scored against. Every URL a decision cites must be one
its searches returned. Each step records its method in preclin.analysis_method.
"""
from __future__ import annotations

import argparse
from collections import defaultdict

import numpy as np
import pandas as pd
from psycopg2.extras import execute_values

from pipeline import llm
from pipeline.stops import (CODE_CAUSE, INFERENCE_TASK, INFERENCE_VERSION, PHASES, REGISTRY_CAUSE, RELATED_DISEASE,
                            UNSTATED, inferred_causes, keys, labels, settled, stops)
from report import frame
from report.disease_match import Mondo

CAUSES = ["efficacy", "safety", "pk_formulation", "business_strategic", "company_event", "operational",
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
keyed by (entity, disease, phase): stopped_on is the latest end (completion, else primary completion, else start)
of the program's own trials; drug_continued_elsewhere is true when another program of the entity had a trial start
after that date or has an active trial; drug_approved_anywhere is true when the entity has any FDA approval;
sponsor_active_after is true when a lead sponsor of the program's trials started any registered trial more than
{SPONSOR_GAP_MONTHS} months after stopped_on (null without a sponsor name); target_peers_stopped counts other entities
sharing a primary target whose programs in a related disease (MONDO Lin similarity >= {RELATED_DISEASE}) were suspended
within {PEER_WINDOW_MONTHS} months of this one; trials_terminated, trials_completed, has_results and has_publication
describe the program's own trials. No LLM is involved."""


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

    targets = frame.query("SELECT moiety_id, target_id FROM preclin.moiety_target WHERE is_primary")
    tset = targets.groupby("moiety_id").target_id.apply(set)
    by_target = targets.groupby("target_id").moiety_id.apply(set)
    susp = rows[(rows.event == "suspended") & ~rows.credited].merge(progs[["program_id", "mondo_id"]], on="program_id")
    susp_by_entity = defaultdict(list)
    for m, d, e in zip(susp.moiety_id, susp.mondo_id, pd.to_datetime(susp.event_date)):
        if isinstance(d, str):
            susp_by_entity[m].append((d, e))
    mondo, window_days = Mondo(), PEER_WINDOW_MONTHS * 30.44
    peers = []
    for m, d, when in zip(stopped.moiety_id, stopped.mondo_id, stopped.stopped_on):
        others = {o for x in tset.get(m, ()) for o in by_target[x]} - {m}
        peers.append(sum(any(isinstance(d, str) and mondo.lin(od, d) >= RELATED_DISEASE
                             and abs((oe - when).days) <= window_days for od, oe in susp_by_entity[o])
                         for o in others) if pd.notna(when) else 0)
    stopped["target_peers_stopped"] = peers

    phase_trials = own[own.phase == own.stop_phase]
    pubs = set(frame.query("SELECT DISTINCT nct_id FROM preclin.trial_publication WHERE nct_id = ANY(%s)",
                           (sorted(set(phase_trials.nct_id)),)).nct_id)
    agg = phase_trials.groupby("key").agg(
        trials_terminated=("overall_status", lambda s: int(s.isin(["TERMINATED", "SUSPENDED"]).sum())),
        trials_completed=("overall_status", lambda s: int((s == "COMPLETED").sum())),
        has_results=("has_results", "any"),
        has_publication=("nct_id", lambda s: bool(set(s) & pubs)))
    stopped = stopped.merge(agg, left_on="key", right_index=True, how="left")
    for c in ("trials_terminated", "trials_completed"):
        stopped[c] = stopped[c].fillna(0).astype(int)
    for c in ("has_results", "has_publication"):
        stopped[c] = stopped[c].fillna(False).astype(bool)
    stopped["mondo_id"] = stopped.mondo_id.fillna("")
    return stopped


def signals(_args) -> None:
    modes, rows, progs, trials = stops()
    s = compute_signals(modes, rows, progs, trials)
    with llm.connect() as conn, conn.cursor() as cur:
        mid = llm.record_method(cur, SIGNALS_METHOD, "Structured signals of stopped programs", SIGNALS_DESCRIPTION,
                     ["preclin.dev_program", "preclin.dev_program_trial", "preclin.ctgov_study",
                      "preclin.moiety_target", "preclin.trial_publication", "preclin.dev_program_approval"],
                     {"phases": list(PHASES), "sponsor_gap_months": SPONSOR_GAP_MONTHS,
                      "peer_window_months": PEER_WINDOW_MONTHS, "related_disease_lin": RELATED_DISEASE})
        cur.execute("DELETE FROM preclin.stop_signal")
        execute_values(cur, """INSERT INTO preclin.stop_signal (moiety_id, mondo_id, phase, stopped_on,
                                 drug_continued_elsewhere, drug_approved_anywhere, sponsor_active_after,
                                 target_peers_stopped, trials_terminated, trials_completed, has_results,
                                 has_publication, method_id) VALUES %s""",
                       [(int(r.moiety_id), r.mondo_id, int(r.phase),
                         r.stopped_on.date() if pd.notna(r.stopped_on) else None,
                         bool(r.drug_continued_elsewhere), bool(r.drug_approved_anywhere),
                         None if r.sponsor_active_after is None else bool(r.sponsor_active_after),
                         int(r.target_peers_stopped), int(r.trials_terminated), int(r.trials_completed),
                         bool(r.has_results), bool(r.has_publication), mid) for r in s.itertuples()])
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
        "cause": {"type": "string", "enum": CAUSES},
        "secondary_causes": {"type": "array", "items": {"type": "string", "enum": CAUSES}},
        "evidence_kind": {"type": "string", "enum": EVIDENCE},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "stop_year": {"type": ["integer", "null"]},
        "quote": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
        "likely_cause": {"type": "string", "enum": CAUSES},
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
returns a cause ({', '.join(CAUSES)}), how directly sources state it ({', '.join(EVIDENCE)}), confidence, a
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
                "preclin.moiety_publication", "preclin.stop_signal", "preclin.efficacy_failure_attribution",
                "preclin.efficacy_attribution_search", "web search"], {"task": TASK.name, "prompt_version": TASK.prompt_version, "model": TASK.model,
                                "effort": TASK.effort, "tools": TOOLS, "causes": CAUSES, "evidence": EVIDENCE})
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


ASSEMBLE_METHOD = "stop_cause_assembly@v2"
ASSEMBLE_DESCRIPTION = f"""Final cause of every Phase 2/3 stop Section 1 counts. A stated registry reason is kept and
mapped to a cause ({'; '.join(f'{k} -> {v}' for k, v in REGISTRY_CAUSE.items())}), cause_source registry. A stop
for efficacy or exposure, registry or traced, whose final efficacy-attribution code (the web-search label where the
bundle label was U) is {' or '.join(f'{c} takes {v}' for c, v in CODE_CAUSE.items())}, cause_source corrected. A
registry efficacy stop coded F9 and a positive readout whose index trial's primary endpoint is not an efficacy
endpoint take the inferred cause, cause_source corrected. An unstated, bare sponsor-decision or unspecified other
reason takes the inferred cause, cause_source inferred; likely_cause and likely_basis carry the model's best
inference. If inference produced no validated decision (a refusal or invalid output) the cause is unknown with no
decision."""


def assemble(_args) -> None:
    modes = stops()[0]
    dec = inferred_causes().set_index("key")
    how = settled(modes, labels())
    rows = []
    with llm.connect() as conn, conn.cursor() as cur:
        mid = llm.record_method(cur, ASSEMBLE_METHOD, "Final cause of each Phase 2/3 stop", ASSEMBLE_DESCRIPTION,
                     ["report.section1.failure_modes", "preclin.efficacy_failure_attribution",
                      "preclin.efficacy_attribution_search", f"pv_evidence.llm_decision ({TASK.name})"],
                     {"registry_cause": REGISTRY_CAUSE, "code_cause": CODE_CAUSE, "unstated": list(UNSTATED)})
        for r in modes[modes.phase.isin(PHASES)].itertuples():
            row = (int(r.moiety_id), r.mondo_id if isinstance(r.mondo_id, str) else "", int(r.phase), r.reason)
            source = "inferred" if r.reason in UNSTATED else "corrected"
            settle = how.get(r.key, "infer" if r.reason in UNSTATED else None)
            if settle is None:
                rows.append((*row, REGISTRY_CAUSE[r.reason], "registry", None, None, [], None, mid, None, None))
            elif settle != "infer":
                rows.append((*row, settle, "corrected", None, None, [], None, mid, settle,
                             "efficacy attribution code"))
            elif r.key in dec.index:
                o = dec.at[r.key, "parsed_output"]
                rows.append((*row, o["cause"], source, o["evidence_kind"], o["confidence"], o["sources"],
                             int(dec.at[r.key, "llm_decision_id"]), mid, o["likely_cause"], o["likely_basis"]))
            else:
                rows.append((*row, "unknown", source, None, None, [], None, mid, "unknown", "no validated decision"))
        cur.execute("DELETE FROM preclin.stop_cause")
        execute_values(cur, """INSERT INTO preclin.stop_cause (moiety_id, mondo_id, phase, recorded_reason, cause,
                                 cause_source, evidence_kind, confidence, sources, llm_decision_id, method_id,
                                 likely_cause, likely_basis) VALUES %s""", rows)
        conn.commit()
    print(pd.Series([(r[5], r[4]) for r in rows]).value_counts().sort_index().to_string())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("signals").set_defaults(fn=signals)
    sub.add_parser("infer").set_defaults(fn=infer)
    sub.add_parser("validate").set_defaults(fn=validate_run)
    sub.add_parser("assemble").set_defaults(fn=assemble)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
