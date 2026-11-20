"""What first proposed each target-disease hypothesis, read from sources dated before its first entry (issue #146,
steps 2 to 5). Commands, registered on pipeline.target_disease:

    search   retrieve PubMed and Europe PMC records naming the gene and the disease, dated before the pair's
             cutoff year (the year of its first Phase 2 or 3 entry), into preclin.target_disease_search and
             preclin.target_disease_source; shared with the target-literature screen (#154)
    label    an LLM reads the earliest and latest records (and the web, under the same date rule) and labels the
             origin, its grade and the first drug's discovery route (preclin.target_disease_origin, basis labelled)
    check    a second model verifies each graded label's quote, date and reading; a failed label becomes unclear
    blind    a second model labels the hand-check sets from the records alone, for comparison with the reader
    sample   draw the pilot of 100 pairs (50 with a settled "not causal" stop, 50 without) and the two hand-check sets
    package  write the reader's page for one hand-check set
    gate     score the pilot against the reader's sheet: agreement and coverage gates
    summary  counts of labels, grades, check outcomes and coverage

Every source must be dated before the cutoff year. Every model pass goes through pipeline.llm. Run order for a pair
set: search, label, check, blind, gate; `label` rewrites its rows as not_checked, so `check` always follows it.
"""
from __future__ import annotations

import os
import re
from collections.abc import Callable

import pandas as pd
from psycopg2.extras import execute_values

from pipeline import attribution, literature, llm
from pipeline.literature import names_clause
from pipeline.stop_causes import BLOCKED_DOMAINS
from report import frame
from report.windows import SECTION1

ORIGINS = ["human_genetics", "tumour_genetics", "diseased_tissue", "mouse_genetics", "curated_pathway", "cell_screen",
           "earlier_drug_other_disease", "observational_biomarker", "human_cell_perturbation",
           "animal_model_pharmacology", "clinical_observation", "phenotypic_screen", "unclear"]
GRADES = ["stated", "pattern", "none"]
ROUTES = ["phenotypic_screen", "target_screen", "de_novo_design", "derived_from_active", "repurposed_drug", "unclear"]

MAX_GENE_NAMES = 16
MAX_DISEASE_NAMES = 20
BUNDLE_EARLIEST = 25  # records shown to the model and the reader: the earliest by (year, id) ...
BUNDLE_LATEST = 15  # ... and the latest before the cutoff
ABSTRACT_CHARS = 1500

PILOT_CSV = os.path.join(frame.REPO, "report", "audits", "target_origin_pilot.csv")
PAIR_SETS = ["pilot", "set_a", "set_b", "window", "all"]

SEARCH_METHOD = "target_origin_search@v1"
ORIGIN_SERVICES = ("pubmed", "europepmc")  # the origin search's services; firecrawl rows belong to #154
DELETE_SOURCES = ("DELETE FROM preclin.target_disease_source WHERE (ensembl_id, mondo_id) = (%s, %s) "
                  "AND service IN %s")
DELETE_SEARCH = ("DELETE FROM preclin.target_disease_search WHERE (ensembl_id, mondo_id) = (%s, %s) "
                 "AND service IN %s")
SEARCHED_SQL = "SELECT DISTINCT ensembl_id, mondo_id FROM preclin.target_disease_search WHERE service IN %s"
SOURCES_SQL = """SELECT ensembl_id, mondo_id, record_id, service, title, abstract, year, rank
                 FROM preclin.target_disease_source WHERE (ensembl_id, mondo_id) IN %s AND service IN %s
                 ORDER BY rank"""
COVERED_SQL = ("SELECT ensembl_id, mondo_id, count(*) AS records FROM preclin.target_disease_source "
               "WHERE (ensembl_id, mondo_id) IN %s AND service IN %s GROUP BY 1, 2")
SEARCH_DESCRIPTION = f"""For each target-disease pair (preclin.target_disease): PubMed (esearch, efetch) and Europe PMC
(records outside MEDLINE with an abstract) for titles or abstracts naming the gene (HGNC symbol first, then its name,
the target name, the UniProt and HGNC protein names, and aliases passing pipeline.literature.usable, at most
{MAX_GENE_NAMES}) and the disease (MONDO label
and its synonyms, shortest first, at most {MAX_DISEASE_NAMES}), dated 1900 to the year before the pair's first entry. Reviews are kept. A record without a year, or dated in or after the cutoff year, is
dropped. Every remaining record is stored with its rank by (year, record_id)."""


def key(ensembl_id: str, mondo_id: str) -> str:
    return f"{ensembl_id}|{mondo_id}"


def split_key(k: str) -> tuple[str, str]:
    e, m = k.split("|")[:2]
    return e, m


# --- names and queries ---

def disease_usable(name: str) -> bool:
    """A disease name a paper could use: 4 to 60 characters, at most six words, no brackets or punctuation."""
    return name_usable(name)


def _dedupe(names: list[str]) -> list[str]:
    seen: set[str] = set()
    out = []
    for n in names:
        n = n.strip()
        if n and n.lower() not in seen:
            seen.add(n.lower())
            out.append(n)
    return out


def name_usable(name: str) -> bool:
    """A gene or protein name a paper could use: 4 to 60 characters, at most six words, no brackets or punctuation
    (HGNC names of the form "X, receptor" are dropped; a paper writes neither half alone)."""
    return 4 <= len(name) <= 60 and len(name.split()) <= 6 and not any(c in name for c in "()[]{},;^")


UNIPROT_URL = "https://rest.uniprot.org/uniprotkb/{acc}.json?fields=protein_name"
HGNC_URL = "https://rest.genenames.org/fetch/symbol/{symbol}"
_protein_names: dict[str, list[str]] = {}


def uniprot_names(doc: dict) -> list[str]:
    """Protein names in a UniProtKB entry: the recommended full and short names, then each alternative name's."""
    desc = doc.get("proteinDescription", {})
    out = []
    for block in [desc.get("recommendedName", {}), *desc.get("alternativeNames", [])]:
        if block.get("fullName", {}).get("value"):
            out.append(block["fullName"]["value"])
        out += [x["value"] for x in block.get("shortNames", []) if x.get("value")]
    return out


def hgnc_names(doc: dict) -> list[str]:
    """Alias and previous names of an HGNC record (its alias_name and prev_name fields)."""
    return list(doc.get("alias_name", []) or []) + list(doc.get("prev_name", []) or [])


def protein_names(symbol: str, uniprot_ids: list[str]) -> list[str]:
    """Protein names from UniProt (first accession) and HGNC's REST service, cached per process; empty when a service
    fails, which is logged."""
    if symbol in _protein_names:
        return _protein_names[symbol]
    names: list[str] = []
    try:
        if uniprot_ids:
            names += uniprot_names(literature.request("GET", UNIPROT_URL.format(acc=uniprot_ids[0]), log).json())
        docs = literature.request("GET", HGNC_URL.format(symbol=symbol), log,
                                  headers={"Accept": "application/json"}).json().get("response", {}).get("docs", [])
        if docs:
            names += hgnc_names(docs[0])
    except (literature.SourceDown, ValueError) as e:
        log(f"protein names for {symbol}: {e}")
    _protein_names[symbol] = names
    return names


def gene_names(symbol: str, hgnc: pd.DataFrame, target_name: str | None, protein: list[str] = (),
               exclude: set[str] = frozenset()) -> list[str]:
    """The symbol first (when four characters or longer, or the only name); then the HGNC name, the target name and
    the protein names (UniProt, HGNC alias and previous names) that pass name_usable and are not in exclude (lower-
    cased disease labels: HGNC lists "Kennedy disease" as an alias name of AR), then previous and alias symbols that
    pass pipeline.literature.usable; at most MAX_GENE_NAMES."""
    names = [n for n in [*(hgnc.name if not hgnc.empty else []), target_name, *protein]
             if n and name_usable(n) and n.lower() not in exclude]
    aliases: list[str] = []
    for r in hgnc.itertuples():
        aliases += list(r.prev_symbols or []) + list(r.alias_symbols or [])
    aliases = [a for a in aliases if a and literature.usable(a)]
    # a symbol of three characters or fewer (AR, KIT, C5) is an English word or an abbreviation of something else
    # as often as the gene: it is searched only when no other name exists
    lead = [symbol] if len(symbol) >= 4 or not (names or aliases) else []
    return _dedupe(lead + names + aliases)[:MAX_GENE_NAMES]


def disease_names(label: str, synonyms: list[str]) -> list[str]:
    """The label first; then its MONDO synonyms that pass disease_usable, shortest first; at most MAX_DISEASE_NAMES.
    Terms close to the disease (the evidence lines' Lin 0.8 neighbourhood) are not searched: that neighbourhood puts
    lung cancer beside breast cancer, which is right for matching evidence rows and wrong for naming a disease."""
    rest = sorted((n for n in _dedupe(list(synonyms)) if disease_usable(n) and n.lower() != label.lower()), key=len)
    return [label] + rest[:MAX_DISEASE_NAMES - 1]


def pair_term(genes: list[str], diseases: list[str]) -> Callable[[str, str], str]:
    """An esearch term builder for a date span: gene names AND disease names in title or abstract; reviews kept."""
    return lambda lo, hi: f'{names_clause(genes)} AND {names_clause(diseases)} AND ("{lo}"[dp] : "{hi}"[dp])'


def pair_epmc_query(genes: list[str], diseases: list[str], cutoff_year: int) -> str:
    """Europe PMC records outside MEDLINE with an abstract, naming the gene and the disease, dated before the cutoff."""
    def clause(names: list[str]) -> str:
        return "(" + " OR ".join(f'TITLE_ABS:"{n}"' for n in names) + ")"
    return (f"{clause(genes)} AND {clause(diseases)} AND PUB_YEAR:[1900 TO {cutoff_year - 1}] "
            "AND NOT SRC:MED AND HAS_ABSTRACT:Y")


# --- records ---

def pubmed_rows(fetched: list[tuple], cutoff_year: int) -> list[dict]:
    """Rows from pipeline.attribution.efetch tuples (pmid, title, first author, journal, year, doi, abstract), dropping
    records without a year or dated in or after the cutoff year."""
    return [{"record_id": f"PMID:{pmid}", "service": "pubmed", "title": title or "", "abstract": abstract,
             "year": int(year), "doi": doi}
            for pmid, title, _author, _journal, year, doi, abstract in fetched
            if year is not None and int(year) < cutoff_year]


def epmc_rows(records: list[tuple], cutoff_year: int) -> list[dict]:
    """Rows from pipeline.literature.epmc_record tuples (record_id, source, title, abstract, year, doi), same rule."""
    return [{"record_id": rid, "service": "europepmc", "title": title or "", "abstract": abstract, "year": int(year),
             "doi": doi}
            for rid, _source, title, abstract, year, doi in records if year is not None and int(year) < cutoff_year]


