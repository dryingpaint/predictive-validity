"""Published evidence about a target's biology in a disease, as known the year before a phase entry (issue #154).

    python -m pipeline.target_literature names        # LLM: vet each gene's names; list each disease's model terms
    python -m pipeline.target_literature origin       # link the origin search's records (#146) as hits
    python -m pipeline.target_literature search       # PubMed and Europe PMC by gene names and disease names/models
    python -m pipeline.target_literature firecrawl --mode search|related   # Firecrawl, per pair and kind / related papers
    python -m pipeline.target_literature screen       # LLM: prefilter large literatures, then screen every record
    python -m pipeline.target_literature check        # second model on a seeded sample of screens, and kappa per kind
    python -m pipeline.target_literature prefilter-check   # full screen of a seeded sample the prefilter dropped
    python -m pipeline.target_literature web          # the web arm: a web-enabled model lists each pair's studies
    python -m pipeline.target_literature web-screen   # screen the records the web arm (or --sources) added
    python -m pipeline.target_literature yardstick    # a differently set up web-enabled model on 100 seeded pairs
    python -m pipeline.target_literature web-score    # recall of the abstract run, the web arm and both, per kind
    python -m pipeline.target_literature reconcile    # bring the stored literature to a rebuilt cohort, adding only
    python -m pipeline.target_literature adjudicate   # the confirmed set: a careful reading of every candidate of the yardstick's pairs
    python -m pipeline.target_literature resolve-score  # coverage, precision and capture-recapture against the confirmed set
    python -m pipeline.target_literature integrity    # completeness and consistency checks
    python -m pipeline.target_literature summary      # pairs with each kind, before entry
    python -m pipeline.target_literature cost         # spend by task

Commands take --pairs pilot (the default), cohort (every cohort pair) or new (cohort pairs with nothing stored yet);
search, screen, web and web-screen take --shard i/n to run n processes on disjoint pairs; screen --follow screens
pairs as their searches finish. The method, the gate and the results are in report/audits/target_literature.md.

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

Retrieval per pair: the records of the origin search (#146, preclin.target_disease_source), linked as hits rather
than copied; PubMed and Europe PMC (outside MEDLINE) titles and abstracts naming the gene (HGNC symbol and its
names, vetted by an LLM, which drops ambiguous aliases and may add the receptor or complex names papers use for the
protein) and the disease (MONDO label, synonyms and direct subtypes) or one of its experimental models (terms an LLM
lists per disease, such as collagen-induced arthritis), reviews excluded; Firecrawl's research index once per pair
and kind, and once for papers related to the pair's first screened-in record; and the web arm, a web-enabled model
asked for the pair's studies of every kind (WEB_TASK), each study verified to a record (verify_studies). A pair with
more than PREFILTER_ABOVE records gets a cheap prefilter first, except records the web arm named. Every record gets
the same screen (screen_task). The kinds failed the registered gate (recall >= 0.8, kappa >= 0.6, Phase 2 coverage
>= 0.08), so they are descriptive.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import zlib
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import Json, execute_values

from pipeline import llm, throttle
from pipeline.outcomes import eutils
from pipeline.attribution import NOT_REVIEWS
from pipeline.literature import (FIRECRAWL_BACKOFF_MAX, FIRECRAWL_PER_SECOND, FIRECRAWL_RESULTS,
                                 FirecrawlError, SourceDown, clean, epmc_records, fetch_papers, firecrawl_cli,
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
VERSION = "v2"  # prompt_version of the screen, prefilter, check and gene-vet tasks (#154's single allowed revision)
SCREEN_VERSION = "v2"  # the screen new readings are stored under (preclin.target_literature_screen.screen_version)
# The v3 screen's definitions, revised against the adjudication (resolve-score): its false positives were evidence about
# the target's ligand, pathway partners or regulators rather than the target; another gene's knockout; drugs whose
# effect on the target was incidental; single cases, null findings and genotype-defined groups read as biomarkers;
# and mutation carriers' clinical course read as a clinical observation.
KIND_TEXT_V3 = {
    **KIND_TEXT,
    "human_cell_perturbation": KIND_TEXT["human_cell_perturbation"] + "; the experimenter changes THIS target directly "
                               "(its gene, or an agent whose primary action is on it), not a ligand's or another "
                               "gene's level; work in living animals or people is never this kind",
    "cell_line_perturbation": "the target is changed experimentally in an ESTABLISHED cell line (HeLa, HEK293, named "
                              "cancer lines and the like): knockdown, knockout or overexpression of THIS target's gene, "
                              "or an agent whose primary action is on THIS target; and a feature of the disease changes. "
                              "Genome-wide screens count. An agent with many actions whose effect on the target is "
                              "incidental, or changing an upstream regulator or pathway partner, does not count",
    "diseased_tissue_protein": KIND_TEXT["diseased_tissue_protein"] + "; differences only among patients (for example "
                               "with prognosis) without normal or less-affected tissue to compare do not count, nor do "
                               "measurements of a different protein in the target's pathway",
    "mouse_genetic_disease_model": "a knockout, knock-in or transgene of THIS target's own gene (not a regulator, "
                                   "partner or pathway gene) alters an animal model of the disease, or the genetically "
                                   "altered animal develops the disease; a drug given to a genetic model is "
                                   "animal_model_pharmacology, not this kind",
    "observational_biomarker": "an OBSERVATIONAL study of patients (no intervention assigned) measures THIS target or "
                               "its own product (its protein, its enzymatic activity, or its occupancy by an imaging "
                               "ligand; not its ligand, a hormone acting on it or a downstream marker) in blood, another "
                               "body fluid or by imaging, and the measurement differs with the disease's presence, "
                               "severity, progression or outcome in a group of patients; single cases, null findings, "
                               "groups defined by genotype, tissue measurements, genetic association and drug-response "
                               "markers in a trial do not count",
    "clinical_observation": KIND_TEXT["clinical_observation"] + "; the clinical course of carriers of a mutation in "
                            "the gene, and responses to surgery or devices, do not count",
}
# v4, the screen kept: v3's definitions except clinical_observation, whose v3 revision lowered both its coverage and
# its precision against the adjudication (report/audits/target_literature.md), so it keeps the v2 definition.
KIND_TEXT_V4 = {**KIND_TEXT_V3, "clinical_observation": KIND_TEXT["clinical_observation"]}
COHORT = (2008, 2019)  # phase entry years of the evidence dataset
PILOT_N = 300
PILOT_SEED = 20261122  # drew the pilot from the cohort of 2026-11-22; that cohort has since changed, so the draw is kept
PILOT_CSV = os.path.join(llm.REPO, "report", "audits", "target_literature_pilot.csv")
MAX_GENE_NAMES = 16
MAX_DISEASE_NAMES = 20
MAX_SUBTYPE_NAMES = 15  # labels of the disease's direct MONDO subtypes searched as disease names (v2)
MAX_MODEL_TERMS = 10
FIRECRAWL_WORKERS = 16  # concurrent research-index calls: calls take seconds, so the shared rate throttle, not this, sets the pace
PREFILTER_ABOVE = 3000  # records per pair above which a cheap model reads each record first (as #154 registered; v1 used 500)
PREFILTER_CHECK = 300  # seeded prefiltered-out records given the full screen, to measure the prefilter's misses
CHECK_PER_KIND = 50  # half screened in, half screened out, per kind
CHECK_SEED = 20261123
SCREEN_MODEL = "claude-sonnet-5"
SCREEN_FALLBACK = "claude-opus-5"  # reads the records the screen model refuses or answers invalidly
PREFILTER_MODEL = "claude-haiku-4-5-20251001"  # the id pipeline.literature runs
CHECK_MODEL = "claude-opus-5-5"
REFERENCE_MODEL = "claude-opus-5-5"
REFERENCE_TOOLS = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 12},
                   {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 6}]
METHOD = "target_literature@v1"
ABSTRACT_CHARS = 4000
NETWORK_RETRIES = 8  # reruns of a command after a network or database outage (main)


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


def confirm_pairs() -> pd.DataFrame:
    """The pairs of the confirmation entries (report.windows.CONFIRM: US-sited Phase 2 entries of 2020 to 2022-11-02,
    as issue #140's): ensembl_id, mondo_id, cutoff_year (the year before the pair's latest such entry), symbol and
    disease label, for each entry's primary target gene that forms a pair in preclin.target_disease."""
    from report import frame
    from report.section1 import phase_rows
    from report.windows import CONFIRM
    progs = frame.programs()
    rows = phase_rows(progs, frame.program_trials(), frame.snapshot(), window=CONFIRM)
    rows = rows[~rows.credited & rows.us_site & rows.phase.eq(2)].copy()
    rows["mondo_id"] = rows.program_id.map(progs.set_index("program_id").mondo_id)
    rows["cutoff_year"] = pd.to_datetime(rows.entry).dt.year - 1
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT mt.moiety_id, t.ensembl_id FROM preclin.moiety_target mt
                       JOIN public.targets t ON t.id = mt.target_id WHERE mt.is_primary""")
        genes = pd.DataFrame(cur.fetchall(), columns=["moiety_id", "ensembl_id"])
        cur.execute("""SELECT td.ensembl_id, td.mondo_id, td.symbol, o.label FROM preclin.target_disease td
                       LEFT JOIN preclin.ontology_term o ON o.term_id = td.mondo_id""")
        meta = pd.DataFrame(cur.fetchall(), columns=["ensembl_id", "mondo_id", "symbol", "disease"])
    e = rows[["moiety_id", "mondo_id", "cutoff_year"]].merge(genes, on="moiety_id")
    p = e.groupby(["ensembl_id", "mondo_id"], as_index=False).cutoff_year.max()
    return p.merge(meta, on=["ensembl_id", "mondo_id"]).sort_values(["ensembl_id", "mondo_id"]).reset_index(drop=True)


def pilot_pairs() -> pd.DataFrame:
    return pd.read_csv(PILOT_CSV)


def pairs_of(which: str) -> pd.DataFrame:
    """The pilot sample, every cohort pair (the full descriptive run), the confirmation pairs (confirm_pairs), or the
    cohort or confirmation pairs with no search stored at an earlier cutoff than their own (new, confirm-new: pairs
    searched only now, as against pairs whose cutoff moved, which reconcile brings forward)."""
    if which in ("new", "confirm-new"):  # no search stored at an earlier cutoff: stays the same set as its run proceeds
        p = cohort_pairs() if which == "new" else confirm_pairs()
        with llm.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT ensembl_id, mondo_id, min(cutoff_year) FROM preclin.target_literature_search GROUP BY 1, 2")
            first = {(e, m): y for e, m, y in cur.fetchall()}
        return p[[first.get((e, m), c) >= c for e, m, c in zip(p.ensembl_id, p.mondo_id, p.cutoff_year)]].reset_index(drop=True)
    return {"pilot": pilot_pairs, "cohort": cohort_pairs, "confirm": confirm_pairs, "yardstick": yardstick_pairs}[which]()


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


def names(args) -> None:
    n = pair_names(pairs_of(args.pairs))
    print(f"names: pairs={len(n)} without gene names={sum(not v['gene'] for v in n.values())}")


# --- retrieval -----------------------------------------------------------------------------------------------------

def record_texts(record_ids: list[str]) -> dict[str, tuple]:
    """record id -> (title, abstract, year), read once from wherever the record is stored: public.publications,
    preclin.literature_record, else the origin search's own copy in preclin.target_disease_source (PMID:N as N)."""
    out = stored_papers(record_ids)
    rest = [r for r in record_ids if r not in out]
    if rest:
        with llm.connect() as conn, conn.cursor() as cur:
            cur.execute("""SELECT DISTINCT ON (record_id) regexp_replace(record_id, '^PMID:', ''), title, abstract, year
                           FROM preclin.target_disease_source WHERE record_id = ANY(%s) ORDER BY record_id""",
                        ([("PMID:" + r) if r.isdigit() else r for r in rest],))
            out.update({r: (t or "", a, y) for r, t, a, y in cur.fetchall()})
    return out


def fetch_texts(pmids: list[str]) -> None:
    """Fetch and store the PubMed records not yet stored, in PMID order and retried on a deadlock: parallel searches
    insert overlapping PMIDs into public.publications, and a common order keeps their row locks from crossing."""
    for start in range(0, len(pmids), 1000):
        part = sorted(pmids[start:start + 1000], key=int)
        for attempt in range(5):
            try:
                fetch_papers(part, store=True)
                break
            except psycopg2.errors.DeadlockDetected:
                time.sleep(5 * (attempt + 1))
        else:
            raise RuntimeError(f"deadlock storing {len(part)} PubMed records")


def origin(args) -> None:
    """Read the origin search's records (#146) as hits of the pairs (--pairs): for each pair it searched, its PubMed
    and Europe PMC records dated by this run's cutoff become hits linked to preclin.target_disease_source, with one
    search row per service recording its query and names. No text is copied; record_texts reads it from there."""
    p = pairs_of(args.pairs)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT ensembl_id, mondo_id, service, cutoff_year, gene_names, disease_names, query, n_hits
                       FROM preclin.target_disease_search""")
        searches = {(e, m, sv): (y, g, d, q, n) for e, m, sv, y, g, d, q, n in cur.fetchall()}
    rows = [(r, sv) for r in p.itertuples() for sv in ("pubmed", "europepmc") if (r.ensembl_id, r.mondo_id, sv) in searches]
    print(f"origin: pairs={len(p)} searched by the origin search={len({(r.ensembl_id, r.mondo_id) for r, _ in rows})}",
          flush=True)
    linked = 0
    for start in range(0, len(rows), 500):
        part = rows[start:start + 500]
        with llm.connect() as conn, conn.cursor() as cur:
            cur.execute("CREATE TEMP TABLE want (ensembl_id text, mondo_id text, service text, cutoff_year int) ON COMMIT DROP")
            execute_values(cur, "INSERT INTO want VALUES %s",
                           [(r.ensembl_id, r.mondo_id, sv, int(r.cutoff_year)) for r, sv in part])
            cur.execute("""SELECT s.ensembl_id, s.mondo_id, s.service, regexp_replace(s.record_id, '^PMID:', '')
                           FROM preclin.target_disease_source s JOIN want w USING (ensembl_id, mondo_id, service)
                           WHERE s.year <= w.cutoff_year""")
            got: dict = {}
            for e, m, sv, rid in cur.fetchall():
                got.setdefault((e, m, sv), []).append(rid)
            for r, sv in part:
                y, g, d, q, n = searches[(r.ensembl_id, r.mondo_id, sv)]
                ids = got.get((r.ensembl_id, r.mondo_id, sv), [])
                store_search(cur, r.ensembl_id, r.mondo_id, int(r.cutoff_year), "origin_" + sv, "",
                             {"gene": g, "disease": d, "origin_cutoff_year": y}, q, n, ids)
                linked += len(ids)
            conn.commit()
    print(f"origin: search rows={len(rows)} hits linked={linked}", flush=True)


def epmc_clause(names: list[str]) -> str:
    return f'({" OR ".join(f"TITLE_ABS:{chr(34)}{n}{chr(34)}" for n in names)})'


def clauses(n: dict) -> tuple[str, str]:
    """The PubMed and Europe PMC clauses of one pair: a gene name and a disease name or model term."""
    dm = n["disease"] + [m for m in n["models"] if m.lower() not in {d.lower() for d in n["disease"]}]
    return (f"{names_clause(n['gene'])} AND {names_clause(dm)}", f"{epmc_clause(n['gene'])} AND {epmc_clause(dm)}")


def store_search(cur, e: str, m: str, y: int, source: str, kind: str, n: dict, query: str, n_hits: int,
                 record_ids: list[str]) -> None:
    cur.execute("""DELETE FROM preclin.target_literature_hit WHERE ensembl_id = %s AND mondo_id = %s AND cutoff_year = %s
                   AND source = %s AND kind = %s""", (e, m, y, source, kind))
    cur.execute("""INSERT INTO preclin.target_literature_search (ensembl_id, mondo_id, cutoff_year, source, kind, names,
                                                                 query, n_hits)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (ensembl_id, mondo_id, cutoff_year, source, kind)
                   DO UPDATE SET names = EXCLUDED.names, query = EXCLUDED.query, n_hits = EXCLUDED.n_hits,
                                 searched_at = now()""", (e, m, y, source, kind, Json(n), query, n_hits))
    if record_ids:
        execute_values(cur, """INSERT INTO preclin.target_literature_hit (ensembl_id, mondo_id, cutoff_year, source, kind,
                                                                          record_id)
                               VALUES %s ON CONFLICT DO NOTHING""", [(e, m, y, source, kind, r) for r in record_ids],
                       page_size=5000)


def search(args) -> None:
    """PubMed and Europe PMC for every pair (--pairs) not yet searched at its cutoff with its current names; PubMed
    abstracts not in public.publications are fetched and stored. Each pair is committed before the next, so a
    restarted run resumes where it stopped."""
    p = pairs_of(args.pairs)
    if args.shard:
        i, n = map(int, args.shard.split("/"))
        p = p.iloc[i - 1::n]
    nm = pair_names(p, run=args.shard in (None, "1/1"))
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
        have = set(record_texts(pmids))
        missing = [x for x in pmids if x not in have]
        fetch_texts(missing)
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
    """Firecrawl's research index for the pairs (--pairs): --mode search runs one semantic search per pair and kind;
    --mode related, papers related to each pair's first screened-in record. Results dated after the cutoff are dropped;
    ids outside PubMed resolve through Europe PMC. A failed call is not recorded, so a later run retries it."""
    from concurrent.futures import ThreadPoolExecutor
    p = pairs_of(args.pairs)
    nm = pair_names(p, run=False)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT ensembl_id, mondo_id, cutoff_year, source, kind FROM preclin.target_literature_search
                       WHERE source LIKE 'firecrawl%%'""")
        done = set(cur.fetchall())  # by cutoff: a pair searched only at another cutoff is searched at its own
        cur.execute(f"""SELECT DISTINCT ON (ensembl_id, mondo_id) ensembl_id, mondo_id, record_id
                        FROM preclin.target_literature_screen
                        WHERE original_data AND disease_match = 'same_or_subtype' AND ({" OR ".join(KINDS)})
                        ORDER BY ensembl_id, mondo_id, record_id""")
        seeds = {(e, m): rid for e, m, rid in cur.fetchall()}
    if args.mode == "search":
        calls = [(r, k) for r in p.itertuples() for k in KINDS
                 if (r.ensembl_id, r.mondo_id, int(r.cutoff_year), "firecrawl", k) not in done and nm[pair_key(r.ensembl_id, r.mondo_id)]["gene"]]
    else:
        calls = [(r, "") for r in p.itertuples() if (r.ensembl_id, r.mondo_id) in seeds
                 and (r.ensembl_id, r.mondo_id, int(r.cutoff_year), "firecrawl_related", "") not in done]
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
        for attempt in range(5):  # a dropped database link is retried; the call's results are kept in memory
            try:
                with llm.connect() as conn, conn.cursor() as cur:
                    store_search(cur, r.ensembl_id, r.mondo_id, y, source, k, n, q, len(results), ids)
                    conn.commit()
                break
            except (psycopg2.OperationalError, psycopg2.InterfaceError):
                time.sleep(10 * (attempt + 1))
        else:
            state["failed"] += 1
            print(f"firecrawl not stored {r.symbol} {r.mondo_id} {k}: database unreachable", flush=True)
            return
        state["done"] += 1
        if state["done"] % 500 == 0:
            print(f"firecrawl {args.mode} {state['done']}/{len(calls)} failed={state['failed']}", flush=True)

    with ThreadPoolExecutor(FIRECRAWL_WORKERS) as pool:
        list(pool.map(one, calls))
    print(f"firecrawl {args.mode} finished: {state['done']}/{len(calls)} failed={state['failed']} credits "
          f"{before} -> {firecrawl_credits()}" + (f"; STOPPED, {state['stop']}" if state["stop"] else ""), flush=True)


