"""Why each program that stopped for efficacy failed: the target was never engaged,
the target was engaged and the disease did not respond, or something else.

    python -m pipeline.attribution literature   # PubMed: each entity's human pharmacology and its program diseases
    python -m pipeline.attribution label        # LLM: three pillars and failure code -> preclin.efficacy_failure_attribution
    python -m pipeline.attribution check        # LLM: independent re-derivation on a seeded sample (stepwise prompt)
    python -m pipeline.attribution search       # LLM with web search: Phase 2/3 programs the label left indeterminate

The cohort is every program Section 1 records as suspended for efficacy
(report.section1.failure_modes), keyed by (entity, disease, phase); the trial that
gave it that reason is the index trial. Each program's evidence bundle holds the
index trial (record, posted results, linked papers), the entity's other trials
with their classified outcomes, results posted by its Phase 1 trials, its FDA
approvals, other entities on the same primary target in the same or a related
disease, and PubMed abstracts on the entity's human pharmacology and on the
entity in the program's disease. The model judges the three pillars of Morgan et
al. (2012) only from the bundle, cites what it used, and codes the failure. The
plan is report/attribution_plan.md.
"""
from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from collections import defaultdict

import numpy as np
from psycopg2.extras import execute_values

from pipeline import llm
from pipeline.outcomes import eutils
from report import frame, section1
from report.disease_match import Mondo

PHARMACOLOGY_HITS = 15  # PubMed results kept per entity, relevance order
DISEASE_HITS = 8  # per (entity, program disease)
RELATED_DISEASE = 0.5  # Lin similarity at which another entity's disease counts as related
MAX_CODES = 6  # code names searched per entity
ABSTRACT_CHARS = 2000
RESULTS_CHARS = 4000  # posted results of the index trial
PHASE1_RESULTS_CHARS = 1500
MAX_PHASE1_RESULTS = 6
MAX_OTHER_TRIALS = 40
MAX_SAME_TARGET = 15
CHECK_SAMPLE = 150
CHECK_SEED = 20261026
EFFICACY_REASONS = ("efficacy: stated", "efficacy: primary endpoint not met")

PHARMACOLOGY_TERMS = ('pharmacodynamic*[tiab] OR "target engagement"[tiab] OR occupancy[tiab] OR '
                      '"proof of mechanism"[tiab] OR "proof-of-mechanism"[tiab] OR "first-in-human"[tiab] OR '
                      '"first in human"[tiab] OR "healthy volunteers"[tiab] OR "healthy subjects"[tiab] OR '
                      '"ascending dose"[tiab] OR "positron emission tomography"[tiab] OR "cerebrospinal fluid"[tiab] OR '
                      '"dose-response"[tiab] OR "dose-ranging"[tiab]')
NOT_REVIEWS = "NOT (review[pt] OR systematic review[pt] OR meta-analysis[pt])"  # primary human studies only


def subject_key(moiety_id: int, mondo_id: str | None, phase: int) -> str:
    """Key of an (entity, disease, phase); a program without a disease (None or NaN) has an empty disease."""
    return f"{moiety_id}|{mondo_id if isinstance(mondo_id, str) else ''}|{phase}"


def stops():
    """Every program Section 1 records as suspended, with the reason it assigns and its disease,
    one row per (entity, disease, phase), and the phase rows, programs and trials it was built from."""
    snap = frame.snapshot()
    progs, trials = frame.programs(), frame.program_trials()
    rows = section1.phase_rows(progs, trials, snap)
    modes = section1.failure_modes(rows, progs, trials, frame.trial_outcomes()).merge(
        progs[["program_id", "mondo_id"]], on="program_id")
    modes["key"] = [subject_key(m, d, p) for m, d, p in zip(modes.moiety_id, modes.mondo_id, modes.phase)]
    if modes.key.duplicated().any():
        raise ValueError(f"programs share an (entity, disease, phase): {modes[modes.key.duplicated()].key.tolist()[:5]}")
    return modes, rows, progs, trials


def cohort():
    """Section 1's efficacy-suspended programs with their index trial."""
    modes = stops()[0]
    return modes[modes.reason.isin(EFFICACY_REASONS)]


def search_names(name: str, codes: list[str]) -> list[str]:
    """The entity's name and up to MAX_CODES code names that carry a digit and are long
    enough not to match unrelated words (ASA, TF2)."""
    picked = [c for c in codes if re.search(r"\d", c) and len(re.sub(r"\W", "", c)) >= 5][:MAX_CODES]
    return [name, *picked]


def name_clause(names: list[str]) -> str:
    return "(" + " OR ".join(f'"{n.replace(chr(34), "")}"[tiab]' for n in names) + ")"


def esearch(query: str, retmax: int) -> list[str]:
    root = ET.fromstring(eutils("esearch", term=query, retmax=str(retmax), sort="relevance"))
    return [e.text for e in root.iter("Id")]