def ranked(rows: list[dict]) -> list[dict]:
    """Rows ordered by (year, record_id) with a 1-based rank; a record id appears once."""
    seen: set[str] = set()
    unique = []
    for r in rows:
        if r["record_id"] not in seen:
            seen.add(r["record_id"])
            unique.append(r)
    out = sorted(unique, key=lambda r: (r["year"], r["record_id"]))
    return [{**r, "rank": i + 1} for i, r in enumerate(out)]


def bundle(rows: list[dict]) -> list[dict]:
    """What the model and the reader see: the earliest BUNDLE_EARLIEST and the latest BUNDLE_LATEST ranked rows, with
    abstracts cut to ABSTRACT_CHARS."""
    rows = sorted(rows, key=lambda r: r["rank"])
    chosen = rows[:BUNDLE_EARLIEST] + rows[max(BUNDLE_EARLIEST, len(rows) - BUNDLE_LATEST):]
    return [{**r, "abstract": (r["abstract"] if isinstance(r["abstract"], str) else "")[:ABSTRACT_CHARS]}
            for r in chosen]


def records_from(df: pd.DataFrame) -> list[dict]:
    """Rows of a source frame as dicts, with a missing abstract or doi as None rather than NaN."""
    return df.astype(object).where(df.notna(), None).to_dict("records")


# --- pair sets ---

def pair_frame(which: str) -> pd.DataFrame:
    """The pairs a command works on: ensembl_id, mondo_id, symbol, first_entry, cutoff_year, validated_at_entry
    (and group, hand_check_set for the pilot sets)."""
    hub = frame.query("SELECT ensembl_id, mondo_id, symbol, first_entry, validated_at_entry FROM preclin.target_disease")
    hub["first_entry"] = pd.to_datetime(hub.first_entry)
    hub["cutoff_year"] = hub.first_entry.dt.year
    if which == "all":
        return hub
    if which == "window":
        return hub[hub.first_entry.between(pd.Timestamp(SECTION1[0]), pd.Timestamp(SECTION1[1]))].reset_index(drop=True)
    pilot = pd.read_csv(PILOT_CSV, dtype=str)
    if which == "set_a":
        pilot = pilot[pilot.hand_check_set == "a"]
    elif which == "set_b":
        pilot = pilot[pilot.hand_check_set == "b"]
    elif which != "pilot":
        raise ValueError(f"unknown pair set {which!r}; one of {PAIR_SETS}")
    return hub.merge(pilot[["ensembl_id", "mondo_id", "group", "hand_check_set"]], on=["ensembl_id", "mondo_id"])


# --- search ---

def log(msg: str) -> None:
    print(msg, flush=True)


def mondo_labels() -> dict[str, str]:
    t = frame.query("SELECT term_id, label FROM preclin.ontology_term WHERE ontology = 'MONDO'")
    return dict(zip(t.term_id, t.label))


def pair_names(ensembl_id: str, symbol: str, mondo_id: str, labels: dict[str, str]) -> tuple[list[str], list[str]]:
    hgnc = frame.query("SELECT symbol, name, prev_symbols, alias_symbols, uniprot_ids FROM preclin.hgnc_gene "
                       "WHERE ensembl_id = %s", (ensembl_id,))
    accessions = [a for r in hgnc.itertuples() for a in (r.uniprot_ids or [])]
    tname = frame.query("SELECT min(name) AS name FROM public.targets WHERE ensembl_id = %s", (ensembl_id,))
    target_name = tname.name[0] if len(tname) and isinstance(tname.name[0], str) else None
    term = frame.query("SELECT label, synonyms FROM preclin.ontology_term WHERE term_id = %s", (mondo_id,))
    label = term.label[0] if len(term) else labels.get(mondo_id, mondo_id)
    synonyms = list(term.synonyms[0] or []) if len(term) else []
    diseases = {x.lower() for x in labels.values()}
    return (gene_names(symbol, hgnc, target_name, protein_names(symbol, accessions), exclude=diseases),
            disease_names(label, synonyms))


def search_pair(cur, row, labels: dict[str, str], max_records: int | None) -> tuple[int, int, int]:
    """Search both services for one pair and replace its rows; returns (PubMed hits, Europe PMC hits, rows stored)."""
    cutoff = int(row.cutoff_year)
    genes, diseases = pair_names(row.ensembl_id, row.symbol, row.mondo_id, labels)
    term = pair_term(genes, diseases)
    pm_query, pm_hits, pmids = literature.pubmed_ids(genes, cutoff - 1, term=term)
    # the same count without the symbol: when far below pm_hits, the symbol (an English word?) floods the search
    without = [g for g in genes if g != row.symbol]
    pm_hits_without = (literature.pubmed_count(pair_term(without, diseases)("1900", str(cutoff - 1)))
                       if without and row.symbol in genes else None)
    pm_rows = pubmed_rows(attribution.efetch(pmids), cutoff) if pmids else []
    ep_query = pair_epmc_query(genes, diseases, cutoff)
    _, ep_hits, records = literature.epmc_records(genes, cutoff - 1, log, query=ep_query)
    ep_rows = epmc_rows(records, cutoff)
    if max_records is not None:
        pm_rows = sorted(pm_rows, key=lambda r: (r["year"], r["record_id"]))[:max_records]
        ep_rows = sorted(ep_rows, key=lambda r: (r["year"], r["record_id"]))[:max_records]
    rows = ranked(pm_rows + ep_rows)
    pair = (row.ensembl_id, row.mondo_id)
    cur.execute(DELETE_SOURCES, (*pair, ORIGIN_SERVICES))
    cur.execute(DELETE_SEARCH, (*pair, ORIGIN_SERVICES))
    execute_values(cur, """INSERT INTO preclin.target_disease_search
                             (ensembl_id, mondo_id, service, cutoff_year, gene_names, disease_names, query, n_hits,
                              n_hits_without_symbol)
                           VALUES %s""",
                   [(*pair, "pubmed", cutoff, genes, diseases, pm_query, int(pm_hits), pm_hits_without),
                    (*pair, "europepmc", cutoff, genes, diseases, ep_query, int(ep_hits), None)])
    if rows:
        execute_values(cur, """INSERT INTO preclin.target_disease_source
                                 (ensembl_id, mondo_id, record_id, service, title, abstract, year, doi, rank)
                               VALUES %s""",
                       [(*pair, r["record_id"], r["service"], r["title"], r["abstract"], r["year"], r["doi"], r["rank"])
                        for r in rows], page_size=2000)
    return int(pm_hits), int(ep_hits), len(rows)


def searched() -> set[tuple[str, str]]:
    s = frame.query(SEARCHED_SQL, (ORIGIN_SERVICES,))
    return set(zip(s.ensembl_id, s.mondo_id))


def search(args) -> None:
    pairs = pair_frame(args.pairs)
    done = set() if args.redo else searched()
    todo = pairs[[(e, m) not in done for e, m in zip(pairs.ensembl_id, pairs.mondo_id)]]
    log(f"{len(pairs)} pairs in {args.pairs}; {len(todo)} to search")
    labels = mondo_labels()
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, SEARCH_METHOD, "Pre-entry sources per target-disease pair", SEARCH_DESCRIPTION,
                          ["PubMed", "Europe PMC", "preclin.target_disease", "preclin.hgnc_gene", "public.targets",
                           "preclin.ontology_term", "MONDO"],
                          {"max_gene_names": MAX_GENE_NAMES, "max_disease_names": MAX_DISEASE_NAMES,
                           "date_rule": "publication year < year of first_entry", "reviews": "kept",
                           "max_records": args.max_records})
        conn.commit()
    failed, stored = 0, 0
    with llm.connect() as conn, conn.cursor() as cur:
        for i, row in enumerate(todo.itertuples(), 1):
            try:
                pm, ep, n = search_pair(cur, row, labels, args.max_records)
                conn.commit()
            except (literature.SourceDown, RuntimeError) as e:
                conn.rollback()
                failed += 1
                log(f"[{i}/{len(todo)}] {row.symbol} x {labels.get(row.mondo_id, row.mondo_id)} FAILED: {e}")
                continue
            stored += n
            log(f"[{i}/{len(todo)}] {row.symbol} x {labels.get(row.mondo_id, row.mondo_id)} cutoff {row.cutoff_year}: "
                f"pubmed {pm} europepmc {ep} stored {n}")
    log(f"searched {len(todo) - failed} pairs, {stored:,} records stored, {failed} failed")




# --- labelling ---

DEFINITIONS = """- human_genetics: germline variants link the target to the disease (GWAS, gene burden, Mendelian)
- tumour_genetics: the gene is recurrently mutated in the cancer
- diseased_tissue: the gene's RNA or protein level differs in diseased tissue
- mouse_genetics: knocked-out or mutant mice show the disease
- curated_pathway: a curated pathway shows a disease mutation disrupting the target
- cell_screen: a gene-knockout screen in human cells
- earlier_drug_other_disease: a drug on the target was approved for an unrelated disease
- observational_biomarker: the target or its product in patients' blood, another fluid or on imaging tracks the disease
- human_cell_perturbation: perturbing the target in human cells or tissue changes a disease phenotype
- animal_model_pharmacology: modulating the target by means other than genetics changes an animal model of the disease
- clinical_observation: an effect seen in people, such as a side effect
- phenotypic_screen: a molecule found without a target hypothesis came first
- unclear: no source settles it"""

# The evidence chart's line that each origin kind answers "present before entry?" for (report.evidence_lines; the
# owner's one-list decision of 2026-11-20 on #146): one list of target-evidence kinds, used two ways. None: no chart
# line. The CHART_LINE_PENDING kinds get their lines from #154, under these names.
CHART_LINE = {"human_genetics": "g3", "tumour_genetics": "somatic", "diseased_tissue": "expression",
              "mouse_genetics": "altered_animal", "curated_pathway": "reactome", "cell_screen": "crispr",
              "earlier_drug_other_disease": "approved_unrelated_only", "observational_biomarker": None,
              "human_cell_perturbation": None, "animal_model_pharmacology": None, "clinical_observation": None,
              "phenotypic_screen": None, "unclear": None}
CHART_LINE_PENDING = ("observational_biomarker", "human_cell_perturbation", "animal_model_pharmacology",
                      "clinical_observation")

GRADE_RULE = """stated: a source says why the target was chosen for the disease (a rationale in an introduction or discussion, a
review written before the cutoff, a patent's background). pattern: no source says so, but a source shows the defining
observation of the category, published before any other kind of evidence for the pair. none: the sources would leave
the origin to inference; then the origin is unclear, the quote is empty and the sources are empty. A label graded
stated or pattern carries a verbatim quote from one of its cited sources."""

ROUTE_DEFINITIONS = """- phenotypic_screen: a screen in cells or animals with no target hypothesis
- target_screen: a high-throughput, fragment or virtual screen against the target; immunization or display for a biologic
- de_novo_design: designed from the sequence or structure (antisense, siRNA, structure-based design)
- derived_from_active: derived from an existing active: a known drug, an endogenous ligand, a natural product
- repurposed_drug: an existing drug tried in this disease
- unclear: no source settles it"""

