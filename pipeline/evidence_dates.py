"""Years Open Targets evidence became known, where an evidence row's own date is missing or is not that year.

    python -m pipeline.evidence_dates clinvar  # ClinVar record accession -> year the record was created
    python -m pipeline.evidence_dates impc     # IMPC data releases -> year of the first release with an allele's calls
    python -m pipeline.evidence_dates studies  # GEO/ArrayExpress, IntOGen cohort and screen-paper years
    python -m pipeline.evidence_dates projectscore  # Open Targets releases -> first year a Project Score pair was listed

Each command replaces its rows of preclin.evidence_known_year, keyed by preclin.ot_evidence_key
over the loaded rows of preclin.ot_evidence; `pipeline.opentargets dates` then dates every row
with a key year and rebuilds the association series from the dated rows.

- ClinVar (eva, eva_somatic). Open Targets dates a record by its latest evaluation, which moves
  forward at every re-review and can precede a late submission. RCV accessions are issued in
  order of creation, so the year used is the creation year of the record, read off a calibration
  (preclin.clinvar_accession_calibration): the first submission date of CLINVAR_SAMPLE records
  spread over the accession range, a record taking the earliest year among calibration records at
  or above its accession. Records created by ClinVar's launch (CLINVAR_LAUNCH) import older
  submissions and take their evaluation year when that is earlier. The year is when the
  variant-condition record first appeared; a record first submitted with another classification
  and reclassified pathogenic later is dated too early, and the run reports how often that happens
  among the sampled records.
- IMPC (impc). Mouse lines from the high-throughput consortia carry no date of their own (none, or
  the gene's first literature year). The year used is that of the first IMPC data release with a
  genotype-phenotype call for the allele (IMPC_RELEASES), dated by the release file's modification
  time; releases 1.0-2.0 have no such file, so 2015 is the earliest year.
- Studies, for rows with no date of their own: Expression Atlas experiments by their GEO or
  ArrayExpress public date; IntOGen cohorts by the year their name carries; CRISPR screens without
  literature by the screen's paper (SCREEN_PAPERS).
- Project Score (crispr). Open Targets dates every row by the 2024 re-analysis (Pacini et al.) that
  now supplies it, though most target-cancer pairs were first prioritised in Behan et al. 2019. A row
  is keyed by its target and disease and takes the year of the first Open Targets release whose
  Project Score file lists the pair (PROJECT_SCORE_FILES).
Cancer Gene Census, Orphanet, UniProt and Reactome rows without a date have no source history to
date them, and Genomics England PanelApp genes only the panels' full activity logs (hundreds of
megabytes across the panels); they stay undated and count only in release scores.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests
from psycopg2.extras import execute_values

from pipeline import llm

CACHE = os.path.join(llm.REPO, ".cache", "evidence_dates")
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
CLINVAR_SAMPLE = 120  # records sampled evenly across the accession range to calibrate accession -> creation date
CLINVAR_TRIES = 5     # neighbours tried at each sample point when a record cannot be read
CLINVAR_MAX_BYTES = 400_000  # a variant record larger than this (hundreds of submissions) is skipped for a neighbour
CLINVAR_LAUNCH = 2013  # records created by then are ClinVar's launch import of earlier submissions
IMPC_URL = "https://ftp.ebi.ac.uk/pub/databases/impc/all-data-releases/"
# The last release of each year with a genotype-phenotype file, through the last year a phase entry is
# scored as of (2016 had no release); an allele first called later stays undated.
IMPC_RELEASES = ("04.0", "06.0", "08.0", "10.1", "12.0", "15.0", "18.0", "20.0", "22.1")
IMPC_FILES = ("csv/ALL_genotype_phenotype.csv.gz", "results/genotype-phenotype-assertions-ALL.csv.gz")
BIOSTUDIES = "https://www.ebi.ac.uk/biostudies/api/v1/studies/"
# CRISPR-screen studies Open Targets lists without literature: study id prefix -> (PMID, publication year)
SCREEN_PAPERS = {"iTF-Microglia": ("35953545", 2022)}  # Dräger et al., Nat Neurosci 2022
OPENTARGETS_URL = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/"
# Each Project Score evidence file Open Targets ingested, in release order: Behan et al. 2019 and its
# updates through 23.02, then Pacini et al. 2024 from 24.03
PROJECT_SCORE_FILES = (("19.04", "crispr-2019-04-08.json.gz"), ("19.09", "crispr-2019-08-21.json.gz"),
                       ("21.02", "crispr-2020-11-18.json.gz"), ("22.02", "crispr-2022-01-24.json.gz"),
                       ("23.02", "crispr.json.gz"), ("24.03", "crispr.json.gz"))
INTOGEN_YEAR = re.compile(r"_((?:19|20)\d\d)$")


def request(method: str, url: str, **kwargs) -> requests.Response:
    """`url` fetched with retries over a slow or dropping connection; a HEAD may answer 404."""
    for attempt in range(6):
        try:
            r = requests.request(method, url, timeout=300, **kwargs)
            if r.status_code == 429:
                raise requests.RequestException("rate limited")
            if method == "GET" or r.status_code != 404:
                r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == 5:
                raise
            time.sleep(15 * (attempt + 1))
    raise AssertionError("unreachable")


def download(url: str, dest: str) -> str:
    """`url` saved at `dest` unless already cached; a partial download never takes the final name."""
    if not os.path.exists(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        part = dest + ".part"
        for attempt in range(6):
            try:
                with requests.get(url, stream=True, timeout=600) as r, open(part, "wb") as f:
                    r.raise_for_status()
                    for block in r.iter_content(1 << 16):
                        f.write(block)
                break
            except requests.RequestException:
                if attempt == 5:
                    raise
                time.sleep(30 * (attempt + 1))
        os.replace(part, dest)
    return dest


def keys(datasources: tuple[str, ...], undated_only: bool = False) -> list[tuple[str, str]]:
    """(datasource, key) of the loaded evidence rows of `datasources` that have a key."""
    undated = "AND source_year IS NULL" if undated_only else ""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute(f"""SELECT DISTINCT datasource, k FROM (
                          SELECT datasource, preclin.ot_evidence_key(datasource, detail) AS k FROM preclin.ot_evidence
                          WHERE datasource = ANY(%s) {undated}) x
                        WHERE k IS NOT NULL ORDER BY 1, 2""", (list(datasources),))
        return cur.fetchall()


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


def pathogenic(significance: str) -> bool:
    s = significance.lower()
    return "pathogenic" in s and "conflicting" not in s


def submissions(rcv: str) -> list[tuple[str, str]] | None:
    """(date created, germline classification) of the submissions on record `rcv`: those whose condition
    ClinVar maps to the record's MedGen concept. None when the record cannot be read."""
    ids = request("GET", EUTILS + "esearch.fcgi",
                  params={"db": "clinvar", "term": f"{rcv}[rcv]", "retmode": "json"}).json()["esearchresult"]["idlist"]
    if len(ids) != 1:
        return None
    for attempt in range(6):
        try:
            with requests.get(EUTILS + "efetch.fcgi", params={"db": "clinvar", "id": ids[0], "rettype": "vcv",
                                                              "is_variationid": ""}, stream=True, timeout=300) as r:
                r.raise_for_status()
                body = b""
                for block in r.iter_content(1 << 14):
                    body += block
                    if len(body) > CLINVAR_MAX_BYTES:
                        return None
            break
        except requests.RequestException:
            if attempt == 5:
                raise
            time.sleep(15 * (attempt + 1))
    root = ET.fromstring(body)
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
    with llm.connect() as conn, conn.cursor() as cur:  # CLINVAR_TRIES records at each of CLINVAR_SAMPLE quantiles
        cur.execute("""
            WITH r AS (SELECT DISTINCT k, substring(k FROM 4)::bigint AS n FROM (
                         SELECT preclin.ot_evidence_key(datasource, detail) AS k FROM preclin.ot_evidence
                         WHERE datasource IN ('eva', 'eva_somatic')) x WHERE k ~ '^RCV[0-9]+$'),
                 t AS (SELECT k, n, ntile(%s) OVER (ORDER BY n) AS q FROM r),
                 o AS (SELECT k, q, row_number() OVER (PARTITION BY q ORDER BY n) AS i FROM t)
            SELECT q, k FROM o WHERE i <= %s ORDER BY q, i""", (CLINVAR_SAMPLE, CLINVAR_TRIES))
        candidates = defaultdict(list)
        for q, k in cur.fetchall():
            candidates[q].append(k)
    points: list[tuple[int, str]] = []
    changed = plp = 0
    for q in sorted(candidates):
        for rcv in candidates[q]:
            subs = submissions(rcv)
            time.sleep(0.4)  # E-utilities: at most three requests a second without a key
            if subs:
                points.append((int(rcv[3:]), subs[0][0]))
                if any(pathogenic(s) for _, s in subs):
                    plp += 1
                    changed += not pathogenic(subs[0][1])
                break
        print(f"sample {q}/{len(candidates)}: {len(points)} calibration records", flush=True)
    print(f"calibration: {len(points)} records; of {plp} with a pathogenic submission, {changed} were first "
          f"submitted with another classification", flush=True)
    with llm.connect() as conn, conn.cursor() as cur:
        release = llm.register_release(cur, "clinvar_record_creation_calibration", str(len(points)), EUTILS,
                                       hashlib.sha256(repr(sorted(points)).encode()).hexdigest(),
                                       {"datasources": ["eva", "eva_somatic"], "sampled_pathogenic": plp,
                                        "first_submitted_otherwise": changed})
        cur.execute("DELETE FROM preclin.clinvar_accession_calibration")
        execute_values(cur, "INSERT INTO preclin.clinvar_accession_calibration (rcv_number, created, source_release_id) "
                            "VALUES %s", [(n, created, release) for n, created in points])
        cur.execute("DELETE FROM preclin.evidence_known_year WHERE datasource IN ('eva', 'eva_somatic')")
        cur.execute("""
            WITH c AS (SELECT rcv_number, min(extract(year FROM created)::int)
                                          OVER (ORDER BY rcv_number DESC) AS year
                       FROM preclin.clinvar_accession_calibration),
                 r AS (SELECT datasource, k, substring(k FROM 4)::bigint AS n, min(source_year) AS evaluated
                       FROM (SELECT datasource, preclin.ot_evidence_key(datasource, detail) AS k, source_year
                             FROM preclin.ot_evidence WHERE datasource IN ('eva', 'eva_somatic')) x
                       WHERE k ~ '^RCV[0-9]+$' GROUP BY 1, 2)
            INSERT INTO preclin.evidence_known_year (datasource, key, year, basis, source_release_id)
            SELECT r.datasource, r.k,
                   CASE WHEN c.year <= %(launch)s AND r.evaluated < c.year THEN r.evaluated ELSE c.year END,
                   CASE WHEN c.year <= %(launch)s AND r.evaluated < c.year THEN 'clinvar_evaluated'
                        ELSE 'clinvar_accession' END, %(release)s
            FROM r CROSS JOIN LATERAL (SELECT year FROM c WHERE c.rcv_number >= r.n
                                       ORDER BY c.rcv_number LIMIT 1) c""",
                    {"launch": CLINVAR_LAUNCH, "release": release})
        cur.execute("""SELECT basis, count(*), min(year), max(year) FROM preclin.evidence_known_year
                       WHERE datasource IN ('eva', 'eva_somatic') GROUP BY 1 ORDER BY 1""")
        summary = cur.fetchall()
        conn.commit()
    print(summary)