def efetch(pmids: list[str]) -> list[tuple]:
    rows = []
    for start in range(0, len(pmids), 200):
        root = ET.fromstring(eutils("efetch", id=",".join(pmids[start:start + 200]), retmode="xml"))
        for art in root.iter("PubmedArticle"):
            pmid = art.findtext(".//PMID")
            title = art.find(".//ArticleTitle")
            abstract = "\n".join("".join(a.itertext()) for a in art.iter("AbstractText"))
            year = (art.findtext(".//PubDate/Year") or art.findtext(".//PubDate/MedlineDate") or "")[:4]
            authors = [a.findtext("LastName") + " " + (a.findtext("Initials") or "")
                       for a in art.iter("Author") if a.findtext("LastName")]
            doi = next((i.text for i in art.iter("ArticleId") if i.get("IdType") == "doi"), None)
            rows.append((pmid, "".join(title.itertext()) if title is not None else "",
                         (authors[0].strip() + (" et al." if len(authors) > 1 else "")) if authors else None,
                         art.findtext(".//Journal/ISOAbbreviation") or art.findtext(".//Journal/Title"),
                         int(year) if year.isdigit() else None, doi, abstract or None))
    return rows


def literature(_args) -> None:
    """Search PubMed once per entity (human pharmacology) and once per (entity, program
    disease) of the cohort; a search already stored with the same query is not repeated. New papers are
    added to public.publications; existing rows are left as they are."""
    eff = cohort()
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT moiety_id, name, code_names FROM preclin.moiety WHERE moiety_id = ANY(%s)",
                    (sorted({int(m) for m in eff.moiety_id}),))
        names = {m: search_names(n, c) for m, n, c in cur.fetchall()}
        cur.execute("""SELECT term_id, label FROM preclin.ontology_term
                       WHERE ontology = 'MONDO' AND term_id = ANY(%s)""",
                    (sorted({d for d in eff.mondo_id if isinstance(d, str)}),))
        labels = dict(cur.fetchall())
        cur.execute("SELECT DISTINCT moiety_id, mondo_id, query_kind, query FROM preclin.moiety_publication")
        done = set(cur.fetchall())
    searches = [(m, "", "pharmacology", f"{name_clause(names[m])} AND ({PHARMACOLOGY_TERMS}) {NOT_REVIEWS}", PHARMACOLOGY_HITS)
                for m in sorted(names)]
    searches += [(int(m), d, "disease", f'{name_clause(names[int(m)])} AND "{labels[d]}"[tiab] {NOT_REVIEWS}', DISEASE_HITS)
                 for m, d in sorted({(int(m), d) for m, d in zip(eff.moiety_id, eff.mondo_id)
                                     if isinstance(d, str) and d in labels})]
    todo = [s for s in searches if s[:4] not in done]
    print(f"searches={len(searches)} to run={len(todo)}", flush=True)
    for start in range(0, len(todo), 50):
        chunk = todo[start:start + 50]
        hits = [(m, d, kind, q, esearch(q, n)) for m, d, kind, q, n in chunk]
        pmids = sorted({p for *_, ids in hits for p in ids})
        with llm.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT pmid FROM public.publications WHERE pmid = ANY(%s)", (pmids,))
            have = {r[0] for r in cur.fetchall()}
            papers = efetch([p for p in pmids if p not in have])
            if papers:
                execute_values(cur, """INSERT INTO public.publications (pmid, title, authors, journal, year, doi, abstract)
                                       VALUES %s ON CONFLICT (pmid) DO NOTHING""", papers)
            stored = have | {p[0] for p in papers}
            links = [(m, d, p, kind, rank, q) for m, d, kind, q, ids in hits
                     for rank, p in enumerate(ids, 1) if p in stored]
            # A search replaces whatever an earlier query for the same entity, disease and kind found.
            execute_values(cur, """DELETE FROM preclin.moiety_publication p USING (VALUES %s) AS s(m, d, k)
                                   WHERE p.moiety_id = s.m AND p.mondo_id = s.d AND p.query_kind = s.k""",
                           [(m, d, kind) for m, d, kind, _, _ in hits])
            if links:
                execute_values(cur, """INSERT INTO preclin.moiety_publication
                                         (moiety_id, mondo_id, pmid, query_kind, rank, query) VALUES %s
                                       ON CONFLICT DO NOTHING""", links)
            conn.commit()
        print(f"searched {start + len(chunk)}/{len(todo)} new papers={len(papers)}", flush=True)


PILLAR = ["adequate", "inferred_adequate", "inadequate", "no_human_data"]
CODES = ["F1a", "F1b", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "U"]

