"""DepMap common-essential genes per year, and cancer cell-line dependency screens published before 2019.

    python -m pipeline.depmap load           # common-essential lists -> preclin.depmap_common_essential
    python -m pipeline.depmap dependencies   # screened lines and their dependencies -> preclin.cell_line,
                                             # preclin.cell_screen, preclin.cell_dependency
    python -m pipeline.depmap lineages       # LLM: each line's lineage -> its cancer's MONDO term

DepMap's own list of genes essential in most cell lines, from the last public release of each year
(RELEASES), read from each release's figshare record (the DepMap portal blocks scripted downloads).
DepMap first published an inferred list in 19Q2, so no list covers a year before 2019. The list's
file and its screens changed over the years: Achilles screens alone through 20Q4, Achilles and
Project Score together from 21Q4. Each row is "SYMBOL (Entrez id)"; genes are keyed by Entrez id
and joined to Ensembl through preclin.hgnc_gene. Sections 2 and 3 flag a target pan-essential when
it is on the latest list from before the program entered the phase.

Dependency screens (the 2026-11-04 comprehensiveness amendment, report/translation_plan.md): DEMETER2
combined RNAi scores of the Achilles, Project DRIVE and Marcotte screens, and Avana CRISPR scored by
CERES. A line's DEMETER2 scores are dated by the earliest source paper of the screens it was in
(SCREEN_YEARS; Achilles lines in the 216-line Achilles v2.4 release take 2014). Avana lines are dated
2017 when Meyers et al. 2017 screened them (their scores from that paper) and 2018 when DepMap 18Q4
first released them (their 18Q4 scores). Only scores at or below DEPENDENT are stored. Lineages are
mapped to MONDO by an LLM choosing among MONDO candidates, as pipeline.indications maps conditions.
"""
from __future__ import annotations

import argparse
import csv
import os
import re

import pandas as pd
import requests
from psycopg2.extras import execute_values

from pipeline import llm
from pipeline.indications import N_CANDIDATES, MondoIndex

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

DEPENDENT = -0.5  # gene effect at or below which a line depends on a gene (the amendment's threshold)
# Source paper of each screen and the year it was published (verified against Europe PMC).
SCREEN_YEARS = {
    "achilles_v2.4": (2014, "Cowley et al. 2014 Sci Data, doi:10.1038/sdata.2014.35"),
    "achilles": (2017, "Tsherniak et al. 2017 Cell, doi:10.1016/j.cell.2017.06.010"),
    "drive": (2017, "McDonald et al. 2017 Cell, doi:10.1016/j.cell.2017.07.005"),
    "marcotte": (2016, "Marcotte et al. 2016 Cell, doi:10.1016/j.cell.2015.11.062"),
    "avana_2017": (2017, "Meyers et al. 2017 Nat Genet, doi:10.1038/ng.3984"),
    "avana_18q4": (2018, "DepMap Achilles 18Q4 public, figshare 7270880"),
}
# dataset -> (release, figshare article, files read)
DEPENDENCY_FILES = {
    "demeter2": ("DEMETER2 combined RNAi 19Q3", 9170975, ("sample_info.csv", "gene_effect.csv")),
    "achilles_v2.4": ("Achilles v2.4.3", 1019873, ("Achilles_QC_v2.4.3.rnai.Gs.gct",)),  # its 216 lines
    "avana_2017": ("Meyers et al. 2017", 5319388, ("avana_ceres_gene_effects.csv",)),
    "avana_18q4": ("DepMap Achilles 18Q4", 7270880, ("sample_info.csv", "gene_effect.csv")),
}


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


def gene_columns(columns) -> dict:
    """Column -> (Entrez id, symbol) for "SYMBOL (Entrez)" columns; gene families scored jointly ("A&B") are left out."""
    out = {}
    for c in columns:
        m = re.fullmatch(r"([^&\s]+) \((\d+)\)", str(c))
        if m:
            out[c] = (int(m.group(2)), m.group(1))
    return out


def dependent(scores: pd.DataFrame, genes: dict) -> list[tuple]:
    """(line, Entrez id, symbol, score) for every score at or below DEPENDENT; `scores` is lines x gene columns."""
    long = scores[list(genes)].stack()
    long = long[long <= DEPENDENT]
    return [(line, genes[col][0], genes[col][1], float(v)) for (line, col), v in long.items()]


def screened_lines(info: pd.DataFrame, achilles_v24: set[str]) -> pd.DataFrame:
    """DEMETER2 lines with the screens behind their scores and the year the earliest became public."""
    rows = []
    for depmap_id, r in info.iterrows():
        screens = [s for s, flag in (("achilles", r.in_Achilles), ("drive", r.in_DRIVE), ("marcotte", r.in_Marcotte))
                   if flag]
        years = [SCREEN_YEARS["achilles_v2.4" if s == "achilles" and r.CCLE_ID in achilles_v24 else s][0]
                 for s in screens]
        rows.append({"depmap_id": depmap_id, "screens": screens, "public_year": min(years)})
    return pd.DataFrame(rows)


