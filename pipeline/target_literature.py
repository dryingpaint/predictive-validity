"""Published evidence about a target's biology in a disease, as known the year before a phase entry (issue #154).

    python -m pipeline.target_literature sample       # the seeded pilot of 300 pairs (report/audits/target_literature_pilot.csv)
    python -m pipeline.target_literature names        # LLM: vet each gene's names; list each disease's model terms
    python -m pipeline.target_literature search       # PubMed and Europe PMC by gene names and disease names/models
    python -m pipeline.target_literature firecrawl --mode search|related   # Firecrawl, per pair and kind / related papers
    python -m pipeline.target_literature screen       # LLM: prefilter large literatures, then screen every record
    python -m pipeline.target_literature check        # second model on a seeded sample of screened records
    python -m pipeline.target_literature prefilter-check   # full screen of a seeded sample the prefilter dropped
    python -m pipeline.target_literature reference --rows 1-100   # blind web-enabled model lists every study per kind
    python -m pipeline.target_literature gate --rows 1-100 --label v1   # recall, agreement and coverage gates
    python -m pipeline.target_literature cost         # the pilot's measured cost and its extrapolation

The unit is a target-disease pair (preclin.target_disease) with a US-sited phase entry of 2008-2019 in the stored
evidence dataset (preclin.evidence_entry). A pair is searched up to its cutoff, the year before its latest such
entry; each entry then counts only records published by the year before its own entry.

Seven kinds of evidence about the target, each needing original data on the target (not the program's drug, except
as kind 4's flag) in the pair's disease, a subtype or a near-identical disease:
- human_cell_perturbation (#159 row 8): changing the target in primary human cells or tissue changes a disease feature;
- cell_line_perturbation: the same in an established cell line (the literature part of cell-line perturbation);
- diseased_tissue_protein (row 6 tier): the target's protein differs in patients' diseased tissue (not bulk RNA);
- animal_model_pharmacology (row 9): a non-genetic change to the target alters an animal model of the disease, with
  agent_is_program_drug recording whether the only agent is one of the pair's program drugs (the registered L2 counts
  only other agents);
- mouse_genetic_disease_model (row 4 tier): a knockout or transgene of the target alters an animal model;
- observational_biomarker (row 7): the target or its product, measured in blood, another fluid or by imaging, tracks
  the disease in an observational study;
- clinical_observation (row 10): an effect seen in people that implicates the target, such as another drug's side effect.

Retrieval per pair: PubMed and Europe PMC (outside MEDLINE) titles and abstracts naming the gene (HGNC symbol and its
names, vetted by an LLM, which drops ambiguous aliases and may add common protein names) and the disease (MONDO label
and synonyms) or one of its experimental models (terms an LLM lists per disease, such as collagen-induced arthritis),
reviews excluded; Firecrawl's research index once per pair and kind, and once for papers related to the pair's first
screened-in record. A pair with more than PREFILTER_ABOVE records gets a cheap prefilter first. A second model
relabels a seeded sample; a blind web-enabled model lists every study of each kind for pilot rows 1-100, the
reference for recall. The plan's gates (recall >= 0.8, kappa >= 0.6, Phase 2 coverage >= 0.08) decide which kinds
run on every pair, after the pilot's measured cost is approved.

Version 1 failed every gate on rows 1-100. Version 2, the one revision #154 allows, fixed before its reference
was built: gene names may add the receptor or complex names papers use for the protein; the disease's direct MONDO
subtypes are searched with its names; the prefilter applies above 3,000 records, as registered; the screen first
names the system of the paper's main finding and reads tighter kind definitions (clinical observations exclude
efficacy trials in the disease). It is scored on rows 101-200 against a fresh reference. Every reference PMID is
checked against the title the model gave (verify_pmids).
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
from psycopg2.extras import Json, execute_values

from pipeline import llm, throttle
from pipeline.outcomes import eutils
from pipeline.attribution import NOT_REVIEWS
from pipeline.literature import (FIRECRAWL_BACKOFF_MAX, FIRECRAWL_PER_SECOND, FIRECRAWL_RESULTS, FIRECRAWL_WORKERS,
                                 GATES, FirecrawlError, SourceDown, clean, epmc_records, fetch_papers, firecrawl_cli,
                                 firecrawl_credits, firecrawl_ids, kappa, names_clause, pubmed_ids, resolve_external,
                                 stored_papers, store_records)

KINDS = ("human_cell_perturbation", "cell_line_perturbation", "diseased_tissue_protein", "animal_model_pharmacology",
         "mouse_genetic_disease_model", "observational_biomarker", "clinical_observation")
KIND_TEXT = {
    "human_cell_perturbation": "the target is changed experimentally (knockdown, knockout, overexpression, or a tool "
                               "compound, antibody or drug acting on it) in PRIMARY human cells or tissue, explicitly "
                               "primary: cells isolated from patients or donors, primary cultures, organoids, "
                               "iPSC-derived cells, or explants of patient tissue; and a feature of the disease changes",
    "cell_line_perturbation": "the same in an ESTABLISHED cell line (HeLa, HEK293, named cancer lines and the like); "
                              "genome-wide screens count",
    "diseased_tissue_protein": "the target's PROTEIN is measured (immunohistochemistry, western blot, ELISA, mass "
                               "spectrometry, activity assay, or single-cell protein methods) in patients' diseased "
                               "tissue and differs from normal or less-affected tissue; RNA-only measurements do not count",
    "animal_model_pharmacology": "a NON-GENETIC change to the target (tool compound, antibody, antisense, siRNA, viral "
                                 "vector, or a drug acting on it) alters an animal model of the disease",
    "mouse_genetic_disease_model": "a knockout, knock-in or transgene of the target alters an animal model of the "
                                   "disease, or the genetically altered animal develops the disease",
    "observational_biomarker": "an OBSERVATIONAL study of patients (no intervention assigned) measures the target or its "
                               "product in blood, another body fluid or by imaging, and the measurement goes with the "
                               "disease's presence, severity, progression or outcome; tissue measurements, genetic "
                               "association and drug-response markers in a trial do not count",
    "clinical_observation": "an effect seen in people, outside a trial of a drug for this disease, implicates the target "
                            "in the disease: a side effect or unexpected benefit of a drug acting on the target in "
                            "another setting, people with the target deficient or blocked (case reports, natural "
                            "experiments), or autoantibodies against the target; efficacy trials of drugs in this "
                            "disease do not count",
}
VERSION = "v2"  # v1 (14b38ea) failed every gate; v2 is the registered single revision, scored on rows 101-200
COHORT = (2008, 2019)  # phase entry years of the evidence dataset
PILOT_N = 300
PILOT_SEED = 20261122
PILOT_CSV = os.path.join(llm.REPO, "report", "audits", "target_literature_pilot.csv")
GATE = os.path.join(llm.REPO, "report", "audits", "target_literature_gate.json")
REFERENCE_DIR = os.path.join(llm.REPO, "report", "audits", "target_literature_reference")
MAX_GENE_NAMES = 16
MAX_DISEASE_NAMES = 20
MAX_SUBTYPE_NAMES = 15  # labels of the disease's direct MONDO subtypes searched as disease names (v2)
MAX_MODEL_TERMS = 10
PREFILTER_ABOVE = 3000  # records per pair above which a cheap model reads each record first (as #154 registered; v1 used 500)
PREFILTER_CHECK = 300  # seeded prefiltered-out records given the full screen, to measure the prefilter's misses
CHECK_PER_KIND = 50  # half screened in, half screened out, per kind
CHECK_SEED = 20261123
SCREEN_MODEL = "claude-sonnet-5"
PREFILTER_MODEL = "claude-haiku-4-5-20251001"  # the id pipeline.literature runs
CHECK_MODEL = "claude-opus-5-5"
REFERENCE_MODEL = "claude-opus-5-5"
REFERENCE_TOOLS = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 12},
                   {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 6}]
METHOD = "target_literature@v1"
ABSTRACT_CHARS = 4000


# --- pairs ---------------------------------------------------------------------------------------------------------

def cohort_entries() -> pd.DataFrame:
    """Every stored 2008-2019 phase entry with a target and a disease, once per primary target gene that forms a
    pair in preclin.target_disease: moiety_id, mondo_id, phase, entry_year, ensembl_id."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT e.moiety_id, e.mondo_id, e.phase, e.entry_year, t.ensembl_id
                       FROM preclin.evidence_entry e
                       JOIN preclin.moiety_target mt ON mt.moiety_id = e.moiety_id AND mt.is_primary
                       JOIN public.targets t ON t.id = mt.target_id
                       JOIN preclin.target_disease td ON td.ensembl_id = t.ensembl_id AND td.mondo_id = e.mondo_id
                       WHERE e.has_target_disease AND e.mondo_id <> ''""")
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=["moiety_id", "mondo_id", "phase", "entry_year", "ensembl_id"])


def cohort_pairs() -> pd.DataFrame:
    """ensembl_id, mondo_id, cutoff_year (the year before the pair's latest cohort entry), symbol and disease label."""
    e = cohort_entries()
    p = e.groupby(["ensembl_id", "mondo_id"], as_index=False).entry_year.max()
    p["cutoff_year"] = p.pop("entry_year") - 1
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT td.ensembl_id, td.mondo_id, td.symbol, o.label FROM preclin.target_disease td
                       LEFT JOIN preclin.ontology_term o ON o.term_id = td.mondo_id""")
        meta = pd.DataFrame(cur.fetchall(), columns=["ensembl_id", "mondo_id", "symbol", "disease"])
    return p.merge(meta, on=["ensembl_id", "mondo_id"]).sort_values(["ensembl_id", "mondo_id"]).reset_index(drop=True)


def sample(_args) -> None:
    """Draw the seeded pilot of PILOT_N cohort pairs, numbered 1..PILOT_N in draw order."""
    p = cohort_pairs()
    rng = np.random.default_rng(PILOT_SEED)
    s = p.iloc[rng.choice(len(p), PILOT_N, replace=False)].reset_index(drop=True)
    s.insert(0, "row", range(1, len(s) + 1))
    s.to_csv(PILOT_CSV, index=False)
    print(f"pilot: {len(s)} of {len(p)} cohort pairs -> {PILOT_CSV}")


def pilot_pairs() -> pd.DataFrame:
    return pd.read_csv(PILOT_CSV)


def pair_key(ensembl_id: str, mondo_id: str) -> str:
    return f"{ensembl_id}|{mondo_id}"


# --- names ---------------------------------------------------------------------------------------------------------

def gene_candidates(genes: list[str]) -> dict[str, dict]:
    """Ensembl id -> {symbol, name, candidates}: the HGNC symbol first, then the approved name, the target's name,
    previous and alias symbols, case-insensitively distinct, at most MAX_GENE_NAMES. Symbols are kept whatever their
    length; the vet drops the ambiguous ones."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT g.ensembl_id, g.symbol, g.name, g.prev_symbols, g.alias_symbols,
                              (SELECT string_agg(DISTINCT t.name, '|') FROM public.targets t WHERE t.ensembl_id = g.ensembl_id)
                       FROM preclin.hgnc_gene g WHERE g.ensembl_id = ANY(%s)""", (genes,))
        rows = cur.fetchall()
    out = {}
    for ens, symbol, name, prev, alias, tnames in rows:
        cands: list[str] = []
        for n in [symbol, name, *(tnames or "").split("|"), *(prev or []), *(alias or [])]:
            n = clean(n or "")
            if 2 <= len(n) <= 60 and n.lower() not in {c.lower() for c in cands}:
                cands.append(n)
        out[ens] = {"symbol": symbol, "name": name, "candidates": cands[:MAX_GENE_NAMES]}
    return out


GENE_VET_SYSTEM = """You vet the names used to search titles and abstracts for papers about one human gene or its protein. The search requires a gene name AND a disease name in the same title or abstract, so a name must, in that context, almost always mean THIS gene or protein.

Keep the official symbol and full name, the protein's common names, and aliases papers really use for it. Drop aliases that are common words or abbreviations with other meanings (CAT, MET when it would match methionine or metformin papers, SET, PC, CO, AIM), names of other genes or protein families, and names so generic that most papers using them mean something else. A symbol that is also a common abbreviation is kept only when, next to a disease name, it still almost always means this gene.

You may add up to five names papers commonly use for this protein that are missing from the candidates (for example "TNF-alpha" or "tumour necrosis factor alpha" for TNF, "IL-6" for IL6, "PD-1" for PDCD1), each at most four words. When the protein works as part of a receptor, channel or complex that papers usually name instead of the gene (for example "glycoprotein IIb/IIIa" for ITGA2B, "GABA-A receptor alpha1" for GABRA1, "NMDA receptor" for GRIN1), you may add up to three such names, counted in the five.

Return the candidates to keep, copied exactly, and any added names."""

GENE_VET_SCHEMA = {"type": "object", "additionalProperties": False,
                   "properties": {"keep": {"type": "array", "items": {"type": "string"}},
                                  "add": {"type": "array", "items": {"type": "string"}}},
                   "required": ["keep", "add"]}


def render_gene_vet(p: dict) -> str:
    return "\n".join([f"Gene: {p['symbol']} ({p['name']})", "", "Candidate names:"] + [f"- {n}" for n in p["candidates"]])


def validate_gene_vet(p: dict, out: dict) -> None:
    if not out["keep"] and not out["add"]:
        raise ValueError("keep or add at least one name")
    extra = [n for n in out["keep"] if n not in p["candidates"]]
    if extra:
        raise ValueError(f"names not among the candidates: {extra[:3]}")
    if len(out["add"]) > 10 or any(len(n.split()) > 6 for n in out["add"]):
        raise ValueError("at most ten added names of at most six words")


def gene_vet_task(model: str = SCREEN_MODEL, suffix: str = "") -> llm.Task:
    return llm.Task(name="target_literature_gene_vet" + suffix, prompt_version=VERSION, schema_version="v1",
                    system=GENE_VET_SYSTEM, schema=GENE_VET_SCHEMA, render=render_gene_vet, validate=validate_gene_vet,
                    subject_type="gene", model=model, effort="low", max_tokens=2000)


MODEL_TERMS_SYSTEM = """You list the terms experimental papers use for models of one human disease, so a literature search can find animal and cell studies that name the model rather than the disease.

List up to ten established model names as they appear in titles and abstracts: induced or genetic animal models ("collagen-induced arthritis", "experimental autoimmune encephalomyelitis", "DSS colitis", "db/db mice", "APP/PS1 mice"), named xenograft or cell models when they are specific to the disease, and behavioural assays used only as models of it ("forced swim test" for depression). Each term at most five words. Do not list the disease's own names or synonyms, generic words (model, mice, in vitro), or models of other diseases. Return an empty list when the disease has no established named models."""

MODEL_TERMS_SCHEMA = {"type": "object", "additionalProperties": False,
                      "properties": {"terms": {"type": "array", "items": {"type": "string"}}}, "required": ["terms"]}


def render_model_terms(p: dict) -> str:
    return f"Disease: {p['label']}\nSynonyms: {', '.join(p['synonyms']) or 'none'}"


def validate_model_terms(_p: dict, out: dict) -> None:
    if len(out["terms"]) > 2 * MAX_MODEL_TERMS or any(len(t) < 3 for t in out["terms"]):
        raise ValueError("at most twenty terms of at least three characters")


MODEL_TERMS_TASK = llm.Task(name="target_literature_model_terms", prompt_version="v1", schema_version="v1",
                            system=MODEL_TERMS_SYSTEM, schema=MODEL_TERMS_SCHEMA, render=render_model_terms,
                            validate=validate_model_terms, subject_type="mondo", model=SCREEN_MODEL, effort="low",
                            max_tokens=2000)


def disease_names(mondos: list[str]) -> dict[str, dict]:
    """MONDO id -> {label, synonyms}: the label, then synonyms shortest first, case-insensitively distinct, at most
    MAX_DISEASE_NAMES names."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT term_id, label, synonyms FROM preclin.ontology_term WHERE term_id = ANY(%s)", (mondos,))
        rows = cur.fetchall()
        cur.execute("""SELECT i.parent_id, t.label FROM preclin.ontology_is_a i JOIN preclin.ontology_term t ON t.term_id = i.child_id
                       WHERE i.ontology = 'MONDO' AND i.parent_id = ANY(%s) AND NOT t.is_obsolete""", (mondos,))
        subtypes: dict[str, list[str]] = {}
        for parent, label in cur.fetchall():
            subtypes.setdefault(parent, []).append(label)
    out = {}
    for term, label, syns in rows:
        names: list[str] = []
        for n in [label, *sorted(syns or [], key=len)]:
            n = clean(n or "")
            if 3 <= len(n) <= 80 and n.lower() not in {x.lower() for x in names}:
                names.append(n)
        subs = [clean(x) for x in sorted(subtypes.get(term, []), key=len) if 3 <= len(clean(x)) <= 80
                and clean(x).lower() not in {n.lower() for n in names}][:MAX_SUBTYPE_NAMES]
        out[term] = {"label": label, "synonyms": names[1:MAX_DISEASE_NAMES], "names": names[:MAX_DISEASE_NAMES] + subs}
    return out


def pair_names(pairs: pd.DataFrame, run: bool = True) -> dict[str, dict]:
    """Pair key -> {"gene": [...], "disease": [...], "models": [...]}: the vetted gene names, the disease names and the
    disease's model terms. With run, missing decisions are made first."""
    genes = sorted(set(pairs.ensembl_id))
    mondos = sorted(set(pairs.mondo_id))
    cands = gene_candidates(genes)
    gitems = {g: v for g, v in cands.items() if v["candidates"]}
    t = gene_vet_task()
    got = llm.current_decisions(t, gitems)
    if run and len(got) < len(gitems):
        llm.run(t, {k: v for k, v in gitems.items() if k not in got})
        got = llm.current_decisions(t, gitems)
    gene = {g: list(dict.fromkeys(o["keep"] + [clean(n) for n in o["add"][:5] if len(n.split()) <= 4]))
            for g, (_, o) in got.items()}
    for g, v in cands.items():  # a gene the vet could not decide is searched by its symbol and name
        gene.setdefault(g, [n for n in (v["symbol"], v["name"]) if n])
    dis = disease_names(mondos)
    ditems = {m: {"label": v["label"], "synonyms": v["synonyms"]} for m, v in dis.items()}
    got = llm.current_decisions(MODEL_TERMS_TASK, ditems)
    if run and len(got) < len(ditems):
        llm.run(MODEL_TERMS_TASK, {k: v for k, v in ditems.items() if k not in got})
        got = llm.current_decisions(MODEL_TERMS_TASK, ditems)
    models = {m: [clean(x) for x in o["terms"] if len(x.split()) <= 5][:MAX_MODEL_TERMS] for m, (_, o) in got.items()}
    return {pair_key(r.ensembl_id, r.mondo_id): {"gene": gene.get(r.ensembl_id, []),
                                                 "disease": dis.get(r.mondo_id, {}).get("names", []),
                                                 "models": models.get(r.mondo_id, [])}
            for r in pairs.itertuples()}


def names(_args) -> None:
    n = pair_names(pilot_pairs())
    print(f"names: pairs={len(n)} without gene names={sum(not v['gene'] for v in n.values())}")


# --- retrieval -----------------------------------------------------------------------------------------------------

def epmc_clause(names: list[str]) -> str:
    return f'({" OR ".join(f"TITLE_ABS:{chr(34)}{n}{chr(34)}" for n in names)})'


def clauses(n: dict) -> tuple[str, str]:
    """The PubMed and Europe PMC clauses of one pair: a gene name and a disease name or model term."""
    dm = n["disease"] + [m for m in n["models"] if m.lower() not in {d.lower() for d in n["disease"]}]
    return (f"{names_clause(n['gene'])} AND {names_clause(dm)}", f"{epmc_clause(n['gene'])} AND {epmc_clause(dm)}")


def store_search(cur, e: str, m: str, y: int, source: str, kind: str, n: dict, query: str, n_hits: int,
                 record_ids: list[str]) -> None:
    cur.execute("""DELETE FROM preclin.target_literature_hit WHERE ensembl_id = %s AND mondo_id = %s AND cutoff_year = %s
                   AND source = %s AND %s = ''""", (e, m, y, source, kind))
    cur.execute("""INSERT INTO preclin.target_literature_search (ensembl_id, mondo_id, cutoff_year, source, kind, names,
                                                                 query, n_hits)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (ensembl_id, mondo_id, cutoff_year, source, kind)
                   DO UPDATE SET names = EXCLUDED.names, query = EXCLUDED.query, n_hits = EXCLUDED.n_hits,
                                 searched_at = now()""", (e, m, y, source, kind, Json(n), query, n_hits))
    if record_ids:
        execute_values(cur, """INSERT INTO preclin.target_literature_hit (ensembl_id, mondo_id, cutoff_year, source, record_id)
                               VALUES %s ON CONFLICT DO NOTHING""", [(e, m, y, source, r) for r in record_ids],
                       page_size=5000)


def search(_args) -> None:
    """PubMed and Europe PMC for every pilot pair not yet searched with its current names; PubMed abstracts not in
    public.publications are fetched and stored. Each pair is committed before the next."""
    p = pilot_pairs()
    nm = pair_names(p)
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, METHOD, "Published evidence about the target's biology before phase entry (#154)",
                          __doc__, ["PubMed", "Europe PMC", "Firecrawl research index", "preclin.hgnc_gene",
                                    "preclin.ontology_term", "preclin.target_disease", "preclin.evidence_entry"],
                          {"prefilter_above": PREFILTER_ABOVE, "max_gene_names": MAX_GENE_NAMES,
                           "max_disease_names": MAX_DISEASE_NAMES, "max_model_terms": MAX_MODEL_TERMS})
        cur.execute("""SELECT ensembl_id, mondo_id, cutoff_year, names FROM preclin.target_literature_search
                       WHERE source = 'pubmed'""")
        done = {(e, m, y): n for e, m, y, n in cur.fetchall()}
        conn.commit()
    todo = [r for r in p.itertuples() if done.get((r.ensembl_id, r.mondo_id, int(r.cutoff_year)))
            != nm[pair_key(r.ensembl_id, r.mondo_id)] and nm[pair_key(r.ensembl_id, r.mondo_id)]["gene"]]
    print(f"search: pairs={len(p)} to search={len(todo)}", flush=True)
    for i, r in enumerate(todo, 1):
        n, y = nm[pair_key(r.ensembl_id, r.mondo_id)], int(r.cutoff_year)
        pm, ep = clauses(n)
        for attempt in range(3):
            try:
                pq, pn, pmids = pubmed_ids([], y, term=lambda lo, hi, pm=pm: f'{pm} AND ("{lo}"[dp] : "{hi}"[dp]) {NOT_REVIEWS}')
                eq, en, records = epmc_records([], y, query=f'{ep} AND PUB_YEAR:[1900 TO {y}] AND NOT SRC:MED '
                                                            'AND HAS_ABSTRACT:Y AND NOT PUB_TYPE:"review"')
                break
            except (SourceDown, RuntimeError) as err:
                print(f"retry {r.symbol} {r.mondo_id}: {err}", flush=True)
                time.sleep(60 * (attempt + 1))
        else:
            print(f"skipped {r.symbol} {r.mondo_id}: search failed", flush=True)
            continue
        have = set(stored_papers(pmids))
        missing = [x for x in pmids if x not in have]
        for start in range(0, len(missing), 1000):
            fetch_papers(missing[start:start + 1000], store=True)
        with llm.connect() as conn, conn.cursor() as cur:
            store_records(cur, records)
            store_search(cur, r.ensembl_id, r.mondo_id, y, "pubmed", "", n, pq, pn, pmids)
            store_search(cur, r.ensembl_id, r.mondo_id, y, "europepmc", "", n, eq, en, [x[0] for x in records])
            conn.commit()
        print(f"[{i}/{len(todo)}] {r.symbol} x {r.disease}: pubmed={len(pmids)}/{pn} europepmc={len(records)} "
              f"fetched={len(missing)}", flush=True)


