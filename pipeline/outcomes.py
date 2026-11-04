"""What happened in a trial: posted results and the stated reason for stopping.

    python -m pipeline.outcomes results    # cached CT.gov results sections -> preclin.ctgov_result_summary
    python -m pipeline.outcomes publications   # PubMed results papers for completed trials without posted results
    python -m pipeline.outcomes classify   # LLM: execution, stop reason and primary-endpoint outcome per trial
    python -m pipeline.outcomes endpoints  # LLM: the kind of endpoint each Phase 2/3 trial's primary measures
    python -m pipeline.outcomes biomarkers  # LLM: whether each phase-starting trial enrols by a molecular biomarker
    python -m pipeline.outcomes biomarkers-check  # the same on a seeded sample with another model

The results summary keeps, for every primary outcome measure, the
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
import time
import xml.etree.ElementTree as ET
from datetime import date

import numpy as np
import requests
from psycopg2.extras import Json, execute_values

from pipeline import llm
from pipeline.ctgov import CACHE as CTGOV_CACHE

TRIALS_FROM = date(2008, 1, 1)  # completed trials that start earlier get no outcome or endpoint label


def analysed(denoms: list[dict], units: str | None) -> dict[str, str]:
    """Group id -> number analysed, in the unit the measure selects (participants, eyes, lesions…)."""
    chosen = next((d for d in denoms if d.get("units") == units), denoms[0] if denoms else {})
    return {c["groupId"]: c.get("value") for c in chosen.get("counts", [])}


def summarize(results: dict) -> tuple[str, list[dict]]:
    lines, analyses = [], []
    measures = [m for m in (results.get("outcomeMeasuresModule") or {}).get("outcomeMeasures", [])
                if m.get("type") == "PRIMARY"]
    for m in measures:
        groups = {g["id"]: g.get("title", "") for g in m.get("groups", [])}
        units = m.get("denomUnitsSelected")
        measure_n = analysed(m.get("denoms", []), units)
        lines.append(f"PRIMARY: {m.get('title')} [{m.get('timeFrame', '')}] "
                     f"({m.get('paramType', '')}, {m.get('unitOfMeasure', '')})")
        for cls in m.get("classes", []):
            n = analysed(cls["denoms"], units) if cls.get("denoms") else measure_n
            for cat in cls.get("categories", []):
                vals = "; ".join(f"{groups.get(x['groupId'], x['groupId'])} (n={n.get(x['groupId'])}): "
                                 f"{x.get('value')}" + (f" ±{x['spread']}" if x.get("spread") else "")
                                 for x in cat.get("measurements", []))
                label = " / ".join(filter(None, [cls.get("title"), cat.get("title")]))
                lines.append(f"  {label + ': ' if label else ''}{vals}")
        for a in m.get("analyses", []):
            row = {k: a.get(k) for k in ("pValue", "statisticalMethod", "paramType", "paramValue",
                                          "ciLowerLimit", "ciUpperLimit", "nonInferiorityType")}
            row["groups"] = [groups.get(g, g) for g in a.get("groupIds", [])]
            analyses.append(row)
            lines.append(f"  analysis {' vs '.join(row['groups'])}: p={row['pValue']} {row['statisticalMethod'] or ''} "
                         f"{row['paramType'] or ''} {row['paramValue'] or ''} "
                         f"[{row['ciLowerLimit']}, {row['ciUpperLimit']}] {row['nonInferiorityType'] or ''}")
    for g in (results.get("adverseEventsModule") or {}).get("eventGroups", []):
        lines.append(f"AE {g.get('title', '')}: deaths {g.get('deathsNumAffected')}/{g.get('deathsNumAtRisk')}, "
                     f"serious {g.get('seriousNumAffected')}/{g.get('seriousNumAtRisk')}")
    return "\n".join(lines), analyses


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


EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def eutils(endpoint: str, **params) -> str:
    for attempt in range(6):
        try:
            r = requests.post(f"{EUTILS}/{endpoint}.fcgi", data={"db": "pubmed", **params}, timeout=120)
            r.raise_for_status()
            time.sleep(0.4)  # stay under 3 requests/second without an API key
            return r.text
        except requests.RequestException:
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"eutils {endpoint} failed")


def publications(_args) -> None:
    """Results papers for completed industry Phase 2/3 trials that started on or
    after TRIALS_FROM and have no posted results: PMIDs the registry lists as
    RESULT/DERIVED, plus PubMed articles indexing the NCT id as a
    ClinicalTrials.gov secondary identifier."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT nct_id, references_ FROM preclin.ctgov_study
                       WHERE lead_sponsor_class = 'INDUSTRY' AND overall_status = 'COMPLETED' AND NOT has_results
                         AND phases && ARRAY['PHASE2','PHASE3'] AND start_date >= %s""", (TRIALS_FROM,))
        trials = cur.fetchall()
    ncts = {n for n, _ in trials}
    links = {(n, r["pmid"], "ctgov_reference") for n, refs in trials for r in refs
             if r.get("pmid") and r.get("type") in ("RESULT", "DERIVED")}
    found = set()
    for start in range(0, len(trials), 100):
        batch = [n for n, _ in trials[start:start + 100]]
        xml = eutils("esearch", term=" OR ".join(f"{n}[si]" for n in batch), retmax=5000)
        found.update(e.text for e in ET.fromstring(xml).iter("Id"))
    pmids = sorted(found | {p for _, p, _ in links})
    rows = {}
    for start in range(0, len(pmids), 200):
        xml = eutils("efetch", id=",".join(pmids[start:start + 200]), retmode="xml")
        for art in ET.fromstring(xml).iter("PubmedArticle"):
            pmid = art.findtext(".//PMID")
            title = art.find(".//ArticleTitle")
            abstract = " ".join("".join(t.itertext()) for t in art.iter("AbstractText"))
            year = art.findtext(".//PubDate/Year") or (art.findtext(".//PubDate/MedlineDate") or "")[:4]
            authors = [a.findtext("LastName") + " " + (a.findtext("Initials") or "")
                       for a in art.iter("Author") if a.findtext("LastName")]
            doi = next((i.text for i in art.iter("ArticleId") if i.get("IdType") == "doi"), None)
            rows[pmid] = (pmid, "".join(title.itertext()) if title is not None else "",
                          (authors[0].strip() + (" et al." if len(authors) > 1 else "")) if authors else None,
                          art.findtext(".//Journal/ISOAbbreviation") or art.findtext(".//Journal/Title"),
                          int(year) if year.isdigit() else None, doi, abstract or None)
            for acc in art.iter("AccessionNumber"):
                if acc.text in ncts:
                    links.add((acc.text, pmid, "pubmed_secondary_id"))
    links = {(n, p, s) for n, p, s in links if p in rows}
    content = llm.canonical_json({"articles": sorted(rows.values()), "links": sorted(links)})
    with llm.connect() as conn, conn.cursor() as cur:
        llm.register_release(cur, "pubmed_trial_results", date.today().isoformat(), EUTILS, llm.sha256_text(content),
                             {"n_trials": len(trials), "n_articles": len(rows), "n_links": len(links)})
        execute_values(cur, """INSERT INTO public.publications (pmid, title, authors, journal, year, doi, abstract)
                               VALUES %s
                               ON CONFLICT (pmid) DO UPDATE SET abstract = EXCLUDED.abstract,
                                   doi = coalesce(publications.doi, EXCLUDED.doi)""", list(rows.values()))
        execute_values(cur, """INSERT INTO preclin.trial_publication (nct_id, pmid, link_source) VALUES %s
                               ON CONFLICT DO NOTHING""", sorted(links))
        conn.commit()
    print(f"trials={len(trials)} articles={len(rows)} links={len(links)} "
          f"trials with a paper={len({n for n, _, _ in links})}")


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
            f"Conditions: {'; '.join(p['conditions'])}\nInterventions: {'; '.join(p['interventions'])}\n"
            f"Stated reason for stopping: {p['why_stopped'] or '(none)'}\n"
            + (f"Brief summary (the record states no reason above; sponsors sometimes give it here):\n"
               f"{p['brief_summary']}\n" if p.get("brief_summary") else "")
            + f"\nPosted results:\n{p['results'] or '(no results posted)'}")


PUBLICATION_SYSTEM = CLASSIFY_SYSTEM.replace(
    "and posted results if any) and record what happened.",
    "the primary outcome measures as registered, and the published results paper(s) of the trial) and record what "
    "happened. The trial completed and posted no results on the registry; judge the primary endpoint from the "
    "publication abstracts given, and use no_results only when no abstract reports this trial's primary endpoint. "
    "Judge only from the text given: never fill in a result from memory. A linked paper may be a protocol, a pooled "
    "or post hoc analysis, a review or a different trial; use only a paper that reports this trial's prespecified "
    "primary endpoint. The registered primary outcome measures say what that endpoint is, whatever a paper calls "
    "its primary endpoint or emphasises in its abstract. When they are all descriptive safety, tolerability or PK "
    "measures with no comparison or success criterion (common in open-label extensions and dose-escalation "
    "trials), the answer is not_assessable whatever the authors conclude about safety or efficacy, including any "
    "efficacy comparison the paper reports.")


def render_outcomes(outcomes: list[dict]) -> str:
    """Registered outcome measures, numbered from 1: measure | description | time frame."""
    return "\n".join(f"{i}. {o.get('measure', '')}" + (f" | {o['description']}" if o.get("description") else "")
                     + (f" | time frame: {o['timeFrame']}" if o.get("timeFrame") else "")
                     for i, o in enumerate(outcomes, 1))


def render_publication(p: dict) -> str:
    return render_trial(p).replace(
        "Posted results:",
        f"Registered primary outcome measures:\n{render_outcomes(p['primary_outcomes']) or '(none registered)'}\n"
        "\nResults publications:", 1)


CLASSIFY_TASK = llm.Task(name="trial_outcome", prompt_version="v1", schema_version="v1", system=CLASSIFY_SYSTEM,
                         schema=CLASSIFY_SCHEMA, render=render_trial, subject_type="trial",
                         model="claude-opus-5-5", effort="medium", max_tokens=2000)


PUBLICATION_TASK = llm.Task(name="trial_outcome_from_publication", prompt_version="v3", schema_version="v1",
                            system=PUBLICATION_SYSTEM, schema=CLASSIFY_SCHEMA, render=render_publication,
                            subject_type="trial", model="claude-opus-5-5", effort="medium", max_tokens=2000)


def trial_payload(nct_id, title, phases, status, enrollment, start, completion, conditions, interventions,
                  why_stopped, results) -> dict:
    """The registry fields every outcome judgement sees, in the SELECT order of classify's queries."""
    return {"nct_id": nct_id, "title": title, "phases": phases, "status": status, "enrollment": enrollment,
            "start": str(start), "completion": str(completion), "conditions": conditions or [],
            "interventions": interventions or [], "why_stopped": why_stopped, "results": results}


