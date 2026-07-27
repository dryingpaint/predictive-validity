#!/usr/bin/env python3
"""
Drug-efficacy PRE-TRIAL re-extraction  (rigorous upgrade to PR #9).

PR #9 date-cleaned the drug-efficacy signal with a PAPER-PRESENCE proxy (does *any*
pre-first-trial preclinical paper exist for the drug), because Melissa's drug-efficacy
rubric stores NO pmids and therefore cannot be dated in place. The proxy conflates a
date change with a metric change.

This script does the real thing: it RE-SCORES drug cell + animal efficacy on Melissa's
own 0-3 rubric (verbatim anchors from db/SCHEMA.md, Categories C and D) using ONLY
PubMed abstracts published BEFORE the program's first_trial_date, then compares the
time-sliced rubric score to the present-day rubric score and computes Relative Success
(RS) of the time-sliced score. The question it answers: does "the drug worked in a
model" carry real predictive signal once you use only evidence that existed before the
trial started?

Reuses infrastructure from PR #9's analyses/nuance_drug_and_structural.py:
  - rs_ci()            : RS + bootstrap CI (copied verbatim, same convention)
  - PubMed eutils      : esearch date-restricted, same 0.34s throttle
The NEW parts are efetch of abstract TEXT and an LLM (or manual) rubric re-score.

RUBRIC SOURCE (verbatim, db/SCHEMA.md):
  C. Cell-pathway validation, drug-level "drug_cell_efficacy":
     C1 Cell-line pharmacology: 0=none / 1=basic / 2=multiple / 3=full panel
     C2 iPSC-derived models 0/1/2/3 ; C3 Organoid 0/1/2/3 ; C4 Primary human cells
     0/1/2/3 ; C6 Perturbation-rescue 0/1/2/3.  (Category C composite = cell efficacy.)
  D. Animal in vivo, drug-level "drug_rodent_efficacy"/"drug_nonrodent_efficacy":
     D2 Rodent drug efficacy: "Drug tested in rodent disease model, effect size" 0/1/2/3
     D3 Non-rodent efficacy:  "Dog, monkey, non-human primate efficacy" 0/1/2/3
The 0-3 anchor Melissa uses for these PubMed-extracted efficacy dims (from the C1
anchor, generalized): 0 = no efficacy evidence in the given model class; 1 = basic /
single positive report; 2 = multiple independent positive reports; 3 = full panel /
strong dose-response, disease-relevant model.

SCORER BACKENDS (--scorer):
  anthropic : model claude-haiku-4-5-20251001 (cheap), needs ANTHROPIC_API_KEY.
  manual    : reads data/drug_efficacy_pretrial_manual_scores.csv (hand scores by a
              careful reader against the rubric) -- the honest fallback when no API key
              is available. Used for the proof-of-concept run.

MODES (--mode):
  present-rs : present-day raw rubric RS on the assessed-drug cohort (real; anchor).
  fetch      : esearch (pre-first-trial-date) + efetch abstracts for the POC drug set;
               cache to data/drug_pretrial_abstracts.json.
  score      : run the chosen scorer over fetched abstracts -> time-sliced scores.
  rs         : RS of the time-sliced score + per-drug time-sliced-vs-present table.
  all        : present-rs, then (given fetched+scored inputs) rs.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
os.makedirs(DATA, exist_ok=True)
ABSTRACT_CACHE = os.path.join(DATA, "drug_pretrial_abstracts.json")
MANUAL_SCORES = os.path.join(DATA, "drug_efficacy_pretrial_manual_scores.csv")
TIMESLICED_OUT = os.path.join(DATA, "drug_efficacy_pretrial_scores.csv")
PRESENT_RS_OUT = os.path.join(DATA, "drug_efficacy_present_rs.csv")
DB = os.environ.get("DATABASE_URL")

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# Verbatim rubric block handed to the scorer (see db/SCHEMA.md, Categories C and D).
RUBRIC = """You are scoring DRUG-SPECIFIC preclinical efficacy on Melissa Du's 0-3 rubric
(from db/SCHEMA.md, Categories C "Cell-pathway validation" and D "Animal in vivo").

Score TWO dimensions from the supplied pre-trial PubMed abstracts ONLY:

drug_cell_efficacy (Category C, does the drug work in human-relevant CELLS):
  anchors (generalized from C1 "Cell-line pharmacology" 0=none/1=basic/2=multiple/3=full panel,
  plus C2 iPSC, C3 organoid, C4 primary human cells, C6 perturbation-rescue):
    0 = no cell efficacy evidence for this drug
    1 = basic: a single positive in-vitro / cell-line result (e.g. one IC50 or one assay)
    2 = multiple independent positive cell results, or a disease-relevant human cell model
    3 = full panel / strong dose-response across models incl. iPSC / organoid / primary human cells

