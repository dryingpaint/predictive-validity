"""PubMed evidence about the drug itself, as known the year before a phase entry.

    python -m pipeline.literature search [--entries pilot|cohort] [--kinds ...]   # PubMed searches and hits
    python -m pipeline.literature screen [--entries pilot|cohort] [--kinds ...]   # LLM: does each abstract report it
    python -m pipeline.literature check                                            # second model on a seeded sample
    python -m pipeline.literature gate --reference DIR                             # pilot against the blind reference

Three kinds of evidence, each searched in titles and abstracts up to the year before entry, reviews excluded:
animal_disease (the drug tested for efficacy in an animal model of the program disease or a subtype),
animal_healthy (the drug's pharmacokinetics, pharmacodynamics or exposure in healthy animals) and
human_engagement (target engagement or a pharmacodynamic biomarker measured in people; Phase 2 and 3
entries only). A drug is searched by its name, code names and FDA substance-registry names; a disease by
its MONDO label, synonyms and direct subtypes. An LLM reads each abstract kept and decides whether it
reports the drug itself in that kind of study. The entries are the US-sited phase entries of 2008-2019
(cohort) or a seeded sample of 300 of them (pilot, report/audits/literature_pilot_sample.csv); a kind is
run on the cohort only once the pilot passes the gates of the plan amendment (report/translation_plan.md).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from psycopg2.extras import execute_values

from pipeline import llm
from pipeline.attribution import NOT_REVIEWS, PHARMACOLOGY_TERMS, efetch
from pipeline.outcomes import eutils

KINDS = ("animal_disease", "animal_healthy", "human_engagement")
PILOT = os.path.join(llm.REPO, "report", "audits", "literature_pilot_sample.csv")
GATE = os.path.join(llm.REPO, "report", "audits", "literature_gate.json")
HITS = 20  # abstracts kept per search, PubMed relevance order
MAX_DRUG_NAMES = 15
MAX_DISEASE_NAMES = 25
CHECK_PER_KIND = 50
CHECK_SEED = 20261104
GATES = {"recall": 0.80, "kappa": 0.60, "phase2_coverage": 0.08}
METHOD = "literature_evidence@v1"

ANIMAL_TERMS = ('(mice[tiab] OR mouse[tiab] OR murine[tiab] OR rat[tiab] OR rats[tiab] OR "in vivo"[tiab] OR '
                'xenograft*[tiab] OR monkey*[tiab] OR primate*[tiab] OR dog[tiab] OR dogs[tiab] OR rabbit*[tiab] OR '
                'pigs[tiab] OR minipig*[tiab] OR "animal model"[tiab] OR "animal models"[tiab])')
EXPOSURE_TERMS = ('(pharmacokinetic*[tiab] OR pharmacodynamic*[tiab] OR bioavailability[tiab] OR exposure[tiab] OR '
                  '"tissue distribution"[tiab] OR "brain penetration"[tiab] OR "blood-brain barrier"[tiab] OR '
                  'occupancy[tiab] OR "target engagement"[tiab] OR biomarker*[tiab])')
HUMAN_TERMS = '(humans[mh] OR patients[tiab] OR volunteers[tiab] OR subjects[tiab])'
ENGAGEMENT_TERMS = f'({PHARMACOLOGY_TERMS} OR biomarker*[tiab] OR "receptor occupancy"[tiab])'


def clean(name: str) -> str:
    return re.sub(r"\s*\[[^\]]*\]$", "", name).replace('"', "").strip()


def drug_names(name: str, codes: list[str], registry: list[str]) -> list[str]:
    """The entity's name, code names and registry names: a name with a digit must have at least five
    letters or digits (ASA, TF2 match unrelated words), any other at least four characters."""
    out: list[str] = []
    for n in map(clean, [name, *codes, *registry]):
        if len(n) < 4 or (re.search(r"\d", n) and len(re.sub(r"\W", "", n)) < 5):
            continue
        if n.lower() not in {o.lower() for o in out}:
            out.append(n)
    return out[:MAX_DRUG_NAMES]


def tiab(names: list[str]) -> str:
    return "(" + " OR ".join(f'"{n}"[tiab]' for n in names) + ")"


def queries(drug: list[str], disease: list[str], cutoff: int) -> dict[str, str]:
    before = f'("1900"[dp] : "{cutoff}"[dp])'
    return {"animal_disease": f"{tiab(drug)} AND {tiab(disease)} AND {ANIMAL_TERMS} AND {before} {NOT_REVIEWS}",
            "animal_healthy": f"{tiab(drug)} AND {ANIMAL_TERMS} AND {EXPOSURE_TERMS} AND {before} {NOT_REVIEWS}",
            "human_engagement": f"{tiab(drug)} AND {ENGAGEMENT_TERMS} AND {HUMAN_TERMS} AND {before} {NOT_REVIEWS}"}


def pilot_entries() -> pd.DataFrame:
    return pd.read_csv(PILOT)[["moiety_id", "mondo_id", "phase", "entry_date", "evidence_cutoff_year", "reference_set"]] \
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


def searches(e: pd.DataFrame, kinds: tuple[str, ...]) -> list[tuple[int, str, str, int]]:
    """(entity, disease or '', kind, cutoff year) of each search the entries need."""
    out = set()
    for r in e.itertuples(index=False):
        for k in kinds:
            if k == "animal_disease":
                out.add((int(r.moiety_id), r.mondo_id, k, int(r.cutoff_year)))
            elif k == "animal_healthy" or r.phase >= 2:
                out.add((int(r.moiety_id), "", k, int(r.cutoff_year)))
    return sorted(out)


def names_of(cur, moieties: list[int], diseases: list[str]) -> tuple[dict, dict]:
    cur.execute("""SELECT m.moiety_id, m.name, m.code_names,
                          coalesce(array_agg(n.name) FILTER (WHERE n.name IS NOT NULL), '{}')
                   FROM preclin.moiety m
                   LEFT JOIN preclin.unii_name n ON n.unii = m.unii AND n.name_type IN ('cn', 'cd', 'of')
                   WHERE m.moiety_id = ANY(%s) GROUP BY 1, 2, 3""", (moieties,))
    drugs = {m: drug_names(n, list(c or []), sorted(r)) for m, n, c, r in cur.fetchall()}
    cur.execute("""SELECT t.term_id, t.label, t.synonyms,
                          coalesce(array_agg(k.label ORDER BY k.label) FILTER (WHERE k.label IS NOT NULL), '{}')
                   FROM preclin.ontology_term t
                   LEFT JOIN preclin.ontology_is_a i ON i.ontology = 'MONDO' AND i.parent_id = t.term_id
                   LEFT JOIN preclin.ontology_term k ON k.term_id = i.child_id AND NOT k.is_obsolete
                   WHERE t.term_id = ANY(%s) GROUP BY 1, 2, 3""", (diseases,))
    dis = {}
    for d, label, syn, kids in cur.fetchall():
        names = [n.replace('"', "") for n in [label, *(syn or []), *kids] if len(n) >= 4]
        dis[d] = {"label": label, "names": list(dict.fromkeys(names))[:MAX_DISEASE_NAMES]}
    return drugs, dis


def search(args) -> None:
    """Run each search the entries need that has not been run; store its hits and their abstracts."""
    kinds = tuple(args.kinds)
    e = entries(args.entries)
    need = searches(e, kinds)
    with llm.connect() as conn, conn.cursor() as cur:
        llm.record_method(cur, METHOD, "PubMed evidence about the drug before phase entry", __doc__,
                          ["PubMed", "preclin.moiety", "preclin.unii_name", "preclin.ontology_term"],
                          {"hits": HITS, "animal_terms": ANIMAL_TERMS, "exposure_terms": EXPOSURE_TERMS,
                           "engagement_terms": ENGAGEMENT_TERMS, "human_terms": HUMAN_TERMS, "exclude": NOT_REVIEWS})
        drugs, dis = names_of(cur, sorted({m for m, *_ in need}), sorted({d for _, d, *_ in need if d}))
        cur.execute("SELECT moiety_id, mondo_id, kind, cutoff_year FROM preclin.literature_search")
        done = set(cur.fetchall())
        conn.commit()
    todo = [s for s in need if s not in done and drugs.get(s[0]) and (not s[1] or s[1] in dis)]
    print(f"searches={len(need)} to run={len(todo)}", flush=True)
    for start in range(0, len(todo), 50):
        chunk = todo[start:start + 50]
        found = []
        for m, d, k, y in chunk:
            q = queries(drugs[m], dis[d]["names"] if d else [], y)[k]
            root = ET.fromstring(eutils("esearch", term=q, retmax=str(HITS), sort="relevance"))
            found.append((m, d, k, y, q, int(root.findtext("Count") or 0), [x.text for x in root.iter("Id")]))
        pmids = sorted({p for *_, ids in found for p in ids})
        with llm.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT pmid FROM public.publications WHERE pmid = ANY(%s)", (pmids,))
            have = {r[0] for r in cur.fetchall()}
            papers = efetch([p for p in pmids if p not in have])
            if papers:
                execute_values(cur, """INSERT INTO public.publications (pmid, title, authors, journal, year, doi, abstract)
                                       VALUES %s ON CONFLICT (pmid) DO NOTHING""", papers)
            stored = have | {p[0] for p in papers}
            execute_values(cur, """INSERT INTO preclin.literature_search
                                     (moiety_id, mondo_id, kind, cutoff_year, query, n_hits) VALUES %s
                                   ON CONFLICT (moiety_id, mondo_id, kind, cutoff_year) DO NOTHING""",
                           [(m, d, k, y, q, n) for m, d, k, y, q, n, _ in found])
            hits = [(m, d, k, y, p, rank) for m, d, k, y, _, _, ids in found
                    for rank, p in enumerate(ids, 1) if p in stored]
            if hits:
                execute_values(cur, """INSERT INTO preclin.literature_hit (moiety_id, mondo_id, kind, cutoff_year, pmid, rank)
                                       VALUES %s ON CONFLICT DO NOTHING""", hits)
            conn.commit()
        print(f"searched {start + len(chunk)}/{len(todo)} new papers={len(papers)}", flush=True)


DISEASE_SYSTEM = """You read one PubMed abstract and decide whether it reports a specific drug tested for efficacy in an animal model of a specific disease.

