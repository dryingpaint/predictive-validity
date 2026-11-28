"""LDSC SNP heritability, LD clumping and heritability concentration per GWAS Catalog study (issue #147).

    python -m pipeline.ldsc references        # LD scores, HapMap3 list, 1000 Genomes EUR cut to HapMap3 -> .cache/ldsc/
    python -m pipeline.ldsc check             # the ldsc (Python 3.11 venv) and plink (conda env) tools
    python -m pipeline.ldsc run GCST...       # one study: fetch, munge, h2, clump, concentration -> preclin.ldsc_run
    python -m pipeline.ldsc run-all [--retry] [--gcst-file F]   # every study preclin.disease_polygenicity names

Per study: the harmonised summary statistics are streamed from the Catalog's FTP site, cut to the HapMap3 SNPs
and the columns munge_sumstats needs (rsid, alleles, beta or log odds ratio, p), munged against the HapMap3 list
with N = cases + controls, and regressed with ldsc --h2 on the European LD scores (observed scale; the liability
conversion is done later from K, pipeline.polygenicity). The same munged SNPs are clumped with PLINK against the
1000 Genomes European panel (P <= 5e-8, r2 < 0.1 within 1 Mb): the index SNPs are the independent loci, every
index SNP in the extended MHC (chr6:25-34 Mb) counted once. The heritability concentration is the share of
observed-scale h2 carried by the ten index SNPs with the largest z^2, each SNP's h2 taken as (z^2 - 1) / N
(Melissa's registered sensitivity 3). One study's files are on disk at a time and are deleted when its row is
written; a rerun skips studies with an ok row.

Tools (TOOLS): ldsc 2.0.1, the Python 3 port of bulik/ldsc, in its own Python 3.11 venv (it pins nose, which
does not import on 3.12, and reads with pandas < 3); PLINK 1.90b7.7 from bioconda. References (REFERENCES): eur_w_ld_chr from Zenodo
8182036, w_hm3.snplist from Zenodo 7773502, 1000 Genomes Phase 3 EUR from Zenodo 6614170.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import tarfile
import time
import traceback
from io import StringIO

import numpy as np
import pandas as pd
from psycopg2.extras import Json
from scipy.stats import norm

from pipeline import llm
from pipeline.gwas_catalog import SUMSTATS_BASE, download

REF = os.path.join(llm.REPO, ".cache", "ldsc")
WORK = os.path.join(REF, "work")
VENV = os.path.join(REF, "venv311")
PLINK = os.path.expanduser("~/miniforge3/envs/plink/bin/plink")
CONDA = os.path.expanduser("~/miniforge3/bin/conda")
TOOLS = {"ldsc": "2.0.1", "plink": "1.9.0-b.8"}   # what each binary reports
LD_REFERENCE = "eur_w_ld_chr (Zenodo 8182036); 1000G_EUR_hm3 (Zenodo 6614170 cut to HapMap3 SNPs)"
REFERENCES = {"eur_w_ld_chr.tar.gz": 8182036, "w_hm3.snplist.gz": 7773502, "1000G_EUR.bed": 6614170,
              "1000G_EUR.bim": 6614170, "1000G_EUR.fam": 6614170}
PANEL = os.path.join(REF, "1000G_EUR_hm3")
MHC = (6, 25_000_000, 34_000_000)
GWS = 5e-8
CLUMP_R2, CLUMP_KB = 0.1, 1000
TOP = 10
CHUNK = 1_000_000   # rows per chunk when a harmonised file is streamed
STREAMS = 16            # byte-range segments fetched concurrently per file: EBI throttles each connection to ~20 KB/s
FETCH_ATTEMPTS = 200    # per segment: EBI caps connections per IP near 50, so a dropped segment can wait over an hour for a slot
P_FLOOR = 1e-300    # p below the double range reads as 0 and munge would drop the SNP
LOG_HEAD, LOG_TAIL = 5_000, 15_000
# The harmonised files come in two layouts: the older one with hm_ columns, the GWAS-SSF one without the prefix
COLUMNS = {"snp": ("hm_rsid", "rsid", "variant_id"), "a1": ("hm_effect_allele", "effect_allele"),
           "a2": ("hm_other_allele", "other_allele"), "beta": ("hm_beta", "beta"), "odds": ("hm_odds_ratio", "odds_ratio", "OR", "or"),
           "p": ("p_value", "neg_log_10_p_value")}
STATUSES = ("ok", "no_effect", "fetch_failed", "munge_failed", "h2_failed", "clump_failed")


def references(_args) -> None:
    os.makedirs(REF, exist_ok=True)
    for name, record in REFERENCES.items():
        download(f"https://zenodo.org/api/records/{record}/files/{name}/content", os.path.join(REF, name))
    if not os.path.isdir(os.path.join(REF, "eur_w_ld_chr")):
        with tarfile.open(os.path.join(REF, "eur_w_ld_chr.tar.gz")) as t:
            t.extractall(REF, filter="data")
    snplist = os.path.join(REF, "w_hm3.snplist")
    if not os.path.exists(snplist):
        with gzip.open(snplist + ".gz", "rt") as f, open(snplist, "w") as out:
            out.write(f.read())
    ids = os.path.join(REF, "w_hm3.ids")
    if not os.path.exists(ids):
        pd.read_csv(snplist, sep=r"\s+").SNP.to_csv(ids, index=False, header=False)
    if not os.path.exists(PANEL + ".bed"):
        subprocess.run([PLINK, "--bfile", os.path.join(REF, "1000G_EUR"), "--extract", ids, "--make-bed", "--out", PANEL],
                       check=True, capture_output=True, text=True)
        for ext in ("bed", "bim", "fam"):
            os.remove(os.path.join(REF, f"1000G_EUR.{ext}"))
    print("ld scores:", len(os.listdir(os.path.join(REF, "eur_w_ld_chr"))), "files; hapmap3:", sum(1 for _ in open(ids)),
          "SNPs; panel:", sum(1 for _ in open(PANEL + ".bim")), "SNPs")


def ldsc_cmd(script: str) -> list[str]:
    """The command for an ldsc entry point (ldsc.py, munge_sumstats.py) in the Python 3.11 venv."""
    for name in (script, script.removesuffix(".py")):
        path = os.path.join(VENV, "bin", name)
        if os.path.exists(path):
            return [path]
    return [os.path.join(VENV, "bin", "python"), "-m", "ldsc." + script.removesuffix(".py")]


def check(_args) -> None:
    if not os.path.exists(os.path.join(VENV, "bin", "python")):
        subprocess.run(["uv", "venv", "--python", "3.11", VENV], check=True)
        subprocess.run(["uv", "pip", "install", "--python", os.path.join(VENV, "bin", "python"), f"ldsc=={TOOLS['ldsc']}",
                        "pandas<3"], check=True)  # ldsc 2.0.1 reads with delim_whitespace, removed in pandas 3
    if not os.path.exists(PLINK):
        subprocess.run([CONDA, "create", "-y", "-n", "plink", "-c", "bioconda", f"plink={TOOLS['plink']}"], check=True)
    for cmd in (ldsc_cmd("ldsc.py") + ["-h"], ldsc_cmd("munge_sumstats.py") + ["-h"], [PLINK, "--version"]):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"{cmd[0]} failed:\n{r.stdout}\n{r.stderr}")
        print(cmd[0].split("/")[-1], (r.stdout or r.stderr).strip().splitlines()[0])


def column_map(columns) -> dict[str, str | None]:
    """Which of a harmonised file's columns serve as SNP, A1, A2, beta, odds ratio and p (None when absent)."""
    cols = list(columns)
    return {k: next((c for c in names if c in cols), None) for k, names in COLUMNS.items()}