def impc(_args) -> None:
    wanted = {k for _, k in keys(("impc",))}
    first: dict[str, int] = {}
    shas = []
    for release in IMPC_RELEASES:
        for name in IMPC_FILES:
            url = f"{IMPC_URL}release-{release}/{name}"
            head = request("HEAD", url)
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
          [("impc", allele, year, "impc_release") for allele, year in sorted(first.items())])


def experiment_year(accession: str) -> int | None:
    """Public year of an Expression Atlas experiment: GEO series for E-GEOD-*, else BioStudies."""
    m = re.fullmatch(r"E-GEOD-(\d+)", accession)
    if m:
        uids = request("GET", EUTILS + "esearch.fcgi", params={
            "db": "gds", "term": f"GSE{m.group(1)}[ACCN] AND gse[ETYP]", "retmode": "json"}).json()["esearchresult"]["idlist"]
        if not uids:
            return None
        doc = request("GET", EUTILS + "esummary.fcgi",
                      params={"db": "gds", "id": uids[0], "retmode": "json"}).json()["result"][uids[0]]
        return int(doc["pdat"][:4])
    doc = request("GET", BIOSTUDIES + accession).json()
    released = next((a["value"] for a in doc.get("attributes", []) if a.get("name") == "ReleaseDate"), None)
    return int(released[:4]) if released else None


