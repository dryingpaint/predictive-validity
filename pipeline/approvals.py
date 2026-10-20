"""FDA approval of each development program's disease.

    python -m pipeline.approvals judge   # LLM: was this entity FDA-approved for this disease, and when?

For every molecular entity with FDA applications, the LLM sees the entity's
dated approval events (uses extracted from 2015-2026 approval letters, less
efficacy_labeling changes that add data without approving a new use;
original-approval dates) and its current label indications, and rules on each
of the entity's program diseases (preclin.dev_program). Results go to
preclin.dev_program_approval.
"""
from __future__ import annotations

import argparse
from collections import defaultdict

from psycopg2.extras import execute_values

from pipeline import llm

DISEASES_PER_CALL = 30
LABELS_PER_ENTITY = 12
LABEL_CHARS = 3000

SYSTEM = """You decide whether a drug (molecular entity) has been approved by the U.S. FDA for each of a list of diseases, and when.

You are given the entity's FDA approval events: the uses approved by each approval letter dated from 2015 onward (with the action date), the original approval date of each application, and the Indications and Usage text of the current labels, oldest application first. A use counts for a disease when the FDA approved the entity to treat, prevent or diagnose that disease, alone or in combination, in any population, line of therapy or biomarker subgroup of it, or under a broader approved class that includes it (an approval for "acute leukemia" covers acute myeloid leukemia; "rheumatoid arthritis and osteoarthritis" covers knee osteoarthritis).

For each disease in the list:
- approved: yes if an approved use is for this disease, a subtype of it, a population within it (e.g. an approval for "EGFR-mutant metastatic NSCLC" or for "squamous NSCLC" counts for "non-small cell lung carcinoma"), or a broader approved class that includes it. A tissue-agnostic biomarker approval (e.g. MSI-H or NTRK-fusion solid tumors) counts for a specific cancer only if the program's trials enrolled that biomarker group. no if no approved use covers the disease. uncertain only when the evidence genuinely does not let you decide; a broad class wording that plainly includes the disease is yes, not uncertain.
- first_approval: the action date (YYYY-MM-DD) of the earliest approval that covers the disease, chosen from the dates listed, or "before_2015". A later application of the same entity (a new formulation, a 505(b)(2) product, a new manufacturer's application) whose original approval repeats a use that an older application already had is not the first approval of that use. Answer "before_2015" when an application approved before 2015 carries the use on its label and no letter from 2015 onward added the use to that application, or when you know with confidence that the FDA approved the entity for the use before 2015 (older, discontinued or generic labelling not given here); say so in evidence when the answer rests on your knowledge rather than the text given. Use "undated" only when the use is approved but its date cannot be placed, and "none" when approved is no.
- relation: same_disease, subtype_or_subpopulation (the approved use is narrower than the program disease), broader (the approved use covers a broader disease that includes the program disease), or none.
- evidence: a short verbatim quote from the event or label that supports a yes.
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


def render(p: dict) -> str:
    events = "\n".join(f"- {e['date']} {e['appl']} {e['kind']}: {e['use']}"
                       + (f" [qualifiers: {'; '.join(e['qualifiers'])}]" if e["qualifiers"] else "")
                       + (f" [product also contains: {', '.join(e['partners'])}]" if e["partners"] else "")
                       for e in p["events"])
    origs = "\n".join(f"- {a}: original approval {d}" for a, d in p["originals"])
    labels = "\n\n".join(f"[{l['appl']}, original approval {l['orig']}] {l['text']}" for l in p["labels"])
    diseases = "\n".join(f"- {d['mondo_id']} | {d['label']} (is_a: {d['parents']}) | trial conditions: "
                         f"{'; '.join(d['conditions'])}" for d in p["diseases"])
    return (f"Entity: {p['entity']}\n\nApproval events from letters (2015 onward):\n{events or '(none)'}\n\n"
            f"Applications:\n{origs}\n\nCurrent label indications:\n{labels or '(no current label)'}\n\n"
            f"Diseases to judge:\n{diseases}")


def validate(p: dict, out: dict) -> None:
    want = sorted(d["mondo_id"] for d in p["diseases"])
    got = sorted(d["mondo_id"] for d in out["decisions"])
    if got != want:
        raise ValueError(f"decisions cover {got[:5]}..., expected {want[:5]}...")
    allowed = {e["date"] for e in p["events"]} | {d for _, d in p["originals"]} | {"before_2015", "undated", "none"}
    for d in out["decisions"]:
        if d["approved"] == "yes" and d["first_approval"] not in allowed:
            raise ValueError(f"{d['mondo_id']}: first_approval {d['first_approval']} not an event date")


TASK = llm.Task(name="program_fda_approval", prompt_version="v2", schema_version="v1", system=SYSTEM,
                schema=SCHEMA, render=render, validate=validate, subject_type="moiety_disease_chunk",
                model="claude-opus-5-5", effort="medium", max_tokens=12000)


def items(cur) -> dict[str, dict]:
    cur.execute("""
        SELECT am.moiety_id, m.name, a.appl_type || ' ' || a.appl_no,
               (SELECT min(status_date) FROM preclin.fda_submission s
                WHERE s.appl_no = a.appl_no AND s.submission_type = 'ORIG' AND s.status = 'AP')
        FROM preclin.fda_application_moiety am
        JOIN preclin.moiety m USING (moiety_id)
        JOIN preclin.fda_application a USING (appl_no)
        WHERE EXISTS (SELECT 1 FROM preclin.dev_program p WHERE p.moiety_id = am.moiety_id
                      AND p.mondo_id IS NOT NULL)""")
    entities = defaultdict(lambda: {"name": None, "apps": []})
    for mid, name, appl, orig in cur.fetchall():
        entities[mid]["name"] = name
        entities[mid]["apps"].append((appl, orig))
    cur.execute("""
        SELECT am.moiety_id, a.appl_type || ' ' || a.appl_no, s.status_date, u.change_type, u.indication_as_written,
               u.qualifiers,
               (SELECT array_agg(m2.name) FROM preclin.fda_application_moiety am2 JOIN preclin.moiety m2 USING (moiety_id)
                WHERE am2.appl_no = a.appl_no AND am2.moiety_id <> am.moiety_id)
        FROM preclin.fda_application_moiety am
        JOIN preclin.fda_application a USING (appl_no)
        JOIN preclin.fda_submission_letter sl ON sl.appl_no = a.appl_no
        JOIN preclin.fda_submission s ON s.appl_no = sl.appl_no AND s.submission_type = sl.submission_type
                                     AND s.submission_no = sl.submission_no
        JOIN preclin.fda_approved_use u ON u.letter_sha256 = sl.letter_sha256
        WHERE u.change_type <> 'efficacy_labeling'
        ORDER BY s.status_date""")
    events = defaultdict(dict)
    for mid, appl, d, kind, use, quals, partners in cur.fetchall():
        events[mid][(d, use)] = {"date": d.isoformat(), "appl": appl, "kind": kind, "use": use,
                                 "qualifiers": quals, "partners": partners or []}
    cur.execute("""
        SELECT am.moiety_id, a.appl_type || ' ' || a.appl_no, l.indications_text, l.effective_date
        FROM preclin.fda_application_moiety am JOIN preclin.fda_application a USING (appl_no)
        JOIN preclin.fda_label l ON (a.appl_type || a.appl_no) = ANY(l.application_numbers)
        WHERE l.indications_text IS NOT NULL""")
    labels = defaultdict(dict)
    for mid, appl, text, eff in cur.fetchall():
        orig = dict(entities[mid]["apps"]).get(appl) if mid in entities else None
        labels[mid].setdefault(text, {"appl": appl, "orig": str(orig) if orig else "unknown",
                                      "text": text[:LABEL_CHARS]})
    cur.execute("""
        SELECT p.moiety_id, p.mondo_id, t.label,
               (SELECT string_agg(pt.label, '; ') FROM preclin.ontology_is_a e
                JOIN preclin.ontology_term pt ON pt.term_id = e.parent_id WHERE e.child_id = p.mondo_id),
               (SELECT array_agg(DISTINCT i.display_name) FROM preclin.dev_program_trial dt
                JOIN preclin.ctgov_study_indication si USING (nct_id)
                JOIN preclin.indication i USING (indication_id)
                WHERE dt.program_id = p.program_id AND i.mondo_id = p.mondo_id)
        FROM preclin.dev_program p JOIN preclin.ontology_term t ON t.term_id = p.mondo_id""")
    diseases = defaultdict(list)
    for mid, mondo, label, parents, conds in cur.fetchall():
        diseases[mid].append({"mondo_id": mondo, "label": label, "parents": parents or "",
                              "conditions": sorted(conds or [])[:5]})

    out = {}
    for mid, ent in entities.items():
        ds = sorted(diseases.get(mid, []), key=lambda d: d["mondo_id"])
        ent_labels = sorted(labels[mid].values(), key=lambda l: l["orig"])[:LABELS_PER_ENTITY]
        for start in range(0, len(ds), DISEASES_PER_CALL):
            out[f"{mid}:{start // DISEASES_PER_CALL}"] = {
                "entity": ent["name"], "events": list(events[mid].values()),
                "originals": sorted({(a, o.isoformat()) for a, o in ent["apps"] if o}),
                "labels": ent_labels, "diseases": ds[start:start + DISEASES_PER_CALL]}
    return out


def judge(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        work = items(cur)
    run_id = llm.run(TASK, work)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT subject_key, llm_decision_id, parsed_output FROM pv_evidence.llm_decision
                       WHERE decision_run_id = %s AND validation_status = 'validated'""", (str(run_id),))
        rows = []
        for key, did, out in cur.fetchall():
            mid = int(key.split(":")[0])
            for d in out["decisions"]:
                fa = d["first_approval"]
                rows.append((mid, d["mondo_id"], d["approved"],
                             fa if fa[:2] in ("19", "20") else None,
                             fa if fa[:2] not in ("19", "20") else "dated",
                             d["relation"], d["evidence"], did))
        cur.execute("DELETE FROM preclin.dev_program_approval")
        execute_values(cur, """INSERT INTO preclin.dev_program_approval
              (program_id, approved, first_approval_date, date_basis, relation, evidence, llm_decision_id)
            SELECT p.program_id, v.approved, v.d::date, v.basis, v.relation, v.evidence, v.did
            FROM (VALUES %s) AS v(mid, mondo, approved, d, basis, relation, evidence, did)
            JOIN preclin.dev_program p ON p.moiety_id = v.mid AND p.mondo_id = v.mondo""", rows, page_size=5000)
        conn.commit()
    print(f"calls={len(work)} judgements={len(rows)} approved={sum(r[2] == 'yes' for r in rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("judge").set_defaults(fn=judge)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