# --- screen --------------------------------------------------------------------------------------------------------

SCREEN_PREAMBLE = """You read one paper's title and abstract and decide what original evidence it reports about ONE human gene or its protein (the target) in ONE disease.

original_data: true when the paper reports new experimental or clinical results (not a review, commentary, guideline, protocol or case-free opinion).

disease_match: the disease the evidence is about, against the disease given: same_or_subtype (the same disease, a subtype of it, or a near-identical disease, including an animal or cell model of it), related (a related but distinct disease), other (an unrelated disease), or none (no disease studied).

kinds: true for each kind of evidence the paper reports about THIS target (under any of its names; a different gene of the same family does not count) in the disease named under disease_match, with original data:
"""
SCREEN_RULES = """

system: the experimental or clinical system of the paper's main finding about the target: primary_human_cells, cell_line, patient_tissue, patient_fluid_or_imaging, animal_model, people_other (clinical observations outside a trial), trial (an interventional trial), or none. Decide it first; each kind's system must match: primary_human_cells for human_cell_perturbation, cell_line for cell_line_perturbation, patient_tissue for diseased_tissue_protein, animal_model for the two animal kinds, patient_fluid_or_imaging for observational_biomarker, people_other for clinical_observation. A paper with several findings may show kinds in other systems too.

A paper whose only agent is the program drug named below can show animal_model_pharmacology; mark agent_is_program_drug true then, false when another agent (a tool compound, antibody, siRNA, another drug) was used, and null when animal_model_pharmacology is false. Evidence must be about the target: a drug tested without the target being the point does not count, except under animal_model_pharmacology when the drug acts on this target. A kind is true only when the abstract states the finding; do not infer. Quote the sentence that decided the reading (empty when nothing qualifies)."""


V3_RULE = """

The target is the gene or protein named, under any of its names. Evidence about its ligand or hormone, an upstream regulator, a pathway partner or a downstream marker is not evidence about the target, even when the paper discusses the target's pathway."""


def screen_system(version: str) -> str:
    text = {"v3": KIND_TEXT_V3, "v4": KIND_TEXT_V4}.get(version, KIND_TEXT)
    return SCREEN_PREAMBLE + "\n".join(f"- {k}: {v}" for k, v in text.items()) + \
        (V3_RULE if version in ("v3", "v4") else "") + SCREEN_RULES


SCREEN_SYSTEM = screen_system(VERSION)  # the gated v2 screen

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


def screen_task(model: str = SCREEN_MODEL, suffix: str = "", version: str | None = None) -> llm.Task:
    """The screen at `version` (SCREEN_VERSION by default): v2 reads with KIND_TEXT, v3 with KIND_TEXT_V3, v4 (kept)
    with KIND_TEXT_V4."""
    version = version or SCREEN_VERSION
    return llm.Task(name="target_literature_screen" + suffix, prompt_version=version, schema_version=VERSION,
                    system=screen_system(version), schema=SCREEN_SCHEMA, render=render_screen, validate=validate_screen,
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
    papers = record_texts(sorted(set(recs.record_id)))
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


CHUNK_PAIRS = 250  # pairs prefiltered and screened together; each chunk is stored before the next
POLL_SECONDS = 300  # wait for searches to make more pairs ready


def screened(p: pd.DataFrame) -> set[tuple[str, str]]:
    """The pairs every retrieved record of which has a screen row or a prefilter-out row (or no stored text)."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE want (ensembl_id text, mondo_id text, cutoff_year int) ON COMMIT DROP")
        execute_values(cur, "INSERT INTO want VALUES %s", [(r.ensembl_id, r.mondo_id, int(r.cutoff_year)) for r in p.itertuples()])
        cur.execute("""SELECT w.ensembl_id, w.mondo_id FROM want w
                       WHERE EXISTS (SELECT 1 FROM preclin.target_literature_screen s
                                     WHERE (s.ensembl_id, s.mondo_id) = (w.ensembl_id, w.mondo_id))
                         AND NOT EXISTS (
                           SELECT 1 FROM preclin.target_literature_hit h
                           WHERE (h.ensembl_id, h.mondo_id, h.cutoff_year) = (w.ensembl_id, w.mondo_id, w.cutoff_year)
                             AND NOT EXISTS (SELECT 1 FROM preclin.target_literature_screen s
                                             WHERE (s.ensembl_id, s.mondo_id, s.record_id) = (h.ensembl_id, h.mondo_id, h.record_id))
                             AND NOT EXISTS (SELECT 1 FROM preclin.target_literature_prefilter f WHERE NOT f.possibly
                                             AND (f.ensembl_id, f.mondo_id, f.record_id) = (h.ensembl_id, h.mondo_id, h.record_id))
                             AND (EXISTS (SELECT 1 FROM public.publications x WHERE x.pmid = h.record_id)
                                  OR EXISTS (SELECT 1 FROM preclin.literature_record x WHERE x.record_id = h.record_id)
                                  OR EXISTS (SELECT 1 FROM preclin.target_disease_source x
                                             WHERE x.record_id IN (h.record_id, 'PMID:' || h.record_id))))""")
        return set(cur.fetchall())


def ready(p: pd.DataFrame) -> pd.DataFrame:
    """The pairs whose PubMed, Europe PMC and per-kind Firecrawl searches are all stored at their cutoff."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT ensembl_id, mondo_id, cutoff_year FROM preclin.target_literature_search
                       GROUP BY 1, 2, 3
                       HAVING count(*) FILTER (WHERE source = 'pubmed') = 1
                          AND count(*) FILTER (WHERE source = 'europepmc') = 1
                          AND count(DISTINCT kind) FILTER (WHERE source = 'firecrawl') = %s""", (len(KINDS),))
        done = set(cur.fetchall())
    return p[[(r.ensembl_id, r.mondo_id, int(r.cutoff_year)) in done for r in p.itertuples()]]


def screen_chunk(p: pd.DataFrame) -> None:
    """Prefilter the records of pairs with more than PREFILTER_ABOVE, screen every record that reaches the screen, and
    store both, replacing the pairs' earlier rows: a pair's prefilter and screen rows are exactly its current
    decisions on the records its searches now return."""
    recs = pair_records(p)
    ids = sorted(set(recs.record_id))
    have = set(record_texts(ids))
    fetch_texts([x for x in ids if x.isdigit() and x not in have])  # Firecrawl's PubMed hits, fetched in bulk here
    items = screen_payloads(p, recs)
    large = large_pairs(recs)
    pre = {k: v for k, v in items.items() if tuple(k.split("|")[:2]) in large}
    pdec = decide(PREFILTER_TASK, pre) if pre else {}
    todo = {k: v for k, v in items.items() if k not in pre or pdec[k][1]["possibly"]}
    dec = decide(screen_task(), todo)
    refused = {k: v for k, v in todo.items() if k not in dec}
    if refused:  # the screen model's refusals and failed outputs, read once more by the fallback model
        dec.update(decide(screen_task(SCREEN_FALLBACK, "_fallback"), refused))
    store_screens(p, pdec, dec)
    print(f"screen chunk: pairs={len(p)} records={len(recs)} readable={len(items)} large pairs={len(large)} "
          f"prefiltered={len(pdec)} screened={len(dec)}", flush=True)


def large_pairs(recs: pd.DataFrame) -> set[tuple[str, str]]:
    size = recs.groupby(["ensembl_id", "mondo_id"]).size()
    return {k for k, n in size.items() if n > PREFILTER_ABOVE}


def screen(args) -> None:
    """Screen the pairs (--pairs) in chunks of CHUNK_PAIRS. With --follow, keep taking pairs as their searches
    finish until every pair is screened. A chunk whose decisions are all stored costs nothing to redo: the runner
    reuses them. With --since, each chunk logs the spend since then and its projection to every pair. --shard i/n
    takes the pairs whose key hashes to i of n, so parallel screens never share a pair."""
    p = pairs_of(args.pairs)
    if args.shard:
        i, n = map(int, args.shard.split("/"))
        p = p[[zlib.crc32(pair_key(e, m).encode()) % n == i - 1 for e, m in zip(p.ensembl_id, p.mondo_id)]]
    reused = set(zip(*[pilot_pairs()[c] for c in ("ensembl_id", "mondo_id")]))  # screened by the pilot already
    done: set[tuple[str, str]] = screened(p) if args.skip_done else set()
    print(f"screen: pairs={len(p)} already screened={len(done)}", flush=True)
    while True:
        avail = ready(p)
        avail = avail[[(e, m) not in done for e, m in zip(avail.ensembl_id, avail.mondo_id)]]
        if avail.empty:
            if len(done) == len(p) or not args.follow:
                break
            time.sleep(POLL_SECONDS)
            continue
        for start in range(0, len(avail), CHUNK_PAIRS):
            if args.since:
                spent = spend(args.since)
                new_done = len(done - reused)
                projected = spent / new_done * (len(p) - len(reused)) if new_done else 0.0
                print(f"spend since {args.since}: ${spent:,.0f}; pairs screened {len(done)}/{len(p)}; projected "
                      f"${projected:,.0f}", flush=True)
            chunk = avail.iloc[start:start + CHUNK_PAIRS]
            screen_chunk(chunk)
            done |= set(zip(chunk.ensembl_id, chunk.mondo_id))
        if not args.follow:
            break
    print(f"screen finished: pairs={len(done)}/{len(p)}", flush=True)


def store_screens(p: pd.DataFrame, pdec: dict[str, tuple[int, dict]], dec: dict[str, tuple[int, dict]]) -> None:
    """Replace the pairs' prefilter and screen rows with these decisions, in one transaction after every model
    call has returned."""
    keys = list(zip(p.ensembl_id, p.mondo_id))
    rows = [(*k.split("|", 2), o["original_data"], o["disease_match"], *(o["kinds"][x] for x in KINDS[:4]),
             o["agent_is_program_drug"], *(o["kinds"][x] for x in KINDS[4:]), o["quote"] or None, d)
            for k, (d, o) in dec.items()]
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE chunk_pairs (ensembl_id text, mondo_id text) ON COMMIT DROP")
        execute_values(cur, "INSERT INTO chunk_pairs VALUES %s", keys)
        if SCREEN_VERSION == VERSION:  # a revised screen reads the same prefiltered records: its prefilter rows stand
            cur.execute("DELETE FROM preclin.target_literature_prefilter USING chunk_pairs c "
                        "WHERE (target_literature_prefilter.ensembl_id, target_literature_prefilter.mondo_id) = (c.ensembl_id, c.mondo_id)")
            execute_values(cur, """INSERT INTO preclin.target_literature_prefilter (ensembl_id, mondo_id, record_id, possibly,
                                                                                    llm_decision_id) VALUES %s""",
                           [(*k.split("|", 2), o["possibly"], d) for k, (d, o) in pdec.items()], page_size=5000)
        cur.execute("DELETE FROM preclin.target_literature_screen USING chunk_pairs c "
                    "WHERE (target_literature_screen.ensembl_id, target_literature_screen.mondo_id) = (c.ensembl_id, c.mondo_id) "
                    "AND target_literature_screen.screen_version = %s", (SCREEN_VERSION,))
        execute_values(cur, f"""INSERT INTO preclin.target_literature_screen (ensembl_id, mondo_id, record_id, original_data,
                                    disease_match, {", ".join(KINDS[:4])}, agent_is_program_drug, {", ".join(KINDS[4:])},
                                    quote, llm_decision_id, screen_version) VALUES %s""",
                       [(*r, SCREEN_VERSION) for r in rows], page_size=2000)
        conn.commit()


def screen_decisions(items: dict[str, dict]) -> dict[str, tuple[int, dict]]:
    """The screen's decision of each item, or the fallback model's where the screen model gave none."""
    dec = llm.current_decisions(screen_task(), items)
    rest = {k: v for k, v in items.items() if k not in dec}
    return dec | (llm.current_decisions(screen_task(SCREEN_FALLBACK, "_fallback"), rest) if rest else {})


def screened_items(p: pd.DataFrame) -> dict[str, dict]:
    """The screen payloads of every record of the pairs that reached the screen: all records of a pair with at most
    PREFILTER_ABOVE, else those the prefilter read as possibly."""
    recs = pair_records(p)
    items = screen_payloads(p, recs)
    large = large_pairs(recs)
    pre = {k: v for k, v in items.items() if tuple(k.split("|")[:2]) in large}
    dropped = {k for k, (_, o) in llm.current_decisions(PREFILTER_TASK, pre).items() if not o["possibly"]}
    return {k: v for k, v in items.items() if k not in dropped}


def prefilter_check(args) -> None:
    """Give the full screen to PREFILTER_CHECK seeded records the prefilter read as not possibly, and report how many
    of them count for any kind: the prefilter's misses."""
    p = pairs_of(args.pairs)
    recs = pair_records(p)
    large = large_pairs(recs)
    items = {k: v for k, v in screen_payloads(p, recs).items() if tuple(k.split("|")[:2]) in large}
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


def check(args) -> None:
    """A second model relabels a seeded sample of pilot screens: per kind, up to CHECK_PER_KIND / 2 screened in and as
    many screened out (the screened-out drawn from records the screen read as same-disease original data, where
    errors would matter); then prints kappa per kind (agreement)."""
    items = screened_items(pairs_of(args.pairs))
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
    print(json.dumps(agreement(args.pairs), indent=2))


def agreement(which: str = "pilot") -> dict[str, dict]:
    """Kind -> kappa of the screen against the check model on the records both read."""
    items = screened_items(pairs_of(which))
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


# --- web search: the pilot's reference prompt, the web arm and the yardstick ----------------------------------------

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


REFERENCE_FALLBACK = "claude-opus-5"  # answers the pairs the reference model refuses


def reference_payloads(rows: pd.DataFrame) -> dict[str, dict]:
    nm = pair_names(rows, run=False)
    dis = disease_names(sorted(set(rows.mondo_id)))
    drugs = pair_drugs(rows)
    return {pair_key(r.ensembl_id, r.mondo_id): {
        "symbol": r.symbol, "gene": nm[pair_key(r.ensembl_id, r.mondo_id)]["gene"], "disease": dis[r.mondo_id]["label"],
        "synonyms": dis[r.mondo_id]["synonyms"], "drugs": drugs.get((r.ensembl_id, r.mondo_id), []),
        "cutoff_year": int(r.cutoff_year)} for r in rows.itertuples()}


TITLE_MATCH = 0.6  # share of the shorter title's words the other shares, for a PMID to match a stated title


def title_words(t: str | None) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (t or "").lower()) if len(w) > 2}


