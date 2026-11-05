"""Published evidence about the drug itself, as known the year before a phase entry.

    python -m pipeline.literature search [--entries pilot|cohort]    # every record matching a drug's names
    python -m pipeline.literature screen [--entries pilot|cohort]    # LLM: prefilter (large literatures), then screen
    python -m pipeline.literature diseases                          # LLM: MONDO term of each modelled disease
    python -m pipeline.literature check                             # second model on a seeded pilot sample
    python -m pipeline.literature prefilter-check                   # recall of the prefilter against the full screen
    python -m pipeline.literature gate --reference PREFIX --rows A-B [--label NAME]   # pilot against a blind reference

Three kinds of evidence: animal_disease (the drug tested for efficacy in an animal model of the program disease,
a subtype or a disease within Lin 0.5 of it), animal_healthy (the drug's pharmacokinetics, pharmacodynamics or
exposure in healthy animals) and human_engagement (target engagement or a pharmacodynamic biomarker measured in
people; Phase 2 and 3 entries only).

This is the third version, user-directed, which report/translation_plan.md fixed before it ran and which overrides
the plan's stop rule; a kind that passes is labelled as passing on a third attempt. Each drug is searched once
by its names alone (INN, code names, ChEMBL and PubChem synonyms, FDA substance-registry names), with no disease,
species or kind terms, up to the latest cutoff of its entries (the year before entry), reviews excluded: in PubMed
titles and abstracts, keeping every hit, and in Europe PMC titles and abstracts outside MEDLINE (preprints,
patents, theses and other sources with an abstract). For a drug with more than PREFILTER_ABOVE records, a cheap
model first reads each one for whether it possibly reports original data on the drug of any kind; the rest, and
every record of a smaller literature, get the version 2 screen, which decides every kind and names the disease of
any animal model; a second step maps that disease to MONDO, as pipeline.indications maps trial conditions. An
entry counts only records published by its own cutoff.

The entries are the US-sited phase entries of 2008-2019 (cohort) or a seeded sample of 300 of them (pilot,
report/audits/literature_pilot_sample.csv). Versions 1 and 2 keep their rows (preclin.literature_search, _hit,
_screen; preclin.literature_drug_search, _hit, _screen). A kind runs on the cohort only once the pilot passes the
plan's gates.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import requests
from psycopg2.extras import execute_values

from pipeline import llm
from pipeline.attribution import NOT_REVIEWS, efetch
from pipeline.chembl import IDS_PER_CALL, PAGE, get as chembl_get
from pipeline.indications import N_CANDIDATES, MondoIndex
from pipeline.outcomes import eutils

KINDS = ("animal_disease", "animal_healthy", "human_engagement")
PILOT = os.path.join(llm.REPO, "report", "audits", "literature_pilot_sample.csv")
GATE = os.path.join(llm.REPO, "report", "audits", "literature_gate.json")
ESEARCH_MAX = 9999  # PubMed returns at most this many ids per search; larger sets are split by date
PREFILTER_ABOVE = 3000  # records per drug above which a cheap model reads each record first
PREFILTER_CHECK = 1000  # seeded large-literature records given the full screen to measure the prefilter's recall
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/searchPOST"
EPMC_PAGE = 1000
NAME_CHUNK = 50  # drugs whose names are looked up together
CHUNK_RECORDS = 60000  # records a cohort worker prefilters and screens together
FIRECRAWL_LIMIT = 550  # calls to Firecrawl's research index on the pilot (the user approves any cohort run)
FIRECRAWL_RESULTS = 20  # results per call; 40 times out
MAX_DRUG_NAMES = 50
MAX_NAME_CHARS = 30
MAX_NAME_WORDS = 4
CIDS_PER_CALL = 100
PUBCHEM_SYNONYMS = 20  # PubChem lists the most used synonyms first; vendor catalogue codes follow
CHECK_PER_KIND = 50  # half screened in, half screened out, per kind
CHECK_SEED = 20261104
RELATED = 0.5  # Lin similarity within which a modelled disease counts for the entry's disease
GATES = {"recall": 0.80, "kappa": 0.60, "phase2_coverage": 0.08}
METHOD = "literature_evidence@v3"
PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/synonyms/JSON"

# Synonyms that are database or registry identifiers, not names a paper would use for the drug.
IDENTIFIER = re.compile(
    r"^(\d{2,7}-\d{2}-\d|\d{3}-\d{3}-\d|[A-Z]\d{2}[A-Z]{2}\d{2}|Q\d+|[CD]\d{5}|DB\d{5}|C\d+H\d+\S*"
    r"|(CHEMBL|SCHEMBL|CHEBI|DTXSID|DTXCID|MFCD|RefChem|UNII|NCGC|AKOS|ZINC|BDBM|HMS|SMR|MLS|KBio|Tox21|CCRIS|HSDB"
    r"|EINECS|BRD|GTPL|BCP|EN300|STK|SPECTRUM|Prestwick|BSPBio|nchembio|Pharmakon|Kinome|GLXC|SDCCG|CAS-|cid_|orb\d"
    r"|DEA NO|WHO \d|AS-|HY-|CS-|SR-|AC-|AB\d|CU-\d|EX-A\d|BS-\d|s\d).*"
    r"|(compound|cpd|example|drug|molecule)\s*\d+[a-z]?)$",
    re.IGNORECASE)
UNII_CODE = re.compile(r"^(?=.*\d)(?=.*[A-Z])[A-Z0-9]{10}$")


def clean(name: str) -> str:
    """A name without a trailing bracketed qualifier ("ALVOCIDIB [INN]", "Iressa (TN)") or quotes."""
    return re.sub(r"\s*[\[(][^\])]*[\])]$", "", name).replace('"', "").strip()


def usable(name: str) -> bool:
    """A name a paper could use for the drug: not a systematic or bracketed chemical name, not a database
    identifier, at most MAX_NAME_CHARS characters and MAX_NAME_WORDS words; a name with a digit has at least
    five letters or digits (ASA, TF2 match unrelated words), any other at least four characters."""
    if len(name) < 4 or len(name) > MAX_NAME_CHARS or len(name.split()) > MAX_NAME_WORDS:
        return False
    if any(c in name for c in "()[]{},;^") or IDENTIFIER.match(name) or UNII_CODE.match(name):
        return False
    return not (re.search(r"\d", name) and len(re.sub(r"\W", "", name)) < 5)


def drug_names(*groups: list[str]) -> list[str]:
    """Usable names from each group in order (INN, code names, ChEMBL, PubChem, then the substance registry, which
    lists every biosimilar and formulation code), case-insensitively distinct, at most MAX_DRUG_NAMES."""
    out: list[str] = []
    for n in (clean(x) for g in groups for x in g):
        if usable(n) and n.lower() not in {o.lower() for o in out}:
            out.append(n)
    return out[:MAX_DRUG_NAMES]


def names_clause(names: list[str]) -> str:
    return f'({" OR ".join(f"{chr(34)}{n}{chr(34)}[tiab]" for n in names)})'


def pubmed_term(names: list[str], lo: str, hi: str) -> str:
    return f'{names_clause(names)} AND ("{lo}"[dp] : "{hi}"[dp]) {NOT_REVIEWS}'


def pubmed_count(term: str) -> int:
    return int(ET.fromstring(eutils("esearch", term=term, retmax="0")).findtext("Count") or 0)


def pubmed_ids(names: list[str], cutoff: int) -> tuple[str, int, list[str]]:
    """The query, its hit count and every PMID it returns: one search when the count is within ESEARCH_MAX,
    else the date range is halved (years, then months) until each part is."""
    full = pubmed_term(names, "1900", str(cutoff))
    total = pubmed_count(full)
    ids: list[str] = []

    def collect(lo: tuple[int, int], hi: tuple[int, int]) -> None:
        span = (f"{lo[0]}/{lo[1]:02d}", f"{hi[0]}/{hi[1]:02d}")
        term = pubmed_term(names, *span)
        n = pubmed_count(term)
        if n == 0:
            return
        months = (hi[0] - lo[0]) * 12 + hi[1] - lo[1]
        if n <= ESEARCH_MAX or months == 0:
            ids.extend(x.text for x in ET.fromstring(eutils("esearch", term=term, retmax=str(ESEARCH_MAX))).iter("Id"))
            return
        mid = lo[0] * 12 + lo[1] - 1 + months // 2
        collect(lo, (mid // 12, mid % 12 + 1))
        nxt = mid + 1
        collect((nxt // 12, nxt % 12 + 1), hi)

    if total <= ESEARCH_MAX:
        ids = [x.text for x in ET.fromstring(eutils("esearch", term=full, retmax=str(ESEARCH_MAX))).iter("Id")]
    else:
        collect((1900, 1), (cutoff, 12))
    return full, total, sorted(set(ids), key=int)


def epmc_query(names: list[str], cutoff: int) -> str:
    """Europe PMC titles and abstracts outside MEDLINE (whose records the PubMed search covers), with an abstract."""
    return (f'({" OR ".join(f"TITLE_ABS:{chr(34)}{n}{chr(34)}" for n in names)}) AND PUB_YEAR:[1900 TO {cutoff}] '
            'AND NOT SRC:MED AND HAS_ABSTRACT:Y AND NOT PUB_TYPE:"review"')


def epmc_post(query: str, cursor: str = "*", page: int = EPMC_PAGE) -> dict:
    for attempt in range(6):
        try:
            r = requests.post(EPMC, data={"query": query, "format": "json", "resultType": "core",
                                          "pageSize": page, "cursorMark": cursor}, timeout=180)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("Europe PMC search failed")


def epmc_record(r: dict) -> tuple:
    year = r.get("pubYear")
    return (f"{r['source']}:{r['id']}", r["source"], r.get("title") or "", r.get("abstractText"),
            int(year) if year and str(year).isdigit() else None, r.get("doi"))


def epmc_records(names: list[str], cutoff: int) -> tuple[str, int, list[tuple]]:
    """The query, its hit count and every record (record_id, source, title, abstract, year, doi) it returns."""
    q = epmc_query(names, cutoff)
    out, cursor, total = [], "*", 0
    while True:
        page = epmc_post(q, cursor)
        total = int(page.get("hitCount") or 0)
        out += [epmc_record(r) for r in page.get("resultList", {}).get("result", [])]
        nxt = page.get("nextCursorMark")
        if not nxt or nxt == cursor or len(out) >= total:
            return q, total, out
        cursor = nxt


def pilot_entries() -> pd.DataFrame:
    s = pd.read_csv(PILOT)
    return s.assign(row=np.arange(1, len(s) + 1))[["moiety_id", "mondo_id", "phase", "entry_date",
                                                   "evidence_cutoff_year", "reference_set", "row"]] \
        .rename(columns={"evidence_cutoff_year": "cutoff_year"})


def cohort_entries() -> pd.DataFrame:
    """US-sited phase entries of 2008-2019 with a disease (report.section1.phase_rows)."""
    from report import frame
    from report.section1 import phase_rows
    from report.section3 import SECTION1
    progs = frame.programs()
    rows = phase_rows(progs, frame.program_trials(), frame.snapshot(), window=SECTION1)
    rows = rows[~rows.credited & rows.us_site].copy()
    rows["mondo_id"] = rows.program_id.map(progs.set_index("program_id").mondo_id)
    rows = rows[rows.mondo_id.notna()]
    rows["cutoff_year"] = pd.to_datetime(rows.entry).dt.year - 1
    rows["entry_date"] = pd.to_datetime(rows.entry).dt.date.astype(str)
    return rows[["moiety_id", "mondo_id", "phase", "entry_date", "cutoff_year"]].astype({"moiety_id": int}) \
        .drop_duplicates(["moiety_id", "mondo_id", "phase"]).reset_index(drop=True)


def survivors(ids: list[int]) -> dict[int, int]:
    """Entity -> the entity it now is, following preclin.moiety_merge chains."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT loser_id, survivor_id FROM preclin.moiety_merge WHERE cause <> 'reversed' ORDER BY merged_at")
        merged = dict(cur.fetchall())
    out = {}
    for m in ids:
        seen, x = set(), m
        while x in merged and x not in seen:
            seen.add(x)
            x = merged[x]
        out[m] = x
    return out


