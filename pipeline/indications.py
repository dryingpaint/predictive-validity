"""Map every preclin.indication to the MONDO term for its core disease.

    python -m pipeline.indications map

Candidates come from the OLS4 search API (MONDO) for the indication's name and
canonical disease. The LLM picks the MONDO term naming the disease itself,
leaving population qualifiers (line, stage, biomarker, age) aside, or reports
that none fits and proposes better search terms; a second retrieval round runs
for those. Results go to preclin.indication.mondo_id / mondo_label /
mondo_decision_id.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests
from psycopg2.extras import execute_values

from pipeline import llm

CACHE = os.path.join(llm.REPO, ".cache", "ols")
OLS = "https://www.ebi.ac.uk/ols4/api/search"


def ols_search(query: str, rows: int = 10) -> list[dict]:
    """MONDO classes matching `query` (cached per query string)."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, hashlib.sha256(f"{rows}|{query}".encode()).hexdigest() + ".json")
    if os.path.exists(path):
        return json.load(open(path))
    params = {"q": query, "ontology": "mondo", "type": "class", "rows": rows,
              "fieldList": "obo_id,label,exact_synonyms,description,is_obsolete"}
    for attempt in range(5):
        try:
            r = requests.get(OLS, params=params, timeout=60)
            r.raise_for_status()
            break
        except requests.RequestException:
            if attempt == 4:
                raise
    docs = [{"mondo_id": d.get("obo_id"), "label": d.get("label"),
             "synonyms": (d.get("exact_synonyms") or [])[:6],
             "definition": ((d.get("description") or [""])[0] or "")[:300]}
            for d in r.json()["response"]["docs"]
            if (d.get("obo_id") or "").startswith("MONDO:") and not d.get("is_obsolete")]
    json.dump(docs, open(path, "w"))
    return docs


def candidates(queries: list[str]) -> list[dict]:
    seen, out = set(), []
    for q in queries:
        for doc in ols_search(q):
            if doc["mondo_id"] not in seen:
                seen.add(doc["mondo_id"])
                out.append(doc)
    return out


SYSTEM = """You map a clinical-trial indication to the MONDO disease ontology.

Pick the single MONDO term that names the disease or condition being treated, at the level a drug-development program would call its indication (e.g. "non-small cell lung carcinoma", "ovarian cancer", "type 2 diabetes mellitus", "atopic dermatitis"). Leave out population qualifiers: line of therapy, relapsed/refractory status, biomarker or mutation subgroup, stage, severity, age group, setting (adjuvant, maintenance). Those belong to the patient subset, not the disease. Prefer the specific disease over a broad grouping when the indication names it; prefer the grouping when the indication itself is broad (e.g. "solid tumors").

Choose only from the candidate list. If no candidate names the core disease, set mondo_id to null and give up to three short search queries (standard disease names) likely to retrieve the right MONDO term.

kind: disease (a disease, disorder, infection, injury or cancer), symptom_or_sign (e.g. pain, nausea, pruritus), procedure_or_state (e.g. anesthesia, surgery, transplantation, contraception, imaging), healthy_volunteers (healthy subjects, PK/bioequivalence/drug-interaction studies), or other. Use mondo_id null for anything other than a disease unless a candidate names it exactly."""

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
    cand = "\n".join(f"- {c['mondo_id']} | {c['label']} | synonyms: {', '.join(c['synonyms'])}"
                     + (f" | {c['definition']}" if c["definition"] else "") for c in p["candidates"])
    return (f"Indication: {p['name']}\nCanonical disease (earlier automated guess): {p['canonical']}\n"
            f"ClinicalTrials.gov condition strings: {'; '.join(p['conditions'][:8])}\n\n"
            f"MONDO candidates:\n{cand or '(none retrieved)'}")


def validate(p: dict, out: dict) -> None:
    if out["mondo_id"] and out["mondo_id"] not in {c["mondo_id"] for c in p["candidates"]}:
        raise ValueError(f"mondo_id {out['mondo_id']} not among candidates")


TASK = llm.Task(name="indication_mondo", prompt_version="v1", schema_version="v1", system=SYSTEM,
                schema=SCHEMA, render=render, validate=validate, subject_type="indication",
                effort="medium", max_tokens=3000)


def map_indications(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT indication_id, display_name, canonical_disease, "
                    "coalesce(ct_gov_conditions, '{}') FROM preclin.indication")
        rows = cur.fetchall()

    def payload(row, extra_queries=()):
        iid, name, canonical, conditions = row
        queries = [q for q in dict.fromkeys([canonical, name, *extra_queries]) if q]
        return str(iid), {"name": name, "canonical": canonical, "conditions": list(conditions),
                          "candidates": candidates(queries)}

    with ThreadPoolExecutor(max_workers=8) as pool:
        items = dict(pool.map(payload, rows))
    run1 = llm.run(TASK, items)
    first = llm.decisions(run1)

    retry_rows = [r for r in rows if (d := first.get(str(r[0]))) and not d["mondo_id"]
                  and d["kind"] == "disease" and d["retry_queries"]]
    final = dict(first)
    runs = {k: run1 for k in first}
    if retry_rows:
        with ThreadPoolExecutor(max_workers=8) as pool:
            retry_items = dict(pool.map(lambda r: payload(r, first[str(r[0])]["retry_queries"]), retry_rows))
        run2 = llm.run(TASK, retry_items)
        for k, d in llm.decisions(run2).items():
            final[k], runs[k] = d, run2

    labels = {c["mondo_id"]: c["label"] for p in items.values() for c in p["candidates"]}
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT subject_key, decision_run_id, llm_decision_id FROM pv_evidence.llm_decision
                       WHERE decision_run_id = ANY(%s::uuid[]) AND validation_status = 'validated'""",
                    ([str(r) for r in set(runs.values())],))
        ids = {(k, str(run)): did for k, run, did in cur.fetchall()}
        updates = [(int(k), d["mondo_id"], labels.get(d["mondo_id"]) if d["mondo_id"] else None,
                    d["kind"], ids[(k, str(runs[k]))]) for k, d in final.items()]
        execute_values(cur, """UPDATE preclin.indication i SET mondo_id = u.mondo_id,
                 mondo_label = u.mondo_label, indication_kind = u.kind, mondo_decision_id = u.did
               FROM (VALUES %s) AS u(iid, mondo_id, mondo_label, kind, did)
               WHERE i.indication_id = u.iid""", updates)
        conn.commit()
    mapped = sum(1 for u in updates if u[1])
    print(f"indications={len(rows)} decided={len(final)} mapped_to_mondo={mapped} retried={len(retry_rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("map").set_defaults(fn=map_indications)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