Answer qualifies = true only when the abstract reports an experiment in which THIS drug (under any of the names given) was given to animals that model THIS disease or one of its subtypes (induced, genetic or xenograft models, in vivo), and an efficacy outcome of the drug was measured. It does not qualify when: the drug is only mentioned or compared; another drug was tested; the work is only in cells or tissue in vitro; the animals do not model this disease; the abstract is a review; or the subjects are people.

Give the species (empty if none), the model in a few words in `detail` (empty if none), and the sentence that decides it in `quote` (empty if none). Judge only from the abstract."""
DISEASE_SCHEMA = {"type": "object", "additionalProperties": False,
                  "properties": {"qualifies": {"type": "boolean"}, "species": {"type": "string"},
                                 "detail": {"type": "string"}, "quote": {"type": "string"}},
                  "required": ["qualifies", "species", "detail", "quote"]}

DRUG_SYSTEM = """You read one PubMed abstract about a specific drug and decide two things.

animal_healthy: true when the abstract reports THIS drug (under any of the names given) given to animals that do not model a disease (healthy or naive animals) and measures its pharmacokinetics, tissue or brain exposure, or a pharmacodynamic effect on its target or pathway. Toxicology alone, in vitro work, other drugs and reviews do not qualify.

human_engagement: true when the abstract reports, in people (healthy volunteers or patients), a measurement showing whether THIS drug engaged its target or moved a pharmacodynamic biomarker of its mechanism: receptor occupancy (e.g. PET), target enzyme inhibition, target protein or ligand lowered, transcript knockdown, or a downstream biomarker of the target's pathway. Pharmacokinetics alone, clinical efficacy or safety alone, and animal or in vitro work do not qualify.