def cohort_drugs() -> dict[int, int]:
    """Entity -> latest cutoff year (year before entry) over the stored evidence entries
    (preclin.evidence_entry, the US-sited phase entries of 2008-2019), merged entities resolved to survivors."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT moiety_id, max(entry_year) - 1 FROM preclin.evidence_entry GROUP BY 1")
        rows = cur.fetchall()
    to = survivors([m for m, _ in rows])
    out: dict[int, int] = {}
    for m, y in rows:
        out[to[m]] = max(out.get(to[m], 0), int(y))
    return out


def entries(which: str) -> pd.DataFrame:
    return pilot_entries() if which == "pilot" else cohort_entries()


def drug_cutoffs(e: pd.DataFrame) -> dict[int, int]:
    """Entity -> the latest cutoff year of its entries: the one search it needs."""
    return {int(m): int(y) for m, y in e.groupby("moiety_id").cutoff_year.max().items()}


def pubchem_synonyms(cids: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for i in range(0, len(cids), CIDS_PER_CALL):
        r = requests.post(PUG, data={"cid": ",".join(cids[i:i + CIDS_PER_CALL])}, timeout=180)
        if r.status_code == 404:
            continue
        r.raise_for_status()
        for info in r.json()["InformationList"]["Information"]:
            out[str(info["CID"])] = (info.get("Synonym") or [])[:PUBCHEM_SYNONYMS]
    return out


def chembl_synonyms(ids: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for i in range(0, len(ids), IDS_PER_CALL):
        page = chembl_get("molecule.json", limit=PAGE, molecule_chembl_id__in=",".join(ids[i:i + IDS_PER_CALL]),
                          only="molecule_chembl_id,pref_name,molecule_synonyms")
        for m in page["molecules"]:
            out[m["molecule_chembl_id"]] = [m["pref_name"]] * bool(m.get("pref_name")) + \
                [s["molecule_synonym"] for s in m.get("molecule_synonyms") or []]
    return out


def names_of(moieties: list[int]) -> dict[int, list[str]]:
    """Searchable names of each entity; the database read ends before PubChem and ChEMBL are called."""
    with llm.connect() as conn, conn.cursor() as cur:
        rows = name_rows(cur, moieties)
    return names_from(rows)


def name_rows(cur, moieties: list[int]) -> list[tuple]:
    cur.execute("""SELECT m.moiety_id, m.name, m.code_names, u.pubchem_cid,
                          coalesce(array_agg(DISTINCT n.name) FILTER (WHERE n.name IS NOT NULL), '{}'),
                          coalesce(array_agg(DISTINCT cm.parent_chembl_id) FILTER (WHERE cm.parent_chembl_id IS NOT NULL), '{}')
                   FROM preclin.moiety m
                   LEFT JOIN preclin.unii_substance u ON u.unii = m.unii
                   LEFT JOIN preclin.unii_name n ON n.unii = m.unii AND n.name_type IN ('cn', 'cd', 'of')
                   LEFT JOIN preclin.chembl_moiety cm ON cm.moiety_id = m.moiety_id
                   WHERE m.moiety_id = ANY(%s) GROUP BY 1, 2, 3, 4""", (moieties,))
    return cur.fetchall()


def names_from(rows: list[tuple]) -> dict[int, list[str]]:
    pubchem = pubchem_synonyms(sorted({c for *_, c, _, _ in rows if c}, key=int))
    chembl = chembl_synonyms(sorted({x for *_, ids in rows for x in ids}))
    out = {}
    for m, name, codes, cid, reg, ids in rows:
        own = [name, *(codes or []), *reg, *(pubchem.get(cid, []) if cid else [])]
        known = {clean(n).lower() for n in own}
        # A ChEMBL parent counts only when one of its names is already the entity's: a few parents are
        # matched to the wrong entity, and their synonyms would search for another drug.
        same = [s for x in ids if known & {clean(n).lower() for n in chembl.get(x, [])} for s in chembl[x]]
        out[m] = drug_names([name], list(codes or []), same, pubchem.get(cid, []) if cid else [], sorted(reg))
    return out


def store_records(cur, records: list[tuple]) -> None:
    if records:
        execute_values(cur, """INSERT INTO preclin.literature_record (record_id, source, title, abstract, year, doi)
                               VALUES %s ON CONFLICT (record_id) DO NOTHING""", records)


def store_hits(cur, hits: list[tuple]) -> None:
    if hits:
        execute_values(cur, """INSERT INTO preclin.literature_v3_hit (moiety_id, cutoff_year, source, record_id)
                               VALUES %s ON CONFLICT DO NOTHING""", hits, page_size=5000)


def search_drugs(cut: dict[int, int], log=print) -> None:
    """PubMed and Europe PMC searches for each drug at its cutoff not yet searched; each drug's results are
    committed before the next, so an interrupted run resumes where it stopped."""
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, METHOD, "Published evidence about the drug before phase entry (version 3)", __doc__,
                          ["PubMed", "Europe PMC", "Firecrawl research index", "PubChem", "ChEMBL", "preclin.moiety",
                           "preclin.unii_name", "preclin.ontology_term"],
                          {"prefilter_above": PREFILTER_ABOVE, "max_names": MAX_DRUG_NAMES, "exclude": NOT_REVIEWS,
                           "related_lin": RELATED, "firecrawl_limit": FIRECRAWL_LIMIT})
        cur.execute("SELECT moiety_id, cutoff_year FROM preclin.literature_v3_search GROUP BY 1, 2 HAVING count(*) = 2")
        done = set(cur.fetchall())
        conn.commit()
    todo = sorted((m, y) for m, y in cut.items() if (m, y) not in done)
    log(f"search: drugs={len(cut)} to search={len(todo)}")
    for start in range(0, len(todo), NAME_CHUNK):
        chunk = todo[start:start + NAME_CHUNK]
        names = names_of([m for m, _ in chunk])
        for m, y in chunk:
            if not names.get(m):
                continue
            pq, pn, pmids = pubmed_ids(names[m], y)
            eq, en, records = epmc_records(names[m], y)
            with llm.connect() as conn, conn.cursor() as cur:
                store_records(cur, records)
                execute_values(cur, """INSERT INTO preclin.literature_v3_search (moiety_id, cutoff_year, source, names, query, n_hits)
                                       VALUES %s ON CONFLICT DO NOTHING""",
                               [(m, y, "pubmed", names[m], pq, pn), (m, y, "europepmc", names[m], eq, en)])
                store_hits(cur, [(m, y, "pubmed", p) for p in pmids] + [(m, y, "europepmc", r[0]) for r in records])
                conn.commit()
            log(f"searched moiety={m} pubmed={len(pmids)}/{pn} europepmc={len(records)}")


def search(args) -> None:
    """Search the drugs of the entries (pilot or cohort)."""
    search_drugs(drug_cutoffs(entries(args.entries)) if args.entries == "pilot" else cohort_drugs())


def firecrawl_cli(args: list[str]) -> list[dict]:
    """One call to Firecrawl's research index through its CLI; a failed call (a 504) is retried twice."""
    import subprocess
    import tempfile
    for attempt in range(3):
        with tempfile.NamedTemporaryFile(suffix=".json") as f:
            try:
                r = subprocess.run(["firecrawl", "research", *args, "--json", "-o", f.name], capture_output=True,
                                   text=True, timeout=300)
            except subprocess.TimeoutExpired:
                continue
            if r.returncode == 0:
                with open(f.name) as fh:
                    return json.load(fh).get("results") or []
        time.sleep(15 * (attempt + 1))
    return []