def title_match(a: str | None, b: str | None) -> float:
    x, y = title_words(a), title_words(b)
    return len(x & y) / max(1, min(len(x), len(y)))


def norm_doi(d: str | None) -> str | None:
    return d.lower().removeprefix("https://doi.org/").removeprefix("doi:").strip() if d else None


# --- web arm and yardstick (the second retrieval arm) ----------------------------------------------------------------

WEB_TASK = llm.Task(name="target_literature_web", prompt_version="v1", schema_version="v1", system=REFERENCE_SYSTEM,
                    schema=REFERENCE_SCHEMA, render=render_reference, subject_type="pair", model=REFERENCE_MODEL,
                    effort="medium", max_tokens=16000, tools=REFERENCE_TOOLS)
WEB_FALLBACK = llm.Task(**{**WEB_TASK.__dict__, "name": "target_literature_web_fallback", "model": REFERENCE_FALLBACK})
WEB_CHUNK = 100  # pairs whose web searches are verified and stored together

YARDSTICK_N = 100
YARDSTICK_SEED = 20261124
YARDSTICK_MODEL = "claude-sonnet-5"
YARDSTICK_SYSTEM = """You are an expert curator auditing how complete a literature collection is. For one human gene (the target) and one disease, list the original studies published in or before the cutoff year that report evidence of the kinds below about this target in this disease (or a subtype, or an animal or cell model of it).

Work from the field's secondary literature outward: first find recent reviews, book chapters and guidelines on this target in this disease (or this target's pathway in the disease), read their reference lists, and follow citations both backwards (what the key papers cite) and forwards (who cites them). Then fill gaps with targeted web searches under the target's class, complex or receptor names and the disease's experimental model names. Prefer full text, figure legends and supplements to abstracts when deciding whether a study qualifies.

Kinds:
""" + "\n".join(f"- {k}: {v}" for k, v in REFERENCE_TEXT.items()) + """

Only original data counts (no reviews, no editorials). A study can be listed under several kinds. Give the PMID whenever the study is in PubMed (look it up), else its DOI; the publication year; the venue. List at most 15 studies per kind, the ones you are most confident qualify. Return an empty list for a kind with no qualifying study. Do not list studies published after the cutoff year."""
YARDSTICK_TASK = llm.Task(name="target_literature_yardstick", prompt_version="v1", schema_version="v1",
                          system=YARDSTICK_SYSTEM, schema=REFERENCE_SCHEMA, render=render_reference, subject_type="pair",
                          model=YARDSTICK_MODEL, effort="medium", max_tokens=16000, tools=REFERENCE_TOOLS)
YARDSTICK_FALLBACK = llm.Task(**{**YARDSTICK_TASK.__dict__, "name": "target_literature_yardstick_fallback",
                                 "model": REFERENCE_FALLBACK})


def title_search(title: str) -> str | None:
    """The one PubMed record whose title matches a title search for `title` (TITLE_MATCH), stored; else None."""
    words = " ".join(sorted(title_words(title), key=len, reverse=True)[:8])
    if not words:
        return None
    hits = [x.text for x in ET.fromstring(eutils("esearch", term=f"{words}[ti]", retmax="5")).iter("Id")]
    found = fetch_papers(hits, store=True) if hits else {}
    best = max(found.items(), key=lambda kv: title_match(title, kv[1][0]), default=None)
    return best[0] if best and title_match(title, best[1][0]) >= TITLE_MATCH else None


DOI_BATCH = 40  # DOIs per PubMed search


def pmids_by_doi(dois: list[str]) -> dict[str, str]:
    """Normalised DOI -> PMID for the DOIs PubMed holds, DOI_BATCH per search; the records are stored."""
    out: dict[str, str] = {}
    for start in range(0, len(dois), DOI_BATCH):
        part = dois[start:start + DOI_BATCH]
        term = " OR ".join(f'"{d}"[doi]' for d in part)
        ids = [x.text for x in ET.fromstring(eutils("esearch", term=term, retmax=str(4 * len(part)))).iter("Id")]
        if not ids:
            continue
        fetch_texts(ids)
        with llm.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT lower(doi), pmid FROM public.publications WHERE pmid = ANY(%s) AND doi IS NOT NULL", (ids,))
            got = dict(cur.fetchall())
        out.update({d: got[d] for d in part if d in got})
    return out


def verify_studies(studies: list[dict]) -> list[dict]:
    """Each named study with record_id and verification: the given PMID when its PubMed title matches the stated
    title (pmid_matched); else the PubMed record of its DOI (one search per DOI_BATCH DOIs), or the Europe PMC record
    the DOI resolves to (pipeline.literature.resolve_external), when that record's title matches (doi_resolved); else
    the record a PubMed title search matches (pmid_corrected); else unverified. Records found are stored."""
    ids = sorted({str(s["pmid"]).strip() for s in studies if s.get("pmid")})
    papers = stored_papers(ids)
    fetch_texts([i for i in ids if i not in papers and i.isdigit()])
    papers.update(stored_papers([i for i in ids if i not in papers]))
    out = []
    for s in studies:
        pid = str(s["pmid"]).strip() if s.get("pmid") else None
        ok = pid and title_match(s["title"], (papers.get(pid) or ("",))[0]) >= TITLE_MATCH
        out.append({**s, "record_id": pid if ok else None, "verification": "pmid_matched" if ok else "unverified"})
    todo = [s for s in out if s["record_id"] is None and s.get("doi")]
    by_doi = pmids_by_doi(sorted({norm_doi(s["doi"]) for s in todo}))
    rest = [s for s in todo if norm_doi(s["doi"]) not in by_doi]
    by_doi.update({k[4:]: v for k, v in resolve_external(
        [("DOI:" + d, d) for d in sorted({norm_doi(s["doi"]) for s in rest})]).items()})
    texts = record_texts(sorted(set(by_doi.values())))
    for s in todo:
        rec = by_doi.get(norm_doi(s["doi"]))
        if rec and title_match(s["title"], (texts.get(rec) or ("",))[0]) >= TITLE_MATCH:
            s["record_id"], s["verification"] = rec, "doi_resolved"
    for s in out:
        if s["record_id"] is None and s.get("title"):
            rec = title_search(s["title"])
            if rec:
                s["record_id"], s["verification"] = rec, "pmid_corrected"
    return out


def store_web(arm: str, pairs: pd.DataFrame, answers: dict[str, tuple[int | None, list[dict]]], refused: set[str]) -> None:
    """Replace the pairs' studies of `arm`; for the web arm also their web_agent search row (refusals recorded with
    no hits) and hits (one per verified record), in one transaction."""
    cut = {pair_key(e, m): int(c) for e, m, c in zip(pairs.ensembl_id, pairs.mondo_id, pairs.cutoff_year)}
    keys = [tuple(k.split("|")) for k in (*answers, *refused)]
    studies = [(arm, *k.split("|"), cut[k], i, s["kind"], s["title"] or "", s.get("year"), s.get("venue"),
                s.get("pmid_given", s.get("pmid")), s.get("doi"), s["record_id"], s["verification"], d)
               for k, (d, ss) in answers.items() for i, s in enumerate(ss)]
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE chunk_pairs (ensembl_id text, mondo_id text) ON COMMIT DROP")
        execute_values(cur, "INSERT INTO chunk_pairs VALUES %s", keys)
        cur.execute("DELETE FROM preclin.target_literature_web_study w USING chunk_pairs c WHERE w.arm = %s "
                    "AND (w.ensembl_id, w.mondo_id) = (c.ensembl_id, c.mondo_id)", (arm,))
        execute_values(cur, """INSERT INTO preclin.target_literature_web_study (arm, ensembl_id, mondo_id, cutoff_year,
                                   ordinal, kind, title, year, venue, pmid_given, doi_given, record_id, verification,
                                   llm_decision_id) VALUES %s""", studies, page_size=2000)
        if arm == "web":
            cur.execute("DELETE FROM preclin.target_literature_hit h USING chunk_pairs c WHERE h.source = 'web_agent' "
                        "AND (h.ensembl_id, h.mondo_id) = (c.ensembl_id, c.mondo_id)")
            cur.execute("DELETE FROM preclin.target_literature_search s USING chunk_pairs c WHERE s.source = 'web_agent' "
                        "AND (s.ensembl_id, s.mondo_id) = (c.ensembl_id, c.mondo_id)")
            hits = {(*k.split("|"), cut[k], s["record_id"]) for k, (_, ss) in answers.items() for s in ss if s["record_id"]}
            execute_values(cur, """INSERT INTO preclin.target_literature_search (ensembl_id, mondo_id, cutoff_year, source,
                                       kind, names, query, n_hits) VALUES %s""",
                           [(*k.split("|"), cut[k], "web_agent", "",
                             Json({"task": WEB_TASK.name, "prompt_version": WEB_TASK.prompt_version, "refused": k in refused}),
                             "refused by both models" if k in refused else f"{WEB_TASK.name} {WEB_TASK.prompt_version}",
                             sum(h[0] == k.split("|")[0] and h[1] == k.split("|")[1] for h in hits))
                            for k in (*answers, *refused)])
            execute_values(cur, """INSERT INTO preclin.target_literature_hit (ensembl_id, mondo_id, cutoff_year, source, kind,
                                       record_id) VALUES %s ON CONFLICT DO NOTHING""",
                           [(e, m, c, "web_agent", "", r) for e, m, c, r in sorted(hits)], page_size=5000)
        conn.commit()