Give the species of the study that decided either (human, mouse, rat, ...; empty if neither qualifies), what was measured in a few words in `detail`, and the deciding sentence in `quote` (empty if neither). Judge only from the abstract."""
DRUG_SCHEMA = {"type": "object", "additionalProperties": False,
               "properties": {"animal_healthy": {"type": "boolean"}, "human_engagement": {"type": "boolean"},
                              "species": {"type": "string"}, "detail": {"type": "string"}, "quote": {"type": "string"}},
               "required": ["animal_healthy", "human_engagement", "species", "detail", "quote"]}


def render(p: dict) -> str:
    lines = [f"Drug: {'; '.join(p['drug_names'])}"]
    if p.get("targets"):
        lines.append(f"Its targets: {p['targets']}")
    if p.get("disease"):
        lines.append(f"Disease: {p['disease']} (also: {'; '.join(p['disease_names'][:12])})")
    lines += ["", f"PMID {p['pmid']} ({p.get('year') or 'year unknown'}). {p['title']}", "", p["abstract"] or "(no abstract)"]
    return "\n".join(lines)


def validate_quote(p: dict, out: dict) -> None:
    q = re.sub(r"\s+", " ", out["quote"]).strip().lower()
    text = re.sub(r"\s+", " ", f"{p['title']} {p['abstract'] or ''}").lower()
    if q and q[:60] not in text:
        raise ValueError("quote is not in the abstract")


def task(kind: str, model: str = "claude-sonnet-5", suffix: str = "") -> llm.Task:
    disease = kind == "animal_disease"
    return llm.Task(name=("literature_animal_disease" if disease else "literature_drug_pharmacology") + suffix,
                    prompt_version="v1", schema_version="v1", system=DISEASE_SYSTEM if disease else DRUG_SYSTEM,
                    schema=DISEASE_SCHEMA if disease else DRUG_SCHEMA, render=render, validate=validate_quote,
                    subject_type="moiety_disease_pmid" if disease else "moiety_pmid", model=model,
                    effort="low", max_tokens=2000)


def screen_items(e: pd.DataFrame, kinds: tuple[str, ...]) -> dict[str, dict[str, dict]]:
    """Task name -> subject key -> payload, for every hit of the entries' searches."""
    need = searches(e, kinds)
    with llm.connect() as conn, conn.cursor() as cur:
        drugs, dis = names_of(cur, sorted({m for m, *_ in need}), sorted({d for _, d, *_ in need if d}))
        cur.execute("""SELECT mt.moiety_id, string_agg(DISTINCT t.symbol || ' (' || mt.action || ')', ', ')
                       FROM preclin.moiety_target mt JOIN public.targets t ON t.id = mt.target_id
                       WHERE mt.is_primary AND mt.moiety_id = ANY(%s) GROUP BY 1""", (sorted(drugs),))
        targets = dict(cur.fetchall())
        cur.execute("CREATE TEMP TABLE want (moiety_id int, mondo_id text, kind text, cutoff_year int) ON COMMIT DROP")
        execute_values(cur, "INSERT INTO want VALUES %s", need)
        cur.execute("""SELECT h.moiety_id, h.mondo_id, h.kind, h.pmid, p.title, p.abstract, p.year
                       FROM preclin.literature_hit h JOIN want USING (moiety_id, mondo_id, kind, cutoff_year)
                       JOIN public.publications p USING (pmid)""")
        rows = cur.fetchall()
    out: dict[str, dict[str, dict]] = {}
    for m, d, k, pmid, title, abstract, year in rows:
        t = task(k)
        p = {"drug_names": drugs[m], "targets": targets.get(m, ""), "pmid": pmid, "title": title or "",
             "abstract": abstract, "year": year}
        if k == "animal_disease":
            p |= {"disease": dis[d]["label"], "disease_names": dis[d]["names"]}
        out.setdefault(t.name, {})[f"{m}|{d}|{pmid}" if d else f"{m}|{pmid}"] = p
    return out


