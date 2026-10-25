"""Years Open Targets evidence became known, where an evidence row's own date is missing or is not that year.

    python -m pipeline.evidence_dates clinvar  # ClinVar record accession -> year the record was created
    python -m pipeline.evidence_dates impc     # IMPC data releases -> year of the first release with an allele's calls
    python -m pipeline.evidence_dates studies  # GEO/ArrayExpress, IntOGen cohort and screen-paper years

Each command replaces its rows of preclin.evidence_known_year, keyed by the source key
pipeline.opentargets.evidence_key gives a row; `pipeline.opentargets evidence` then dates every
row it has a key year for and rebuilds the association series from the dated rows.

- ClinVar (eva, eva_somatic). Open Targets dates a record by its latest evaluation, which moves
  forward at every re-review and can precede a late submission. RCV accessions are issued in
  order of creation, so the year used is the creation year of the record, read off a calibration:
  the first submission date of CLINVAR_SAMPLE records spread over the accession range, a record
  taking the earliest year among calibration records at or above its accession. Records created by
  ClinVar's launch (CLINVAR_LAUNCH) import older submissions and take their evaluation year when
  that is earlier. The year is when the variant-condition record first appeared; a record first
  submitted with another classification and reclassified pathogenic later is dated too early, and
  the calibration run reports how often that happens among the sampled records.
- IMPC (impc). Mouse lines from the high-throughput consortia carry no date of their own (none, or
  the gene's first literature year). The year used is that of the first IMPC data release with a
  genotype-phenotype call for the allele (IMPC_RELEASES), dated by the release file's modification
  time; releases 1.0-2.0 have no such file, so 2015 is the earliest year.
- Studies, for rows with no publication date: Expression Atlas experiments by their GEO or
  ArrayExpress public date; IntOGen cohorts by the year their name carries; CRISPR screens without
  literature by the screen's paper (SCREEN_PAPERS).
Cancer Gene Census, Orphanet, UniProt and Reactome rows without a date have no source history to
date them, and Genomics England PanelApp genes only the panels' full activity logs (hundreds of
megabytes across the panels); they stay undated and count only in release scores.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import hashlib
import os
import re
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from email.utils import parsedate_to_datetime

import pyarrow.dataset as ds
import requests
from psycopg2.extras import execute_values

from pipeline import llm, opentargets

CACHE = os.path.join(llm.REPO, ".cache", "evidence_dates")
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
CLINVAR_SAMPLE = 120  # records sampled evenly across the accession range to calibrate accession -> creation date
CLINVAR_TRIES = 5     # neighbours tried at each sample point when a record cannot be read
CLINVAR_LAUNCH = 2013  # records created by then are ClinVar's launch import of earlier submissions
IMPC_URL = "https://ftp.ebi.ac.uk/pub/databases/impc/all-data-releases/"
# The last release of each year with a genotype-phenotype file, through the last year a phase entry is
# scored as of (2016 had no release); an allele first called later stays undated.
IMPC_RELEASES = ("04.0", "06.0", "08.0", "10.1", "12.0", "15.0", "18.0", "20.0", "22.1")
IMPC_FILES = ("csv/ALL_genotype_phenotype.csv.gz", "results/genotype-phenotype-assertions-ALL.csv.gz")
BIOSTUDIES = "https://www.ebi.ac.uk/biostudies/api/v1/studies/"
# CRISPR-screen studies Open Targets lists without literature: study id prefix -> (PMID, publication year)
SCREEN_PAPERS = {"iTF-Microglia": ("35953545", 2022)}  # Dräger et al., Nat Neurosci 2022
INTOGEN_YEAR = re.compile(r"_((?:19|20)\d\d)$")


def download(url: str, dest: str) -> str:
    """`url` saved at `dest` unless already cached; a partial download never takes the final name."""
    if not os.path.exists(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        part = dest + ".part"
        for attempt in range(5):
            try:
                with requests.get(url, stream=True, timeout=600) as r, open(part, "wb") as f:
                    r.raise_for_status()
                    for block in r.iter_content(1 << 20):
                        f.write(block)
                break
            except requests.RequestException:
                if attempt == 4:
                    raise
                time.sleep(15 * (attempt + 1))
        os.replace(part, dest)
    return dest


def get_json(url: str, **params) -> dict | list:
    for attempt in range(5):
        try:
            r = requests.get(url, params=params, timeout=120)
            if r.status_code == 429:
                raise requests.RequestException("rate limited")
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def evidence_rows(datasets: tuple[str, ...], columns: list[str]) -> list[dict]:
    """Open Targets evidence rows of `datasets` for the loaded targets, with `columns`."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT t.ensembl_id FROM preclin.moiety_target mt
                       JOIN public.targets t ON t.id = mt.target_id WHERE t.ensembl_id IS NOT NULL""")
        targets = [r[0] for r in cur.fetchall()]
    rows = []
    for name in datasets:
        data = ds.dataset(os.path.join(opentargets.CACHE, name), format="parquet")
        cols = [c for c in columns if c in data.schema.names]
        rows += data.to_table(columns=cols, filter=ds.field("targetId").isin(targets)).to_pylist()
    return rows


def store(datasources: tuple[str, ...], release_name: str, version: str, url: str, sha: str,
          rows: list[tuple[str, str, int, str]]) -> None:
    """Replace the evidence_known_year rows of `datasources` with `rows` (datasource, key, year, basis)."""
    with llm.connect() as conn, conn.cursor() as cur:
        release = llm.register_release(cur, release_name, version, url, sha, {"datasources": list(datasources)})
        cur.execute("DELETE FROM preclin.evidence_known_year WHERE datasource = ANY(%s)", (list(datasources),))
        execute_values(cur, """INSERT INTO preclin.evidence_known_year (datasource, key, year, basis, source_release_id)
                               VALUES %s""", [(*r, release) for r in rows], page_size=5000)
        conn.commit()
    by_basis = defaultdict(int)
    for r in rows:
        by_basis[(r[0], r[3])] += 1
    print(", ".join(f"{d}/{b}={n}" for (d, b), n in sorted(by_basis.items())))


def rcv_number(accession: str) -> int:
    return int(accession[3:])


def submissions(rcv: str) -> list[tuple[str, str]] | None:
    """(date created, germline classification) of the submissions on record `rcv`: those whose condition
    ClinVar maps to the record's MedGen concept. None when the record cannot be found."""
    found = get_json(EUTILS + "esearch.fcgi", db="clinvar", term=f"{rcv}[rcv]", retmode="json")
    ids = found["esearchresult"]["idlist"]
    if len(ids) != 1:
        return None
    for attempt in range(5):
        try:
            r = requests.get(EUTILS + "efetch.fcgi", params={"db": "clinvar", "id": ids[0], "rettype": "vcv",
                                                             "is_variationid": ""}, timeout=120)
            r.raise_for_status()
            root = ET.fromstring(r.content)
            break
        except (requests.RequestException, ET.ParseError):
            if attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))
    record = next((a for a in root.iter("RCVAccession") if a.get("Accession") == rcv), None)
    if record is None:
        return None
    concepts = {c.get("ID") for c in record.iter("ClassifiedCondition") if c.get("DB") == "MedGen"}
    mapped = defaultdict(set)
    for m in root.iter("TraitMapping"):
        medgen = m.find("MedGen")
        if medgen is not None:
            mapped[m.get("ClinicalAssertionID")].add(medgen.get("CUI"))
    out = []
    for a in root.iter("ClinicalAssertion"):
        if mapped[a.get("ID")] & concepts and a.get("DateCreated"):
            sig = a.find("Classification/GermlineClassification")
            out.append((a.get("DateCreated"), (sig.text or "") if sig is not None else ""))
    return sorted(out) or None