drug_animal_efficacy (Category D, does the drug work in ANIMAL disease models):
  anchors (from D2 "Drug tested in rodent disease model, effect size" and
  D3 "Dog/monkey/NHP efficacy", 0/1/2/3):
    0 = no animal efficacy evidence for this drug
    1 = basic: a single rodent model showing an effect
    2 = multiple rodent models, or clear dose-response / disease-relevant effect size
    3 = strong, replicated, disease-relevant efficacy incl. non-rodent (dog/monkey/NHP)

Rules:
- Use ONLY the abstracts provided. They are all published BEFORE the trial started.
- Score the DRUG named, not the target in general. Target-only KO/genetics is NOT drug efficacy.
- If no relevant abstract, score 0.
Return STRICT JSON: {"drug_cell_efficacy": int, "drug_animal_efficacy": int, "rationale": str}"""


# ---------------------------------------------------------------------------
# RS + bootstrap CI -- copied verbatim from PR #9 nuance_drug_and_structural.py
# ---------------------------------------------------------------------------
def rs_ci(support, approved, n_boot=2000, seed=7):
    support = np.asarray(support, bool)
    approved = np.asarray(approved, bool)

    def _rs(sup, appr):
        s = appr[sup]
        ns = appr[~sup]
        if s.size == 0 or ns.size == 0 or ns.mean() == 0:
            return np.nan
        return s.mean() / ns.mean()

    pt = _rs(support, approved)
    rng = np.random.default_rng(seed)
    idx = np.arange(support.size)
    boots = []
    for _ in range(n_boot):
        b = rng.choice(idx, idx.size, replace=True)
        boots.append(_rs(support[b], approved[b]))
    boots = np.array([x for x in boots if not np.isnan(x)])
    lo, hi = (np.percentile(boots, [2.5, 97.5]) if boots.size else (np.nan, np.nan))
    f = lambda x: round(x, 2) if x == x else np.nan
    return dict(rs=f(pt), lo=f(lo), hi=f(hi), n_support=int(support.sum()),
                n_not=int((~support).sum()),
                pct_appr_support=round(100 * approved[support].mean(), 1) if support.sum() else np.nan,
                pct_appr_not=round(100 * approved[~support].mean(), 1) if (~support).sum() else np.nan)


# ---------------------------------------------------------------------------
# DB cohort
# ---------------------------------------------------------------------------
def load_cohort():
    """Program-level cohort restricted to drugs that HAVE a stored efficacy rubric
    score (the assessed-drug universe). Present-day RS is computed here among assessed
    drugs (score>=2 vs score<2), which is the fair comparator for a re-score -- unlike
    PR #9's left-join onto all ~13.9k drugs, which lumps every UNSCORED drug into
    'not supported' and inflates RS via a scored-vs-unscored selection effect."""
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(DB)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT p.program_id, p.drug_id, d.display_name, d.normalized_name,
               p.first_trial_date, p.highest_phase,
               (po.approved_us OR po.approved_ex_us) AS approved
        FROM preclin.program p
        JOIN preclin.drug d ON d.drug_id = p.drug_id
        JOIN preclin.program_outcome po ON po.program_id = p.program_id
        WHERE p.highest_phase >= 2 AND p.first_trial_date IS NOT NULL
    """)
    progs = pd.DataFrame(cur.fetchall())
    cur.execute("""
        SELECT subject_id AS drug_id, dimension, value_numeric AS score
        FROM preclin.evidence_score
        WHERE subject_type='drug'
          AND dimension IN ('drug_cell_efficacy','drug_rodent_efficacy','drug_nonrodent_efficacy')
    """)
    eff = pd.DataFrame(cur.fetchall())
    conn.close()
    piv = eff.pivot_table(index="drug_id", columns="dimension", values="score", aggfunc="max")
    # present-day "animal" = max(rodent, nonrodent), to match the two-dim re-score
    piv["present_cell"] = piv.get("drug_cell_efficacy")
    piv["present_animal"] = piv[["drug_rodent_efficacy", "drug_nonrodent_efficacy"]].max(axis=1)
    cohort = progs.merge(piv.reset_index(), on="drug_id", how="inner")
    return cohort


