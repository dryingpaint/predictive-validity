"""PubMed evidence about the drug itself, as known the year before a phase entry.

    python -m pipeline.literature search [--entries pilot|cohort]    # one PubMed search per drug, by its names
    python -m pipeline.literature screen [--entries pilot|cohort]    # LLM: what each abstract reports about the drug
    python -m pipeline.literature diseases                          # LLM: MONDO term of each modelled disease
    python -m pipeline.literature check                             # second model on a seeded pilot sample
    python -m pipeline.literature gate --reference PREFIX --rows A-B [--label NAME]   # pilot against a blind reference

Three kinds of evidence: animal_disease (the drug tested for efficacy in an animal model of the program disease,
a subtype or a disease within Lin 0.5 of it), animal_healthy (the drug's pharmacokinetics, pharmacodynamics or
exposure in healthy animals) and human_engagement (target engagement or a pharmacodynamic biomarker measured in
people; Phase 2 and 3 entries only).

Each drug is searched once, in PubMed titles and abstracts, by its names alone: INN, code names, ChEMBL and
PubChem synonyms, and FDA substance-registry names, with no disease, species or kind terms. The search runs
to the latest cutoff of the drug's entries (the year before entry), excludes reviews and keeps up to HITS results
in relevance order; an entry counts only abstracts published by its own cutoff. An LLM reads each abstract once
and decides every kind, naming the diseases any animal model models; a second LLM step maps each modelled disease
to MONDO among retrieved candidates, as pipeline.indications maps trial conditions.

The entries are the US-sited phase entries of 2008-2019 (cohort) or a seeded sample of 300 of them (pilot,
report/audits/literature_pilot_sample.csv). This is the second version, fixed in report/translation_plan.md
before it ran; version 1 searched by drug, disease and kind terms, and its rows stay in preclin.literature_search,
literature_hit and literature_screen. A kind runs on the cohort only once the pilot passes the plan's gates.
"""
from __future__ import annotations

import argparse
import json
import os
import re
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
HITS = 200  # abstracts kept per drug, PubMed relevance order
MAX_DRUG_NAMES = 50
MAX_NAME_CHARS = 30
MAX_NAME_WORDS = 4
CIDS_PER_CALL = 100
PUBCHEM_SYNONYMS = 20  # PubChem lists the most used synonyms first; vendor catalogue codes follow
CHECK_PER_KIND = 50  # half screened in, half screened out, per kind
CHECK_SEED = 20261104
RELATED = 0.5  # Lin similarity within which a modelled disease counts for the entry's disease
GATES = {"recall": 0.80, "kappa": 0.60, "phase2_coverage": 0.08}
METHOD = "literature_evidence@v2"
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


def query(names: list[str], cutoff: int) -> str:
    return (f'({" OR ".join(f"{chr(34)}{n}{chr(34)}[tiab]" for n in names)}) AND ("1900"[dp] : "{cutoff}"[dp]) '
            f"{NOT_REVIEWS}")


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


def names_of(cur, moieties: list[int]) -> dict[int, list[str]]:
    cur.execute("""SELECT m.moiety_id, m.name, m.code_names, u.pubchem_cid,
                          coalesce(array_agg(DISTINCT n.name) FILTER (WHERE n.name IS NOT NULL), '{}'),
                          coalesce(array_agg(DISTINCT cm.parent_chembl_id) FILTER (WHERE cm.parent_chembl_id IS NOT NULL), '{}')
                   FROM preclin.moiety m
                   LEFT JOIN preclin.unii_substance u ON u.unii = m.unii
                   LEFT JOIN preclin.unii_name n ON n.unii = m.unii AND n.name_type IN ('cn', 'cd', 'of')
                   LEFT JOIN preclin.chembl_moiety cm ON cm.moiety_id = m.moiety_id
                   WHERE m.moiety_id = ANY(%s) GROUP BY 1, 2, 3, 4""", (moieties,))
    rows = cur.fetchall()
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


