"""Development programs built from the ClinicalTrials.gov snapshot.

    python -m pipeline.programs register   # trial -> intervention names / conditions (preclin.ctgov_study_*)
    python -m pipeline.programs roles      # role of each molecular entity in each trial (arm types, else LLM)
    python -m pipeline.programs build      # (molecular entity, MONDO disease) programs -> preclin.dev_program

A trial is in scope when it lists Early Phase 1, Phase 1, 2 or 3 (any sponsor,
any date). Intervention names (DRUG, BIOLOGICAL, GENETIC, COMBINATION_PRODUCT)
and condition strings are registered in preclin.drug and preclin.indication,
keyed like every earlier row (lower-case alphanumerics), so pipeline.drugs and
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
    return re.sub(r"[^a-z0-9]", "", (text or "").lower().strip())


def in_scope_studies(cur):
    cur.execute("""SELECT nct_id, interventions, arm_groups, conditions FROM preclin.ctgov_study
                   WHERE phases && %s::text[]""", (IN_SCOPE_PHASES,))
    return cur.fetchall()


def register(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        studies = in_scope_studies(cur)
        drug_names, drug_syns = defaultdict(Counter), defaultdict(set)
        cond_names = defaultdict(Counter)
        study_drugs = {}
        study_conds = set()
        for nct, interventions, arms, conditions in studies:
            arm_type = {a.get("label"): a.get("type") or "UNKNOWN" for a in arms}
            for iv in interventions:
                if iv.get("type") not in DRUG_TYPES or not norm(iv.get("name")):
                    continue
                key = norm(iv["name"])
                drug_names[key][iv["name"].strip()] += 1
                drug_syns[key].update(o.strip() for o in iv.get("otherNames") or [] if o.strip())
                types = sorted({arm_type.get(l, "UNKNOWN") for l in iv.get("armGroupLabels") or []})
                prev = study_drugs.get((nct, key))
                study_drugs[(nct, key)] = (iv["type"], sorted(set(types) | set(prev[1] if prev else [])),
                                           sorted(drug_syns[key])[:10])
            for c in conditions:
                if norm(c):
                    cond_names[norm(c)][c.strip()] += 1
                    study_conds.add((nct, norm(c)))

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
    ivs = "\n".join(f"- {i['name']} [{i['type']}] -> {', '.join(i['moieties'])}: {i['description'][:200]}"
                     for i in p["interventions"])
    return (f"Trial {p['nct_id']}: {p['title']}\nPhases: {', '.join(p['phases'])}\n\nArms:\n{arms or '(none listed)'}"
            f"\n\nInterventions (-> molecular entities):\n{ivs}\n\nEntities to classify: {', '.join(p['moieties'])}")


def validate_roles(p: dict, out: dict) -> None:
    got = sorted(r["moiety"] for r in out["roles"])
    if got != sorted(p["moieties"]):
        raise ValueError(f"roles cover {got}, expected {sorted(p['moieties'])}")


ROLE_TASK = llm.Task(name="trial_moiety_role", prompt_version="v1", schema_version="v1", system=ROLE_SYSTEM,
                     schema=ROLE_SCHEMA, render=render_roles, validate=validate_roles,
                     subject_type="trial", effort="low", max_tokens=2000)


def roles(_args) -> None:
    """Role of each molecular entity in each in-scope trial. Industry-sponsored
    trials with several entities go to the LLM. Every other trial is decided
    per entity from arm types: comparator when the entity appears only in
    comparator arms, investigational otherwise."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT sd.nct_id, m.moiety_id, m.name, d.display_name, sd.intervention_type, sd.arm_types
            FROM preclin.ctgov_study_drug sd
            JOIN preclin.drug_moiety dm USING (drug_id)
            JOIN preclin.moiety m USING (moiety_id)
            JOIN preclin.drug d USING (drug_id)""")
        by_trial = defaultdict(list)
        for nct, mid, mname, dname, itype, arms in cur.fetchall():
            by_trial[nct].append((mid, mname, dname, itype, arms))
        cur.execute("""SELECT nct_id, brief_title, phases, arm_groups, interventions,
                              lead_sponsor_class = 'INDUSTRY'
                       FROM preclin.ctgov_study WHERE nct_id = ANY(%s)""", (list(by_trial),))
        studies = {r[0]: r[1:] for r in cur.fetchall()}

    fixed, items, moiety_ids = [], {}, {}
    for nct, rows in by_trial.items():
        moieties = {}
        for mid, mname, dname, itype, arms in rows:
            moieties.setdefault(mid, (mname, set()))[1].update(arms)
        title, phases, arm_groups, interventions, industry = studies[nct]
        if len(moieties) == 1 or not industry:
            for mid, (_, arms) in moieties.items():
                role = "comparator" if arms and arms <= COMPARATOR_ARMS else "investigational"
                fixed.append((nct, mid, role, "arm_types", None))
            continue
        names = {}
        for mid, mname, dname, itype, arms in rows:
            names.setdefault(norm(dname), set()).add(mname)
        ivs = [{"name": iv.get("name"), "type": iv.get("type"),
                "description": iv.get("description") or "",
                "moieties": sorted(names.get(norm(iv.get("name")), []))}
               for iv in interventions if names.get(norm(iv.get("name")))]
        items[nct] = {"nct_id": nct, "title": title, "phases": phases, "arms": arm_groups,
                      "interventions": ivs, "moieties": sorted({m[0] for m in moieties.values()})}
        moiety_ids[nct] = {m[0]: mid for mid, m in moieties.items()}

    run_id = llm.run(ROLE_TASK, items)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT subject_key, llm_decision_id, parsed_output FROM pv_evidence.llm_decision
                       WHERE decision_run_id = %s AND validation_status = 'validated'""", (str(run_id),))
        decided = [(nct, moiety_ids[nct][r["moiety"]], r["role"], "llm", did)
                   for nct, did, out in cur.fetchall() for r in out["roles"]]
        cur.execute("DELETE FROM preclin.ctgov_study_moiety")
        execute_values(cur, """INSERT INTO preclin.ctgov_study_moiety (nct_id, moiety_id, role, method, llm_decision_id)
                               VALUES %s""", fixed + decided, page_size=10000)
        conn.commit()
    print(f"trials={len(by_trial)} single-entity={len(fixed)} llm={len(items)} llm-decided={len(decided)}")


