"""Development programs built from the ClinicalTrials.gov snapshot.

    python -m pipeline.programs register   # trial -> intervention names / conditions (preclin.ctgov_study_*)
    python -m pipeline.programs roles      # role of each molecular entity in each trial (arm types, else LLM)
    python -m pipeline.programs purposes   # LLM: what each industry trial contributes to development
    python -m pipeline.programs indications  # LLM: group each entity's diseases into development indications
    python -m pipeline.programs build      # (molecular entity, indication) programs -> preclin.dev_program

A trial is in scope when it lists Early Phase 1, Phase 1, 2 or 3 (any sponsor,
any date). Intervention names (DRUG, BIOLOGICAL, GENETIC, COMBINATION_PRODUCT)
and condition strings are registered in preclin.drug and preclin.indication,
keyed by their lower-case alphanumerics (norm), so pipeline.drugs and
pipeline.indications resolve them.
"""
from __future__ import annotations

import argparse
import re
import uuid
from collections import Counter, defaultdict
from datetime import date

from psycopg2.extras import Json, execute_values

from pipeline import llm

IN_SCOPE_PHASES = ["EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3"]
DRUG_TYPES = {"DRUG", "BIOLOGICAL", "GENETIC", "COMBINATION_PRODUCT"}
COMPARATOR_ARMS = {"ACTIVE_COMPARATOR", "PLACEBO_COMPARATOR", "SHAM_COMPARATOR", "NO_INTERVENTION"}


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def mondo_ancestors(cur) -> defaultdict[str, set[str]]:
    """MONDO term -> all of its ancestor terms."""
    cur.execute("SELECT term_id, ancestor_id FROM preclin.ontology_ancestor WHERE ontology = 'MONDO'")
    ancestors = defaultdict(set)
    for term, anc in cur.fetchall():
        ancestors[term].add(anc)
    return ancestors