def search(args) -> None:
    """Run each drug search the entries need that has not been run; store its hits and their abstracts."""
    cut = drug_cutoffs(entries(args.entries))
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, METHOD, "PubMed evidence about the drug before phase entry (version 2)", __doc__,
                          ["PubMed", "PubChem", "ChEMBL", "preclin.moiety", "preclin.unii_name", "preclin.ontology_term"],
                          {"hits": HITS, "max_names": MAX_DRUG_NAMES, "exclude": NOT_REVIEWS, "related_lin": RELATED})
        cur.execute("SELECT moiety_id, cutoff_year FROM preclin.literature_drug_search")
        done = set(cur.fetchall())
        todo = sorted((m, y) for m, y in cut.items() if (m, y) not in done)
        names = names_of(cur, [m for m, _ in todo])
        conn.commit()
    todo = [(m, y) for m, y in todo if names.get(m)]
    print(f"drugs={len(cut)} to search={len(todo)}", flush=True)
    for start in range(0, len(todo), 25):
        found = []
        for m, y in todo[start:start + 25]:
            q = query(names[m], y)
            root = ET.fromstring(eutils("esearch", term=q, retmax=str(HITS), sort="relevance"))
            found.append((m, y, names[m], q, int(root.findtext("Count") or 0), [x.text for x in root.iter("Id")]))
        pmids = sorted({p for *_, ids in found for p in ids})
        with llm.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT pmid FROM public.publications WHERE pmid = ANY(%s)", (pmids,))
            have = {r[0] for r in cur.fetchall()}
            papers = efetch([p for p in pmids if p not in have])
            if papers:
                execute_values(cur, """INSERT INTO public.publications (pmid, title, authors, journal, year, doi, abstract)
                                       VALUES %s ON CONFLICT (pmid) DO NOTHING""", papers)
            stored = have | {p[0] for p in papers}
            execute_values(cur, """INSERT INTO preclin.literature_drug_search (moiety_id, cutoff_year, names, query, n_hits)
                                   VALUES %s ON CONFLICT (moiety_id, cutoff_year) DO NOTHING""",
                           [(m, y, n, q, c) for m, y, n, q, c, _ in found])
            hits = [(m, y, p, rank) for m, y, _, _, _, ids in found for rank, p in enumerate(ids, 1) if p in stored]
            if hits:
                execute_values(cur, """INSERT INTO preclin.literature_drug_hit (moiety_id, cutoff_year, pmid, rank)
                                       VALUES %s ON CONFLICT DO NOTHING""", hits)
            conn.commit()
        print(f"searched {start + len(found)}/{len(todo)} new papers={len(papers)}", flush=True)


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


def screen_items(e: pd.DataFrame) -> dict[str, dict]:
    """Subject key (entity|pmid) -> payload, for every hit of the entries' drug searches."""
    cut = drug_cutoffs(e)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT moiety_id, names FROM preclin.literature_drug_search WHERE moiety_id = ANY(%s)", (sorted(cut),))
        names = {m: n for m, n in cur.fetchall()}
        cur.execute("""SELECT mt.moiety_id, string_agg(DISTINCT t.symbol || ' (' || mt.action || ')', ', ')
                       FROM preclin.moiety_target mt JOIN public.targets t ON t.id = mt.target_id
                       WHERE mt.is_primary AND mt.moiety_id = ANY(%s) GROUP BY 1""", (sorted(cut),))
        targets = dict(cur.fetchall())
        cur.execute("CREATE TEMP TABLE want (moiety_id int, cutoff_year int) ON COMMIT DROP")
        execute_values(cur, "INSERT INTO want VALUES %s", list(cut.items()))
        cur.execute("""SELECT h.moiety_id, h.pmid, p.title, p.abstract, p.year FROM preclin.literature_drug_hit h
                       JOIN want USING (moiety_id, cutoff_year) JOIN public.publications p USING (pmid)""")
        rows = cur.fetchall()
    return {f"{m}|{pmid}": {"drug_names": names[m], "targets": targets.get(m, ""), "pmid": pmid, "title": title or "",
                            "abstract": abstract, "year": year} for m, pmid, title, abstract, year in rows}