def primary_outcomes(outcomes: list[dict] | None) -> list[dict]:
    """The registered primary outcome measures as a payload shows them: measure, description, time frame."""
    return [{k: o.get(k) for k in ("measure", "description", "timeFrame")} for o in outcomes or []]


def classify(_args) -> None:
    """Every in-scope trial that stopped early, whatever its sponsor or start date, and industry
    Phase 2/3 trials started since TRIALS_FROM that completed with posted results; completed
    Phase 2/3 trials without posted results that have a linked results paper are judged from the
    paper abstracts (PUBLICATION_TASK). The report filters to its own sponsors and years."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT s.nct_id, s.brief_title, s.phases, s.overall_status, s.enrollment, s.start_date,
                   s.completion_date, s.conditions,
                   (SELECT array_agg(i->>'name') FROM jsonb_array_elements(s.interventions) i),
                   s.why_stopped, r.summary,
                   CASE WHEN coalesce(s.why_stopped, '') = '' AND s.overall_status <> 'COMPLETED'
                        THEN s.brief_summary END
            FROM preclin.ctgov_study s LEFT JOIN preclin.ctgov_result_summary r USING (nct_id)
            WHERE s.phases && ARRAY['EARLY_PHASE1','PHASE1','PHASE2','PHASE3']
              AND (s.overall_status IN ('TERMINATED', 'WITHDRAWN', 'SUSPENDED')
                   OR (s.overall_status = 'COMPLETED' AND s.has_results AND s.lead_sponsor_class = 'INDUSTRY'
                       AND s.start_date >= %s AND s.phases && ARRAY['PHASE2','PHASE3']))""", (TRIALS_FROM,))
        items = {r[0]: {**trial_payload(*r[:11]), **({"brief_summary": r[11]} if r[11] else {})}
                 for r in cur.fetchall()}
        cur.execute("""
            SELECT s.nct_id, s.brief_title, s.phases, s.overall_status, s.enrollment, s.start_date,
                   s.completion_date, s.conditions,
                   (SELECT array_agg(i->>'name') FROM jsonb_array_elements(s.interventions) i), s.why_stopped,
                   (SELECT string_agg('PMID ' || a.pmid || ' (' || coalesce(a.year::text, '') || '): ' || a.title
                                      || E'\n' || coalesce(a.abstract, ''), E'\n\n' ORDER BY a.pmid)
                    FROM preclin.trial_publication tp JOIN public.publications a USING (pmid)
                    WHERE tp.nct_id = s.nct_id),
                   s.primary_outcomes
            FROM preclin.ctgov_study s
            WHERE s.lead_sponsor_class = 'INDUSTRY' AND s.start_date >= %s AND NOT s.has_results
              AND s.overall_status = 'COMPLETED' AND s.phases && ARRAY['PHASE2','PHASE3']
              AND EXISTS (SELECT 1 FROM preclin.trial_publication tp WHERE tp.nct_id = s.nct_id)""", (TRIALS_FROM,))
        pub_items = {r[0]: {**trial_payload(*r[:11]), "primary_outcomes": primary_outcomes(r[11])}
                     for r in cur.fetchall()}
    run_id = llm.run(CLASSIFY_TASK, items)
    pub_run = llm.run(PUBLICATION_TASK, pub_items) if pub_items else None
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
                  WHERE decision_run_id = ANY(%s::uuid[]) AND validation_status = 'validated') d""",
                    ([str(r) for r in (run_id, pub_run) if r],))
        conn.commit()
    print(f"trials={len(items)} from publications={len(pub_items)}")


ENDPOINT_CLASSES = ["B1_target_engagement", "B2_exploratory_biomarker", "B3_regulatory_surrogate",
                    "B4_objective_physiological", "B5_clinician_scale", "B6_patient_reported", "B7_disease_events",
                    "B8_hard_outcome", "B9_infection_cure", "O1_tumor_response", "O2_progression_free",
                    "O3_overall_survival", "not_efficacy"]

ENDPOINT_SYSTEM = """You classify the primary endpoint of a clinical trial from its registry entry: the conditions, the design and the primary outcome measures as registered (title, description, time frame), and the molecular targets of each investigational drug (human gene symbols with the drug's action, or why it has none). You are not told the drug's name.

First pick the governing primary outcome: with one primary, that one; with several, the first in a stated hierarchy, else the one the description says the trial is powered on, else the first listed efficacy measure. Answer its number (governing_index) and how many primary outcomes are listed (n_primaries).

purpose of the governing primary: efficacy (does the drug treat, prevent or change the disease), safety_tolerability (adverse events, tolerability, lab safety as the primary), pk_pd_dose (pharmacokinetics, exposure, dose finding, bioequivalence), other (feasibility, device performance, adherence, immunogenicity of a non-vaccine drug).

endpoint_class (efficacy only; otherwise not_efficacy):
- B1_target_engagement: the analyte is a listed target of an investigational drug, its immediate product or a direct readout of that target's pathway (receptor occupancy, enzyme activity, target protein or mRNA knockdown, free ligand, pSTAT for a JAK inhibitor, complement activity for a complement inhibitor, IgE for anti-IgE). Check the analyte against the listed targets: a disease measure that is not their own readout is B2 or B3, even when it is the usual readout of another drug class for the disease. With no target listed, use B1 only when the outcome text itself states that it measures the drug's target or pathway.
- B2_exploratory_biomarker: a disease-related lab, imaging or histology measure that regulators do not accept as a surrogate for approval in this disease (amyloid PET, neurofilament light, CRP or cytokines, MRI lesion counts in an exploratory setting, endoscopic or histologic scores used exploratorily, liver fat by MRI-PDFF).
- B3_regulatory_surrogate: a measure FDA accepts as a basis for approval in this disease (LDL-C for hypercholesterolaemia, HbA1c for diabetes, blood pressure for hypertension, viral load for HIV or hepatitis B/C, bone mineral density for osteoporosis, proteinuria or eGFR slope where accepted, serum phosphate or calcium, platelet count for ITP, hemoglobin for anemia, FEV1 for asthma/COPD bronchodilators, MRI gadolinium lesions in relapsing MS dose finding, uric acid for gout, biomarker reduction accepted for accelerated approval).
- B4_objective_physiological: an objective physiological or performance measure that is not an accepted surrogate here (FEV1 or FVC outside the above, six-minute walk distance, visual acuity, timed motor tests, ejection fraction, exercise capacity, body weight).
- B5_clinician_scale: a clinician-rated scale, composite or responder index, including remission defined by such an index (PASI-75, EASI-75, IGA, ACR20, DAS28, Mayo score, CDAI, EDSS, MDS-UPDRS, ADAS-Cog, CDR-SB, PANSS, MADRS, HAM-D, ALSFRS-R, SLEDAI/BICLA, clinical cure assessed by investigator outside infection).
- B6_patient_reported: a patient-reported symptom, function or quality-of-life measure (pain NRS, itch NRS, diaries, migraine days from diaries when reported as symptom scores, SGRQ, fatigue scales, PROMIS).
- B7_disease_events: recurrent or non-fatal disease events or their rate (exacerbations, relapses, flares, attacks, seizures or seizure frequency, monthly migraine days, bleeding episodes, infections, hypoglycaemia events as efficacy, confirmed disability progression).
- B8_hard_outcome: death, MACE or its components, heart-failure hospitalisation, clinical fracture, kidney failure, dialysis or transplant, decompensation, amputation, incident disease in a prevention trial; any composite that includes death or an irreversible organ event.
- B9_infection_cure: microbiological or clinical cure or eradication of an infection.
- O1_tumor_response (oncology): objective response rate, complete response, pathological complete response, MRD negativity, other tumour response criteria.
- O2_progression_free (oncology): progression-free, event-free, disease-free, relapse-free or metastasis-free survival, time to progression.
- O3_overall_survival (oncology): overall survival.

measurement_type of the governing primary: lab, imaging, clinician_rated, patient_reported, performance, event, other.
scale: continuous (change in a measure), responder (proportion reaching a threshold), time_to_event, count_rate, other.
Judge from the outcome text and the conditions; a trial's own wording ("primary efficacy endpoint") does not override what is measured."""

ENDPOINT_SCHEMA = {
    "type": "object",
    "properties": {
        "governing_index": {"type": "integer"},
        "n_primaries": {"type": "integer"},
        "purpose": {"type": "string", "enum": ["efficacy", "safety_tolerability", "pk_pd_dose", "other"]},
        "endpoint_class": {"type": "string", "enum": ENDPOINT_CLASSES},
        "measurement_type": {"type": "string", "enum": ["lab", "imaging", "clinician_rated", "patient_reported",
                                                        "performance", "event", "other"]},
        "scale": {"type": "string", "enum": ["continuous", "responder", "time_to_event", "count_rate", "other"]},
        "rationale": {"type": "string"},
    },
    "required": ["governing_index", "n_primaries", "purpose", "endpoint_class", "measurement_type", "scale",
                 "rationale"],
    "additionalProperties": False,
}


def render_endpoint(p: dict) -> str:
    targets = "\n".join(f"- {t}" for t in p["investigational_targets"]) or "(no investigational drug identified)"
    return (f"Conditions: {'; '.join(p['conditions'])}\nPhases: {', '.join(p['phases'])}; allocation: "
            f"{p['allocation']}; masking: {p['masking']}; model: {p['model']}\n\n"
            f"Targets of the investigational drug(s), one line per drug:\n{targets}\n\n"
            f"Primary outcome measures:\n{render_outcomes(p['primary_outcomes'])}")


def validate_endpoint(p: dict, out: dict) -> None:
    if not 1 <= out["governing_index"] <= len(p["primary_outcomes"]):
        raise ValueError(f"governing_index {out['governing_index']} of {len(p['primary_outcomes'])} outcomes")
    if (out["purpose"] == "efficacy") == (out["endpoint_class"] == "not_efficacy"):
        raise ValueError(f"purpose {out['purpose']} with class {out['endpoint_class']}")


ENDPOINT_TASK = llm.Task(name="trial_endpoint", prompt_version="v2", schema_version="v1", system=ENDPOINT_SYSTEM,
                         schema=ENDPOINT_SCHEMA, render=render_endpoint, validate=validate_endpoint,
                         subject_type="trial", model="claude-opus-5-5", effort="low", max_tokens=1500)


# Why an investigational entity has no primary target rows, by preclin.moiety.target_kind; any other kind,
# or none (targets not resolved), reads "target unknown".
NO_TARGET = {"pathogen": "acts on a pathogen, no human protein target", "no_single_target": "no single molecular target"}


def investigational_targets(drugs: list[tuple[str | None, str | None]] | None) -> list[str]:
    """One line per investigational entity, from (target_kind, primary targets as 'SYMBOL (action); ...'),
    sorted and without repeats so the payload does not depend on entity order."""
    return sorted({targets or NO_TARGET.get(kind, "target unknown") for kind, targets in drugs or []})


def endpoints(_args) -> None:
    """Industry Phase 2/3 trials started since TRIALS_FROM that belong to a development program, each shown
    with the primary targets of its investigational entities (pipeline.targets resolve) but not their names."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT s.nct_id, s.conditions, s.phases, s.allocation, s.masking, s.intervention_model, s.primary_outcomes,
                   (SELECT jsonb_agg(jsonb_build_array(m.target_kind,
                             (SELECT string_agg(t.symbol || ' (' || mt.action || ')', '; ' ORDER BY t.symbol)
                              FROM preclin.moiety_target mt JOIN public.targets t ON t.id = mt.target_id
                              WHERE mt.moiety_id = m.moiety_id AND mt.is_primary)))
                    FROM preclin.ctgov_study_moiety sm JOIN preclin.moiety m USING (moiety_id)
                    WHERE sm.nct_id = s.nct_id AND sm.role = 'investigational')
            FROM preclin.ctgov_study s
            WHERE s.lead_sponsor_class = 'INDUSTRY' AND s.phases && ARRAY['PHASE2','PHASE3']
              AND s.overall_status <> 'WITHDRAWN' AND s.start_date >= %s
              AND jsonb_array_length(s.primary_outcomes) > 0
              AND EXISTS (SELECT 1 FROM preclin.dev_program_trial dt WHERE dt.nct_id = s.nct_id)""", (TRIALS_FROM,))
        items = {r[0]: {"conditions": r[1] or [], "phases": r[2], "allocation": r[3], "masking": r[4], "model": r[5],
                        "primary_outcomes": primary_outcomes(r[6]),
                        "investigational_targets": investigational_targets(r[7])} for r in cur.fetchall()}
    run_id = llm.run(ENDPOINT_TASK, items)
    rows = [(nct, o["purpose"], o["endpoint_class"], o["governing_index"], o["measurement_type"], o["scale"], did)
            for nct, did, o in llm.decisions(run_id)]
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.trial_endpoint")
        execute_values(cur, """INSERT INTO preclin.trial_endpoint (nct_id, purpose, endpoint_class, governing_index,
                                 measurement_type, scale, llm_decision_id) VALUES %s""", rows,
                       page_size=5000)
        conn.commit()
    print(f"trials={len(items)} classified={len(rows)}")