def lineage_of(*parts) -> str:
    return "|".join("" if pd.isna(p) else str(p) for p in parts)


def dependencies(_args) -> None:
    paths = {k: [fetch(k, article, name) for name in names] for k, (_, article, names) in DEPENDENCY_FILES.items()}
    d2_info = pd.read_csv(paths["demeter2"][0], index_col=0)
    with open(paths["achilles_v2.4"][0]) as f:
        achilles_v24 = set(f.read().split("\n")[2].split("\t")[2:])
    q4_info = pd.read_csv(paths["avana_18q4"][0])
    lines = {i: (r.CCLE_ID, lineage_of(r.lineage, r.lineage_subtype, r.lineage_sub_subtype))
             for i, r in d2_info.iterrows()}
    for r in q4_info.itertuples():
        lines.setdefault(r.DepMap_ID, (r.CCLE_name, lineage_of(r.primary_tissue, r.secondary_tissue, r.tertiary_tissue)))
    by_name = {name: i for i, (name, _) in lines.items()}

    screens, deps = [], []
    d2 = pd.read_csv(paths["demeter2"][1], index_col=0)
    for r in screened_lines(d2_info.loc[d2_info.index.intersection(d2.index)], achilles_v24).itertuples():
        screens.append((r.depmap_id, "demeter2", r.screens, r.public_year))
    deps += [(line, "demeter2", *rest) for line, *rest in dependent(d2, gene_columns(d2.columns))]
    a17 = pd.read_csv(paths["avana_2017"][0], index_col=0).T  # the source holds genes x lines
    for name in a17.index:
        if name not in by_name:  # a line DepMap never re-released: its lineage is the tissue in its CCLE name
            by_name[name] = name
            lines[name] = (name, name.split("_", 1)[1].lower())
    a17.index = [by_name[n] for n in a17.index]
    q4 = pd.read_csv(paths["avana_18q4"][1], index_col=0)
    entrez = {sym: e for e, sym in gene_columns(q4.columns).values()}  # Meyers et al. key genes by symbol alone
    a17 = a17[[g for g in a17.columns if g in entrez]]
    a17.columns = [f"{g} ({entrez[g]})" for g in a17.columns]
    screens += [(line, "avana_2017", ["avana"], SCREEN_YEARS["avana_2017"][0]) for line in a17.index]
    deps += [(line, "avana_2017", *rest) for line, *rest in dependent(a17, gene_columns(a17.columns))]
    q4 = q4.loc[q4.index.difference(a17.index)]
    screens += [(line, "avana_18q4", ["avana"], SCREEN_YEARS["avana_18q4"][0]) for line in q4.index]
    deps += [(line, "avana_18q4", *rest) for line, *rest in dependent(q4, gene_columns(q4.columns))]

    screened = {s[0] for s in screens}
    with llm.connect() as conn, conn.cursor() as cur:
        rid = {k: llm.register_release(cur, f"depmap_dependency_{k}", release, f"{FIGSHARE}{article}",
                                       llm.sha256_file(paths[k][-1]),
                                       {"files": list(names), "papers": {s: list(v) for s, v in SCREEN_YEARS.items()},
                                        "dependent_at_or_below": DEPENDENT})
               for k, (release, article, names) in DEPENDENCY_FILES.items()}
        cur.execute("DELETE FROM preclin.cell_dependency")
        cur.execute("DELETE FROM preclin.cell_screen")
        execute_values(cur, """INSERT INTO preclin.cell_line (depmap_id, ccle_name, lineage) VALUES %s
                               ON CONFLICT (depmap_id) DO UPDATE SET ccle_name = EXCLUDED.ccle_name,
                                 lineage = EXCLUDED.lineage""",
                       [(i, name, lin) for i, (name, lin) in lines.items() if i in screened])
        execute_values(cur, """INSERT INTO preclin.cell_screen (depmap_id, dataset, screens, public_year, source_release_id)
                               VALUES %s""", [(*s, rid[s[1]]) for s in screens])
        execute_values(cur, """INSERT INTO preclin.cell_dependency (depmap_id, dataset, entrez_id, symbol, score)
                               VALUES %s""", deps, page_size=10000)
        conn.commit()
    print(f"lines={len(screened)} screens={len(screens)} dependencies={len(deps)} "
          f"by dataset={pd.Series([s[1] for s in screens]).value_counts().to_dict()}")