def munge_input(h: pd.DataFrame) -> pd.DataFrame | None:
    """SNP, A1, A2, BETA, P from a harmonised frame (either layout): beta, else log odds ratio; None when no row
    has an effect or the file has no SNP, allele or effect column."""
    m = column_map(h.columns)
    if not (m["snp"] and m["a1"] and m["a2"] and (m["beta"] or m["odds"])):
        return None
    beta = pd.to_numeric(h[m["beta"]], errors="coerce") if m["beta"] else pd.Series(np.nan, index=h.index)
    if m["odds"]:
        odds = pd.to_numeric(h[m["odds"]], errors="coerce")
        beta = beta.where(beta.notna(), np.log(odds.where(odds > 0)))
    p = pd.to_numeric(h[m["p"]], errors="coerce") if m["p"] else pd.Series(np.nan, index=h.index)
    if m["p"] == "neg_log_10_p_value":
        p = 10 ** -p
    p = p.clip(lower=P_FLOOR)
    out = pd.DataFrame({"SNP": h[m["snp"]], "A1": h[m["a1"]], "A2": h[m["a2"]], "BETA": beta, "P": p})
    out = out[out.BETA.notna() & out.SNP.notna() & out.A1.notna() & out.A2.notna()].reset_index(drop=True)
    return out if len(out) else None