INTRO = """You explain why a drug development program stopped after a failed efficacy readout. You are given an evidence bundle: the program's index trial (the trial that failed), the drug's other trials with their classified outcomes, results posted by its Phase 1 trials, its FDA approvals, other drugs on the same target in the same or a related disease, and PubMed abstracts about the drug. Every source has an id (an NCT id or PMID:n).

"""
JUDGE = """Judge only from the bundle. Never fill a gap from memory: if the bundle does not show something, it was not shown. Cite the ids you relied on.

"""
RUBRIC = """First, the three pillars (Morgan et al. 2012), each for humans, at the doses taken into the index trial or comparable ones:
1. exposure: the drug reached its site of action (plasma exposure for a systemic target; CSF or tissue levels, or brain penetration, for a CNS or tissue target).
2. engagement: the drug bound or engaged its target (receptor occupancy, enzyme inhibition, target protein or ligand lowered, knockdown of the transcript).
3. pathway: the expected immediate functional or pathway effect followed (a downstream biomarker moved as the mechanism predicts).
For each answer:
- adequate: shown in humans at a level the sources treat as sufficient (e.g. high occupancy, near-complete inhibition, a clear dose-dependent biomarker change);
- inferred_adequate: not measured directly, but the drug met a clinical efficacy endpoint in another disease through the same target and tissue compartment at a comparable dose, so the pillar must have held there (state this in the rationale);
- inadequate: shown insufficient (low or partial occupancy, poor tissue penetration, biomarker unchanged), or the dose was capped by tolerability below the level needed;
- no_human_data: the bundle has no human evidence either way. Animal or in vitro data do not count.
Also: engagement_in_disease (was engagement shown in patients with this program's disease, not only in healthy volunteers or another disease), engagement_before_index (was that engagement evidence registered or published before the index trial started), dose_limited (tolerability capped the dose below what engagement needed).

Then the primary failure code:
- F1a: exposure or engagement inadequate, or dose capped by tolerability below adequate engagement. The mechanism was not properly tested.
- F1b: the molecule, not the target: another drug on the same target succeeded (approved or met a pivotal endpoint) in this disease or a close subtype, and no pillar evidence shows this drug engaged adequately.
- F2: engagement adequate or inferred_adequate, and at least one other pillar not inadequate, yet no clinical benefit: the target or mechanism does not drive the disease as tested.
- F3: wrong population or subtype: benefit confined to a subgroup, or the sources attribute the failure to patient selection or disease heterogeneity, with the mechanism engaged or not in question.
- F4: wrong endpoint or timing: a proximal or biomarker effect was shown in this disease and the clinical endpoint, duration or disease stage is what the sources blame.
- F5: efficacy offset by on-target toxicity.
- F6: off-target or molecule-specific toxicity ended the program.
- F7: trial design or execution: high placebo response, underpowered, operational problems, the sources say the trial could not answer the question.
- F8: commercial: the bundle shows the program stopped for business reasons and the readout was not a failure.
- F9: not an efficacy failure of the drug: the index trial met its primary endpoint, missed only a non-inferiority margin against an active drug, or was not an efficacy test of this drug.
- U: indeterminate. Engagement is no_human_data and nothing in the bundle separates a drug that never engaged from a target that does not matter. Use U whenever that is the case; it is a correct answer, not a failure.
Rules: F2 requires engagement adequate or inferred_adequate. F1a requires exposure or engagement inadequate, or dose_limited. F1b requires engagement not adequate. U requires engagement no_human_data. Pick the code the evidence supports most directly; list other codes that also apply in secondary_codes.

confidence: high when the sources state the reason or the pillars are measured directly; medium when inferred; low when the bundle is thin. rationale: at most 120 words, citing ids."""
SYSTEM = INTRO + JUDGE + RUBRIC