def studies(_args) -> None:
    out = []
    for source, key in keys(("expression_atlas", "intogen", "crispr_screen"), undated_only=True):
        if source == "expression_atlas":
            year = experiment_year(key)
            time.sleep(0.4)
            if year:
                out.append((source, key, year, "geo_public" if key.startswith("E-GEOD-") else "arrayexpress_public"))
        elif source == "intogen" and (m := INTOGEN_YEAR.search(key)):
            out.append((source, key, int(m.group(1)), "intogen_cohort_year"))
        elif source == "crispr_screen":
            paper = next((v for p, v in SCREEN_PAPERS.items() if key.startswith(p)), None)
            if paper:
                out.append((source, key, paper[1], "publication"))
    store(("expression_atlas", "intogen", "crispr_screen"), "evidence_study_dates",
          datetime.now().date().isoformat(), f"{EUTILS} {BIOSTUDIES}",
          hashlib.sha256(repr(out).encode()).hexdigest(), out)


def projectscore(_args) -> None:
    """Each loaded Project Score (crispr) row keyed "target disease", dated by the first Open Targets release
    whose crispr evidence file lists that target for that disease (EFO ids mapped to their equivalent MONDO term)."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT DISTINCT target_ensembl || ' ' || disease_id FROM preclin.ot_evidence WHERE datasource = 'crispr'")
        wanted = {k for (k,) in cur.fetchall()}
        cur.execute("""SELECT xref_id, term_id FROM preclin.ontology_xref
                       WHERE ontology = 'MONDO' AND equivalent AND xref_id LIKE 'EFO:%'""")
        mondo = dict(cur.fetchall())
    first: dict[str, int] = {}
    shas = []
    for release, name in PROJECT_SCORE_FILES:
        url = f"{OPENTARGETS_URL}{release}/input/evidence-files/{name}"
        year = parsedate_to_datetime(request("HEAD", url).headers["Last-Modified"]).year
        local = download(url, os.path.join(CACHE, "projectscore", release, name))
        shas.append(llm.sha256_file(local))
        with gzip.open(local, "rt") as f:
            for line in f:
                r = json.loads(line)
                if "target" in r:  # the 2019-2020 evidence schema
                    target, disease = r["target"]["id"].rsplit("/", 1)[-1], r["disease"]["id"].rsplit("/", 1)[-1]
                else:
                    target, disease = r["targetFromSourceId"], r["diseaseFromSourceMappedId"]
                disease = disease.replace("_", ":", 1)
                key = f"{target} {mondo.get(disease, disease)}"
                if key in wanted and key not in first:
                    first[key] = year
        print(f"release {release} ({year}): {len(first)} of {len(wanted)} target-disease pairs dated", flush=True)
    store(("crispr",), "opentargets_projectscore_releases", ",".join(r for r, _ in PROJECT_SCORE_FILES),
          OPENTARGETS_URL, hashlib.sha256("".join(shas).encode()).hexdigest(),
          [("crispr", key, year, "opentargets_release") for key, year in sorted(first.items())])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in [("clinvar", clinvar), ("impc", impc), ("studies", studies), ("projectscore", projectscore)]:
        sub.add_parser(name).set_defaults(fn=fn)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