LABEL_SYSTEM = f"""You work out what first proposed a drug target for a disease: the evidence that made someone think the target was worth a drug in that disease, before any drug on it was tested in patients for it. You are given the gene, the disease, the cutoff year (the year the hypothesis was first tested in Phase 2 or 3), the first program that tested it, a provisional origin read from dated evidence databases, and the records that name the gene and the disease and were published before the cutoff year: the earliest and the latest of them, with the total count. You may search and read the web. Only a source dated before the cutoff year counts: a later source, including a later history or review, is not evidence of what proposed the hypothesis at the time and must not be cited.

ORIGIN. One of these categories, with the database's own definitions:
{DEFINITIONS}
The origin is the kind of evidence that first proposed the pair, not the strongest evidence and not the latest. Where the sources show two kinds, the earlier is the origin and the other is secondary_origin. The provisional origin, when shown, is the earliest dated item in the evidence databases: confirm or correct it from the sources, and never repeat it without a source of your own.

GRADE. {GRADE_RULE}

SOURCES. Cite only record ids from the records given (PMID:... or the Europe PMC id shown) or URLs that you fetched or that a search returned in this conversation. Give one publication year per source, the year the source itself shows; every year must be before the cutoff year. origin_year is the year of the source that carries the origin, and null when the origin is unclear.

DISCOVERY ROUTE. Separately, where did the first program's drug come from? One of:
{ROUTE_DEFINITIONS}
It carries its own verbatim quote and sources under the same rules; unclear carries neither. It describes the drug, not the target hypothesis.

Answer in the JSON schema given. rationale is two or three sentences on how the sources settle the origin and the route, or why they do not."""

LABEL_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "origin": {"type": "string", "enum": ORIGINS},
        "origin_year": {"type": ["integer", "null"]},
        "secondary_origin": {"anyOf": [{"type": "string", "enum": ORIGINS}, {"type": "null"}]},
        "grade": {"type": "string", "enum": GRADES},
        "quote": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
        "source_years": {"type": "array", "items": {"type": "integer"}},
        "rationale": {"type": "string"},
        "discovery_route": {"type": "string", "enum": ROUTES},
        "route_quote": {"type": "string"},
        "route_sources": {"type": "array", "items": {"type": "string"}},
        "route_source_years": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["origin", "origin_year", "secondary_origin", "grade", "quote", "sources", "source_years",
                 "rationale", "discovery_route", "route_quote", "route_sources", "route_source_years"],
}

TOOLS = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 8, "blocked_domains": BLOCKED_DOMAINS},
         {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 4, "blocked_domains": BLOCKED_DOMAINS}]
LABEL_METHOD = "target_origin_label@v1"
# shown beside the input; a change in them alone does not relabel. Whether the provisional origin was shown at all
# (provisional_shown) is part of the input, so a run with --hide-provisional never reuses a label made with it shown.
CONTEXT = ("provisional_origin", "provisional_year", "first_program")


def own_input(p: dict) -> dict:
    """What a label decision is about: the payload without its context keys."""
    return llm.own_input(p, CONTEXT)
LABEL_PASSES = 3  # a pair whose answers fail validation is asked again, up to this many times


def render_records(p: dict) -> list[str]:
    n = p["n_records_total"]
    shown = len(p["records"])
    earliest = min(BUNDLE_EARLIEST, shown)
    which = f"the earliest {earliest} and the latest {shown - earliest} are shown" if n > shown else "all are shown"
    out = [f"RECORDS: {n} records name the gene and the disease before the cutoff year; {which}."]
    for r in p["records"]:
        out.append(f"[{r['record_id']}] ({r['year']}) {r['title']}")
        if r.get("abstract"):
            out.append(r["abstract"])
    if not p["records"]:
        out.append("(none)")
    return out


def render_label(p: dict) -> str:
    fp = p["first_program"]
    out = [f"TARGET: {p['symbol']} ({p['gene_name']}), {p['ensembl_id']}",
           f"DISEASE: {p['disease']} ({p['mondo_id']})",
           f"CUTOFF YEAR: {p['cutoff_year']}. Only sources dated {p['cutoff_year'] - 1} or earlier count.",
           (f"FIRST PROGRAM: {fp['entity']}; sponsor {fp['sponsor'] or 'not recorded'}; Phase {fp['phase']} entry "
            f"{fp['entry']}; trials {', '.join(fp['nct_ids']) or 'not recorded'}")]
    if p.get("provisional_origin") is not None:
        year = f" ({p['provisional_year']})" if p.get("provisional_year") else ""
        out.append(f"PROVISIONAL ORIGIN (earliest dated item in the evidence databases): {p['provisional_origin']}{year}")
    return "\n".join(out + render_records(p))


def _check_sources(p: dict, sources: list, years: list, retrieved: set[str], what: str) -> None:
    bundle_years = {r["record_id"]: r["year"] for r in p["records"]}
    if len(years) != len(sources):
        raise ValueError(f"{what}: {len(sources)} sources but {len(years)} years")
    for s, y in zip(sources, years):
        if s in bundle_years:
            if y != bundle_years[s]:
                raise ValueError(f"{what}: {s} is dated {bundle_years[s]}, not {y}")
        elif llm.norm_url(s) not in retrieved:
            raise ValueError(f"{what}: cites a source it did not retrieve: {s}")
        if y >= p["cutoff_year"]:
            raise ValueError(f"{what}: {s} dated {y}, not before the cutoff year {p['cutoff_year']}")


def validate_label(p: dict, out: dict) -> None:
    """Raise ValueError when a label breaks a rule; pipeline.llm then stores the decision as invalid."""
    if out["origin"] not in ORIGINS or out["grade"] not in GRADES or out["discovery_route"] not in ROUTES:
        raise ValueError("origin, grade or discovery_route outside the lists")
    if out["secondary_origin"] is not None and (out["secondary_origin"] not in ORIGINS
                                                or out["secondary_origin"] == out["origin"]):
        raise ValueError(f"secondary_origin {out['secondary_origin']} with origin {out['origin']}")
    if (out["origin"] == "unclear") != (out["grade"] == "none"):
        raise ValueError(f"origin {out['origin']} with grade {out['grade']}")
    retrieved = {llm.norm_url(u) for u in out.get("retrieved_urls", [])}
    if out["grade"] == "none":
        if out["quote"].strip() or out["sources"] or out["source_years"] or out["origin_year"] is not None \
                or out["secondary_origin"] is not None:
            raise ValueError("an unclear origin carries no quote, source, year or secondary origin")
    else:
        if not out["quote"].strip() or not out["sources"]:
            raise ValueError("a graded origin needs a quote and a source")
        _check_sources(p, out["sources"], out["source_years"], retrieved, "origin")
        if out["origin_year"] not in out["source_years"]:
            raise ValueError(f"origin_year {out['origin_year']} is not the year of a cited source")
    if (out["discovery_route"] == "unclear") != (not out["route_quote"].strip()):
        raise ValueError(f"discovery_route {out['discovery_route']} with route_quote {out['route_quote']!r}")
    if out["discovery_route"] == "unclear":
        if out["route_sources"] or out["route_source_years"]:
            raise ValueError("an unclear route carries no source")
    else:
        if not out["route_sources"]:
            raise ValueError("a graded route needs a source")
        _check_sources(p, out["route_sources"], out["route_source_years"], retrieved, "route")


LABEL_TASK = llm.Task(name="target_origin", prompt_version="v2", schema_version="v1", system=LABEL_SYSTEM,
                      schema=LABEL_SCHEMA, render=render_label, validate=validate_label, subject_type="target_disease",
                      model="claude-opus-5-5", effort="medium", max_tokens=16000, tools=TOOLS)

LABEL_DESCRIPTION = f"""For each pair: task {LABEL_TASK.name} {LABEL_TASK.prompt_version} ({LABEL_TASK.model}, effort
{LABEL_TASK.effort}, web search and fetch with {', '.join(BLOCKED_DOMAINS)} blocked) reads the gene, the disease, the
cutoff year, the first program, the provisional origin and the earliest {BUNDLE_EARLIEST} and latest {BUNDLE_LATEST}
pre-entry records (abstracts cut to {ABSTRACT_CHARS} characters) and returns the origin (13 categories), its year,
a secondary origin, the grade (stated, pattern, none), a verbatim quote, the sources with their years, and the first
drug's discovery route with its own quote and sources. Every cited source is a shown record or a URL retrieved in the
turn, dated before the cutoff year; a label breaking a rule is stored invalid and the pair is asked again, up to
{LABEL_PASSES} times. Rows replace earlier labelled rows for the decided pairs only."""


def first_programs(pairs: pd.DataFrame) -> dict[tuple[str, str], dict]:
    """The first program to test each pair: entity, sponsor, phase, entry date, NCT ids of the trials marking it."""
    from pipeline.target_disease import (
        EARLY,  # the hub module registers this one; import here, not at the top
    )
    from pipeline.target_history import targets
    from report.section1 import phase_rows
    snap = frame.snapshot()
    rows = phase_rows(frame.programs(), frame.program_trials(), snap, window=(EARLY, snap))
    rows = rows[rows.phase.isin([2, 3]) & ~rows.credited][["program_id", "phase", "entry"]]
    progs = frame.query("SELECT program_id, moiety_id, mondo_id, lead_sponsors FROM preclin.dev_program")
    t = targets()[["moiety_id", "ens"]].drop_duplicates()
    d = rows.merge(progs, on="program_id").merge(t, on="moiety_id")
    d = d.sort_values(["ens", "mondo_id", "entry", "program_id"]).drop_duplicates(["ens", "mondo_id"])
    want = set(zip(pairs.ensembl_id, pairs.mondo_id))
    d = d[[(e, m) in want for e, m in zip(d.ens, d.mondo_id)]]
    names = frame.query("SELECT moiety_id, name FROM preclin.moiety").set_index("moiety_id").name.to_dict()
    trials = frame.program_trials()
    trials = trials[trials.marks_entry]
    out = {}
    for r in d.itertuples():
        ncts = trials[(trials.program_id == r.program_id) & (trials.phase == r.phase)].nct_id.tolist()[:3]
        out[(r.ens, r.mondo_id)] = {"entity": names.get(r.moiety_id, str(r.moiety_id)),
                                   "sponsor": (list(r.lead_sponsors or []) or [None])[0], "phase": int(r.phase),
                                   "entry": str(pd.Timestamp(r.entry).date()), "nct_ids": ncts}
    return out


def sources_for(pairs: pd.DataFrame) -> dict[tuple[str, str], list[dict]]:
    """Every stored record of each pair, ranked."""
    if pairs.empty:
        return {}
    s = frame.query(SOURCES_SQL, (tuple(zip(pairs.ensembl_id, pairs.mondo_id)), ORIGIN_SERVICES))
    return {k: records_from(g.drop(columns=["ensembl_id", "mondo_id"]))
            for k, g in s.groupby(["ensembl_id", "mondo_id"])}