def present_rs():
    cohort = load_cohort()
    appr = cohort.approved.fillna(False).to_numpy(bool)
    rows = []
    for dim, lab in [("present_cell", "drug_cell_efficacy (present, assessed-drug RS)"),
                     ("present_animal", "drug_animal_efficacy (present, assessed-drug RS)")]:
        sup = (cohort[dim].fillna(0) >= 2).to_numpy()
        r = rs_ci(sup, appr)
        r.update(dimension=dim, measure=lab)
        rows.append(r)
        print(f"  {lab:52s} RS={r['rs']} [{r['lo']},{r['hi']}] "
              f"n_sup={r['n_support']} n_not={r['n_not']}")
    out = pd.DataFrame(rows)
    out.to_csv(PRESENT_RS_OUT, index=False)
    print(f"  programs={len(cohort)} unique drugs={cohort.drug_id.nunique()}")
    print(f"  wrote {PRESENT_RS_OUT}")
    return cohort


# ---------------------------------------------------------------------------
# PubMed
# ---------------------------------------------------------------------------
def esearch(term, retmax=20):
    url = (f"{EUTILS}/esearch.fcgi?db=pubmed&retmode=json&retmax={retmax}"
           f"&term={urllib.parse.quote(term)}")
    try:
        d = json.load(urllib.request.urlopen(url, timeout=30))
        return d["esearchresult"].get("idlist", []), int(d["esearchresult"]["count"])
    except Exception as e:
        print(f"    esearch error: {e}")
        return [], -1


def efetch_abstracts(pmids):
    if not pmids:
        return []
    url = (f"{EUTILS}/efetch.fcgi?db=pubmed&retmode=xml&rettype=abstract"
           f"&id={','.join(pmids)}")
    import re
    from xml.etree import ElementTree as ET
    try:
        xml = urllib.request.urlopen(url, timeout=60).read()
        root = ET.fromstring(xml)
    except Exception as e:
        print(f"    efetch error: {e}")
        return []
    out = []
    for art in root.findall(".//PubmedArticle"):
        pmid = art.findtext(".//PMID") or ""
        year = (art.findtext(".//PubDate/Year")
                or (art.findtext(".//PubDate/MedlineDate") or "")[:4])
        title = art.findtext(".//ArticleTitle") or ""
        abst = " ".join(t.text or "" for t in art.findall(".//AbstractText"))
        out.append({"pmid": pmid, "year": year, "title": title,
                    "abstract": re.sub(r"\s+", " ", abst).strip()})
    return out


def fetch_poc(poc):
    """poc: list of dicts {drug_id, name, cutoff_year, note}. Cache abstracts."""
    cache = {}
    if os.path.exists(ABSTRACT_CACHE):
        cache = json.load(open(ABSTRACT_CACHE))
    preclin = ('(mice OR mouse OR rat OR "cell line" OR "in vitro" OR xenograft OR '
               'preclinical OR "animal model" OR "cell culture" OR monkey OR dog OR '
               'cynomolgus OR pharmacology)')
    for d in poc:
        key = str(d["drug_id"])
        if key in cache:
            print(f"  cached: {d['name']}")
            continue
        cy = int(d["cutoff_year"])
        syns = d.get("synonyms", [d["name"]])
        name_clause = "(" + " OR ".join(f'"{s}"[tiab]' for s in syns) + ")"
        term = f'{name_clause} AND {preclin} AND ("1900"[dp] : "{cy - 1}"[dp])'
        pmids, count = esearch(term, retmax=20)
        time.sleep(0.34)
        abstracts = efetch_abstracts(pmids)
        time.sleep(0.34)
        cache[key] = {"drug_id": d["drug_id"], "name": d["name"],
                      "cutoff_year": cy, "note": d.get("note", ""),
                      "n_hits_total": count, "n_fetched": len(abstracts),
                      "abstracts": abstracts}
        print(f"  {d['name']:16s} cutoff<{cy}  hits={count} fetched={len(abstracts)}")
        json.dump(cache, open(ABSTRACT_CACHE, "w"), indent=1)
    json.dump(cache, open(ABSTRACT_CACHE, "w"), indent=1)
    print(f"  wrote {ABSTRACT_CACHE}")


# ---------------------------------------------------------------------------
# Scorers
# ---------------------------------------------------------------------------
def score_anthropic(entry):
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    absts = "\n\n".join(f"[{a['year']}] {a['title']}\n{a['abstract']}"
                        for a in entry["abstracts"][:15])
    if not absts.strip():
        return {"drug_cell_efficacy": 0, "drug_animal_efficacy": 0,
                "rationale": "no pre-trial abstracts"}
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=500,
        system=RUBRIC,
        messages=[{"role": "user", "content":
                   f"DRUG: {entry['name']}\nPRE-TRIAL ABSTRACTS (before "
                   f"{entry['cutoff_year']}):\n\n{absts}"}])
    txt = msg.content[0].text
    import re
    m = re.search(r"\{.*\}", txt, re.S)
    return json.loads(m.group(0)) if m else {"drug_cell_efficacy": 0,
                                             "drug_animal_efficacy": 0, "rationale": txt[:200]}


