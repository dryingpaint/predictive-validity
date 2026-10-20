"""Pinned MONDO and EFO releases -> preclin.ontology_* tables.

    python -m pipeline.ontology load

Downloads each ontology's OBO release, records it in
preclin.evidence_source_release, and loads terms, is_a edges, the transitive
ancestor closure (with distances) and cross-references. MONDO is the disease
vocabulary for indications; EFO is needed to place GWAS Catalog traits.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from collections import defaultdict, deque

import requests
from psycopg2.extras import Json, execute_values

from pipeline import llm

CACHE = os.path.join(llm.REPO, ".cache", "ontology")
SOURCES = {
    "MONDO": "https://github.com/monarch-initiative/mondo/releases/latest/download/mondo.obo",
    "EFO": "https://github.com/EBISPOT/efo/releases/latest/download/efo.obo",
}


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


def parse_obo(path: str) -> tuple[dict[str, str], list[dict]]:
    """(header, terms): one dict per [Term] stanza with id, name, def, exact synonyms, is_a, xrefs,
    replaced_by and obsolete flag; identifiers in CURIE form."""
    header, terms, term = {}, [], None
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
                if key == "data-version" or key == "format-version":
                    header[key] = value
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
                term["xrefs"].append(norm_id(value))
            elif key == "replaced_by":
                term["replaced_by"] = norm_id(value)
            elif key == "is_obsolete" and value == "true":
                term["obsolete"] = True
    if term:
        terms.append(term)
    return header, terms


def closure(parents: dict[str, list[str]]) -> list[tuple[str, str, int]]:
    """(term, ancestor, shortest is_a distance) for every term, excluding self."""
    rows = []
    for term in parents:
        seen = {term: 0}
        queue = deque([term])
        while queue:
            node = queue.popleft()
            for parent in parents.get(node, ()):
                if parent not in seen:
                    seen[parent] = seen[node] + 1
                    queue.append(parent)
        rows.extend((term, anc, d) for anc, d in seen.items() if anc != term)
    return rows


def load(_args) -> None:
    os.makedirs(CACHE, exist_ok=True)
    for prefix, url in SOURCES.items():
        path = os.path.join(CACHE, os.path.basename(url))
        if not os.path.exists(path):
            with requests.get(url, stream=True, timeout=600) as r, open(path, "wb") as f:
                r.raise_for_status()
                for block in r.iter_content(1 << 20):
                    f.write(block)
        sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
        header, terms = parse_obo(path)
        version = header.get("data-version", "unknown")
        if prefix == "MONDO":
            terms = [t for t in terms if t.get("id", "").startswith("MONDO:")]
            graph = {}
        else:  # EFO imports MONDO terms; those stay owned by the MONDO release.
            terms = [t for t in terms if "id" in t and not t["id"].startswith("MONDO:")]
            with llm.connect() as conn, conn.cursor() as cur:
                cur.execute("SELECT child_id, parent_id FROM preclin.ontology_is_a WHERE ontology = 'MONDO'")
                graph = defaultdict(list)
                for child, parent in cur.fetchall():
                    graph[child].append(parent)
        parents = defaultdict(list)
        for t in terms:
            if not t["obsolete"]:
                parents[t["id"]].extend(t["is_a"])
        anc = [r for r in closure({**graph, **parents}) if r[0] in parents]
        with llm.connect() as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO preclin.evidence_source_release
                  (source_name, source_version, source_url, content_sha256, metadata)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (source_name, source_version, content_sha256) DO UPDATE SET metadata = EXCLUDED.metadata
                RETURNING source_release_id""",
                        (f"{prefix.lower()}_obo", version, url, sha, Json({"n_terms": len(terms)})))
            release = cur.fetchone()[0]
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
            execute_values(cur, """INSERT INTO preclin.ontology_xref (ontology, term_id, xref_id) VALUES %s
                                   ON CONFLICT DO NOTHING""",
                           [(prefix, t["id"], x) for t in terms for x in set(t["xrefs"])], page_size=5000)
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
