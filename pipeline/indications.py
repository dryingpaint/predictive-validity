"""Map every condition string (preclin.indication) to the MONDO term for its core disease.

    python -m pipeline.indications map     # LLM choice among MONDO candidates -> indication.mondo_id
    python -m pipeline.indications areas   # BIO 2021 disease area of every program disease

Condition strings enter preclin.indication through pipeline.programs register.

Candidates come from the pinned MONDO release in preclin.ontology_term:
character n-gram and word TF-IDF retrieval (hits interleaved) over labels and
exact synonyms. The LLM picks the term naming the disease itself, leaving
population qualifiers (line, stage, biomarker, age) aside, or reports that none
fits and proposes standard disease names; a second retrieval round runs on
those names. A disease still
without a term gets the most specific MONDO term that contains it (its nearest
parent disease or grouping), chosen from the retrieved terms and their parents;
indication.mondo_match records which kind of match each mapping is.
"""
from __future__ import annotations

import argparse

from psycopg2.extras import execute_values
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

from pipeline import llm

N_CANDIDATES = 20


class MondoIndex:
    """Nearest-neighbour search over MONDO labels and exact synonyms."""

    def __init__(self, cur):
        cur.execute("""SELECT t.term_id, t.label, t.synonyms, t.definition,
                              (SELECT string_agg(p.label, '; ') FROM preclin.ontology_is_a e
                               JOIN preclin.ontology_term p ON p.term_id = e.parent_id
                               WHERE e.child_id = t.term_id),
                              (SELECT array_agg(e.parent_id) FROM preclin.ontology_is_a e WHERE e.child_id = t.term_id)
                       FROM preclin.ontology_term t
                       WHERE t.ontology = 'MONDO' AND NOT t.is_obsolete""")
        self.terms, self.parents = {}, {}
        strings, owners = [], []
        for tid, label, syns, definition, parents, parent_ids in cur.fetchall():
            self.terms[tid] = {"mondo_id": tid, "label": label, "synonyms": list(syns)[:6],
                               "parents": parents or "", "definition": (definition or "")[:240]}
            self.parents[tid] = parent_ids or []
            for s in [label, *syns]:
                strings.append(s.lower())
                owners.append(tid)
        self.owners = owners
        self.char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 4), sublinear_tf=True)
        self.word = TfidfVectorizer(analyzer="word", token_pattern=r"[a-z0-9]+", sublinear_tf=True)
        self.nn_char = NearestNeighbors(n_neighbors=60, metric="cosine").fit(self.char.fit_transform(strings))
        self.nn_word = NearestNeighbors(n_neighbors=60, metric="cosine").fit(self.word.fit_transform(strings))

    def search(self, queries: list[str]) -> list[list[dict]]:
        """Up to N_CANDIDATES distinct MONDO terms per query, interleaving char and word hits."""
        q = [x.lower() for x in queries]
        _, ic = self.nn_char.kneighbors(self.char.transform(q))
        _, iw = self.nn_word.kneighbors(self.word.transform(q))
        out = []
        for row_c, row_w in zip(ic, iw):
            seen = dict.fromkeys(self.owners[k] for pair in zip(row_c, row_w) for k in pair)
            out.append([self.terms[t] for t in list(seen)[:N_CANDIDATES]])
        return out


SYSTEM = """You map a clinical-trial condition to the MONDO disease ontology.

Pick the single MONDO term that names the disease or condition being treated, at the level a drug-development program would call its indication (e.g. "non-small cell lung carcinoma", "ovarian cancer", "type 2 diabetes mellitus", "atopic dermatitis"). Leave out population qualifiers: line of therapy, relapsed/refractory status, biomarker or mutation subgroup, stage, severity, age group, setting (adjuvant, maintenance). Those belong to the patient subset, not the disease. Prefer the specific disease over a broad grouping when the condition names it; prefer the grouping when the condition itself is broad (e.g. "solid tumors" -> a malignant-neoplasm term).

Choose only from the candidate list. If no candidate names the core disease, set mondo_id to null and give up to three standard disease names likely to match a MONDO label, for a second search.

kind: disease (a disease, disorder, infection, injury or cancer), symptom_or_sign (e.g. pain, nausea, pruritus), procedure_or_state (e.g. anesthesia, surgery, transplantation, contraception, imaging, pregnancy), healthy_volunteers (healthy subjects, PK/bioequivalence/drug-interaction studies), or other (e.g. a trial acronym or a drug name given as the condition). mondo_id stays null for anything other than a disease unless a candidate names it exactly."""

SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["disease", "symptom_or_sign", "procedure_or_state",
                                             "healthy_volunteers", "other"]},
        "core_disease": {"type": "string"},
        "mondo_id": {"type": ["string", "null"]},
        "retry_queries": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["kind", "core_disease", "mondo_id", "retry_queries", "confidence"],
    "additionalProperties": False,
}


def render(p: dict) -> str:
    cand = "\n".join(
        f"- {c['mondo_id']} | {c['label']} | is_a: {c['parents']} | synonyms: {', '.join(c['synonyms'])}"
        + (f" | {c['definition']}" if c["definition"] else "") for c in p["candidates"])
    return (f"Condition: {p['name']}\nOther spellings: {'; '.join(p['variants'][:6]) or 'none'}\n\n"
            f"MONDO candidates:\n{cand or '(none retrieved)'}")