def pair_items(pairs: pd.DataFrame) -> dict[str, dict]:
    """What every reader of a pair sees: the gene, the disease, the cutoff year and the bundle of records."""
    labels = mondo_labels()
    gene_name = frame.query("SELECT ensembl_id, min(name) AS name FROM preclin.hgnc_gene WHERE ensembl_id IS NOT NULL "
                            "GROUP BY 1").set_index("ensembl_id").name.to_dict()
    sources = sources_for(pairs)
    items = {}
    for r in pairs.itertuples():
        rows = sources.get((r.ensembl_id, r.mondo_id), [])
        items[key(r.ensembl_id, r.mondo_id)] = {
            "ensembl_id": r.ensembl_id, "mondo_id": r.mondo_id, "symbol": r.symbol,
            "gene_name": gene_name.get(r.ensembl_id, r.symbol), "disease": labels.get(r.mondo_id, r.mondo_id),
            "cutoff_year": int(r.cutoff_year), "n_records_total": len(rows), "records": bundle(rows)}
    return items


def label_items(pairs: pd.DataFrame, hide_provisional: bool) -> dict[str, dict]:
    """The labelling payloads: pair_items plus the first program and, unless hidden, the provisional origin."""
    prov = frame.query("SELECT ensembl_id, mondo_id, origin, origin_year FROM preclin.target_disease_origin "
                       "WHERE basis = 'provisional'")
    prov = {(e, m): (o, None if pd.isna(y) else int(y)) for e, m, o, y in
            zip(prov.ensembl_id, prov.mondo_id, prov.origin, prov.origin_year)}
    programs = first_programs(pairs)
    entry = {(r.ensembl_id, r.mondo_id): str(r.first_entry.date()) for r in pairs.itertuples()}
    items = pair_items(pairs)
    for k, item in items.items():
        pair = split_key(k)
        po, py = (None, None) if hide_provisional else prov.get(pair, (None, None))
        item["first_program"] = programs.get(pair, {"entity": "not recorded", "sponsor": None, "phase": 2,
                                                    "entry": entry[pair], "nct_ids": []})
        item["provisional_origin"], item["provisional_year"] = po, py
        item["provisional_shown"] = not hide_provisional
    return items


def undecided(items: dict[str, dict], decided: list[tuple]) -> dict[str, dict]:
    done = {k for k, _, _ in decided}
    return {k: v for k, v in items.items() if k not in done}


def origin_rows(decided: list[tuple[str, int, dict]]) -> list[tuple]:
    """Rows for preclin.target_disease_origin in the INSERT's column order."""
    out = []
    for k, decision_id, o in decided:
        e, m = split_key(k)
        out.append((e, m, "labelled", o["origin"], o["origin_year"], o["secondary_origin"], o["grade"],
                    list(o["sources"]), o["quote"].strip() or None, decision_id, LABEL_METHOD, "not_checked",
                    o["discovery_route"], o["route_quote"].strip() or None, list(o["route_sources"])))
    return out


def replace_sql(keys: list[tuple[str, str]]) -> tuple[str, tuple]:
    """The DELETE that clears the labelled rows of exactly these pairs before their new rows go in."""
    return ("DELETE FROM preclin.target_disease_origin WHERE basis = 'labelled' AND (ensembl_id, mondo_id) IN %s",
            (tuple(keys),))


INSERT_ORIGIN = """INSERT INTO preclin.target_disease_origin
                     (ensembl_id, mondo_id, basis, origin, origin_year, secondary_origin, grade, sources, quote,
                      llm_decision_id, method_id, check_outcome, discovery_route, route_quote, route_sources)
                   VALUES %s"""


def label(args) -> None:
    pairs = pair_frame(args.pairs)
    items = label_items(pairs, args.hide_provisional)
    params = {"task": LABEL_TASK.name, "prompt_version": LABEL_TASK.prompt_version, "model": LABEL_TASK.model,
              "effort": LABEL_TASK.effort, "tools": TOOLS, "origins": ORIGINS, "routes": ROUTES,
              "bundle": [BUNDLE_EARLIEST, BUNDLE_LATEST], "abstract_chars": ABSTRACT_CHARS,
              "hide_provisional": bool(args.hide_provisional), "passes": LABEL_PASSES, "runs": []}
    inputs = ["preclin.target_disease", "preclin.target_disease_source", "preclin.target_disease_origin",
              "preclin.dev_program", "preclin.dev_program_trial", "web search"]
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, LABEL_METHOD, "What first proposed each target-disease hypothesis", LABEL_DESCRIPTION,
                          inputs, params)
        conn.commit()
    decided: list[tuple] = []
    todo = items
    for _ in range(LABEL_PASSES):
        if not todo:
            break
        run_id = llm.run(LABEL_TASK, todo, context=CONTEXT)
        params["runs"].append(str(run_id))
        new = llm.decisions(run_id)
        decided += new
        todo = undecided(todo, new)
        log(f"run {run_id}: {len(new)} decided, {len(todo)} undecided")
    rows = origin_rows(decided)
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, LABEL_METHOD, "What first proposed each target-disease hypothesis", LABEL_DESCRIPTION,
                          inputs, params)
        if rows:
            cur.execute(*replace_sql([(r[0], r[1]) for r in rows]))
            execute_values(cur, INSERT_ORIGIN, rows, page_size=1000)
        conn.commit()
    log(f"pairs={len(items)} decided={len(rows)} undecided={len(todo)} runs={params['runs']}")
    log("the rewritten rows are not_checked: run `check` on the same pairs before `gate`, `summary` or any test")


# --- check ---

CHECK_SYSTEM = f"""You verify one label of what first proposed a drug target for a disease. You are given the label (origin, grade, quote, sources with the years the labeller gave), the cutoff year, the full text of every cited record that was among the records shown to the labeller, and the category definitions. For a cited URL, fetch it; if the page cannot be fetched, search for the same source elsewhere (the journal's site, PubMed Central, Europe PMC, a preprint or patent host) and read it there, since the labeller read it somewhere. Answer three questions.
quote_found: yes if the quote, or the sentence it closely paraphrases, is in a cited source; no if it is not; could_not_open only if no copy of a cited source could be fetched or found by search and no shown record carries the quote. A cited PubMed or Europe PMC URL is shown to you as a record (its url is given); read the record rather than fetching the page, and fetch the full text only if the quote is not in the abstract.
year_ok: yes if every cited source's own date (the publication year it shows) is before the cutoff year; no if any is in or after it; unknown if a cited URL's date could not be read.
origin_follows: yes if the quoted passage supports the origin category under its definition; partly if it supports the category only together with the other sources, or supports a neighbouring category as well; no if it does not support it.
note: one sentence.

Categories:
{DEFINITIONS}"""

CHECK_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"quote_found": {"type": "string", "enum": ["yes", "no", "could_not_open"]},
                   "year_ok": {"type": "string", "enum": ["yes", "no", "unknown"]},
                   "origin_follows": {"type": "string", "enum": ["yes", "partly", "no"]},
                   "note": {"type": "string"}},
    "required": ["quote_found", "year_ok", "origin_follows", "note"],
}
# v3: the labeller's search and fetch, after a fetch-only checker (v2) could not open 18 of the 35 labels it rejected
CHECK_TOOLS = TOOLS
CHECK_METHOD = "target_origin_check@v1"


def render_check(p: dict) -> str:
    out = [(f"TARGET: {p['symbol']}; DISEASE: {p['disease']}; CUTOFF YEAR: {p['cutoff_year']} "
            f"(sources must be dated {p['cutoff_year'] - 1} or earlier)"),
           f"LABEL: origin {p['origin']} ({p['grade']}), year {p['origin_year']}, secondary {p['secondary_origin']}",
           f"QUOTE: {p['quote']}",
           "SOURCES: " + "; ".join(f"{s} ({y})" for s, y in zip(p["sources"], p["source_years"])),
           "CITED RECORDS (shown to the labeller, or read for a cited PubMed URL):"]
    for r in p["records"]:
        where = f" = {r['url']}" if r.get("url") else ""
        out += [f"[{r['record_id']}]{where} ({r['year']}) {r['title']}", r.get("abstract") or "(no abstract)"]
    if not p["records"]:
        out.append("(none; every cited source is a URL)")
    return "\n".join(out)


CHECK_CONTEXT = ("label_decision_id",)  # the row's provenance, not what the checker reads
CHECK_TASK = llm.Task(name="target_origin_check", prompt_version="v3", schema_version="v1", system=CHECK_SYSTEM,
                      schema=CHECK_SCHEMA, render=render_check, validate=None, subject_type="target_disease",
                      model="claude-sonnet-5-5", effort="medium", max_tokens=4000, tools=CHECK_TOOLS)

CHECK_DESCRIPTION = f"""For each graded labelled row of {LABEL_METHOD}: task {CHECK_TASK.name} {CHECK_TASK.prompt_version}
({CHECK_TASK.model}, web search and fetch) reads the label, its quote and sources, and the full text of the cited records,
and says whether the quote is in a source, whether every source is dated before the cutoff year, and whether the
origin follows. supported: all three hold (origin_follows yes or partly); unsupported: any is no; unverified: a URL
could not be opened or dated and nothing is no. An unsupported or unverified row is rewritten as unclear (grade none,
no quote, no sources); its label stays in llm_decision_id's decision. Unclear labels are not checked."""


def check_outcome(out: dict) -> str:
    if out["quote_found"] == "no" or out["year_ok"] == "no" or out["origin_follows"] == "no":
        return "unsupported"
    if out["quote_found"] == "could_not_open" or out["year_ok"] == "unknown":
        return "unverified"
    return "supported"


def check_items(pairs: pd.DataFrame) -> dict[str, dict]:
    """A payload per graded labelled row: the label and the full text of the cited records it was shown."""
    if pairs.empty:
        return {}
    rows = frame.query("""SELECT o.ensembl_id, o.mondo_id, o.origin, o.origin_year, o.secondary_origin, o.grade, o.quote,
                                 o.sources, o.llm_decision_id, d.parsed_output
                          FROM preclin.target_disease_origin o JOIN pv_evidence.llm_decision d USING (llm_decision_id)
                          WHERE o.basis = 'labelled' AND o.grade <> 'none' AND (o.ensembl_id, o.mondo_id) IN %s""",
                       (tuple(zip(pairs.ensembl_id, pairs.mondo_id)),))
    base = pair_items(pairs)
    sources = sources_for(pairs)
    items = {}
    for r in records_from(rows):
        k = key(r["ensembl_id"], r["mondo_id"])
        items[k] = check_payload(r, base[k], sources.get((r["ensembl_id"], r["mondo_id"]), []))
    return items


PMID_URL = re.compile(r"(?:pubmed\.ncbi\.nlm\.nih\.gov/|ncbi\.nlm\.nih\.gov/pubmed/|europepmc\.org/(?:article|abstract)/MED/)(\d+)")


