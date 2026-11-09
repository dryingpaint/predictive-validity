"""Why an efficacy stop failed when the drug engaged its target: what other drugs on the same target went on to do.

    python -m pipeline.target_history assess    # target history of every such stop -> preclin.stop_target_history
    python -m pipeline.target_history label     # LLM with web search: verdict on the stops history leaves open
    python -m pipeline.target_history validate  # the same, blind to target history, on stops history does settle
    python -m pipeline.target_history summary   # shares by target fate and verdict, and the validation agreement

The cohort is every Phase 2/3 stop in preclin.stop whose cause (or likely cause, where no source states one) is
efficacy and whose subcause is engaged_no_benefit. A drug that engaged its target and did nothing for the disease
can have failed because the target does not drive the disease, because it was tried at the wrong stage or in the
wrong patients, or because the drug or trial fell short where the target itself is sound. One failure rarely says
which; the later record of the target does. `assess` reads it from the database (approvals, trials that met or
missed their primary endpoint, biomarker selection). Where another drug on the target worked in this disease, or
where no drug on it was tried again, history alone cannot tell the explanations apart, so `label` reads the
program's sources and searches the web. `validate` checks the reading against history where history settles it.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd
from psycopg2.extras import execute_values

from pipeline import llm
from pipeline.stop_causes import BLOCKED_DOMAINS, bundles, load_signals, render as render_bundle
from pipeline.stops import keys, stops
from report import frame
from report.section3 import CLOSE, DECREASE, INCREASE, RELATED, neighbourhood
from report.windows import SECTION1

PHASES = (2, 3)
FATES = ["worked_here", "worked_here_selected", "worked_related", "worked_elsewhere_only", "never_worked_tried_again",
         "never_worked_single", "no_target"]
OPEN = ("worked_here", "worked_here_selected", "never_worked_single")  # fates history leaves open: `label` reads them
VERDICTS = ["target_not_causal", "wrong_stage_or_timing", "wrong_patients", "drug_inadequate", "trial_inadequate",
            "unclear"]
EVIDENCE = ["explicit", "results", "context", "none"]
# The verdicts each fate `validate` samples is consistent with: history says the target works here, so the drug,
# trial, patients or timing failed; works only in a related disease, so the stage or patients; never in this disease
# though it works elsewhere or was tried again, so the target is not causal here.
CONSISTENT = {"worked_here": {"drug_inadequate", "trial_inadequate", "wrong_patients", "wrong_stage_or_timing"},
              "worked_related": {"wrong_stage_or_timing", "wrong_patients"},
              "worked_elsewhere_only": {"target_not_causal"},
              "never_worked_tried_again": {"target_not_causal"}}
VALIDATION_PER_FATE = 25
VALIDATION_SEED = 20261108
MAX_PARTNERS = 12  # other drugs on the target shown to the model, most successful first

ASSESS_METHOD = "stop_target_history@v1"
ASSESS_DESCRIPTION = f"""Cohort: every Phase {'/'.join(map(str, PHASES))} stop in preclin.stop whose cause, or likely
cause where no source states one, is efficacy with subcause engaged_no_benefit. Partners: other entities sharing a
primary target (preclin.moiety_target, human Ensembl genes) whose action is compatible (both lower or both raise
function, or either is ambiguous). A partner worked in a disease when it is FDA-approved for it
(preclin.dev_program_approval) or a Phase 2/3 trial of it met its primary endpoint there (preclin.trial_outcome); the
success is biomarker-selected when its successful trials restricted enrolment by a biomarker
(preclin.trial_biomarker_selection). Diseases are this disease (MONDO Lin >= {CLOSE}), related (Lin >= {RELATED}) or
other. Fate, first that applies: worked_here (worked_here_selected when every success here was biomarker-selected and
this program was not); worked_related; worked_elsewhere_only; never_worked_tried_again (a partner also missed a
primary endpoint, stopped for futility or stopped for efficacy in a related disease); never_worked_single; no_target
(no resolved human primary target). success_first: a success here ended before this program's last trial. No LLM is
involved."""


@dataclass(frozen=True)
class Success:
    moiety_id: int
    mondo_id: str
    kind: str  # approved or met
    selected: bool
    ended: pd.Timestamp | None


def fate(here: list[Success], related: list[Success], elsewhere: list[Success], partners_failed: int,
         selected_entry: bool) -> str:
    """The target fate of one stop from its partners' successes in this, related and other diseases."""
    if here:
        return "worked_here_selected" if all(s.selected for s in here) and not selected_entry else "worked_here"
    if related:
        return "worked_related"
    if elsewhere:
        return "worked_elsewhere_only"
    return "never_worked_tried_again" if partners_failed else "never_worked_single"