BIOMARKER_FROM, BIOMARKER_TO = date(2008, 1, 1), date(2019, 12, 31)  # start dates of the trials labelled
ELIGIBILITY_CHARS = 8000
BIOMARKER_KINDS = ["germline_variant", "somatic_mutation", "expression", "signature", "other_molecular"]
BIOMARKER_CHECK_SAMPLE = 100
BIOMARKER_CHECK_SEED = 20261104
BIOMARKER_CHECK_OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "report", "audits", "biomarker_selection_check.json")

BIOMARKER_SYSTEM = """You read a clinical trial's registry record and decide whether the trial restricts enrolment to patients selected by a molecular biomarker.

A biomarker requirement is an inclusion criterion (or an exclusion criterion that leaves only marker-positive or marker-negative patients) on a measured molecular marker of the patient or their disease:
- germline_variant: an inherited variant or genotype (BRCA1/2 germline mutation, HLA-B*57:01, a CFTR genotype, a named mutation causing a hereditary disease when the trial requires it to be confirmed);
- somatic_mutation: an acquired mutation, fusion, amplification or rearrangement in the tumour or diseased tissue (EGFR exon 19 deletion, ALK fusion, BRAF V600E, KRAS G12C, FLT3-ITD, HER2 amplification by ISH);
- expression: a protein or RNA level in tissue or blood used to select patients (PD-L1 ≥ 1%, HER2 IHC 3+, ER/PR-positive, CD20-positive or CD33-positive disease);
- signature: a multi-gene or multi-analyte score (Oncotype DX recurrence score, a gene-expression classifier, MSI-high or tumour mutational burden);
- other_molecular: any other measured molecular marker (a specific antibody or autoantibody, a metabolite or enzyme deficiency demonstrated by assay, a pathogen genotype or resistance mutation).

Not a biomarker selection:
- a clinical diagnosis or histology, even when made with tests (type 2 diabetes, adenocarcinoma, multiple myeloma, chronic hepatitis C);
- disease stage, severity, scores or prior treatment;
- ordinary laboratory thresholds and safety labs (HbA1c, LDL cholesterol, eGFR, blood counts, liver enzymes, eosinophil counts, viral load);
- a biomarker that is only measured, stratified on or explored, not required for entry;
- marker status used only to exclude a small subgroup while everyone else is eligible (e.g. "no known EGFR mutation" in an all-comers lung cancer trial).

When the requirement depends on the disease's definition (a trial in "HER2-positive breast cancer", "Philadelphia chromosome-positive ALL", "CD19-positive lymphoma"), it is a biomarker selection.

Return selected, and when selected the biomarker as the record writes it, its kind, and a quote of the record text stating the requirement, copied exactly. When not selected, return kind "none" and nulls for biomarker and quote."""