def screen(args) -> None:
    """Screen every hit of the entries' drug searches; an earlier decision on the same input is reused."""
    items = screen_items(entries(args.entries))
    run_id = llm.run(task(), items)
    decided = [x for x in llm.decisions(run_id) if x[2] and "error" not in x[2]]
    rows = [(int(k.split("|")[0]), k.split("|")[1], o["original_data"], o["animal_disease"], o["modelled_diseases"],
             o["animal_healthy"], o["human_engagement"], o["species"] or None, o["detail"] or None, o["quote"] or None, did)
            for k, did, o in decided]
    with llm.connect() as conn, conn.cursor() as cur:
        execute_values(cur, """INSERT INTO preclin.literature_drug_screen (moiety_id, pmid, original_data, animal_disease,
                                 modelled_diseases, animal_healthy, human_engagement, species, detail, quote, llm_decision_id)
                               VALUES %s ON CONFLICT (moiety_id, pmid) DO UPDATE SET
                                 original_data = EXCLUDED.original_data, animal_disease = EXCLUDED.animal_disease,
                                 modelled_diseases = EXCLUDED.modelled_diseases, animal_healthy = EXCLUDED.animal_healthy,
                                 human_engagement = EXCLUDED.human_engagement, species = EXCLUDED.species,
                                 detail = EXCLUDED.detail, quote = EXCLUDED.quote,
                                 llm_decision_id = EXCLUDED.llm_decision_id""", rows, page_size=5000)
        conn.commit()
    print(f"abstracts={len(items)} decided={len(decided)} run={run_id}", flush=True)


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
        cur.execute("""SELECT DISTINCT d FROM preclin.literature_drug_screen, unnest(modelled_diseases) d
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
    """A second model relabels, per kind, a seeded CHECK_PER_KIND pilot abstracts: half that the screen put in
    that kind, half that it left out (fewer when a side has fewer)."""
    items = screen_items(pilot_entries())
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT moiety_id || '|' || pmid, animal_disease, animal_healthy, human_engagement
                       FROM preclin.literature_drug_screen""")
        verdict = {k: dict(zip(KINDS, v)) for k, *v in cur.fetchall()}
    rng = np.random.default_rng(CHECK_SEED)
    keys = sorted(k for k in items if k in verdict)
    picked: set[str] = set()
    for kind in KINDS:
        for side in (True, False):
            pool = [k for k in keys if verdict[k][kind] is side]
            picked |= {pool[i] for i in rng.choice(len(pool), min(CHECK_PER_KIND // 2, len(pool)), replace=False)}
    run_id = llm.run(task(model="claude-opus-5-5", suffix="_check"), {k: items[k] for k in sorted(picked)})
    print(f"check sample={len(picked)} decided={len(llm.decisions(run_id))} run={run_id}", flush=True)


def kappa(a: list[bool], b: list[bool]) -> float | None:
    a, b = np.array(a, bool), np.array(b, bool)
    if not len(a):
        return None
    po = float((a == b).mean())
    pe = float(a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean()))
    return None if pe == 1 else (po - pe) / (1 - pe)


def agreement() -> dict[str, dict]:
    """Kind -> agreement of the screen with the check model on the check sample, and the sample's make-up."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT ON (subject_key, task) subject_key, task, parsed_output
                       FROM pv_evidence.llm_decision
                       WHERE task IN ('literature_drug_screen', 'literature_drug_screen_check')
                         AND validation_status = 'validated'
                       ORDER BY subject_key, task, created_at DESC""")
        by: dict = {}
        for key, tname, out_ in cur.fetchall():
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


def qualifying() -> pd.DataFrame:
    """Entity, PMID, publication year, kind and (for animal models) mapped MONDO term of every qualifying screen."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT s.moiety_id, s.pmid, p.year, 'animal_disease', md.mondo_id
                       FROM preclin.literature_drug_screen s JOIN public.publications p USING (pmid)
                       CROSS JOIN unnest(s.modelled_diseases) d
                       JOIN preclin.literature_model_disease md ON md.modelled_disease = d
                       WHERE s.animal_disease AND md.mondo_id IS NOT NULL
                       UNION ALL
                       SELECT s.moiety_id, s.pmid, p.year, k.kind, NULL
                       FROM preclin.literature_drug_screen s JOIN public.publications p USING (pmid)
                       CROSS JOIN LATERAL (VALUES ('animal_healthy', s.animal_healthy),
                                                  ('human_engagement', s.human_engagement)) k(kind, ok)
                       WHERE k.ok""")
        return pd.DataFrame(cur.fetchall(), columns=["moiety_id", "pmid", "year", "kind", "mondo_id"])


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
                         "pmid": str(s["pmid"]) if s.get("pmid") else None, "venue": s.get("venue")})
    return pd.DataFrame(rows, columns=["moiety_id", "mondo_id", "phase", "kind", "pmid", "venue"])