def firecrawl_query(names: list[str], disease: str) -> str:
    """A natural-language description of the papers sought for one entry: the drug, its disease and the kinds."""
    alias = f" ({', '.join(names[1:6])})" if len(names) > 1 else ""
    return (f"{names[0]}{alias}: efficacy in animal models of {disease}, pharmacokinetics or pharmacodynamics in "
            f"animals, and target engagement or pharmacodynamic biomarkers in humans")


def firecrawl_ids(results: list[dict], cutoff: int) -> list[tuple[str, str | None]]:
    """(PMID or other id, DOI) of each result published by the cutoff year."""
    out = []
    for r in results:
        if (r.get("createdDate") or "9999")[:4] > str(cutoff):
            continue
        ids = r.get("ids") or {}
        pmid = (ids.get("pmid") or [None])[0]
        doi = (ids.get("doi") or [None])[0]
        pmcid = (ids.get("pmcid") or [None])[0]
        out.append((pmid or (f"PMC:{pmcid}" if pmcid else f"DOI:{doi}" if doi else r.get("primaryId")), doi))
    return out


def resolve_external(keys: list[tuple[str, str | None]]) -> dict[str, str]:
    """Firecrawl ids without a PMID -> a record id: the PMID Europe PMC lists for a PMCID or DOI, else a Europe PMC
    record (preprint and others) stored in preclin.literature_record. Ids Europe PMC does not hold are dropped."""
    out, records = {}, []
    for key, doi in keys:
        q = f"PMCID:{key[4:]}" if key.startswith("PMC:") else f'DOI:"{doi}"' if doi else None
        if not q:
            continue
        res = epmc_post(q, page=5).get("resultList", {}).get("result", [])
        if not res:
            continue
        r = next((x for x in res if x.get("pmid")), res[0])
        if r.get("pmid"):
            out[key] = r["pmid"]
        elif r.get("abstractText"):
            rec = epmc_record(r)
            records.append(rec)
            out[key] = rec[0]
    with llm.connect() as conn, conn.cursor() as cur:
        store_records(cur, records)
        conn.commit()
    return out


def firecrawl_credits() -> int | None:
    import subprocess
    try:
        r = subprocess.run(["firecrawl", "credit-usage", "--json"], capture_output=True, text=True, timeout=60)
        return int(json.loads(r.stdout)["data"]["remainingCredits"])
    except (subprocess.TimeoutExpired, ValueError, KeyError):
        return None


def firecrawl_entries(which: str) -> pd.DataFrame:
    """Entries to search in Firecrawl: the pilot sample, or the stored cohort entries with merged entities
    resolved to survivors."""
    if which == "pilot":
        return pilot_entries()
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT moiety_id, mondo_id, max(entry_year) - 1 FROM preclin.evidence_entry GROUP BY 1, 2")
        rows = cur.fetchall()
    to = survivors([m for m, _, _ in rows])
    e = pd.DataFrame([(to[m], d, y) for m, d, y in rows], columns=["moiety_id", "mondo_id", "cutoff_year"])
    return e.groupby(["moiety_id", "mondo_id"], as_index=False).cutoff_year.max()