PILLAR_SCHEMA = {"type": "string", "enum": PILLAR}
SCHEMA = {
    "type": "object",
    "properties": {
        "exposure": PILLAR_SCHEMA, "engagement": PILLAR_SCHEMA, "pathway": PILLAR_SCHEMA,
        "engagement_in_disease": {"type": "boolean"},
        "engagement_before_index": {"type": "boolean"},
        "dose_limited": {"type": "boolean"},
        "primary_code": {"type": "string", "enum": CODES},
        "secondary_codes": {"type": "array", "items": {"type": "string", "enum": CODES}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "sources": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": ["exposure", "engagement", "pathway", "engagement_in_disease", "engagement_before_index",
                 "dose_limited", "primary_code", "secondary_codes", "confidence", "sources", "rationale"],
    "additionalProperties": False,
}


def source_ids(p: dict) -> set[str]:
    ids = {p["index"]["nct_id"], *(t["nct_id"] for t in p["trials"]), *(t["nct_id"] for t in p["phase1_results"])}
    return ids | {f"PMID:{a['pmid']}" for a in p["papers"]}


def validate(p: dict, out: dict) -> None:
    unknown = [s for s in out["sources"] if s not in source_ids(p)]
    if unknown:
        raise ValueError(f"cites sources not in the bundle: {unknown}")
    validate_codes(out)


def validate_codes(out: dict) -> None:
    """Reject a failure code that contradicts the pillars."""
    code, eng = out["primary_code"], out["engagement"]
    engaged = eng in ("adequate", "inferred_adequate")
    if code == "F2" and not engaged:
        raise ValueError(f"F2 with engagement {eng}")
    if code == "F1a" and not ("inadequate" in (out["exposure"], eng) or out["dose_limited"]):
        raise ValueError("F1a without an inadequate pillar or a dose limit")
    if code == "F1b" and eng == "adequate":
        raise ValueError("F1b with adequate engagement")
    if code == "U" and eng != "no_human_data":
        raise ValueError(f"U with engagement {eng}")


def render(p: dict) -> str:
    ix = p["index"]
    out = [f"Drug: {p['drug']} (codes: {', '.join(p['codes']) or 'none'}; modality: {p['modality']})",
           "Primary targets: " + ("; ".join(p["targets"]) or "none recorded"),
           f"Program disease: {p['disease']}", f"Phase the program stopped in: {p['phase']}",
           "FDA approvals of this drug: " + ("; ".join(p["approvals"]) or "none"),
           "",
           f"INDEX TRIAL {ix['nct_id']}: {ix['title']}",
           f"Phases {', '.join(ix['phases'])}; status {ix['status']}; start {ix['start']}; enrollment {ix['enrollment']}",
           f"Conditions: {'; '.join(ix['conditions'])}",
           f"Stated reason for stopping: {ix['why_stopped'] or '(none)'}",
           f"Classified: stop reason {ix['stop_reason']}; primary endpoint {ix['primary_endpoint']}; "
           f"endpoint class {ix['endpoint_class']}; evidence quote: {ix['evidence']}",
           f"Primary outcome measures: {ix['primary_outcomes']}",
           f"Posted results:\n{ix['results'] or '(none posted)'}",
           "",
           "OTHER TRIALS OF THIS DRUG (classified outcome where available):"]
    out += [f"- {t['nct_id']} phase {t['phase']} {t['start']} [{t['sponsor']}] {t['title']} | conditions: "
            f"{t['conditions']} | status {t['status']} | stop {t['stop_reason']} | primary {t['primary_endpoint']}"
            f" | endpoint class {t['endpoint_class']}" + (f" | quote: {t['evidence']}" if t["evidence"] else "")
            for t in p["trials"]] or ["(none)"]
    out += ["", "RESULTS POSTED BY PHASE 1 TRIALS OF THIS DRUG:"]
    out += [f"- {t['nct_id']} {t['start']} {t['title']}\n  primary outcomes: {t['primary_outcomes']}\n  {t['results']}"
            for t in p["phase1_results"]] or ["(none)"]
    out += ["", "OTHER DRUGS ON THE SAME PRIMARY TARGET IN THIS OR A RELATED DISEASE:"]
    out += [f"- {s}" for s in p["same_target"]] or ["(none)"]
    out += ["", "PUBMED ABSTRACTS:"]
    out += [f"[PMID:{a['pmid']}] ({a['year']}) {a['title']}\n{a['abstract']}" for a in p["papers"]] or ["(none)"]
    return "\n".join(out)


TASK = llm.Task(name="efficacy_failure_attribution", prompt_version="v1", schema_version="v1", system=SYSTEM,
                schema=SCHEMA, render=render, validate=validate, subject_type="program_phase",
                model="claude-opus-5-5", effort="high", max_tokens=6000)

SEARCH_JUDGE = """The bundle does not show human evidence of whether this drug engaged its target. Search the web for it: full-text papers (PubMed Central, journal sites), conference abstracts and posters, FDA and EMA review documents (Drugs@FDA reviews, EPARs), company presentations and press releases, and Phase 1 or pharmacology results published outside ClinicalTrials.gov. Look for, in humans: drug levels at the site of action, receptor occupancy, target enzyme inhibition, target protein or ligand lowering, transcript knockdown, and a downstream biomarker moving as the mechanism predicts; and for what the sponsor or investigators said about why the program failed. Search the drug's name and code names with words like pharmacodynamics, target engagement, occupancy, biomarker, first-in-human, phase 1, and with the program disease. Use at most a handful of searches; stop when you have the answer or the trail is cold.

From here on, "the bundle" means the bundle together with the pages your searches return. Judge only from them. Never fill a gap from memory. Cite bundle ids and the URLs of the pages you relied on, and put the decisive sentence from a source in quote (empty if none).

"""
SEARCH_SCHEMA = {**SCHEMA, "properties": {**SCHEMA["properties"], "quote": {"type": "string"}},
                 "required": [*SCHEMA["required"], "quote"]}
SEARCH_TOOLS = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 6},
                {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 4}]


def validate_search(p: dict, out: dict) -> None:
    retrieved = {llm.norm_url(u) for u in out.get("retrieved_urls", [])}
    unknown = [s for s in out["sources"] if s not in source_ids(p) and llm.norm_url(s) not in retrieved]
    if unknown:
        raise ValueError(f"cites sources it did not retrieve: {unknown[:3]}")
    validate_codes(out)


SEARCH_TASK = llm.Task(name="efficacy_attribution_search", prompt_version="v1", schema_version="v1",
                       system=INTRO + SEARCH_JUDGE + RUBRIC, schema=SEARCH_SCHEMA, render=render,
                       validate=validate_search, subject_type="program_phase", model="claude-opus-5-5",
                       effort="medium", max_tokens=16000, tools=SEARCH_TOOLS)


