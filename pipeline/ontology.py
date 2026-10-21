"""MONDO and Mammalian Phenotype OBO releases -> preclin.ontology_* tables.

    python -m pipeline.ontology load

Downloads each ontology's latest OBO release once (SOURCES points at the latest
release); the cached file under .cache/ontology is what pins it. Records it in
preclin.evidence_source_release, and loads terms, is_a edges, the transitive
ancestor closure (with distances) and cross-references, flagging those MONDO
declares equivalent. MONDO is the disease vocabulary for indications and for
matching Open Targets evidence to them; MP places mouse mutant phenotypes
(preclin.ot_mouse_phenotype), e.g. under preweaning lethality.
"""
from __future__ import annotations

import argparse
import os
from collections import defaultdict, deque
from collections.abc import Iterable

import requests
from psycopg2.extras import execute_values

from pipeline import llm

CACHE = os.path.join(llm.REPO, ".cache", "ontology")
SOURCES = {"MONDO": "https://github.com/monarch-initiative/mondo/releases/latest/download/mondo.obo",
           "MP": "http://purl.obolibrary.org/obo/mp.obo"}


def norm_id(value: str) -> str:
    """CURIE form: efo:EFO_0000270 and .../obo/EFO_0000270 -> EFO:0000270."""
    value = value.split(" ")[0]
    if value.startswith("efo:"):
        value = value[4:]
    if "/obo/" in value or "/efo/" in value:
        value = value.rsplit("/", 1)[1]
    if ":" not in value and "_" in value:
        prefix, local = value.split("_", 1)
        value = f"{prefix}:{local}"
    return value


def parse_obo(path: str) -> tuple[str, list[dict]]:
    """(data-version, terms): one dict per [Term] stanza with id, name, def, exact synonyms, is_a, xrefs
    as (id, declared equivalent), replaced_by and obsolete flag; identifiers in CURIE form."""
    version, terms, term = "unknown", [], None
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if line.startswith("["):
                if term:
                    terms.append(term)
                term = ({"synonyms": [], "is_a": [], "xrefs": [], "replaced_by": None, "obsolete": False}
                        if line == "[Term]" else None)
                continue
            if ": " not in line:
                continue
            key, value = line.split(": ", 1)
            if term is None:
                if key == "data-version":
                    version = value
                continue
            if key == "id":
                term["id"] = norm_id(value)
            elif key == "name":
                term["name"] = value
            elif key == "def":
                term["def"] = value.split('"')[1] if value.startswith('"') else value
            elif key == "synonym" and value.startswith('"'):
                text, rest = value[1:].split('"', 1)
                if "EXACT" in rest.split("[")[0]:
                    term["synonyms"].append(text)
            elif key == "is_a":
                term["is_a"].append(norm_id(value))
            elif key == "xref":
                term["xrefs"].append((norm_id(value), 'source="MONDO:equivalentTo"' in value))
            elif key == "replaced_by":
                term["replaced_by"] = norm_id(value)
            elif key == "is_obsolete" and value == "true":
                term["obsolete"] = True
    if term:
        terms.append(term)
    return version, terms


def closure(graph: dict[str, list[str]], terms: Iterable[str]) -> list[tuple[str, str, int]]:
    """(term, ancestor, shortest is_a distance) for each of terms, excluding self."""
    rows = []
    for term in terms:
        seen = {term: 0}
        queue = deque([term])
        while queue:
            node = queue.popleft()
            for parent in graph.get(node, ()):
                if parent not in seen:
                    seen[parent] = seen[node] + 1
                    queue.append(parent)
        rows.extend((term, anc, d) for anc, d in seen.items() if anc != term)
    return rows


def load(_args) -> None:
    os.makedirs(CACHE, exist_ok=True)
    with llm.connect() as conn, conn.cursor() as cur:  # ontologies no longer in SOURCES
        for table in ("ontology_ancestor", "ontology_xref", "ontology_is_a", "ontology_term"):
            cur.execute(f"DELETE FROM preclin.{table} WHERE ontology <> ALL(%s)", (list(SOURCES),))
    for prefix, url in SOURCES.items():
        path = os.path.join(CACHE, os.path.basename(url))
        if not os.path.exists(path):
            with requests.get(url, stream=True, timeout=600) as r, open(path, "wb") as f:
                r.raise_for_status()
                for block in r.iter_content(1 << 20):
                    f.write(block)
        sha = llm.sha256_file(path)
        version, terms = parse_obo(path)
        terms = [t for t in terms if t.get("id", "").startswith(f"{prefix}:")]
        parents = defaultdict(list)
        for t in terms:
            if not t["obsolete"]:
                parents[t["id"]].extend(t["is_a"])
        anc = closure(parents, parents)
        with llm.connect() as conn, conn.cursor() as cur:
            release = llm.register_release(cur, f"{prefix.lower()}_obo", version, url, sha, {"n_terms": len(terms)})
            cur.execute("DELETE FROM preclin.ontology_ancestor WHERE ontology = %s", (prefix,))
            cur.execute("DELETE FROM preclin.ontology_xref WHERE ontology = %s", (prefix,))
            cur.execute("DELETE FROM preclin.ontology_is_a WHERE ontology = %s", (prefix,))
            cur.execute("DELETE FROM preclin.ontology_term WHERE ontology = %s", (prefix,))
            execute_values(cur, """INSERT INTO preclin.ontology_term
                (term_id, ontology, label, definition, synonyms, is_obsolete, replaced_by, source_release_id)
                VALUES %s ON CONFLICT (term_id) DO NOTHING""",
                [(t["id"], prefix, t.get("name", ""), t.get("def"), t["synonyms"], t["obsolete"],
                  t["replaced_by"], release) for t in terms], page_size=5000)
            execute_values(cur, """INSERT INTO preclin.ontology_is_a (ontology, child_id, parent_id) VALUES %s
                                   ON CONFLICT DO NOTHING""",
                           [(prefix, c, p) for c, ps in parents.items() for p in set(ps)], page_size=5000)
            xrefs = {(t["id"], x): False for t in terms for x, _ in t["xrefs"]}
            xrefs.update({(t["id"], x): True for t in terms for x, eq in t["xrefs"] if eq})
            execute_values(cur, """INSERT INTO preclin.ontology_xref (ontology, term_id, xref_id, equivalent) VALUES %s
                                   ON CONFLICT DO NOTHING""",
                           [(prefix, term, x, eq) for (term, x), eq in xrefs.items()], page_size=5000)
            execute_values(cur, """INSERT INTO preclin.ontology_ancestor (ontology, term_id, ancestor_id, distance)
                                   VALUES %s ON CONFLICT DO NOTHING""", [(prefix, *r) for r in anc], page_size=10000)
            conn.commit()
        print(f"{prefix} {version}: terms={len(terms)} is_a={sum(len(p) for p in parents.values())} "
              f"ancestor_rows={len(anc)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("load").set_defaults(fn=load)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
