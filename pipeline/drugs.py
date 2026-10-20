"""Canonicalize every preclin.drug name to the molecular entities it contains.

    python -m pipeline.drugs canonicalize   # intervention names -> molecular entities
    python -m pipeline.drugs modality       # modality class of every entity with a development program

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
        cur.execute("SELECT drug_id, display_name, coalesce(synonyms, '{}'), chembl_id FROM preclin.drug")
        drugs = cur.fetchall()
        # Context: up to three trials per name, from the legacy program tables
        # when the name has programs there, otherwise from the CT.gov snapshot.
        cur.execute("""
            WITH t AS (
              SELECT p.drug_id, pt.nct_id,
                     row_number() OVER (PARTITION BY p.drug_id ORDER BY pt.nct_id) AS rn
              FROM preclin.program p JOIN preclin.program_trial pt USING (program_id)
              GROUP BY p.drug_id, pt.nct_id)
            SELECT t.drug_id, json_agg(json_build_object('title', tr.brief_title, 'sponsor', tr.sponsor_name,
                                                         'interventions', tr.interventions))
            FROM t JOIN public.trials tr ON tr.nct_id = t.nct_id
            WHERE t.rn <= 3 GROUP BY t.drug_id""")
        context = dict(cur.fetchall())
        cur.execute("""
            WITH s AS (
              SELECT drug_id, nct_id, row_number() OVER (PARTITION BY drug_id ORDER BY nct_id) AS rn
              FROM preclin.ctgov_study_drug)
            SELECT s.drug_id, json_agg(json_build_object('title', c.brief_title, 'sponsor', c.lead_sponsor,
                                                         'interventions', c.interventions))
            FROM s JOIN preclin.ctgov_study c USING (nct_id)
            WHERE s.rn <= 3 GROUP BY s.drug_id""")
        for drug_id, trials in cur.fetchall():
            context.setdefault(drug_id, trials)
        items = {str(did): {"name": name, "synonyms": list(syn)[:6], "chembl_id": chembl,
                            "trials": [{**t, "interventions": t["interventions"] or []}
                                       for t in context.get(did, [])]}
                 for did, name, syn, chembl in drugs}
    run_id = llm.run(TASK, items, reuse_by="subject")

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


MODALITIES = ["small_molecule", "peptide", "protein", "monoclonal_antibody", "multispecific_antibody",
              "antibody_drug_conjugate", "radioligand", "sirna_rnai", "antisense_oligonucleotide",
              "other_oligonucleotide", "mrna", "gene_therapy", "car_t", "other_cell_therapy", "vaccine",
              "microbiome_or_live_biotherapeutic", "other"]

MODALITY_SYSTEM = """You classify a drug (molecular entity) into one modality, following the classes used by BIO's 2021 Clinical Development Success Rates report plus a few finer classes.

- small_molecule: synthetic or natural-product small molecules, including prodrugs and small-molecule radiosensitizers.
- peptide: peptides and peptide analogues up to about 40 amino acids, including GLP-1 analogues, cyclic peptides, peptide hormones and peptide-drug conjugates.
- protein: recombinant or purified proteins that are not antibodies: enzymes, hormones such as insulin, cytokines, fusion proteins (e.g. Fc-fusion), coagulation factors, plasma proteins, toxins.
- monoclonal_antibody: monospecific antibodies and antibody fragments (including nanobodies), unconjugated.
- multispecific_antibody: bispecific or multispecific antibodies and T-cell engagers.
- antibody_drug_conjugate: antibodies conjugated to a cytotoxic or other payload (not radionuclides).
- radioligand: small molecules, peptides or antibodies carrying a therapeutic radionuclide.
- sirna_rnai: siRNA and other RNA-interference agents.
- antisense_oligonucleotide: antisense oligonucleotides, including splice-switching ASOs and gapmers.
- other_oligonucleotide: aptamers, CpG and other oligonucleotides that are neither siRNA nor antisense.
- mrna: mRNA therapeutics other than vaccines.
- gene_therapy: viral or non-viral gene transfer and in vivo gene editing.
- car_t: chimeric antigen receptor T cells (autologous or allogeneic).
- other_cell_therapy: other cell therapies (TCR-T, TILs, NK, stem cells, ex vivo gene-modified HSCs).
- vaccine: prophylactic or therapeutic vaccines (any platform, including mRNA vaccines).
- microbiome_or_live_biotherapeutic: live bacteria, fecal microbiota, phages.
- other: anything else (e.g. herbal extracts, plasma, mixtures, devices with drug).
Use the name, code names and trial context. If you do not recognise a code-named entity, infer from the trial descriptions; say so with confidence low."""

MODALITY_SCHEMA = {
    "type": "object",
    "properties": {"modality": {"type": "string", "enum": MODALITIES},
                   "confidence": {"type": "string", "enum": ["high", "medium", "low"]}},
    "required": ["modality", "confidence"],
    "additionalProperties": False,
}


def render_modality(p: dict) -> str:
    return (f"Entity: {p['name']}\nCode names: {', '.join(p['codes']) or 'none'}\n"
            f"Intervention strings naming it: {'; '.join(p['strings'])}\n"
            f"FDA application types: {', '.join(p['fda']) or 'none'}\n"
            f"Trial titles: {' | '.join(p['titles'])}")


MODALITY_TASK = llm.Task(name="moiety_modality", prompt_version="v1", schema_version="v1",
                         system=MODALITY_SYSTEM, schema=MODALITY_SCHEMA, render=render_modality,
                         subject_type="moiety", model="claude-opus-5-5", effort="low", max_tokens=1000)


def modality(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT m.moiety_id, m.name, m.code_names,
                   (SELECT array_agg(DISTINCT d.display_name) FROM preclin.drug_moiety dm
                    JOIN preclin.drug d USING (drug_id) WHERE dm.moiety_id = m.moiety_id),
                   (SELECT array_agg(DISTINCT a.appl_type) FROM preclin.fda_application_moiety am
                    JOIN preclin.fda_application a USING (appl_no) WHERE am.moiety_id = m.moiety_id),
                   (SELECT array_agg(t.brief_title) FROM (
                      SELECT DISTINCT c.brief_title FROM preclin.ctgov_study_moiety sm
                      JOIN preclin.ctgov_study c USING (nct_id)
                      WHERE sm.moiety_id = m.moiety_id AND sm.role = 'investigational' LIMIT 3) t)
            FROM preclin.moiety m
            WHERE EXISTS (SELECT 1 FROM preclin.dev_program p WHERE p.moiety_id = m.moiety_id)""")
        items = {str(mid): {"name": name, "codes": codes or [], "strings": sorted(strings or [])[:8],
                            "fda": fda or [], "titles": titles or []}
                 for mid, name, codes, strings, fda, titles in cur.fetchall()}
    run_id = llm.run(MODALITY_TASK, items)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""UPDATE preclin.moiety m SET modality = d.parsed_output->>'modality',
                         modality_decision_id = d.llm_decision_id
                       FROM pv_evidence.llm_decision d
                       WHERE d.decision_run_id = %s AND d.validation_status = 'validated'
                         AND d.subject_key = m.moiety_id::text""", (str(run_id),))
        conn.commit()
    print(f"entities={len(items)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("canonicalize").set_defaults(fn=canonicalize)
    sub.add_parser("modality").set_defaults(fn=modality)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