CHECK_SYSTEM = """You review one failed drug development program to decide whether the drug's target was ever properly tested in humans. You are given an evidence bundle with ids (NCT ids, PMID:n). Use only the bundle; when it does not show something, treat it as not shown. Cite the ids you used.

Work through these questions in order, writing a short note for each in `notes` before choosing anything:
Q1. Is there human evidence that the drug reached its site of action at the doses used in the failed (index) trial? (exposure)
Q2. Is there human evidence that it bound or engaged its target at those doses? (engagement)
Q3. Is there human evidence that the expected pathway or biomarker effect followed? (pathway)
For Q1-Q3 answer adequate, inferred_adequate (not measured, but the drug met a clinical efficacy endpoint in another disease through the same target and compartment at a comparable dose), inadequate (shown insufficient, or dose capped by tolerability) or no_human_data. Animal data do not count.
Q4. Did tolerability cap the dose below what engagement needed? (dose_limited)
Q5. Has another drug on the same target succeeded in this disease?
Q6. Did the index trial really fail on efficacy, or did it meet its endpoint, fail only a non-inferiority margin, or stop for business reasons?
Q7. Do the sources blame the population, the endpoint or timing, toxicity, or the trial's design or execution?

Only then choose the primary code:
F1a not adequately exposed or engaged (or dose-capped); F1b another drug on the target worked here and this one was not shown to engage; F2 engaged (adequate or inferred) yet no benefit; F3 wrong population or subtype; F4 wrong endpoint, duration or stage after a proximal effect in this disease; F5 on-target toxicity offset efficacy; F6 off-target or molecule-specific toxicity; F7 trial design or execution; F8 commercial stop, not a failed readout; F9 not an efficacy failure of the drug; U engagement unknown from the bundle, so no engagement and a wrong target cannot be told apart.
F2 needs engagement adequate or inferred_adequate; F1a needs an inadequate exposure or engagement, or dose_limited; F1b needs engagement not adequate; U needs engagement no_human_data."""

CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "notes": {"type": "string"},
        "exposure": PILLAR_SCHEMA, "engagement": PILLAR_SCHEMA, "pathway": PILLAR_SCHEMA,
        "dose_limited": {"type": "boolean"},
        "primary_code": {"type": "string", "enum": CODES},
        "sources": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["notes", "exposure", "engagement", "pathway", "dose_limited", "primary_code", "sources"],
    "additionalProperties": False,
}


def validate_check(p: dict, out: dict) -> None:
    validate(p, {**out, "engagement_in_disease": False, "engagement_before_index": False,
                 "secondary_codes": [], "confidence": "low", "rationale": ""})


CHECK_TASK = llm.Task(name="efficacy_failure_attribution_check", prompt_version="v1", schema_version="v1",
                      system=CHECK_SYSTEM, schema=CHECK_SCHEMA, render=render, validate=validate_check,
                      subject_type="program_phase", model="claude-sonnet-5", effort="high", max_tokens=6000)