H2_LINES = {"h2_obs": r"Total Observed scale h2: ([-\d.e]+) \(([\d.e-]+)\)", "intercept": r"Intercept: ([-\d.e]+) \(([\d.e-]+)\)",
            "ratio": r"Ratio: ([-\d.e]+) \(([\d.e-]+)\)", "lambda_gc": r"Lambda GC: ([-\d.e]+)",
            "mean_chi2": r"Mean Chi\^2: ([-\d.e]+)", "n_snps": r"After merging with regression SNP LD, (\d+) SNPs remain"}


def parse_h2_log(text: str) -> dict:
    out = {}
    for key, pattern in H2_LINES.items():
        m = re.search(pattern, text)
        if key == "h2_obs":
            out["h2_obs"], out["h2_obs_se"] = (float(m.group(1)), float(m.group(2))) if m else (None, None)
        elif key == "n_snps":
            out[key] = int(m.group(1)) if m else None
        else:
            out[key] = float(m.group(1)) if m else None
    return out


def parse_clumped(text: str) -> pd.DataFrame:
    """The index SNPs of a PLINK .clumped file: SNP, CHR, BP, P."""
    if not text.strip():
        return pd.DataFrame(columns=["SNP", "CHR", "BP", "P"])
    c = pd.read_csv(StringIO(text), sep=r"\s+")
    return c[["SNP", "CHR", "BP", "P"]].astype({"CHR": int, "BP": int, "P": float}).reset_index(drop=True)


def loci(index: pd.DataFrame) -> int:
    """Index SNPs as loci, the extended MHC counted once."""
    mhc = (index.CHR == MHC[0]) & index.BP.between(MHC[1], MHC[2])
    return int((~mhc).sum() + (1 if mhc.any() else 0))


def concentration(z2: pd.Series, n: int, h2_obs: float | None, index: pd.DataFrame | None = None) -> tuple[float | None, list[dict]]:
    """(share of h2_obs in the TOP largest z^2, those SNPs): per-SNP h2 = (z^2 - 1) / n. With `index` (SNP, CHR, BP)
    the extended MHC keeps only its strongest SNP, as it counts once among the loci."""
    if h2_obs is None or not np.isfinite(h2_obs) or h2_obs <= 0 or not len(z2):
        return None, []
    if index is not None and len(index):
        mhc = [x for x in index.SNP[(index.CHR == MHC[0]) & index.BP.between(MHC[1], MHC[2])] if x in z2.index]
        if len(mhc) > 1:
            keep = z2.loc[mhc].idxmax()
            z2 = z2.drop([x for x in mhc if x != keep])
    top = z2.sort_values(ascending=False).head(TOP)
    rows = [{"snp": str(k), "z2": float(v), "h2": float((v - 1) / n)} for k, v in top.items()]
    return float(sum(r["h2"] for r in rows) / h2_obs), rows