BIOMARKER_SCHEMA = {
    "type": "object",
    "properties": {
        "selected": {"type": "boolean"},
        "biomarker": {"type": ["string", "null"]},
        "kind": {"type": "string", "enum": BIOMARKER_KINDS + ["none"]},
        "quote": {"type": ["string", "null"]},
    },
    "required": ["selected", "biomarker", "kind", "quote"],
    "additionalProperties": False,
}


def render_biomarker(p: dict) -> str:
    return (f"Title: {p['title']}\nConditions: {'; '.join(p['conditions'])}\n\nBrief summary:\n{p['summary']}\n\n"
            f"Eligibility criteria:\n{p['eligibility']}")


def squash(text: str) -> str:
    return " ".join(text.lower().split())


def validate_biomarker(p: dict, out: dict) -> None:
    filled = [out["biomarker"] is not None, out["kind"] != "none", out["quote"] is not None]
    if out["selected"] != all(filled) or any(filled) != all(filled):
        raise ValueError(f"selected={out['selected']} with biomarker/kind/quote filled={filled}")
    if out["selected"] and squash(out["quote"]) not in squash(" ".join([p["title"], *p["conditions"], p["summary"],
                                                                       p["eligibility"]])):
        raise ValueError(f"quote not in the record: {out['quote'][:120]}")