def firecrawl_query(symbol: str, gene: list[str], disease: str, kind: str) -> str:
    alias = f" ({', '.join(gene[1:4])})" if len(gene) > 1 else ""
    return f"{symbol}{alias} in {disease}: {KIND_TEXT[kind].split(';')[0]}"


def firecrawl(args) -> None:
    """Firecrawl's research index for the pilot pairs: --mode search runs one semantic search per pair and kind;
    --mode related, papers related to each pair's first screened-in record. Results dated after the cutoff are dropped;
    ids outside PubMed resolve through Europe PMC. A failed call is not recorded, so a later run retries it."""
    from concurrent.futures import ThreadPoolExecutor
    p = pilot_pairs()
    nm = pair_names(p, run=False)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT ensembl_id, mondo_id, source, kind FROM preclin.target_literature_search WHERE source LIKE 'firecrawl%%'")
        done = set(cur.fetchall())
        cur.execute(f"""SELECT DISTINCT ON (ensembl_id, mondo_id) ensembl_id, mondo_id, record_id
                        FROM preclin.target_literature_screen
                        WHERE original_data AND disease_match = 'same_or_subtype' AND ({" OR ".join(KINDS)})
                        ORDER BY ensembl_id, mondo_id, record_id""")
        seeds = {(e, m): rid for e, m, rid in cur.fetchall()}
    if args.mode == "search":
        calls = [(r, k) for r in p.itertuples() for k in KINDS
                 if (r.ensembl_id, r.mondo_id, "firecrawl", k) not in done and nm[pair_key(r.ensembl_id, r.mondo_id)]["gene"]]
    else:
        calls = [(r, "") for r in p.itertuples() if (r.ensembl_id, r.mondo_id) in seeds
                 and (r.ensembl_id, r.mondo_id, "firecrawl_related", "") not in done]
    before = firecrawl_credits()
    print(f"firecrawl {args.mode}: calls={len(calls)} credits={before}", flush=True)
    state = {"done": 0, "failed": 0, "stop": None, "wait": 30}

    def one(call) -> None:
        r, k = call
        n, y = nm[pair_key(r.ensembl_id, r.mondo_id)], int(r.cutoff_year)
        if args.mode == "search":
            q = firecrawl_query(r.symbol, n["gene"], r.disease, k)
            cli = ["search-papers", q, "--limit", str(FIRECRAWL_RESULTS), "--to", f"{y}-12-31"]
            source = "firecrawl"
        else:
            seed = seeds[(r.ensembl_id, r.mondo_id)]
            q = f"{'pmid:' + seed if seed.isdigit() else seed} | similar | {r.symbol} in {r.disease}"
            cli = ["related-papers", f"pmid:{seed}" if seed.isdigit() else seed, "--intent",
                   f"{r.symbol} in {r.disease}: experimental or clinical evidence about the target in the disease",
                   "--mode", "similar", "--limit", str(FIRECRAWL_RESULTS)]
            source = "firecrawl_related"
        while state["stop"] is None:
            try:
                throttle.wait("firecrawl", FIRECRAWL_PER_SECOND)
                results = firecrawl_cli(cli)
                state["wait"] = 30
                break
            except FirecrawlError as err:
                if err.out_of_credits:
                    state["stop"] = f"out of credits: {err}"
                    return
                if not err.rate_limited:
                    state["failed"] += 1
                    print(f"firecrawl failed {r.symbol} {r.mondo_id} {k}: {err}", flush=True)
                    return
                wait = state["wait"]
                state["wait"] = min(FIRECRAWL_BACKOFF_MAX, wait * 2)
                time.sleep(wait)
        else:
            return
        got = firecrawl_ids(results, y)
        external = resolve_external([g for g in got if not g[0].isdigit()])
        ids = sorted({g if g.isdigit() else external[g] for g, _ in got if g.isdigit() or g in external})
        pmids = [x for x in ids if x.isdigit()]
        have = set(stored_papers(pmids))
        if [x for x in pmids if x not in have]:
            fetch_papers([x for x in pmids if x not in have], store=True)
        with llm.connect() as conn, conn.cursor() as cur:
            store_search(cur, r.ensembl_id, r.mondo_id, y, source, k, n, q, len(results), ids)
            conn.commit()
        state["done"] += 1
        if state["done"] % 100 == 0:
            print(f"firecrawl {args.mode} {state['done']}/{len(calls)} failed={state['failed']}", flush=True)

    with ThreadPoolExecutor(FIRECRAWL_WORKERS) as pool:
        list(pool.map(one, calls))
    print(f"firecrawl {args.mode} finished: {state['done']}/{len(calls)} failed={state['failed']} credits "
          f"{before} -> {firecrawl_credits()}" + (f"; STOPPED, {state['stop']}" if state["stop"] else ""), flush=True)