def register(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT nct_id, interventions, arm_groups, conditions FROM preclin.ctgov_study
                       WHERE phases && %s::text[]""", (IN_SCOPE_PHASES,))
        studies = cur.fetchall()
        drug_names, drug_syns = defaultdict(Counter), defaultdict(set)
        cond_names = defaultdict(Counter)
        study_drugs = {}
        study_conds = set()
        for nct, interventions, arms, conditions in studies:
            arm_type = {a.get("label"): a.get("type") or "UNKNOWN" for a in arms}
            for iv in interventions:
                key = norm(iv.get("name"))
                if iv.get("type") not in DRUG_TYPES or not key:
                    continue
                drug_names[key][iv["name"].strip()] += 1
                drug_syns[key].update(o.strip() for o in iv.get("otherNames") or [] if o.strip())
                seen = study_drugs.get((nct, key), (None, []))[1]
                types = {arm_type.get(l, "UNKNOWN") for l in iv.get("armGroupLabels") or []}
                study_drugs[(nct, key)] = (iv["type"], sorted(types | set(seen)), sorted(drug_syns[key])[:10])
            for c in conditions:
                if key := norm(c):
                    cond_names[key][c.strip()] += 1
                    study_conds.add((nct, key))

        execute_values(cur, """INSERT INTO preclin.drug (normalized_name, display_name, synonyms, resolved_via)
            VALUES %s ON CONFLICT (normalized_name) DO NOTHING""",
                       [(k, v.most_common(1)[0][0], sorted(drug_syns[k])[:10], "ctgov_snapshot")
                        for k, v in drug_names.items()], page_size=5000)
        execute_values(cur, """INSERT INTO preclin.indication (normalized_name, display_name, ct_gov_conditions)
            VALUES %s ON CONFLICT (normalized_name) DO NOTHING""",
                       [(k, v.most_common(1)[0][0], sorted(v)) for k, v in cond_names.items()], page_size=5000)
        cur.execute("SELECT normalized_name, drug_id FROM preclin.drug")
        drug_id = dict(cur.fetchall())
        cur.execute("SELECT normalized_name, indication_id FROM preclin.indication")
        ind_id = dict(cur.fetchall())
        cur.execute("DELETE FROM preclin.ctgov_study_drug")
        execute_values(cur, """INSERT INTO preclin.ctgov_study_drug
            (nct_id, drug_id, intervention_type, arm_types, other_names) VALUES %s""",
                       [(nct, drug_id[k], t, arms, syns) for (nct, k), (t, arms, syns) in study_drugs.items()],
                       page_size=10000)
        cur.execute("DELETE FROM preclin.ctgov_study_indication")
        execute_values(cur, "INSERT INTO preclin.ctgov_study_indication (nct_id, indication_id) VALUES %s",
                       [(nct, ind_id[k]) for nct, k in study_conds], page_size=10000)
        conn.commit()
    print(f"in-scope studies={len(studies)} drug names={len(drug_names)} conditions={len(cond_names)} "
          f"study-drug links={len(study_drugs)} study-condition links={len(study_conds)}")


ROLE_SYSTEM = """You read a clinical trial's arms and interventions and say what role each molecular entity plays in it.

- investigational: what the trial is developing or testing; the entity whose effect the trial is designed to measure. In a combination trial of two new agents, both are investigational. A new formulation, dose or schedule of an existing drug that the trial tests is investigational.
- background: given to every participant or added on in every arm as standard therapy (e.g. "drug X + standard chemotherapy vs placebo + standard chemotherapy": the chemotherapy is background), premedication, rescue or supportive medication, or a diagnostic/probe drug in a drug-interaction study other than the drug being studied.
- comparator: what the investigational agent is compared against (active control or standard-of-care arm drug that the investigational arm does not receive).

In a co-administration study (two vaccines, or a vaccine and a drug, given together to test interference, immunogenicity or safety of the combination), an already licensed product given alongside the one in development is background, even though the trial measures its response; it is investigational only when the trial is developing it for the listed condition.

Use the arm types and descriptions. Every entity listed must get exactly one role."""

ROLE_SCHEMA = {
    "type": "object",
    "properties": {"roles": {"type": "array", "items": {
        "type": "object",
        "properties": {"moiety": {"type": "string"},
                       "role": {"type": "string", "enum": ["investigational", "background", "comparator"]}},
        "required": ["moiety", "role"], "additionalProperties": False}}},
    "required": ["roles"],
    "additionalProperties": False,
}


def render_roles(p: dict) -> str:
    arms = "\n".join(f"- [{a.get('type')}] {a.get('label')}: {(a.get('description') or '')[:300]} "
                      f"(interventions: {', '.join(a.get('interventionNames') or [])})" for a in p["arms"])
    ivs = "\n".join(f"- {i['name']} [{i['type']}] -> {'; '.join(i['moieties'])}: {i['description'][:200]}"
                     for i in p["interventions"])
    entities = "\n".join(f"- {m}" for m in p["moieties"])  # one per line: entity names can contain commas
    return (f"Trial {p['nct_id']}: {p['title']}\nPhases: {', '.join(p['phases'])}\n\nArms:\n{arms or '(none listed)'}"
            f"\n\nInterventions (-> molecular entities):\n{ivs}\n\nEntities to classify, one per line:\n{entities}")


def validate_roles(p: dict, out: dict) -> None:
    got = sorted(r["moiety"] for r in out["roles"])
    if got != sorted(p["moieties"]):
        raise ValueError(f"roles cover {got}, expected {sorted(p['moieties'])}")


ROLE_TASK = llm.Task(name="trial_moiety_role", prompt_version="v3", schema_version="v1", system=ROLE_SYSTEM,
                     schema=ROLE_SCHEMA, render=render_roles, validate=validate_roles,
                     subject_type="trial", effort="low", max_tokens=2000)


def roles(_args) -> None:
    """Role of each molecular entity in each in-scope trial. Industry-sponsored
    trials with several entities go to the LLM. Every other trial is decided
    per entity from arm types: comparator when the entity appears only in
    comparator arms, investigational otherwise."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT sd.nct_id, m.moiety_id, m.name, d.display_name, sd.arm_types
            FROM preclin.ctgov_study_drug sd
            JOIN preclin.drug_moiety dm USING (drug_id)
            JOIN preclin.moiety m USING (moiety_id)
            JOIN preclin.drug d USING (drug_id)""")
        by_trial = defaultdict(list)
        for nct, *row in cur.fetchall():
            by_trial[nct].append(row)
        cur.execute("""SELECT nct_id, brief_title, phases, arm_groups, interventions,
                              lead_sponsor_class = 'INDUSTRY'
                       FROM preclin.ctgov_study WHERE nct_id = ANY(%s)""", (list(by_trial),))
        studies = {r[0]: r[1:] for r in cur.fetchall()}

    fixed, items, moiety_ids = [], {}, {}
    for nct, rows in by_trial.items():
        moieties, names = {}, defaultdict(set)
        for mid, mname, dname, arms in rows:
            moieties.setdefault(mid, (mname, set()))[1].update(arms)
            names[norm(dname)].add(mname)
        title, phases, arm_groups, interventions, industry = studies[nct]
        if len(moieties) == 1 or not industry:
            for mid, (_, arms) in moieties.items():
                role = "comparator" if arms and arms <= COMPARATOR_ARMS else "investigational"
                fixed.append((nct, mid, role, "arm_types", None))
            continue
        ivs = [{"name": iv.get("name"), "type": iv.get("type"),
                "description": iv.get("description") or "",
                "moieties": sorted(names.get(norm(iv.get("name")), []))}
               for iv in interventions if names.get(norm(iv.get("name")))]
        items[nct] = {"nct_id": nct, "title": title, "phases": phases, "arms": arm_groups,
                      "interventions": ivs, "moieties": sorted({m[0] for m in moieties.values()})}
        moiety_ids[nct] = {m[0]: mid for mid, m in moieties.items()}

    run_id = llm.run(ROLE_TASK, items)
    decided = [(nct, moiety_ids[nct][r["moiety"]], r["role"], "llm", did)
               for nct, did, out in llm.decisions(run_id) for r in out["roles"]]
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.ctgov_study_moiety")
        execute_values(cur, """INSERT INTO preclin.ctgov_study_moiety (nct_id, moiety_id, role, method, llm_decision_id)
                               VALUES %s""", fixed + decided, page_size=10000)
        conn.commit()
    print(f"trials={len(by_trial)} arm-types={len(fixed)} llm={len(items)} llm-decided={len(decided)}")


PURPOSE_SYSTEM = """You classify what an industry-sponsored clinical trial contributes to the development of its investigational drug(s).

purpose:
- indication_development: tests the drug in people with a particular disease or condition as part of developing it for that indication: dose finding, proof of concept, pivotal or confirmatory efficacy, a new population, line of therapy or combination within the indication, or long-term extension of such trials.
- multi_indication: one trial spanning several distinct indications with none as the single target: dose escalation in "advanced solid tumors" or in several named tumor types, basket, umbrella or tumor-agnostic designs, or a platform across diseases.
- early_development: first-in-human or early clinical pharmacology of a drug still in development (single or multiple ascending dose, healthy-volunteer or patient PK/PD, early safety) that does not itself establish an indication.
- product_support: clinical pharmacology or bridging work on a drug that is already marketed or past early development, done for labelling, manufacturing or market access rather than for an indication: bioequivalence or bioavailability, formulation, device or manufacturing-site bridging, food effect, drug-drug interaction, thorough QT, renal or hepatic impairment PK, ethnic bridging PK, generic or biosimilar comparative PK or equivalence.
- other: anything else (e.g. an observational protocol registered as interventional, a diagnostic or imaging use, an expanded-access program).

development_conditions: for indication_development and multi_indication, the listed conditions the trial develops the drug for, copied exactly as listed (leave out listed conditions that only describe the population, such as "Healthy"); otherwise an empty list.
Judge from the design, not from words alone: a Phase 1 in patients with one named disease that tests efficacy is indication_development; a Phase 3 bioequivalence study is product_support."""

PURPOSE_SCHEMA = {
    "type": "object",
    "properties": {
        "purpose": {"type": "string", "enum": ["indication_development", "multi_indication", "early_development",
                                               "product_support", "other"]},
        "development_conditions": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": ["purpose", "development_conditions", "rationale"],
    "additionalProperties": False,
}


def render_purpose(p: dict) -> str:
    conditions = "\n".join(f"- {c}" for c in p["conditions"])  # one per line: a condition can contain commas
    arms = "\n".join(f"- [{a.get('type')}] {a.get('label')}: {(a.get('description') or '')[:200]}" for a in p["arms"][:8])
    ivs = "\n".join(f"- {i.get('name')} [{i.get('type')}]: {(i.get('description') or '')[:200]}"
                     for i in p["interventions"][:8])
    return (f"Trial {p['nct_id']}: {p['title']}\nOfficial title: {p['official_title'] or '-'}\n"
            f"Sponsor: {p['sponsor']}; phases: {', '.join(p['phases'])}; status: {p['status']}; start: {p['start']}; "
            f"enrollment: {p['enrollment']}; healthy volunteers accepted: {p['healthy_volunteers']}; "
            f"primary purpose: {p['primary_purpose']}\n"
            f"Listed conditions, one per line:\n{conditions or '(none)'}\n"
            f"Interventions:\n{ivs or '(none)'}\nArms:\n{arms or '(none)'}\n"
            f"Brief summary: {p['summary'] or '(none)'}")


def validate_purpose(p: dict, out: dict) -> None:
    extra = set(out["development_conditions"]) - set(p["conditions"])
    if extra:
        raise ValueError(f"development_conditions not among listed conditions: {sorted(extra)[:3]}")


PURPOSE_TASK = llm.Task(name="trial_purpose", prompt_version="v2", schema_version="v1", system=PURPOSE_SYSTEM,
                        schema=PURPOSE_SCHEMA, render=render_purpose, validate=validate_purpose,
                        subject_type="trial", model="claude-opus-5-5", effort="low", max_tokens=1500)


PHASE_ROLE_SYSTEM = """You read one clinical trial registration and the investigational drugs linked to it, and decide whether the trial can mark a drug's entry into its registered phase.

extension: true when the trial enrolls only people who took part in earlier trials of the drug (an open-label extension, rollover or long-term continuation study), rather than recruiting new participants; false otherwise.
main_period_drugs: the listed drugs that the trial's main period tests (its first, randomized or primary-endpoint period), copied exactly as listed. Leave out a drug that enters only in a later sub-study, extension period or optional add-on to another drug's trial. For an extension study, list the drugs it continues.
Judge from the design described, not from words alone."""

PHASE_ROLE_SCHEMA = {
    "type": "object",
    "properties": {
        "extension": {"type": "boolean"},
        "main_period_drugs": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": ["extension", "main_period_drugs", "rationale"],
    "additionalProperties": False,
}


def render_phase_role(p: dict) -> str:
    arms = "\n".join(f"- [{a.get('type')}] {a.get('label')} ({', '.join(a.get('interventionNames') or [])}): "
                     f"{a.get('description') or ''}" for a in p["arms"])
    ivs = "\n".join(f"- {i.get('name')} (also {', '.join(i.get('otherNames') or []) or '-'})" for i in p["interventions"])
    drugs = "\n".join(f"- {d}" for d in p["drugs"])
    return (f"Trial {p['nct_id']}: {p['title']}\nOfficial title: {p['official_title'] or '-'}\n"
            f"Phases: {', '.join(p['phases'])}; status: {p['status']}; start: {p['start']}; enrollment: {p['enrollment']}; "
            f"allocation: {p['allocation']}; masking: {p['masking']}; model: {p['model']}\n"
            f"Investigational drugs linked to the trial, one per line:\n{drugs}\n"
            f"Interventions:\n{ivs or '(none)'}\nArms:\n{arms or '(none)'}\n"
            f"Brief summary: {p['summary'] or '(none)'}")


def validate_phase_role(p: dict, out: dict) -> None:
    extra = set(out["main_period_drugs"]) - set(p["drugs"])
    if extra:
        raise ValueError(f"main_period_drugs not among the listed drugs: {sorted(extra)[:3]}")


PHASE_ROLE_TASK = llm.Task(name="trial_phase_role", prompt_version="v1", schema_version="v1", system=PHASE_ROLE_SYSTEM,
                           schema=PHASE_ROLE_SCHEMA, render=render_phase_role, validate=validate_phase_role,
                           subject_type="trial", model="claude-sonnet-5", effort="low", max_tokens=1500)


def judge_phase_roles(ncts: set[str]) -> None:
    """Judge PHASE_ROLE_TASK for `ncts` and add the validated decisions to preclin.trial_phase_role."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT s.nct_id, s.brief_title, s.official_title, s.phases, s.overall_status, s.start_date, s.enrollment,
                   s.allocation, s.masking, s.intervention_model, s.interventions, s.arm_groups, s.brief_summary,
                   array_agg(m.name ORDER BY m.name), array_agg(m.moiety_id ORDER BY m.name)
            FROM preclin.ctgov_study s JOIN preclin.ctgov_study_moiety sm ON sm.nct_id = s.nct_id AND sm.role = 'investigational'
            JOIN preclin.moiety m ON m.moiety_id = sm.moiety_id
            WHERE s.nct_id = ANY(%s) GROUP BY s.nct_id""", (sorted(ncts),))
        rows = cur.fetchall()
    items, ids = {}, {}
    for (nct, title, official, phases, status, start, enrollment, allocation, masking, model, ivs, arms, summary,
         names, mids) in rows:
        items[nct] = {"nct_id": nct, "title": title, "official_title": official, "phases": phases, "status": status,
                      "start": str(start), "enrollment": enrollment, "allocation": allocation, "masking": masking,
                      "model": model, "interventions": ivs or [], "arms": arms or [], "summary": summary, "drugs": names}
        ids[nct] = dict(zip(names, mids))
    run_id = llm.run(PHASE_ROLE_TASK, items)
    out = [(key, parsed["extension"], sorted(ids[key][d] for d in parsed["main_period_drugs"]), decision)
           for key, decision, parsed in llm.decisions(run_id)]
    with llm.connect() as conn, conn.cursor() as cur:
        execute_values(cur, """INSERT INTO preclin.trial_phase_role (nct_id, extension, main_period_moieties, llm_decision_id)
                               VALUES %s ON CONFLICT (nct_id) DO UPDATE SET extension = EXCLUDED.extension,
                               main_period_moieties = EXCLUDED.main_period_moieties,
                               llm_decision_id = EXCLUDED.llm_decision_id""", out)
        conn.commit()


def purposes(_args) -> None:
    """Purpose of every in-scope industry trial with an investigational entity."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT s.nct_id, s.brief_title, s.official_title, s.lead_sponsor, s.phases, s.overall_status,
                   s.start_date, s.enrollment, s.healthy_volunteers, s.primary_purpose, s.conditions,
                   s.interventions, s.arm_groups, left(s.brief_summary, 1500)
            FROM preclin.ctgov_study s
            WHERE s.lead_sponsor_class = 'INDUSTRY' AND s.phases && %s::text[] AND s.overall_status <> 'WITHDRAWN'
              AND EXISTS (SELECT 1 FROM preclin.ctgov_study_moiety sm
                          WHERE sm.nct_id = s.nct_id AND sm.role = 'investigational')""", (IN_SCOPE_PHASES,))
        items = {r[0]: {"nct_id": r[0], "title": r[1], "official_title": r[2], "sponsor": r[3], "phases": r[4],
                        "status": r[5], "start": str(r[6]), "enrollment": r[7], "healthy_volunteers": r[8],
                        "primary_purpose": r[9], "conditions": r[10] or [], "interventions": r[11] or [],
                        "arms": r[12] or [], "summary": r[13]} for r in cur.fetchall()}
    run_id = llm.run(PURPOSE_TASK, items)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.trial_purpose")
        cur.execute("""INSERT INTO preclin.trial_purpose (nct_id, purpose, development_conditions, llm_decision_id)
                       SELECT subject_key, parsed_output->>'purpose',
                              ARRAY(SELECT jsonb_array_elements_text(parsed_output->'development_conditions')),
                              llm_decision_id
                       FROM pv_evidence.llm_decision WHERE decision_run_id = %s AND validation_status = 'validated'""",
                    (str(run_id),))
        conn.commit()
    print(f"trials={len(items)}")


INDICATION_SYSTEM = """You group the diseases a drug (molecular entity) has been tested in into development indications: the units a sponsor runs and reports as separate development programs, as industry trackers such as Biomedtracker record them.

Put a disease together with its subtypes, stages, lines of therapy, biomarker groups and settings when they are the same indication for development (prostate cancer, castration-resistant prostate carcinoma, metastatic prostate carcinoma and prostate adenocarcinoma are one indication; non-small cell lung carcinoma with squamous and non-squamous NSCLC; type 2 diabetes mellitus with its complications studied as glycaemic control). Keep apart diseases that are separate indications even when one ontology term contains the other: different cancer types or lymphoma subtypes (diffuse large B-cell vs follicular lymphoma), type 1 vs type 2 diabetes, Crohn's disease vs ulcerative colitis, a complication developed as its own indication (diabetic kidney disease vs type 2 diabetes; diabetic macular edema vs diabetes). A generic grouping term the trials used for a basket (cancer, solid tumor, neoplasm) is its own group.

Every disease belongs to exactly one group. The representative of a group is the member that names the indication, usually the broadest member that is still a single indication. Write members and representatives as the MONDO ids exactly as listed (e.g. "MONDO:0008315"), never as names."""

INDICATION_SCHEMA = {
    "type": "object",
    "properties": {"groups": {"type": "array", "items": {
        "type": "object",
        "properties": {"representative": {"type": "string"}, "members": {"type": "array", "items": {"type": "string"}}},
        "required": ["representative", "members"], "additionalProperties": False}}},
    "required": ["groups"],
    "additionalProperties": False,
}


def render_indications(p: dict) -> str:
    lines = "\n".join(f"- {d['mondo_id']}: {d['label']} ({d['n_trials']} trials, phases {d['phases']}"
                       + (f"; subtype of {', '.join(d['within'])}" if d["within"] else "") + ")"
                       for d in p["diseases"])
    return f"Entity: {p['entity']}\n\nDiseases (answer with these MONDO ids):\n{lines}"


def validate_indications(p: dict, out: dict) -> None:
    want = sorted(d["mondo_id"] for d in p["diseases"])
    got = sorted(m for g in out["groups"] for m in g["members"])
    if got != want:
        raise ValueError(f"groups cover {len(got)} diseases, expected {len(want)} once each")
    for g in out["groups"]:
        if g["representative"] not in g["members"]:
            raise ValueError(f"representative {g['representative']} not a member")


INDICATION_TASK = llm.Task(name="entity_indication_groups", prompt_version="v2", schema_version="v1",
                           system=INDICATION_SYSTEM, schema=INDICATION_SCHEMA, render=render_indications,
                           validate=validate_indications, subject_type="moiety", model="claude-opus-5-5",
                           effort="medium", max_tokens=32000)


def indications(_args) -> None:
    """Group each entity's diseases into development indications (entities with
    two or more diseases, one of which contains another)."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT sm.moiety_id, m.name, i.mondo_id, t.label, count(DISTINCT sm.nct_id),
                   array_agg(DISTINCT s.phases[array_upper(s.phases, 1)])
            FROM preclin.ctgov_study_moiety sm JOIN preclin.moiety m USING (moiety_id)
            JOIN preclin.ctgov_study s USING (nct_id)
            JOIN preclin.ctgov_study_indication si USING (nct_id) JOIN preclin.indication i USING (indication_id)
            JOIN preclin.ontology_term t ON t.term_id = i.mondo_id
            WHERE sm.role = 'investigational' AND i.mondo_id IS NOT NULL
              AND i.indication_kind IS DISTINCT FROM 'healthy_volunteers'
            GROUP BY 1, 2, 3, 4""")
        rows = cur.fetchall()
        ancestors = mondo_ancestors(cur)
    by_entity = defaultdict(list)
    names = {}
    for mid, name, mondo, label, n, phases in rows:
        names[mid] = name
        by_entity[mid].append({"mondo_id": mondo, "label": label, "n_trials": n,
                               "phases": ", ".join(sorted(p for p in phases if p))})
    items = {}
    for mid, ds in by_entity.items():
        ids = {d["mondo_id"] for d in ds}
        for d in ds:
            d["within"] = sorted(ids & ancestors[d["mondo_id"]])
        if any(d["within"] for d in ds):
            items[str(mid)] = {"entity": names[mid], "diseases": sorted(ds, key=lambda d: d["mondo_id"])}
    run_id = llm.run(INDICATION_TASK, items)
    out = [(int(mid), m, g["representative"], did) for mid, did, o in llm.decisions(run_id)
           for g in o["groups"] for m in g["members"]]
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.program_indication")
        execute_values(cur, """INSERT INTO preclin.program_indication (moiety_id, mondo_id, indication_mondo,
                                 llm_decision_id) VALUES %s""", out, page_size=5000)
        conn.commit()
    print(f"entities={len(items)} diseases={len(out)} grouped into "
          f"{len({(m, r) for m, _, r, _ in out})} indications")


ACTIVE_STATUSES = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"}
PHASE_NUM = {"EARLY_PHASE1": 1, "PHASE1": 1, "PHASE2": 2, "PHASE3": 3}


def build(_args) -> None:
    """(molecular entity, indication) programs from investigational trials. An
    indication is the MONDO disease representing a group of the entity's diseases
    (preclin.program_indication); ungrouped diseases are their own indication.

    A trial's phase is the highest phase it lists (Phase 1/2 counts as 2).
    Withdrawn trials never enrolled and are left out. A trial whose condition
    is an ancestor of another of the entity's diseases (e.g. "solid tumors"
    and "non-small cell lung carcinoma") attaches to the more specific
    programs instead of forming its own; a trial without a disease
    (healthy volunteers, or none listed) attaches to every program of the
    entity, or forms the entity's disease-unspecified program when it has none.
    A trial whose conditions are only symptoms, procedures or other conditions
    without a MONDO term (pain, contraception) attaches only to that
    unspecified program. Any condition with a MONDO term counts as a disease. Such a shared
    trial marks phase entry (marks_entry) only for programs whose own first
    trial had started by then and for the program(s) begun next after it: an
    indication the sponsor added later enters at its own first trial.

    Industry trials follow their purpose (preclin.trial_purpose): product-support
    and other trials are left out; an indication-development trial counts for the
    conditions it develops the drug for; an early-development trial is shared like
    a healthy-volunteer trial; a multi-indication basket is shared by the programs
    of the diseases it lists (marking entry for those under way or begun next), and
    belongs to the entity's unspecified program when none of them qualifies.

    A Phase 2 or 3 trial starts its phase for a program (starts_phase) unless it is an extension
    of earlier trials or the program's entity enters it only after its main period
    (preclin.trial_phase_role, judged by PHASE_ROLE_TASK for the trials that would set a phase
    start); either kind still attaches and counts as activity."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT max(source_version) FROM preclin.evidence_source_release "
                    "WHERE source_name = 'clinicaltrials_gov_api_v2'")
        snapshot = cur.fetchone()[0]
        cur.execute("SELECT nct_id, purpose, development_conditions FROM preclin.trial_purpose")
        purpose = {nct: (p, set(conds)) for nct, p, conds in cur.fetchall()}
        cur.execute("""SELECT nct_id, phases, start_date, primary_completion_date, completion_date,
                              overall_status, lead_sponsor, lead_sponsor_class, allocation, masking
                       FROM preclin.ctgov_study WHERE phases && %s::text[]
                         AND overall_status <> 'WITHDRAWN' AND start_date IS NOT NULL""", (IN_SCOPE_PHASES,))
        trials = {}
        for nct, phases, start, pcd, comp, status, sponsor, sponsor_class, allocation, masking in cur.fetchall():
            if purpose.get(nct, ("",))[0] in ("product_support", "other"):
                continue
            trials[nct] = {"phase": max(PHASE_NUM[p] for p in phases if p in PHASE_NUM), "start": start,
                           "active": status in ACTIVE_STATUSES, "end": comp or pcd or start,
                           "industry": sponsor_class == "INDUSTRY", "sponsor": sponsor,
                           "open_uncontrolled": allocation != "RANDOMIZED" and masking in (None, "NONE")}
        cur.execute("SELECT nct_id, moiety_id FROM preclin.ctgov_study_moiety WHERE role = 'investigational'")
        by_moiety = defaultdict(list)
        for nct, mid in cur.fetchall():
            if nct in trials:
                by_moiety[mid].append(nct)
        cur.execute("""SELECT si.nct_id, i.mondo_id, i.display_name, coalesce(i.ct_gov_conditions, '{}')
                       FROM preclin.ctgov_study_indication si JOIN preclin.indication i USING (indication_id)
                       WHERE i.indication_kind IS DISTINCT FROM 'healthy_volunteers'""")
        trial_diseases, trial_other = defaultdict(set), set()
        for nct, mondo, name, spellings in cur.fetchall():
            p, developed = purpose.get(nct, ("indication_development", set()))
            if p == "early_development" or (developed and not developed & {name, *spellings}):
                continue  # a condition the trial does not develop the drug for
            if mondo:
                trial_diseases[nct].add(mondo)
            else:
                trial_other.add(nct)
        baskets = {nct for nct, (p, _) in purpose.items() if p == "multi_indication"}
        cur.execute("SELECT moiety_id, mondo_id, indication_mondo FROM preclin.program_indication")
        indication = {(mid, d): rep for mid, d, rep in cur.fetchall()}
        ancestors = mondo_ancestors(cur)

    snap = date.fromisoformat(snapshot)

    def entry_programs(first: dict, start: date) -> set:
        """Programs a shared trial starting on `start` can mark entry for: those
        already under way and the one(s) begun next after it."""
        later = [f for f in first.values() if f > start]
        nxt = min(later, default=None)
        return {k for k, f in first.items() if f <= start or f == nxt}

    programs = {}   # (moiety, mondo) -> {nct: (attach, marks_entry)}
    for mid, ncts in by_moiety.items():
        direct = defaultdict(set)
        no_disease, other_condition, basket = [], [], []
        for nct in ncts:
            if nct in baskets:
                basket.append(nct)
            elif trial_diseases[nct]:
                for d in trial_diseases[nct]:
                    direct[indication.get((mid, d), d)].add(nct)
            elif nct in trial_other:
                other_condition.append(nct)
            else:
                no_disease.append(nct)
        specific = {d for d in direct if not any(d in ancestors[o] for o in direct if o != d)}
        first = {(mid, d): min(trials[n]["start"] for n in direct[d]) for d in specific}
        for d in sorted(specific):
            programs[(mid, d)] = dict.fromkeys(sorted(direct[d]), ("disease", True))
        for d in sorted(set(direct) - specific):
            covered = {k: f for k, f in first.items() if d in ancestors[k[1]]}
            for nct in direct[d]:
                lead = entry_programs(covered, trials[nct]["start"])
                for key in covered:
                    programs[key].setdefault(nct, ("broader_condition", key in lead))
        if other_condition:
            programs[(mid, None)] = dict.fromkeys(other_condition, ("non_disease_condition", True))
            first[(mid, None)] = min(trials[n]["start"] for n in other_condition)
        for nct in basket:  # shared by the programs of the diseases it lists, else the unspecified program
            listed = {k for k in first if any(indication.get((mid, d), d) == k[1] or d in ancestors[k[1]]
                                              for d in trial_diseases[nct])}
            lead = entry_programs({k: first[k] for k in listed}, trials[nct]["start"])
            for key in listed:
                programs[key].setdefault(nct, ("basket", key in lead))
            if not lead:
                programs.setdefault((mid, None), {})[nct] = ("basket", True)
        targets = [k for k in programs if k[0] == mid] or [(mid, None)]
        for nct in no_disease:
            lead = entry_programs({k: first[k] for k in targets if k in first}, trials[nct]["start"]) \
                if first else set(targets)
            for key in targets:
                programs.setdefault(key, {}).setdefault(nct, ("no_disease", key in lead))

    # Which trials can start a phase (preclin.trial_phase_role). A Phase 2 or 3 trial that would set a
    # program's phase start is judged when it could be an extension (open-label, not randomised) or
    # tests several investigational entities; judging one can expose the next trial, hence the loop.
    investigational = Counter(n for ncts in by_moiety.values() for n in ncts)

    def load_roles() -> dict:
        with llm.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT nct_id, extension, main_period_moieties FROM preclin.trial_phase_role")
            return {n: (ext, set(mids)) for n, ext, mids in cur.fetchall()}

    def starts_phase(nct: str, mid: int) -> bool:
        r = roles.get(nct)
        return r is None or (not r[0] and mid in r[1])

    roles = load_roles()
    while True:
        need = set()
        for (mid, _), attached in programs.items():
            for phase in (2, 3):
                eligible = [n for n in attached if trials[n]["phase"] == phase and starts_phase(n, mid)]
                if eligible:
                    first = min(trials[n]["start"] for n in eligible)
                    need |= {n for n in eligible if trials[n]["start"] == first and n not in roles
                             and (trials[n]["open_uncontrolled"] or investigational[n] > 1)}
        if not need:
            break
        judge_phase_roles(need)
        roles = load_roles()

    rows, links = [], []
    for (mid, mondo), attached in programs.items():
        ts = [trials[n] for n in attached]
        starting = [trials[n] for n in attached if trials[n]["phase"] == 1 or starts_phase(n, mid)]
        starts = {p: min((t["start"] for t in starting if t["phase"] == p), default=None) for p in (1, 2, 3)}
        industry = [t for t in ts if t["industry"]]
        sponsors = Counter(t["sponsor"] for t in industry)
        rows.append((mid, mondo, starts[1], starts[2], starts[3], min(t["start"] for t in ts),
                     max(t["phase"] for t in ts), len(ts), len(industry),
                     min((t["start"] for t in industry), default=None),
                     [s for s, _ in sponsors.most_common(5)],
                     min(snap, max(snap if t["active"] else t["end"] for t in ts)),
                     sum(t["active"] for t in ts)))
        links.append([(n, trials[n]["phase"], a, entry, trials[n]["phase"] == 1 or starts_phase(n, mid))
                      for n, (a, entry) in attached.items()])

    build_id = str(uuid.uuid4())
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO preclin.dev_program_build (build_id, code_commit, snapshot, parameters)
                       VALUES (%s, %s, %s, %s)""",
                    (build_id, llm.git_commit(), snap,
                     Json({"phases": IN_SCOPE_PHASES, "active_statuses": sorted(ACTIVE_STATUSES),
                           "combined_phase": "higher", "withdrawn": "excluded",
                           "shared_trial_entry": "programs under way or begun next",
                           "industry_trials": "by purpose (preclin.trial_purpose)",
                           "phase_start": "not extensions or later-period entities (preclin.trial_phase_role)",
                           "n_programs": len(rows), "n_links": sum(map(len, links))})))
        cur.execute("DELETE FROM preclin.dev_program")
        ids = execute_values(cur, """INSERT INTO preclin.dev_program
              (moiety_id, mondo_id, ph1_start, ph2_start, ph3_start, first_start, highest_phase, n_trials,
               n_industry_trials, first_industry_start, lead_sponsors, last_activity, n_active_trials, build_id)
            VALUES %s RETURNING program_id""",
            [r + (build_id,) for r in rows], page_size=5000, fetch=True)
        execute_values(cur, """INSERT INTO preclin.dev_program_trial (program_id, nct_id, phase, attach, marks_entry,
                                                                    starts_phase) VALUES %s""",
                       [(pid, *l) for (pid,), ls in zip(ids, links, strict=True) for l in ls], page_size=10000)
        conn.commit()
    print(f"build={build_id} programs={len(rows)} trial links={sum(map(len, links))} "
          f"entities={len(by_moiety)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("register").set_defaults(fn=register)
    sub.add_parser("roles").set_defaults(fn=roles)
    sub.add_parser("purposes").set_defaults(fn=purposes)
    sub.add_parser("indications").set_defaults(fn=indications)
    sub.add_parser("build").set_defaults(fn=build)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