def pmid_from_url(url: str) -> str | None:
    """The PMID a PubMed or Europe PMC MEDLINE URL names; None for any other string."""
    m = PMID_URL.search(url) if url.startswith("http") else None
    return m.group(1) if m else None


def check_payload(row: dict, base: dict, records: list[dict], fetch=None) -> dict:
    """One check payload from a labelled row (NaN-free), the pair's base item and the pair's stored records. A cited
    PubMed URL whose record is not among them is read through E-utilities (fetch: pmids -> efetch tuples) and shown
    as a record, so the checker need not fetch the page."""
    def clean(v):
        return None if v is None or (isinstance(v, float) and pd.isna(v)) else v
    cited = set(row["sources"])
    shown = [x for x in records if x["record_id"] in cited]
    have = {x["record_id"] for x in shown}
    wanted = {pmid_from_url(s): s for s in row["sources"] if pmid_from_url(s) and f"PMID:{pmid_from_url(s)}" not in have}
    if wanted:
        fetched = (fetch or attribution.efetch)(sorted(wanted))
        for pmid, title, _author, _journal, year, doi, abstract in fetched:
            shown.append({"record_id": f"PMID:{pmid}", "year": year, "title": title or "", "abstract": abstract,
                          "doi": doi, "url": wanted.get(pmid)})
    return {**{f: base[f] for f in ["ensembl_id", "mondo_id", "symbol", "disease", "cutoff_year"]},
            "origin": row["origin"],
            "origin_year": None if clean(row["origin_year"]) is None else int(row["origin_year"]),
            "secondary_origin": clean(row["secondary_origin"]), "grade": row["grade"],
            "quote": clean(row["quote"]) or "", "sources": list(row["sources"]),
            "source_years": list((row["parsed_output"] or {}).get("source_years", [])),
            "records": shown, "label_decision_id": int(row["llm_decision_id"])}


def check(args) -> None:
    pairs = pair_frame(args.pairs)
    items = check_items(pairs)
    params = {"task": CHECK_TASK.name, "prompt_version": CHECK_TASK.prompt_version, "model": CHECK_TASK.model,
              "effort": CHECK_TASK.effort, "tools": CHECK_TOOLS, "run": None}
    inputs = ["preclin.target_disease_origin", "preclin.target_disease_source", "pv_evidence.llm_decision",
              "web fetch"]
    decided: list[tuple] = []
    todo = items
    params["runs"] = []
    for _ in range(LABEL_PASSES):
        if not todo:
            break
        run_id = llm.run(CHECK_TASK, todo, context=CHECK_CONTEXT)
        params["runs"].append(str(run_id))
        new = llm.decisions(run_id)
        decided += new
        todo = undecided(todo, new)
    params["run"] = params["runs"][-1] if params["runs"] else None
    params["unchecked"] = sorted(todo)
    run_id = params["run"]
    outcomes = {k: (check_outcome(o), i) for k, i, o in decided}
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, CHECK_METHOD, "Second-model check of the origin labels", CHECK_DESCRIPTION, inputs, params)
        for k, (outcome, decision_id) in outcomes.items():
            e, m = split_key(k)
            if outcome == "supported":
                cur.execute("""UPDATE preclin.target_disease_origin SET check_outcome = %s, check_decision_id = %s
                               WHERE basis = 'labelled' AND (ensembl_id, mondo_id) = (%s, %s)""",
                            (outcome, decision_id, e, m))
            else:
                cur.execute("""UPDATE preclin.target_disease_origin SET check_outcome = %s, check_decision_id = %s,
                                 origin = 'unclear', grade = 'none', origin_year = NULL, secondary_origin = NULL,
                                 quote = NULL, sources = '{}'
                               WHERE basis = 'labelled' AND (ensembl_id, mondo_id) = (%s, %s)""",
                            (outcome, decision_id, e, m))
        conn.commit()
    counts = pd.Series([o for o, _ in outcomes.values()]).value_counts().to_dict() if outcomes else {}
    log(f"graded labels={len(items)} checked={len(outcomes)} outcomes={counts} still not_checked={len(todo)} "
        f"runs={params['runs']}")


# --- blind coder ---

BLIND_SYSTEM = f"""You label what first proposed a drug target for a disease: the evidence that made someone think the target was worth a drug in that disease, before any drug on it was tested in patients for it. You are given the gene, the disease, the cutoff year and the records naming both that were published before it (the earliest and the latest, with the total count). You may search and read the web. Only a source dated before the cutoff year counts: a later source, including a later history or review, is not evidence of what proposed the hypothesis at the time and must not be cited. Nothing you know from memory counts without a source.

ORIGIN. One of these categories:
{DEFINITIONS}
The origin is the kind of evidence that first proposed the pair, not the strongest and not the latest. Where the records show two kinds, the earlier is the origin and the other is secondary_origin.

GRADE. {GRADE_RULE}

SOURCE. For a graded label, exactly one source: a record id from those given, with the year shown for it, or a URL you fetched or that a search returned in this conversation, with the publication year it shows, before the cutoff year. An unclear label carries none. note is one sentence."""

BLIND_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"origin": {"type": "string", "enum": ORIGINS},
                   "secondary_origin": {"anyOf": [{"type": "string", "enum": ORIGINS}, {"type": "null"}]},
                   "grade": {"type": "string", "enum": GRADES},
                   "quote": {"type": "string"},
                   "source": {"type": ["string", "null"]},
                   "source_year": {"type": ["integer", "null"]},
                   "note": {"type": "string"}},
    "required": ["origin", "secondary_origin", "grade", "quote", "source", "source_year", "note"],
}
BLIND_METHOD = "target_origin_blind_read@v1"
BLIND_REPLICATES = 3  # independent readings per pair; the reference label is their majority


def replicate_items(items: dict[str, dict], n: int) -> dict[str, dict]:
    """n copies of each item, keyed key|r1..rn with the replicate in the payload, so each is a separate decision."""
    return {f"{k}|r{i}": {**v, "replicate": i} for k, v in items.items() for i in range(1, n + 1)}


def majority_reference(readings: list[tuple[str, str]]) -> tuple[pd.DataFrame, dict]:
    """From (key|r<n>, origin) readings: the majority origin per pair (ensembl_id, mondo_id, origin; pairs with no
    majority left out) and the consistency statistics: pairs, replicates, unanimous, majority, no_majority,
    pairwise_agreement (share of agreeing replicate pairs)."""
    from collections import Counter, defaultdict
    by_pair: dict[tuple[str, str], list[str]] = defaultdict(list)
    for k, origin in readings:
        by_pair[split_key(k)].append(origin)
    replicates = max((len(v) for v in by_pair.values()), default=0)
    rows, unanimous, majority, none, agree = [], 0, 0, 0, []
    for (e, m), origins in by_pair.items():
        top, n = Counter(origins).most_common(1)[0]
        if n == replicates and replicates > 1:
            unanimous += 1
            rows.append((e, m, top))
        elif n >= 2 and n > len(origins) / 2:
            majority += 1
            rows.append((e, m, top))
        else:
            none += 1
        agree += [a == b for i, a in enumerate(origins) for b in origins[i + 1:]]
    stats = {"pairs": len(by_pair), "replicates": replicates, "unanimous": unanimous, "majority": majority,
             "no_majority": none, "pairwise_agreement": float(sum(agree) / len(agree)) if agree else None}
    return pd.DataFrame(rows, columns=["ensembl_id", "mondo_id", "origin"]), stats


def render_blind(p: dict) -> str:
    out = [f"TARGET: {p['symbol']} ({p['gene_name']}), {p['ensembl_id']}",
           f"DISEASE: {p['disease']} ({p['mondo_id']})",
           f"CUTOFF YEAR: {p['cutoff_year']}. Only sources dated {p['cutoff_year'] - 1} or earlier count."]
    return "\n".join(out + render_records(p))


def validate_blind(p: dict, out: dict) -> None:
    if out["origin"] not in ORIGINS or out["grade"] not in GRADES:
        raise ValueError("origin or grade outside the lists")
    if out["secondary_origin"] is not None and (out["secondary_origin"] not in ORIGINS
                                                or out["secondary_origin"] == out["origin"]):
        raise ValueError(f"secondary_origin {out['secondary_origin']} with origin {out['origin']}")
    if (out["origin"] == "unclear") != (out["grade"] == "none"):
        raise ValueError(f"origin {out['origin']} with grade {out['grade']}")
    if out["grade"] == "none":
        if out["quote"].strip() or out["source"] is not None:
            raise ValueError("an unclear origin carries no quote or source")
        return
    years = {r["record_id"]: r["year"] for r in p["records"]}
    retrieved = {llm.norm_url(u) for u in out.get("retrieved_urls", [])}
    if not out["quote"].strip() or not out["source"]:
        raise ValueError("a graded origin needs a quote and a source")
    if out["source"] in years:
        if out["source_year"] != years[out["source"]]:
            raise ValueError(f"{out['source']} is dated {years[out['source']]}, not {out['source_year']}")
    elif llm.norm_url(out["source"]) not in retrieved:
        raise ValueError(f"cites a source it did not retrieve: {out['source']}")
    if out["source_year"] is None or out["source_year"] >= p["cutoff_year"]:
        raise ValueError(f"source year {out['source_year']} is not before the cutoff year {p['cutoff_year']}")


BLIND_TASK = llm.Task(name="target_origin_blind_read", prompt_version="v3", schema_version="v1", system=BLIND_SYSTEM,
                      schema=BLIND_SCHEMA, render=render_blind, validate=validate_blind, subject_type="target_disease",
                      model="claude-opus-5-5", effort="medium", max_tokens=16000, tools=TOOLS)

BLIND_DESCRIPTION = f"""Blind reference reading of a hand-check set (#146; the owner's decision of 2026-11-19 that a
model reads the set in place of a human hand check): task {BLIND_TASK.name} {BLIND_TASK.prompt_version}
({BLIND_TASK.model}; v2 with the labeller's web search and fetch, after v1 without them failed the gate for want of
access) labels each pair from the same records the labeller was shown, with no provisional origin and no program,
{BLIND_REPLICATES} times independently. The reference label is the majority of the readings;
pairs with no majority are reported and left out of the agreement gate; the readings' mutual agreement is the
consistency check. The readings never shape a prompt revision."""


def blind(args) -> None:
    pairs = pair_frame(args.pairs)
    items = replicate_items(pair_items(pairs), BLIND_REPLICATES)
    run_id = llm.run(BLIND_TASK, items)
    decided = llm.decisions(run_id)
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, BLIND_METHOD, "Blind second coder of a hand-check set", BLIND_DESCRIPTION,
                          ["preclin.target_disease", "preclin.target_disease_source"],
                          {"task": BLIND_TASK.name, "prompt_version": BLIND_TASK.prompt_version,
                           "model": BLIND_TASK.model, "effort": BLIND_TASK.effort, "pairs": args.pairs,
                           "replicates": BLIND_REPLICATES, "run": str(run_id)})
        conn.commit()
    _, stats = majority_reference([(k, o["origin"]) for k, _, o in decided])
    log(f"pairs={len(pairs)} readings={len(decided)} of {len(items)} run={run_id} consistency={stats}")


