"""Map every condition string (preclin.indication) to the MONDO term for its core disease.

    python -m pipeline.indications map   # LLM choice among MONDO candidates -> indication.mondo_id

Condition strings enter preclin.indication through pipeline.programs register.

Candidates come from the pinned MONDO release in preclin.ontology_term:
character n-gram TF-IDF retrieval over labels and exact synonyms. The LLM
picks the term naming the disease itself, leaving population qualifiers (line,
stage, biomarker, age) aside, or reports that none fits and proposes standard
disease names; a second retrieval round runs on those names.
"""
from __future__ import annotations

import argparse
import re

import numpy as np
from psycopg2.extras import execute_values
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

from pipeline import llm

N_CANDIDATES = 20


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower().strip())


class MondoIndex:
    """Nearest-neighbour search over MONDO labels and exact synonyms."""

    def __init__(self, cur):
        cur.execute("""SELECT t.term_id, t.label, t.synonyms, t.definition,
                              (SELECT string_agg(p.label, '; ') FROM preclin.ontology_is_a e
                               JOIN preclin.ontology_term p ON p.term_id = e.parent_id
                               WHERE e.child_id = t.term_id)
                       FROM preclin.ontology_term t
                       WHERE t.ontology = 'MONDO' AND NOT t.is_obsolete""")
        self.terms = {}
        strings, owners = [], []
        for tid, label, syns, definition, parents in cur.fetchall():
            self.terms[tid] = {"mondo_id": tid, "label": label, "synonyms": list(syns)[:6],
                               "parents": parents or "", "definition": (definition or "")[:240]}
            for s in [label, *syns]:
                strings.append(s.lower())
                owners.append(tid)
        self.owners = np.array(owners)
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
            seen = []
            for a, b in zip(row_c, row_w):
                for k in (a, b):
                    tid = self.owners[k]
                    if tid not in seen:
                        seen.append(tid)
            out.append([self.terms[t] for t in seen[:N_CANDIDATES]])
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


def map_indications(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        index = MondoIndex(cur)
        cur.execute("SELECT indication_id, display_name, coalesce(ct_gov_conditions, '{}') FROM preclin.indication")
        rows = cur.fetchall()
    names = [r[1] for r in rows]
    cands = index.search(names)
    items = {str(r[0]): {"name": r[1], "variants": [v for v in r[2] if v != r[1]], "candidates": c}
             for r, c in zip(rows, cands)}
    run1 = llm.run(TASK, items)
    first = llm.decisions(run1)

    retry = {k: v for k, v in first.items() if not v["mondo_id"] and v["kind"] == "disease" and v["retry_queries"]}
    final, runs = dict(first), {k: run1 for k in first}
    if retry:
        keys = list(retry)
        retry_items = {}
        for k in keys:
            extra = [c for q in index.search(retry[k]["retry_queries"]) for c in q]
            merged = {c["mondo_id"]: c for c in items[k]["candidates"] + extra}
            retry_items[k] = {**items[k], "candidates": list(merged.values())[:3 * N_CANDIDATES]}
        run2 = llm.run(TASK, retry_items)
        for k, d in llm.decisions(run2).items():
            final[k], runs[k] = d, run2

    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT subject_key, decision_run_id, llm_decision_id FROM pv_evidence.llm_decision
                       WHERE decision_run_id = ANY(%s::uuid[]) AND validation_status = 'validated'""",
                    ([str(r) for r in set(runs.values())],))
        ids = {(k, str(run)): did for k, run, did in cur.fetchall()}
        updates = [(int(k), d["mondo_id"], index.terms[d["mondo_id"]]["label"] if d["mondo_id"] else None,
                    d["kind"], ids[(k, str(runs[k]))]) for k, d in final.items()]
        execute_values(cur, """UPDATE preclin.indication i SET mondo_id = u.mondo_id,
                 mondo_label = u.mondo_label, indication_kind = u.kind, mondo_decision_id = u.did
               FROM (VALUES %s) AS u(iid, mondo_id, mondo_label, kind, did)
               WHERE i.indication_id = u.iid""", updates, page_size=5000)
        conn.commit()
    print(f"indications={len(rows)} decided={len(final)} mapped={sum(1 for u in updates if u[1])} "
          f"retried={len(retry)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("map").set_defaults(fn=map_indications)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
