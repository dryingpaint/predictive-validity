"""FDA approval of each development program's disease.

    python -m pipeline.approvals judge   # LLM: was this entity FDA-approved for this disease, and when?

For every molecular entity with FDA applications, the LLM sees the entity's
dated approval events (uses extracted from the 2008-2026 approval letters, or
from the label or review of an efficacy supplement with no letter, less
efficacy_labeling changes that add data without approving a new use; the dates
of the other efficacy supplements; original-approval dates) and its current
label indications, and rules on each of the entity's program diseases
(preclin.dev_program), seen with their MONDO definition and ancestors and the
titles and inclusion criteria of the program's trials. Results go to
preclin.dev_program_approval.
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from datetime import date

from psycopg2.extras import execute_values

from pipeline import llm
from pipeline.fda import LETTERS_FROM

DISEASES_PER_CALL = 30
LABELS_PER_ENTITY = 12
LABEL_CHARS = 3000
CONDITIONS_PER_DISEASE = 10  # trial condition strings shown per disease
TRIALS_PER_DISEASE = 5  # the program's trials of the disease shown, most advanced phase then latest start first
INCLUSION_CHARS = 900  # inclusion criteria shown per trial (a biomarker group decides tissue-agnostic uses)
ANCESTORS_SHOWN = 30  # MONDO ancestors shown per disease, nearest first
DEFINITION_CHARS = 400
YEAR = LETTERS_FROM[:4]
BEFORE = f"before_{YEAR}"  # the answer for a use approved before the first letter read; stored as date_basis 'before_letters'

SYSTEM = f"""You decide whether a drug (molecular entity) has been approved by the U.S. FDA for each of a list of diseases, and when.

You are given the entity's FDA approval events: the uses approved by each approval letter dated from {YEAR} onward (with the action date), or, for an efficacy supplement that has no letter, the use read from the label or review the FDA posted for it. Then the other efficacy supplements approved from {YEAR} onward, from which no new use was read; the original approval date of each application; the Indications and Usage text of the current labels, oldest application first; and the approved-use diseases found in the MONDO ontology with their ancestor classes. Each disease to judge comes with its MONDO definition and ancestor classes (nearest first), the condition strings of the program's trials of it, and those trials, whose titles and inclusion criteria are listed once under Program trials.

A use counts for a disease when the FDA approved the entity to treat, prevent or diagnose that disease, alone or in combination, in any population, line of therapy or biomarker subgroup of it, or under a broader approved class that includes it (an approval for "acute leukemia" covers acute myeloid leukemia; "rheumatoid arthritis and osteoarthritis" covers knee osteoarthritis).

For each disease in the list:
- approved: yes if an approved use is for this disease, a subtype of it, a population within it (e.g. an approval for "EGFR-mutant metastatic NSCLC" or for "squamous NSCLC" counts for "non-small cell lung carcinoma"), or a broader approved class that includes it. no if no approved use covers the disease. uncertain only when the evidence genuinely does not let you decide; a broad class wording that plainly includes the disease is yes, not uncertain.
  - Place the disease by its definition and ancestors, not its name alone. A disease that is a class whose members include the approved disease (by the class's definition or the approved disease's ancestors) is yes, subtype_or_subpopulation. Ancestor lists are incomplete: an approved disease that meets a class's definition belongs to it even when the class is missing from its ancestors. An approval for a histologic or cell type that names no site (e.g. "CD20-positive B-cell non-Hodgkin lymphoma") covers a disease named by its organ or site whose cases include that type (e.g. a lymphoma of one organ): those patients are a population within it.
  - A tissue-agnostic biomarker approval (e.g. MSI-H, dMMR or NTRK-fusion solid tumors) counts for a specific cancer only if the program's trials of that cancer enrolled that biomarker group. Decide this from the listed trials' titles and inclusion criteria, not from recollection: a trial that requires the biomarker, or a basket trial with a cohort for it that admits this cancer, enrolled it; trials that select another biomarker, or do not select for one, did not. If no listed trial selects for the biomarker, answer no.
  - A supportive use in patients who have the disease, which does not itself treat, prevent or diagnose the disease (e.g. mobilizing stem cells for transplant, preventing chemotherapy-induced neutropenia or nausea), counts for that disease only when the program's trials test that same supportive use; otherwise it is no for that disease.