def firecrawl(args) -> None:
    """Firecrawl's research index. --mode search runs one semantic search per entry not yet searched (a drug is
    searched once its names are stored); --mode related expands, per drug, from its first qualifying screened record.
    The pilot is capped at FIRECRAWL_LIMIT calls; a cohort run stops when the account has under 10 credits left,
    and resumes where it stopped."""
    e = firecrawl_entries(args.entries)
    cut = {int(m): int(y) for m, y in e.groupby("moiety_id").cutoff_year.max().items()}
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM preclin.literature_v3_firecrawl")
        used = cur.fetchone()[0]
        cur.execute("SELECT moiety_id, mondo_id, mode FROM preclin.literature_v3_firecrawl")
        done = set(cur.fetchall())
        cur.execute("SELECT DISTINCT ON (moiety_id) moiety_id, names FROM preclin.literature_v3_search WHERE source = 'pubmed'")
        names = dict(cur.fetchall())
        cur.execute("SELECT term_id, label FROM preclin.ontology_term WHERE term_id = ANY(%s)", (sorted(set(e.mondo_id)),))
        label = dict(cur.fetchall())
        cur.execute("""SELECT DISTINCT ON (moiety_id) moiety_id, record_id FROM preclin.literature_v3_screen
                       WHERE animal_disease OR animal_healthy OR human_engagement ORDER BY moiety_id, record_id""")
        seeds = dict(cur.fetchall())
    if args.mode == "search":
        calls = [(int(r.moiety_id), r.mondo_id, int(r.cutoff_year)) for r in e.itertuples()
                 if (int(r.moiety_id), r.mondo_id, "search") not in done and names.get(int(r.moiety_id))]
    else:
        calls = [(m, "", cut[m]) for m in sorted(seeds) if m in cut and (m, "", "related") not in done]
    if args.entries == "pilot":
        calls = calls[:max(FIRECRAWL_LIMIT - used, 0)]
    print(f"firecrawl {args.mode} ({args.entries}): calls={len(calls)} credits={firecrawl_credits()}", flush=True)
    for i, (m, d, y) in enumerate(calls, 1):
        if args.entries == "cohort" and i % 100 == 1:
            left = firecrawl_credits()
            if left is not None and left < 10:
                print(f"firecrawl paused: {left} credits left, {len(calls) - i + 1} calls to go", flush=True)
                return
        if args.mode == "search":
            q = firecrawl_query(names[m], label.get(d, "the diseases it treats"))
            results = firecrawl_cli(["search-papers", q, "--limit", str(FIRECRAWL_RESULTS), "--to", f"{y}-12-31"])
        else:
            seed = seeds[m]
            q = f"{'pmid:' + seed if seed.isdigit() else seed} | similar | {names[m][0]}"
            results = firecrawl_cli(["related-papers", f"pmid:{seed}" if seed.isdigit() else seed, "--intent",
                                     f"{names[m][0]}: preclinical efficacy, animal pharmacology or human target engagement",
                                     "--mode", "similar", "--limit", str(FIRECRAWL_RESULTS)])
        got = firecrawl_ids(results, cut[m])
        external = resolve_external([k for k in got if not k[0].isdigit()])
        record_ids = sorted({k if k.isdigit() else external[k] for k, _ in got if k.isdigit() or k in external})
        with llm.connect() as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO preclin.literature_v3_firecrawl (moiety_id, mondo_id, cutoff_year, mode, query, n_results)
                           VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""", (m, d, y, args.mode, q, len(results)))
            store_hits(cur, [(m, cut[m], "firecrawl", r) for r in record_ids])
            conn.commit()
        if i % 100 == 0 or i == len(calls):
            print(f"firecrawl {args.mode} {i}/{len(calls)}", flush=True)


SYSTEM = """You read one PubMed abstract about a specific drug and decide what it reports about THIS drug (under any of the names given; a different drug with the same target does not count).

original_data: true when the abstract reports new experimental or clinical results involving this drug (not a review, commentary, guideline or protocol).

animal_disease: true when this drug was given in vivo to animals that model a human disease (induced, genetic, transgenic or xenograft models; behavioural models of a psychiatric or neurological disease count) and an efficacy outcome of the drug was measured. List in modelled_diseases each human disease the models stand for, as a standard disease name (e.g. "non-small cell lung carcinoma" for an A549 xenograft, "major depressive disorder" for a forced-swim test, "rheumatoid arthritis" for collagen-induced arthritis); empty unless animal_disease. In vitro work, healthy animals and people do not count.

animal_healthy: true when this drug was given to animals that do not model a disease (healthy or naive animals) and its pharmacokinetics, absorption, distribution (tissue or brain exposure, transport), metabolism or excretion, or a pharmacodynamic effect on its target or pathway was measured. Toxicology alone, in vitro work and disease models do not count.

human_engagement: true when, in people (healthy volunteers or patients), a measurement shows whether this drug engaged its target or moved a pharmacodynamic biomarker of its mechanism: receptor occupancy (e.g. PET), target enzyme inhibition, target protein or ligand lowered, transcript knockdown, or a downstream biomarker of the target's pathway. Pharmacokinetics alone, clinical efficacy or safety alone, and animal or in vitro work do not count.

Give the species of the deciding study (human, mouse, rat, ...; empty if no kind is true), what was measured in a few words in detail, and the sentence that decides it in quote, copied exactly (empty if no kind is true). Judge only from the abstract."""

SCHEMA = {"type": "object", "additionalProperties": False,
          "properties": {"original_data": {"type": "boolean"}, "animal_disease": {"type": "boolean"},
                         "modelled_diseases": {"type": "array", "items": {"type": "string"}},
                         "animal_healthy": {"type": "boolean"}, "human_engagement": {"type": "boolean"},
                         "species": {"type": "string"}, "detail": {"type": "string"}, "quote": {"type": "string"}},
          "required": ["original_data", "animal_disease", "modelled_diseases", "animal_healthy", "human_engagement",
                       "species", "detail", "quote"]}


def render(p: dict) -> str:
    lines = [f"Drug: {'; '.join(p['drug_names'])}"]
    if p.get("targets"):
        lines.append(f"Its targets: {p['targets']}")
    lines += ["", f"PMID {p['pmid']} ({p.get('year') or 'year unknown'}). {p['title']}", "", p["abstract"] or "(no abstract)"]
    return "\n".join(lines)


def validate(p: dict, out: dict) -> None:
    if bool(out["modelled_diseases"]) != out["animal_disease"]:
        raise ValueError("modelled_diseases must be listed exactly when animal_disease is true")
    q = re.sub(r"\s+", " ", out["quote"]).strip().lower()
    text = re.sub(r"\s+", " ", f"{p['title']} {p['abstract'] or ''}").lower()
    if q and q[:60] not in text:
        raise ValueError("quote is not in the abstract")


def task(model: str = "claude-sonnet-5", suffix: str = "") -> llm.Task:
    return llm.Task(name="literature_drug_screen" + suffix, prompt_version="v1", schema_version="v1", system=SYSTEM,
                    schema=SCHEMA, render=render, validate=validate, subject_type="moiety_pmid", model=model,
                    effort="low", max_tokens=2000)


PREFILTER_SYSTEM = """You skim one abstract to decide whether it could report original data about a specific drug (under any of the names given; a different drug does not count) of any of these kinds: the drug tested for efficacy in an animal model of a disease; its pharmacokinetics, distribution or pharmacodynamics in animals; or its target engagement or a pharmacodynamic biomarker measured in people. possibly is false only when the abstract clearly reports none of these about this drug (it is about another drug or substance, the drug is only mentioned, or it reports only chemistry, in vitro work, clinical outcomes or epidemiology). When unsure, answer true."""

PREFILTER_SCHEMA = {"type": "object", "additionalProperties": False,
                    "properties": {"possibly": {"type": "boolean"}}, "required": ["possibly"]}

PREFILTER_TASK = llm.Task(name="literature_prefilter", prompt_version="v1", schema_version="v1", system=PREFILTER_SYSTEM,
                          schema=PREFILTER_SCHEMA, render=render, subject_type="moiety_record",
                          model="claude-haiku-4-5-20251001", effort=None, max_tokens=100)


def drug_records(cut: dict[int, int]) -> pd.DataFrame:
    """Every record of the drugs' version 3 retrievals at their cutoff: entity, record id, sources."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE want (moiety_id int, cutoff_year int) ON COMMIT DROP")
        execute_values(cur, "INSERT INTO want VALUES %s", list(cut.items()))
        cur.execute("""SELECT h.moiety_id, h.record_id, array_agg(h.source ORDER BY h.source)
                       FROM preclin.literature_v3_hit h JOIN want USING (moiety_id, cutoff_year) GROUP BY 1, 2""")
        return pd.DataFrame(cur.fetchall(), columns=["moiety_id", "record_id", "sources"])