BIOMARKER_TASK = llm.Task(name="trial_biomarker_selection", prompt_version="v1", schema_version="v1",
                          system=BIOMARKER_SYSTEM, schema=BIOMARKER_SCHEMA, render=render_biomarker,
                          validate=validate_biomarker, subject_type="trial", model="claude-opus-5-5", effort="low",
                          max_tokens=1500)
BIOMARKER_CHECK_TASK = llm.Task(name="trial_biomarker_selection_check", prompt_version="v1", schema_version="v1",
                                system=BIOMARKER_SYSTEM, schema=BIOMARKER_SCHEMA, render=render_biomarker,
                                validate=validate_biomarker, subject_type="trial", model="claude-sonnet-5",
                                effort="medium", max_tokens=1500)


def biomarker_items() -> dict[str, dict]:
    """Industry trials that start a phase of a development program (dev_program_trial.starts_phase) and began
    in BIOMARKER_FROM..BIOMARKER_TO, the first trials of the phase entries the evidence analyses use."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT s.nct_id, s.brief_title, s.conditions, s.brief_summary, s.eligibility_criteria
            FROM preclin.ctgov_study s
            WHERE s.lead_sponsor_class = 'INDUSTRY' AND s.start_date BETWEEN %s AND %s
              AND EXISTS (SELECT 1 FROM preclin.dev_program_trial dt WHERE dt.nct_id = s.nct_id AND dt.starts_phase)""",
                    (BIOMARKER_FROM, BIOMARKER_TO))
        return {r[0]: {"title": r[1] or "", "conditions": r[2] or [], "summary": (r[3] or "")[:ELIGIBILITY_CHARS],
                       "eligibility": (r[4] or "(not registered)")[:ELIGIBILITY_CHARS]} for r in cur.fetchall()}


