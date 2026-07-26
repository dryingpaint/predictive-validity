#!/usr/bin/env python3
"""
Download helper for the STRUCTURAL VERSIONED RE-PULL (PR #9 top follow-up).

Pulls DATED / versioned snapshots of the three structural-evidence sources Melissa
uses in `v_target_evidence_wide`, and reduces each release to a LEAN per-gene summary
(one small CSV per release). Raw downloads are streamed / read remotely and never kept
on disk (disk-discipline mandate) -- only the derived per-gene tables are written.

Sources (see STRUCTURAL_VERSIONED_REPULL.md for the availability/size assessment):

  OPEN TARGETS (ot_overall_max / ot_genetic_max / ot_animal_model_max)
    Method (identical for every release): per Ensembl gene, MAX over diseases of
      - association*overall_indirect.score            -> ot_overall_max
      - association*datatype_indirect (genetic_association) -> ot_genetic_max
      - association*datatype_indirect (animal_model)        -> ot_animal_model_max
    Three on-disk layouts across the release timeline:
      * Era A (<=20.11): single "NN.NN_association_data.json.gz" (LEGACY scoring scale,
        pre harmonic-sum rewrite of 21.02 -- NOT numerically comparable to Era B; used
        for coverage/robustness with prevalence-matched thresholds, see analysis).
      * Era B1 (21.02-24.09): parquet under output/etl/parquet/associationBy*Indirect/
        (camelCase).  Read remotely with duckdb httpfs (column-projected, no local copy).
      * Era B2 (>=25.03): parquet under output/association_by_*_indirect/ (snake_case).

  IMPC (impc_n_phenotypes)
    Dated data releases DR-12 (2020-10) .. DR-21 (2024-05). File
    results/phenotypeHitsPerGene.csv.gz gives mouse-gene -> "# Phenotype Hits".
    Mouse symbol -> human by upper-casing (1:1-ortholog approximation; documented).

  DEPMAP (depmap_pan_essential)
    figshare "DepMap Public" releases 2019-2024. Small common-essentials gene list
    per release (Achilles_common_essentials.csv / CRISPRInferredCommonEssentials.csv).
    depmap_n_dep_lineages / depmap_mean_effect need the full multi-hundred-MB Chronos
    matrix and are OUT OF SCOPE here (documented) -- pan-essentiality is the dim the
    v_relative_success view thresholds on and is biologically stable across releases.

Usage:
    python3 analyses/fetch_versioned_structural.py            # all sources
    python3 analyses/fetch_versioned_structural.py ot         # one source: ot|impc|depmap
Outputs (committed, lean):  data/versioned/{ot,impc,depmap}_<release>.csv
Idempotent: skips a release whose output CSV already exists.
"""
from __future__ import annotations
import gzip
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "versioned")
COHORT = os.path.join(OUT, "cohort_genes.csv")
UA = {"User-Agent": "capable-pv-structural-repull/1.0"}

# ----------------------------------------------------------------------------
# Release registries.  Dates = the release date used for pinning (YYYY-MM-01 for OT
# YY.MM tags; figshare published_date for DepMap; FTP Last-Modified for IMPC).
# ----------------------------------------------------------------------------
OT_RELEASES = [
    # tag,     date,         era ('A' legacy json | 'B1' camel parquet | 'B2' snake parquet)
    ("18.06", "2018-06-01", "A"),
    ("19.06", "2019-06-01", "A"),
    ("20.06", "2020-06-01", "A"),
    ("21.06", "2021-06-01", "B1"),
    ("22.06", "2022-06-01", "B1"),
    ("23.06", "2023-06-01", "B1"),
    ("24.06", "2024-06-01", "B1"),
    ("25.06", "2025-06-01", "B2"),  # newest full release = "present-day (self-consistent)"
]

IMPC_RELEASES = [
    ("12.0", "2020-10-06"),
    ("14.0", "2021-05-10"),
    ("16.0", "2022-03-24"),
    ("18.0", "2022-11-28"),
    ("19.0", "2023-05-09"),
    ("20.0", "2023-11-21"),
    ("21.0", "2024-05-07"),
]

