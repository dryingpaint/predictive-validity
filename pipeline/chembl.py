"""ChEMBL drug mechanisms of action -> preclin.chembl_mechanism, preclin.chembl_molecule.

    python -m pipeline.chembl load

Reads every mechanism record of the release the ChEMBL web services serve
(status.json gives the release, which names the cache directory and is recorded
in preclin.evidence_source_release), the targets they name, and the parent of
every ChEMBL molecule preclin.drug carries. A human target's genes are its
UniProt components mapped to HGNC approved symbols (preclin.hgnc_gene), so a
protein complex or multi-target record keeps all its genes. pipeline.targets
shows these records to the LLM that assigns each entity's targets.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os

import requests
from psycopg2.extras import execute_values

from pipeline import llm

API = "https://www.ebi.ac.uk/chembl/api/data"
PAGE = 1000
IDS_PER_CALL = 50


def get(path: str, **params) -> dict:
    for attempt in range(6):
        try:
            r = requests.get(f"{API}/{path}", params=params, timeout=180)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == 5:
                raise


def cached(cache: str, name: str, fetch) -> dict:
    path = os.path.join(cache, f"{name}.json")
    if not os.path.exists(path):
        data = fetch()
        with open(path, "w") as f:
            json.dump(data, f)
    return json.load(open(path))


def load(_args) -> None:
    status = get("status.json")
    release = status["chembl_db_version"]
    cache = os.path.join(llm.REPO, ".cache", "chembl", release)
    os.makedirs(cache, exist_ok=True)
    mechanisms, offset = [], 0
    while True:
        page = cached(cache, f"mechanism_{offset:06d}",
                      lambda: get("mechanism.json", limit=PAGE, offset=offset, order_by="mec_id"))
        mechanisms += page["mechanisms"]
        if not page["page_meta"]["next"]:
            break
        offset += PAGE
    target_ids = sorted({m["target_chembl_id"] for m in mechanisms if m["target_chembl_id"]})
    targets = {}
    for i in range(0, len(target_ids), IDS_PER_CALL):
        chunk = target_ids[i:i + IDS_PER_CALL]
        page = cached(cache, f"target_{i:06d}", lambda: get("target.json", limit=PAGE,
                                                            target_chembl_id__in=",".join(chunk)))
        targets.update({t["target_chembl_id"]: t for t in page["targets"]})
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT DISTINCT chembl_id FROM preclin.drug WHERE chembl_id IS NOT NULL ORDER BY 1")
        drug_ids = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT u, symbol FROM preclin.hgnc_gene, unnest(uniprot_ids) u")
        by_uniprot = dict(cur.fetchall())
    parents = {}
    for i in range(0, len(drug_ids), IDS_PER_CALL):
        chunk = drug_ids[i:i + IDS_PER_CALL]
        page = cached(cache, f"molecule_{chunk[0]}_{len(chunk)}", lambda: get(
            "molecule.json", limit=PAGE, molecule_chembl_id__in=",".join(chunk),
            only="molecule_chembl_id,molecule_hierarchy"))
        for m in page["molecules"]:
            parents[m["molecule_chembl_id"]] = (m.get("molecule_hierarchy") or {}).get("parent_chembl_id") \
                or m["molecule_chembl_id"]

    def genes(target_id: str | None) -> list[str]:
        t = targets.get(target_id)
        if not t or t.get("organism") != "Homo sapiens":
            return []
        return sorted({by_uniprot[c["accession"]] for c in t.get("target_components") or []
                       if c.get("accession") in by_uniprot})

    rows = [(m["mec_id"], m["molecule_chembl_id"], m["parent_molecule_chembl_id"] or m["molecule_chembl_id"],
             m["target_chembl_id"], (targets.get(m["target_chembl_id"]) or {}).get("pref_name"), m["action_type"],
             m["mechanism_of_action"], genes(m["target_chembl_id"])) for m in mechanisms]
    sha = hashlib.sha256(b"".join(open(p, "rb").read() for p in sorted(glob.glob(os.path.join(cache, "*.json")))))
    with llm.connect() as conn, conn.cursor() as cur:
        rid = llm.register_release(cur, "chembl_mechanism", release, API, sha.hexdigest(),
                                   {"release_date": status["chembl_release_date"], "n_mechanisms": len(rows),
                                    "n_targets": len(targets), "n_molecules": len(parents)})
        cur.execute("DELETE FROM preclin.chembl_mechanism")
        cur.execute("DELETE FROM preclin.chembl_molecule")
        execute_values(cur, """INSERT INTO preclin.chembl_mechanism (mec_id, molecule_chembl_id, parent_chembl_id,
                                 target_chembl_id, target_name, action_type, mechanism_of_action, symbols,
                                 source_release_id) VALUES %s""", [(*r, rid) for r in rows], page_size=5000)
        execute_values(cur, """INSERT INTO preclin.chembl_molecule (molecule_chembl_id, parent_chembl_id,
                                 source_release_id) VALUES %s""", [(m, p, rid) for m, p in parents.items()],
                       page_size=5000)
        conn.commit()
    print(f"{release}: mechanisms={len(rows)} with human genes={sum(bool(r[-1]) for r in rows)} "
          f"targets={len(targets)} molecules={len(parents)} of {len(drug_ids)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("load").set_defaults(fn=load)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