def validate(p: dict, out: dict) -> None:
    if out["mondo_id"] and out["mondo_id"] not in {c["mondo_id"] for c in p["candidates"]}:
        raise ValueError(f"mondo_id {out['mondo_id']} not among candidates")


TASK = llm.Task(name="indication_mondo", prompt_version="v2", schema_version="v1", system=SYSTEM,
                schema=SCHEMA, render=render, validate=validate, subject_type="indication",
                effort="medium", max_tokens=3000)


BROADER_SYSTEM = """You map a clinical-trial condition that is a disease to the MONDO disease ontology. An earlier pass found no MONDO term naming it exactly.

Pick from the candidate list:
- match "exact": a candidate names the condition's core disease itself (by label, synonym or definition), leaving population qualifiers (line of therapy, stage, biomarker, age, setting) aside. Example: "metastatic malignant neoplasm in the rectum" -> rectal cancer.
- match "broader": no candidate names it, so pick the most specific candidate whose meaning contains the condition: its nearest parent disease or grouping (e.g. "melasma" -> hyperpigmentation of the skin; "contrast-induced nephropathy" -> acute kidney injury; "finger injuries" -> injury). Prefer the narrowest candidate that still contains the whole condition.
- match "none" with mondo_id null: no candidate contains the condition, or the condition is not a disease."""

BROADER_SCHEMA = {
    "type": "object",
    "properties": {
        "match": {"type": "string", "enum": ["exact", "broader", "none"]},
        "mondo_id": {"type": ["string", "null"]},
        "rationale": {"type": "string"},
    },
    "required": ["match", "mondo_id", "rationale"],
    "additionalProperties": False,
}


def render_broader(p: dict) -> str:
    return render(p).replace("\n\nMONDO candidates:", f"\nCore disease: {p['core_disease']}\n\nMONDO candidates:")


def validate_broader(p: dict, out: dict) -> None:
    validate(p, out)
    if (out["match"] == "none") != (out["mondo_id"] is None):
        raise ValueError("match 'none' requires mondo_id null, and only then")


BROADER_TASK = llm.Task(name="indication_mondo_broader", prompt_version="v1", schema_version="v1",
                        system=BROADER_SYSTEM, schema=BROADER_SCHEMA, render=render_broader,
                        validate=validate_broader, subject_type="indication", effort="medium", max_tokens=3000)