# figshare article id per DepMap Public release (from api.figshare.com search)
DEPMAP_RELEASES = [
    ("20Q1", "2020-05-07", 11791698),
    ("21Q2", "2021-05-05", 14541774),
    ("22Q2", "2022-05-05", 19700056),
    ("23Q2", "2023-06-02", 22765112),
    ("24Q2", "2024-05-23", 25880521),
]

OT_FTP = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform"
IMPC_FTP = "https://ftp.ebi.ac.uk/pub/databases/impc/all-data-releases"


def _cohort():
    g = pd.read_csv(COHORT)
    ensembl = set(g.ensembl_id.dropna())
    symbols = set(g.symbol.dropna())
    return g, ensembl, symbols


def _list_parts(url_dir: str):
    html = urllib.request.urlopen(
        urllib.request.Request(url_dir, headers=UA), timeout=60
    ).read().decode()
    return [url_dir + p for p in re.findall(r'href="(part-[^"]+\.parquet)"', html)]


# ----------------------------------------------------------------------------
# Open Targets
# ----------------------------------------------------------------------------
def _ot_parquet_paths(tag: str, era: str):
    base = f"{OT_FTP}/{tag}/output/"
    if era == "B1":
        p = base + "etl/parquet/associationByOverallIndirect/"
        d = base + "etl/parquet/associationByDatatypeIndirect/"
    else:  # B2
        p = base + "association_by_overall_indirect/"
        d = base + "association_by_datatype_indirect/"
    return p, d


def fetch_ot_parquet(tag, era, ensembl, con):
    ov_dir, dt_dir = _ot_parquet_paths(tag, era)
    gl = "','".join(sorted(ensembl))
    ov_parts = _list_parts(ov_dir)
    ov = con.execute(
        f"SELECT targetId ensembl_id, max(score) ot_overall_max "
        f"FROM read_parquet({ov_parts}) WHERE targetId IN ('{gl}') GROUP BY targetId"
    ).df()
    dt_parts = _list_parts(dt_dir)
    dt = con.execute(
        f"SELECT targetId ensembl_id, datatypeId, max(score) s "
        f"FROM read_parquet({dt_parts}) "
        f"WHERE targetId IN ('{gl}') AND datatypeId IN ('genetic_association','animal_model') "
        f"GROUP BY targetId, datatypeId"
    ).df()
    gen = dt[dt.datatypeId == "genetic_association"][["ensembl_id", "s"]].rename(
        columns={"s": "ot_genetic_max"})
    ani = dt[dt.datatypeId == "animal_model"][["ensembl_id", "s"]].rename(
        columns={"s": "ot_animal_model_max"})
    out = ov.merge(gen, on="ensembl_id", how="outer").merge(ani, on="ensembl_id", how="outer")
    return out


def fetch_ot_json(tag, ensembl):
    """Era A legacy single-JSON. Stream + aggregate max per cohort gene; nothing kept."""
    # file lives under output/ for 19.x/20.x but at the release root for 18.x
    r = None
    for url in (f"{OT_FTP}/{tag}/output/{tag}_association_data.json.gz",
                f"{OT_FTP}/{tag}/{tag}_association_data.json.gz"):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120)
            break
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
    if r is None:
        raise RuntimeError(f"no association_data.json.gz found for {tag}")
    gz = gzip.GzipFile(fileobj=r)
    acc = {}  # ensembl -> [overall, genetic, animal]
    n = 0
    for raw in gz:
        n += 1
        try:
            rec = json.loads(raw)
        except Exception:
            continue
        tid = rec.get("target", {}).get("id")
        if tid not in ensembl:
            continue
        sc = rec.get("association_score", {})
        ov = float(sc.get("overall", 0) or 0)
        dts = sc.get("datatypes", {})
        gen = float(dts.get("genetic_association", 0) or 0)
        ani = float(dts.get("animal_model", 0) or 0)
        cur = acc.get(tid)
        if cur is None:
            acc[tid] = [ov, gen, ani]
        else:
            cur[0] = max(cur[0], ov); cur[1] = max(cur[1], gen); cur[2] = max(cur[2], ani)
    r.close()
    rows = [{"ensembl_id": k, "ot_overall_max": v[0], "ot_genetic_max": v[1],
             "ot_animal_model_max": v[2]} for k, v in acc.items()]
    print(f"    (streamed {n} assoc records)")
    return pd.DataFrame(rows)