# --- pilot sample ---

PILOT_SEED = 20261119
PILOT_PER_GROUP = 50
SET_PER_GROUP = 25
SAMPLE_METHOD = "target_origin_pilot_sample@v1"
SAMPLE_DESCRIPTION = f"""Pilot of the origin labelling (#146 step 4). Frame: pairs first entered in
{SECTION1[0].year}-{SECTION1[1].year}, not validated at entry, with no engaged-without-benefit stop filed as unresolved
(#158: the 102 contradicted "not causal" verdicts are unresolved, so neither group draws on them). Group not_causal:
pairs with at least one stop of mode not_causal (report.engaged_modes); group other: the rest. Seed {PILOT_SEED}:
{PILOT_PER_GROUP} per group, then {SET_PER_GROUP} of each group to hand-check set a and the rest to set b, disjoint."""


def sample_pairs(cohort: pd.DataFrame, stop_modes: pd.DataFrame, seed: int) -> pd.DataFrame:
    """The pilot sample: ensembl_id, mondo_id, group (not_causal | other), hand_check_set (a | b)."""
    import numpy as np
    pairs = sorted(set(zip(cohort.ensembl_id, cohort.mondo_id)))
    modes = stop_modes[stop_modes.set_index(["ensembl_id", "mondo_id"]).index.isin(pairs)]
    unresolved = set(zip(*[modes[modes["mode"] == "unresolved"][c] for c in ["ensembl_id", "mondo_id"]]))
    not_causal = set(zip(*[modes[modes["mode"] == "not_causal"][c] for c in ["ensembl_id", "mondo_id"]]))
    candidates = [p for p in pairs if p not in unresolved]
    rng = np.random.default_rng(seed)
    out = []
    for group, members in [("not_causal", [p for p in candidates if p in not_causal]),
                           ("other", [p for p in candidates if p not in not_causal])]:
        idx = rng.choice(len(members), size=min(PILOT_PER_GROUP, len(members)), replace=False)
        chosen = [members[i] for i in sorted(idx)]
        set_a = set(rng.choice(len(chosen), size=min(SET_PER_GROUP, len(chosen)), replace=False).tolist())
        out += [(e, m, group, "a" if i in set_a else "b") for i, (e, m) in enumerate(chosen)]
    return pd.DataFrame(out, columns=["ensembl_id", "mondo_id", "group", "hand_check_set"])


def stop_modes() -> pd.DataFrame:
    """Every engaged-without-benefit stop's failure mode, keyed to its pair: ensembl_id, mondo_id, mode."""
    from pipeline.target_history import targets
    from report.engaged_modes import engaged_modes
    m = engaged_modes()
    t = targets()[["moiety_id", "ens"]].drop_duplicates()
    d = m.merge(t, on="moiety_id").rename(columns={"ens": "ensembl_id"})
    return d[["ensembl_id", "mondo_id", "mode"]]


def sample(args) -> None:
    if os.path.exists(PILOT_CSV) and not args.force:
        raise SystemExit(f"{PILOT_CSV} exists; the pilot is drawn once. Pass --force to redraw it.")
    hub = pair_frame("window")
    cohort = hub[~hub.validated_at_entry]
    modes = stop_modes()
    s = sample_pairs(cohort, modes, PILOT_SEED)
    s = s.merge(hub[["ensembl_id", "mondo_id", "symbol", "cutoff_year"]], on=["ensembl_id", "mondo_id"])
    labels = mondo_labels()
    s["disease"] = s.mondo_id.map(labels)
    s = s[["ensembl_id", "mondo_id", "symbol", "disease", "cutoff_year", "group", "hand_check_set"]]
    s.to_csv(PILOT_CSV, index=False)
    in_cohort = modes.merge(cohort[["ensembl_id", "mondo_id"]], on=["ensembl_id", "mondo_id"])
    unresolved = in_cohort[in_cohort["mode"] == "unresolved"][["ensembl_id", "mondo_id"]].drop_duplicates()
    settled = cohort.merge(unresolved, on=["ensembl_id", "mondo_id"], how="left", indicator=True)
    settled = settled[settled._merge == "left_only"]
    nc = in_cohort[in_cohort["mode"] == "not_causal"][["ensembl_id", "mondo_id"]].drop_duplicates()
    nc_settled = settled.merge(nc, on=["ensembl_id", "mondo_id"])
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, SAMPLE_METHOD, "Pilot sample of the origin labelling", SAMPLE_DESCRIPTION,
                          ["preclin.target_disease", "preclin.stop_target_history", "report.engaged_modes"],
                          {"seed": PILOT_SEED, "per_group": PILOT_PER_GROUP, "set_per_group": SET_PER_GROUP,
                           "cohort": len(cohort), "excluded_unresolved": len(unresolved),
                           "frame_not_causal": len(nc_settled), "frame_other": int(len(settled) - len(nc_settled)),
                           "drawn": s.groupby("group").size().to_dict()})
        conn.commit()
    log(f"cohort {len(cohort):,} pairs in the window and not validated; {len(unresolved):,} excluded for an unresolved "
        f"stop; frame not_causal {len(nc_settled):,}, other {len(settled) - len(nc_settled):,}; drawn "
        f"{s.groupby(['group', 'hand_check_set']).size().to_dict()}; written {PILOT_CSV}")


# --- reader package ---

CODEBOOK = os.path.join(frame.REPO, "report", "audits", "target_origin_codebook.md")
FORM_FIELDS = ["origin", "secondary_origin", "grade", "quote", "source", "source_year", "discovery_route", "note"]


def record_url(record_id: str) -> str:
    source, _, ident = record_id.partition(":")
    if source == "PMID":
        return f"https://pubmed.ncbi.nlm.nih.gov/{ident}/"
    return f"https://europepmc.org/article/{source}/{ident}"


def search_links(row: dict) -> dict[str, str]:
    from urllib.parse import quote
    genes = row.get("gene_names") or [row["symbol"]]
    diseases = row.get("disease_names") or [row["disease"]]
    cutoff = int(row["cutoff_year"])
    term = pair_term(list(genes), list(diseases))("1900", str(cutoff - 1))
    return {"pubmed": "https://pubmed.ncbi.nlm.nih.gov/?term=" + quote(term),
            "patents": (f"https://patents.google.com/?q={quote(row['symbol'])}&q={quote(row['disease'])}"
                        f"&before=priority:{cutoff}0101")}


def definitions() -> dict[str, str]:
    return {line[2:].split(":", 1)[0]: line[2:].split(":", 1)[1].strip() for line in DEFINITIONS.splitlines()}


PACKAGE_STYLE = """
:root { --bg: #fbfaf7; --fg: #1d1d1b; --muted: #6b675f; --line: #ddd8cc; --card: #ffffff; --accent: #2b5d8a; --done: #2f7d4f; }
@media (prefers-color-scheme: dark) { :root { --bg: #171716; --fg: #ebe8e1; --muted: #a39e93; --line: #3a3833; --card: #1f1f1d; --accent: #8fb8e0; --done: #7cc39a; } }
* { box-sizing: border-box; } body { margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.45 -apple-system, "Helvetica Neue", Arial, sans-serif; }
header { padding: 12px 16px; border-bottom: 1px solid var(--line); display: flex; gap: 16px; align-items: baseline; flex-wrap: wrap; }
header h1 { font-size: 18px; margin: 0; } header .progress { color: var(--muted); } header button { font: inherit; padding: 4px 10px; }
.wrap { display: grid; grid-template-columns: 260px 1fr; } nav { border-right: 1px solid var(--line); padding: 8px; position: sticky; top: 0; height: 100vh; overflow: auto; }
nav a { display: block; padding: 3px 6px; color: var(--fg); text-decoration: none; border-radius: 4px; font-size: 13px; } nav a.done::before { content: "\\2713 "; color: var(--done); } nav a:hover { background: var(--line); }
main { padding: 16px; max-width: 1100px; } details.codebook { border: 1px solid var(--line); border-radius: 6px; padding: 8px 12px; margin-bottom: 16px; background: var(--card); }
details.codebook pre { white-space: pre-wrap; font: 13px/1.4 inherit; margin: 0; }
.card { border: 1px solid var(--line); border-radius: 8px; background: var(--card); padding: 14px 16px; margin-bottom: 20px; }
.card h2 { margin: 0 0 4px; font-size: 18px; } .meta { color: var(--muted); font-size: 13px; margin-bottom: 8px; } .meta a { color: var(--accent); }
.records { margin: 10px 0; } .rec { padding: 6px 0; border-top: 1px dashed var(--line); font-size: 14px; } .rec .y { color: var(--muted); font-variant-numeric: tabular-nums; margin-right: 6px; }
.rec a { color: var(--accent); text-decoration: none; } .rec details { margin-top: 2px; } .rec summary { cursor: pointer; color: var(--muted); font-size: 13px; } .rec p { margin: 4px 0 0; white-space: pre-wrap; }
form { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 14px; margin-top: 10px; border-top: 1px solid var(--line); padding-top: 10px; }
label { display: flex; flex-direction: column; font-size: 13px; color: var(--muted); gap: 3px; } label.wide { grid-column: 1 / -1; }
select, input, textarea { font: inherit; color: var(--fg); background: var(--bg); border: 1px solid var(--line); border-radius: 4px; padding: 5px 6px; } textarea { min-height: 56px; }
@media (max-width: 800px) { .wrap { grid-template-columns: 1fr; } nav { position: static; height: auto; max-height: 30vh; } form { grid-template-columns: 1fr; } }
"""

PACKAGE_SCRIPT = """
const SET = __SET__; const KEYS = __KEYS__; const FIELDS = __FIELDS__;
const STORE = "target_origin_hand_check_" + SET;
let answers = {};
try { answers = JSON.parse(localStorage.getItem(STORE) || "{}"); } catch (e) { answers = {}; }
function save() { try { localStorage.setItem(STORE, JSON.stringify(answers)); } catch (e) {} progress(); }
function progress() {
  const done = KEYS.filter(k => (answers[k] || {}).origin).length;
  document.getElementById("progress").textContent = done + " of " + KEYS.length + " answered";
  document.querySelectorAll("nav a").forEach(a => a.classList.toggle("done", !!(answers[a.dataset.key] || {}).origin));
}
function csv() {
  const q = s => '"' + String(s == null ? "" : s).replace(/"/g, '""') + '"';
  const rows = KEYS.map(k => { const a = answers[k] || {}; const [e, m] = k.split("|"); return [e, m, ...FIELDS.map(f => a[f] || "")].map(q).join(","); });
  return [["ensembl_id", "mondo_id", ...FIELDS].join(","), ...rows].join("\\n") + "\\n";
}
document.querySelectorAll("[data-key][data-field]").forEach(el => {
  const v = (answers[el.dataset.key] || {})[el.dataset.field]; if (v != null) el.value = v;
  el.addEventListener("input", () => { answers[el.dataset.key] = answers[el.dataset.key] || {}; answers[el.dataset.key][el.dataset.field] = el.value; save(); });
});
document.getElementById("copy").addEventListener("click", () => {
  const text = csv(); const status = document.getElementById("status");
  const fallback = () => { const ta = document.createElement("textarea"); ta.value = text; ta.style.width = "100%"; ta.style.height = "200px"; document.body.prepend(ta); ta.select(); status.textContent = "select all in the box and copy"; };
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(() => { status.textContent = "copied"; }, fallback); else fallback();
});
document.getElementById("download").addEventListener("click", e => { e.target.href = URL.createObjectURL(new Blob([csv()], {type: "text/csv"})); });
progress();
"""