def map_indications(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        index = MondoIndex(cur)
        cur.execute("SELECT indication_id, display_name, coalesce(ct_gov_conditions, '{}') FROM preclin.indication")
        rows = cur.fetchall()
    items = {str(r[0]): {"name": r[1], "variants": [v for v in r[2] if v != r[1]], "candidates": c}
             for r, c in zip(rows, index.search([r[1] for r in rows]))}
    final = {k: (did, d) for k, did, d in llm.decisions(llm.run(TASK, items))}

    retry = {k: d for k, (_, d) in final.items() if not d["mondo_id"] and d["kind"] == "disease" and d["retry_queries"]}
    match = {k: "exact" for k, (_, d) in final.items() if d["mondo_id"]}
    for k in retry:
        extra = [c for q in index.search(retry[k]["retry_queries"]) for c in q]
        merged = {c["mondo_id"]: c for c in items[k]["candidates"] + extra}
        items[k] = {**items[k], "candidates": list(merged.values())[:3 * N_CANDIDATES]}
    if retry:
        for k, did, d in llm.decisions(llm.run(TASK, {k: items[k] for k in retry})):
            final[k] = did, d
            if d["mondo_id"]:
                match[k] = "exact"

    unmapped = {k: d for k, (_, d) in final.items() if not d["mondo_id"] and d["kind"] == "disease"}
    broader_items = {}
    for k, d in unmapped.items():
        pool = items[k]["candidates"] + [c for q in index.search([d["core_disease"]]) for c in q]
        parents = [index.terms[p] for c in pool for p in index.parents.get(c["mondo_id"], []) if p in index.terms]
        merged = {c["mondo_id"]: c for c in pool + parents}
        broader_items[k] = {**items[k], "core_disease": d["core_disease"], "candidates": list(merged.values())[:100]}
    if broader_items:
        for k, did, d in llm.decisions(llm.run(BROADER_TASK, broader_items)):
            if d["mondo_id"]:
                final[k], match[k] = (did, {**final[k][1], "mondo_id": d["mondo_id"]}), d["match"]

    updates = [(int(k), d["mondo_id"], index.terms[d["mondo_id"]]["label"] if d["mondo_id"] else None,
                match.get(k), d["kind"], did) for k, (did, d) in final.items()]
    with llm.connect() as conn, conn.cursor() as cur:
        execute_values(cur, """UPDATE preclin.indication i SET mondo_id = u.mondo_id,
                 mondo_label = u.mondo_label, mondo_match = u.match, indication_kind = u.kind,
                 mondo_decision_id = u.did
               FROM (VALUES %s) AS u(iid, mondo_id, mondo_label, match, kind, did)
               WHERE i.indication_id = u.iid""", updates, page_size=5000)
        conn.commit()
    print(f"indications={len(rows)} decided={len(final)} mapped={sum(1 for u in updates if u[1])} "
          f"retried={len(retry)} broader_pass={len(broader_items)} "
          f"broader={sum(1 for v in match.values() if v == 'broader')}")


BIO_AREAS = ["allergy", "autoimmune", "cardiovascular", "endocrine", "gastroenterology", "hematology",
             "infectious_disease", "metabolic", "neurology", "oncology", "ophthalmology", "psychiatry",
             "respiratory", "urology", "other"]

AREA_SYSTEM = """You assign a disease to one of the disease areas of BIO's 2021 Clinical Development Success Rates report, which follows Biomedtracker's conventions.

Areas: allergy, autoimmune, cardiovascular, endocrine, gastroenterology (non-IBD), hematology, infectious_disease, metabolic, neurology, oncology, ophthalmology, psychiatry, respiratory, urology, other.
Conventions:
- oncology includes all cancers and pre-malignant neoplasms, including hematologic malignancies (leukemia, lymphoma, myeloma, MDS, myeloproliferative neoplasms) and cancer-related conditions treated with anticancer intent.
- hematology covers non-malignant blood disorders: anemias, hemoglobinopathies, hemophilia and other coagulation disorders, thrombocytopenia, neutropenia, PNH.
- autoimmune covers immune-mediated inflammatory diseases including rheumatoid arthritis, lupus, psoriasis and psoriatic arthritis, spondyloarthritis, inflammatory bowel disease (Crohn's disease, ulcerative colitis), vasculitis, Sjogren's, and transplant rejection.
- gastroenterology covers non-IBD digestive and liver diseases (e.g. GERD, IBS, NASH/MASH, cirrhosis, pancreatitis).
- metabolic covers lipid disorders, obesity, inborn errors of metabolism and lysosomal storage diseases; endocrine covers diabetes, thyroid, adrenal, pituitary, growth and reproductive-hormone disorders.
- infectious_disease covers bacterial, viral, fungal and parasitic infections, including prevention by vaccination.
- neurology includes multiple sclerosis, epilepsy, migraine, pain syndromes of neurological origin, neurodegeneration and neuromuscular disease; psychiatry includes depression, schizophrenia, bipolar disorder, anxiety, ADHD, substance use disorders and insomnia.
- respiratory includes asthma, COPD, cystic fibrosis, pulmonary fibrosis and pulmonary hypertension.
- urology covers urological conditions (overactive bladder, BPH, urinary incontinence, erectile dysfunction, interstitial cystitis).
- other covers dermatology (non-autoimmune skin disease, e.g. acne, atopic dermatitis unless clearly allergic, wounds), renal disease (CKD, glomerulonephritis, kidney transplant function), obstetrics and gynecology, non-autoimmune rheumatology (osteoarthritis, gout, osteoporosis), ENT/dental, orthopedics, and anything that fits no other area.
Choose the single best area."""

AREA_SCHEMA = {
    "type": "object",
    "properties": {"area": {"type": "string", "enum": BIO_AREAS},
                   "confidence": {"type": "string", "enum": ["high", "medium", "low"]}},
    "required": ["area", "confidence"],
    "additionalProperties": False,
}


def render_area(p: dict) -> str:
    return (f"Disease: {p['label']} ({p['mondo_id']})\nDefinition: {p['definition'] or 'none'}\n"
            f"Broader terms: {p['ancestors']}")


AREA_TASK = llm.Task(name="mondo_bio_area", prompt_version="v1", schema_version="v1", system=AREA_SYSTEM,
                     schema=AREA_SCHEMA, render=render_area, subject_type="mondo_term",
                     model="claude-opus-5-5", effort="low", max_tokens=1000)


def areas(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT t.term_id, t.label, t.definition,
                   (SELECT string_agg(a.label, '; ' ORDER BY x.distance) FROM preclin.ontology_ancestor x
                    JOIN preclin.ontology_term a ON a.term_id = x.ancestor_id
                    WHERE x.term_id = t.term_id AND x.distance <= 4)
            FROM preclin.ontology_term t
            WHERE t.term_id IN (SELECT DISTINCT mondo_id FROM preclin.dev_program WHERE mondo_id IS NOT NULL)""")
        items = {tid: {"mondo_id": tid, "label": label, "definition": (definition or "")[:400],
                       "ancestors": anc or ""} for tid, label, definition, anc in cur.fetchall()}
    run_id = llm.run(AREA_TASK, items)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.mondo_bio_area")
        cur.execute("""INSERT INTO preclin.mondo_bio_area (mondo_id, bio_area, llm_decision_id)
                       SELECT subject_key, parsed_output->>'area', llm_decision_id FROM pv_evidence.llm_decision
                       WHERE decision_run_id = %s AND validation_status = 'validated'""", (str(run_id),))
        conn.commit()
    print(f"diseases={len(items)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("map").set_defaults(fn=map_indications)
    sub.add_parser("areas").set_defaults(fn=areas)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