def extra_loci(missing: pd.DataFrame, index: pd.DataFrame) -> pd.DataFrame:
    """Genome-wide significant SNPs the clumping panel lacks (SNP, CHR, BP, P), taken by p, each counted as a locus
    when it lies more than CLUMP_KB from every index SNP and every SNP already added."""
    taken = index[["CHR", "BP"]].astype(int).copy() if len(index) else pd.DataFrame(columns=["CHR", "BP"])
    added = []
    for r in missing.sort_values("P").itertuples():
        near = taken[(taken.CHR == int(r.CHR)) & ((taken.BP - int(r.BP)).abs() <= CLUMP_KB * 1000)]
        if near.empty:
            added.append({"SNP": r.SNP, "CHR": int(r.CHR), "BP": int(r.BP), "P": float(r.P)})
            taken = pd.concat([taken, pd.DataFrame([{"CHR": int(r.CHR), "BP": int(r.BP)}])], ignore_index=True)
    return pd.DataFrame(added, columns=["SNP", "CHR", "BP", "P"])


_POSITIONS: pd.DataFrame | None = None
_PANEL: set[str] | None = None


def positions() -> pd.DataFrame:
    """CHR and BP of the LD-score reference SNPs (eur_w_ld_chr), indexed by SNP; read once."""
    global _POSITIONS
    if _POSITIONS is None:
        parts = [pd.read_csv(os.path.join(REF, "eur_w_ld_chr", f"{c}.l2.ldscore.gz"), sep="\t", usecols=["CHR", "SNP", "BP"])
                 for c in range(1, 23)]
        _POSITIONS = pd.concat(parts, ignore_index=True).drop_duplicates("SNP").set_index("SNP")
    return _POSITIONS


def panel_ids() -> set[str]:
    global _PANEL
    if _PANEL is None:
        _PANEL = set(pd.read_csv(PANEL + ".bim", sep="\t", header=None, usecols=[1])[1])
    return _PANEL


def trim_log(text: str, head: int = LOG_HEAD, tail: int = LOG_TAIL) -> str:
    """The first `head` and last `tail` characters of a long log, so the munge summary survives pandas warnings."""
    if len(text) <= head + tail:
        return text
    return text[:head] + f"\n... [{len(text) - head - tail:,} characters cut] ...\n" + text[-tail:]


def study(gcst: str) -> dict:
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT sumstats_path, cases, controls FROM preclin.gwas_catalog_study WHERE gcst = %s", (gcst,))
        row = cur.fetchone()
    if row is None or row[0] is None or row[1] is None or row[2] is None:
        raise ValueError(f"{gcst}: no harmonised summary statistics or no case-control counts")
    return {"gcst": gcst, "path": row[0], "cases": int(row[1]), "controls": int(row[2])}