def cohort() -> pd.DataFrame:
    """The engaged-without-benefit efficacy stops, with when they ended, their phase entry and whether the entry
    enrolled by biomarker (preclin.evidence_entry, US entries 2008-2019; null elsewhere, counted as not selected)."""
    d = frame.query("""
        SELECT c.moiety_id, c.mondo_id, c.phase, s.stopped_on, s.phase_entry, e.biomarker_selected
        FROM preclin.stop c JOIN preclin.stop_signal s USING (moiety_id, mondo_id, phase)
        LEFT JOIN preclin.evidence_entry e USING (moiety_id, mondo_id, phase)
        WHERE c.phase = ANY(%s) AND c.subcause = 'engaged_no_benefit'
          AND (c.cause = 'efficacy' OR (c.cause = 'unknown' AND c.guess = 'efficacy'))""", (list(PHASES),))
    d["key"] = keys(d)
    return d


def targets() -> pd.DataFrame:
    t = frame.query("""SELECT mt.moiety_id, t.ensembl_id AS ens, mt.action FROM preclin.moiety_target mt
                       JOIN public.targets t ON t.id = mt.target_id
                       WHERE mt.is_primary AND t.ensembl_id IS NOT NULL""")
    t["sign"] = np.where(t.action.isin(DECREASE), "-", np.where(t.action.isin(INCREASE), "+", "?"))
    return t


def partner_map(t: pd.DataFrame) -> dict[int, set[int]]:
    """Entity -> other entities on a shared primary target acting in a compatible direction."""
    on_gene = defaultdict(set)
    for m, e, s in zip(t.moiety_id, t.ens, t.sign):
        on_gene[e].add((m, s))
    out = defaultdict(set)
    for m, e, s in zip(t.moiety_id, t.ens, t.sign):
        out[m] |= {o for o, s2 in on_gene[e] if o != m and (s == s2 or "?" in (s, s2))}
    return out


def successes() -> dict[int, list[Success]]:
    """Entity -> its approvals and Phase 2/3 trials that met their primary endpoint, by disease."""
    met = frame.query("""
        SELECT p.moiety_id, p.mondo_id, max(coalesce(s.primary_completion_date, s.completion_date)) AS ended,
               bool_or(coalesce(b.selected, false)) AS selected
        FROM preclin.trial_outcome o JOIN preclin.ctgov_study s USING (nct_id)
        JOIN preclin.dev_program_trial dt USING (nct_id) JOIN preclin.dev_program p USING (program_id)
        LEFT JOIN preclin.trial_biomarker_selection b USING (nct_id)
        WHERE dt.phase >= 2 AND p.mondo_id IS NOT NULL AND o.primary_endpoint = 'met'
        GROUP BY 1, 2""")
    selected = {(m, d): bool(s) for m, d, s in zip(met.moiety_id, met.mondo_id, met.selected)}
    progs = frame.programs()
    appr = progs[progs.approved.eq("yes") & progs.mondo_id.notna()]
    out = defaultdict(list)
    for m, d, when in zip(appr.moiety_id, appr.mondo_id, appr.first_approval_date):
        out[m].append(Success(m, d, "approved", selected.get((m, d), False), pd.Timestamp(when) if pd.notna(when) else None))
    for r in met.itertuples():
        out[r.moiety_id].append(Success(r.moiety_id, r.mondo_id, "met", bool(r.selected),
                                        pd.Timestamp(r.ended) if pd.notna(r.ended) else None))
    return out


def failures() -> dict[int, set[str]]:
    """Entity -> diseases where a Phase 2/3 trial of it missed its primary endpoint or stopped for futility, or it
    stopped for efficacy."""
    f = frame.query("""
        SELECT DISTINCT p.moiety_id, p.mondo_id FROM preclin.trial_outcome o
        JOIN preclin.dev_program_trial dt USING (nct_id) JOIN preclin.dev_program p USING (program_id)
        WHERE dt.phase >= 2 AND p.mondo_id IS NOT NULL
          AND (o.primary_endpoint = 'not_met' OR o.stop_reason = 'efficacy_futility')
        UNION
        SELECT moiety_id, mondo_id FROM preclin.stop
        WHERE cause = 'efficacy' OR (cause = 'unknown' AND guess = 'efficacy')""")
    return f.groupby("moiety_id").mondo_id.apply(set).to_dict()