- first_approval: the action date (YYYY-MM-DD) of the earliest approval that covers the disease, chosen from the dates listed (events, other efficacy supplements, original approvals), or "{BEFORE}". A later approval that widens a use the disease was already covered by (a new population, setting or regimen) does not move the date: the earlier approval stands. When you know with confidence that the FDA approved the use by an efficacy supplement listed without a use, answer with that supplement's date and say so in evidence. A later application of the same entity (a new formulation, a 505(b)(2) product, a new manufacturer's application) whose original approval repeats a use that an older application already had is not the first approval of that use. Answer "{BEFORE}" when an application approved before {YEAR} carries the use on its label and no letter from {YEAR} onward added the use to that application, or when you know with confidence that the FDA approved the entity for the use before {YEAR} (older, discontinued or generic labelling not given here); say so in evidence when the answer rests on your knowledge rather than the text given. Use "undated" only when the use is approved but its date cannot be placed, and "none" when approved is no.
- relation: same_disease, subtype_or_subpopulation (the approved use is narrower than the program disease), broader (the approved use covers a broader disease that includes the program disease), or none.
- evidence: a short verbatim quote from the event, label or trial that supports the answer.
Judge the disease by its meaning, not by matching words: "plaque psoriasis" is psoriasis; "chronic hepatitis C virus infection" is hepatitis C; "type 2 diabetes mellitus" is not type 1 diabetes."""

SCHEMA = {
    "type": "object",
    "properties": {"decisions": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "mondo_id": {"type": "string"},
            "approved": {"type": "string", "enum": ["yes", "no", "uncertain"]},
            "first_approval": {"type": "string"},
            "relation": {"type": "string", "enum": ["same_disease", "subtype_or_subpopulation", "broader", "none"]},
            "evidence": {"type": "string"},
        },
        "required": ["mondo_id", "approved", "first_approval", "relation", "evidence"],
        "additionalProperties": False}}},
    "required": ["decisions"],
    "additionalProperties": False,
}


def inclusion(criteria: str | None) -> str:
    """The inclusion part of a registered eligibility text (what precedes its exclusion
    criteria heading), whitespace collapsed and cut at INCLUSION_CHARS."""
    text = " ".join(re.split(r"exclusion criteria", criteria or "", maxsplit=1, flags=re.IGNORECASE)[0].split())
    return text if len(text) <= INCLUSION_CHARS else text[:INCLUSION_CHARS] + " ..."


def unstated_supplements(p: dict) -> list[dict]:
    """The payload's efficacy supplements with no event of the same application and date."""
    seen = {(e["date"], e["appl"]) for e in p["events"]}
    return [s for s in p["supplements"] if (s["date"], s["appl"]) not in seen]


def allowed_dates(p: dict) -> set[str]:
    """The first_approval answers a payload admits: every event, efficacy-supplement and
    original-approval date, and the non-date bases."""
    return ({e["date"] for e in p["events"]} | {s["date"] for s in p["supplements"]}
            | {d for _, d in p["originals"]} | {BEFORE, "undated", "none"})


def render(p: dict) -> str:
    events = "\n".join(f"- {e['date']} {e['appl']} {e['kind']}: {e['use']} [disease: {e['disease']}]"
                       + (f" [qualifiers: {'; '.join(e['qualifiers'])}]" if e["qualifiers"] else "")
                       + (f" [product also contains: {', '.join(e['partners'])}]" if e["partners"] else "")
                       + (f" [read from the supplement's {e['source']}; it has no letter]"
                          if e["source"] != "letter" else "")
                       for e in p["events"])
    supplements = "\n".join(f"- {s['date']} {s['appl']} {s['submission']}" for s in unstated_supplements(p))
    origs = "\n".join(f"- {a}: original approval {d}" for a, d in p["originals"])
    labels = "\n\n".join(f"[{l['appl']}, original approval {l['orig']}] {l['text']}" for l in p["labels"])
    terms = "\n".join(f"- {t['disease']} ({t['mondo_id']}) ancestors: {'; '.join(t['ancestors'])}"
                      for t in p["use_terms"])
    trials = "\n".join(f"- {nct}: {t['title']} | inclusion: {t['inclusion'] or '(not registered)'}"
                       for nct, t in p["trials"].items())
    diseases = "\n".join(f"- {d['mondo_id']} | {d['label']} | definition: {d['definition'] or '(none)'} | "
                         f"ancestors: {'; '.join(d['ancestors'])} | trial conditions: {'; '.join(d['conditions'])} | "
                         f"trials: {', '.join(d['trials']) or '(none)'}" for d in p["diseases"])
    return (f"Entity: {p['entity']}\n\nApproval events ({YEAR} onward):\n{events or '(none)'}\n\n"
            f"Other efficacy supplements approved ({YEAR} onward; no new use read from them):\n"
            f"{supplements or '(none)'}\n\n"
            f"Applications:\n{origs}\n\nCurrent label indications:\n{labels or '(no current label)'}\n\n"
            f"Approved-use diseases in MONDO:\n{terms or '(none found)'}\n\n"
            f"Program trials:\n{trials or '(none)'}\n\nDiseases to judge:\n{diseases}")