def reconcile(args) -> None:
    """Bring the stored literature to the cohort as it is now, after a rebuild of programs or pairs, without deleting
    or rewriting any stored row. A cohort pair with searches stored but none at its current cutoff gets rows at the new
    cutoff linking the records of its latest earlier-stored cutoff (screens are keyed by pair and record, so they apply
    as they are); when the new cutoff is later, the years between are searched in every source and added (gap).
    Records dated after an earlier new cutoff stay as hits; the cutoff applied on read leaves them out. Pairs that
    left the cohort keep their rows. A cohort pair with no search stored is new: run names, origin, search,
    firecrawl --mode search, screen, firecrawl --mode related, web and web-screen with --pairs new (web-screen
    --pairs cohort --sources all then screens every record added here). With --pairs confirm the same brings the
    confirmation pairs to their cutoffs (their new pairs: --pairs confirm-new); pairs not among them keep their rows."""
    p = shard_of(pairs_of(args.pairs if args.pairs in ("cohort", "confirm") else "cohort"), args.shard)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT DISTINCT ensembl_id, mondo_id, cutoff_year FROM preclin.target_literature_search")
        stored: dict = {}
        for e, m, y in cur.fetchall():
            stored.setdefault((e, m), set()).add(y)
    moved = [(r, max(stored[(r.ensembl_id, r.mondo_id)])) for r in p.itertuples()
             if (r.ensembl_id, r.mondo_id) in stored and int(r.cutoff_year) not in stored[(r.ensembl_id, r.mondo_id)]]
    linked = {"search": 0, "hit": 0}
    with llm.connect() as conn, conn.cursor() as cur:
        for r, old in moved:
            cur.execute("""INSERT INTO preclin.target_literature_search (ensembl_id, mondo_id, cutoff_year, source, kind,
                                                                         names, query, n_hits)
                           SELECT ensembl_id, mondo_id, %s, source, kind, names,
                                  'as searched at cutoff ' || cutoff_year || ': ' || query, n_hits
                           FROM preclin.target_literature_search WHERE ensembl_id = %s AND mondo_id = %s AND cutoff_year = %s
                           ON CONFLICT DO NOTHING""", (int(r.cutoff_year), r.ensembl_id, r.mondo_id, old))
            linked["search"] += cur.rowcount
            cur.execute("""INSERT INTO preclin.target_literature_hit (ensembl_id, mondo_id, cutoff_year, source, kind, record_id)
                           SELECT ensembl_id, mondo_id, %s, source, kind, record_id FROM preclin.target_literature_hit
                           WHERE ensembl_id = %s AND mondo_id = %s AND cutoff_year = %s ON CONFLICT DO NOTHING""",
                        (int(r.cutoff_year), r.ensembl_id, r.mondo_id, old))
            linked["hit"] += cur.rowcount
        conn.commit()
    later = [(r, old) for r, old in moved if int(r.cutoff_year) > old]
    # A pair linked forward by an earlier run whose gap search never finished: its PubMed row at the new cutoff is
    # still only the link, so the years between are searched now (resuming a run that stopped).
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT ensembl_id, mondo_id, cutoff_year FROM preclin.target_literature_search
                       WHERE source = 'pubmed' AND query LIKE 'as searched at cutoff %%' AND query NOT LIKE '%%| gap %%'""")
        pending = set(cur.fetchall())
    seen = {(r.ensembl_id, r.mondo_id) for r, _ in later}
    later += [(r, max(y for y in stored[(r.ensembl_id, r.mondo_id)] if y < int(r.cutoff_year)))
              for r in p.itertuples() if (r.ensembl_id, r.mondo_id, int(r.cutoff_year)) in pending
              and (r.ensembl_id, r.mondo_id) not in seen
              and any(y < int(r.cutoff_year) for y in stored.get((r.ensembl_id, r.mondo_id), ()))]
    if later:
        gap(p[[(e, m) in {(r.ensembl_id, r.mondo_id) for r, _ in later} for e, m in zip(p.ensembl_id, p.mondo_id)]],
            {(r.ensembl_id, r.mondo_id): old for r, old in later})
    cohort = {(e, m) for e, m in zip(p.ensembl_id, p.mondo_id)}
    print(json.dumps({"cohort_pairs": len(p), "new": int(sum(k not in stored for k in cohort)),
                      "left_rows_kept": int(sum(k not in cohort for k in stored)),
                      "cutoff_later": len(later), "cutoff_earlier": len(moved) - len(later),
                      "rows_linked_to_new_cutoff": linked}, indent=2))


def gap(p: pd.DataFrame, old_cutoff: dict[tuple[str, str], int]) -> None:
    """For pairs whose cutoff moved later (p, with old_cutoff), search only the years after the old cutoff up to the
    new one, in every source the run uses, and add the results to the pair's rows at the new cutoff (add_search):
    PubMed and Europe PMC by the run's queries, the origin search's records of those years, Firecrawl once per kind,
    and the web arm asked at the new cutoff with only its studies of those years added. Nothing is removed."""
    nm = pair_names(p, run=False)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT ensembl_id, mondo_id, service, query FROM preclin.target_disease_search")
        origin_q = {(e, m, sv): q for e, m, sv, q in cur.fetchall()}
    for r in p.itertuples():
        e, m, hi = r.ensembl_id, r.mondo_id, int(r.cutoff_year)
        lo = old_cutoff[(e, m)] + 1
        n = nm[pair_key(e, m)]
        pm, ep = clauses(n)
        pq, pn, pmids = pubmed_ids([], hi, term=lambda a, b, pm=pm: f'{pm} AND ("{max(a, str(lo))}"[dp] : "{b}"[dp]) {NOT_REVIEWS}')
        eq, en, records = epmc_records([], hi, query=f'{ep} AND PUB_YEAR:[{lo} TO {hi}] AND NOT SRC:MED '
                                                     'AND HAS_ABSTRACT:Y AND NOT PUB_TYPE:"review"')
        fetch_texts([x for x in pmids if x not in record_texts(pmids)])
        fc = {}
        for k in KINDS:
            throttle.wait("firecrawl", FIRECRAWL_PER_SECOND)
            res = firecrawl_cli(["search-papers", firecrawl_query(r.symbol, n["gene"], r.disease, k), "--limit",
                                 str(FIRECRAWL_RESULTS), "--from", f"{lo}-01-01", "--to", f"{hi}-12-31"])
            got = firecrawl_ids([x for x in res if (x.get("createdDate") or "0000")[:4] >= str(lo)], hi)
            ext = resolve_external([g for g in got if not g[0].isdigit()])
            fc[k] = (len(res), sorted({g if g.isdigit() else ext[g] for g, _ in got if g.isdigit() or g in ext}))
        with llm.connect() as conn, conn.cursor() as cur:
            cur.execute("""SELECT service, regexp_replace(record_id, '^PMID:', '') FROM preclin.target_disease_source
                           WHERE ensembl_id = %s AND mondo_id = %s AND year BETWEEN %s AND %s""", (e, m, lo, hi))
            orig: dict = {}
            for sv, rid in cur.fetchall():
                orig.setdefault(sv, []).append(rid)
            store_records(cur, records)
            tag = f"gap {lo}-{hi}"
            add_search(cur, e, m, hi, "pubmed", "", n, f"{tag}: {pq}", pn, pmids)
            add_search(cur, e, m, hi, "europepmc", "", n, f"{tag}: {eq}", en, [x[0] for x in records])
            for sv, ids in orig.items():
                add_search(cur, e, m, hi, "origin_" + sv, "", n, f"{tag}: {origin_q.get((e, m, sv), '')}", len(ids), ids)
            for k, (cnt, ids) in fc.items():
                add_search(cur, e, m, hi, "firecrawl", k, n, f"{tag}: {firecrawl_query(r.symbol, n['gene'], r.disease, k)}",
                           cnt, ids)
            conn.commit()
        print(f"gap {r.symbol} x {r.disease} {lo}-{hi}: pubmed={len(pmids)} europepmc={len(records)} "
              f"origin={sum(map(len, orig.values()))} firecrawl={sum(len(v[1]) for v in fc.values())}", flush=True)
    dec, refused = ask(WEB_TASK, WEB_FALLBACK, p)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT ensembl_id, mondo_id, coalesce(max(ordinal), -1), array_agg(record_id) FROM
                       preclin.target_literature_web_study WHERE arm = 'web' GROUP BY 1, 2""")
        prior = {(e, m): (o, set(x for x in rs if x)) for e, m, o, rs in cur.fetchall()}
        for key, (d, o) in dec.items():
            e, m = key.split("|")
            lo, hi = old_cutoff[(e, m)], int(p[(p.ensembl_id == e) & (p.mondo_id == m)].cutoff_year.iloc[0])
            last, have = prior.get((e, m), (-1, set()))
            new = [x for x in verify_studies(o["studies"]) if x.get("year") and lo < x["year"] <= hi
                   and x["record_id"] not in have]
            if new:
                execute_values(cur, """INSERT INTO preclin.target_literature_web_study (arm, ensembl_id, mondo_id,
                                           cutoff_year, ordinal, kind, title, year, venue, pmid_given, doi_given, record_id,
                                           verification, llm_decision_id) VALUES %s""",
                               [("web", e, m, hi, last + 1 + i, x["kind"], x["title"] or "", x.get("year"), x.get("venue"),
                                 x.get("pmid"), x.get("doi"), x["record_id"], x["verification"], d)
                                for i, x in enumerate(new)])
            ids = sorted({x["record_id"] for x in new if x["record_id"]})
            add_search(cur, e, m, hi, "web_agent", "", {"task": WEB_TASK.name, "prompt_version": WEB_TASK.prompt_version,
                                                        "refused": False},
                       f"gap {lo + 1}-{hi}: {WEB_TASK.name} {WEB_TASK.prompt_version} at cutoff {hi}", len(ids), ids)
        conn.commit()
    print(f"gap web: pairs={len(p)} answered={len(dec)} refused={len(refused)}", flush=True)


def ask(task: llm.Task, fallback: llm.Task, pairs: pd.DataFrame) -> tuple[dict[str, tuple[int, dict]], set[str]]:
    """Each pair's answer from task, or from fallback where task refused or failed; and the pairs neither answered.
    A pair the fallback already answered is not asked again."""
    items = reference_payloads(pairs)
    dec = llm.current_decisions(fallback, items)
    dec.update(decide(task, {k: v for k, v in items.items() if k not in dec}))
    rest = {k: v for k, v in items.items() if k not in dec}
    if rest:
        dec.update(decide(fallback, rest))
    return dec, set(items) - set(dec)


def shard_of(p: pd.DataFrame, shard: str | None) -> pd.DataFrame:
    if not shard:
        return p
    i, n = map(int, shard.split("/"))
    return p[[zlib.crc32(pair_key(e, m).encode()) % n == i - 1 for e, m in zip(p.ensembl_id, p.mondo_id)]]






SOURCES = ("pubmed", "europepmc", "firecrawl", "firecrawl_related", "origin_pubmed", "origin_europepmc", "web_agent")


def add_search(cur, e: str, m: str, y: int, source: str, kind: str, n: dict, query: str, n_hits: int,
               record_ids: list[str]) -> None:
    """Add a search's results to the pair's search row at cutoff y without removing anything: a new row, or the
    query and hit count appended to an existing one; hits are added, never replaced (unlike store_search)."""
    cur.execute("""INSERT INTO preclin.target_literature_search (ensembl_id, mondo_id, cutoff_year, source, kind, names,
                                                                 query, n_hits)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (ensembl_id, mondo_id, cutoff_year, source, kind)
                   DO UPDATE SET query = target_literature_search.query || ' | ' || EXCLUDED.query,
                                 n_hits = target_literature_search.n_hits + EXCLUDED.n_hits, searched_at = now()""",
                (e, m, y, source, kind, Json(n), query, n_hits))
    if record_ids:
        execute_values(cur, """INSERT INTO preclin.target_literature_hit (ensembl_id, mondo_id, cutoff_year, source, kind,
                                                                          record_id)
                               VALUES %s ON CONFLICT DO NOTHING""", [(e, m, y, source, kind, r) for r in record_ids],
                       page_size=5000)


def web_done() -> set[tuple[str, str]]:
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT ensembl_id, mondo_id FROM preclin.target_literature_search WHERE source = 'web_agent'")
        return set(cur.fetchall())


def web(args) -> None:
    """The web arm over every cohort pair not yet stored (--shard i/n to run n in parallel): ask, verify, store,
    WEB_CHUNK pairs at a time, so an interrupted run resumes where it stopped and reuses stored decisions."""
    p = shard_of(pairs_of(args.pairs), args.shard)
    done = web_done()
    p = p[[(e, m) not in done for e, m in zip(p.ensembl_id, p.mondo_id)]]
    print(f"web: pairs to ask={len(p)}", flush=True)
    for start in range(0, len(p), WEB_CHUNK):
        chunk = p.iloc[start:start + WEB_CHUNK]
        for attempt in range(5):  # a dropped database link mid-chunk: the decisions are stored, so retry the chunk
            try:
                dec, refused = ask(WEB_TASK, WEB_FALLBACK, chunk)
                answers = {k: (d, verify_studies(o["studies"])) for k, (d, o) in dec.items()}
                store_web("web", chunk, answers, refused)
                break
            except (psycopg2.OperationalError, psycopg2.InterfaceError, SourceDown) as exc:
                print(f"web chunk {start // WEB_CHUNK + 1}: database or Europe PMC unavailable ({exc}); retrying",
                      flush=True)
                time.sleep(120 * (attempt + 1))
        else:
            raise RuntimeError(f"web chunk {start // WEB_CHUNK + 1}: database unavailable")
        n = sum(len(ss) for _, ss in answers.values())
        v = sum(s["record_id"] is not None for _, ss in answers.values() for s in ss)
        print(f"web chunk {start // WEB_CHUNK + 1}: pairs={len(chunk)} refused={len(refused)} studies={n} verified={v}",
              flush=True)


def web_screen(args) -> None:
    """Screen every record from --sources (default web_agent) of the pairs not yet read for that pair at the screen
    version stored (--screen-version), with that screen (and its fallback), adding rows only: one screen definition
    for every record. A record the web arm named skips the
    prefilter (a cost saving for large literatures that has no bearing on a named study); any other record keeps an
    earlier prefilter-out decision."""
    p = shard_of(pairs_of(args.pairs), args.shard)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT h.ensembl_id, h.mondo_id, h.record_id FROM preclin.target_literature_hit h
                       WHERE h.source = ANY(%s)
                         AND (h.source = 'web_agent' OR NOT EXISTS (
                           SELECT 1 FROM preclin.target_literature_prefilter f WHERE NOT f.possibly
                           AND (f.ensembl_id, f.mondo_id, f.record_id) = (h.ensembl_id, h.mondo_id, h.record_id)))
                         AND NOT EXISTS (
                           SELECT 1 FROM preclin.target_literature_screen s
                           WHERE (s.ensembl_id, s.mondo_id, s.record_id) = (h.ensembl_id, h.mondo_id, h.record_id)
                             AND s.screen_version = %s)""",
                    (list(SOURCES) if args.sources == "all" else args.sources.split(","), SCREEN_VERSION))
        recs = pd.DataFrame(cur.fetchall(), columns=["ensembl_id", "mondo_id", "record_id"])
    want = set(zip(p.ensembl_id, p.mondo_id))
    recs = recs[[(e, m) in want for e, m in zip(recs.ensembl_id, recs.mondo_id)]]
    print(f"web screen: records to screen={len(recs)}", flush=True)
    for start in range(0, len(recs), 5000):
        part = recs.iloc[start:start + 5000]
        ids = sorted(set(part.record_id))
        have = set(record_texts(ids))
        fetch_texts([x for x in ids if x.isdigit() and x not in have])
        pp = p.merge(part[["ensembl_id", "mondo_id"]].drop_duplicates(), on=["ensembl_id", "mondo_id"])
        items = screen_payloads(pp, part)
        dec = decide(screen_task(), items)
        refused = {k: v for k, v in items.items() if k not in dec}
        if refused:
            dec.update(decide(screen_task(SCREEN_FALLBACK, "_fallback"), refused))
        rows = [(*k.split("|", 2), o["original_data"], o["disease_match"], *(o["kinds"][x] for x in KINDS[:4]),
                 o["agent_is_program_drug"], *(o["kinds"][x] for x in KINDS[4:]), o["quote"] or None, d)
                for k, (d, o) in dec.items()]
        with llm.connect() as conn, conn.cursor() as cur:
            execute_values(cur, f"""INSERT INTO preclin.target_literature_screen (ensembl_id, mondo_id, record_id,
                                        original_data, disease_match, {", ".join(KINDS[:4])}, agent_is_program_drug,
                                        {", ".join(KINDS[4:])}, quote, llm_decision_id, screen_version) VALUES %s
                                        ON CONFLICT DO NOTHING""",
                           [(*r, SCREEN_VERSION) for r in rows], page_size=2000)
            conn.commit()
        print(f"web screen: {start + len(part)}/{len(recs)} readable={len(items)} screened={len(dec)}", flush=True)


def yardstick_pairs() -> pd.DataFrame:
    """The yardstick's pairs: those the yardstick task answered (its validated decisions in pv_evidence.llm_decision,
    including pairs it found no study for), with the cutoff they were asked at; else a fresh draw of YARDSTICK_N
    cohort pairs outside the pilot (YARDSTICK_SEED). The stored draw was made on 2026-11-24 from the cohort as it then
    stood, so it is read back from the database, not redrawn."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT split_part(d.subject_key, '|', 1), split_part(d.subject_key, '|', 2),
                                       (d.input_payload->>'cutoff_year')::int, d.input_payload->>'symbol',
                                       d.input_payload->>'disease'
                       FROM pv_evidence.llm_decision d
                       WHERE d.task IN (%s, %s) AND d.validation_status = 'validated'""",
                    (YARDSTICK_TASK.name, YARDSTICK_FALLBACK.name))
        stored = pd.DataFrame(cur.fetchall(), columns=["ensembl_id", "mondo_id", "cutoff_year", "symbol", "disease"])
    if len(stored):
        return stored.sort_values(["ensembl_id", "mondo_id"]).reset_index(drop=True)
    p = cohort_pairs()
    pil = set(zip(pilot_pairs().ensembl_id, pilot_pairs().mondo_id))
    p = p[[(e, m) not in pil for e, m in zip(p.ensembl_id, p.mondo_id)]].reset_index(drop=True)
    rng = np.random.default_rng(YARDSTICK_SEED)
    return p.iloc[rng.choice(len(p), YARDSTICK_N, replace=False)].reset_index(drop=True)


def yardstick(_args) -> None:
    """The yardstick: a differently set up web-enabled model (YARDSTICK_SYSTEM, starting from reviews and
    citations; YARDSTICK_MODEL) lists every qualifying study of YARDSTICK_N seeded cohort pairs outside the pilot."""
    p = yardstick_pairs()
    dec, refused = ask(YARDSTICK_TASK, YARDSTICK_FALLBACK, p)
    answers = {k: (d, verify_studies(o["studies"])) for k, (d, o) in dec.items()}
    store_web("yardstick", p, answers, refused)
    print(f"yardstick: pairs={len(p)} answered={len(answers)} refused={len(refused)} "
          f"studies={sum(len(ss) for _, ss in answers.values())}", flush=True)




def stored_qualifying(pairs: pd.DataFrame, version: str | None = None) -> pd.DataFrame:
    if version == "final":
        return kept_qualifying(pairs)
    return screen_qualifying(pairs, version)


def kept_qualifying(pairs: pd.DataFrame) -> pd.DataFrame:
    """As screen_qualifying, from each kind's kept screen version (the view preclin.target_literature_reading)."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE want_pairs (ensembl_id text, mondo_id text) ON COMMIT DROP")
        execute_values(cur, "INSERT INTO want_pairs VALUES %s", sorted(set(zip(pairs.ensembl_id, pairs.mondo_id))))
        cur.execute("""SELECT r.ensembl_id, r.mondo_id, r.record_id, coalesce(p.year, lr.year, o.year),
                              lower(coalesce(p.doi, lr.doi)), r.kind, r.agent_is_program_drug
                       FROM preclin.target_literature_reading r JOIN want_pairs USING (ensembl_id, mondo_id)
                       LEFT JOIN public.publications p ON p.pmid = r.record_id
                       LEFT JOIN preclin.literature_record lr ON lr.record_id = r.record_id
                       LEFT JOIN LATERAL (SELECT min(x.year) AS year FROM preclin.target_disease_source x
                                          WHERE x.record_id IN (r.record_id, 'PMID:' || r.record_id)) o ON true
                       WHERE r.counts""")
        rows = cur.fetchall()
    out = [(e, m, rid, year, doi, k) for e, m, rid, year, doi, k, _ in rows]
    out += [(e, m, rid, year, doi, "animal_model_pharmacology_other") for e, m, rid, year, doi, k, agent in rows
            if k == "animal_model_pharmacology" and agent is False]
    return pd.DataFrame(out, columns=["ensembl_id", "mondo_id", "record_id", "year", "doi", "kind"])