def _run(cmd: list[str], log: list[str]) -> bool:
    r = subprocess.run(cmd, capture_output=True, text=True)
    log.append(f"$ {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
    return r.returncode == 0


def hapmap_ids() -> set[str]:
    return set(open(os.path.join(REF, "w_hm3.ids")).read().split())


def read_sumstats(path: str, keep: set[str]) -> pd.DataFrame | None:
    """The munge input from a harmonised file, streamed in chunks and cut to the HapMap3 SNPs."""
    parts = []
    header = pd.read_csv(path, sep="\t", nrows=0, compression="gzip").columns
    m = column_map(header)
    use = [c for c in m.values() if c]
    if not (m["snp"] and m["a1"] and m["a2"] and (m["beta"] or m["odds"])):
        return None
    for chunk in pd.read_csv(path, sep="\t", usecols=use, dtype=str, chunksize=CHUNK, compression="gzip"):
        chunk = chunk[chunk[m["snp"]].isin(keep)]
        part = munge_input(chunk) if len(chunk) else None
        if part is not None:
            parts.append(part)
    return pd.concat(parts, ignore_index=True) if parts else None


def write_run(gcst: str, status: str, fields: dict, log: list[str]) -> None:
    cols = ["n", "n_snps", "h2_obs", "h2_obs_se", "intercept", "ratio", "lambda_gc", "mean_chi2", "n_index_snps", "loci",
            "concentration", "top10"]
    values = [Json(fields.get(c)) if c == "top10" and fields.get(c) is not None else fields.get(c) for c in cols]
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute(f"""INSERT INTO preclin.ldsc_run (gcst, status, {', '.join(cols)}, tool, tool_version, ld_reference, log)
                        VALUES (%s, %s, {', '.join(['%s'] * len(cols))}, 'ldsc', %s, %s, %s)
                        ON CONFLICT (gcst) DO UPDATE SET status = EXCLUDED.status, {', '.join(f'{c} = EXCLUDED.{c}' for c in cols)},
                            tool_version = EXCLUDED.tool_version, ld_reference = EXCLUDED.ld_reference,
                            run_at = now(), log = EXCLUDED.log""",
                    [gcst, status, *values, TOOLS["ldsc"] + "; plink " + TOOLS["plink"], LD_REFERENCE, trim_log("\n".join(log))])
        conn.commit()


def run(gcst: str) -> dict:
    """Fetch, munge, h2, clump and concentration for one study; writes preclin.ldsc_run and returns the row."""
    s = study(gcst)
    n = s["cases"] + s["controls"]
    work = os.path.join(WORK, gcst)
    os.makedirs(work, exist_ok=True)
    log, fields = [], {"n": n}
    status = "fetch_failed"
    try:
        try:
            raw = download(SUMSTATS_BASE + s["path"], os.path.join(work, "raw.h.tsv.gz"), attempts=FETCH_ATTEMPTS, streams=STREAMS)
        except Exception as e:  # noqa: BLE001
            log.append(f"fetch: {e}")
            return {"gcst": gcst, "status": status}
        status = "munge_failed"   # from here every failure is in reading or munging the file
        m = read_sumstats(raw, hapmap_ids())
        os.remove(raw)
        if m is None:
            status = "no_effect"
            return {"gcst": gcst, "status": status}
        inp = os.path.join(work, "input.tsv")
        m.to_csv(inp, sep="\t", index=False)
        out = os.path.join(work, gcst)
        status = "munge_failed"
        if not _run(ldsc_cmd("munge_sumstats.py") + ["--sumstats", inp, "--N", str(n), "--merge-alleles",
                                                     os.path.join(REF, "w_hm3.snplist"), "--signed-sumstats", "BETA,0",
                                                     "--p", "P", "--snp", "SNP", "--a1", "A1", "--a2", "A2", "--out", out], log):
            return {"gcst": gcst, "status": status}
        status = "h2_failed"
        ld = os.path.join(REF, "eur_w_ld_chr") + "/"
        if not _run(ldsc_cmd("ldsc.py") + ["--h2", out + ".sumstats.gz", "--ref-ld-chr", ld, "--w-ld-chr", ld, "--out", out], log):
            return {"gcst": gcst, "status": status}
        h2 = parse_h2_log(open(out + ".log").read())
        if h2["h2_obs"] is None:
            return {"gcst": gcst, "status": status}
        fields.update(h2)
        status = "clump_failed"
        ss = pd.read_csv(out + ".sumstats.gz", sep="\t", compression="gzip")
        ss = ss[ss.Z.notna()].assign(P=lambda x: 2 * norm.sf(x.Z.abs()))
        ss[["SNP", "P"]].to_csv(os.path.join(work, "clump.tsv"), sep="\t", index=False)
        ok = _run([PLINK, "--bfile", PANEL, "--clump", os.path.join(work, "clump.tsv"), "--clump-p1", str(GWS), "--clump-p2",
                   str(GWS), "--clump-r2", str(CLUMP_R2), "--clump-kb", str(CLUMP_KB), "--clump-snp-field", "SNP",
                   "--clump-field", "P", "--out", out], log)
        clumped = out + ".clumped"
        if not ok and not ("No significant --clump results" in log[-1] or "no significant" in log[-1].lower()):
            return {"gcst": gcst, "status": status}
        index = parse_clumped(open(clumped).read()) if os.path.exists(clumped) else parse_clumped("")
        sig = ss[(ss.P < GWS) & ~ss.SNP.isin(panel_ids())]   # significant SNPs the panel cannot clump
        pos = positions().reindex(sig.SNP)
        placed = sig.assign(CHR=pos.CHR.values, BP=pos.BP.values).dropna(subset=["CHR", "BP"])
        extra = extra_loci(placed[["SNP", "CHR", "BP", "P"]], index)
        log.append(f"significant SNPs not in the clumping panel: {len(sig)}; without a reference position: "
                   f"{len(sig) - len(placed)}; counted as loci: {len(extra)}")
        index = pd.concat([index, extra], ignore_index=True)
        z2 = ss.set_index("SNP").Z.pow(2)
        share, top = concentration(z2.reindex(index.SNP).dropna(), n, h2["h2_obs"], index)
        fields.update({"n_index_snps": int(len(index)), "loci": loci(index), "concentration": share, "top10": top})
        status = "ok"
        return {"gcst": gcst, "status": status, **fields}
    except Exception:  # noqa: BLE001  the stage reached is the status; the traceback is the log
        log.append(traceback.format_exc())
        return {"gcst": gcst, "status": status}
    finally:
        write_run(gcst, status, fields, log)
        shutil.rmtree(work, ignore_errors=True)


def pending(retry: bool, gcst_file: str | None, shard: str | None = None) -> list[str]:
    """The studies still to run; shard "k/n" keeps every n-th of them starting at k (1-based) for parallel runs."""
    with llm.connect() as conn, conn.cursor() as cur:
        if gcst_file:
            wanted = [line.strip() for line in open(gcst_file) if line.strip()]
        else:
            cur.execute("SELECT DISTINCT gcst FROM preclin.disease_polygenicity WHERE gcst IS NOT NULL ORDER BY gcst")
            wanted = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT gcst, status FROM preclin.ldsc_run")
        done = dict(cur.fetchall())
    todo = [g for g in wanted if g not in done or (retry and done[g] != "ok")]
    if shard:
        k, n = (int(x) for x in shard.split("/"))
        todo = todo[k - 1::n]
    return todo


def run_cmd(args) -> None:
    for gcst in args.gcst:
        t = time.time()
        r = run(gcst)
        print(f"{gcst} {r['status']} h2_obs={r.get('h2_obs')} loci={r.get('loci')} concentration={r.get('concentration')} "
              f"{time.time() - t:.0f}s", flush=True)


def run_all(args) -> None:
    todo = pending(args.retry, args.gcst_file, args.shard)
    print(f"{len(todo)} studies to run", flush=True)
    counts: dict[str, int] = {}
    for i, gcst in enumerate(todo, 1):
        t = time.time()
        try:
            r = run(gcst)
        except Exception as e:  # noqa: BLE001
            r = {"status": f"error: {e}"}
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        print(f"[{i}/{len(todo)}] {gcst} {r['status']} h2_obs={r.get('h2_obs')} loci={r.get('loci')} "
              f"concentration={r.get('concentration')} {time.time() - t:.0f}s", flush=True)
    print(json.dumps(counts))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("references").set_defaults(fn=references)
    sub.add_parser("check").set_defaults(fn=check)
    p = sub.add_parser("run")
    p.add_argument("gcst", nargs="+")
    p.set_defaults(fn=run_cmd)
    p = sub.add_parser("run-all")
    p.add_argument("--retry", action="store_true", help="rerun studies whose last run failed")
    p.add_argument("--gcst-file", help="run these accessions (one per line) instead of the chosen studies")
    p.add_argument("--shard", help="k/n: this worker's share of the studies (every n-th from the k-th)")
    p.set_defaults(fn=run_all)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