# --- screen --------------------------------------------------------------------------------------------------------

SCREEN_SYSTEM = """You read one paper's title and abstract and decide what original evidence it reports about ONE human gene or its protein (the target) in ONE disease.

original_data: true when the paper reports new experimental or clinical results (not a review, commentary, guideline, protocol or case-free opinion).

disease_match: the disease the evidence is about, against the disease given: same_or_subtype (the same disease, a subtype of it, or a near-identical disease, including an animal or cell model of it), related (a related but distinct disease), other (an unrelated disease), or none (no disease studied).

kinds: true for each kind of evidence the paper reports about THIS target (under any of its names; a different gene of the same family does not count) in the disease named under disease_match, with original data:
""" + "\n".join(f"- {k}: {v}" for k, v in KIND_TEXT.items()) + """

system: the experimental or clinical system of the paper's main finding about the target: primary_human_cells, cell_line, patient_tissue, patient_fluid_or_imaging, animal_model, people_other (clinical observations outside a trial), trial (an interventional trial), or none. Decide it first; each kind's system must match: primary_human_cells for human_cell_perturbation, cell_line for cell_line_perturbation, patient_tissue for diseased_tissue_protein, animal_model for the two animal kinds, patient_fluid_or_imaging for observational_biomarker, people_other for clinical_observation. A paper with several findings may show kinds in other systems too.

A paper whose only agent is the program drug named below can show animal_model_pharmacology; mark agent_is_program_drug true then, false when another agent (a tool compound, antibody, siRNA, another drug) was used, and null when animal_model_pharmacology is false. Evidence must be about the target: a drug tested without the target being the point does not count, except under animal_model_pharmacology when the drug acts on this target. A kind is true only when the abstract states the finding; do not infer. Quote the sentence that decided the reading (empty when nothing qualifies)."""