def screen_qualifying(pairs: pd.DataFrame, version: str | None = None) -> pd.DataFrame:
    """ensembl_id, mondo_id, record_id, year, doi and kind of every stored screen row that counts for a kind (counts),
    read from preclin.target_literature_screen: unlike qualifying, it does not rebuild the screen's inputs, which
    name the program drugs and so move when programs are rebuilt."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE want_pairs (ensembl_id text, mondo_id text) ON COMMIT DROP")
        execute_values(cur, "INSERT INTO want_pairs VALUES %s", sorted(set(zip(pairs.ensembl_id, pairs.mondo_id))))
        cur.execute(f"""SELECT s.ensembl_id, s.mondo_id, s.record_id, coalesce(p.year, r.year, o.year),
                               lower(coalesce(p.doi, r.doi)), {", ".join("s." + k for k in KINDS)}, s.agent_is_program_drug
                        FROM (SELECT DISTINCT ON (ensembl_id, mondo_id, record_id) * FROM preclin.target_literature_screen
                              JOIN want_pairs USING (ensembl_id, mondo_id)
                              WHERE %(version)s IS NULL OR screen_version = %(version)s
                              ORDER BY ensembl_id, mondo_id, record_id, screen_version DESC) s
                        LEFT JOIN public.publications p ON p.pmid = s.record_id
                        LEFT JOIN preclin.literature_record r ON r.record_id = s.record_id
                        LEFT JOIN LATERAL (SELECT min(x.year) AS year FROM preclin.target_disease_source x
                                           WHERE x.record_id IN (s.record_id, 'PMID:' || s.record_id)) o ON true
                        WHERE s.original_data AND s.disease_match = 'same_or_subtype'""", {"version": version})
        rows = cur.fetchall()
    want = set(zip(pairs.ensembl_id, pairs.mondo_id))
    out = []
    for e, m, rid, year, doi, *flags in rows:
        if (e, m) not in want:
            continue
        shown, agent = dict(zip(KINDS, flags[:-1])), flags[-1]
        out += [(e, m, rid, year, doi, k) for k in KINDS if shown[k]]
        if shown["animal_model_pharmacology"] and agent is False:
            out.append((e, m, rid, year, doi, "animal_model_pharmacology_other"))
    return pd.DataFrame(out, columns=["ensembl_id", "mondo_id", "record_id", "year", "doi", "kind"])


def web_score(_args) -> None:
    """Recall of the abstract run, the web arm and their union against the yardstick, per kind: the share of the
    yardstick's verified studies (those with a record, verify_studies) found among the records counting for the kind
    from that arm's hits (recall_all_studies also counts unverified studies, as misses); per kind the cohort
    pairs with a counting record, and those with one only from the web arm; and the union's Phase 2 coverage."""
    ys = yardstick_pairs()
    cp = cohort_pairs()
    cut = {(r.ensembl_id, r.mondo_id): int(r.cutoff_year) for r in ys.itertuples()}  # the cutoff each pair was asked at
    in_cohort = set(zip(cp.ensembl_id, cp.mondo_id))
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT ensembl_id, mondo_id, kind, record_id, doi_given, year FROM preclin.target_literature_web_study
                       WHERE arm = 'yardstick'""")
        ref = pd.DataFrame(cur.fetchall(), columns=["ensembl_id", "mondo_id", "kind", "record_id", "doi", "year"])
        cur.execute("""SELECT DISTINCT ensembl_id, mondo_id, record_id, source = 'web_agent' FROM preclin.target_literature_hit""")
        arms = pd.DataFrame(cur.fetchall(), columns=["ensembl_id", "mondo_id", "record_id", "web"])
    by_arm = arms.groupby(["ensembl_id", "mondo_id", "record_id"]).web.agg(["any", "all"]).reset_index()
    q = stored_qualifying(pd.concat([cp, ys]))
    q = q.merge(by_arm, on=["ensembl_id", "mondo_id", "record_id"], how="left")
    q["from_web"], q["from_abstract"] = q["any"].fillna(False), ~q["all"].fillna(False)
    result = {"yardstick_pairs": len(ys), "kinds": {}}
    entries = cohort_entries()
    e2 = entries[entries.phase == 2]
    for kind in (*KINDS, "animal_model_pharmacology_other"):
        ref_kind = "animal_model_pharmacology_other" if kind == "animal_model_pharmacology" else kind
        studies = ref[(ref.kind == ref_kind) & (ref.year.isna() | (ref.year <= ref.apply(
            lambda r: cut[(r.ensembl_id, r.mondo_id)], axis=1)))] if len(ref) else ref
        qk = q[q.kind == kind]
        sets = {}
        for arm, mask in (("abstract", qk.from_abstract), ("web", qk.from_web), ("union", qk.from_abstract | qk.from_web)):
            g = qk[mask]
            sets[arm] = {(e, m): set(x.record_id) | {norm_doi(d) for d in x.doi.dropna()}
                         for (e, m), x in g.groupby(["ensembl_id", "mondo_id"])}
        rec, rec_all = {}, {}
        for arm, got in sets.items():
            hit, hit_all = [], []
            for s in studies.itertuples():
                found = isinstance(s.record_id, str) and s.record_id in got.get((s.ensembl_id, s.mondo_id), set())
                hit_all.append(found)
                if isinstance(s.record_id, str):
                    hit.append(found)
            rec[arm] = float(np.mean(hit)) if hit else None
            rec_all[arm] = float(np.mean(hit_all)) if hit_all else None
        pairs_any = {(e, m) for e, m in zip(qk.ensembl_id, qk.mondo_id)} & in_cohort
        pairs_abs = {(e, m) for e, m in zip(qk[qk.from_abstract].ensembl_id, qk[qk.from_abstract].mondo_id)} & in_cohort
        years = {k: g.year.dropna().astype(int).tolist() for k, g in qk.groupby(["ensembl_id", "mondo_id"])}
        cov = [any(y <= r.entry_year - 1 for y in years.get((r.ensembl_id, r.mondo_id), [])) for r in e2.itertuples()]
        result["kinds"][kind] = {
            "yardstick_studies": len(studies),
            "yardstick_studies_verified": int(studies.record_id.notna().sum()) if len(studies) else 0,
            "recall_abstract": rec["abstract"], "recall_web": rec["web"], "recall_union": rec["union"],
            "recall_all_studies": rec_all,
            "cohort_pairs_with_any": len(pairs_any), "cohort_pairs_from_abstract_arm": len(pairs_abs),
            "cohort_pairs_only_from_web_arm": len(pairs_any - pairs_abs),
            "phase2_coverage_union": float(np.mean(cov)) if cov else None}
    print(json.dumps(result, indent=2))


# --- resolve: the confirmed set, coverage and precision -----------------------------------------------------------

ADJUDICATE_MODEL = "claude-opus-5-5"
ADJUDICATE_TOOLS = [{"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 3}]
NEGATIVE_SAMPLE = 300  # seeded retrieved records of the yardstick's pairs that the screen read as showing no kind
NEGATIVE_SEED = 20261125

ADJUDICATE_SYSTEM = """You are the adjudicator who builds the confirmed set against which literature searches are scored. You judge ONE paper for ONE human gene or its protein (the target) and ONE disease, strictly, from the paper itself. Several searches found this paper; decide whether it truly reports each kind of evidence below. Do not search for other papers.

Read the title and abstract given. When they do not settle a kind (for example the abstract mentions knockdown but not in which cells, or says "biomarker" without saying where it was measured), open the paper's full text with web_fetch (the PubMed Central, Europe PMC or publisher page from the link given) and read the methods, results and figure legends. Set full_text_read accordingly.

original_data: true when the paper reports new experimental or clinical results (not a review, commentary, guideline, protocol or opinion).

disease_match: the disease the evidence is about, against the disease given: same_or_subtype (the same disease, a subtype, a near-identical disease, or an animal or cell model of it), related (a related but distinct disease), other, or none.

kinds: true for each kind the paper shows about THIS target (any of its names; a different gene of the same family does not count) in the disease under disease_match, with original data:
""" + "\n".join(f"- {k}: {v}" for k, v in KIND_TEXT.items()) + """