def clinvar(_args) -> None:
    rows = evidence_rows(("evidence_eva", "evidence_eva_somatic"),
                         ["targetId", "datasourceId", "studyId", "evidenceDate"])
    wanted: dict[str, tuple[str, int | None]] = {}  # RCV -> (datasource, year of latest evaluation)
    for r in rows:
        key = opentargets.evidence_key(r)
        if key and re.fullmatch(r"RCV\d+", key):
            wanted[key] = (r["datasourceId"], int(r["evidenceDate"][:4]) if r.get("evidenceDate") else None)
    ordered = sorted(wanted, key=rcv_number)
    # Calibration: the creation date (first submission) of records spread evenly over the accession range.
    points: list[tuple[int, str]] = []
    changed = plp = 0
    for q in range(CLINVAR_SAMPLE):
        for rcv in ordered[q * len(ordered) // CLINVAR_SAMPLE:][:CLINVAR_TRIES]:
            subs = submissions(rcv)
            time.sleep(0.4)  # E-utilities: at most three requests a second without a key
            if subs and subs[0][0]:
                points.append((rcv_number(rcv), subs[0][0]))
                if any(pathogenic(s) for _, s in subs):
                    plp += 1
                    changed += not pathogenic(subs[0][1])
                break
    points.sort()
    print(f"calibration: {len(points)} records; of {plp} with a pathogenic submission, {changed} were first "
          f"submitted with another classification", flush=True)
    # A record is created no later than any record with a higher accession: its year is the earliest
    # creation year among calibration records at or above it.
    suffix_min, years = [], 9999
    for n, created in reversed(points):
        years = min(years, int(created[:4]))
        suffix_min.append((n, years))
    suffix_min.reverse()
    numbers = [n for n, _ in suffix_min]
    out = []
    for rcv in ordered:
        i = bisect.bisect_left(numbers, rcv_number(rcv))
        if i == len(numbers):
            continue  # newer than every calibration record: keeps its own date
        datasource, evaluated = wanted[rcv]
        year = suffix_min[i][1]
        if year <= CLINVAR_LAUNCH and evaluated is not None and evaluated < year:
            out.append((datasource, rcv, evaluated, "clinvar_evaluated"))
        else:
            out.append((datasource, rcv, year, "clinvar_accession"))
    store(("eva", "eva_somatic"), "clinvar_record_creation_calibration", str(len(points)), EUTILS,
          hashlib.sha256(repr(points).encode()).hexdigest(), out)


def pathogenic(significance: str) -> bool:
    s = significance.lower()
    return "pathogenic" in s and "conflicting" not in s


def impc(_args) -> None:
    rows = evidence_rows(("evidence_impc",), ["targetId", "datasourceId", "biologicalModelAllelicComposition"])
    wanted = {k for k in map(opentargets.evidence_key, rows) if k}
    first: dict[str, int] = {}
    shas = []
    for release in IMPC_RELEASES:
        for name in IMPC_FILES:
            url = f"{IMPC_URL}release-{release}/{name}"
            head = requests.head(url, timeout=120)
            if head.status_code == 200:
                break
        else:
            raise RuntimeError(f"no genotype-phenotype file in IMPC release {release}")
        year = parsedate_to_datetime(head.headers["Last-Modified"]).year
        local = download(url, os.path.join(CACHE, "impc", release, os.path.basename(name)))
        shas.append(llm.sha256_file(local))
        with gzip.open(local, "rt", errors="replace", newline="") as f:
            for r in csv.DictReader(f):
                allele = r.get("allele_symbol") or ""
                if allele in wanted and allele not in first:
                    first[allele] = year
        print(f"release {release} ({year}): {len(first)} of {len(wanted)} alleles dated", flush=True)
    store(("impc",), "impc_genotype_phenotype_releases", ",".join(IMPC_RELEASES), IMPC_URL,
          hashlib.sha256("".join(shas).encode()).hexdigest(),
          [("impc", allele, year, "impc_release") for allele, year in first.items()])


def experiment_year(accession: str) -> int | None:
    """Public year of an Expression Atlas experiment: GEO series for E-GEOD-*, else BioStudies."""
    m = re.fullmatch(r"E-GEOD-(\d+)", accession)
    if m:
        ids = get_json(EUTILS + "esearch.fcgi", db="gds", term=f"GSE{m.group(1)}[ACCN] AND gse[ETYP]", retmode="json")
        uids = ids["esearchresult"]["idlist"]
        if uids:
            doc = get_json(EUTILS + "esummary.fcgi", db="gds", id=uids[0], retmode="json")["result"][uids[0]]
            return int(doc["pdat"][:4])
        return None
    doc = get_json(BIOSTUDIES + accession)
    release = next((a["value"] for a in doc.get("attributes", []) if a.get("name") == "ReleaseDate"), None)
    return int(release[:4]) if release else None


def studies(_args) -> None:
    rows = evidence_rows(("evidence_expression_atlas", "evidence_intogen", "evidence_crispr_screen"),
                         ["targetId", "datasourceId", "studyId", "cohortShortName",
                          "publicationDate", "evidenceDate", "releaseDate"])
    undated = [r for r in rows if not (r.get("publicationDate") or r.get("evidenceDate") or r.get("releaseDate"))]
    out: dict[tuple[str, str], tuple[int, str]] = {}
    for acc in sorted({r["studyId"] for r in undated if r["datasourceId"] == "expression_atlas"}):
        year = experiment_year(acc)
        if year:
            out[("expression_atlas", acc)] = (year, "geo_public" if acc.startswith("E-GEOD-") else "arrayexpress_public")
    for r in undated:
        key = opentargets.evidence_key(r)
        if r["datasourceId"] == "intogen" and (m := INTOGEN_YEAR.search(key or "")):
            out[("intogen", key)] = (int(m.group(1)), "intogen_cohort_year")
        if r["datasourceId"] == "crispr_screen":
            paper = next((v for p, v in SCREEN_PAPERS.items() if key and key.startswith(p)), None)
            if paper:
                out[("crispr_screen", key)] = (paper[1], "publication")
    store(("expression_atlas", "intogen", "crispr_screen"), "evidence_study_dates",
          datetime.now().date().isoformat(), f"{EUTILS} {BIOSTUDIES}",
          hashlib.sha256(repr(sorted(out.items())).encode()).hexdigest(),
          [(d, k, y, b) for (d, k), (y, b) in sorted(out.items())])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in [("clinvar", clinvar), ("impc", impc), ("studies", studies)]:
        sub.add_parser(name).set_defaults(fn=fn)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