def unrecorded_original_before(p: dict) -> str | None:
    """The latest date an unrecorded original approval can carry: the first listed action of an application whose
    original approval the payload does not give (a CBER biologic first approved before its actions were read)."""
    first = {}
    for x in (*p["events"], *p["supplements"]):
        first[x["appl"]] = min(first.get(x["appl"], x["date"]), x["date"])
    recorded = {a for a, _ in p["originals"]}
    return max((d for a, d in first.items() if a not in recorded), default=None)


def validate(p: dict, out: dict) -> None:
    want = sorted(d["mondo_id"] for d in p["diseases"])
    got = sorted(d["mondo_id"] for d in out["decisions"])
    if got != want:
        raise ValueError(f"decisions cover {got[:5]}..., expected {want[:5]}...")
    allowed = allowed_dates(p)
    unrecorded = unrecorded_original_before(p)
    for d in out["decisions"]:
        fa = d["first_approval"]
        known_original = unrecorded and re.fullmatch(r"\d{4}-\d{2}-\d{2}", fa) and fa < unrecorded
        if fa not in allowed and not known_original:  # known_original: before an unrecorded original's first action
            raise ValueError(f"{d['mondo_id']}: first_approval {fa} not an event date or basis")
        if (d["approved"] == "no") != (fa == "none") and d["approved"] != "uncertain":
            raise ValueError(f"{d['mondo_id']}: first_approval {fa} with approved={d['approved']}")


TASK = llm.Task(name="program_fda_approval", prompt_version="v4", schema_version="v1", system=SYSTEM,
                schema=SCHEMA, render=render, validate=validate, subject_type="moiety_disease_chunk",
                model="claude-opus-5-5", effort="medium", max_tokens=12000)


def payloads(entities: dict, events: dict, supplements: dict, labels: dict, use_terms: dict,
             diseases: dict, trials: dict) -> dict[str, dict]:
    """One payload per chunk of DISEASES_PER_CALL of an entity's program diseases, keyed
    'moiety_id:chunk'. Each chunk lists once the trials its diseases name."""
    work = {}
    for mid, ent in entities.items():
        ds = sorted(diseases.get(mid, []), key=lambda d: d["mondo_id"])
        ent_labels = sorted(labels.get(mid, {}).values(), key=lambda l: l["orig"])[:LABELS_PER_ENTITY]
        for start in range(0, len(ds), DISEASES_PER_CALL):
            chunk = ds[start:start + DISEASES_PER_CALL]
            work[f"{mid}:{start // DISEASES_PER_CALL}"] = {
                "entity": ent["name"], "events": list(events.get(mid, {}).values()),
                "supplements": sorted(supplements.get(mid, []), key=lambda s: (s["date"], s["appl"], s["submission"])),
                "originals": sorted({(a, o.isoformat()) for a, o in ent["apps"].items() if o}),
                "labels": ent_labels, "use_terms": use_terms.get(mid, []),
                "trials": {nct: trials[nct] for nct in sorted({n for d in chunk for n in d["trials"]})},
                "diseases": chunk}
    return work