def store_screens(t: llm.Task, decided: list[tuple[str, int, dict]]) -> None:
    rows = []
    for key, decision_id, out in decided:
        parts = key.split("|")
        m, d, pmid = (int(parts[0]), parts[1], parts[2]) if len(parts) == 3 else (int(parts[0]), "", parts[1])
        verdicts = {"animal_disease": out["qualifies"]} if t.name.startswith("literature_animal_disease") else \
            {"animal_healthy": out["animal_healthy"], "human_engagement": out["human_engagement"]}
        rows += [(m, d, pmid, k, v, out["species"] or None, out["detail"] or None, out["quote"] or None, decision_id)
                 for k, v in verdicts.items()]
    with llm.connect() as conn, conn.cursor() as cur:
        execute_values(cur, """INSERT INTO preclin.literature_screen
                                 (moiety_id, mondo_id, pmid, kind, qualifies, species, detail, quote, llm_decision_id)
                               VALUES %s ON CONFLICT (moiety_id, mondo_id, pmid, kind) DO UPDATE SET
                                 qualifies = EXCLUDED.qualifies, species = EXCLUDED.species, detail = EXCLUDED.detail,
                                 quote = EXCLUDED.quote, llm_decision_id = EXCLUDED.llm_decision_id""", rows)
        conn.commit()