def _select(k: str, name: str, values: list[str], defs: dict[str, str]) -> str:
    import html as h
    opts = "".join(f'<option value="{v}" title="{h.escape(defs.get(v, ""))}">{v}</option>' for v in values)
    return f'<select data-key="{h.escape(k)}" data-field="{name}"><option value=""></option>{opts}</select>'


def _card(p: dict, defs: dict[str, str]) -> str:
    import html as h
    k = h.escape(p["key"])
    fp = p["first_program"]
    recs = []
    for r in p["records"]:
        abstract = f'<details><summary>abstract</summary><p>{h.escape(r["abstract"])}</p></details>' if r["abstract"] else ""
        recs.append(f'<div class="rec"><span class="y">{r["year"]}</span><a href="{h.escape(r["url"])}" target="_blank" '
                    f'rel="noopener">{h.escape(r["title"])}</a> <span class="y">[{h.escape(r["record_id"])}]</span>{abstract}</div>')
    n = p["n_records_total"]
    shown = "; the earliest and the latest are shown" if n > len(p["records"]) else ""
    prov_year = f" ({p['provisional_year']})" if p.get("provisional_year") else ""
    return f"""<section class="card" id="{k}">
<h2>{h.escape(p["symbol"])} &times; {h.escape(p["disease"])}</h2>
<div class="meta">{h.escape(p["gene_name"])} ({h.escape(p["ensembl_id"])}); {h.escape(p["mondo_id"])}. <b>Cutoff year {p["cutoff_year"]}</b>: only sources dated {p["cutoff_year"] - 1} or earlier count.<br>
First program: {h.escape(str(fp.get("entity", "not recorded")))}; sponsor {h.escape(str(fp.get("sponsor") or "not recorded"))}; Phase {h.escape(str(fp.get("phase", "")))} entry {h.escape(str(fp.get("entry", "")))}; trials {h.escape(", ".join(fp.get("nct_ids") or []) or "not recorded")}.<br>
Provisional origin (earliest dated item in the evidence databases; the model saw it too): <b>{h.escape(p.get("provisional_origin") or "none recorded")}</b>{prov_year}.<br>
Search before the cutoff: <a href="{h.escape(p["links"]["pubmed"])}" target="_blank" rel="noopener">PubMed</a> &middot; <a href="{h.escape(p["links"]["patents"])}" target="_blank" rel="noopener">Google Patents</a></div>
<div class="records"><b>{n}</b> records name the gene and the disease before the cutoff year{shown}.{"".join(recs) or '<div class="rec">(none)</div>'}</div>
<form onsubmit="return false">
<label>origin {_select(p["key"], "origin", ORIGINS, defs)}</label>
<label>secondary_origin {_select(p["key"], "secondary_origin", ORIGINS, defs)}</label>
<label>grade {_select(p["key"], "grade", GRADES, {})}</label>
<label>discovery_route (optional) {_select(p["key"], "discovery_route", ROUTES, {})}</label>
<label class="wide">quote (verbatim) <textarea data-key="{k}" data-field="quote"></textarea></label>
<label>source (record id as shown, or URL) <input type="text" data-key="{k}" data-field="source"></label>
<label>source_year <input type="number" data-key="{k}" data-field="source_year"></label>
<label class="wide">note <textarea data-key="{k}" data-field="note"></textarea></label>
</form></section>"""


def render_package(rows: list[dict], codebook: str, set_name: str) -> str:
    """The reader's page for one hand-check set: one card per pair with the same records the model saw, the codebook,
    the form, answers kept in the browser and exported as CSV. No model label is read or shown."""
    import html as h
    import json
    pairs = []
    for r in sorted(rows, key=lambda r: (r["symbol"], r["disease"])):
        pairs.append({"key": key(r["ensembl_id"], r["mondo_id"]), "ensembl_id": r["ensembl_id"],
                      "mondo_id": r["mondo_id"], "symbol": r["symbol"], "gene_name": r.get("gene_name", r["symbol"]),
                      "disease": r["disease"], "cutoff_year": int(r["cutoff_year"]),
                      "first_program": r.get("first_program") or {}, "provisional_origin": r.get("provisional_origin"),
                      "provisional_year": r.get("provisional_year"), "n_records_total": r.get("n_records_total", 0),
                      "records": [{"record_id": x["record_id"], "year": x["year"], "title": x["title"],
                                   "abstract": x.get("abstract") or "", "url": record_url(x["record_id"])}
                                  for x in r.get("records", [])],
                      "links": search_links(r)})
    defs = definitions()
    nav = "".join(f'<a href="#{h.escape(p["key"])}" data-key="{h.escape(p["key"])}">{h.escape(p["symbol"])} &times; '
                  f'{h.escape(p["disease"])}</a>' for p in pairs)
    cards = "\n".join(_card(p, defs) for p in pairs)
    script = PACKAGE_SCRIPT
    for token, value in [("__SET__", json.dumps(set_name)), ("__KEYS__", json.dumps([p["key"] for p in pairs])),
                         ("__FIELDS__", json.dumps(FORM_FIELDS))]:
        script = script.replace(token, value.replace("</", "<\\/"))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Target origin hand check (set {h.escape(set_name)})</title>