def biomarkers(args) -> None:
    """Label every trial of biomarker_items; with --limit, label a seeded sample of that size and print it."""
    items = biomarker_items()
    if args.limit:
        keys = np.random.default_rng(BIOMARKER_CHECK_SEED).choice(sorted(items), size=args.limit, replace=False)
        run_id = llm.run(BIOMARKER_TASK, {k: items[k] for k in keys})
        for nct, _, o in llm.decisions(run_id):
            print(nct, json.dumps(o))
        return
    run_id = llm.run(BIOMARKER_TASK, items)
    rows = [(nct, o["selected"], o["biomarker"], None if o["kind"] == "none" else o["kind"], o["quote"], did)
            for nct, did, o in llm.decisions(run_id)]
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.trial_biomarker_selection")
        execute_values(cur, """INSERT INTO preclin.trial_biomarker_selection
                                 (nct_id, selected, biomarker, kind, quote, llm_decision_id) VALUES %s""", rows,
                       page_size=5000)
        conn.commit()
    print(f"trials={len(items)} labelled={len(rows)} selected={sum(r[1] for r in rows)}")


def biomarkers_check(_args) -> None:
    """Label a seeded sample of BIOMARKER_CHECK_SAMPLE trials again with BIOMARKER_CHECK_TASK (another model) and
    write agreement, Cohen's kappa and every disagreement to BIOMARKER_CHECK_OUT."""
    items = biomarker_items()
    keys = np.random.default_rng(BIOMARKER_CHECK_SEED + 1).choice(sorted(items), size=BIOMARKER_CHECK_SAMPLE,
                                                                  replace=False)
    first = {k: o for k, (_, o) in llm.current_decisions(BIOMARKER_TASK, {k: items[k] for k in keys}).items()}
    run_id = llm.run(BIOMARKER_CHECK_TASK, {k: items[k] for k in first})
    second = {k: o for k, _, o in llm.decisions(run_id)}
    both = sorted(set(first) & set(second))
    a = np.array([first[k]["selected"] for k in both])
    b = np.array([second[k]["selected"] for k in both])
    po = float((a == b).mean())
    pe = float(a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean()))
    out = {"sample": len(both), "model": BIOMARKER_TASK.model, "check_model": BIOMARKER_CHECK_TASK.model,
           "selected_first": int(a.sum()), "selected_check": int(b.sum()), "agreement": po,
           "kappa": (po - pe) / (1 - pe) if pe < 1 else None,
           "disagreements": [{"nct_id": k, "first": first[k], "check": second[k]} for k in both
                             if first[k]["selected"] != second[k]["selected"]]}
    with open(BIOMARKER_CHECK_OUT, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "disagreements"}), f"disagreements={len(out['disagreements'])}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("results").set_defaults(fn=results)
    sub.add_parser("publications").set_defaults(fn=publications)
    sub.add_parser("classify").set_defaults(fn=classify)
    sub.add_parser("endpoints").set_defaults(fn=endpoints)
    p = sub.add_parser("biomarkers")
    p.add_argument("--limit", type=int, default=0, help="label only a seeded sample of this size and print it")
    p.set_defaults(fn=biomarkers)
    sub.add_parser("biomarkers-check").set_defaults(fn=biomarkers_check)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