LINEAGE_SYSTEM = """You map the lineage annotation of a cancer cell line to the MONDO disease ontology.

The annotation gives the line's tissue or lineage, subtype and sub-subtype, joined by "|" (some parts may be empty), in the vocabulary of the Cancer Cell Line Encyclopedia (e.g. "lung|lung_NSC|lung_adenocarcinoma", "pancreas||", "haematopoietic_and_lymphoid_tissue|AML|"). In that vocabulary "upper_aerodigestive" is the head and neck (oral cavity, pharynx, larynx), and "MSI" marks a molecular subgroup, not a separate cancer. A line is a cancer cell line unless the annotation says it is immortalized normal tissue or a non-cancer cell type (e.g. "breast_immortalized", "fibroblast"), so a cancer annotation names a cancer even when it gives only a tissue: "pancreas||" is a pancreatic cancer line, "breast|TNBC|" a triple-negative breast cancer line. An immortalized or non-cancer line gets mondo_id null and match "none".

Pick the single MONDO term for the most specific cancer the annotation states, never more specific than it states ("lung||" -> lung cancer, not a subtype). Choose only from the candidate list. When no candidate names that cancer exactly, pick the narrowest candidate that contains it (its nearest parent cancer: "ovary_high_grade_serous" -> ovarian serous adenocarcinoma when MONDO has no high-grade term), and give up to three standard cancer names likely to match a MONDO label, for a second search that may find the exact term. Set mondo_id to null only when no candidate contains the cancer at all."""

LINEAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "cancer": {"type": "string"},
        "mondo_id": {"type": ["string", "null"]},
        "match": {"type": "string", "enum": ["exact", "broader", "none"]},
        "retry_queries": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["cancer", "mondo_id", "match", "retry_queries"],
    "additionalProperties": False,
}


def render_lineage(p: dict) -> str:
    cand = "\n".join(f"- {c['mondo_id']} | {c['label']} | is_a: {c['parents']} | synonyms: {', '.join(c['synonyms'])}"
                     for c in p["candidates"])
    return f"Cell-line lineage: {p['lineage']}\nExample lines: {', '.join(p['lines'])}\n\nMONDO candidates:\n{cand}"


def validate_lineage(p: dict, out: dict) -> None:
    if out["mondo_id"] and out["mondo_id"] not in {c["mondo_id"] for c in p["candidates"]}:
        raise ValueError(f"mondo_id {out['mondo_id']} not among candidates")
    if (out["match"] == "none") != (out["mondo_id"] is None):
        raise ValueError("match 'none' requires mondo_id null, and only then")


LINEAGE_TASK = llm.Task(name="cell_line_lineage_mondo", prompt_version="v3", schema_version="v2",
                        system=LINEAGE_SYSTEM, schema=LINEAGE_SCHEMA, render=render_lineage,
                        validate=validate_lineage, subject_type="cell_lineage", effort="medium", max_tokens=2000)


def lineage_queries(lineage: str) -> list[str]:
    """Retrieval queries for a lineage: each annotated part in words, and the most specific part as a cancer."""
    parts = [p.replace("_", " ") for p in lineage.split("|") if p]
    return [*parts, f"{parts[-1]} cancer"] if parts else ["cancer"]


def lineages(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        index = MondoIndex(cur)
        cur.execute("SELECT lineage, array_agg(ccle_name ORDER BY ccle_name) FROM preclin.cell_line GROUP BY 1")
        groups = cur.fetchall()

    def candidates(queries: list[str]) -> list[dict]:
        merged = {c["mondo_id"]: c for q in index.search(queries) for c in q}
        return list(merged.values())[:3 * N_CANDIDATES]

    items = {lin: {"lineage": lin, "lines": names[:4], "candidates": candidates(lineage_queries(lin))}
             for lin, names in groups}
    final = {k: (did, d) for k, did, d in llm.decisions(llm.run(LINEAGE_TASK, items))}
    retry = {k: d for k, (_, d) in final.items() if d["match"] != "exact" and d["retry_queries"]}
    if retry:
        for k in retry:
            items[k] = {**items[k], "candidates": candidates(lineage_queries(k) + retry[k]["retry_queries"])}
        for k, did, d in llm.decisions(llm.run(LINEAGE_TASK, {k: items[k] for k in retry})):
            if d["match"] == "exact" or (d["mondo_id"] and final[k][1]["match"] == "none"):
                final[k] = did, d  # a second search can only sharpen the match, never lose it
    with llm.connect() as conn, conn.cursor() as cur:
        execute_values(cur, """UPDATE preclin.cell_line c SET mondo_id = u.mondo_id, llm_decision_id = u.did
                               FROM (VALUES %s) AS u(lineage, mondo_id, did) WHERE c.lineage = u.lineage""",
                       [(k, d["mondo_id"], did) for k, (did, d) in final.items()])
        conn.commit()
    print(f"lineages={len(items)} mapped={sum(1 for _, d in final.values() if d['mondo_id'])} "
          f"broader={sum(1 for _, d in final.values() if d['match'] == 'broader')} retried={len(retry)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("load").set_defaults(fn=load)
    sub.add_parser("dependencies").set_defaults(fn=dependencies)
    sub.add_parser("lineages").set_defaults(fn=lineages)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