SCREEN_SCHEMA = {"type": "object", "additionalProperties": False,
                 "properties": {"original_data": {"type": "boolean"},
                                "system": {"type": "string", "enum": ["primary_human_cells", "cell_line", "patient_tissue",
                                                                      "patient_fluid_or_imaging", "animal_model",
                                                                      "people_other", "trial", "none"]},
                                "disease_match": {"type": "string", "enum": ["same_or_subtype", "related", "other", "none"]},
                                "kinds": {"type": "object", "additionalProperties": False,
                                          "properties": {k: {"type": "boolean"} for k in KINDS}, "required": list(KINDS)},
                                "agent_is_program_drug": {"type": ["boolean", "null"]},
                                "quote": {"type": "string"}},
                 "required": ["original_data", "system", "disease_match", "kinds", "agent_is_program_drug", "quote"]}


def render_screen(p: dict) -> str:
    return "\n".join([f"Target: {p['symbol']} ({', '.join(p['gene'][:6])})",
                      f"Disease: {p['disease']}" + (f" (also: {', '.join(p['synonyms'][:5])})" if p["synonyms"] else ""),
                      f"Program drugs on this target in this disease: {', '.join(p['drugs']) or 'none'}", "",
                      f"Record {p['record_id']} ({p['year'] or 'year unknown'})", f"Title: {p['title']}",
                      f"Abstract: {p['abstract'] or '(no abstract)'}"])