def fetch_ot():
    import duckdb
    _, ensembl, _ = _cohort()
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; SET enable_progress_bar=false;")
    for tag, date, era in OT_RELEASES:
        dst = os.path.join(OUT, f"ot_{tag}.csv")
        if os.path.exists(dst):
            print(f"  OT {tag}: exists, skip"); continue
        print(f"  OT {tag} (era {era}, {date}) ...")
        t = time.time()
        df = fetch_ot_json(tag, ensembl) if era == "A" else fetch_ot_parquet(tag, era, ensembl, con)
        df["release"] = tag; df["release_date"] = date; df["era"] = era
        df.to_csv(dst, index=False)
        print(f"    wrote {dst}  ({len(df)} genes, {time.time()-t:.0f}s)")


# ----------------------------------------------------------------------------
# IMPC
# ----------------------------------------------------------------------------
def fetch_impc():
    _, _, symbols = _cohort()
    for tag, date in IMPC_RELEASES:
        dst = os.path.join(OUT, f"impc_{tag}.csv")
        if os.path.exists(dst):
            print(f"  IMPC {tag}: exists, skip"); continue
        url = f"{IMPC_FTP}/release-{tag}/results/phenotypeHitsPerGene.csv.gz"
        print(f"  IMPC release-{tag} ({date}) ...")
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
        df = pd.read_csv(io.BytesIO(raw), compression="gzip")
        df = df.rename(columns={"Gene Symbol": "mouse_symbol", "# Phenotype Hits": "n_phenotypes"})
        df["symbol"] = df.mouse_symbol.str.upper()  # mouse->human 1:1 ortholog approx
        df = df[df.symbol.isin(symbols)][["symbol", "n_phenotypes"]].copy()
        df = df.groupby("symbol", as_index=False).n_phenotypes.max()
        df["release"] = tag; df["release_date"] = date
        df.to_csv(dst, index=False)
        print(f"    wrote {dst}  ({len(df)} cohort genes)")


# ----------------------------------------------------------------------------
# DepMap
# ----------------------------------------------------------------------------
def _figshare_files(aid):
    url = f"https://api.figshare.com/v2/articles/{aid}/files"
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))


def fetch_depmap():
    _, _, symbols = _cohort()
    for tag, date, aid in DEPMAP_RELEASES:
        dst = os.path.join(OUT, f"depmap_{tag}.csv")
        if os.path.exists(dst):
            print(f"  DepMap {tag}: exists, skip"); continue
        files = _figshare_files(aid)
        pick = None
        for want in ("CRISPRInferredCommonEssentials.csv", "Achilles_common_essentials.csv"):
            for f in files:
                if f["name"] == want:
                    pick = f; break
            if pick:
                break
        if not pick:
            print(f"  DepMap {tag}: no common-essentials file, skip"); continue
        print(f"  DepMap {tag} ({date}) <- {pick['name']} ...")
        raw = urllib.request.urlopen(
            urllib.request.Request(pick["download_url"], headers=UA), timeout=120).read()
        s = pd.read_csv(io.BytesIO(raw))
        col = s.columns[0]
        genes = s[col].astype(str).str.replace(r"\s*\(\d+\)$", "", regex=True).str.strip()
        df = pd.DataFrame({"symbol": genes})
        df = df[df.symbol.isin(symbols)].drop_duplicates()
        df["pan_essential"] = 1
        df["release"] = tag; df["release_date"] = date
        df.to_csv(dst, index=False)
        print(f"    wrote {dst}  ({len(df)} cohort common-essential genes)")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "ot"):
        fetch_ot()
    if which in ("all", "impc"):
        fetch_impc()
    if which in ("all", "depmap"):
        fetch_depmap()
    print("done.")