def stored_papers(record_ids: list[str]) -> dict[str, tuple]:
    """record id -> (title, abstract, year) for PubMed papers already in public.publications and Europe PMC records."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT pmid, title, abstract, year FROM public.publications WHERE pmid = ANY(%s)",
                    ([r for r in record_ids if r.isdigit()],))
        out = {p: (t or "", a, y) for p, t, a, y in cur.fetchall()}
        cur.execute("SELECT record_id, title, abstract, year FROM preclin.literature_record WHERE record_id = ANY(%s)",
                    ([r for r in record_ids if not r.isdigit()],))
        out.update({r: (t or "", a, y) for r, t, a, y in cur.fetchall()})
    return out


def fetch_papers(pmids: list[str], store: bool) -> dict[str, tuple]:
    """PubMed abstracts by PMID, (title, abstract, year); stored in public.publications when store."""
    papers = efetch(pmids)
    if store and papers:
        with llm.connect() as conn, conn.cursor() as cur:
            execute_values(cur, """INSERT INTO public.publications (pmid, title, authors, journal, year, doi, abstract)
                                   VALUES %s ON CONFLICT (pmid) DO NOTHING""", papers)
            conn.commit()
    return {p[0]: (p[1] or "", p[6], p[4]) for p in papers}


def payload(names: list[str], targets: str, record_id: str, paper: tuple) -> dict:
    """The screen's input, in version 2's form so its decisions on the same PubMed abstracts are reused."""
    title, abstract, year = paper
    return {"drug_names": names, "targets": targets, "pmid": record_id, "title": title, "abstract": abstract,
            "year": year}


def drug_context(cut: dict[int, int]) -> tuple[dict, dict]:
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT moiety_id, names FROM preclin.literature_v3_search WHERE source = 'pubmed' AND moiety_id = ANY(%s)",
                    (sorted(cut),))
        names = dict(cur.fetchall())
        cur.execute("""SELECT mt.moiety_id, string_agg(DISTINCT t.symbol || ' (' || mt.action || ')', ', ')
                       FROM preclin.moiety_target mt JOIN public.targets t ON t.id = mt.target_id
                       WHERE mt.is_primary AND mt.moiety_id = ANY(%s) GROUP BY 1""", (sorted(cut),))
        targets = dict(cur.fetchall())
    return names, targets


def screen_items(cut: dict[int, int], log=print) -> dict[str, dict]:
    """Subject key (entity|record) -> screen payload for every record of the drugs (entity -> cutoff) that reaches
    the screen: all records of a drug with at most PREFILTER_ABOVE, else those the prefilter reads as possibly.
    Runs the prefilter where needed."""
    names, targets = drug_context(cut)
    recs = drug_records(cut)
    size = recs.groupby("moiety_id").size()
    large = set(size[size > PREFILTER_ABOVE].index)
    have = stored_papers(sorted(set(recs.record_id)))
    small_missing = sorted({r for m, r in zip(recs.moiety_id, recs.record_id) if m not in large and r not in have
                            and r.isdigit()}, key=int)
    log(f"drugs={len(cut)} records={len(recs)} large drugs={len(large)} "
        f"large-drug records={int(size[size > PREFILTER_ABOVE].sum())} small-drug pmids to fetch={len(small_missing)}")
    have.update(fetch_papers(small_missing, store=True))
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT moiety_id || '|' || record_id, possibly FROM preclin.literature_v3_prefilter")
        possibly = dict(cur.fetchall())
    big = recs[recs.moiety_id.isin(large)]
    todo = big[~(big.moiety_id.astype(str) + "|" + big.record_id).isin(possibly)]
    memory = fetch_papers(sorted({r for r in todo.record_id if r.isdigit() and r not in have}, key=int), store=False)
    papers = {**memory, **have}
    pre = {f"{m}|{r}": payload(names[m], targets.get(m, ""), r, papers[r])
           for m, r in zip(todo.moiety_id, todo.record_id) if r in papers and m in names}
    if pre:
        decided = [x for x in llm.decisions(llm.run(PREFILTER_TASK, pre)) if x[2] and "error" not in x[2]]
        with llm.connect() as conn, conn.cursor() as cur:
            execute_values(cur, """INSERT INTO preclin.literature_v3_prefilter (moiety_id, record_id, possibly, llm_decision_id)
                                   VALUES %s ON CONFLICT (moiety_id, record_id) DO UPDATE SET possibly = EXCLUDED.possibly,
                                     llm_decision_id = EXCLUDED.llm_decision_id""",
                           [(int(k.split("|")[0]), k.split("|", 1)[1], o["possibly"], did) for k, did, o in decided],
                           page_size=5000)
            conn.commit()
        possibly.update({k: o["possibly"] for k, _, o in decided})
    passed = sorted({r for m, r in zip(big.moiety_id, big.record_id) if possibly.get(f"{m}|{r}") and r.isdigit()
                     and r not in have}, key=int)
    if passed:  # a large literature's abstracts are stored only once they pass the prefilter
        with llm.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT pmid FROM public.publications WHERE pmid = ANY(%s)", (passed,))
            stored = {r[0] for r in cur.fetchall()}
        have.update(fetch_papers([p for p in passed if p not in stored], store=True))
    keep = [(m, r) for m, r in zip(recs.moiety_id, recs.record_id)
            if r in have and m in names and (m not in large or possibly.get(f"{m}|{r}"))]
    return {f"{m}|{r}": payload(names[m], targets.get(m, ""), r, have[r]) for m, r in keep}


def screen_drugs(cut: dict[int, int], log=print) -> int:
    """Prefilter and screen the drugs' records and store the screens; returns the records screened. Decisions are
    reused on the same input, so a rerun after an interruption only pays for what was not decided."""
    items = screen_items(cut, log)
    run_id = llm.run(task(), items)
    decided = [x for x in llm.decisions(run_id) if x[2] and "error" not in x[2]]
    to = survivors(sorted({int(k.split("|")[0]) for k, _, _ in decided}))
    with llm.connect() as conn, conn.cursor() as cur:  # an entity merged while the run was out stores under its survivor
        cur.execute("SELECT moiety_id FROM preclin.moiety WHERE moiety_id = ANY(%s)", (sorted(set(to.values())),))
        live = {r[0] for r in cur.fetchall()}
    rows = list({(to[int(k.split("|")[0])], k.split("|", 1)[1]): (
        to[int(k.split("|")[0])], k.split("|", 1)[1], o["original_data"], o["animal_disease"], o["modelled_diseases"],
        o["animal_healthy"], o["human_engagement"], o["species"] or None, o["detail"] or None, o["quote"] or None, did)
        for k, did, o in decided if to[int(k.split("|")[0])] in live}.values())
    with llm.connect() as conn, conn.cursor() as cur:
        execute_values(cur, """INSERT INTO preclin.literature_v3_screen (moiety_id, record_id, original_data, animal_disease,
                                 modelled_diseases, animal_healthy, human_engagement, species, detail, quote, llm_decision_id)
                               VALUES %s ON CONFLICT (moiety_id, record_id) DO UPDATE SET
                                 original_data = EXCLUDED.original_data, animal_disease = EXCLUDED.animal_disease,
                                 modelled_diseases = EXCLUDED.modelled_diseases, animal_healthy = EXCLUDED.animal_healthy,
                                 human_engagement = EXCLUDED.human_engagement, species = EXCLUDED.species,
                                 detail = EXCLUDED.detail, quote = EXCLUDED.quote,
                                 llm_decision_id = EXCLUDED.llm_decision_id""", rows, page_size=5000)
        conn.commit()
    log(f"records screened={len(items)} decided={len(decided)} run={run_id}")
    return len(items)


def screen(args) -> None:
    """Screen every record of the pilot's drugs that reaches the screen."""
    screen_drugs(drug_cutoffs(entries(args.entries)) if args.entries == "pilot" else cohort_drugs())