class History:
    """What every partner of a stopped entity did, split by disease relatedness."""

    def __init__(self):
        self.nb = neighbourhood()
        t = targets()
        self.has_target = set(t.moiety_id)
        self.partners = partner_map(t)
        self.succ = successes()
        self.fail = failures()
        self.approved = {m for m, ss in self.succ.items() if any(s.kind == "approved" for s in ss)}

    def split(self, moiety_id: int, mondo_id: str) -> tuple[list[Success], list[Success], list[Success], int]:
        close, rel = self.nb.terms(mondo_id, CLOSE), self.nb.terms(mondo_id, RELATED)
        ss = [s for o in self.partners.get(moiety_id, ()) for s in self.succ.get(o, ())]
        failed = sum(1 for o in self.partners.get(moiety_id, ()) if self.fail.get(o, set()) & rel)
        return ([s for s in ss if s.mondo_id in close], [s for s in ss if s.mondo_id in rel - close],
                [s for s in ss if s.mondo_id not in rel], failed)

    def row(self, r) -> dict:
        m = int(r.moiety_id)
        base = {"drug_approved_elsewhere": m in self.approved, "partners": len(self.partners.get(m, ()))}
        if m not in self.has_target:
            return {**base, "target_fate": "no_target", "success_first": None, "partners_failed": 0}
        here, related, elsewhere, failed = self.split(m, r.mondo_id)
        f = fate(here, related, elsewhere, failed, r.biomarker_selected == 1.0)
        first = None
        if f in ("worked_here", "worked_here_selected"):
            first = bool(pd.notna(r.stopped_on) and any(s.ended is not None and s.ended < pd.Timestamp(r.stopped_on)
                                                        for s in here))
        return {**base, "target_fate": f, "success_first": first, "partners_failed": failed}


def assess(_args) -> None:
    d = cohort()
    h = History()
    rows = pd.DataFrame([h.row(r) for r in d.itertuples()], index=d.index)
    d = d.join(rows)
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, ASSESS_METHOD, "Target history of engaged-without-benefit efficacy stops",
                          ASSESS_DESCRIPTION,
                          ["preclin.stop", "preclin.stop_signal", "preclin.evidence_entry", "preclin.moiety_target",
                           "preclin.dev_program_approval", "preclin.trial_outcome",
                           "preclin.trial_biomarker_selection", "MONDO"],
                          {"close": CLOSE, "related": RELATED, "phases": list(PHASES)})
        # verdicts are kept for stops still in the cohort; a stop that left it loses its row
        cur.execute("""CREATE TEMP TABLE th_new (moiety_id integer, mondo_id text, phase integer, target_fate text,
                       success_first boolean, drug_approved_elsewhere boolean, partners integer,
                       partners_failed integer) ON COMMIT DROP""")
        execute_values(cur, "INSERT INTO th_new VALUES %s", [
            (int(r.moiety_id), r.mondo_id, int(r.phase), r.target_fate,
             None if r.success_first is None else bool(r.success_first), bool(r.drug_approved_elsewhere),
             int(r.partners), int(r.partners_failed)) for r in d.itertuples()])
        cur.execute("""DELETE FROM preclin.stop_target_history h WHERE NOT EXISTS
                       (SELECT 1 FROM th_new n WHERE (n.moiety_id, n.mondo_id, n.phase) = (h.moiety_id, h.mondo_id, h.phase))""")
        cur.execute("""INSERT INTO preclin.stop_target_history (moiety_id, mondo_id, phase, target_fate, success_first,
                         drug_approved_elsewhere, partners, partners_failed, method_id)
                       SELECT n.*, %s FROM th_new n
                       ON CONFLICT (moiety_id, mondo_id, phase) DO UPDATE SET target_fate = EXCLUDED.target_fate,
                         success_first = EXCLUDED.success_first,
                         drug_approved_elsewhere = EXCLUDED.drug_approved_elsewhere,
                         partners = EXCLUDED.partners, partners_failed = EXCLUDED.partners_failed,
                         method_id = EXCLUDED.method_id""", (ASSESS_METHOD,))
        conn.commit()
    print(d.target_fate.value_counts().reindex(FATES, fill_value=0).to_string())