def run_score(scorer):
    cache = json.load(open(ABSTRACT_CACHE))
    if scorer == "manual":
        if not os.path.exists(MANUAL_SCORES):
            sys.exit(f"manual scorer needs {MANUAL_SCORES}")
        man = pd.read_csv(MANUAL_SCORES)
        rows = []
        for _, m in man.iterrows():
            e = cache.get(str(m.drug_id), {})
            rows.append(dict(drug_id=m.drug_id, name=m["name"],
                             cutoff_year=e.get("cutoff_year"),
                             n_fetched=e.get("n_fetched"),
                             ts_cell=m.drug_cell_efficacy, ts_animal=m.drug_animal_efficacy,
                             scorer="manual"))
        df = pd.DataFrame(rows)
    else:  # anthropic
        rows = []
        for key, e in cache.items():
            s = score_anthropic(e)
            rows.append(dict(drug_id=e["drug_id"], name=e["name"],
                             cutoff_year=e["cutoff_year"], n_fetched=e["n_fetched"],
                             ts_cell=s["drug_cell_efficacy"],
                             ts_animal=s["drug_animal_efficacy"], scorer="anthropic"))
            print(f"  {e['name']:16s} cell={s['drug_cell_efficacy']} "
                  f"animal={s['drug_animal_efficacy']}")
        df = pd.DataFrame(rows)
    df.to_csv(TIMESLICED_OUT, index=False)
    print(f"  wrote {TIMESLICED_OUT}")
    return df


# ---------------------------------------------------------------------------
# Time-sliced RS + comparison
# ---------------------------------------------------------------------------
def timesliced_rs():
    ts = pd.read_csv(TIMESLICED_OUT)
    cohort = load_cohort()
    # attach approval + present score from cohort (dedup to drug level)
    dl = (cohort.sort_values("approved", ascending=False)
          .drop_duplicates("drug_id")[["drug_id", "approved", "present_cell", "present_animal"]])
    m = ts.merge(dl, on="drug_id", how="left")
    # Out-of-DB POC drugs (pre-2015 failures / approved contrast not in the 2015-2025
    # window) get documented approval labels; DB failures default to their DB label.
    m["approved"] = m["approved"].where(m.approved.notna(),
                                        m.drug_id.map(POC_APPROVED)).fillna(False)
    # Present-day reference: DB stored score if the drug is in the assessed cohort,
    # else the CASE_STUDIES.md present-day expert score (failures only).
    m["present_cell"] = m["present_cell"].where(m.present_cell.notna(),
                                                m.drug_id.map(CASE_STUDIES_PRESENT_CELL))
    m["present_animal"] = m["present_animal"].where(m.present_animal.notna(),
                                                    m.drug_id.map(CASE_STUDIES_PRESENT_ANIMAL))
    m["ts_max"] = m[["ts_cell", "ts_animal"]].max(axis=1)
    print("\n  Per-drug time-sliced vs present:")
    for _, r in m.iterrows():
        print(f"    {r['name']:16s} ts(cell/animal)={int(r.ts_cell)}/{int(r.ts_animal)}"
              f"  present(cell/animal)={r.present_cell}/{r.present_animal}"
              f"  approved={bool(r.approved)}")
    appr = m.approved.fillna(False).to_numpy(bool)
    if appr.sum() and (~appr).sum():
        for lab, col in [("time-sliced cell", "ts_cell"),
                         ("time-sliced animal", "ts_animal"),
                         ("time-sliced max(cell,animal)", "ts_max")]:
            sup = (m[col].fillna(0) >= 2).to_numpy()
            r = rs_ci(sup, appr)
            print(f"  RS {lab:30s}: {r['rs']} [{r['lo']},{r['hi']}] "
                  f"n_sup={r['n_support']} n_not={r['n_not']}")
    else:
        print("  [RS undefined: POC sample lacks both approved and failed drugs]")
    m.to_csv(os.path.join(DATA, "drug_efficacy_pretrial_comparison.csv"), index=False)
    print(f"  wrote {os.path.join(DATA, 'drug_efficacy_pretrial_comparison.csv')}")