def chunks(cut: dict[int, int], sizes: dict[int, int]) -> list[dict[int, int]]:
    """The drugs split into groups of about CHUNK_RECORDS retrieved records (a drug is never split)."""
    out, cur, n = [], {}, 0
    for m in sorted(cut, key=lambda x: (-sizes.get(x, 0), x)):
        if cur and n + sizes.get(m, 0) > CHUNK_RECORDS:
            out.append(cur)
            cur, n = {}, 0
        cur[m] = cut[m]
        n += sizes.get(m, 0)
    return out + ([cur] if cur else [])


def run_cohort(args) -> None:
    """One worker of the cohort run: search, then prefilter and screen in chunks, the drugs with
    moiety_id % workers == worker. Progress goes to --log; every step resumes from what is stored."""
    def log(msg: str) -> None:
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} [w{args.worker}] {msg}"
        print(line, flush=True)
        with open(args.log, "a") as fh:
            fh.write(line + "\n")
    cut = {m: y for m, y in cohort_drugs().items() if m % args.workers == args.worker}
    if args.skip_pilot:  # the pilot screen decides these; a worker deciding them too would pay twice
        pilot = set(pilot_entries().moiety_id.astype(int))
        cut = {m: y for m, y in cut.items() if m not in pilot}
    log(f"cohort drugs for this worker={len(cut)}")
    search_drugs(cut, log)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT moiety_id, count(DISTINCT record_id) FROM preclin.literature_v3_hit
                       WHERE moiety_id = ANY(%s) GROUP BY 1""", (sorted(cut),))
        sizes = dict(cur.fetchall())
        cur.execute("SELECT DISTINCT moiety_id FROM preclin.literature_v3_screen WHERE moiety_id = ANY(%s)", (sorted(cut),))
        screened = {r[0] for r in cur.fetchall()}
    todo = {m: y for m, y in cut.items() if m not in screened and sizes.get(m)}
    groups = chunks(todo, sizes)
    log(f"to screen: drugs={len(todo)} records={sum(sizes.get(m, 0) for m in todo)} chunks={len(groups)}")
    for i, g in enumerate(groups, 1):
        n = screen_drugs(g, log)
        log(f"chunk {i}/{len(groups)} done: drugs={len(g)} screened={n}")
    log("worker done")


def prefilter_check(_args) -> None:
    """Give a seeded PREFILTER_CHECK of the prefiltered pilot records the full screen whatever the prefilter said,
    and record the prefilter's recall: the share of records the screen finds qualifying that it passed."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT moiety_id, record_id, possibly FROM preclin.literature_v3_prefilter ORDER BY 1, 2")
        pre = cur.fetchall()
    rng = np.random.default_rng(CHECK_SEED)
    pick = [pre[i] for i in sorted(rng.choice(len(pre), min(PREFILTER_CHECK, len(pre)), replace=False))]
    cut = drug_cutoffs(pilot_entries())
    names, targets = drug_context(cut)
    have = stored_papers([r for _, r, _ in pick])
    have.update(fetch_papers(sorted({r for _, r, _ in pick if r not in have and r.isdigit()}, key=int), store=False))
    items = {f"{m}|{r}": payload(names[m], targets.get(m, ""), r, have[r]) for m, r, _ in pick if r in have}
    full = {k: o for k, _, o in llm.decisions(llm.run(task(), items)) if o and "error" not in o}
    passed = {f"{m}|{r}": p for m, r, p in pick}
    qual = [k for k, o in full.items() if any(o[kind] for kind in KINDS)]
    result = {"sample": len(items), "qualifying_by_screen": len(qual),
              "passed_by_prefilter": int(sum(passed[k] for k in items)),
              "recall": float(np.mean([passed[k] for k in qual])) if qual else None,
              "by_kind": {kind: {"qualifying": int(sum(full[k][kind] for k in full)),
                                 "recall": float(np.mean([passed[k] for k in full if full[k][kind]]))
                                 if any(full[k][kind] for k in full) else None} for kind in KINDS}}
    record = json.load(open(GATE))
    record["v3_prefilter_check"] = result
    with open(GATE, "w") as fh:
        json.dump(record, fh, indent=2)
    print(json.dumps(result, indent=2))


DISEASE_SYSTEM = """You map the human disease an animal model was said to model to the MONDO disease ontology.

Pick from the candidate list:
- match "exact": a candidate names the disease itself (by label, synonym or definition).
- match "broader": no candidate names it, so pick the most specific candidate whose meaning contains it: its nearest parent disease or grouping (e.g. "chemotherapy-induced neuropathic pain" -> a peripheral neuropathy term). Prefer the narrowest candidate that still contains the whole disease.
- match "none" with mondo_id null: when no candidate contains it, or the text is not a human disease (a symptom alone, a physiological state, a procedure). Never pick MONDO:0000001 (disease) or another root grouping that names no body system or disease class."""

DISEASE_SCHEMA = {"type": "object", "additionalProperties": False,
                  "properties": {"match": {"type": "string", "enum": ["exact", "broader", "none"]},
                                 "mondo_id": {"type": ["string", "null"]}, "rationale": {"type": "string"}},
                  "required": ["match", "mondo_id", "rationale"]}


def render_disease(p: dict) -> str:
    cand = "\n".join(f"- {c['mondo_id']} | {c['label']} | is_a: {c['parents']} | synonyms: {', '.join(c['synonyms'])}"
                     + (f" | {c['definition']}" if c["definition"] else "") for c in p["candidates"])
    return f"Disease the model stands for: {p['name']}\n\nMONDO candidates:\n{cand or '(none retrieved)'}"


def validate_disease(p: dict, out: dict) -> None:
    if out["mondo_id"] and out["mondo_id"] not in {c["mondo_id"] for c in p["candidates"]}:
        raise ValueError(f"mondo_id {out['mondo_id']} not among candidates")
    if (out["match"] == "none") != (out["mondo_id"] is None):
        raise ValueError("match 'none' requires mondo_id null, and only then")


DISEASE_TASK = llm.Task(name="literature_model_disease_mondo", prompt_version="v1", schema_version="v1",
                        system=DISEASE_SYSTEM, schema=DISEASE_SCHEMA, render=render_disease, validate=validate_disease,
                        subject_type="modelled_disease", model="claude-sonnet-5", effort="low", max_tokens=1500)


def diseases(_args) -> None:
    """Map every modelled disease named by a screen and not yet mapped; candidates are retrieved terms, their
    parents and grandparents, as pipeline.indications offers for a condition with no term of its own."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT d FROM preclin.literature_v3_screen, unnest(modelled_diseases) d
                       WHERE d NOT IN (SELECT modelled_disease FROM preclin.literature_model_disease)""")
        todo = sorted(r[0] for r in cur.fetchall())
        index = MondoIndex(cur)
    items = {}
    for name, pool in zip(todo, index.search(todo) if todo else []):
        parents = [index.terms[p] for c in pool for p in index.parents.get(c["mondo_id"], []) if p in index.terms]
        grand = [index.terms[g] for c in parents for g in index.parents.get(c["mondo_id"], []) if g in index.terms]
        merged = {c["mondo_id"]: c for c in pool + parents + grand if c["mondo_id"] != "MONDO:0000001"}
        items[name] = {"name": name, "candidates": list(merged.values())[:3 * N_CANDIDATES]}
    if not items:
        print("modelled diseases to map=0")
        return
    decided = llm.decisions(llm.run(DISEASE_TASK, items))
    with llm.connect() as conn, conn.cursor() as cur:
        execute_values(cur, """INSERT INTO preclin.literature_model_disease (modelled_disease, mondo_id, match, llm_decision_id)
                               VALUES %s ON CONFLICT (modelled_disease) DO UPDATE SET mondo_id = EXCLUDED.mondo_id,
                                 match = EXCLUDED.match, llm_decision_id = EXCLUDED.llm_decision_id""",
                       [(k, o["mondo_id"], o["match"], did) for k, did, o in decided if o and "error" not in o])
        conn.commit()
    print(f"modelled diseases={len(items)} mapped={sum(1 for _, _, o in decided if o and o.get('mondo_id'))}")