<style>{PACKAGE_STYLE}</style></head><body>
<header><h1>Target origin hand check, set {h.escape(set_name)}</h1><span class="progress" id="progress"></span>
<button id="copy">Copy answers as CSV</button><a id="download" download="target_origin_hand_check_{h.escape(set_name)}.csv" href="#">Download CSV</a><span id="status" class="progress"></span></header>
<div class="wrap"><nav id="nav">{nav}</nav><main>
<details class="codebook" open><summary>Codebook</summary><pre>{h.escape(codebook)}</pre></details>
{cards}
</main></div>
<script>{script}</script></body></html>
"""

def package(args) -> None:
    pairs = pair_frame(f"set_{args.set}")
    items = label_items(pairs, hide_provisional=False)
    names = frame.query("""SELECT ensembl_id, mondo_id, gene_names, disease_names FROM preclin.target_disease_search
                           WHERE service = 'pubmed' AND (ensembl_id, mondo_id) IN %s""",
                        (tuple(zip(pairs.ensembl_id, pairs.mondo_id)),))
    names = {(e, m): (list(g), list(d)) for e, m, g, d in
             zip(names.ensembl_id, names.mondo_id, names.gene_names, names.disease_names)}
    rows = []
    for k, item in items.items():
        g, d = names.get(split_key(k), (None, None))
        rows.append({**item, "gene_names": g, "disease_names": d})
    with open(CODEBOOK, encoding="utf-8") as f:
        codebook = f.read()
    page = render_package(rows, codebook, args.set)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(page)
    log(f"{len(rows)} pairs, {sum(len(r['records']) for r in rows)} records, {len(page.encode()) / 1e6:.1f} MB -> {args.out}")


# --- gate and summary ---

LAYER = {"human_genetics": "genetics", "tumour_genetics": "genetics",
         "diseased_tissue": "tissue_biomarker", "observational_biomarker": "tissue_biomarker",
         "mouse_genetics": "model_systems", "curated_pathway": "model_systems", "cell_screen": "model_systems",
         "human_cell_perturbation": "model_systems", "animal_model_pharmacology": "model_systems",
         "earlier_drug_other_disease": "earlier_drug",
         "clinical_observation": "clinical_phenotypic", "phenotypic_screen": "clinical_phenotypic",
         "unclear": "unclear"}
KAPPA_MIN = 0.6
GAP_MAX = 10.0
GATE_JSON = os.path.join(frame.REPO, "report", "audits", "target_origin_gate.json")
GATE_METHOD = "target_origin_pilot@v1"
GATE_DESCRIPTION = f"""Pilot gates of the origin labelling (#146 step 4, registered 2026-11-19; reference changed to a
blind model reading by the owner's decision the same day). Agreement: Cohen's kappa between the reference origin (the
majority of {BLIND_REPLICATES} blind readings, or a human reader's sheet when one is given) and the labeller's origin as
read, before the second-model check (the registered wording, "against a blind hand check"; decision of 2026-11-20), over
the 13 categories, on one hand-check set; must be at least {KAPPA_MIN}. Coverage: the share of pilot pairs with at least
one pre-entry record, in the group with a settled "not causal" stop and the group without; the gap must be at most
{GAP_MAX} points. Also reported, never gating: kappa on the stored origin after the check (the check is a filter on what
enters the tests, and its outcome rates are reported as such), both kappas on the collapsed reporting layer (LAYER),
agreement with the labeller's primary or secondary origin, and the blind second coder's kappa against the reader and
the labeller."""


def kappa(a: pd.Series, b: pd.Series) -> float | None:
    from sklearn.metrics import cohen_kappa_score
    if len(a) < 2:
        return None
    if list(a) == list(b):
        return 1.0
    return float(cohen_kappa_score(list(a), list(b)))


def gate_result(reader: pd.DataFrame, stored: pd.DataFrame, raw: pd.DataFrame, coverage: dict[str, float],
                blind: pd.DataFrame | None, kappa_min: float = KAPPA_MIN, gap_max: float = GAP_MAX,
                covered: set[tuple[str, str]] | None = None) -> dict:
    """The gate statistics for one hand-check set. reader: ensembl_id, mondo_id, origin; stored: the same after the
    check; raw: the labeller's origin and secondary_origin; coverage: group -> share of pairs with a record; blind:
    ensembl_id, mondo_id, blind_origin, or None; covered: the pairs with at least one record, for the stratified
    kappas. A pair the reader decided and the labeller did not counts as unclear on the labeller's side. The gate is
    scored on the labeller's origin as read (gate_origin "raw"); the stored origin after the check is reported."""
    on = ["ensembl_id", "mondo_id"]
    m = reader[on + ["origin"]].merge(stored[on + ["origin"]].rename(columns={"origin": "stored"}), on=on, how="left") \
        .merge(raw[on + ["origin", "secondary_origin"]].rename(columns={"origin": "raw"}), on=on, how="left")
    n_missing = int(m.stored.isna().sum())
    m["stored"] = m.stored.fillna("unclear")
    m["raw"] = m.raw.fillna("unclear")
    layer = lambda s: s.map(LAYER)
    gap = abs(coverage["not_causal"] - coverage["other"]) * 100
    out = {"n": len(m), "kappa_stored": kappa(m.origin, m.stored), "kappa_raw": kappa(m.origin, m.raw),
           "kappa_stored_layer": kappa(layer(m.origin), layer(m.stored)),
           "kappa_raw_layer": kappa(layer(m.origin), layer(m.raw)),
           "any_origin_agree": float(((m.origin == m.raw) | (m.origin == m.secondary_origin)).mean()) if len(m) else None,
           "coverage": {k: float(v) for k, v in coverage.items()}, "gap_points": round(gap, 2),
           "n_missing": n_missing, "kappa_blind_vs_reader": None, "kappa_blind_vs_raw": None}
    if covered is not None:
        is_covered = pd.Series([(e, x) in covered for e, x in zip(m.ensembl_id, m.mondo_id)], index=m.index)
        out["n_covered"] = int(is_covered.sum())
        out["kappa_covered"] = kappa(m.origin[is_covered], m.stored[is_covered])
        out["kappa_uncovered"] = kappa(m.origin[~is_covered], m.stored[~is_covered])
    if blind is not None:
        b = m.merge(blind[on + ["blind_origin"]], on=on)
        out["kappa_blind_vs_reader"] = kappa(b.origin, b.blind_origin)
        out["kappa_blind_vs_raw"] = kappa(b.raw, b.blind_origin)
        out["n_blind"] = len(b)
    out["gate_origin"] = "raw"
    out["pass"] = bool(out["kappa_raw"] is not None and out["kappa_raw"] >= kappa_min and gap <= gap_max)
    return out


def coverage_by_group() -> dict[str, float]:
    """Share of pilot pairs, per group, with at least one stored pre-entry record."""
    pilot = pd.read_csv(PILOT_CSV, dtype=str)
    keys = tuple(zip(pilot.ensembl_id, pilot.mondo_id))
    unsearched = set(keys) - searched()
    if unsearched:
        raise SystemExit(f"{len(unsearched)} pilot pairs have not been searched; run `search --pairs pilot` first")
    have = frame.query(COVERED_SQL, (keys, ORIGIN_SERVICES))
    have = set(zip(have.ensembl_id, have.mondo_id))
    pilot["covered"] = [(e, m) in have for e, m in zip(pilot.ensembl_id, pilot.mondo_id)]
    return pilot.groupby("group").covered.mean().to_dict()



def blind_reference(keys: set[str] | None = None) -> tuple[pd.DataFrame, dict]:
    """The majority origin of the blind readings per pair (those in keys when given), and their consistency."""
    d = llm.latest_decisions(BLIND_TASK.name, BLIND_TASK.prompt_version)
    readings = [(k, o["origin"]) for k, o in zip(d.key, d.parsed_output) if keys is None or key(*split_key(k)) in keys]
    return majority_reference(readings)


def stored_labels(pairs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The labelled rows of the pairs after the check (ensembl_id, mondo_id, origin, grade, check_outcome) and the
    labeller's raw origin and secondary origin read from each row's own decision."""
    on = ["ensembl_id", "mondo_id"]
    stored = frame.query("""SELECT o.ensembl_id, o.mondo_id, o.origin, o.grade, o.check_outcome,
                                   d.parsed_output->>'origin' AS raw, d.parsed_output->>'secondary_origin' AS secondary_origin
                            FROM preclin.target_disease_origin o JOIN pv_evidence.llm_decision d USING (llm_decision_id)
                            WHERE o.basis = 'labelled' AND (o.ensembl_id, o.mondo_id) IN %s""",
                         (tuple(zip(pairs.ensembl_id, pairs.mondo_id)),))
    raw = stored[on + ["raw", "secondary_origin"]].rename(columns={"raw": "origin"})
    return stored[on + ["origin", "grade", "check_outcome"]], raw


def gate(args) -> None:
    import json
    pairs = pair_frame(f"set_{args.set}")
    reference, consistency = blind_reference({key(e, m) for e, m in zip(pairs.ensembl_id, pairs.mondo_id)})
    if args.hand_check:
        reader = pd.read_csv(args.hand_check, dtype=str)
        missing = {"ensembl_id", "mondo_id", "origin"} - set(reader.columns)
        if missing:
            raise SystemExit(f"{args.hand_check} lacks columns {sorted(missing)}")
        reader = reader[reader.origin.notna() & reader.origin.ne("")]
        bad = sorted(set(reader.origin) - set(ORIGINS))
        if bad:
            raise SystemExit(f"origins outside the list: {bad}")
        blind = reference.rename(columns={"origin": "blind_origin"}) if len(reference) else None
    else:
        reader, blind = reference, None
    stored, raw = stored_labels(pairs)
    have = frame.query(COVERED_SQL, (tuple(zip(pairs.ensembl_id, pairs.mondo_id)), ORIGIN_SERVICES))
    covered = set(zip(have.ensembl_id, have.mondo_id))
    result = gate_result(reader, stored, raw, coverage_by_group(), blind, covered=covered)
    runs = frame.query("SELECT method_id, parameters FROM preclin.analysis_method WHERE method_id IN %s",
                       ((LABEL_METHOD, CHECK_METHOD, BLIND_METHOD),))
    result.update({"set": args.set, "reader": args.reader, "read_pairs": len(reader),
                   "labelled_in_set": len(stored), "kappa_min": KAPPA_MIN, "gap_max": GAP_MAX,
                   "graded_not_checked": int((stored.grade.ne("none") & stored.check_outcome.eq("not_checked")).sum()),
                   "runs": {m: (par.get("runs") or par.get("run")) for m, par in zip(runs.method_id, runs.parameters)},
                   "reference": "hand check" if args.hand_check else "blind model reading, majority of replicates",
                   "consistency": consistency})
    with open(GATE_JSON, "w") as f:
        json.dump(result, f, indent=2)
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, GATE_METHOD, "Pilot gates of the origin labelling", GATE_DESCRIPTION,
                          ["preclin.target_disease_origin", "preclin.target_disease_source", "pv_evidence.llm_decision",
                           args.hand_check], result)
        conn.commit()
    log(json.dumps(result, indent=2))
    log(gate_message(result) + f"; written {GATE_JSON}")


def gate_message(result: dict) -> str:
    """One line naming the kappa the gate is scored on (the label as read) and the stored-origin kappa beside it."""
    fmt = lambda k: "None" if k is None else f"{k:.2f}"
    return (f"gate {'PASSED' if result['pass'] else 'FAILED'}: kappa {fmt(result['kappa_raw'])} on the label as read "
            f"(min {KAPPA_MIN}; stored {fmt(result['kappa_stored'])}), coverage gap {result['gap_points']} points "
            f"(max {GAP_MAX})")


def summary(args) -> None:
    pairs = pair_frame(args.pairs)
    on = ["ensembl_id", "mondo_id"]
    o = frame.query("""SELECT ensembl_id, mondo_id, origin, grade, check_outcome, discovery_route
                       FROM preclin.target_disease_origin WHERE basis = 'labelled' AND (ensembl_id, mondo_id) IN %s""",
                    (tuple(zip(pairs.ensembl_id, pairs.mondo_id)),))
    have = frame.query(COVERED_SQL, (tuple(zip(pairs.ensembl_id, pairs.mondo_id)), ORIGIN_SERVICES))
    p = pairs.merge(have, on=on, how="left").fillna({"records": 0})
    log(f"{len(pairs)} pairs in {args.pairs}: {int((p.records > 0).sum())} with records "
        f"(median {int(p.records.median())}, max {int(p.records.max())}); {len(o)} labelled")
    if "group" in p.columns:
        log("coverage by group:\n" + p.groupby("group").records.apply(lambda r: (r > 0).mean()).round(3).to_string())
    if len(o):
        for col in ["origin", "grade", "check_outcome", "discovery_route"]:
            log(f"{col}:\n" + o[col].value_counts(dropna=False).to_string())
        if "group" in p.columns:
            log(pd.crosstab(o.merge(p[on + ["group"]], on=on).group, o.origin).to_string())
    usage = frame.query("""SELECT d.task, count(*) AS n, avg((d.usage->>'input_tokens')::float) AS input_tokens,
                                  avg((d.usage->>'output_tokens')::float) AS output_tokens
                           FROM pv_evidence.llm_decision d
                           WHERE d.task IN %s AND d.validation_status = 'validated'
                             AND split_part(d.subject_key, '|', 1) || '|' || split_part(d.subject_key, '|', 2) IN %s
                           GROUP BY 1""",
                        ((LABEL_TASK.name, CHECK_TASK.name, BLIND_TASK.name),
                         tuple(key(e, m) for e, m in zip(pairs.ensembl_id, pairs.mondo_id))))
    if len(usage):
        log("tokens per decision:\n" + usage.round(0).to_string(index=False))


# --- command line ---

def add_commands(sub) -> None:
    """Register the origin commands on pipeline.target_disease's subparsers."""
    def pairs_option(p, default="pilot"):
        p.add_argument("--pairs", choices=PAIR_SETS, default=default, help="which pairs to work on")

    p = sub.add_parser("search", help="retrieve pre-entry PubMed and Europe PMC records per pair")
    pairs_option(p)
    p.add_argument("--redo", action="store_true", help="search pairs already searched")
    p.add_argument("--max-records", type=int, default=None, help="keep only the earliest N records per service")
    p.set_defaults(fn=search)
    p = sub.add_parser("label", help="label the origin and discovery route of each pair from its sources")
    pairs_option(p)
    p.add_argument("--hide-provisional", action="store_true", help="do not show the model the provisional origin")
    p.set_defaults(fn=label)
    p = sub.add_parser("check", help="second-model check of each graded label")
    pairs_option(p)
    p.set_defaults(fn=check)
    p = sub.add_parser("blind", help="second model labels a hand-check set from the records alone")
    pairs_option(p, default="set_a")
    p.set_defaults(fn=blind)
    p = sub.add_parser("sample", help="draw the pilot of 100 pairs and the two hand-check sets")
    p.add_argument("--force", action="store_true", help="redraw even though the pilot CSV exists")
    p.set_defaults(fn=sample)
    p = sub.add_parser("package", help="write the reader's page for a hand-check set")
    p.add_argument("--set", choices=["a", "b"], default="a")
    p.add_argument("--out", required=True, help="path of the HTML file to write")
    p.set_defaults(fn=package)
    p = sub.add_parser("gate", help="score the pilot against the reader's sheet")
    p.add_argument("--hand-check", default=None,
                   help="a human reader's CSV; without it the blind model reading is the reference")
    p.add_argument("--reader", default="model", help="who read the set")
    p.add_argument("--set", choices=["a", "b"], default="a")
    p.set_defaults(fn=gate)
    p = sub.add_parser("summary", help="labels, grades, check outcomes and coverage")
    pairs_option(p)
    p.set_defaults(fn=summary)