# ---------------------------------------------------------------------------
# POC drug set (6 CASE_STUDIES failures + matched approved contrast).
# cutoff_year = documented true first-in-human YEAR (DB first_trial_date is bounded by
# the 2015-2025 CT.gov window, so it is wrong for pre-2015 drugs; documented here).
# ---------------------------------------------------------------------------
POC = [
    # --- CASE_STUDIES.md failures (strong preclinical, failed in humans) ---
    # synonyms include the developmental CODE NAME, because the INN is coined late and
    # pre-trial preclinical papers use the code (a real coverage fix over name-only search).
    dict(drug_id=20212, name="verubecestat", cutoff_year=2012, note="BACE1/AD, fail; FIH ~2012",
         synonyms=["verubecestat", "MK-8931", "MK 8931"]),
    dict(drug_id=11898, name="torcetrapib", cutoff_year=2004, note="CETP/CVD, fail; FIH ~2004",
         synonyms=["torcetrapib", "CP-529414", "CP 529414"]),
    dict(drug_id=11151, name="semagacestat", cutoff_year=2005, note="gamma-secretase/AD, fail; FIH ~2005",
         synonyms=["semagacestat", "LY450139", "LY-450139"]),
    dict(drug_id=16167, name="solanezumab", cutoff_year=2007, note="anti-Abeta mAb/AD, fail; FIH ~2007",
         synonyms=["solanezumab", "LY2062430", "m266"]),
    dict(drug_id=18800, name="theralizumab", cutoff_year=2006, note="TGN1412 CD28/2006 fail",
         synonyms=["theralizumab", "TGN1412", "TGN-1412", "TAB08"]),
    dict(drug_id=999001, name="fialuridine", cutoff_year=1993, note="HBV pol, 5 deaths 1993; not in DB",
         synonyms=["fialuridine", "FIAU", "FIAC"]),
    # --- approved contrast (well-characterized pre-trial preclinical) ---
    dict(drug_id=999101, name="sofosbuvir", cutoff_year=2010, note="HCV NS5B, approved 2013",
         synonyms=["sofosbuvir", "PSI-7977", "GS-7977", "PSI-7851"]),
    dict(drug_id=999102, name="sitagliptin", cutoff_year=2003, note="DPP4, approved 2006",
         synonyms=["sitagliptin", "MK-0431"]),
    dict(drug_id=999103, name="maraviroc", cutoff_year=2003, note="CCR5, approved 2007",
         synonyms=["maraviroc", "UK-427857", "UK 427857"]),
    dict(drug_id=999104, name="palbociclib", cutoff_year=2009, note="CDK4/6, approved 2015",
         synonyms=["palbociclib", "PD-0332991", "PD 0332991"]),
    dict(drug_id=999105, name="venetoclax", cutoff_year=2011, note="BCL2, approved 2016",
         synonyms=["venetoclax", "ABT-199", "GDC-0199"]),
    dict(drug_id=999106, name="tofacitinib", cutoff_year=2004, note="JAK, approved 2012",
         synonyms=["tofacitinib", "CP-690550", "CP-690,550", "tasocitinib"]),
]
# approval labels for the POC sample (documented outcome, since several are not in the
# 2015-2025 DB cohort). Failures = CASE_STUDIES; approvals = FDA-approved.
POC_APPROVED = {999101: True, 999102: True, 999103: True, 999104: True,
                999105: True, 999106: True}
# Present-day expert scores from CASE_STUDIES.md ("Cell-pathway validation" / "Animal
# in vivo"), for the 6 failures (which have no stored drug_cell/animal_efficacy row).
CASE_STUDIES_PRESENT_CELL = {20212: 3, 11898: 3, 11151: 3, 16167: 3, 18800: 3, 999001: 2}
CASE_STUDIES_PRESENT_ANIMAL = {20212: 3, 11898: 3, 11151: 3, 16167: 3, 18800: 3, 999001: 3}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True,
                    choices=["present-rs", "fetch", "score", "rs", "all"])
    ap.add_argument("--scorer", default="manual", choices=["manual", "anthropic"])
    args = ap.parse_args()

    if args.mode in ("present-rs", "all"):
        if not DB:
            sys.exit("Set DATABASE_URL")
        print("== present-day raw rubric RS (assessed-drug cohort) ==")
        present_rs()
    if args.mode == "fetch":
        print("== fetch pre-first-trial abstracts (PubMed) ==")
        fetch_poc(POC)
    if args.mode == "score":
        print(f"== score time-sliced ({args.scorer}) ==")
        run_score(args.scorer)
    if args.mode in ("rs", "all"):
        print("== time-sliced RS + comparison ==")
        timesliced_rs()


if __name__ == "__main__":
    main()