SYSTEM = """You work out why a drug failed in a disease although it engaged its target. A program is one drug developed for one disease; it stopped in the phase given because it did not work, and the evidence says the drug reached and engaged its target. You are given the program's trials (records, posted results, linked papers), the drug's other programs, and, when available, what other drugs on the same target did.

Search the web for what was learned: publications and conference reports of the trials, company statements, reviews and commentary on the target in this disease, and later results with other drugs on the target. Search for the drug's name and codes with the disease, and for the target with the disease. ClinicalTrials.gov is not available to search. Use at most a handful of searches.

Give the verdict:
- target_not_causal: the drug moved its target or pathway (a biomarker, a downstream marker, receptor occupancy) and the disease did not respond, or later evidence (human genetics, other drugs, mechanistic studies) shows the target does not drive this disease.
- wrong_stage_or_timing: the target drives the disease at another stage (earlier, prevention, acute vs chronic) and the trial treated too late or at the wrong time.
- wrong_patients: the target drives the disease only in a subgroup (a genotype, biomarker, subtype or phenotype) the trial did not select; e.g. a subgroup responded, or a later biomarker-selected trial worked.
- drug_inadequate: the target is sound here but this drug fell short where others worked: exposure in the diseased tissue, potency, selectivity, duration, or partial engagement.
- trial_inadequate: the trial could not show a benefit that was there: comparator, endpoint, size, duration, dose, placebo response or background therapy.
- unclear: no source supports a verdict.
verdict_evidence: explicit (a source states the explanation for this drug or this target in this disease), results (posted or published results show it, e.g. a biomarker moved and the clinical endpoint did not, or a subgroup responded), context (a reasoned inference from the target's record, e.g. every drug on the target failed in this disease while it works elsewhere), none (unclear).
A verdict other than unclear needs evidence other than none. Quote the decisive sentence when evidence is explicit. Cite only URLs your searches returned, NCT ids and PMIDs from the bundle. Prefer unclear to a verdict no source supports.
basis: one or two sentences on what the verdict rests on."""

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": VERDICTS},
        "evidence": {"type": "string", "enum": EVIDENCE},
        "basis": {"type": "string"},
        "quote": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "evidence", "basis", "quote", "sources"],
    "additionalProperties": False,
}


def validate_output(p: dict, out: dict) -> None:
    allowed = {t["nct_id"] for t in p["trials"]} | {f"PMID:{a['pmid']}" for a in p["papers"]}
    retrieved = {llm.norm_url(u) for u in out.get("retrieved_urls", [])}
    unknown = [s for s in out["sources"] if s not in allowed and llm.norm_url(s) not in retrieved]
    if unknown:
        raise ValueError(f"cites sources it did not retrieve: {unknown[:3]}")
    if (out["verdict"] == "unclear") != (out["evidence"] == "none"):
        raise ValueError(f"verdict {out['verdict']} with evidence {out['evidence']}")
    if out["evidence"] == "explicit" and not (out["quote"].strip() and out["sources"]):
        raise ValueError("explicit evidence without a quote and a source")


def render(p: dict) -> str:
    out = [render_bundle(p), "", "OTHER DRUGS ON THE SAME TARGET:"]
    if p["history"] is None:
        out.append("(not given)")
    else:
        out += [f"- {h}" for h in p["history"]] or ["(no other drug on the target is recorded)"]
    return "\n".join(out)


TOOLS = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 6, "blocked_domains": BLOCKED_DOMAINS},
         {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 3, "blocked_domains": BLOCKED_DOMAINS}]
TASK = llm.Task(name="target_failure_verdict", prompt_version="v1", schema_version="v1", system=SYSTEM, schema=SCHEMA,
                render=render, validate=validate_output, subject_type="program_phase", model="claude-opus-5-5",
                effort="medium", max_tokens=16000, tools=TOOLS)

