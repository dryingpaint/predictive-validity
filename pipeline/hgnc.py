"""HGNC approved human genes -> preclin.hgnc_gene.

    python -m pipeline.hgnc load

Downloads HGNC's complete set once into .cache/hgnc, named by the file's
Last-Modified date, which is the release recorded in
preclin.evidence_source_release; later loads read the newest cached copy.
Keeps approved genes with Entrez, Ensembl and UniProt identifiers and their
previous and alias symbols. pipeline.targets resolves the symbols an LLM names
through this table, and pipeline.chembl and pipeline.depmap map their genes
through it.
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
from email.utils import parsedate_to_datetime

import requests
from psycopg2.extras import execute_values

from pipeline import llm

URL = "https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt"
CACHE = os.path.join(llm.REPO, ".cache", "hgnc")


def fetch() -> str:
    os.makedirs(CACHE, exist_ok=True)
    r = requests.get(URL, timeout=600)
    r.raise_for_status()
    day = parsedate_to_datetime(r.headers["Last-Modified"]).date().isoformat()
    path = os.path.join(CACHE, f"hgnc_complete_set_{day}.txt")
    if not os.path.exists(path):
        open(path, "wb").write(r.content)
    return path


def split(value: str) -> list[str]:
    return [v for v in value.strip('"').split("|") if v]


def load(_args) -> None:
    cached = sorted(glob.glob(os.path.join(CACHE, "hgnc_complete_set_*.txt")))
    path = cached[-1] if cached else fetch()
    release = os.path.basename(path)[len("hgnc_complete_set_"):-len(".txt")]
    with open(path, encoding="utf-8") as f:
        genes = [g for g in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE) if g["status"] == "Approved"]
    rows = [(g["hgnc_id"], g["symbol"], g["name"], g["locus_group"], int(g["entrez_id"]) if g["entrez_id"] else None,
             g["ensembl_gene_id"] or None, split(g["uniprot_ids"]), split(g["prev_symbol"]), split(g["alias_symbol"]))
            for g in genes]
    with llm.connect() as conn, conn.cursor() as cur:
        rid = llm.register_release(cur, "hgnc_complete_set", release, URL, llm.sha256_file(path),
                                   {"n_genes": len(rows)})
        cur.execute("DELETE FROM preclin.hgnc_gene")
        execute_values(cur, """INSERT INTO preclin.hgnc_gene (hgnc_id, symbol, name, locus_group, entrez_id,
                                 ensembl_id, uniprot_ids, prev_symbols, alias_symbols, source_release_id) VALUES %s""",
                       [(*r, rid) for r in rows], page_size=5000)
        conn.commit()
    print(f"HGNC {release}: genes={len(rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("load").set_defaults(fn=load)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