Boundaries, decided by the system and by HOW the target was changed:
- Primary versus established cells: primary means cells or tissue taken from people (patients or healthy donors) and used directly or in short-term culture: PBMCs and isolated immune cells, primary fibroblasts, endothelial cells such as HUVEC, primary tumour cells, patient-derived organoids, iPSC-derived cells, tissue explants and slices. An established line is an immortalised or continuous line (HeLa, HEK293, Jurkat, THP-1, named cancer lines, commercial immortalised lines). Cells grown in animals (xenografts, PDX) are animal models.
- Perturbation means the experimenter changes the target (knockdown, knockout, overexpression, or an inhibitor, antibody or agonist acting on it) and a feature of the disease changes (the disease's cells grow, die, invade or signal differently; a disease-relevant output changes). Only measuring the target's level does not count as perturbation.
- Animal pharmacology versus animal genetics: a heritable genetic change of the target (germline or conditional knockout, knock-in, transgene, in vivo genome editing) is mouse_genetic_disease_model; a drug, antibody, tool compound, siRNA, antisense or viral vector given to the animal is animal_model_pharmacology. Either needs an animal model of THIS disease (induced, genetic or xenograft of this cancer); healthy animals do not count.
- Tissue versus fluid: the target's PROTEIN measured in patients' diseased tissue (biopsy, resection, autopsy) against normal or less-affected tissue is diseased_tissue_protein; RNA alone does not count. The target or its product measured in patients' blood, serum, plasma, CSF, urine, another fluid, or by imaging, in an OBSERVATIONAL study, and associated with the disease's presence, severity, progression or outcome, is observational_biomarker. Genetic association is neither.
- clinical_observation: an effect seen in people implicates the target in the disease: a side effect or unexpected benefit of a drug acting on the target outside trials of drugs for this disease, people with the target deficient or blocked, or autoantibodies against the target. Efficacy trials of drugs in this disease do not count.

A paper whose only agent is a program drug named below can show animal_model_pharmacology; mark agent_is_program_drug true then, false when another agent was used, and null when animal_model_pharmacology is false. A kind is true only when the paper shows the finding. Quote the sentence that decided the reading (empty when nothing qualifies)."""

ADJUDICATE_SCHEMA = {"type": "object", "additionalProperties": False,
                     "properties": {**{k: v for k, v in SCREEN_SCHEMA["properties"].items() if k != "system"},
                                    "full_text_read": {"type": "boolean"}},
                     "required": ["original_data", "disease_match", "kinds", "agent_is_program_drug", "quote",
                                  "full_text_read"]}


def render_adjudicate(p: dict) -> str:
    return render_screen(p) + f"\nLink: {p['link']}\nCutoff year: {p['cutoff_year']}"


# v2 of the rubric, after the spot check (SPOT_CHECK): every disagreement was a lenient YES at a kind's boundary.
ADJUDICATE_SYSTEM_V2 = ADJUDICATE_SYSTEM.replace(
    "A paper whose only agent is a program drug",
    """Stricter boundaries:
- Viral, transgenic or other genetic expression of the target (wild type or mutant) that creates or alters an animal model is mouse_genetic_disease_model, never animal_model_pharmacology; animal_model_pharmacology needs an agent acting on the target (drug, antibody, tool compound, siRNA or antisense) given to a model.
- Genome editing of cells that are then transplanted into an animal (a xenograft) is cell_line_perturbation or human_cell_perturbation by the cells' origin, not mouse_genetic_disease_model.
- human_cell_perturbation needs human cells or tissue; a study in animals or animal cells is never this kind.
- Human germline variants of the gene (carriers, null or loss-of-function variants, families) are genetics, not clinical_observation.
- A single case or a series of two patients does not count for observational_biomarker or clinical_observation.
- Perturbing cells (platelets, blood cells) ex vivo is perturbation, not observational_biomarker.
- An agent that acts on many targets counts for this target only when the paper attributes the effect to this target specifically.
- Decide only from the text given or the full text you open: never from your memory of a paper. When neither shows the finding, the kind is false.

A paper whose only agent is a program drug""")
assert ADJUDICATE_SYSTEM_V2 != ADJUDICATE_SYSTEM
ADJUDICATE_VERSION = "v2"  # the rubric new readings are stored under
REVISED_KINDS = ("human_cell_perturbation", "animal_model_pharmacology", "mouse_genetic_disease_model",
                 "observational_biomarker", "clinical_observation")  # the kinds whose v1 YES calls v2 re-reads

ADJUDICATE_TASK = llm.Task(name="target_literature_adjudicate", prompt_version="v1", schema_version="v1",
                           system=ADJUDICATE_SYSTEM, schema=ADJUDICATE_SCHEMA, render=render_adjudicate,
                           validate=validate_screen, subject_type="pair_record", model=ADJUDICATE_MODEL, effort="high",
                           max_tokens=16000, tools=ADJUDICATE_TOOLS)
ADJUDICATE_FALLBACK = llm.Task(**{**ADJUDICATE_TASK.__dict__, "name": "target_literature_adjudicate_fallback",
                                  "model": REFERENCE_FALLBACK})
ADJUDICATE_V2 = llm.Task(**{**ADJUDICATE_TASK.__dict__, "prompt_version": "v2", "system": ADJUDICATE_SYSTEM_V2})
ADJUDICATE_V2_FALLBACK = llm.Task(**{**ADJUDICATE_FALLBACK.__dict__, "prompt_version": "v2", "system": ADJUDICATE_SYSTEM_V2})

# The spot check of 50 seeded v1 adjudications (the review packet, items 0-49 in order): a second-model review by the
# coordinating Claude session, delegated by Melissa and final: a second-model review (Claude), not human-verified. Verdict on the
# adjudicator's call: agree, disagree or unsure. Keyed (kind, ensembl_id, mondo_id, record_id).
SPOT_CHECK = {
    ("human_cell_perturbation", "ENSG00000159110", "MONDO:0005301", "11696016"): "agree",
    ("human_cell_perturbation", "ENSG00000188906", "MONDO:0005180", "27863501"): "agree",
    ("human_cell_perturbation", "ENSG00000198793", "MONDO:0001734", "23947572"): "agree",
    ("human_cell_perturbation", "ENSG00000188906", "MONDO:0005180", "22773119"): "agree",
    ("human_cell_perturbation", "ENSG00000188906", "MONDO:0005180", "22914360"): "agree",
    ("human_cell_perturbation", "ENSG00000121966", "MONDO:0009693", "17686053"): "agree",
    ("human_cell_perturbation", "ENSG00000128052", "MONDO:0005150", "28715845"): "disagree",
    ("cell_line_perturbation", "ENSG00000198793", "MONDO:0005575", "14729629"): "agree",
    ("cell_line_perturbation", "ENSG00000140443", "MONDO:0021038", "11410521"): "agree",
    ("cell_line_perturbation", "ENSG00000166851", "MONDO:0008315", "28043128"): "unsure",
    ("cell_line_perturbation", "ENSG00000188906", "MONDO:0005180", "20144646"): "agree",
    ("cell_line_perturbation", "ENSG00000112062", "MONDO:0004975", "23178511"): "agree",
    ("cell_line_perturbation", "ENSG00000188906", "MONDO:0005180", "27618216"): "unsure",
    ("cell_line_perturbation", "ENSG00000198793", "MONDO:0005575", "19517193"): "agree",
    ("diseased_tissue_protein", "ENSG00000149295", "MONDO:0005180", "9756147"): "agree",
    ("diseased_tissue_protein", "ENSG00000105329", "MONDO:0005233", "29253845"): "agree",
    ("diseased_tissue_protein", "ENSG00000112062", "MONDO:0004975", "21883897"): "unsure",
    ("diseased_tissue_protein", "ENSG00000157404", "MONDO:0004967", "9697876"): "unsure",
    ("diseased_tissue_protein", "ENSG00000010671", "MONDO:0007915", "28789968"): "agree",
    ("diseased_tissue_protein", "ENSG00000198793", "MONDO:0005575", "22333609"): "agree",
    ("diseased_tissue_protein", "ENSG00000198793", "MONDO:0005575", "19517193"): "agree",
    ("animal_model_pharmacology", "ENSG00000105329", "MONDO:0005233", "23806302"): "unsure",
    ("animal_model_pharmacology", "ENSG00000198793", "MONDO:0005575", "20416302"): "agree",
    ("animal_model_pharmacology", "ENSG00000169710", "MONDO:0007027", "21382219"): "agree",
    ("animal_model_pharmacology", "ENSG00000198793", "MONDO:0001734", "23437388"): "agree",
    ("animal_model_pharmacology", "ENSG00000197891", "MONDO:0005393", "21154198"): "agree",
    ("animal_model_pharmacology", "ENSG00000197891", "MONDO:0005393", "25499818"): "agree",
    ("animal_model_pharmacology", "ENSG00000188906", "MONDO:0005180", "21248115"): "disagree",
    ("animal_model_pharmacology", "ENSG00000188906", "MONDO:0005180", "25731749"): "disagree",
    ("mouse_genetic_disease_model", "ENSG00000188906", "MONDO:0005180", "25836420"): "agree",
    ("mouse_genetic_disease_model", "ENSG00000010671", "MONDO:0007915", "18849077"): "agree",
    ("mouse_genetic_disease_model", "ENSG00000010671", "MONDO:0007915", "26209625"): "unsure",
    ("mouse_genetic_disease_model", "ENSG00000198793", "MONDO:0001734", "22056141"): "agree",
    ("mouse_genetic_disease_model", "ENSG00000185000", "MONDO:0005148", "17618857"): "agree",
    ("mouse_genetic_disease_model", "ENSG00000077782", "MONDO:0005233", "18852144"): "unsure",
    ("mouse_genetic_disease_model", "ENSG00000188389", "MONDO:0001187", "30457360"): "disagree",
    ("observational_biomarker", "ENSG00000149295", "MONDO:0005180", "7884499"): "agree",
    ("observational_biomarker", "ENSG00000149295", "MONDO:0005180", "26419749"): "disagree",
    ("observational_biomarker", "ENSG00000188906", "MONDO:0005180", "ETH:625227"): "agree",
    ("observational_biomarker", "ENSG00000121966", "MONDO:0009693", "19335218"): "agree",
    ("observational_biomarker", "ENSG00000105329", "MONDO:0005233", "18034241"): "agree",
    ("observational_biomarker", "ENSG00000131473", "MONDO:0005148", "14681844"): "disagree",
    ("observational_biomarker", "ENSG00000121966", "MONDO:0009693", "25825601"): "agree",
    ("clinical_observation", "ENSG00000157404", "MONDO:0006951", "27319943"): "disagree",
    ("clinical_observation", "ENSG00000166603", "MONDO:0019182", "15126516"): "disagree",
    ("clinical_observation", "ENSG00000188906", "MONDO:0005180", "24355527"): "agree",
    ("clinical_observation", "ENSG00000109163", "MONDO:0008487", "16704856"): "agree",
    ("clinical_observation", "ENSG00000121966", "MONDO:0009693", "21183878"): "agree",
    ("clinical_observation", "ENSG00000144891", "MONDO:0100313", "23465123"): "unsure",
    ("clinical_observation", "ENSG00000166603", "MONDO:0019182", "10078568"): "disagree",
}
LENIENCY_PRIOR = 4.0  # pseudo-items of a kind's shrinkage toward its screen stratum's pooled agreement
LENIENCY_DRAWS = 2000
LENIENCY_SEED = 20261129


def record_link(record_id: str, doi: str | None) -> str:
    if record_id.isdigit():
        return f"https://pubmed.ncbi.nlm.nih.gov/{record_id}/"
    src, _, rid = record_id.partition(":")
    return f"https://europepmc.org/article/{src}/{rid}" if rid else (f"https://doi.org/{doi}" if doi else record_id)


def candidates() -> pd.DataFrame:
    """Every candidate study of the yardstick's pairs (ensembl_id, mondo_id, record_id, cutoff_year and its sources):
    the records the screen read as showing a kind, the verified studies the web arm and the yardstick named, and a
    seeded sample (NEGATIVE_SAMPLE) of retrieved records the screen read as showing none; each published by the
    pair's cutoff (or of unknown year). Unverified citations are not candidates: no paper behind them could be found."""
    ys = yardstick_pairs()
    cut = {(r.ensembl_id, r.mondo_id): int(r.cutoff_year) for r in ys.itertuples()}
    q = stored_qualifying(ys)
    screen = {(e, m, r) for e, m, r in zip(q.ensembl_id, q.mondo_id, q.record_id)}
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT arm, ensembl_id, mondo_id, record_id FROM preclin.target_literature_web_study
                       WHERE record_id IS NOT NULL""")
        named = pd.DataFrame(cur.fetchall(), columns=["arm", "ensembl_id", "mondo_id", "record_id"])
        cur.execute(f"""SELECT ensembl_id, mondo_id, record_id FROM (
                            SELECT DISTINCT ON (ensembl_id, mondo_id, record_id) * FROM preclin.target_literature_screen
                            ORDER BY ensembl_id, mondo_id, record_id, screen_version DESC) s
                        WHERE NOT (s.original_data AND s.disease_match = 'same_or_subtype'
                                   AND ({" OR ".join(KINDS)}))""")
        negatives = [x for x in cur.fetchall() if (x[0], x[1]) in cut]
    named = named[[(e, m) in cut for e, m in zip(named.ensembl_id, named.mondo_id)]]
    web = set(zip(*[named[named.arm == "web"][c] for c in ("ensembl_id", "mondo_id", "record_id")]))
    yard = set(zip(*[named[named.arm == "yardstick"][c] for c in ("ensembl_id", "mondo_id", "record_id")]))
    texts = record_texts(sorted({x[2] for x in (*screen, *web, *yard, *negatives)}))
    by_cutoff = lambda x: (texts.get(x[2]) or (None, None, None))[2] is None or texts[x[2]][2] <= cut[(x[0], x[1])]  # noqa: E731
    screen, web, yard = ({x for x in s if by_cutoff(x)} for s in (screen, web, yard))
    negatives = sorted({x for x in negatives if by_cutoff(x)} - screen - web - yard)
    rng = np.random.default_rng(NEGATIVE_SEED)
    sample = {negatives[i] for i in rng.choice(len(negatives), min(NEGATIVE_SAMPLE, len(negatives)), replace=False)}
    keys = sorted(screen | web | yard | sample)
    return pd.DataFrame([(e, m, r, cut[(e, m)], (e, m, r) in screen, (e, m, r) in web, (e, m, r) in yard,
                          (e, m, r) in sample) for e, m, r in keys],
                        columns=["ensembl_id", "mondo_id", "record_id", "cutoff_year", "from_screen", "from_web",
                                 "from_yardstick", "screened_out_sample"])


def adjudicate_payloads(c: pd.DataFrame) -> dict[str, dict]:
    pairs = yardstick_pairs()
    items = screen_payloads(pairs, c[["ensembl_id", "mondo_id", "record_id"]])
    cut = {(r.ensembl_id, r.mondo_id): int(r.cutoff_year) for r in pairs.itertuples()}
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT pmid, doi FROM public.publications WHERE pmid = ANY(%s)", (sorted(set(c.record_id)),))
        dois = dict(cur.fetchall())
    for k, v in items.items():
        e, m, r = k.split("|", 2)
        v["link"] = record_link(r, dois.get(r))
        v["cutoff_year"] = cut[(e, m)]
    return items


def adjudicate(args) -> None:
    """Judge every candidate (candidates) once with ADJUDICATE_TASK (the fallback model reads what it refuses) and
    store the readings in preclin.target_literature_adjudication, replacing the table's rows of the same records."""
    v2 = getattr(args, "rubric", "v1") == "v2"
    c = shard_of(candidates(), args.shard)
    if v2:  # re-read only the v1 YES calls of the revised kinds
        a = adjudicated("v1")
        yes = a[a[["true_" + k for k in REVISED_KINDS]].any(axis=1)]
        c = c.merge(yes[["ensembl_id", "mondo_id", "record_id"]], on=["ensembl_id", "mondo_id", "record_id"])
    print(f"adjudicate: candidates={len(c)} screen={int(c.from_screen.sum())} web={int(c.from_web.sum())} "
          f"yardstick={int(c.from_yardstick.sum())} screened-out sample={int(c.screened_out_sample.sum())}", flush=True)
    items = adjudicate_payloads(c)
    print(f"adjudicate: readable={len(items)} (no stored text: {len(c) - len(items)})", flush=True)
    task, fallback = (ADJUDICATE_V2, ADJUDICATE_V2_FALLBACK) if v2 else (ADJUDICATE_TASK, ADJUDICATE_FALLBACK)
    dec = decide(task, items)
    rest = {k: v for k, v in items.items() if k not in dec}
    if rest:
        dec.update(decide(fallback, rest))
    years = {k: v["year"] for k, v in items.items()}
    with llm.connect() as conn, conn.cursor() as cur:  # full text read: the reader fetched a page (its own flag can lag)
        cur.execute("SELECT llm_decision_id, coalesce((usage->>'web_fetch_requests')::int, 0) > 0 FROM pv_evidence.llm_decision "
                    "WHERE llm_decision_id = ANY(%s)", ([d for d, _ in dec.values()],))
        fetched = dict(cur.fetchall())
    src = {(r.ensembl_id, r.mondo_id, r.record_id): r for r in c.itertuples()}
    rows = []
    for k, (d, o) in dec.items():
        r = src[tuple(k.split("|", 2))]
        rows.append((r.ensembl_id, r.mondo_id, r.record_id, r.cutoff_year, years[k], r.from_screen, r.from_web,
                     r.from_yardstick, r.screened_out_sample, o["original_data"], o["disease_match"],
                     *(o["kinds"][x] for x in KINDS[:4]), o["agent_is_program_drug"],
                     *(o["kinds"][x] for x in KINDS[4:]), o["full_text_read"] or fetched.get(d, False),
                     o["quote"] or None, d, "v2" if v2 else "v1"))
    with llm.connect() as conn, conn.cursor() as cur:
        execute_values(cur, f"""INSERT INTO preclin.target_literature_adjudication (ensembl_id, mondo_id, record_id,
                                    cutoff_year, year, from_screen, from_web, from_yardstick, screened_out_sample,
                                    original_data, disease_match, {", ".join(KINDS[:4])}, agent_is_program_drug,
                                    {", ".join(KINDS[4:])}, full_text_read, quote, llm_decision_id,
                                    adjudication_version) VALUES %s
                                ON CONFLICT (ensembl_id, mondo_id, record_id, adjudication_version) DO UPDATE SET
                                    from_screen = EXCLUDED.from_screen, from_web = EXCLUDED.from_web,
                                    from_yardstick = EXCLUDED.from_yardstick,
                                    screened_out_sample = EXCLUDED.screened_out_sample""", rows, page_size=1000)
        conn.commit()
    print(f"adjudicate: stored={len(rows)} unread={len(items) - len(dec)}", flush=True)


SCORE_KINDS = (*KINDS, "animal_model_pharmacology_other")
CR_BOOT = 2000  # parametric bootstrap draws for the capture-recapture intervals
CR_SEED = 20261126


def adjudicated(version: str | None = None) -> pd.DataFrame:
    """The adjudication's rows at their latest rubric version (up to ), each with the kinds it confirms (published by the pair's cutoff, original data, the
    pair's disease or a subtype; animal_model_pharmacology_other when the agent is not a program drug)."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute(f"""SELECT ensembl_id, mondo_id, record_id, cutoff_year, year, from_screen, from_web, from_yardstick,
                               screened_out_sample, original_data, disease_match, {", ".join(KINDS)}, agent_is_program_drug,
                               full_text_read, quote, adjudication_version FROM (
                            SELECT DISTINCT ON (ensembl_id, mondo_id, record_id) * FROM preclin.target_literature_adjudication
                            WHERE %(v)s IS NULL OR adjudication_version <= %(v)s
                            ORDER BY ensembl_id, mondo_id, record_id, adjudication_version DESC) a""", {"v": version})
        a = pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
    ok = a.original_data & a.disease_match.eq("same_or_subtype") & (a.year.isna() | (a.year <= a.cutoff_year))
    for k in KINDS:
        a["true_" + k] = ok & a[k]
    a["true_animal_model_pharmacology_other"] = a.true_animal_model_pharmacology & a.agent_is_program_drug.eq(False)
    return a


def arm_positives(version: str | None = None) -> dict[str, set[tuple[str, str, str, str]]]:
    """(ensembl_id, mondo_id, record_id, kind) each source reads as counting for the yardstick's pairs, by the pair's
    cutoff: abstract (the screen at `version`, records from a non-web search), web (the screen, records the web arm
    named), union (either), yardstick (the yardstick's verified studies under the kind it named)."""
    ys = yardstick_pairs()
    cut = {(r.ensembl_id, r.mondo_id): int(r.cutoff_year) for r in ys.itertuples()}
    q = stored_qualifying(ys, version)
    q = q[[pd.isna(y) or y <= cut[(e, m)] for e, m, y in zip(q.ensembl_id, q.mondo_id, q.year)]]
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT ensembl_id, mondo_id, record_id, source = 'web_agent' FROM preclin.target_literature_hit
                       WHERE (ensembl_id, mondo_id) IN %s""", (tuple(cut),))
        src: dict = {}
        for e, m, r, w in cur.fetchall():
            src.setdefault((e, m, r), set()).add(w)
        cur.execute("""SELECT ensembl_id, mondo_id, record_id, kind, year FROM preclin.target_literature_web_study
                       WHERE arm = 'yardstick' AND record_id IS NOT NULL""")
        yard = {(e, m, r, k) for e, m, r, k, y in cur.fetchall() if (e, m) in cut and (y is None or y <= cut[(e, m)])}
    out = {"abstract": set(), "web": set(), "union": set(), "yardstick": yard}
    for e, m, r, k in zip(q.ensembl_id, q.mondo_id, q.record_id, q.kind):
        how = src.get((e, m, r), set())
        out["union"].add((e, m, r, k))
        if False in how:
            out["abstract"].add((e, m, r, k))
        if True in how:
            out["web"].add((e, m, r, k))
    return out


def capture_recapture(hist: list[tuple[int, int, int]], rng: np.random.Generator) -> dict:
    """Log-linear capture-recapture for three sources: the observed histories (each a (s1, s2, s3) with at least one
    1), the model among independence and the three one-interaction models with the lowest AIC, its estimate of the
    unseen cell and of the total, and a parametric bootstrap interval for the total. Assumes a closed population and
    homogeneous capture within the dependence the chosen model allows."""
    import itertools
    import statsmodels.api as sm
    cells = [c for c in itertools.product((0, 1), repeat=3) if any(c)]
    n = np.array([sum(h == c for h in hist) for c in cells], dtype=float)
    if n.sum() < 5 or (n > 0).sum() < 3:
        return {"observed": int(n.sum()), "estimable": False}
    X0 = np.array(cells, dtype=float)
    designs = {"independence": X0}
    for (i, j), name in (((0, 1), "abstract×web"), ((0, 2), "abstract×yardstick"), ((1, 2), "web×yardstick")):
        designs[f"independence + {name}"] = np.column_stack([X0, X0[:, i] * X0[:, j]])

    def fit(X, y):
        try:
            r = sm.GLM(y, sm.add_constant(X, has_constant="add"), family=sm.families.Poisson()).fit()
        except Exception:
            return None
        return r if np.isfinite(r.params).all() else None

    fits = {k: fit(X, n) for k, X in designs.items()}
    fits = {k: r for k, r in fits.items() if r is not None and len(r.params) < len(cells)}
    name, best = min(fits.items(), key=lambda kv: kv[1].aic)
    unseen = float(np.exp(best.params[0]))
    mu = best.mu
    boot = []
    for _ in range(CR_BOOT):
        y = rng.poisson(mu)
        r = fit(designs[name], y.astype(float))
        if r is not None:
            boot.append(y.sum() + float(np.exp(r.params[0])))
    lo, hi = (np.percentile(boot, [2.5, 97.5]) if boot else (np.nan, np.nan))
    return {"observed": int(n.sum()), "histories": {"".join(map(str, c)): int(v) for c, v in zip(cells, n)},
            "model": name, "aic": float(best.aic), "unseen": unseen, "total": float(n.sum() + unseen),
            "total_lo": float(lo), "total_hi": float(hi), "estimable": True}


def resolve_metrics(version: str | None = None, adjudication: str | None = None) -> dict:
    """Per kind, against the adjudicated confirmed set: each source's coverage and precision at pair level and study
    level; what the screen missed among the screened-out sample; the capture-recapture estimate of the qualifying
    pairs every source missed and the coverage of the union against it; and the screen-versus-adjudicator confusion."""
    a = adjudicated(adjudication)
    pos = arm_positives(version)
    rng = np.random.default_rng(CR_SEED)
    pairs_total = len(yardstick_pairs())
    with llm.connect() as conn, conn.cursor() as cur:  # screened-out records of the yardstick's pairs, by cutoff
        cur.execute(f"""SELECT count(*) FROM (SELECT DISTINCT ON (ensembl_id, mondo_id, record_id) * FROM preclin.target_literature_screen
                            WHERE (%(v)s IS NULL OR screen_version = %(v)s) AND (ensembl_id, mondo_id) IN %(p)s
                            ORDER BY ensembl_id, mondo_id, record_id, screen_version DESC) s
                        WHERE NOT (s.original_data AND s.disease_match = 'same_or_subtype' AND ({" OR ".join(KINDS)}))""",
                    {"v": "v4" if version == "final" else version, "p": tuple(zip(a.ensembl_id, a.mondo_id))})
        negatives_total = cur.fetchone()[0]
    sample = a[a.screened_out_sample]
    out = {"version": version or "latest", "pairs": pairs_total, "candidates": len(a),
           "full_text_read": float(a.full_text_read.mean()), "screened_out_sample": len(sample),
           "screened_out_total": int(negatives_total), "kinds": {}}
    for k in SCORE_KINDS:
        t = a[a["true_" + k]]
        true_studies = set(zip(t.ensembl_id, t.mondo_id, t.record_id))
        true_pairs = {(e, m) for e, m, _ in true_studies}
        res = {"confirmed_studies": len(true_studies), "confirmed_pairs": len(true_pairs)}
        for arm, got in pos.items():
            studies = {(e, m, r) for e, m, r, kk in got if kk == k}
            pairs = {(e, m) for e, m, _ in studies}
            judged = {x for x in studies if x in set(zip(a.ensembl_id, a.mondo_id, a.record_id))}
            res[arm] = {"pairs_yes": len(pairs),
                        "coverage_pair": len(pairs & true_pairs) / len(true_pairs) if true_pairs else None,
                        "precision_pair": len(pairs & true_pairs) / len(pairs) if pairs else None,
                        "coverage_study": len(studies & true_studies) / len(true_studies) if true_studies else None,
                        "precision_study": len(judged & true_studies) / len(judged) if judged else None}
        missed = sample[sample["true_" + k]]
        res["screened_out"] = {"confirmed_in_sample": len(missed),
                               "estimated_missed_studies": len(missed) / len(sample) * negatives_total if len(sample) else None,
                               "pairs_only_from_sample": len({(e, m) for e, m in zip(missed.ensembl_id, missed.mondo_id)}
                                                             - {(e, m) for e, m, _, kk in pos["union"] | pos["yardstick"] if kk == k})}
        found = {arm: {(e, m) for e, m, r, kk in pos[arm] if kk == k and (e, m, r) in true_studies}
                 for arm in ("abstract", "web", "yardstick")}
        hist = [tuple(int(p in found[s]) for s in ("abstract", "web", "yardstick")) for p in true_pairs]
        hist = [h for h in hist if any(h)]
        cr = capture_recapture(hist, rng)
        if cr.get("estimable"):
            union_found = len(found["abstract"] | found["web"])
            cr["union_coverage_pair"] = union_found / cr["total"]
            cr["union_coverage_pair_lo"] = union_found / cr["total_hi"] if cr["total_hi"] else None
            cr["union_coverage_pair_hi"] = union_found / cr["total_lo"] if cr["total_lo"] else None
        res["capture_recapture"] = cr
        out["kinds"][k] = res
    conf: dict = {}
    reasons: dict = {}
    by_rec = {}
    for e, m, r, kk in pos["union"]:
        by_rec.setdefault((e, m, r), set()).add(kk)
    adj = a.set_index(["ensembl_id", "mondo_id", "record_id"])
    for key, kinds in by_rec.items():
        if key not in adj.index:
            continue
        row = adj.loc[key]
        truth = {k for k in SCORE_KINDS if row["true_" + k]}
        for kk in kinds:
            if kk in truth:
                conf.setdefault(kk, {}).setdefault(kk, 0)
                conf[kk][kk] += 1
                continue
            why = ("not original data" if not row.original_data else "disease not the pair's" if row.disease_match != "same_or_subtype"
                   else "after the cutoff" if pd.notna(row.year) and row.year > row.cutoff_year
                   else "another kind: " + ", ".join(sorted(truth)) if truth else "no kind")
            reasons.setdefault(kk, {}).setdefault(why, 0)
            reasons[kk][why] += 1
            for t in truth:
                conf.setdefault(kk, {}).setdefault(t, 0)
                conf[kk][t] += 1
    out["screen_kind_vs_adjudicated_kind"] = conf
    out["screen_false_positive_reasons"] = reasons
    return out


def leniency(a: pd.DataFrame, pos: dict) -> dict:
    """Coverage and precision at pair level corrected for the adjudicator's leniency, from the spot check (SPOT_CHECK):
    a confirmed study is real with the adjudicator's precision on YES calls for its kind and screen stratum (the
    screen found it, or only the adjudicator did), drawn from a Beta posterior that shrinks the kind's decided
    verdicts toward its stratum's pooled agreement (LENIENCY_PRIOR pseudo-items); each draw keeps each confirmed study
    with that probability and recomputes the rates. Unsure verdicts are left out; the adjudicator's NO calls are taken
    as right (the spot check found no disagreement with them). Medians and 95% intervals per kind and source."""
    rng = np.random.default_rng(LENIENCY_SEED)
    found_by = set(pos["union"])
    adj_yes = {(k, e, m, r) for k, e, m, r in SPOT_CHECK
               if a[(a.ensembl_id == e) & (a.mondo_id == m) & (a.record_id == r)]["true_" + k].any()}
    checks = [(k, (e, m, r, k) in found_by, v)
              for (k, e, m, r), v in SPOT_CHECK.items() if v != "unsure" and (k, e, m, r) in adj_yes]
    pooled = {s: (sum(v == "agree" for _, st, v in checks if st == s), sum(1 for _, st, _ in checks if st == s))
              for s in (True, False)}
    out = {"spot_check": {"decided_yes_calls": len(checks),
                          "agreement_screen_found": pooled[True], "agreement_adjudicator_only": pooled[False]},
           "kinds": {}}
    for k in SCORE_KINDS:
        base = "animal_model_pharmacology" if k == "animal_model_pharmacology_other" else k
        t = a[a["true_" + k]]
        studies = list(zip(t.ensembl_id, t.mondo_id, t.record_id))
        if not studies:
            continue
        screen_found = np.array([(e, m, r, k) in found_by for e, m, r in studies])
        post = {}
        for st in (True, False):
            agree, n = pooled[st]
            prior = (agree + 1) / (n + 2)
            ka = sum(v == "agree" for kk, s2, v in checks if kk == base and s2 == st)
            kn = sum(1 for kk, s2, _ in checks if kk == base and s2 == st)
            post[st] = (LENIENCY_PRIOR * prior + ka, LENIENCY_PRIOR * (1 - prior) + kn - ka)
        res = {}
        for arm in ("union", "yardstick"):
            arm_pairs = {(e, m) for e, m, _, kk in pos[arm] if kk == k}
            cov, prec = [], []
            for _ in range(LENIENCY_DRAWS):
                p_found, p_only = rng.beta(*post[True]), rng.beta(*post[False])
                keep = rng.random(len(studies)) < np.where(screen_found, p_found, p_only)
                real = [s for s, kp in zip(studies, keep) if kp]
                true_pairs = {(e, m) for e, m, _ in real}
                if true_pairs:
                    cov.append(len(true_pairs & arm_pairs) / len(true_pairs))
                if arm_pairs:
                    prec.append(len(true_pairs & arm_pairs) / len(arm_pairs))
            q = lambda x: [float(np.median(x)), *map(float, np.percentile(x, [2.5, 97.5]))] if x else None  # noqa: E731
            res[arm] = {"coverage_pair": q(cov), "precision_pair": q(prec)}
        out["kinds"][k] = res
    return out


def resolve_score(args) -> None:
    """resolve_metrics for the screen version --version (default: each record's latest)."""
    out = resolve_metrics(args.version, args.adjudication)
    if args.leniency:
        out["leniency"] = leniency(adjudicated(args.adjudication), arm_positives(args.version))
    print(json.dumps(out, indent=1, default=float))


# --- cost ----------------------------------------------------------------------------------------------------------

# US dollars per million tokens (input, output, cache write, cache read) and per web search
PRICES = {"claude-sonnet-5": (2.0, 10.0, 2.50, 0.20), "claude-haiku-4-5-20251001": (1.0, 5.0, 1.25, 0.10),
          "claude-opus-5-5": (4.0, 20.0, 5.00, 0.20)}
WEB_SEARCH_USD = 0.01
BATCH_DISCOUNT = 0.5


def task_usd(task: str, model: str, batched: bool, u: dict | None) -> float:
    """One decision's cost at list prices: tokens by model, the Batch API discount on batched runs (not the
    reference, the web arm or the yardstick, which run direct with web search), and each web search."""
    u = u or {}
    pi, po, pw, pr = PRICES.get(model, PRICES["claude-opus-5-5"])
    usd = (u.get("input_tokens", 0) * pi + u.get("output_tokens", 0) * po
           + u.get("cache_creation_input_tokens", 0) * pw + u.get("cache_read_input_tokens", 0) * pr) / 1e6
    usd *= BATCH_DISCOUNT if batched and not any(t in task for t in ("reference", "_web", "yardstick")) else 1
    return usd + (u.get("web_search_requests", 0) or 0) * WEB_SEARCH_USD


def decision_costs(since: str | None = None) -> dict[str, float]:
    """Task -> USD of every new (not reused) target-literature decision, made after since when given."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT d.task, r.model, coalesce(r.parameters->>'n_items', '0')::int > %s AS batched, d.usage
                       FROM pv_evidence.llm_decision d JOIN pv_evidence.llm_decision_run r USING (decision_run_id)
                       WHERE d.task LIKE 'target_literature%%' AND d.prior_decision_id IS NULL
                         AND d.created_at >= coalesce(%s::timestamptz, '-infinity')""", (llm.DIRECT_MAX, since))
        rows = cur.fetchall()
    out: dict[str, float] = {}
    for task, model, batched, u in rows:
        out[task] = out.get(task, 0.0) + task_usd(task, model, batched, u)
    return out


def spend(since: str) -> float:
    return sum(decision_costs(since).values())


def cost(args) -> None:
    """The token cost by task (of decisions made after --since when given), and its extrapolation per pair."""
    by = decision_costs(args.since)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM preclin.target_disease")
        all_pairs = cur.fetchone()[0]
    n_pilot, n_cohort = len(pilot_pairs()), len(cohort_pairs())
    run_tasks = [t for t in by if "_check" not in t and "reference" not in t]
    per_pair = sum(by[t] for t in run_tasks) / n_pilot
    print(json.dumps({"since": args.since, "usd_by_task": {k: round(v, 2) for k, v in sorted(by.items())},
                      "usd_total": round(sum(by.values()), 2), "pilot_pairs": n_pilot,
                      "run_usd_per_pilot_pair": round(per_pair, 3), "cohort_pairs": n_cohort,
                      "all_pairs": all_pairs}, indent=2))


# Records the screen model and its fallback both refused (their safety classifiers): no reading exists for them.
REFUSED = """SELECT DISTINCT d.subject_key FROM pv_evidence.llm_decision d
             WHERE d.task = 'target_literature_screen_fallback' AND d.validation_detail::text LIKE '%%refusal%%'
               AND NOT EXISTS (SELECT 1 FROM pv_evidence.llm_decision v WHERE v.subject_key = d.subject_key
                               AND v.task IN ('target_literature_screen', 'target_literature_screen_fallback')
                               AND v.validation_status = 'validated')"""
# Every retrieved (pair, record) of the run's pairs, with whether its text is stored anywhere and its year: a temp
# table built once, so the checks below are joins rather than per-row lookups.
RETRIEVED = """
    CREATE TEMP TABLE retrieved ON COMMIT DROP AS
    WITH ret AS (SELECT DISTINCT h.ensembl_id, h.mondo_id, h.record_id FROM preclin.target_literature_hit h
                 JOIN want USING (ensembl_id, mondo_id, cutoff_year)),
         ids AS (SELECT DISTINCT record_id FROM ret),
         origin AS (SELECT regexp_replace(o.record_id, '^PMID:', '') AS record_id, min(o.year) AS year
                    FROM preclin.target_disease_source o
                    JOIN ids ON ids.record_id = regexp_replace(o.record_id, '^PMID:', '') GROUP BY 1),
         txt AS (SELECT ids.record_id, (p.pmid IS NOT NULL OR r.record_id IS NOT NULL OR o.record_id IS NOT NULL) AS has_text,
                        coalesce(p.year, r.year, o.year) AS year
                 FROM ids LEFT JOIN public.publications p ON p.pmid = ids.record_id
                 LEFT JOIN preclin.literature_record r ON r.record_id = ids.record_id
                 LEFT JOIN origin o ON o.record_id = ids.record_id)
    SELECT ret.*, txt.has_text, txt.year FROM ret JOIN txt USING (record_id)"""
INTEGRITY = {
    "cohort pairs missing a pubmed, europepmc or per-kind firecrawl search at their cutoff": """
        SELECT count(*) FROM want w LEFT JOIN (
            SELECT ensembl_id, mondo_id, cutoff_year FROM preclin.target_literature_search GROUP BY 1, 2, 3
            HAVING count(*) FILTER (WHERE source = 'pubmed') = 1 AND count(*) FILTER (WHERE source = 'europepmc') = 1
               AND count(DISTINCT kind) FILTER (WHERE source = 'firecrawl') = 7) s USING (ensembl_id, mondo_id, cutoff_year)
        WHERE s.ensembl_id IS NULL""",
    "pairs with a qualifying record but no related-paper search": """
        SELECT count(*) FROM want w
        WHERE EXISTS (SELECT 1 FROM preclin.target_literature_screen s
                      WHERE (s.ensembl_id, s.mondo_id) = (w.ensembl_id, w.mondo_id) AND s.original_data
                        AND s.disease_match = 'same_or_subtype'
                        AND (s.human_cell_perturbation OR s.cell_line_perturbation OR s.diseased_tissue_protein
                             OR s.animal_model_pharmacology OR s.mouse_genetic_disease_model
                             OR s.observational_biomarker OR s.clinical_observation))
          AND NOT EXISTS (SELECT 1 FROM preclin.target_literature_search s WHERE s.source = 'firecrawl_related'
                          AND (s.ensembl_id, s.mondo_id, s.cutoff_year) = (w.ensembl_id, w.mondo_id, w.cutoff_year))""",
    "retrieved records with stored text but no screen row, no prefilter-out row and no refusal by both models": f"""
        SELECT count(*) FROM retrieved r
        LEFT JOIN preclin.target_literature_screen s USING (ensembl_id, mondo_id, record_id)
        LEFT JOIN preclin.target_literature_prefilter f USING (ensembl_id, mondo_id, record_id)
        LEFT JOIN ({REFUSED}) x ON x.subject_key = r.ensembl_id || '|' || r.mondo_id || '|' || r.record_id
        WHERE r.has_text AND s.record_id IS NULL AND (f.record_id IS NULL OR f.possibly) AND x.subject_key IS NULL""",
    "screen or prefilter rows of a pair for a record no search of the pair returns, at any cutoff": """
        SELECT (SELECT count(*) FROM preclin.target_literature_screen s
                JOIN (SELECT DISTINCT ensembl_id, mondo_id FROM want) w USING (ensembl_id, mondo_id)
                WHERE NOT EXISTS (SELECT 1 FROM preclin.target_literature_hit h
                                  WHERE (h.ensembl_id, h.mondo_id, h.record_id) = (s.ensembl_id, s.mondo_id, s.record_id)))
             + (SELECT count(*) FROM preclin.target_literature_prefilter f
                JOIN (SELECT DISTINCT ensembl_id, mondo_id FROM want) w USING (ensembl_id, mondo_id)
                WHERE NOT EXISTS (SELECT 1 FROM preclin.target_literature_hit h
                                  WHERE (h.ensembl_id, h.mondo_id, h.record_id) = (f.ensembl_id, f.mondo_id, f.record_id)))""",
    "hits without their search row": """
        SELECT count(*) FROM preclin.target_literature_hit h LEFT JOIN preclin.target_literature_search s
            ON (s.ensembl_id, s.mondo_id, s.cutoff_year, s.source, s.kind) = (h.ensembl_id, h.mondo_id, h.cutoff_year, h.source,
                CASE WHEN h.source = 'firecrawl' AND h.kind = '' THEN s.kind ELSE h.kind END)
        WHERE s.ensembl_id IS NULL""",

    "screen rows whose decision is not a validated screen (or its fallback) of that pair, record and version": """
        SELECT count(*) FROM preclin.target_literature_screen s LEFT JOIN pv_evidence.llm_decision d
            ON d.llm_decision_id = s.llm_decision_id
        LEFT JOIN pv_evidence.llm_decision_run r ON r.decision_run_id = d.decision_run_id
        WHERE d.llm_decision_id IS NULL OR d.task NOT IN ('target_literature_screen', 'target_literature_screen_fallback')
           OR r.prompt_version <> s.screen_version
           OR d.validation_status <> 'validated'
           OR d.subject_key <> s.ensembl_id || '|' || s.mondo_id || '|' || s.record_id""",
    "prefilter rows whose decision is not a validated prefilter of that pair and record": """
        SELECT count(*) FROM preclin.target_literature_prefilter f LEFT JOIN pv_evidence.llm_decision d
            ON d.llm_decision_id = f.llm_decision_id
        WHERE d.llm_decision_id IS NULL OR d.task <> 'target_literature_prefilter' OR d.validation_status <> 'validated'
           OR d.subject_key <> f.ensembl_id || '|' || f.mondo_id || '|' || f.record_id""",
    "prefilter rows of a pair at or below the prefilter threshold": f"""
        SELECT count(*) FROM preclin.target_literature_prefilter f
        JOIN (SELECT ensembl_id, mondo_id, count(*) n FROM retrieved GROUP BY 1, 2) c USING (ensembl_id, mondo_id)
        WHERE c.n <= {PREFILTER_ABOVE}""",
    "cohort pairs without a web-arm search row (answered or refused by both models)": """
        SELECT count(*) FROM want w WHERE NOT EXISTS (SELECT 1 FROM preclin.target_literature_search s
            WHERE s.source = 'web_agent' AND (s.ensembl_id, s.mondo_id, s.cutoff_year) = (w.ensembl_id, w.mondo_id, w.cutoff_year))""",
    "verified web-arm studies without their web_agent hit": """
        SELECT count(*) FROM preclin.target_literature_web_study w WHERE w.arm = 'web' AND w.record_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM preclin.target_literature_hit h WHERE h.source = 'web_agent'
                          AND (h.ensembl_id, h.mondo_id, h.record_id) = (w.ensembl_id, w.mondo_id, w.record_id))""",
    "web_agent hits without a verified web-arm study": """
        SELECT count(*) FROM preclin.target_literature_hit h WHERE h.source = 'web_agent'
          AND NOT EXISTS (SELECT 1 FROM preclin.target_literature_web_study w WHERE w.arm = 'web'
                          AND (h.ensembl_id, h.mondo_id, h.record_id) = (w.ensembl_id, w.mondo_id, w.record_id))""",
}
INFO = {
    "screen rows for records returned only by a search at another cutoff of the pair (kept; the read-time cutoff applies)": """
        SELECT count(*) FROM preclin.target_literature_screen s
        JOIN (SELECT DISTINCT ensembl_id, mondo_id FROM want) w USING (ensembl_id, mondo_id)
        LEFT JOIN retrieved r USING (ensembl_id, mondo_id, record_id)
        WHERE r.record_id IS NULL AND EXISTS (SELECT 1 FROM preclin.target_literature_hit h
              WHERE (h.ensembl_id, h.mondo_id, h.record_id) = (s.ensembl_id, s.mondo_id, s.record_id))""",
    "search rows of cohort pairs at an earlier cutoff (kept; linked to the current one)": """
        SELECT count(*) FROM preclin.target_literature_search s JOIN want w USING (ensembl_id, mondo_id)
        WHERE s.cutoff_year <> w.cutoff_year""",
    "pairs with search rows that are not in the cohort (left it; rows kept)": """
        SELECT count(DISTINCT (ensembl_id, mondo_id)) FROM preclin.target_literature_search s
        WHERE NOT EXISTS (SELECT 1 FROM want w WHERE (w.ensembl_id, w.mondo_id) = (s.ensembl_id, s.mondo_id))""",
    "web-arm studies by verification": """SELECT json_object_agg(verification, n) FROM (SELECT verification, count(*) n
                                          FROM preclin.target_literature_web_study WHERE arm = 'web' GROUP BY 1) x""",
    "yardstick studies by verification": """SELECT json_object_agg(verification, n) FROM (SELECT verification, count(*) n
                                            FROM preclin.target_literature_web_study WHERE arm = 'yardstick' GROUP BY 1) x""",
    "retrieved records without stored text (never screened)": "SELECT count(DISTINCT record_id) FROM retrieved WHERE NOT has_text",
    "retrieved (pair, record)": "SELECT count(*) FROM retrieved",
    "records refused by both the screen and fallback models (unread)": f"SELECT count(*) FROM ({REFUSED}) x",
    "retrieved (pair, record) by source": """SELECT json_object_agg(source, n) FROM (SELECT source, count(DISTINCT (ensembl_id, mondo_id, record_id)) n
                                   FROM preclin.target_literature_hit JOIN want USING (ensembl_id, mondo_id, cutoff_year) GROUP BY 1) x""",
    "retrieved (pair, record) only from the origin search": """SELECT count(*) FROM (SELECT ensembl_id, mondo_id, record_id
                                   FROM preclin.target_literature_hit JOIN want USING (ensembl_id, mondo_id, cutoff_year)
                                   GROUP BY 1, 2, 3 HAVING bool_and(source LIKE 'origin%%')) x""",
    "screen rows": "SELECT count(*) FROM preclin.target_literature_screen",
    "prefilter rows (possibly / not)": """SELECT count(*) FILTER (WHERE possibly) || ' / ' || count(*) FILTER (WHERE NOT possibly)
                                          FROM preclin.target_literature_prefilter""",
    "search rows": "SELECT count(*) FROM preclin.target_literature_search",
    "hit rows": "SELECT count(*) FROM preclin.target_literature_hit",
    "retrieved records with no publication year": "SELECT count(DISTINCT record_id) FROM retrieved WHERE year IS NULL",
}


def integrity(args) -> None:
    """Every check in INTEGRITY must be 0 for the run to be complete; INFO gives the counts the run record reconciles."""
    p = pairs_of(args.pairs)
    out = {"checks": {}, "counts": {}}
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE want (ensembl_id text, mondo_id text, cutoff_year int) ON COMMIT DROP")
        execute_values(cur, "INSERT INTO want VALUES %s", [(r.ensembl_id, r.mondo_id, int(r.cutoff_year)) for r in p.itertuples()])
        cur.execute("CREATE INDEX ON want (ensembl_id, mondo_id, cutoff_year)")
        cur.execute(RETRIEVED)
        cur.execute("CREATE INDEX ON retrieved (ensembl_id, mondo_id, record_id)")
        cur.execute("ANALYZE want")
        cur.execute("ANALYZE retrieved")
        for name, sql in INTEGRITY.items():
            cur.execute(sql)
            out["checks"][name] = cur.fetchone()[0]
        for name, sql in INFO.items():
            cur.execute(sql)
            out["counts"][name] = cur.fetchone()[0]
    out["passes"] = all(v == 0 for v in out["checks"].values())
    print(json.dumps(out, indent=2, default=str))


def summary(args) -> None:
    """Per kind: cohort pairs with any qualifying record, and pairs with one dated by the year before a 2008-2019
    entry of a program on the pair (from preclin.target_literature_evidence)."""
    p = pairs_of(args.pairs)
    want = set(zip(p.ensembl_id, p.mondo_id))
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT ensembl_id, mondo_id, kind, record_years, first_year_other_agent, program_drug_only
                       FROM preclin.target_literature_evidence""")
        ev = [r for r in cur.fetchall() if (r[0], r[1]) in want]
    entries = cohort_entries()
    last = entries.groupby(["ensembl_id", "mondo_id"]).entry_year.max().to_dict()
    first = entries.groupby(["ensembl_id", "mondo_id"]).entry_year.min().to_dict()
    out = {}
    for kind in KINDS:
        rows = [r for r in ev if r[2] == kind]
        years = {(r[0], r[1]): [y for y in r[3] if y is not None] for r in rows}
        out[kind] = {"pairs_with_any": len(rows),
                     "pairs_with_one_before_latest_entry": sum(any(y <= last[k] - 1 for y in v) for k, v in years.items()),
                     "pairs_with_one_before_first_entry": sum(any(y <= first[k] - 1 for y in v) for k, v in years.items())}
        if kind == "animal_model_pharmacology":
            out[kind]["pairs_with_other_agent"] = sum(r[5] is False for r in rows)
            out[kind]["pairs_with_other_agent_before_latest_entry"] = sum(
                r[4] is not None and r[4] <= last[(r[0], r[1])] - 1 for r in rows)
    print(json.dumps({"pairs": len(p), "kinds": out}, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in [("names", names), ("search", search), ("screen", screen), ("check", check),
                     ("prefilter-check", prefilter_check), ("cost", cost), ("integrity", integrity),
                     ("summary", summary), ("firecrawl", firecrawl), ("origin", origin), ("web", web),
                     ("web-screen", web_screen), ("yardstick", yardstick), ("web-score", web_score),
                     ("reconcile", reconcile), ("adjudicate", adjudicate), ("resolve-score", resolve_score)]:
        c = sub.add_parser(name)
        c.add_argument("--pairs", choices=["pilot", "cohort", "new", "confirm", "confirm-new", "yardstick"], default="pilot")
        c.set_defaults(fn=fn)
        if name == "firecrawl":
            c.add_argument("--mode", choices=["search", "related"], required=True)
        if name == "screen":
            c.add_argument("--follow", action="store_true", help="keep screening pairs as their searches finish")
            c.add_argument("--skip-done", action="store_true", help="skip pairs whose every record is already decided")
        if name == "web-screen":
            c.add_argument("--sources", default="web_agent", help="comma-separated hit sources to screen, or all")
        if name in ("search", "screen", "web", "web-screen", "adjudicate", "reconcile"):
            c.add_argument("--shard", help="i/n: this process's share of the pairs, to run n in parallel")
        if name == "adjudicate":
            c.add_argument("--rubric", choices=["v1", "v2"], default="v1",
                           help="v2 re-reads the v1 YES calls of REVISED_KINDS under the tightened rubric, adding rows")
        if name == "resolve-score":
            c.add_argument("--version", help="score this screen version, or final (each kind's kept version; "
                                             "default: each record's latest)")
            c.add_argument("--adjudication", help="the confirmed set as of this rubric version (default: latest)")
            c.add_argument("--leniency", action="store_true", help="also correct for the adjudicator's leniency")
        if name in ("screen", "cost"):
            c.add_argument("--since", help="count spend from this timestamp (the full run's start)")
        if name in ("screen", "web-screen"):
            c.add_argument("--screen-version", choices=["v2", "v3", "v4"], help="store readings of this screen version")
    args = ap.parse_args()
    if getattr(args, "screen_version", None):
        global SCREEN_VERSION
        SCREEN_VERSION = args.screen_version
    # Every command resumes where it stopped (stored searches, decisions and rows are reused), so a dropped database
    # link, a network outage or a source that is down reruns the command after a backoff instead of ending it.
    for attempt in range(NETWORK_RETRIES):
        try:
            args.fn(args)
            return
        except (psycopg2.OperationalError, psycopg2.InterfaceError, FirecrawlError, SourceDown, OSError) as e:
            wait = min(60 * 2 ** attempt, 1800)
            print(f"{args.cmd}: {type(e).__name__}: {str(e)[:200]}; rerunning in {wait} s "
                  f"({attempt + 1}/{NETWORK_RETRIES})", flush=True)
            time.sleep(wait)
    args.fn(args)


if __name__ == "__main__":
    main()