def load_work(cur) -> dict[str, dict]:
    cur.execute("""
        SELECT am.moiety_id, m.name, a.appl_type || ' ' || a.appl_no,
               (SELECT min(status_date) FROM preclin.fda_submission s
                WHERE s.appl_no = a.appl_no AND s.submission_type = 'ORIG' AND s.status = 'AP')
        FROM preclin.fda_application_moiety am
        JOIN preclin.moiety m USING (moiety_id)
        JOIN preclin.fda_application a USING (appl_no)
        WHERE EXISTS (SELECT 1 FROM preclin.dev_program p WHERE p.moiety_id = am.moiety_id
                      AND p.mondo_id IS NOT NULL)""")
    entities = defaultdict(lambda: {"name": None, "apps": {}})
    for mid, name, appl, orig in cur.fetchall():
        entities[mid]["name"] = name
        entities[mid]["apps"][appl] = orig
    cur.execute("""
        SELECT am.moiety_id, a.appl_type || ' ' || a.appl_no, s.status_date, u.change_type, u.indication_as_written,
               u.disease, u.qualifiers,
               (SELECT array_agg(m2.name ORDER BY m2.name) FROM preclin.fda_application_moiety am2
                JOIN preclin.moiety m2 USING (moiety_id)
                WHERE am2.appl_no = a.appl_no AND am2.moiety_id <> am.moiety_id),
               sl.doc_type
        FROM preclin.fda_application_moiety am
        JOIN preclin.fda_application a USING (appl_no)
        JOIN preclin.fda_submission_letter sl ON sl.appl_no = a.appl_no
        JOIN preclin.fda_submission s ON s.appl_no = sl.appl_no AND s.submission_type = sl.submission_type
                                     AND s.submission_no = sl.submission_no
        JOIN preclin.fda_approved_use u ON u.letter_sha256 = sl.letter_sha256
        WHERE u.change_type <> 'efficacy_labeling'
        ORDER BY s.status_date, a.appl_type, a.appl_no, s.submission_type, s.submission_no, u.letter_sha256,
                 u.ordinal""")
    events = defaultdict(dict)
    for mid, appl, d, kind, use, disease, quals, partners, source in cur.fetchall():
        events[mid][(d, use)] = {"date": d.isoformat(), "appl": appl, "kind": kind, "use": use, "disease": disease,
                                 "qualifiers": quals, "partners": partners or [], "source": source}
    cur.execute("""
        SELECT am.moiety_id, a.appl_type || ' ' || a.appl_no, s.submission_no, s.status_date
        FROM preclin.fda_application_moiety am
        JOIN preclin.fda_application a USING (appl_no)
        JOIN preclin.fda_submission s ON s.appl_no = a.appl_no
        WHERE s.submission_type = 'SUPPL' AND s.status = 'AP' AND s.submission_class = 'EFFICACY'
          AND s.status_date >= %s""", (LETTERS_FROM,))
    supplements = defaultdict(list)
    for mid, appl, no, d in cur.fetchall():
        supplements[mid].append({"date": d.isoformat(), "appl": appl, "submission": f"S-{no}"})
    cur.execute("""
        SELECT am.moiety_id, a.appl_type || ' ' || a.appl_no, l.indications_text
        FROM preclin.fda_application_moiety am JOIN preclin.fda_application a USING (appl_no)
        JOIN preclin.fda_label l ON (a.appl_type || a.appl_no) = ANY(l.application_numbers)
        WHERE l.indications_text IS NOT NULL
        ORDER BY am.moiety_id, a.appl_type, a.appl_no, l.set_id""")
    labels = defaultdict(dict)
    for mid, appl, text in cur.fetchall():
        if mid not in entities:
            continue
        orig = entities[mid]["apps"].get(appl)
        labels[mid].setdefault(text, {"appl": appl, "orig": str(orig) if orig else "unknown",
                                      "text": text[:LABEL_CHARS]})
    # Approved-use diseases whose name is a MONDO term's label or synonym (ignoring case); a name that
    # is several terms' synonym and no term's label is left out.
    cur.execute("""
        WITH names AS (
            SELECT lower(label) AS name, term_id, true AS is_label FROM preclin.ontology_term
            WHERE ontology = 'MONDO' AND NOT is_obsolete
            UNION
            SELECT lower(syn), term_id, false FROM preclin.ontology_term, unnest(synonyms) syn
            WHERE ontology = 'MONDO' AND NOT is_obsolete),
        uses AS (
            SELECT DISTINCT am.moiety_id, u.disease
            FROM preclin.fda_application_moiety am
            JOIN preclin.fda_submission_letter sl USING (appl_no)
            JOIN preclin.fda_approved_use u USING (letter_sha256))
        SELECT u.moiety_id, u.disease,
               coalesce(min(n.term_id) FILTER (WHERE n.is_label),
                        CASE WHEN count(DISTINCT n.term_id) = 1 THEN min(n.term_id) END)
        FROM uses u JOIN names n ON n.name = lower(u.disease)
        GROUP BY u.moiety_id, u.disease
        ORDER BY u.moiety_id, u.disease""")
    use_mondo = [(mid, disease, term) for mid, disease, term in cur.fetchall() if term]
    cur.execute("""
        SELECT a.term_id, array_agg(t.label ORDER BY a.distance, t.label)
        FROM preclin.ontology_ancestor a JOIN preclin.ontology_term t ON t.term_id = a.ancestor_id
        WHERE a.term_id = ANY(%s) OR a.term_id IN (SELECT mondo_id FROM preclin.dev_program)
        GROUP BY a.term_id""", (sorted({term for _, _, term in use_mondo}),))
    ancestors = {term: chain[:ANCESTORS_SHOWN] for term, chain in cur.fetchall()}
    use_terms = defaultdict(list)
    for mid, disease, term in use_mondo:
        use_terms[mid].append({"disease": disease, "mondo_id": term, "ancestors": ancestors.get(term, [])})
    # The program's trials of its disease: those with a condition mapped to it, with those conditions.
    cur.execute("""
        SELECT p.program_id, dt.nct_id, (SELECT max(ph) FROM unnest(s.phases) ph), s.start_date,
               array_agg(DISTINCT i.display_name)
        FROM preclin.dev_program p
        JOIN preclin.dev_program_trial dt USING (program_id)
        JOIN preclin.ctgov_study_indication si ON si.nct_id = dt.nct_id
        JOIN preclin.indication i USING (indication_id)
        LEFT JOIN preclin.program_indication pi ON pi.moiety_id = p.moiety_id AND pi.mondo_id = i.mondo_id
        JOIN preclin.ctgov_study s ON s.nct_id = dt.nct_id
        WHERE coalesce(pi.indication_mondo, i.mondo_id) = p.mondo_id
        GROUP BY p.program_id, dt.nct_id, s.phases, s.start_date""")
    program_trials, conditions = defaultdict(list), defaultdict(set)
    for pid, nct, phase, start, names in cur.fetchall():
        program_trials[pid].append((phase or "", start or date.min, nct))
        conditions[pid].update(names)
    program_trials = {pid: [nct for _, _, nct in sorted(ts, reverse=True)[:TRIALS_PER_DISEASE]]
                      for pid, ts in program_trials.items()}
    cur.execute("SELECT nct_id, brief_title, eligibility_criteria FROM preclin.ctgov_study WHERE nct_id = ANY(%s)",
                (sorted({nct for ts in program_trials.values() for nct in ts}),))
    trials = {nct: {"title": title, "inclusion": inclusion(criteria)} for nct, title, criteria in cur.fetchall()}
    cur.execute("""SELECT p.program_id, p.moiety_id, p.mondo_id, t.label, t.definition
                   FROM preclin.dev_program p JOIN preclin.ontology_term t ON t.term_id = p.mondo_id""")
    diseases = defaultdict(list)
    for pid, mid, mondo, label, definition in cur.fetchall():
        diseases[mid].append({"mondo_id": mondo, "label": label, "definition": (definition or "")[:DEFINITION_CHARS],
                              "ancestors": ancestors.get(mondo, []),
                              "conditions": sorted(conditions[pid])[:CONDITIONS_PER_DISEASE],
                              "trials": program_trials.get(pid, [])})
    return payloads(entities, events, supplements, labels, use_terms, diseases, trials)