def check(_args) -> None:
    """A second model relabels, per kind, a seeded CHECK_PER_KIND screened pilot records: half that the screen put
    in that kind, half that it left out (fewer when a side has fewer)."""
    cut = drug_cutoffs(pilot_entries())
    names, targets = drug_context(cut)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT moiety_id, record_id, animal_disease, animal_healthy, human_engagement
                       FROM preclin.literature_v3_screen WHERE moiety_id = ANY(%s)""", (sorted(cut),))
        rows = cur.fetchall()
    verdict = {f"{m}|{r}": dict(zip(KINDS, v)) for m, r, *v in rows}
    rng = np.random.default_rng(CHECK_SEED)
    keys = sorted(verdict)
    picked: set[str] = set()
    for kind in KINDS:
        for side in (True, False):
            pool = [k for k in keys if verdict[k][kind] is side]
            picked |= {pool[i] for i in rng.choice(len(pool), min(CHECK_PER_KIND // 2, len(pool)), replace=False)}
    papers = stored_papers(sorted({k.split("|", 1)[1] for k in picked}))
    items = {k: payload(names[int(k.split("|")[0])], targets.get(int(k.split("|")[0]), ""), k.split("|", 1)[1],
                        papers[k.split("|", 1)[1]]) for k in sorted(picked) if k.split("|", 1)[1] in papers}
    run_id = llm.run(task(model="claude-opus-5-5", suffix="_check"), items)
    print(f"check sample={len(items)} decided={len(llm.decisions(run_id))} run={run_id}", flush=True)


def kappa(a: list[bool], b: list[bool]) -> float | None:
    a, b = np.array(a, bool), np.array(b, bool)
    if not len(a):
        return None
    po = float((a == b).mean())
    pe = float(a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean()))
    return None if pe == 1 else (po - pe) / (1 - pe)


def agreement() -> dict[str, dict]:
    """Kind -> agreement of the screen with the check model on the screened version 3 records both read."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT moiety_id || '|' || record_id FROM preclin.literature_v3_screen")
        screened = {r[0] for r in cur.fetchall()}
        cur.execute("""SELECT DISTINCT ON (subject_key, task) subject_key, task, parsed_output
                       FROM pv_evidence.llm_decision
                       WHERE task IN ('literature_drug_screen', 'literature_drug_screen_check')
                         AND validation_status = 'validated'
                       ORDER BY subject_key, task, created_at DESC""")
        by: dict = {}
        for key, tname, out_ in cur.fetchall():
            if key in screened:
                by.setdefault(key, {})[tname] = out_
    pairs = [v for v in by.values() if len(v) == 2]
    out = {}
    for kind in KINDS:
        a = [v["literature_drug_screen"][kind] for v in pairs]
        b = [v["literature_drug_screen_check"][kind] for v in pairs]
        out[kind] = {"pairs": len(a), "kappa": kappa(a, b),
                     "agreement": float(np.mean(np.array(a) == np.array(b))) if a else None,
                     "positives_screen": int(sum(a)), "positives_check": int(sum(b))}
    return out


def entry_matches(e: pd.DataFrame, q: pd.DataFrame, related) -> list[set[str]]:
    """For each entry and kind, the qualifying abstracts dated by its cutoff (q: entity, pmid, year, kind,
    mondo_id of a modelled disease for animal_disease). related(d) is the set of MONDO terms counting for d."""
    by = {m: g for m, g in q.groupby("moiety_id")}
    empty = q.iloc[:0]
    out = []
    for r in e.itertuples(index=False):
        g = by.get(r.moiety_id, empty)
        g = g[g.year.isna() | (g.year <= r.cutoff_year)]
        rel = related(r.mondo_id)
        for k in KINDS:
            if k == "human_engagement" and r.phase < 2:
                continue
            gk = g[g.kind == k]
            if k == "animal_disease":
                gk = gk[gk.mondo_id.isin(rel)]
            out.append({"moiety_id": r.moiety_id, "mondo_id": r.mondo_id, "phase": r.phase, "kind": k,
                        "pmids": sorted(set(gk.pmid))})
    return out


RECORD_YEAR = """(SELECT year FROM public.publications WHERE pmid = s.record_id
                UNION ALL SELECT year FROM preclin.literature_record WHERE record_id = s.record_id LIMIT 1)"""


def qualifying(without: str | None = None) -> pd.DataFrame:
    """Entity, record, publication year, kind and (for animal models) mapped MONDO term of every qualifying screen;
    without a source, the records only that source retrieved are left out."""
    only = "" if not without else f"""AND EXISTS (SELECT 1 FROM preclin.literature_v3_hit h WHERE h.moiety_id = s.moiety_id
                                       AND h.record_id = s.record_id AND h.source <> '{without}')"""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute(f"""SELECT s.moiety_id, s.record_id, {RECORD_YEAR}, 'animal_disease', md.mondo_id
                        FROM preclin.literature_v3_screen s CROSS JOIN unnest(s.modelled_diseases) d
                        JOIN preclin.literature_model_disease md ON md.modelled_disease = d
                        WHERE s.animal_disease AND md.mondo_id IS NOT NULL {only}
                        UNION ALL
                        SELECT s.moiety_id, s.record_id, {RECORD_YEAR}, k.kind, NULL
                        FROM preclin.literature_v3_screen s
                        CROSS JOIN LATERAL (VALUES ('animal_healthy', s.animal_healthy),
                                                   ('human_engagement', s.human_engagement)) k(kind, ok)
                        WHERE k.ok {only}""")
        return pd.DataFrame(cur.fetchall(), columns=["moiety_id", "pmid", "year", "kind", "mondo_id"])


def record_dois() -> dict[str, str]:
    """Record id -> lower-case DOI, for matching reference studies outside PubMed."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT s.record_id, lower(coalesce(p.doi, r.doi)) FROM preclin.literature_v3_screen s
                       LEFT JOIN public.publications p ON p.pmid = s.record_id
                       LEFT JOIN preclin.literature_record r ON r.record_id = s.record_id
                       WHERE coalesce(p.doi, r.doi) IS NOT NULL""")
        return dict(cur.fetchall())


def related_terms():
    from report.disease_match import Mondo
    from report.section3 import Neighbourhood
    nb = Neighbourhood(Mondo())
    return lambda d: nb.terms(d, RELATED)


def found(e: pd.DataFrame) -> pd.DataFrame:
    """Entry x kind: the qualifying abstracts dated no later than the cutoff."""
    return pd.DataFrame(entry_matches(e, qualifying(), related_terms()))


def reference_rows(ref: list[dict], e: pd.DataFrame) -> pd.DataFrame:
    """One row per qualifying study the reference agents listed: entry, kind, PMID (None when the study
    is not in PubMed) and venue. Studies dated after the entry's cutoff year are dropped."""
    cut = {(int(r.moiety_id), r.mondo_id, int(r.phase)): int(r.cutoff_year) for r in e.itertuples()}
    rows = []
    for entry in ref:
        key = (int(entry["moiety_id"]), entry["mondo_id"], int(entry["phase"]))
        for s in entry.get("studies") or []:
            if s.get("kind") not in KINDS or (s.get("year") is not None and int(s["year"]) > cut[key]):
                continue
            if s["kind"] == "human_engagement" and key[2] < 2:
                continue
            rows.append({"moiety_id": key[0], "mondo_id": key[1], "phase": key[2], "kind": s["kind"],
                         "pmid": str(s["pmid"]) if s.get("pmid") else None, "venue": s.get("venue"),
                         "doi": str(s["doi"]).lower().removeprefix("https://doi.org/") if s.get("doi") else None})
    return pd.DataFrame(rows, columns=["moiety_id", "mondo_id", "phase", "kind", "pmid", "venue", "doi"])