def misses(rk: pd.DataFrame, related) -> dict[str, int]:
    """Why each PubMed-indexed reference study of one kind was or was not found: found; screened in but
    its modelled disease mapped outside the entry's (animal_disease); screened out; kept but not screened;
    matched by the drug search but ranked below the HITS kept; or not matched by it."""
    out: dict[str, int] = {}
    with llm.connect() as conn, conn.cursor() as cur:
        for r in rk.dropna(subset=["pmid"]).itertuples():
            cur.execute("""SELECT s.query, h.pmid IS NOT NULL, c.animal_disease, c.animal_healthy, c.human_engagement,
                                  (SELECT array_agg(md.mondo_id) FROM unnest(c.modelled_diseases) d
                                   JOIN preclin.literature_model_disease md ON md.modelled_disease = d)
                           FROM preclin.literature_drug_search s
                           LEFT JOIN preclin.literature_drug_hit h ON h.moiety_id = s.moiety_id
                                AND h.cutoff_year = s.cutoff_year AND h.pmid = %s
                           LEFT JOIN preclin.literature_drug_screen c ON c.moiety_id = s.moiety_id AND c.pmid = %s
                           WHERE s.moiety_id = %s""", (r.pmid, r.pmid, int(r.moiety_id)))
            row = cur.fetchone()
            if row is None:
                why = "not_searched"
            elif row[1]:
                verdict = dict(zip(KINDS, row[2:5]))
                if verdict[r.kind] is None:
                    why = "unscreened"
                elif not verdict[r.kind]:
                    why = "screened_out"
                elif r.kind == "animal_disease" and not set(row[5] or []) & related(r.mondo_id):
                    why = "screened_in_other_disease"
                else:
                    why = "found"
            else:
                root = ET.fromstring(eutils("esearch", term=f"({row[0]}) AND {r.pmid}[uid]", retmax="0"))
                why = "ranked_below_kept" if int(root.findtext("Count") or 0) else "not_matched_by_query"
            out[why] = out.get(why, 0) + 1
    return out


def evaluate(e: pd.DataFrame, ref: list[dict], f: pd.DataFrame, agree: dict, related) -> dict:
    """Recall, agreement and coverage of one set of pilot entries against its blind reference."""
    rr = reference_rows(ref, e)
    keys = ["moiety_id", "mondo_id", "phase"]
    on_ref = f.merge(e[keys], on=keys)
    result: dict = {"reference_entries": len(ref), "kinds": {}}
    for kind in KINDS:
        got = {(r.moiety_id, r.mondo_id, r.phase): set(r.pmids) for r in on_ref[on_ref.kind == kind].itertuples()}
        rk = rr[rr.kind == kind]
        hit = [p is not None and p in got.get((m, d, ph), set())
               for m, d, ph, p in zip(rk.moiety_id, rk.mondo_id, rk.phase, rk.pmid)]
        in_pm = rk.pmid.notna().to_numpy()
        with_ref = set(rk[keys].itertuples(index=False, name=None))
        none_ref = [k for k in got if k not in with_ref]
        entry_recall = [bool(got.get(k)) for k in with_ref]
        recall = float(np.mean(hit)) if hit else None
        result["kinds"][kind] = {
            "reference_studies": len(rk), "reference_studies_in_pubmed": int(in_pm.sum()),
            "reference_studies_by_venue": rk.venue.fillna("unknown").value_counts().to_dict(),
            "recall": recall,
            "recall_pubmed_indexed": float(np.mean(np.array(hit)[in_pm])) if in_pm.any() else None,
            "reference_entries_with_study": len(with_ref), "entries_judged": len(got),
            "entry_recall": float(np.mean(entry_recall)) if entry_recall else None,
            "pipeline_none_when_reference_none": float(np.mean([not got[k] for k in none_ref])) if none_ref else None,
            "pubmed_reference_studies": misses(rk, related), "check": agree.get(kind)}
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
    agree = agreement()
    result = evaluate(rows_e, ref, f, agree, related) | {"rows": args.rows, "reference": args.reference}
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
    g = sub.add_parser("gate")
    g.add_argument("--reference", required=True, help="path prefix of the four reference files, before {1..4}_result.json")
    g.add_argument("--rows", required=True, help="pilot sample rows scored, e.g. 101-200")
    g.add_argument("--label", default="v2", help="key of this evaluation in the gate record")
    g.set_defaults(fn=gate)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
