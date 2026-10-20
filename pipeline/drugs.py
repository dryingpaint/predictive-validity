"""Canonicalize every preclin.drug name to the molecular entities it contains.

    python -m pipeline.drugs canonicalize

Trial intervention strings name the same molecule many ways ("Keytruda",
"pembrolizumab 200 mg", "Pembrolizumab Dose A", "MK-3475"), bundle placebo
with drug ("Tirzepatide-Placebo") and describe combinations. The LLM reads each
name with the trials it appears in and returns its active components under
their nonproprietary (INN/USAN) names, or sponsor code when no name exists.
Results go to preclin.moiety (one row per distinct active entity) and
preclin.drug_moiety (drug_id -> moiety_id, one row per active component).
"""
from __future__ import annotations

import argparse
import re

from psycopg2.extras import execute_values

from pipeline import llm

SYSTEM = """You resolve clinical-trial intervention names to the molecular entities they contain.

For the intervention name given (with the trials it appears in for context), return:
- kind: drug (one active entity), combination (two or more active entities given together or co-formulated), placebo_or_vehicle (placebo, vehicle, sham, saline, standard-of-care-only label, diluent), vaccine, non_drug (device, procedure, radiation, behavioral, diet, diagnostic/imaging agent used only for diagnosis, supplement of no defined active entity), or unclear.
- components: every active entity, excluding placebo. For each give:
  name: the international nonproprietary name (INN) or USAN in lower case if one exists (e.g. "pembrolizumab", "semaglutide", "insulin glargine", "trastuzumab deruxtecan"); for an entity with no nonproprietary name, its sponsor code exactly as commonly written (e.g. "MK-1084"). Map brand names and sponsor codes to the nonproprietary name when you are confident they are the same entity (e.g. Keytruda and MK-3475 -> pembrolizumab). Strip doses, strengths, routes, formulations, salts and schedules (e.g. "metformin hydrochloride 500 mg XR" -> "metformin").
  code_names: sponsor codes for this entity mentioned in the input or that you are confident of.
  biosimilar_of: for a biosimilar or a proposed biosimilar, the reference product's nonproprietary name; otherwise null. Name a biosimilar by its core nonproprietary name without the four-letter suffix (e.g. "adalimumab").
  role: investigational if this entity is what the trial is developing in this arm; background if it is a partner/standard therapy given alongside.
- confidence: high, medium or low for the mapping as a whole.

Do not invent nonproprietary names: if you are not confident a code maps to an INN, keep the code."""

SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["drug", "combination", "placebo_or_vehicle", "vaccine",
                                             "non_drug", "unclear"]},
        "components": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "code_names": {"type": "array", "items": {"type": "string"}},
                "biosimilar_of": {"type": ["string", "null"]},
                "role": {"type": "string", "enum": ["investigational", "background"]},
            },
            "required": ["name", "code_names", "biosimilar_of", "role"],
            "additionalProperties": False}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["kind", "components", "confidence"],
    "additionalProperties": False,
}


def render(p: dict) -> str:
    trials = "\n".join(
        f"- {t['title']} (sponsor: {t['sponsor']}); interventions: "
        + "; ".join(f"{i.get('name')} [{i.get('type')}]: {(i.get('description') or '')[:160]}"
                    for i in t["interventions"][:8])
        for t in p["trials"])
    return (f"Intervention name: {p['name']}\nOther names recorded: {', '.join(p['synonyms']) or 'none'}\n"
            f"ChEMBL id recorded: {p['chembl_id'] or 'none'}\n\nTrials using it:\n{trials or '(none)'}")


TASK = llm.Task(name="drug_moiety", prompt_version="v1", schema_version="v1", system=SYSTEM,
                schema=SCHEMA, render=render, subject_type="drug", effort="medium", max_tokens=3000)


def moiety_key(name: str) -> str:
    """Identity key for a component name: case- and punctuation-insensitive."""
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def canonicalize(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            WITH t AS (
              SELECT p.drug_id, pt.nct_id,
                     row_number() OVER (PARTITION BY p.drug_id ORDER BY pt.nct_id) AS rn
              FROM preclin.program p JOIN preclin.program_trial pt USING (program_id)
              GROUP BY p.drug_id, pt.nct_id)
            SELECT d.drug_id, d.display_name, coalesce(d.synonyms, '{}'), d.chembl_id,
                   coalesce(json_agg(json_build_object('title', tr.brief_title, 'sponsor', tr.sponsor_name,
                                     'interventions', tr.interventions))
                            FILTER (WHERE tr.nct_id IS NOT NULL), '[]')
            FROM preclin.drug d
            LEFT JOIN t ON t.drug_id = d.drug_id AND t.rn <= 3
            LEFT JOIN public.trials tr ON tr.nct_id = t.nct_id
            GROUP BY d.drug_id""")
        items = {str(did): {"name": name, "synonyms": list(syn)[:6], "chembl_id": chembl,
                            "trials": [{**t, "interventions": t["interventions"] or []} for t in trials]}
                 for did, name, syn, chembl, trials in cur.fetchall()}
    run_id = llm.run(TASK, items)

    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT subject_key, llm_decision_id, parsed_output FROM pv_evidence.llm_decision
                       WHERE decision_run_id = %s AND validation_status = 'validated'""", (str(run_id),))
        decided = cur.fetchall()
        moieties: dict[str, dict] = {}
        links = []
        kinds = []
        for drug_id, decision_id, out in decided:
            kinds.append((int(drug_id), out["kind"], decision_id))
            if out["kind"] not in ("drug", "combination", "vaccine"):
                continue
            for comp in out["components"]:
                key = moiety_key(comp["name"])
                if not key:
                    continue
                m = moieties.setdefault(key, {"name": comp["name"], "codes": set()})
                m["codes"].update(comp["code_names"])
                links.append((int(drug_id), key, comp["role"], comp["biosimilar_of"], decision_id))
        execute_values(cur, """INSERT INTO preclin.moiety (moiety_key, name, code_names) VALUES %s
            ON CONFLICT (moiety_key) DO UPDATE SET code_names = EXCLUDED.code_names""",
            [(k, m["name"], sorted(m["codes"])) for k, m in moieties.items()])
        cur.execute("DELETE FROM preclin.drug_moiety")
        execute_values(cur, """INSERT INTO preclin.drug_moiety
              (drug_id, moiety_id, role, biosimilar_of, llm_decision_id)
            SELECT v.drug_id, m.moiety_id, v.role, v.biosimilar_of, v.did
            FROM (VALUES %s) AS v(drug_id, key, role, biosimilar_of, did)
            JOIN preclin.moiety m ON m.moiety_key = v.key
            ON CONFLICT (drug_id, moiety_id) DO NOTHING""", links)
        execute_values(cur, """UPDATE preclin.drug d SET entity_kind = v.kind, moiety_decision_id = v.did
            FROM (VALUES %s) AS v(drug_id, kind, did) WHERE d.drug_id = v.drug_id""", kinds)
        conn.commit()
    print(f"drugs={len(items)} decided={len(decided)} moieties={len(moieties)} links={len(links)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("canonicalize").set_defaults(fn=canonicalize)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