LABEL_METHOD = "target_failure_verdict@v1"
LABEL_DESCRIPTION = f"""Cohort: the stops of {ASSESS_METHOD} whose fate history leaves open ({', '.join(OPEN)}) with a
phase entry in {SECTION1[0].year}-{SECTION1[1].year}. Input per stop (task {TASK.name} {TASK.prompt_version}, model
{TASK.model}, effort {TASK.effort}): the stop-cause inference bundle (drug, targets, disease, the program's trials with
posted results, linked papers, signals, the drug's other programs) and the record of up to {MAX_PARTNERS} other drugs on
the target (approvals and Phase 2/3 trials that met or missed their primary endpoint, by disease and year, with
biomarker selection). The model searches the web (web_search up to 6, web_fetch up to 3; {', '.join(BLOCKED_DOMAINS)}
blocked) and returns a verdict ({', '.join(VERDICTS)}), how directly sources support it ({', '.join(EVIDENCE)}), a
basis, a quote and sources. Validation rejects a decision citing a URL its searches did not return, a verdict without
evidence, or explicit evidence without a quote. Decisions are stored in pv_evidence.llm_decision and their verdicts in
preclin.stop_target_history."""
VALIDATE_METHOD = "target_failure_verdict_validation@v1"
VALIDATE_DESCRIPTION = f"""Blind check of {LABEL_METHOD}. A seeded sample (seed {VALIDATION_SEED}, up to
{VALIDATION_PER_FATE} per fate) of stops with a phase entry in {SECTION1[0].year}-{SECTION1[1].year} whose fate history
settles ({', '.join(CONSISTENT)}) is run through the same task with the other drugs on the target withheld. A decided
verdict agrees when it is one history allows (worked_here: drug, trial, patients or timing; worked_related: stage or
patients; worked_elsewhere_only and never_worked_tried_again: target not causal). Decisions are stored under the
task's subject keys with the suffix |blind."""


def history_lines(h: History, moiety_id: int, mondo_id: str, names: dict, label: dict) -> list[str]:
    """One line per partner: its successes and failures, this disease first."""
    close, rel = h.nb.terms(mondo_id, CLOSE), h.nb.terms(mondo_id, RELATED)

    def where(d: str) -> str:
        return "this disease" if d in close else "related" if d in rel else "other"
    lines = []
    for o in h.partners.get(moiety_id, ()):
        ss = sorted(h.succ.get(o, ()), key=lambda s: (s.mondo_id not in close, s.mondo_id not in rel))
        wins = [f"{'approved' if s.kind == 'approved' else 'met primary endpoint'} in {label.get(s.mondo_id, s.mondo_id)}"
                f" ({where(s.mondo_id)}{', biomarker-selected' if s.selected else ''}"
                f"{', ' + str(s.ended.year) if s.ended is not None else ''})" for s in ss[:4]]
        fails = sorted(h.fail.get(o, set()) & rel)
        lost = [f"failed in {label.get(d, d)} ({where(d)})" for d in fails[:3]]
        if wins or lost:
            lines.append((bool(wins), f"{names.get(o, o)}: " + "; ".join(wins + lost)))
    return [t for _, t in sorted(lines, key=lambda x: not x[0])][:MAX_PARTNERS]


def items_for(chosen: pd.DataFrame, h: History, with_history: bool, suffix: str = "") -> dict[str, dict]:
    modes = stops()[0]
    m = modes[modes.key.isin(set(chosen.key))]
    names = frame.query("SELECT moiety_id, name FROM preclin.moiety").set_index("moiety_id").name.to_dict()
    label = frame.query("SELECT term_id, label FROM preclin.ontology_term WHERE ontology = 'MONDO'") \
        .set_index("term_id").label.to_dict()
    out = {}
    for k, b in bundles(m, load_signals()).items():
        mid, d, _ = k.split("|")
        b["history"] = history_lines(h, int(mid), d, names, label) if with_history else None
        out[k + suffix] = b
    return out


def stored() -> pd.DataFrame:
    d = frame.query("""SELECT h.*, s.phase_entry FROM preclin.stop_target_history h
                       JOIN preclin.stop_signal s USING (moiety_id, mondo_id, phase)""")
    d["key"] = keys(d)
    d["headline"] = pd.to_datetime(d.phase_entry).between(pd.Timestamp(SECTION1[0]), pd.Timestamp(SECTION1[1]))
    return d


