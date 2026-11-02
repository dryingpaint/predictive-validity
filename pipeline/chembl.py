"""ChEMBL drug mechanisms and bioactivities -> preclin.chembl_mechanism, preclin.chembl_molecule,
preclin.chembl_activity, preclin.chembl_target, preclin.chembl_document, preclin.chembl_moiety.

    python -m pipeline.chembl load        # mechanisms, and the parent of every ChEMBL molecule
    python -m pipeline.chembl activities  # each entity's ChEMBL molecules and their measured potencies

Reads every mechanism record of the release the ChEMBL web services serve
(status.json gives the release, which names the cache directory and is recorded
in preclin.evidence_source_release), the targets they name, and the parent of
every ChEMBL molecule preclin.drug carries. A human target's genes are its
UniProt components mapped to HGNC approved symbols (preclin.hgnc_gene), so a
protein complex or multi-target record keeps all its genes. pipeline.targets
shows these records to the LLM that assigns each entity's targets.

`activities` reads the release's MySQL dump (cached under .cache/chembl/<release>, with the
columns used extracted to tab-separated files beside it). It matches every entity with a
development program to ChEMBL parent molecules (preclin.chembl_moiety: by the ChEMBL id of one
of its names, else its UNII structure, else a registered UNII name
that is the preferred name or a synonym of exactly one ChEMBL parent) and keeps, for every form of
those parents (salts, the parent itself), each activity against a human target that carries a pChEMBL value
(-log10 molar IC50, EC50, Ki, Kd, AC50 or potency, measured exactly). Rows ChEMBL flags as
doubtful (data_validity_comment other than "Manually validated") or as potential duplicates
are left out and counted in the release metadata. Each activity keeps its assay type (B binding, F functional), its BAO
format (cell-based, single protein, ...), its target (whose genes come from its UniProt
components, as for mechanisms) and its document, dated by the year ChEMBL gives it (a paper's
publication year, a patent's year, a deposited dataset's deposition year).
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import re
import tarfile
import time

import pandas as pd
import requests
from psycopg2.extras import execute_values

from pipeline import llm
from pipeline.evidence_dates import download

API = "https://www.ebi.ac.uk/chembl/api/data"
PAGE = 1000
IDS_PER_CALL = 50
# Activities come from the release's MySQL dump: the web service answers an activity query in about 45 s a
# page and fails for hours at a time.
DUMP_RELEASE = "37"
DUMP_URL = f"https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_{DUMP_RELEASE}/chembl_{DUMP_RELEASE}_mysql.tar.gz"
DUMP_COLUMNS = {
    "activities": ["activity_id", "assay_id", "doc_id", "molregno", "standard_type", "pchembl_value",
                   "data_validity_comment", "potential_duplicate"],
    "assays": ["assay_id", "chembl_id", "assay_type", "bao_format", "tid"],
    "bioassay_ontology": ["bao_id", "label"],
    "component_sequences": ["component_id", "accession"],
    "docs": ["doc_id", "chembl_id", "year", "journal", "src_id"],
    "compound_structures": ["molregno", "standard_inchi_key"],
    "molecule_dictionary": ["molregno", "chembl_id", "pref_name"],
    "molecule_synonyms": ["molregno", "synonyms"],
    "molecule_hierarchy": ["molregno", "parent_molregno"],
    "target_components": ["tid", "component_id"],
    "target_dictionary": ["tid", "chembl_id", "pref_name", "target_type", "organism"],
}
TOKEN = re.compile(r"\(|\)|NULL|'(?:[^'\\]|\\.)*'|[^,()']+")  # an INSERT's parentheses, NULLs, strings and numbers
ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "0": "\0", "Z": "\x1a"}
VALID_COMMENTS = {"Manually validated"}  # the one data_validity_comment that does not flag a doubtful value


def get(path: str, **params) -> dict:
    for attempt in range(6):
        try:
            r = requests.get(f"{API}/{path}", params=params, timeout=180)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == 5:
                raise
            time.sleep(15 * (attempt + 1))


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


def unescape(token: str) -> str | None:
    if token == "NULL":
        return None
    if token.startswith("'"):
        return re.sub(r"\\(.)", lambda m: ESCAPES.get(m.group(1), m.group(1)), token[1:-1])
    return token


def rows(insert: str):
    """The value tuples of one INSERT statement, which may hold many rows."""
    row = []
    for token in TOKEN.findall(insert, insert.index(" VALUES ") + 8):
        if token == "(":
            row = []
        elif token == ")":
            yield row
        elif token != ";\n" and token != ";":
            row.append(unescape(token))


def extract(dump: str, out: str) -> None:
    """The DUMP_COLUMNS of each of their tables, read from the release's MySQL dump (one INSERT per row) into
    tab-separated files under `out`; activities only where they carry a pChEMBL value."""
    tmp = out + ".part"
    os.makedirs(tmp, exist_ok=True)
    files, handles, columns, table = {}, [], {}, None
    with tarfile.open(dump, "r|gz") as tar:
        for member in tar:
            if not member.name.endswith(".dmp"):
                continue
            for line in tar.extractfile(member):
                if line.startswith(b"INSERT INTO `"):
                    name = line[13:line.index(b"`", 13)].decode()
                    if name not in DUMP_COLUMNS:
                        continue
                    if name not in files:
                        handles.append(open(os.path.join(tmp, f"{name}.tsv"), "w", newline=""))
                        files[name] = csv.writer(handles[-1], delimiter="\t")
                        files[name].writerow(DUMP_COLUMNS[name])
                    keep = [columns[name].index(c) for c in DUMP_COLUMNS[name]]
                    pchembl = columns[name].index("pchembl_value") if name == "activities" else None
                    files[name].writerows([row[i] for i in keep] for row in rows(line.decode("utf-8", errors="replace"))
                                          if pchembl is None or row[pchembl] is not None)
                elif line.startswith(b"CREATE TABLE"):
                    table = line.decode().split("`")[1]
                    columns[table] = []
                elif line.startswith(b"  `") and table in DUMP_COLUMNS:
                    columns[table].append(line.decode().split("`")[1])
    for h in handles:
        h.close()
    os.rename(tmp, out)


def read(out: str, table: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(out, f"{table}.tsv"), sep="\t", keep_default_na=False, na_values=[""],
                       dtype=str, quoting=csv.QUOTE_MINIMAL)


def name_key(name: str) -> str:
    """A name compared ignoring case and punctuation, as preclin.unii_name.name_key and moiety_key are."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def entity_parents(cur, out: str, parent_of: pd.Series) -> list[tuple[int, str, str]]:
    """(moiety_id, parent_chembl_id, basis) for every entity with a development program, by the first basis that
    matches it (preclin.chembl_moiety.basis)."""
    cur.execute("""SELECT DISTINCT dm.moiety_id, mol.parent_chembl_id
                   FROM preclin.drug_moiety dm JOIN preclin.drug d USING (drug_id)
                   JOIN preclin.chembl_molecule mol ON mol.molecule_chembl_id = d.chembl_id
                   WHERE dm.moiety_id IN (SELECT moiety_id FROM preclin.dev_program)""")
    by_id = cur.fetchall()
    cur.execute("""SELECT m.moiety_id, u.inchikey FROM preclin.moiety m JOIN preclin.unii_substance u USING (unii)
                   WHERE u.inchikey IS NOT NULL AND m.moiety_id IN (SELECT moiety_id FROM preclin.dev_program)""")
    inchikeys = cur.fetchall()
    cur.execute("""SELECT m.moiety_id, un.name FROM preclin.moiety m JOIN preclin.unii_name un USING (unii)
                   WHERE un.name_type IN ('of', 'cn', 'cd') AND m.moiety_id IN (SELECT moiety_id FROM preclin.dev_program)""")
    names = cur.fetchall()
    structures = read(out, "compound_structures").dropna()
    by_inchikey = structures.assign(parent=structures.molregno.map(parent_of)).groupby("standard_inchi_key").parent \
        .agg(lambda p: sorted(set(p)))
    molecules = read(out, "molecule_dictionary")
    synonyms = pd.concat([molecules[["molregno", "pref_name"]].rename(columns={"pref_name": "name"}),
                          read(out, "molecule_synonyms").rename(columns={"synonyms": "name"})]).dropna()
    synonyms["key"] = synonyms.name.map(name_key)
    synonyms["parent"] = synonyms.molregno.map(parent_of)
    by_name = synonyms[synonyms.key != ""].groupby("key").parent.agg(lambda p: sorted(set(p)))
    by_name = by_name[by_name.map(len) == 1].map(lambda p: p[0])  # a name two parents share decides nothing

    found: dict[int, set[tuple[str, str]]] = {}
    for m, parent in by_id:
        found.setdefault(m, set()).add((parent, "drug_chembl_id"))
    for m, key in inchikeys:
        if m not in found and key in by_inchikey.index:
            found[m] = {(p, "inchikey") for p in by_inchikey[key]}
    named: dict[int, set[tuple[str, str]]] = {}
    for m, n in names:
        k = name_key(n)
        if m not in found and k in by_name.index:
            named.setdefault(m, set()).add((by_name[k], "name"))
    return sorted((m, p, b) for m, pairs in {**found, **named}.items() for p, b in pairs)