ACTIVE_STATUSES = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"}
PHASE_NUM = {"EARLY_PHASE1": 1, "PHASE1": 1, "PHASE2": 2, "PHASE3": 3}


def build(_args) -> None:
    """(molecular entity, MONDO disease) programs from investigational trials.

    A trial's phase is the highest phase it lists (Phase 1/2 counts as 2).
    Withdrawn trials never enrolled and are left out. A trial whose condition
    is an ancestor of another of the entity's diseases (e.g. "solid tumors"
    and "non-small cell lung carcinoma") attaches to the more specific
    programs instead of forming its own; a trial without a disease
    (healthy volunteers) attaches to every program of the entity, or forms the
    entity's disease-unspecified program when it has none."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT max(source_version) FROM preclin.evidence_source_release "
                    "WHERE source_name = 'clinicaltrials_gov_api_v2'")
        snapshot = cur.fetchone()[0]
        cur.execute("""SELECT nct_id, phases, start_date, primary_completion_date, completion_date,
                              overall_status, lead_sponsor, lead_sponsor_class
                       FROM preclin.ctgov_study WHERE phases && %s::text[]
                         AND overall_status <> 'WITHDRAWN' AND start_date IS NOT NULL""", (IN_SCOPE_PHASES,))
        trials = {}
        for nct, phases, start, pcd, comp, status, sponsor, sponsor_class in cur.fetchall():
            trials[nct] = {"phase": max(PHASE_NUM[p] for p in phases if p in PHASE_NUM), "start": start,
                           "active": status in ACTIVE_STATUSES, "end": comp or pcd or start,
                           "industry": sponsor_class == "INDUSTRY", "sponsor": sponsor}
        cur.execute("""SELECT nct_id, moiety_id FROM preclin.ctgov_study_moiety WHERE role = 'investigational'""")
        trial_moieties = defaultdict(set)
        for nct, mid in cur.fetchall():
            if nct in trials:
                trial_moieties[nct].add(mid)
        cur.execute("""SELECT si.nct_id, i.mondo_id FROM preclin.ctgov_study_indication si
                       JOIN preclin.indication i USING (indication_id)
                       WHERE i.indication_kind = 'disease' AND i.mondo_id IS NOT NULL""")
        trial_diseases = defaultdict(set)
        for nct, mondo in cur.fetchall():
            trial_diseases[nct].add(mondo)
        cur.execute("SELECT term_id, ancestor_id FROM preclin.ontology_ancestor WHERE ontology = 'MONDO'")
        ancestors = defaultdict(set)
        for term, anc in cur.fetchall():
            ancestors[term].add(anc)

    snap = date.fromisoformat(snapshot)
    by_moiety = defaultdict(list)
    for nct, mids in trial_moieties.items():
        for mid in mids:
            by_moiety[mid].append(nct)

    programs = {}   # (moiety, mondo) -> {nct: attach}
    for mid, ncts in by_moiety.items():
        direct = defaultdict(set)
        no_disease = []
        for nct in ncts:
            if trial_diseases[nct]:
                for d in trial_diseases[nct]:
                    direct[d].add(nct)
            else:
                no_disease.append(nct)
        specific = {d for d in direct if not any(d in ancestors[o] for o in direct if o != d)}
        for d in specific:
            programs[(mid, d)] = {nct: "disease" for nct in direct[d]}
        for d in set(direct) - specific:
            for o in specific:
                if d in ancestors[o]:
                    for nct in direct[d]:
                        programs[(mid, o)].setdefault(nct, "broader_condition")
        targets = [k for k in programs if k[0] == mid] or [(mid, None)]
        for key in targets:
            attached = programs.setdefault(key, {})
            for nct in no_disease:
                attached.setdefault(nct, "no_disease")

    rows, links = [], []
    for (mid, mondo), attached in programs.items():
        ts = [trials[n] for n in attached]
        starts = {p: min((t["start"] for t in ts if t["phase"] == p), default=None) for p in (1, 2, 3)}
        industry = [t for t in ts if t["industry"]]
        sponsors = Counter(t["sponsor"] for t in industry)
        rows.append((mid, mondo, starts[1], starts[2], starts[3], min(t["start"] for t in ts),
                     max(t["phase"] for t in ts), len(ts), len(industry),
                     min((t["start"] for t in industry), default=None),
                     [s for s, _ in sponsors.most_common(5)],
                     min(snap, max(snap if t["active"] else t["end"] for t in ts)),
                     sum(t["active"] for t in ts)))
        links.append([(n, trials[n]["phase"], a) for n, a in attached.items()])

    build_id = uuid.uuid4()
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO preclin.dev_program_build (build_id, code_commit, snapshot, parameters)
                       VALUES (%s, %s, %s, %s)""",
                    (str(build_id), llm.git_commit(), snap,
                     Json({"phases": IN_SCOPE_PHASES, "active_statuses": sorted(ACTIVE_STATUSES),
                           "combined_phase": "higher", "withdrawn": "excluded"})))
        cur.execute("DELETE FROM preclin.dev_program")
        ids = execute_values(cur, """INSERT INTO preclin.dev_program
              (moiety_id, mondo_id, ph1_start, ph2_start, ph3_start, first_start, highest_phase, n_trials,
               n_industry_trials, first_industry_start, lead_sponsors, last_activity, n_active_trials, build_id)
            VALUES %s RETURNING program_id""",
            [r + (str(build_id),) for r in rows], page_size=5000, fetch=True)
        execute_values(cur, "INSERT INTO preclin.dev_program_trial (program_id, nct_id, phase, attach) VALUES %s",
                       [(pid, *l) for (pid,), ls in zip(ids, links) for l in ls], page_size=10000)
        cur.execute("UPDATE preclin.dev_program_build SET parameters = parameters || %s WHERE build_id = %s",
                    (Json({"n_programs": len(rows), "n_links": sum(map(len, links))}), str(build_id)))
        conn.commit()
    print(f"build={build_id} programs={len(rows)} trial links={sum(map(len, links))} "
          f"entities={len(by_moiety)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("register").set_defaults(fn=register)
    sub.add_parser("roles").set_defaults(fn=roles)
    sub.add_parser("build").set_defaults(fn=build)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