def judge(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        work = load_work(cur)
    run_id = llm.run(TASK, work)
    decided = llm.decisions(run_id)
    rows = []
    for key, did, out in decided:
        mid = int(key.split(":")[0])
        for d in out["decisions"]:
            fa = d["first_approval"]
            dated = fa[:2] in ("19", "20")
            basis = "dated" if dated else "before_letters" if fa == BEFORE else fa
            rows.append((mid, d["mondo_id"], d["approved"], fa if dated else None, basis,
                         d["relation"], d["evidence"], did))
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.dev_program_approval")
        execute_values(cur, """INSERT INTO preclin.dev_program_approval
              (program_id, approved, first_approval_date, date_basis, relation, evidence, llm_decision_id)
            SELECT p.program_id, v.approved, v.d::date, v.basis, v.relation, v.evidence, v.did
            FROM (VALUES %s) AS v(mid, mondo, approved, d, basis, relation, evidence, did)
            JOIN preclin.dev_program p ON p.moiety_id = v.mid AND p.mondo_id = v.mondo""", rows, page_size=5000)
        conn.commit()
    unjudged = sorted(set(work) - {key for key, _, _ in decided})  # no validated decision: no approval row
    print(f"calls={len(work)} judgements={len(rows)} approved={sum(r[2] == 'yes' for r in rows)} "
          f"unjudged calls={len(unjudged)} programs={sum(len(work[k]['diseases']) for k in unjudged)}: "
          f"{[work[k]['entity'] for k in unjudged][:10]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("judge").set_defaults(fn=judge)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
