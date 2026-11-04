"""Computed physicochemical properties of each molecular entity -> preclin.moiety_property.

    python -m pipeline.pubchem properties

Every entity whose UNII substance carries a PubChem CID (preclin.unii_substance) takes PubChem's computed
properties of that CID, read from PUG REST in batches of CIDS_PER_CALL. A small-molecule entity with a
development program and no CID takes ChEMBL's molecule_properties of its ChEMBL parent
(preclin.chembl_moiety, from pipeline.chembl activities; the parent matched by ChEMBL id before one matched
by structure or name). Responses are cached under .cache/pubchem/<date>, and each pull is recorded in
preclin.evidence_source_release. Rule-of-5 violations are counted from the stored values.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import time
from datetime import date

import requests
from psycopg2.extras import execute_values

from pipeline import llm
from pipeline.chembl import API as CHEMBL_API, IDS_PER_CALL, PAGE, get as chembl_get

PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/property"
PROPERTIES = "MolecularWeight,XLogP,TPSA,HBondDonorCount,HBondAcceptorCount,RotatableBondCount"
CIDS_PER_CALL = 200
PUBCHEM_PAUSE = 0.25  # PubChem allows at most 5 requests a second
BASIS_ORDER = {"drug_chembl_id": 0, "inchikey": 1, "name": 2}


def pubchem(cids: list[str]) -> list[dict]:
    for attempt in range(6):
        try:
            r = requests.post(f"{PUG}/{PROPERTIES}/JSON", data={"cid": ",".join(cids)}, timeout=180)
            if r.status_code == 404:  # none of the CIDs exists any more
                return []
            r.raise_for_status()
            time.sleep(PUBCHEM_PAUSE)
            return r.json()["PropertyTable"]["Properties"]
        except requests.RequestException:
            if attempt == 5:
                raise
            time.sleep(10 * (attempt + 1))


def cached(path: str, fetch):
    if not os.path.exists(path):
        data = fetch()
        with open(path, "w") as f:
            json.dump(data, f)
    return json.load(open(path))


def number(value, kind=float):
    return None if value in (None, "") else kind(float(value))


def ro5(mw, logp, hbd, hba) -> int:
    return sum([mw is not None and mw > 500, logp is not None and logp > 5,
                hbd is not None and hbd > 5, hba is not None and hba > 10])


def properties(_args) -> None:
    cache = os.path.join(llm.REPO, ".cache", "pubchem", date.today().isoformat())
    os.makedirs(cache, exist_ok=True)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT m.moiety_id, u.pubchem_cid FROM preclin.moiety m
                       JOIN preclin.unii_substance u USING (unii) WHERE u.pubchem_cid IS NOT NULL""")
        by_cid = cur.fetchall()
        cur.execute("""SELECT cm.moiety_id, cm.parent_chembl_id, cm.basis FROM preclin.chembl_moiety cm
                       JOIN preclin.moiety m USING (moiety_id)
                       WHERE m.modality = 'small_molecule'
                         AND EXISTS (SELECT 1 FROM preclin.dev_program p WHERE p.moiety_id = m.moiety_id)""")
        chembl_rows = cur.fetchall()
    cids = sorted({c for _, c in by_cid}, key=int)
    props = {}
    for i in range(0, len(cids), CIDS_PER_CALL):
        chunk = cids[i:i + CIDS_PER_CALL]
        for p in cached(os.path.join(cache, f"pubchem_{i:06d}.json"), lambda: pubchem(chunk)):
            props[str(p["CID"])] = p
    rows = {}
    for moiety_id, cid in by_cid:
        p = props.get(cid)
        if p is None:
            continue
        mw, logp = number(p.get("MolecularWeight")), number(p.get("XLogP"))
        hbd, hba = number(p.get("HBondDonorCount"), int), number(p.get("HBondAcceptorCount"), int)
        rows[moiety_id] = ("pubchem", cid, mw, logp, number(p.get("TPSA")), hbd, hba,
                           number(p.get("RotatableBondCount"), int), ro5(mw, logp, hbd, hba))
    parent = {}
    for moiety_id, chembl_id, basis in sorted(chembl_rows, key=lambda r: (BASIS_ORDER[r[2]], r[1])):
        if moiety_id not in rows:
            parent.setdefault(moiety_id, chembl_id)
    chembl_ids = sorted(set(parent.values()))
    mols = {}
    for i in range(0, len(chembl_ids), IDS_PER_CALL):
        chunk = chembl_ids[i:i + IDS_PER_CALL]
        page = cached(os.path.join(cache, f"chembl_{i:06d}.json"), lambda: chembl_get(
            "molecule.json", limit=PAGE, molecule_chembl_id__in=",".join(chunk),
            only="molecule_chembl_id,molecule_properties"))
        mols.update({m["molecule_chembl_id"]: m.get("molecule_properties") or {} for m in page["molecules"]})
    for moiety_id, chembl_id in parent.items():
        p = mols.get(chembl_id)
        if not p or p.get("full_mwt") is None:
            continue
        mw, logp = number(p.get("full_mwt")), number(p.get("alogp"))
        hbd, hba = number(p.get("hbd"), int), number(p.get("hba"), int)
        rows[moiety_id] = ("chembl", chembl_id, mw, logp, number(p.get("psa")), hbd, hba,
                           number(p.get("rtb"), int), ro5(mw, logp, hbd, hba))
    with llm.connect() as conn, conn.cursor() as cur:
        ids = {}
        for source, url in (("pubchem", PUG), ("chembl", CHEMBL_API)):
            files = sorted(glob.glob(os.path.join(cache, f"{source}_*.json")))
            sha = hashlib.sha256(b"".join(open(p, "rb").read() for p in files)).hexdigest()
            n = sum(r[0] == source for r in rows.values())
            ids[source] = llm.register_release(cur, f"{source}_computed_properties", date.today().isoformat(), url,
                                               sha, {"n_entities": n, "n_requests": len(files)})
        cur.execute("DELETE FROM preclin.moiety_property")
        execute_values(cur, """INSERT INTO preclin.moiety_property (moiety_id, source, source_id, molecular_weight,
                                 logp, tpsa, hbd, hba, rotatable_bonds, ro5_violations, source_release_id)
                               VALUES %s""", [(m, *r, ids[r[0]]) for m, r in rows.items()])
        conn.commit()
    print(f"cids={len(cids)} pubchem={sum(r[0] == 'pubchem' for r in rows.values())} "
          f"chembl={sum(r[0] == 'chembl' for r in rows.values())} of {len(parent)} small molecules without a CID")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("properties").set_defaults(fn=properties)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