def validate_screen(_p: dict, out: dict) -> None:
    if out["kinds"]["animal_model_pharmacology"] != (out["agent_is_program_drug"] is not None):
        raise ValueError("agent_is_program_drug is set exactly when animal_model_pharmacology is true")


def screen_task(model: str = SCREEN_MODEL, suffix: str = "") -> llm.Task:
    return llm.Task(name="target_literature_screen" + suffix, prompt_version=VERSION, schema_version=VERSION,
                    system=SCREEN_SYSTEM, schema=SCREEN_SCHEMA, render=render_screen, validate=validate_screen,
                    subject_type="pair_record", model=model, effort="medium", max_tokens=4000)


PREFILTER_SYSTEM = """You skim one title and abstract to decide whether it could report original data about a specific human gene or its protein in a specific disease, of any of these kinds: changing the target in cells or animals alters a disease feature or model; the target's protein differs in patients' tissue; the target or its product measured in patients tracks the disease; or an effect in people implicates the target. possibly is false only when the record clearly reports none of these (a review, a different gene or disease, only clinical outcomes of a drug, or genetics only). When unsure, answer true."""

PREFILTER_SCHEMA = {"type": "object", "additionalProperties": False,
                    "properties": {"possibly": {"type": "boolean"}}, "required": ["possibly"]}

PREFILTER_TASK = llm.Task(name="target_literature_prefilter", prompt_version="v1", schema_version="v1",
                          system=PREFILTER_SYSTEM, schema=PREFILTER_SCHEMA, render=render_screen,
                          subject_type="pair_record", model=PREFILTER_MODEL, effort=None, max_tokens=200)


def pair_drugs(pairs: pd.DataFrame) -> dict[tuple[str, str], list[str]]:
    """(ensembl_id, mondo_id) -> names of the entities with a primary target on the gene and a program in the disease."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT t.ensembl_id, p.mondo_id, m.name FROM preclin.dev_program p
                       JOIN preclin.moiety m USING (moiety_id)
                       JOIN preclin.moiety_target mt ON mt.moiety_id = p.moiety_id AND mt.is_primary
                       JOIN public.targets t ON t.id = mt.target_id
                       WHERE (t.ensembl_id, p.mondo_id) IN %s""",
                    (tuple(zip(pairs.ensembl_id, pairs.mondo_id)),))
        out: dict = {}
        for e, m, name in cur.fetchall():
            out.setdefault((e, m), []).append(name)
    return {k: sorted(v)[:8] for k, v in out.items()}


