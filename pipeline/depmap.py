"""DepMap CRISPR inferred common-essential genes, one list per year -> preclin.depmap_common_essential.

    python -m pipeline.depmap load

DepMap's own list of genes essential in most cell lines, from the last public release of each year
(RELEASES), read from each release's figshare record (the DepMap portal blocks scripted downloads).
DepMap first published an inferred list in 19Q2, so no list covers a year before 2019. The list's
file and its screens changed over the years: Achilles screens alone through 20Q4, Achilles and
Project Score together from 21Q4. Each row is "SYMBOL (Entrez id)"; genes are keyed by Entrez id
and joined to Ensembl through preclin.hgnc_gene. Sections 2 and 3 flag a target pan-essential when
it is on the latest list from before the program entered the phase.
"""
from __future__ import annotations

import argparse
import csv
import os
import re

import requests
from psycopg2.extras import execute_values

from pipeline import llm

FIGSHARE = "https://api.figshare.com/v2/articles/"
# (release, year, figshare article, file): the last public release of each year with an inferred list
RELEASES = (
    ("DepMap Public 19Q4", 2019, 11384241, "Achilles_common_essentials.csv"),
    ("DepMap Public 20Q4", 2020, 13237076, "Achilles_common_essentials.csv"),
    ("DepMap Public 21Q4", 2021, 16924132, "CRISPR_common_essentials.csv"),
    ("DepMap Public 22Q4", 2022, 21637199, "CRISPRInferredCommonEssentials.csv"),
    ("DepMap Public 23Q4", 2023, 24667905, "CRISPRInferredCommonEssentials.csv"),
    ("DepMap Public 24Q4", 2024, 27993248, "CRISPRInferredCommonEssentials.csv"),
)
CACHE = os.path.join(llm.REPO, ".cache", "depmap")


def fetch(release: str, article: int, name: str) -> str:
    path = os.path.join(CACHE, release.replace(" ", "_"), name)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        files = requests.get(f"{FIGSHARE}{article}/files", params={"page_size": 200}, timeout=60).json()
        r = requests.get(next(f["download_url"] for f in files if f["name"] == name), timeout=300)
        r.raise_for_status()
        open(path, "wb").write(r.content)
    return path


def load(_args) -> None:
    rows = []
    with llm.connect() as conn, conn.cursor() as cur:
        for release, year, article, name in RELEASES:
            path = fetch(release, article, name)
            with open(path, encoding="utf-8") as f:
                genes = [re.fullmatch(r"(\S+) \((\d+)\)", row[0]).groups() for row in list(csv.reader(f))[1:] if row]
            rid = llm.register_release(cur, "depmap_common_essentials", release, f"{FIGSHARE}{article}",
                                       llm.sha256_file(path), {"file": name, "n_genes": len(genes), "year": year})
            rows += [(year, int(e), s, rid) for s, e in genes]
            print(f"{release}: common essentials={len(genes)}")
        cur.execute("DELETE FROM preclin.depmap_common_essential")
        execute_values(cur, """INSERT INTO preclin.depmap_common_essential (release_year, entrez_id, symbol, source_release_id)
                               VALUES %s""", rows)
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("load").set_defaults(fn=load)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