def misses(rk: pd.DataFrame, related) -> dict[str, int]:
    """Why each PubMed-indexed reference study of one kind was or was not found: found (and whether only Firecrawl
    retrieved it); screened in but its modelled disease mapped outside the entry's (animal_disease); screened out;
    left out by the prefilter; retrieved but not screened; or not retrieved."""
    out: dict[str, int] = {}
    with llm.connect() as conn, conn.cursor() as cur:
        for r in rk.dropna(subset=["pmid"]).itertuples():
            cur.execute("""SELECT array_agg(DISTINCT h.source), bool_or(f.possibly) IS FALSE,
                                  c.animal_disease, c.animal_healthy, c.human_engagement,
                                  (SELECT array_agg(md.mondo_id) FROM unnest(c.modelled_diseases) d
                                   JOIN preclin.literature_model_disease md ON md.modelled_disease = d)
                           FROM preclin.literature_v3_hit h
                           LEFT JOIN preclin.literature_v3_prefilter f ON f.moiety_id = h.moiety_id AND f.record_id = h.record_id
                           LEFT JOIN preclin.literature_v3_screen c ON c.moiety_id = h.moiety_id AND c.record_id = h.record_id
                           WHERE h.moiety_id = %s AND h.record_id = %s
                           GROUP BY c.animal_disease, c.animal_healthy, c.human_engagement, c.modelled_diseases""",
                        (int(r.moiety_id), r.pmid))
            row = cur.fetchone()
            if row is None:
                why = "not_retrieved"
            elif row[1]:
                why = "prefiltered_out"
            elif row[2] is None:
                why = "unscreened"
            elif not dict(zip(KINDS, row[2:5]))[r.kind]:
                why = "screened_out"
            elif r.kind == "animal_disease" and not set(row[5] or []) & related(r.mondo_id):
                why = "screened_in_other_disease"
            else:
                why = "found_by_firecrawl_only" if set(row[0]) == {"firecrawl"} else "found"
            out[why] = out.get(why, 0) + 1
    return out


def evaluate(e: pd.DataFrame, ref: list[dict], f: pd.DataFrame, agree: dict, related,
             f_without: pd.DataFrame | None = None) -> dict:
    """Recall, agreement and coverage of one set of pilot entries against its blind reference. A reference study
    is found when its PMID, or its DOI, is among the qualifying records of its entry and kind; f_without is the
    same without the records only Firecrawl retrieved."""
    rr = reference_rows(ref, e)
    keys = ["moiety_id", "mondo_id", "phase"]
    dois = record_dois()

    def recall_of(frame: pd.DataFrame, kind: str, rk: pd.DataFrame) -> tuple[list[bool], dict]:
        on_ref = frame.merge(e[keys], on=keys)
        got = {(r.moiety_id, r.mondo_id, r.phase): set(r.pmids) for r in on_ref[on_ref.kind == kind].itertuples()}
        got_doi = {k: {dois[p] for p in v if p in dois} for k, v in got.items()}
        hit = [(p is not None and p in got.get((m, d, ph), set())) or (x is not None and x in got_doi.get((m, d, ph), set()))
               for m, d, ph, p, x in zip(rk.moiety_id, rk.mondo_id, rk.phase, rk.pmid, rk.doi)]
        return hit, got

    result: dict = {"reference_entries": len(ref), "kinds": {}}
    for kind in KINDS:
        rk = rr[rr.kind == kind]
        hit, got = recall_of(f, kind, rk)
        in_pm = rk.pmid.notna().to_numpy()
        with_ref = set(rk[keys].itertuples(index=False, name=None))
        none_ref = [k for k in got if k not in with_ref]
        entry_recall = [bool(got.get(k)) for k in with_ref]
        k_out = {
            "reference_studies": len(rk), "reference_studies_in_pubmed": int(in_pm.sum()),
            "reference_studies_by_venue": rk.venue.fillna("unknown").value_counts().to_dict(),
            "recall": float(np.mean(hit)) if hit else None,
            "recall_pubmed_indexed": float(np.mean(np.array(hit)[in_pm])) if in_pm.any() else None,
            "reference_entries_with_study": len(with_ref), "entries_judged": len(got),
            "entry_recall": float(np.mean(entry_recall)) if entry_recall else None,
            "pipeline_none_when_reference_none": float(np.mean([not got[k] for k in none_ref])) if none_ref else None,
            "pubmed_reference_studies": misses(rk, related), "check": agree.get(kind)}
        if f_without is not None:
            hit_wo, _ = recall_of(f_without, kind, rk)
            k_out["recall_without_firecrawl"] = float(np.mean(hit_wo)) if hit_wo else None
            k_out["recall_pubmed_indexed_without_firecrawl"] = \
                float(np.mean(np.array(hit_wo)[in_pm])) if in_pm.any() else None
        result["kinds"][kind] = k_out
    return result


def gate(args) -> None:
    """Score the pilot rows --rows against the reference files <PREFIX>{1..4}_result.json; record it in GATE
    under --label, with Phase 2 coverage over all 300 pilot entries and the plan's gates applied."""
    e = pilot_entries()
    lo, hi = map(int, args.rows.split("-"))
    rows_e = e[e.row.between(lo, hi)]
    ref: list[dict] = []
    for i in range(1, 5):
        with open(f"{args.reference}{i}_result.json") as fh:
            ref += json.load(fh)
    related = related_terms()
    f = pd.DataFrame(entry_matches(e, qualifying(), related))
    f_without = pd.DataFrame(entry_matches(e, qualifying(without="firecrawl"), related))
    agree = agreement()
    result = evaluate(rows_e, ref, f, agree, related, f_without) | {"rows": args.rows, "reference": args.reference}
    for kind in KINDS:
        fk = f[(f.kind == kind) & (f.phase == 2)]
        cov = float((fk.pmids.str.len() > 0).mean()) if len(fk) else None
        k = result["kinds"][kind]
        k["pilot_entries_with_any"] = int((f[f.kind == kind].pmids.str.len() > 0).sum())
        k["pilot_entries"] = int((f.kind == kind).sum())
        k["phase2_coverage"] = cov
        kap = (agree.get(kind) or {}).get("kappa")
        k["passes"] = bool(k["recall"] is not None and k["recall"] >= GATES["recall"] and kap is not None
                           and kap >= GATES["kappa"] and cov is not None and cov >= GATES["phase2_coverage"])
    with open(GATE) as fh:
        record = json.load(fh)
    if "v1" not in record:
        record = {"v1": record}
    record[args.label] = {"gates": GATES, **result}
    with open(GATE, "w") as fh:
        json.dump(record, fh, indent=2)
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in (("search", search), ("screen", screen)):
        p = sub.add_parser(name)
        p.add_argument("--entries", choices=("pilot", "cohort"), default="cohort")
        p.set_defaults(fn=fn)
    sub.add_parser("diseases").set_defaults(fn=diseases)
    sub.add_parser("check").set_defaults(fn=check)
    sub.add_parser("prefilter-check").set_defaults(fn=prefilter_check)
    rc = sub.add_parser("run-cohort")
    rc.add_argument("--worker", type=int, required=True)
    rc.add_argument("--workers", type=int, required=True)
    rc.add_argument("--log", required=True)
    rc.add_argument("--skip-pilot", action="store_true", help="leave the pilot's drugs to the pilot screen")
    rc.set_defaults(fn=run_cohort)
    fc = sub.add_parser("firecrawl")
    fc.add_argument("--mode", choices=("search", "related"), required=True)
    fc.add_argument("--entries", choices=("pilot", "cohort"), default="pilot")
    fc.set_defaults(fn=firecrawl)
    g = sub.add_parser("gate")
    g.add_argument("--reference", required=True, help="path prefix of the four reference files, before {1..4}_result.json")
    g.add_argument("--rows", required=True, help="pilot sample rows scored, e.g. 101-200")
    g.add_argument("--label", default="v3", help="key of this evaluation in the gate record")
    g.set_defaults(fn=gate)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