def screen(args) -> None:
    """Screen every hit of the entries' searches; earlier decisions on the same abstract are reused."""
    kinds = tuple(args.kinds)
    for name, items in screen_items(entries(args.entries), kinds).items():
        t = task("animal_disease" if name == "literature_animal_disease" else "animal_healthy")
        run_id = llm.run(t, items)
        decided = [x for x in llm.decisions(run_id) if x[2] and "error" not in x[2]]
        store_screens(t, decided)
        print(f"{name}: abstracts={len(items)} decided={len(decided)} run={run_id}", flush=True)


def check(_args) -> None:
    """A second model relabels a seeded sample of CHECK_PER_KIND screened abstracts per kind of the pilot."""
    items = screen_items(pilot_entries(), KINDS)
    rng = np.random.default_rng(CHECK_SEED)
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT ON (moiety_id, mondo_id, pmid) moiety_id, mondo_id, pmid, kind
                       FROM preclin.literature_hit ORDER BY moiety_id, mondo_id, pmid, kind""")
        kind_of = {(f"{m}|{d}|{p}" if d else f"{m}|{p}"): k for m, d, p, k in cur.fetchall()}
    for name, its in items.items():
        keys = sorted(its)
        if name == "literature_drug_pharmacology":
            picked = []
            for k in ("animal_healthy", "human_engagement"):
                pool = [x for x in keys if kind_of.get(x) == k]
                picked += [pool[i] for i in rng.choice(len(pool), min(CHECK_PER_KIND, len(pool)), replace=False)]
        else:
            picked = [keys[i] for i in rng.choice(len(keys), min(CHECK_PER_KIND, len(keys)), replace=False)]
        t = task("animal_disease" if name == "literature_animal_disease" else "animal_healthy",
                 model="claude-opus-5-5", suffix="_check")
        run_id = llm.run(t, {k: its[k] for k in picked})
        print(f"{t.name}: sample={len(picked)} decided={len(llm.decisions(run_id))} run={run_id}", flush=True)


def kappa(a: list[bool], b: list[bool]) -> float | None:
    a, b = np.array(a, bool), np.array(b, bool)
    if not len(a):
        return None
    po = float((a == b).mean())
    pe = float(a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean()))
    return None if pe == 1 else (po - pe) / (1 - pe)


def found(e: pd.DataFrame) -> pd.DataFrame:
    """Entry x kind: the qualifying abstracts dated no later than the cutoff."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT h.moiety_id, h.mondo_id, h.kind, h.cutoff_year, h.pmid, p.year
                       FROM preclin.literature_hit h JOIN public.publications p USING (pmid)
                       JOIN preclin.literature_screen s ON s.moiety_id = h.moiety_id AND s.mondo_id = h.mondo_id
                            AND s.pmid = h.pmid AND s.kind = h.kind
                       WHERE s.qualifies""")
        q = pd.DataFrame(cur.fetchall(), columns=["moiety_id", "mondo_id", "kind", "cutoff_year", "pmid", "year"])
    rows = []
    for r in e.itertuples(index=False):
        for k in KINDS:
            if k == "human_engagement" and r.phase < 2:
                continue
            d = r.mondo_id if k == "animal_disease" else ""
            g = q[(q.moiety_id == r.moiety_id) & (q.mondo_id == d) & (q.kind == k) & (q.cutoff_year == r.cutoff_year)
                  & (q.year.isna() | (q.year <= r.cutoff_year))]
            rows.append({"moiety_id": r.moiety_id, "mondo_id": r.mondo_id, "phase": r.phase, "kind": k,
                         "pmids": sorted(set(g.pmid))})
    return pd.DataFrame(rows)


def gate(args) -> None:
    """Recall, agreement and coverage of the pilot against the blind reference set; writes GATE."""
    e = pilot_entries()
    f = found(e)
    ref = []
    for i in range(1, 5):
        with open(os.path.join(args.reference, f"reference_part{i}_result.json")) as fh:
            ref += json.load(fh)
    ref_rows = reference_rows(ref, e)
    k_ = {}
    with llm.connect() as conn, conn.cursor() as cur:
        for name, kinds in (("literature_animal_disease", ("qualifies",)),
                            ("literature_drug_pharmacology", ("animal_healthy", "human_engagement"))):
            cur.execute("""SELECT DISTINCT ON (d.subject_key, d.task) d.subject_key, d.task, d.parsed_output
                           FROM pv_evidence.llm_decision d WHERE d.task IN (%s, %s) AND d.validation_status = 'validated'
                           ORDER BY d.subject_key, d.task, d.created_at DESC""", (name, name + "_check"))
            by = {}
            for key, tname, out in cur.fetchall():
                by.setdefault(key, {})[tname] = out
            pairs = {k: v for k, v in by.items() if len(v) == 2}
            for field in kinds:
                kind = "animal_disease" if field == "qualifies" else field
                a = [v[name][field] for v in pairs.values()]
                b = [v[name + "_check"][field] for v in pairs.values()]
                k_[kind] = {"pairs": len(a), "kappa": kappa(a, b), "agreement": float(np.mean(np.array(a) == np.array(b))) if a else None,
                            "positives_main": int(sum(a)), "positives_check": int(sum(b))}
    result = {"gates": GATES, "kinds": {}}
    for kind in KINDS:
        fr = f[(f.kind == kind)]
        ref_k = ref_rows[ref_rows.kind == kind]
        on_ref = fr.merge(e[e.reference_set][["moiety_id", "mondo_id", "phase"]], on=["moiety_id", "mondo_id", "phase"])
        got = {(r.moiety_id, r.mondo_id, r.phase): set(r.pmids) for r in on_ref.itertuples()}
        studies = ref_k.dropna(subset=["pmid"])
        hit = [p in got.get((m, d, ph), set()) for m, d, ph, p in zip(studies.moiety_id, studies.mondo_id, studies.phase, studies.pmid)]
        n_all = len(ref_k)
        none_entries = set(on_ref[["moiety_id", "mondo_id", "phase"]].itertuples(index=False, name=None)) - \
            set(ref_k[["moiety_id", "mondo_id", "phase"]].itertuples(index=False, name=None))
        ph2 = fr[fr.phase == 2]
        cov = float((ph2.pmids.str.len() > 0).mean()) if len(ph2) else None
        recall = float(np.sum(hit) / n_all) if n_all else None
        recall_pm = float(np.mean(hit)) if len(hit) else None
        kap = k_.get(kind, {}).get("kappa")
        result["kinds"][kind] = {
            "reference_studies": n_all, "reference_studies_in_pubmed": len(studies),
            "recall": recall, "recall_pubmed_indexed": recall_pm,
            "reference_entries": int(ref_k[["moiety_id", "mondo_id", "phase"]].drop_duplicates().shape[0]),
            "agreement_on_reference_none": float(np.mean([not got.get(x) for x in none_entries])) if none_entries else None,
            "pipeline_entries_with_any": int((fr.pmids.str.len() > 0).sum()), "entries": len(fr),
            "phase2_coverage": cov, "check": k_.get(kind),
            "passes": bool(recall is not None and recall >= GATES["recall"] and kap is not None and kap >= GATES["kappa"]
                           and cov is not None and cov >= GATES["phase2_coverage"])}
    with open(GATE, "w") as fh:
        json.dump(result, fh, indent=2, default=float)
    print(json.dumps(result, indent=2, default=float))


def reference_rows(ref: list[dict], e: pd.DataFrame) -> pd.DataFrame:
    """One row per qualifying study the reference agents listed: entry, kind, PMID (None when the study
    is not in PubMed), year. Studies after the entry's cutoff year are dropped."""
    cut = {(int(r.moiety_id), r.mondo_id, int(r.phase)): int(r.cutoff_year) for r in e.itertuples()}
    rows = []
    for entry in ref:
        key = (int(entry["moiety_id"]), entry["mondo_id"], int(entry["phase"]))
        for kind in KINDS:
            for s in entry.get(kind, []) or []:
                year = s.get("year")
                if year is not None and int(year) > cut[key]:
                    continue
                pmid = str(s["pmid"]) if s.get("pmid") else None
                rows.append({"moiety_id": key[0], "mondo_id": key[1], "phase": key[2], "kind": kind,
                             "pmid": pmid, "year": year})
    return pd.DataFrame(rows, columns=["moiety_id", "mondo_id", "phase", "kind", "pmid", "year"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in (("search", search), ("screen", screen)):
        p = sub.add_parser(name)
        p.add_argument("--entries", choices=("pilot", "cohort"), default="cohort")
        p.add_argument("--kinds", nargs="+", choices=KINDS, default=list(KINDS))
        p.set_defaults(fn=fn)
    sub.add_parser("check").set_defaults(fn=check)
    g = sub.add_parser("gate")
    g.add_argument("--reference", required=True, help="directory holding reference_part{1..4}_result.json")
    g.set_defaults(fn=gate)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