def clip(text: str | None, n: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[:n] + " […]"


def outcome_text(outcomes) -> str:
    return "; ".join(f"{o.get('measure', '')} [{o.get('timeFrame', '')}]" for o in (outcomes or []))


def bundles(eff) -> dict[str, dict]:
    """Evidence bundle of every cohort program, keyed by subject_key."""
    moieties = sorted({int(m) for m in eff.moiety_id})
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT moiety_id, name, code_names, coalesce(modality, 'unknown')
                       FROM preclin.moiety WHERE moiety_id = ANY(%s)""", (moieties,))
        drug = {m: (n, c, mod) for m, n, c, mod in cur.fetchall()}
        cur.execute("""SELECT mt.moiety_id, t.symbol, mt.action, mt.target_id FROM preclin.moiety_target mt
                       JOIN public.targets t ON t.id = mt.target_id WHERE mt.is_primary
                       ORDER BY mt.moiety_id, t.symbol""")
        target_rows = cur.fetchall()
        cur.execute("SELECT term_id, label FROM preclin.ontology_term WHERE ontology = 'MONDO'")
        label = dict(cur.fetchall())
        cur.execute("""SELECT p.moiety_id, p.mondo_id, ap.first_approval_date, p.highest_phase,
                              ap.approved = 'yes', m.name
                       FROM preclin.dev_program p JOIN preclin.moiety m USING (moiety_id)
                       LEFT JOIN preclin.dev_program_approval ap USING (program_id)""")
        programs = cur.fetchall()
        cur.execute("""
            SELECT DISTINCT p.moiety_id, s.nct_id, dt.phase, s.start_date, s.lead_sponsor_class, s.brief_title,
                   s.conditions, s.overall_status, o.stop_reason, o.primary_endpoint, e.endpoint_class, o.evidence
            FROM preclin.dev_program p JOIN preclin.dev_program_trial dt USING (program_id)
            JOIN preclin.ctgov_study s USING (nct_id)
            LEFT JOIN preclin.trial_outcome o USING (nct_id) LEFT JOIN preclin.trial_endpoint e USING (nct_id)
            WHERE p.moiety_id = ANY(%s)""", (moieties,))
        trial_rows = cur.fetchall()
        cur.execute("""
            SELECT DISTINCT ON (p.moiety_id, s.nct_id) p.moiety_id, s.nct_id, s.start_date, s.brief_title,
                   s.primary_outcomes, r.summary
            FROM preclin.dev_program p JOIN preclin.dev_program_trial dt USING (program_id)
            JOIN preclin.ctgov_study s USING (nct_id) JOIN preclin.ctgov_result_summary r USING (nct_id)
            WHERE p.moiety_id = ANY(%s) AND s.phases && ARRAY['EARLY_PHASE1','PHASE1']
              AND NOT s.phases && ARRAY['PHASE2','PHASE3']
            ORDER BY p.moiety_id, s.nct_id""", (moieties,))
        phase1 = defaultdict(list)
        for m, nct, start, title, prim, summary in cur.fetchall():
            phase1[m].append({"nct_id": nct, "start": str(start), "title": title,
                              "primary_outcomes": outcome_text(prim), "results": clip(summary, PHASE1_RESULTS_CHARS)})
        index_ids = sorted(set(eff.nct_id))
        cur.execute("""
            SELECT s.nct_id, s.brief_title, s.phases, s.overall_status, s.start_date, s.enrollment, s.conditions,
                   s.why_stopped, o.stop_reason, o.primary_endpoint, o.evidence, e.endpoint_class,
                   s.primary_outcomes, r.summary
            FROM preclin.ctgov_study s LEFT JOIN preclin.trial_outcome o USING (nct_id)
            LEFT JOIN preclin.trial_endpoint e USING (nct_id) LEFT JOIN preclin.ctgov_result_summary r USING (nct_id)
            WHERE s.nct_id = ANY(%s)""", (index_ids,))
        index = {r[0]: r for r in cur.fetchall()}
        cur.execute("""SELECT tp.nct_id, a.pmid, a.year, a.title, a.abstract FROM preclin.trial_publication tp
                       JOIN public.publications a USING (pmid) WHERE tp.nct_id = ANY(%s) ORDER BY tp.nct_id, a.pmid""",
                    (index_ids,))
        index_papers = defaultdict(list)
        for nct, pmid, year, title, abstract in cur.fetchall():
            index_papers[nct].append({"pmid": pmid, "year": year, "title": title,
                                      "abstract": clip(abstract, ABSTRACT_CHARS)})
        cur.execute("""SELECT mp.moiety_id, mp.mondo_id, mp.query_kind, mp.rank, a.pmid, a.year, a.title, a.abstract
                       FROM preclin.moiety_publication mp JOIN public.publications a USING (pmid)
                       WHERE mp.moiety_id = ANY(%s) ORDER BY mp.moiety_id, mp.query_kind, mp.mondo_id, mp.rank""",
                    (moieties,))
        papers = defaultdict(list)
        for m, d, kind, rank, pmid, year, title, abstract in cur.fetchall():
            papers[(m, d)].append({"pmid": pmid, "year": year, "title": title,
                                   "abstract": clip(abstract, ABSTRACT_CHARS)})

    targets, target_ids, by_target = defaultdict(list), defaultdict(set), defaultdict(set)
    for m, symbol, action, tid in target_rows:
        targets[m].append(f"{symbol} ({action})")
        target_ids[m].add(tid)
        by_target[tid].add(m)
    approvals = defaultdict(list)
    progs_of = defaultdict(list)
    for m, d, first, highest, approved, name in programs:
        if approved and m in drug:
            approvals[m].append(f"{label.get(d, d)} ({first or 'date unknown'})")
        progs_of[m].append((d, highest, approved, name))
    trials = defaultdict(list)
    for m, nct, phase, start, sponsor, title, conds, status, stop, primary, ec, evidence in trial_rows:
        trials[m].append({"nct_id": nct, "phase": phase, "start": str(start), "sponsor": (sponsor or "").lower(),
                          "title": title, "conditions": "; ".join((conds or [])[:4]), "status": status,
                          "stop_reason": stop or "-", "primary_endpoint": primary or "-", "endpoint_class": ec or "-",
                          "evidence": clip(evidence, 300), "_labelled": primary is not None})
    mondo = Mondo()
    items = {}
    for r in eff.itertuples():
        m, d = int(r.moiety_id), r.mondo_id if isinstance(r.mondo_id, str) else ""
        ix = index[r.nct_id]
        others = sorted((t for t in {t["nct_id"]: t for t in trials[m]}.values() if t["nct_id"] != r.nct_id),
                        key=lambda t: (not t["_labelled"], t["phase"], t["start"], t["nct_id"]))[:MAX_OTHER_TRIALS]
        others = sorted(({k: v for k, v in t.items() if k != "_labelled"} for t in others),
                        key=lambda t: (t["start"], t["nct_id"]))
        same = []
        for o in sorted({o for t in target_ids[m] for o in by_target[t]} - {m}):
            for od, highest, approved, name in progs_of[o]:
                if d and od and mondo.lin(od, d) >= RELATED_DISEASE:
                    same.append((not approved, -highest, name, label.get(od, od), approved))
        same_target = [f"{name}: {dl}, furthest phase {-h}{', FDA-approved for it' if approved else ''}"
                       for _, h, name, dl, approved in sorted(set(same))[:MAX_SAME_TARGET]]
        bundle_papers = {a["pmid"]: a for a in index_papers[r.nct_id] + papers[(m, d)] + papers[(m, "")]}
        name, codes, modality = drug[m]
        items[r.key] = {
            "drug": name, "codes": codes[:MAX_CODES], "modality": modality, "targets": targets[m],
            "disease": label.get(d, "unspecified"), "phase": int(r.phase), "approvals": sorted(approvals[m]),
            "index": {"nct_id": ix[0], "title": ix[1], "phases": ix[2], "status": ix[3], "start": str(ix[4]),
                      "enrollment": ix[5], "conditions": ix[6] or [], "why_stopped": ix[7],
                      "stop_reason": ix[8] or "-", "primary_endpoint": ix[9] or "-", "evidence": clip(ix[10], 500),
                      "endpoint_class": ix[11] or "-", "primary_outcomes": outcome_text(ix[12]),
                      "results": clip(ix[13], RESULTS_CHARS)},
            "trials": others, "phase1_results": phase1[m][:MAX_PHASE1_RESULTS], "same_target": same_target,
            "papers": list(bundle_papers.values()),
        }
    return items


LITERATURE_METHOD = "pharmacology_literature@v1"
LITERATURE_DESCRIPTION = f"""PubMed (E-utilities, relevance order, reviews, systematic reviews and meta-analyses excluded)
searched once per entity with a program Section 1 records as stopped for efficacy: its name and up to {MAX_CODES} code
names (code names need a digit and five alphanumerics) with human-pharmacology terms (pharmacodynamics, target
engagement, occupancy, proof of mechanism, first-in-human, healthy volunteers, ascending dose, PET, CSF,
dose-response, dose-ranging), top {PHARMACOLOGY_HITS}; and once per (entity, program disease) with the disease's MONDO
label, top {DISEASE_HITS}. A changed query replaces the earlier results. Results: preclin.moiety_publication, papers in
public.publications."""
ATTRIBUTION_METHOD = "efficacy_attribution@v1"
ATTRIBUTION_DESCRIPTION = f"""Cohort: programs Section 1 records as suspended for efficacy (sponsor-stated, or the primary
endpoint missed), keyed by (entity, disease, phase); the trial that gave the reason is the index trial. Each program's
bundle holds the index trial (record, classified outcome, primary outcomes, posted results up to {RESULTS_CHARS}
characters, linked papers), up to {MAX_OTHER_TRIALS} other trials of the entity with classified outcomes, posted
results of up to {MAX_PHASE1_RESULTS} Phase 1 trials, FDA approvals, other entities on a shared primary target in a
disease with Lin similarity >= {RELATED_DISEASE}, and pharmacology_literature@v1 abstracts. The model (task
{TASK.name} {TASK.prompt_version}, {TASK.model}, effort {TASK.effort}) judges the three pillars of Morgan et al.
2012 in humans at the tested dose (exposure, engagement, pathway: adequate, inferred_adequate, inadequate,
no_human_data) and a failure code (F1a, F1b, F2-F9, U; report/attribution_plan.md), using only the bundle; validation
rejects citations outside the bundle and codes that contradict the pillars. Checks: {CHECK_TASK.name} (stepwise
prompt, {CHECK_TASK.model}) on a seeded sample of {CHECK_SAMPLE}, and a blind web adjudication of a seeded sample
(report/audits/attribution_adjudication.json)."""


def label(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, LITERATURE_METHOD, "PubMed retrieval of human pharmacology", LITERATURE_DESCRIPTION,
                          ["PubMed"], {"pharmacology_hits": PHARMACOLOGY_HITS, "disease_hits": DISEASE_HITS,
                                       "terms": PHARMACOLOGY_TERMS, "exclude": NOT_REVIEWS})
        llm.record_method(cur, ATTRIBUTION_METHOD, "Why efficacy failed: three pillars", ATTRIBUTION_DESCRIPTION,
                          ["preclin.ctgov_study", "preclin.trial_outcome", "preclin.trial_endpoint",
                           "preclin.ctgov_result_summary", "preclin.moiety_target", "preclin.dev_program_approval",
                           "preclin.moiety_publication"],
                          {"task": TASK.name, "prompt_version": TASK.prompt_version, "model": TASK.model,
                           "codes": CODES, "check_sample": CHECK_SAMPLE, "check_seed": CHECK_SEED})
        conn.commit()
    eff = cohort()
    items = bundles(eff)
    run_id = llm.run(TASK, items)
    index = dict(zip(eff.key, eff.nct_id))
    rows = []
    for key, did, o in llm.decisions(run_id):
        m, d, phase = key.split("|")
        rows.append((int(m), d, int(phase), index[key], o["exposure"], o["engagement"], o["pathway"],
                     o["engagement_in_disease"], o["engagement_before_index"], o["dose_limited"], o["primary_code"],
                     o["secondary_codes"], o["confidence"], o["sources"], did))
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.efficacy_failure_attribution")
        execute_values(cur, """INSERT INTO preclin.efficacy_failure_attribution
                                 (moiety_id, mondo_id, phase, index_nct_id, exposure, engagement, pathway,
                                  engagement_in_disease, engagement_before_index, dose_limited, primary_code,
                                  secondary_codes, confidence, sources, llm_decision_id) VALUES %s""", rows)
        conn.commit()
    print(f"programs={len(items)} labelled={len(rows)}")


SEARCH_PHASES = (2, 3)
SEARCH_METHOD = "efficacy_attribution_search@v1"
SEARCH_DESCRIPTION = f"""Cohort: Phase 2/3 programs that {ATTRIBUTION_METHOD} coded U (no human evidence of engagement in the
bundle). Each is labelled again (task {SEARCH_TASK.name} {SEARCH_TASK.prompt_version}, {SEARCH_TASK.model}, effort
{SEARCH_TASK.effort}) from the same bundle plus the web: the model searches (web_search up to 6 queries, web_fetch up
to 4 pages) for human exposure, engagement and pathway evidence and for stated reasons for failure in full-text papers,
conference reports, FDA and EMA reviews, company releases and Phase 1 results published outside the registry, then
answers the same pillars and failure codes as {ATTRIBUTION_METHOD} with the same rubric. Validation rejects a URL its
own searches did not return, an id outside the bundle, and codes that contradict the pillars. The search label
replaces the bundle label in the report; the bundle label stays in preclin.efficacy_failure_attribution and is
reported as a variant. Agreement with the blind web adjudication is reported on the programs both labelled."""


def search(_args) -> None:
    """Label the programs the bundle left indeterminate again, with web search."""
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, SEARCH_METHOD, "Why efficacy failed: web search for engagement", SEARCH_DESCRIPTION,
                          ["preclin.efficacy_failure_attribution", "preclin.ctgov_study", "preclin.trial_outcome",
                           "preclin.ctgov_result_summary", "preclin.moiety_publication", "web search"],
                          {"task": SEARCH_TASK.name, "prompt_version": SEARCH_TASK.prompt_version,
                           "model": SEARCH_TASK.model, "effort": SEARCH_TASK.effort, "tools": SEARCH_TOOLS,
                           "phases": list(SEARCH_PHASES)})
        conn.commit()
    u = frame.query("""SELECT moiety_id, mondo_id, phase FROM preclin.efficacy_failure_attribution
                       WHERE primary_code = 'U' AND phase = ANY(%s)""", (list(SEARCH_PHASES),))
    keys = {subject_key(m, d, p) for m, d, p in zip(u.moiety_id, u.mondo_id, u.phase)}
    eff = cohort()
    items = bundles(eff[eff.key.isin(keys)])
    run_id = llm.run(SEARCH_TASK, items)
    rows = []
    for key, did, o in llm.decisions(run_id):
        m, d, phase = key.split("|")
        rows.append((int(m), d, int(phase), o["exposure"], o["engagement"], o["pathway"], o["engagement_in_disease"],
                     o["engagement_before_index"], o["dose_limited"], o["primary_code"], o["secondary_codes"],
                     o["confidence"], o["quote"], o["sources"], did, SEARCH_METHOD))
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.efficacy_attribution_search")
        execute_values(cur, """INSERT INTO preclin.efficacy_attribution_search
                                 (moiety_id, mondo_id, phase, exposure, engagement, pathway, engagement_in_disease,
                                  engagement_before_index, dose_limited, primary_code, secondary_codes, confidence,
                                  quote, sources, llm_decision_id, method_id) VALUES %s""", rows)
        conn.commit()
    decided = sum(r[9] != "U" for r in rows)
    print(f"programs={len(items)} labelled={len(rows)} decided={decided} run={run_id}")


def check(_args) -> None:
    """Label a seeded random sample of the cohort again under CHECK_TASK."""
    eff = cohort()
    keys = sorted(eff.key)
    sample = np.random.default_rng(CHECK_SEED).choice(keys, size=min(CHECK_SAMPLE, len(keys)), replace=False)
    items = bundles(eff[eff.key.isin(set(sample))])
    run_id = llm.run(CHECK_TASK, items)
    print(f"sample={len(items)} decided={len(llm.decisions(run_id))} run={run_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("literature").set_defaults(fn=literature)
    sub.add_parser("label").set_defaults(fn=label)
    sub.add_parser("check").set_defaults(fn=check)
    sub.add_parser("search").set_defaults(fn=search)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
