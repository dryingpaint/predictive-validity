"""FDA UNII substance lists -> preclin.unii_substance, preclin.unii_name and preclin.unii_parent.

    python -m pipeline.unii load

Downloads the GSRS public UNII records pinned to RELEASE and the list of all
registered names, which the archive serves only as latest: the copy cached
under .cache/unii at first download pins the names (both URLs are recorded in
the release metadata). Records the release in preclin.evidence_source_release,
upserts substances (entities may reference them) and replaces the names and the
parent of each salt, hydrate or solvate (parents). pipeline.drugs unii resolves
molecular entities against these names and offers each candidate's parent.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
import re
import zipfile
from collections import Counter, defaultdict

import requests
from psycopg2.extras import execute_values
from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize

from pipeline import llm
from pipeline.drugs import moiety_key

CACHE = os.path.join(llm.REPO, ".cache", "unii")
RELEASE = "2026-08-04"
ARCHIVE = "https://precision.fda.gov/uniisearch/archive"
FILES = {"records": f"{ARCHIVE}/{RELEASE}/UNII_Data_{RELEASE.replace('-', '')}.zip",
         "names": f"{ARCHIVE}/latest/UNIIs.zip"}
RDLogger.DisableLog("rdApp.*")  # GSRS SMILES that RDKit rejects are skipped, not reported one by one
COUNTER_ION = 50  # a parent found in more salts than this is a counter-ion (mesylate, citrate), not offered


def read_member(path: str, prefix: str) -> list[dict]:
    with zipfile.ZipFile(path) as zf:
        member = next(n for n in zf.namelist() if os.path.basename(n).startswith(prefix))
        text = io.TextIOWrapper(zf.open(member), encoding="utf-8", errors="replace")
        return list(csv.DictReader(text, delimiter="\t", quoting=csv.QUOTE_NONE))


def structure(smiles: str) -> tuple[int, list[str]]:
    """The number of components of a structure and the canonical SMILES of each one that contains
    carbon, neutralised where protons account for its charge; (0, []) when it does not parse."""
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        return 0, []
    uncharger = rdMolStandardize.Uncharger()
    parts = Chem.GetMolFrags(mol, asMols=True)
    return len(parts), [Chem.MolToSmiles(uncharger.uncharge(p)) for p in parts
                        if any(a.GetAtomicNum() == 6 for a in p.GetAtoms())]


def parents(records: list[dict]) -> set[tuple[str, str]]:
    """(unii, parent unii): each record of several components (a salt, hydrate or solvate) and
    every single-component ingredient substance whose structure is one of its carbon-containing
    components, both neutralised, leaving out counter-ions."""
    structures = {r["UNII"]: structure(r["SMILES"]) for r in records}
    by_structure = defaultdict(set)
    for r in records:
        n, parts = structures[r["UNII"]]
        if n == 1 and parts and r["INGREDIENT_TYPE"] == "INGREDIENT SUBSTANCE":
            by_structure[parts[0]].add(r["UNII"])
    pairs = {(u, p) for u, (n, parts) in structures.items() if n > 1
             for part in parts for p in by_structure.get(part, ()) if p != u}
    salts = Counter(p for _, p in pairs)
    return {(u, p) for u, p in pairs if salts[p] <= COUNTER_ION}


def load(_args) -> None:
    os.makedirs(CACHE, exist_ok=True)
    paths = {}
    for kind, url in FILES.items():
        paths[kind] = os.path.join(CACHE, os.path.basename(url))
        if not os.path.exists(paths[kind]):
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=600)
            r.raise_for_status()
            open(paths[kind], "wb").write(r.content)
    records = read_member(paths["records"], "UNII_Records")
    names = read_member(paths["names"], "UNII_Names")
    sha = hashlib.sha256(b"".join(open(p, "rb").read() for p in paths.values())).hexdigest()
    substances = {r["UNII"]: (r["UNII"], r["DISPLAY_NAME"], r["SUBSTANCE_TYPE"] or None, r["INGREDIENT_TYPE"] or None,
                              r["INN_ID"] or None, r["USAN_ID"] or None, r["RXCUI"] or None, r["PUBCHEM"] or None,
                              r["INCHIKEY"] or None) for r in records}
    # A name's key drops bracketed source tags ([INN], [USAN], [WHO-DD]), then applies the moiety key.
    name_rows = {(n["UNII"], n["NAME"], n["TYPE"]): moiety_key(re.sub(r"\[[^\]]*\]", "", n["NAME"])) for n in names
                 if n["UNII"] in substances and n["NAME"]}
    parent_rows = parents(records)
    with llm.connect() as conn, conn.cursor() as cur:
        release = llm.register_release(cur, "fda_unii", RELEASE, ARCHIVE, sha,
                                       {"n_substances": len(substances), "n_names": len(name_rows),
                                        "n_parents": len(parent_rows), "files": FILES})
        cur.execute("DELETE FROM preclin.unii_name")
        cur.execute("DELETE FROM preclin.unii_parent")
        execute_values(cur, """INSERT INTO preclin.unii_substance (unii, display_name, substance_type, ingredient_type,
                                 inn_id, usan_id, rxcui, pubchem_cid, inchikey, source_release_id) VALUES %s
            ON CONFLICT (unii) DO UPDATE SET display_name = EXCLUDED.display_name,
              substance_type = EXCLUDED.substance_type, ingredient_type = EXCLUDED.ingredient_type,
              inn_id = EXCLUDED.inn_id, usan_id = EXCLUDED.usan_id, rxcui = EXCLUDED.rxcui,
              pubchem_cid = EXCLUDED.pubchem_cid, inchikey = EXCLUDED.inchikey,
              source_release_id = EXCLUDED.source_release_id""",
                       [(*s, release) for s in substances.values()], page_size=5000)
        execute_values(cur, "INSERT INTO preclin.unii_name (unii, name, name_type, name_key) VALUES %s",
                       [(*k, v) for k, v in name_rows.items()], page_size=10000)
        execute_values(cur, "INSERT INTO preclin.unii_parent (unii, parent_unii) VALUES %s", sorted(parent_rows),
                       page_size=10000)
        conn.commit()
    print(f"UNII {RELEASE}: substances={len(substances)} names={len(name_rows)} parents={len(parent_rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("load").set_defaults(fn=load)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
