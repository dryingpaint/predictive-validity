"""DepMap CRISPR inferred common-essential genes -> preclin.depmap_common_essential.

    python -m pipeline.depmap load

DepMap's own list of genes essential in most cell lines, from the Chronos
gene-effect screens of RELEASE, read from the release's figshare record (the
DepMap portal blocks scripted downloads). Each row is "SYMBOL (Entrez id)";
genes are keyed by Entrez id and joined to Ensembl through preclin.hgnc_gene.
Sections 2 and 3 use it as the pan-essential target flag.
"""
from __future__ import annotations

import argparse
import csv
import os
import re

import requests
from psycopg2.extras import execute_values

from pipeline import llm

RELEASE = "DepMap Public 24Q4"
ARTICLE = "https://api.figshare.com/v2/articles/27993248"
FILE = "CRISPRInferredCommonEssentials.csv"
CACHE = os.path.join(llm.REPO, ".cache", "depmap", RELEASE.replace(" ", "_"))


def load(_args) -> None:
    path = os.path.join(CACHE, FILE)
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        files = requests.get(f"{ARTICLE}/files", params={"page_size": 100}, timeout=60).json()
        url = next(f["download_url"] for f in files if f["name"] == FILE)
        r = requests.get(url, timeout=300)
        r.raise_for_status()
        open(path, "wb").write(r.content)
    with open(path, encoding="utf-8") as f:
        genes = [re.fullmatch(r"(\S+) \((\d+)\)", row[0]).groups() for row in list(csv.reader(f))[1:] if row]
    with llm.connect() as conn, conn.cursor() as cur:
        rid = llm.register_release(cur, "depmap_common_essentials", RELEASE, ARTICLE, llm.sha256_file(path),
                                   {"file": FILE, "n_genes": len(genes)})
        cur.execute("DELETE FROM preclin.depmap_common_essential")
        execute_values(cur, """INSERT INTO preclin.depmap_common_essential (entrez_id, symbol, source_release_id)
                               VALUES %s""", [(int(e), s, rid) for s, e in genes])
        conn.commit()
    print(f"{RELEASE}: common essentials={len(genes)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("load").set_defaults(fn=load)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