def pair_records(pairs: pd.DataFrame) -> pd.DataFrame:
    """ensembl_id, mondo_id, record_id of every record the pairs' searches returned at their cutoff."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE want (ensembl_id text, mondo_id text, cutoff_year int) ON COMMIT DROP")
        execute_values(cur, "INSERT INTO want VALUES %s",
                       [(r.ensembl_id, r.mondo_id, int(r.cutoff_year)) for r in pairs.itertuples()])
        cur.execute("""SELECT DISTINCT h.ensembl_id, h.mondo_id, h.record_id FROM preclin.target_literature_hit h
                       JOIN want USING (ensembl_id, mondo_id, cutoff_year)""")
        return pd.DataFrame(cur.fetchall(), columns=["ensembl_id", "mondo_id", "record_id"])


def screen_payloads(pairs: pd.DataFrame, recs: pd.DataFrame) -> dict[str, dict]:
    nm = pair_names(pairs, run=False)
    dis = disease_names(sorted(set(pairs.mondo_id)))
    drugs = pair_drugs(pairs)
    sym = dict(zip(zip(pairs.ensembl_id, pairs.mondo_id), pairs.symbol))
    papers = stored_papers(sorted(set(recs.record_id)))
    out = {}
    for r in recs.itertuples():
        paper = papers.get(r.record_id)
        if paper is None:
            continue
        title, abstract, year = paper
        k = (r.ensembl_id, r.mondo_id)
        out[f"{r.ensembl_id}|{r.mondo_id}|{r.record_id}"] = {
            "symbol": sym[k], "gene": nm[pair_key(*k)]["gene"], "disease": dis[r.mondo_id]["label"],
            "synonyms": dis[r.mondo_id]["synonyms"], "drugs": drugs.get(k, []), "record_id": r.record_id,
            "title": title, "abstract": (abstract or "")[:ABSTRACT_CHARS], "year": year}
    return out


def decide(task: llm.Task, items: dict[str, dict]) -> dict[str, tuple[int, dict]]:
    got = llm.current_decisions(task, items)
    if len(got) < len(items):
        llm.run(task, {k: v for k, v in items.items() if k not in got})
        got = llm.current_decisions(task, items)
    return got


def screen(_args) -> None:
    """Prefilter the records of pairs with more than PREFILTER_ABOVE, then screen every record that reaches the
    screen, storing both."""
    p = pilot_pairs()
    recs = pair_records(p)
    items = screen_payloads(p, recs)
    size = recs.groupby(["ensembl_id", "mondo_id"]).size()
    large = {k for k, n in size.items() if n > PREFILTER_ABOVE}
    pre = {k: v for k, v in items.items() if tuple(k.split("|")[:2]) in large}
    print(f"screen: pairs={len(p)} records={len(items)} large pairs={len(large)} prefilter={len(pre)}", flush=True)
    pdec = decide(PREFILTER_TASK, pre) if pre else {}
    with llm.connect() as conn, conn.cursor() as cur:
        execute_values(cur, """INSERT INTO preclin.target_literature_prefilter (ensembl_id, mondo_id, record_id, possibly,
                                                                                llm_decision_id)
                               VALUES %s ON CONFLICT (ensembl_id, mondo_id, record_id)
                               DO UPDATE SET possibly = EXCLUDED.possibly, llm_decision_id = EXCLUDED.llm_decision_id""",
                       [(*k.split("|", 2), o["possibly"], d) for k, (d, o) in pdec.items()], page_size=5000)
        conn.commit()
    todo = {k: v for k, v in items.items() if k not in pre or pdec.get(k, (0, {"possibly": True}))[1]["possibly"]}
    print(f"screen: to screen={len(todo)}", flush=True)
    store_screens(decide(screen_task(), todo))


def store_screens(dec: dict[str, tuple[int, dict]]) -> None:
    rows = [(*k.split("|", 2), o["original_data"], o["disease_match"], *(o["kinds"][x] for x in KINDS[:4]),
             o["agent_is_program_drug"], *(o["kinds"][x] for x in KINDS[4:]), o["quote"] or None, d)
            for k, (d, o) in dec.items()]
    with llm.connect() as conn, conn.cursor() as cur:
        execute_values(cur, f"""INSERT INTO preclin.target_literature_screen (ensembl_id, mondo_id, record_id, original_data,
                                    disease_match, {", ".join(KINDS[:4])}, agent_is_program_drug, {", ".join(KINDS[4:])},
                                    quote, llm_decision_id)
                                VALUES %s ON CONFLICT (ensembl_id, mondo_id, record_id) DO UPDATE SET
                                    original_data = EXCLUDED.original_data, disease_match = EXCLUDED.disease_match,
                                    {", ".join(f"{x} = EXCLUDED.{x}" for x in KINDS)},
                                    agent_is_program_drug = EXCLUDED.agent_is_program_drug, quote = EXCLUDED.quote,
                                    llm_decision_id = EXCLUDED.llm_decision_id""", rows, page_size=2000)
        conn.commit()
    print(f"stored {len(rows)} screens", flush=True)


def screened_items(p: pd.DataFrame) -> dict[str, dict]:
    """The screen payloads of every record of the pairs that reached the screen (not dropped by the prefilter)."""
    items = screen_payloads(p, pair_records(p))
    dropped = {k for k, (_, o) in llm.current_decisions(PREFILTER_TASK, items).items() if not o["possibly"]}
    return {k: v for k, v in items.items() if k not in dropped}


def prefilter_check(_args) -> None:
    """Give the full screen to PREFILTER_CHECK seeded records the prefilter read as not possibly, and report how many
    of them count for any kind: the prefilter's misses."""
    p = pilot_pairs()
    items = screen_payloads(p, pair_records(p))
    pdec = llm.current_decisions(PREFILTER_TASK, items)
    out = sorted(k for k, (_, o) in pdec.items() if not o["possibly"])
    rng = np.random.default_rng(CHECK_SEED)
    pick = sorted(rng.choice(out, min(PREFILTER_CHECK, len(out)), replace=False)) if out else []
    dec = decide(screen_task(), {k: items[k] for k in pick})
    missed = {kind: sum(counts(o, kind) for _, o in dec.values()) for kind in KINDS}
    print(json.dumps({"prefiltered_out": len(out), "checked": len(dec), "would_count": missed}, indent=2))


def counts(o: dict, kind: str) -> bool:
    """Whether one screen decision counts for a kind (kind animal_model_pharmacology_other: other agents only)."""
    if not (o["original_data"] and o["disease_match"] == "same_or_subtype"):
        return False
    if kind == "animal_model_pharmacology_other":
        return o["kinds"]["animal_model_pharmacology"] and o["agent_is_program_drug"] is False
    return o["kinds"][kind]