def activities(_args) -> None:
    cache = os.path.join(llm.REPO, ".cache", "chembl", f"ChEMBL_{DUMP_RELEASE}")
    dump, out = os.path.join(cache, os.path.basename(DUMP_URL)), os.path.join(cache, "extract")
    os.makedirs(cache, exist_ok=True)
    download(DUMP_URL, dump)
    if not os.path.exists(out):
        extract(dump, out)
    molecules = read(out, "molecule_dictionary").set_index("molregno").chembl_id
    hierarchy = read(out, "molecule_hierarchy").set_index("molregno").parent_molregno
    parent_of = molecules.index.to_series().map(hierarchy).fillna(molecules.index.to_series()).map(molecules)
    with llm.connect() as conn, conn.cursor() as cur:
        matches = entity_parents(cur, out, parent_of)
        cur.execute("SELECT u, symbol FROM preclin.hgnc_gene, unnest(uniprot_ids) u")
        by_uniprot = dict(cur.fetchall())
    parents = {p for _, p, _ in matches}
    acts = read(out, "activities")
    acts["molecule_chembl_id"] = acts.molregno.map(molecules)
    acts["parent_chembl_id"] = acts.molregno.map(parent_of)
    acts = acts[acts.parent_chembl_id.isin(parents)]
    assays = read(out, "assays").set_index("assay_id")
    targets = read(out, "target_dictionary").set_index("tid")
    acts = acts.join(assays.rename(columns={"chembl_id": "assay_chembl_id"}), on="assay_id")
    acts = acts.join(targets.rename(columns={"chembl_id": "target_chembl_id"}), on="tid")
    read_rows = acts[acts.organism == "Homo sapiens"]
    flagged = ~read_rows.data_validity_comment.isin(VALID_COMMENTS) & read_rows.data_validity_comment.notna()
    duplicate = read_rows.potential_duplicate.eq("1")
    kept = read_rows[~flagged & ~duplicate].copy()
    kept["bao_label"] = kept.bao_format.map(read(out, "bioassay_ontology").set_index("bao_id").label)
    docs = read(out, "docs").set_index("doc_id").loc[kept.doc_id.unique()]
    kept["document_chembl_id"] = kept.doc_id.map(docs.chembl_id)

    accession = read(out, "component_sequences").set_index("component_id").accession
    components = read(out, "target_components")
    components["symbol"] = components.component_id.map(accession).map(by_uniprot)
    symbols = components.dropna(subset=["symbol"]).groupby("tid").symbol.agg(lambda s: sorted(set(s)))
    used = targets.loc[kept.tid.unique()]
    none = lambda v: None if pd.isna(v) else v

    with open(dump, "rb") as f:
        sha = hashlib.file_digest(f, "sha256").hexdigest()
    with llm.connect() as conn, conn.cursor() as cur:
        rid = llm.register_release(cur, "chembl_activity", f"ChEMBL_{DUMP_RELEASE}", DUMP_URL, sha,
                                   {"n_entities": len({m for m, _, _ in matches}),
                                    "n_entities_by_basis": {b: len({m for m, _, x in matches if x == b})
                                                            for b in ("drug_chembl_id", "inchikey", "name")},
                                    "n_parents": len(parents), "n_parents_measured": int(kept.parent_chembl_id.nunique()),
                                    "n_activities_read": len(read_rows), "n_activities": len(kept),
                                    "dropped": {"validity_comment": int(flagged.sum()),
                                                "potential_duplicate": int((duplicate & ~flagged).sum())},
                                    "n_targets": len(used), "n_documents": len(docs),
                                    "n_documents_undated": int(docs.year.isna().sum())})
        cur.execute("DELETE FROM preclin.chembl_activity")
        cur.execute("DELETE FROM preclin.chembl_target")
        cur.execute("DELETE FROM preclin.chembl_document")
        cur.execute("DELETE FROM preclin.chembl_moiety")
        execute_values(cur, """INSERT INTO preclin.chembl_moiety (moiety_id, parent_chembl_id, basis, source_release_id)
                                 VALUES %s""", [(*m, rid) for m in matches], page_size=5000)
        execute_values(cur, """INSERT INTO preclin.chembl_target (target_chembl_id, pref_name, target_type, organism,
                                 symbols, source_release_id) VALUES %s""",
                       [(t.chembl_id, none(t.pref_name), t.target_type, none(t.organism), symbols.get(tid, []), rid)
                        for tid, t in used.iterrows()], page_size=5000)
        execute_values(cur, """INSERT INTO preclin.chembl_document (document_chembl_id, year, journal, src_id,
                                 source_release_id) VALUES %s""",
                       [(d.chembl_id, None if pd.isna(d.year) else int(d.year), none(d.journal), int(d.src_id), rid)
                        for d in docs.itertuples()], page_size=5000)
        execute_values(cur, """INSERT INTO preclin.chembl_activity (activity_id, molecule_chembl_id, parent_chembl_id,
                                 target_chembl_id, standard_type, pchembl_value, assay_chembl_id, assay_type,
                                 bao_format, bao_label, document_chembl_id, source_release_id) VALUES %s""",
                       [(int(a.activity_id), a.molecule_chembl_id, a.parent_chembl_id, a.target_chembl_id,
                         a.standard_type, a.pchembl_value, a.assay_chembl_id, a.assay_type, none(a.bao_format),
                         none(a.bao_label), a.document_chembl_id, rid) for a in kept.itertuples()], page_size=5000)
        conn.commit()
    print(f"ChEMBL_{DUMP_RELEASE}: entities={len({m for m, _, _ in matches})} parents={len(parents)} measured={kept.parent_chembl_id.nunique()} "
          f"activities={len(kept)} of {len(read_rows)} on human targets (flagged {int(flagged.sum())}, "
          f"duplicates {int((duplicate & ~flagged).sum())}) targets={len(used)} documents={len(docs)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("load").set_defaults(fn=load)
    sub.add_parser("activities").set_defaults(fn=activities)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