def label(_args) -> None:
    d = stored()
    chosen = d[d.headline & d.target_fate.isin(OPEN)]
    h = History()
    items = items_for(chosen, h, with_history=True)
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, LABEL_METHOD, "Why an engaged drug failed: verdict from sources", LABEL_DESCRIPTION,
                          ["preclin.stop_target_history", "preclin.ctgov_study", "preclin.ctgov_result_summary",
                           "preclin.trial_publication", "preclin.stop_signal", "web search"],
                          {"task": TASK.name, "prompt_version": TASK.prompt_version, "model": TASK.model,
                           "effort": TASK.effort, "tools": TOOLS, "verdicts": VERDICTS, "open": list(OPEN)})
        conn.commit()
    run_id = llm.run(TASK, items)
    decided = llm.decisions(run_id)
    with llm.connect() as conn, conn.cursor() as cur:
        execute_values(cur, """UPDATE preclin.stop_target_history h SET verdict = v.verdict,
                                 verdict_evidence = v.evidence, verdict_basis = v.basis, quote = nullif(v.quote, ''),
                                 sources = v.sources, llm_decision_id = v.decision, label_method_id = v.method
                               FROM (VALUES %s) AS v(moiety_id, mondo_id, phase, verdict, evidence, basis, quote,
                                                     sources, decision, method)
                               WHERE (h.moiety_id, h.mondo_id, h.phase) = (v.moiety_id, v.mondo_id, v.phase)""",
                       [(int(k.split("|")[0]), k.split("|")[1], int(k.split("|")[2]), o["verdict"], o["evidence"],
                         o["basis"], o["quote"], o["sources"], i, LABEL_METHOD) for k, i, o in decided],
                       template="(%s, %s, %s, %s, %s, %s, %s, %s::text[], %s::bigint, %s)")
        conn.commit()
    print(f"stops={len(items)} decided={len(decided)} run={run_id}")


def validate_sample(d: pd.DataFrame) -> list[str]:
    rng = np.random.default_rng(VALIDATION_SEED)
    picks = []
    for f in CONSISTENT:
        g = d[d.headline & d.target_fate.eq(f)].sort_values("key")
        picks += list(rng.choice(g.key.to_numpy(), size=min(VALIDATION_PER_FATE, len(g)), replace=False))
    return picks


def validate(_args) -> None:
    d = stored()
    picks = validate_sample(d)
    items = items_for(d[d.key.isin(set(picks))], History(), with_history=False, suffix="|blind")
    run_id = llm.run(TASK, items)
    a = agreement(blind_verdicts(str(run_id), d))
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, VALIDATE_METHOD, "Blind check of the target-failure verdict", VALIDATE_DESCRIPTION,
                          ["preclin.stop_target_history", "preclin.ctgov_study", "web search"],
                          {"seed": VALIDATION_SEED, "per_fate": VALIDATION_PER_FATE, "run": str(run_id),
                           "agreement": a})
        conn.commit()
    print(f"sample={len(items)} decided={a['decided']} agree={a['agree']} run={run_id}")


def blind_verdicts(run_id: str, d: pd.DataFrame) -> pd.DataFrame:
    """The blind run's verdicts with each stop's target fate."""
    return pd.DataFrame([(k.removesuffix("|blind"), o["verdict"]) for k, _, o in llm.decisions(run_id)],
                        columns=["key", "verdict"]).merge(d[["key", "target_fate"]], on="key")


def agreement(blind: pd.DataFrame) -> dict:
    """Of the blind decisions (columns target_fate, verdict), the share decided and the share of decided verdicts
    history allows, overall and per fate."""
    decided = blind[blind.verdict.ne("unclear")]
    ok = [v in CONSISTENT[f] for f, v in zip(decided.target_fate, decided.verdict)]
    per = {f: {"n": int(len(g)), "decided": int(g.verdict.ne("unclear").sum()),
               "agree": float(np.mean([v in CONSISTENT[f] for v in g.verdict[g.verdict.ne("unclear")]]))
               if g.verdict.ne("unclear").any() else None} for f, g in blind.groupby("target_fate")}
    return {"n": int(len(blind)), "decided": int(len(decided)), "agree": float(np.mean(ok)) if ok else None,
            "per_fate": per}


def summary(_args) -> None:
    d = stored()
    head = d[d.headline]
    print(f"stops={len(d)} with phase entry {SECTION1[0].year}-{SECTION1[1].year}: {len(head)}")
    c = head.target_fate.value_counts().reindex(FATES, fill_value=0)
    print(pd.DataFrame({"n": c, "share": (c / len(head)).round(3)}).to_string())
    print(pd.crosstab(head.target_fate, head.verdict.fillna("(not read)")).to_string())
    run = frame.query("SELECT parameters->>'run' AS run FROM preclin.analysis_method WHERE method_id = %s",
                      (VALIDATE_METHOD,))
    if len(run) and run.run[0]:
        blind = blind_verdicts(run.run[0], d)
        print(pd.crosstab(blind.target_fate, blind.verdict).to_string())
        print(agreement(blind))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(required=True)
    for name, fn in (("assess", assess), ("label", label), ("validate", validate), ("summary", summary)):
        sub.add_parser(name).set_defaults(fn=fn)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