def check(_args) -> None:
    """A second model relabels a seeded sample of pilot screens: per kind, up to CHECK_PER_KIND / 2 screened in and as
    many screened out (the screened-out drawn from records the screen read as same-disease original data, where
    errors would matter); kappa per kind is computed by the gate."""
    items = screened_items(pilot_pairs())
    dec = llm.current_decisions(screen_task(), items)
    rng = np.random.default_rng(CHECK_SEED)
    pick: set[str] = set()
    for kind in KINDS:
        pos = sorted(k for k, (_, o) in dec.items() if counts(o, kind))
        neg = sorted(k for k, (_, o) in dec.items() if o["original_data"] and o["disease_match"] == "same_or_subtype"
                     and not o["kinds"][kind])
        for group in (pos, neg):
            if group:
                pick |= set(rng.choice(group, min(CHECK_PER_KIND // 2, len(group)), replace=False))
    print(f"check: records={len(pick)}", flush=True)
    decide(screen_task(CHECK_MODEL, "_check"), {k: items[k] for k in sorted(pick)})


def agreement() -> dict[str, dict]:
    """Kind -> kappa of the screen against the check model on the records both read."""
    items = screened_items(pilot_pairs())
    a = llm.current_decisions(screen_task(), items)
    b = llm.current_decisions(screen_task(CHECK_MODEL, "_check"), items)
    both = sorted(set(a) & set(b))
    out = {}
    for kind in (*KINDS, "animal_model_pharmacology_other"):
        x = [counts(a[k][1], kind) for k in both]
        y = [counts(b[k][1], kind) for k in both]
        out[kind] = {"pairs": len(both), "kappa": kappa(x, y), "positives_screen": int(sum(x)),
                     "positives_check": int(sum(y))}
    return out


# --- reference and gate --------------------------------------------------------------------------------------------

REFERENCE_KINDS = ("human_cell_perturbation", "cell_line_perturbation", "diseased_tissue_protein",
                   "animal_model_pharmacology_other", "mouse_genetic_disease_model", "observational_biomarker",
                   "clinical_observation")
REFERENCE_TEXT = {**KIND_TEXT, "animal_model_pharmacology_other":
                  KIND_TEXT["animal_model_pharmacology"] + ", by an agent OTHER than the program drugs listed"}

REFERENCE_SYSTEM = """You are building a reference set to measure how complete a literature search is. For one human gene (the target) and one disease, find EVERY original study published in or before the cutoff year that reports evidence of the kinds below about this target in this disease (or a subtype, or an animal or cell model of it). Search the web thoroughly: PubMed, Europe PMC, Google Scholar, publisher sites, conference abstracts. Use several searches per kind, with the target's alternative names and the disease's model names.

Kinds:
""" + "\n".join(f"- {k}: {v}" for k, v in REFERENCE_TEXT.items()) + """

Only original data counts (no reviews). A study can be listed under several kinds. Give the PMID whenever the study is in PubMed (look it up), else its DOI; the publication year; the venue (journal, conference or other). List at most 15 studies per kind, the ones you are most confident qualify. Return an empty list for a kind with no qualifying study. Do not list studies published after the cutoff year."""

REFERENCE_SCHEMA = {"type": "object", "additionalProperties": False,
                    "properties": {"studies": {"type": "array", "items": {
                        "type": "object", "additionalProperties": False,
                        "properties": {"kind": {"type": "string", "enum": list(REFERENCE_KINDS)},
                                       "title": {"type": "string"}, "year": {"type": ["integer", "null"]},
                                       "pmid": {"type": ["string", "null"]}, "doi": {"type": ["string", "null"]},
                                       "venue": {"type": "string"}},
                        "required": ["kind", "title", "year", "pmid", "doi", "venue"]}}},
                    "required": ["studies"]}


def render_reference(p: dict) -> str:
    return "\n".join([f"Target: {p['symbol']} ({', '.join(p['gene'][:8])})",
                      f"Disease: {p['disease']}" + (f" (also: {', '.join(p['synonyms'][:6])})" if p["synonyms"] else ""),
                      f"Program drugs on this target in this disease: {', '.join(p['drugs']) or 'none'}",
                      f"Cutoff year: {p['cutoff_year']} (only studies published in or before it)"])


def reference_task(model: str = REFERENCE_MODEL, suffix: str = "") -> llm.Task:
    return llm.Task(name="target_literature_reference" + suffix, prompt_version=VERSION, schema_version="v1",
                    system=REFERENCE_SYSTEM, schema=REFERENCE_SCHEMA, render=render_reference, subject_type="pair",
                    model=model, effort="medium", max_tokens=16000, tools=REFERENCE_TOOLS)


REFERENCE_FALLBACK = "claude-opus-5"  # answers the pairs the reference model refuses


def reference_payloads(rows: pd.DataFrame) -> dict[str, dict]:
    nm = pair_names(rows, run=False)
    dis = disease_names(sorted(set(rows.mondo_id)))
    drugs = pair_drugs(rows)
    return {pair_key(r.ensembl_id, r.mondo_id): {
        "symbol": r.symbol, "gene": nm[pair_key(r.ensembl_id, r.mondo_id)]["gene"], "disease": dis[r.mondo_id]["label"],
        "synonyms": dis[r.mondo_id]["synonyms"], "drugs": drugs.get((r.ensembl_id, r.mondo_id), []),
        "cutoff_year": int(r.cutoff_year)} for r in rows.itertuples()}


def rows_of(spec: str) -> pd.DataFrame:
    lo, hi = map(int, spec.split("-"))
    p = pilot_pairs()
    return p[p.row.between(lo, hi)]


TITLE_MATCH = 0.6  # share of the shorter title's words the other shares, for a PMID to match a stated title


def title_words(t: str | None) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (t or "").lower()) if len(w) > 2}


def title_match(a: str | None, b: str | None) -> float:
    x, y = title_words(a), title_words(b)
    return len(x & y) / max(1, min(len(x), len(y)))


def verify_pmids(studies: list[dict]) -> list[dict]:
    """Each reference study with pmid checked against its stated title: kept when the PubMed title matches
    (TITLE_MATCH), else replaced by the one PubMed record whose title matches a title search, else set to null.
    pmid_given keeps what the model gave. Models cite real titles with wrong PMIDs; this keeps them from
    counting as misses or matches for the wrong paper."""
    ids = sorted({str(s["pmid"]).strip() for s in studies if s.get("pmid")})
    papers = stored_papers(ids)
    papers.update(fetch_papers([i for i in ids if i not in papers], store=True))
    out = []
    for s in studies:
        s = {**s, "pmid_given": s.get("pmid")}
        pid = str(s["pmid"]).strip() if s.get("pmid") else None
        if pid and title_match(s["title"], (papers.get(pid) or ("",))[0]) < TITLE_MATCH:
            words = " ".join(sorted(title_words(s["title"]), key=len, reverse=True)[:8])
            hits = [x.text for x in ET.fromstring(eutils("esearch", term=f"{words}[ti]", retmax="5")).iter("Id")]
            found = fetch_papers(hits, store=True) if hits else {}
            best = max(found.items(), key=lambda kv: title_match(s["title"], kv[1][0]), default=None)
            s["pmid"] = best[0] if best and title_match(s["title"], best[1][0]) >= TITLE_MATCH else None
        out.append(s)
    return out


def reference(args) -> None:
    """The blind reference for pilot rows --rows: a web-enabled model given only the gene, the disease, the program
    drugs and the cutoff (no retrieval output) lists every qualifying study per kind; written to REFERENCE_DIR."""
    rows = rows_of(args.rows)
    items = reference_payloads(rows)
    dec = {k: (REFERENCE_MODEL, o) for k, (_, o) in decide(reference_task(), items).items()}
    refused = {k: v for k, v in items.items() if k not in dec}
    if refused:
        fb = decide(reference_task(REFERENCE_FALLBACK, "_fallback"), refused)
        dec.update({k: (REFERENCE_FALLBACK, o) for k, (_, o) in fb.items()})
    os.makedirs(REFERENCE_DIR, exist_ok=True)
    out = [{"ensembl_id": k.split("|")[0], "mondo_id": k.split("|")[1], "model": model,
            "studies": verify_pmids(o["studies"])} for k, (model, o) in sorted(dec.items())]
    changed = sum(s["pmid"] != s["pmid_given"] for x in out for s in x["studies"])
    print(f"reference: PMIDs corrected or dropped after title verification={changed}")
    print(f"reference: refused by {REFERENCE_MODEL}={len(refused)}, answered by {REFERENCE_FALLBACK}="
          f"{sum(m == REFERENCE_FALLBACK for m, _ in dec.values())}, unanswered={len(items) - len(dec)}")
    with open(os.path.join(REFERENCE_DIR, f"rows_{args.rows}.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"reference: pairs={len(out)} studies={sum(len(x['studies']) for x in out)}")


def qualifying(pairs: pd.DataFrame) -> pd.DataFrame:
    """ensembl_id, mondo_id, record_id, year, doi and kind of every screened record that counts for a kind."""
    items = screened_items(pairs)
    dec = llm.current_decisions(screen_task(), items)
    dois = record_dois(sorted({k.split("|", 2)[2] for k in dec}))
    rows = []
    for k, (_, o) in dec.items():
        e, m, rid = k.split("|", 2)
        for kind in (*KINDS, "animal_model_pharmacology_other"):
            if counts(o, kind):
                rows.append((e, m, rid, items[k]["year"], dois.get(rid), kind))
    return pd.DataFrame(rows, columns=["ensembl_id", "mondo_id", "record_id", "year", "doi", "kind"])


def record_dois(record_ids: list[str]) -> dict[str, str]:
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT pmid, lower(doi) FROM public.publications WHERE pmid = ANY(%s) AND doi IS NOT NULL",
                    ([r for r in record_ids if r.isdigit()],))
        out = dict(cur.fetchall())
        cur.execute("SELECT record_id, lower(doi) FROM preclin.literature_record WHERE record_id = ANY(%s) AND doi IS NOT NULL",
                    ([r for r in record_ids if not r.isdigit()],))
        out.update(cur.fetchall())
    return out


def norm_doi(d: str | None) -> str | None:
    return d.lower().removeprefix("https://doi.org/").removeprefix("doi:").strip() if d else None


def gate(args) -> None:
    """Score pilot rows --rows against their blind reference: per kind, recall (reference studies dated by the cutoff
    found among the counting records, by PMID or DOI), recall over PubMed-indexed reference studies, retrieval recall
    (found among any retrieved record), kappa against the check model, and Phase 2 coverage over all pilot pairs (the
    share of their 2008-2019 Phase 2 entries with a counting record published by the year before entry). Recorded
    in GATE under --label."""
    p = pilot_pairs()
    rows = rows_of(args.rows)
    with open(os.path.join(REFERENCE_DIR, f"rows_{args.rows}.json")) as fh:
        ref = json.load(fh)
    cut = {(r.ensembl_id, r.mondo_id): int(r.cutoff_year) for r in p.itertuples()}
    q = qualifying(p)
    retrieved = pair_records(rows)
    got = {(e, m, k): set(g.record_id) | set(g.doi.dropna()) for (e, m, k), g in q.groupby(["ensembl_id", "mondo_id", "kind"])}
    ret_dois = record_dois(sorted(set(retrieved.record_id)))
    any_ret = {(e, m): set(g.record_id) | {ret_dois[x] for x in g.record_id if x in ret_dois}
               for (e, m), g in retrieved.groupby(["ensembl_id", "mondo_id"])}
    agree = agreement()
    entries = cohort_entries()
    e2 = entries[(entries.phase == 2)].merge(p[["ensembl_id", "mondo_id"]], on=["ensembl_id", "mondo_id"])
    result = {"rows": args.rows, "reference_pairs": len(ref), "kinds": {}}
    for kind in (*KINDS, "animal_model_pharmacology_other"):
        ref_kind = "animal_model_pharmacology_other" if kind == "animal_model_pharmacology" else kind
        studies = [(x["ensembl_id"], x["mondo_id"], s) for x in ref for s in x["studies"]
                   if s["kind"] == ref_kind and (s["year"] is None or s["year"] <= cut[(x["ensembl_id"], x["mondo_id"])])]
        hit, hit_pm, ret = [], [], []
        for e, m, s in studies:
            keys = {str(s["pmid"]).strip()} if s.get("pmid") else set()
            if s.get("doi"):
                keys.add(norm_doi(s["doi"]))
            found = bool(keys & got.get((e, m, kind), set()))
            hit.append(found)
            ret.append(bool(keys & any_ret.get((e, m), set())))
            if s.get("pmid"):
                hit_pm.append(found)
        qk = q[q.kind == kind]
        by_pair = {k: g.year.dropna().astype(int).tolist() for k, g in qk.groupby(["ensembl_id", "mondo_id"])}
        cov = [any(y <= r.entry_year - 1 for y in by_pair.get((r.ensembl_id, r.mondo_id), [])) for r in e2.itertuples()]
        kap = (agree.get(kind) or {}).get("kappa")
        k_out = {"reference_studies": len(studies), "reference_studies_in_pubmed": len(hit_pm),
                 "recall": float(np.mean(hit)) if hit else None,
                 "recall_pubmed_indexed": float(np.mean(hit_pm)) if hit_pm else None,
                 "retrieval_recall": float(np.mean(ret)) if ret else None,
                 "check": agree.get(kind), "phase2_entries": len(cov),
                 "phase2_coverage": float(np.mean(cov)) if cov else None,
                 "pilot_pairs_with_any": int(qk.groupby(["ensembl_id", "mondo_id"]).ngroups)}
        k_out["passes"] = bool(k_out["recall"] is not None and k_out["recall"] >= GATES["recall"] and kap is not None
                               and kap >= GATES["kappa"] and k_out["phase2_coverage"] is not None
                               and k_out["phase2_coverage"] >= GATES["phase2_coverage"])
        result["kinds"][kind] = k_out
    record = json.load(open(GATE)) if os.path.exists(GATE) else {}
    record[args.label] = {"gates": GATES, **result}
    with open(GATE, "w") as fh:
        json.dump(record, fh, indent=2)
    print(json.dumps(result, indent=2))


# --- cost ----------------------------------------------------------------------------------------------------------

# US dollars per million tokens (input, output, cache write, cache read) and per web search
PRICES = {"claude-sonnet-5": (2.0, 10.0, 2.50, 0.20), "claude-haiku-4-5-20251001": (1.0, 5.0, 1.25, 0.10),
          "claude-opus-5-5": (4.0, 20.0, 5.00, 0.20)}
WEB_SEARCH_USD = 0.01
BATCH_DISCOUNT = 0.5


def cost(_args) -> None:
    """The pilot's token cost by task, from the usage stored with each new decision of its tasks (batched calls at
    the batch discount), and the extrapolation to every cohort pair and every pair in preclin.target_disease."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT d.task, r.model, coalesce(r.parameters->>'n_items', '0')::int > %s AS batched, d.usage
                       FROM pv_evidence.llm_decision d JOIN pv_evidence.llm_decision_run r USING (decision_run_id)
                       WHERE d.task LIKE 'target_literature%%' AND d.prior_decision_id IS NULL""", (llm.DIRECT_MAX,))
        rows = cur.fetchall()
        cur.execute("SELECT count(*) FROM preclin.target_disease")
        all_pairs = cur.fetchone()[0]
    by: dict[str, float] = {}
    for task, model, batched, u in rows:
        u = u or {}
        pi, po, pw, pr = PRICES.get(model, PRICES["claude-opus-5-5"])
        usd = (u.get("input_tokens", 0) * pi + u.get("output_tokens", 0) * po
               + u.get("cache_creation_input_tokens", 0) * pw + u.get("cache_read_input_tokens", 0) * pr) / 1e6
        usd = usd * (BATCH_DISCOUNT if batched and task != "target_literature_reference" else 1)
        usd += (u.get("web_search_requests", 0) or 0) * WEB_SEARCH_USD
        by[task] = by.get(task, 0.0) + usd
    n_pilot, n_cohort = len(pilot_pairs()), len(cohort_pairs())
    run_tasks = [t for t in by if "_check" not in t and "reference" not in t]
    per_pair = sum(by[t] for t in run_tasks) / n_pilot
    out = {"usd_by_task": {k: round(v, 2) for k, v in sorted(by.items())}, "pilot_pairs": n_pilot,
           "run_usd_per_pair": round(per_pair, 3), "cohort_pairs": n_cohort,
           "full_run_usd_cohort": round(per_pair * n_cohort), "all_pairs": all_pairs,
           "full_run_usd_all_pairs": round(per_pair * all_pairs)}
    print(json.dumps(out, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in [("sample", sample), ("names", names), ("search", search), ("screen", screen), ("check", check),
                     ("prefilter-check", prefilter_check), ("cost", cost)]:
        sub.add_parser(name).set_defaults(fn=fn)
    f = sub.add_parser("firecrawl")
    f.add_argument("--mode", choices=["search", "related"], required=True)
    f.set_defaults(fn=firecrawl)
    r = sub.add_parser("reference")
    r.add_argument("--rows", required=True)
    r.set_defaults(fn=reference)
    g = sub.add_parser("gate")
    g.add_argument("--rows", required=True)
    g.add_argument("--label", required=True)
    g.set_defaults(fn=gate)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
