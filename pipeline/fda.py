"""FDA approval sources -> preclin.fda_* tables.

    python -m pipeline.fda fetch     # Drugs@FDA, openFDA labels, approval letters -> .cache/fda
    python -m pipeline.fda load      # cached files -> preclin.fda_application/_product/_submission/_letter/_label
    python -m pipeline.fda extract   # LLM: approved uses stated in each letter -> preclin.fda_approved_use
    python -m pipeline.fda link      # LLM: each application's active ingredients -> preclin.moiety
    python -m pipeline.fda load-cber # CBER approval letters (.cache/cber/letters_index.jsonl) -> preclin.fda_*

CBER-regulated biologics (vaccines, blood and plasma products, cell and gene
therapies) are not in Drugs@FDA; their original approvals and supplements come
from CBER's yearly approval pages and product approval-history pages. An
action listed without a retrievable letter keeps the listing text as its
document.

Letters cover every approved original NDA/BLA and every approved efficacy
supplement (Drugs@FDA submission class EFFICACY) from 2015-01-01 through the
Drugs@FDA data date, so programs that started in the study window are
followed to the snapshot.
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import subprocess
import tempfile
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

import requests
from psycopg2.extras import execute_values
from pypdf import PdfReader

from pipeline import llm

CACHE = os.path.join(llm.REPO, ".cache", "fda")
DRUGSFDA_URL = "https://www.fda.gov/media/89850/download"
OPENFDA_INDEX = "https://api.fda.gov/download.json"
WINDOW = ("2015-01-01", "2026-12-31")
EFFICACY_CLASS = "2"
HEADERS = {"User-Agent": "Mozilla/5.0 (predictive-validity research)"}


def read_tsv(name: str) -> list[dict[str, str]]:
    with open(os.path.join(CACHE, "drugsfda", name), encoding="latin-1") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def fetch(_args) -> None:
    os.makedirs(os.path.join(CACHE, "openfda"), exist_ok=True)
    zpath = os.path.join(CACHE, "drugsfda.zip")
    with open(zpath, "wb") as f:
        f.write(requests.get(DRUGSFDA_URL, headers=HEADERS, timeout=300).content)
    zipfile.ZipFile(zpath).extractall(os.path.join(CACHE, "drugsfda"))
    index = requests.get(OPENFDA_INDEX, timeout=60).json()["results"]["drug"]["label"]
    json.dump(index, open(os.path.join(CACHE, "openfda", "label_index.json"), "w"))
    for part in index["partitions"]:
        dest = os.path.join(CACHE, "openfda", os.path.basename(part["file"]))
        if not os.path.exists(dest):
            with open(dest, "wb") as f:
                f.write(requests.get(part["file"], timeout=600).content)

    # Submissions in scope: approved ORIG submissions and efficacy-class supplements of NDA/BLA
    # applications inside WINDOW.
    apps = {r["ApplNo"] for r in read_tsv("Applications.txt") if r["ApplType"] in ("NDA", "BLA")}
    wanted = {(s["ApplNo"], s["SubmissionType"].strip(), s["SubmissionNo"]) for s in read_tsv("Submissions.txt")
              if s["SubmissionStatus"] == "AP" and WINDOW[0] <= s["SubmissionStatusDate"][:10] <= WINDOW[1]
              and s["ApplNo"] in apps
              and (s["SubmissionType"] == "ORIG" or s["SubmissionClassCodeID"] == EFFICACY_CLASS)}
    docs = [d for d in read_tsv("ApplicationDocs.txt") if d["ApplicationDocsTypeID"] == "1"
            and (d["ApplNo"], d["SubmissionType"].strip(), d["SubmissionNo"]) in wanted]
    index_path = os.path.join(CACHE, "letters_index.jsonl")
    done = {json.loads(line)["url"] for line in open(index_path)} if os.path.exists(index_path) else set()
    todo = [d for d in docs if d["ApplicationDocsURL"].strip() not in done]
    os.makedirs(os.path.join(CACHE, "letters"), exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)

    def get(doc):
        url = doc["ApplicationDocsURL"].strip()
        for attempt in range(5):
            try:
                r = session.get(url.replace("http://", "https://"), timeout=90)
                if r.status_code == 404:
                    return doc, None, "404"
                r.raise_for_status()
                return doc, r.content, None
            except requests.RequestException as exc:
                err = str(exc)
                time.sleep(3 * (attempt + 1))
        return doc, None, err

    with open(index_path, "a") as out, ThreadPoolExecutor(max_workers=4) as pool:
        for fut in as_completed([pool.submit(get, d) for d in todo]):
            doc, content, err = fut.result()
            rec = {"url": doc["ApplicationDocsURL"].strip(), "appl_no": doc["ApplNo"],
                   "submission_type": doc["SubmissionType"].strip(), "submission_no": doc["SubmissionNo"],
                   "doc_date": doc["ApplicationDocsDate"][:10], "error": err}
            if content:
                sha = hashlib.sha256(content).hexdigest()
                open(os.path.join(CACHE, "letters", f"{sha}.pdf"), "wb").write(content)
                rec.update(sha256=sha, n_bytes=len(content))
            out.write(json.dumps(rec) + "\n")
    print(f"letters fetched: {len(todo)}")


COMMON_WORDS = {"the", "of", "and", "to", "in", "for", "this", "that", "your", "with", "is", "we", "on", "be"}


def readable(text: str) -> bool:
    """False for an empty text layer, or one with many words and none of the
    commonest English words (a font with a shifted encoding)."""
    words = [w.lower() for w in text.split() if w.isalpha()]
    return bool(words) and (len(words) < 40 or any(w in COMMON_WORDS for w in words))


def pdf_text(path: str) -> str:
    """Text of every page of a PDF. Pages whose text layer is missing (letters
    whose first page is a scanned letterhead image) or unreadable are rendered
    at 300 dpi and OCRed."""
    pages = []
    for i, page in enumerate(PdfReader(path).pages, start=1):
        text = page.extract_text() or ""
        if not readable(text):
            with tempfile.TemporaryDirectory() as tmp:
                subprocess.run(["pdftoppm", "-r", "300", "-f", str(i), "-l", str(i), "-png", path,
                                os.path.join(tmp, "page")], check=True, capture_output=True)
                image = glob.glob(os.path.join(tmp, "page*.png"))[0]
                text = subprocess.run(["tesseract", image, "-"], check=True, capture_output=True, text=True).stdout
        pages.append(text)
    return "\n".join(pages).replace("\x00", "")


def write_letters(cur, letters: list[tuple], links: list[tuple]) -> None:
    """Letter texts by sha256, then each submission's letter links."""
    execute_values(cur, """INSERT INTO preclin.fda_letter (letter_sha256, letter_text, n_bytes)
        VALUES %s ON CONFLICT (letter_sha256) DO UPDATE SET letter_text = EXCLUDED.letter_text""", letters)
    execute_values(cur, """INSERT INTO preclin.fda_submission_letter
        (appl_no, submission_type, submission_no, url, doc_date, letter_sha256, fetch_error) VALUES %s
        ON CONFLICT (appl_no, submission_type, submission_no, url) DO UPDATE SET
          letter_sha256 = EXCLUDED.letter_sha256, fetch_error = EXCLUDED.fetch_error""", links)


def load(_args) -> None:
    apps = {r["ApplNo"]: r for r in read_tsv("Applications.txt") if r["ApplType"] in ("NDA", "BLA")}
    zip_sha = llm.sha256_file(os.path.join(CACHE, "drugsfda.zip"))
    data_date = max(r["SubmissionStatusDate"][:10] for r in read_tsv("Submissions.txt"))
    label_index = json.load(open(os.path.join(CACHE, "openfda", "label_index.json")))
    label_files = sorted(glob.glob(os.path.join(CACHE, "openfda", "drug-label-*.json.zip")))
    label_sha = hashlib.sha256("".join(llm.sha256_file(p) for p in label_files).encode()).hexdigest()

    with llm.connect() as conn, conn.cursor() as cur:
        rel_drugsfda = llm.register_release(cur, "fda_drugsfda", data_date, DRUGSFDA_URL, zip_sha,
                                            {"latest_submission_date": data_date})
        rel_label = llm.register_release(cur, "openfda_drug_label", label_index["export_date"],
                                         OPENFDA_INDEX, label_sha,
                                         {"partitions": [os.path.basename(p) for p in label_files],
                                          "sha256_of": "concatenated per-partition sha256 hex digests"})

        execute_values(cur, """INSERT INTO preclin.fda_application
            (appl_no, appl_type, center, sponsor_name, source_release_id) VALUES %s
            ON CONFLICT (appl_no) DO UPDATE SET sponsor_name = EXCLUDED.sponsor_name,
              source_release_id = EXCLUDED.source_release_id""",
            [(a, r["ApplType"], "CDER", r["SponsorName"], rel_drugsfda) for a, r in apps.items()])
        execute_values(cur, """INSERT INTO preclin.fda_product
            (appl_no, product_no, drug_name, active_ingredient, form, strength) VALUES %s
            ON CONFLICT (appl_no, product_no) DO UPDATE SET drug_name = EXCLUDED.drug_name,
              active_ingredient = EXCLUDED.active_ingredient""",
            [(p["ApplNo"], p["ProductNo"], p["DrugName"], p["ActiveIngredient"], p["Form"], p["Strength"])
             for p in read_tsv("Products.txt") if p["ApplNo"] in apps])
        classes = {r["SubmissionClassCodeID"]: r["SubmissionClassCode"] for r in read_tsv("SubmissionClass_Lookup.txt")}
        execute_values(cur, """INSERT INTO preclin.fda_submission
            (appl_no, submission_type, submission_no, submission_class, status, status_date, review_priority)
            VALUES %s ON CONFLICT (appl_no, submission_type, submission_no) DO UPDATE SET
              submission_class = EXCLUDED.submission_class, status = EXCLUDED.status,
              status_date = EXCLUDED.status_date, review_priority = EXCLUDED.review_priority""",
            [(s["ApplNo"], s["SubmissionType"].strip(), s["SubmissionNo"], classes.get(s["SubmissionClassCodeID"]),
              s["SubmissionStatus"], s["SubmissionStatusDate"][:10] or None, s["ReviewPriority"] or None)
             for s in read_tsv("Submissions.txt")
             if s["ApplNo"] in apps and s["SubmissionType"].strip() in ("ORIG", "SUPPL")])

        sizes, links = {}, {}
        for line in open(os.path.join(CACHE, "letters_index.jsonl")):
            r = json.loads(line)
            if r.get("sha256"):
                sizes[r["sha256"]] = r["n_bytes"]
            key = (r["appl_no"], r["submission_type"], r["submission_no"], r["url"])
            if r.get("sha256") or key not in links:  # a successful fetch supersedes a failed one
                links[key] = (*key, r.get("doc_date") or None, r.get("sha256"), r.get("error"))
        links = list(links.values())
        with ProcessPoolExecutor() as pool:
            texts = pool.map(pdf_text, [os.path.join(CACHE, "letters", f"{sha}.pdf") for sha in sizes], chunksize=20)
            letters = [(sha, text, n) for (sha, n), text in zip(sizes.items(), texts)]
        write_letters(cur, letters, [l for l in links if l[0] in apps])

        labels = []
        for path in label_files:
            with zipfile.ZipFile(path) as zf:
                for name in zf.namelist():
                    for r in json.loads(zf.read(name))["results"]:
                        of = r.get("openfda", {})
                        nums = [a for a in of.get("application_number", []) if a.startswith(("NDA", "BLA"))]
                        if not nums:
                            continue
                        eff = r.get("effective_time")
                        labels.append((r["set_id"], r["id"], f"{eff[:4]}-{eff[4:6]}-{eff[6:8]}" if eff else None,
                                       nums, of.get("brand_name", []), of.get("generic_name", []),
                                       of.get("substance_name", []), of.get("unii", []),
                                       " ".join(r.get("indications_and_usage", [])) or None, rel_label))
        execute_values(cur, """INSERT INTO preclin.fda_label
            (set_id, spl_id, effective_date, application_numbers, brand_names, generic_names,
             substance_names, unii, indications_text, source_release_id) VALUES %s
            ON CONFLICT (set_id) DO UPDATE SET spl_id = EXCLUDED.spl_id,
              effective_date = EXCLUDED.effective_date, application_numbers = EXCLUDED.application_numbers,
              brand_names = EXCLUDED.brand_names, generic_names = EXCLUDED.generic_names,
              substance_names = EXCLUDED.substance_names, unii = EXCLUDED.unii,
              indications_text = EXCLUDED.indications_text, source_release_id = EXCLUDED.source_release_id""",
            labels)
        conn.commit()
    print(f"applications={len(apps)} letters={len(letters)} letter_links={len(links)} labels={len(labels)}")


LETTER_SYSTEM = """You read U.S. FDA approval letters (NDA/BLA original approvals and efficacy supplements) and record exactly what use was approved by THIS action.

Rules:
- Report only uses that this letter approves or changes. Do not list the drug's previously approved indications unless the letter re-states them as part of this action.
- If the letter only says the supplement "provides for revisions to the labeling" without naming a disease or population, set letter_states_use=false and leave approved_uses empty.
- One entry per distinct disease/population combination approved.
- disease: the disease or condition in plain standard medical terms (e.g. "non-small cell lung cancer", "type 2 diabetes mellitus", "chronic plaque psoriasis"), without population qualifiers.
- qualifiers: the population restrictions stated (age group, line of therapy, prior treatment, biomarker/mutation, disease stage/severity, combination partner drugs, setting such as adjuvant/neoadjuvant/maintenance).
- change_type:
  new_indication = a disease/condition not previously on the label for this product;
  new_population = same disease, newly approved population (e.g. pediatric extension, new line of therapy, new biomarker subgroup, new stage/setting such as adjuvant);
  new_regimen = new dose, schedule, formulation-related use, or combination partner within an already-approved population;
  conversion_to_full = accelerated approval converted to regular approval / confirmatory data;
  efficacy_labeling = efficacy data added to labeling (e.g. new clinical study results, new endpoint) without a new population;
  original_approval = first approval of this application (ORIG submissions);
  other.
- If uncertain whether the disease was already on the label, use your best judgment from the letter text and say so in notes."""

LETTER_SCHEMA = {
    "type": "object",
    "properties": {
        "products": {"type": "array", "items": {"type": "string"}},
        "letter_states_use": {"type": "boolean"},
        "approved_uses": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "indication_as_written": {"type": "string"},
                "disease": {"type": "string"},
                "qualifiers": {"type": "array", "items": {"type": "string"}},
                "change_type": {"type": "string", "enum": [
                    "original_approval", "new_indication", "new_population", "new_regimen",
                    "conversion_to_full", "efficacy_labeling", "other"]},
                "accelerated_approval": {"type": "boolean"},
            },
            "required": ["indication_as_written", "disease", "qualifiers", "change_type", "accelerated_approval"],
            "additionalProperties": False}},
        "notes": {"type": "string"},
    },
    "required": ["products", "letter_states_use", "approved_uses", "notes"],
    "additionalProperties": False,
}


def render_letter(p: dict) -> str:
    subs = "; ".join(f"{s['appl_type']} {s['appl_no']} {s['submission_type']}-{s['submission_no']} "
                     f"approved {s['approval_date']}" for s in p["submissions"])
    return f"Submissions covered by this letter: {subs}\n\nLetter text:\n{p['text']}"


LETTER_TASK = llm.Task(
    name="fda_letter_approved_uses", prompt_version="v1", schema_version="v1",
    system=LETTER_SYSTEM, schema=LETTER_SCHEMA, render=render_letter, subject_type="fda_letter",
    effort="medium", max_tokens=6000)


def extract(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT l.letter_sha256, l.letter_text,
                   json_agg(json_build_object('appl_no', a.appl_no, 'appl_type', a.appl_type,
                            'submission_type', s.submission_type, 'submission_no', s.submission_no,
                            'approval_date', s.status_date) ORDER BY a.appl_no, s.submission_no)
            FROM preclin.fda_letter l
            JOIN preclin.fda_submission_letter sl USING (letter_sha256)
            JOIN preclin.fda_submission s USING (appl_no, submission_type, submission_no)
            JOIN preclin.fda_application a USING (appl_no)
            GROUP BY l.letter_sha256, l.letter_text""")
        items = {sha: {"text": text[:150000], "submissions": subs} for sha, text, subs in cur.fetchall()}
    run_id = llm.run(LETTER_TASK, items)
    rows = [(sha, i, use["disease"], use["indication_as_written"], use["qualifiers"], use["change_type"],
             use["accelerated_approval"], decision_id)
            for sha, decision_id, out in llm.decisions(run_id) for i, use in enumerate(out["approved_uses"])]
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.fda_approved_use")
        execute_values(cur, """INSERT INTO preclin.fda_approved_use
            (letter_sha256, ordinal, disease, indication_as_written, qualifiers, change_type,
             accelerated_approval, llm_decision_id) VALUES %s""", rows)
        conn.commit()
    print(f"run={run_id} approved_uses={len(rows)}")


INGREDIENT_SYSTEM = """You resolve the active ingredients of an FDA-approved product to molecular entities.

Return every active entity in the product. For each give its international nonproprietary name (INN) or USAN in lower case (e.g. "metformin", "insulin glargine", "trastuzumab deruxtecan", "axicabtagene ciloleucel"), with salts, esters used only as salt forms, hydrates, strengths and formulations stripped ("METFORMIN HYDROCHLORIDE" -> "metformin", "ATAZANAVIR SULFATE" -> "atazanavir"). Keep a prodrug or ester that has its own INN as that INN (e.g. "tenofovir alafenamide", "valacyclovir").

For a biologic with a four-letter FDA suffix, use the core name without the suffix and say whether the product is a biosimilar or interchangeable biosimilar of an earlier reference product (biosimilar_of = the reference product's core name), or the originator (biosimilar_of = null). Mixtures without a single defined entity (e.g. allergenic extracts, plasma pools, multivitamins) use kind = mixture with the components you can name."""

INGREDIENT_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["single", "combination", "mixture"]},
        "components": {"type": "array", "items": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "biosimilar_of": {"type": ["string", "null"]}},
            "required": ["name", "biosimilar_of"], "additionalProperties": False}},
    },
    "required": ["kind", "components"],
    "additionalProperties": False,
}


def render_ingredient(p: dict) -> str:
    return (f"{p['appl_type']} {p['appl_no']} (sponsor: {p['sponsor']})\nBrand names: {', '.join(p['brands'])}\n"
            f"Active ingredient field(s): {' | '.join(p['ingredients'])}")


INGREDIENT_TASK = llm.Task(
    name="fda_application_moiety", prompt_version="v1", schema_version="v1",
    system=INGREDIENT_SYSTEM, schema=INGREDIENT_SCHEMA, render=render_ingredient,
    subject_type="fda_application", model="claude-opus-5-5", effort="low", max_tokens=2000)


PRODUCT_SYSTEM = """You match an FDA-approved product to the molecular entities that clinical trials registered it under.

The application's own ingredient names did not match any entity seen in trials: vaccines, cell and gene therapies, blood products and some biologics are named differently in trial records (a code name, a descriptive name such as "recombinant zoster vaccine (gE, adjuvanted)", or an antigen list) than on the FDA application ("Zoster Vaccine Recombinant, Adjuvanted", brand SHINGRIX).

From the candidate trial entities, list every one that is this approved product or the same product under development (the same vaccine with the same antigens and valency, the same cell or gene therapy, the same biologic), including its development code names. Leave out related but different products: another valency or strain composition, a different adjuvant, a competitor's vaccine against the same pathogen, an earlier or later generation. Return an empty list when none is the same product."""

PRODUCT_SCHEMA = {
    "type": "object",
    "properties": {"same_product": {"type": "array", "items": {"type": "integer"}},
                   "rationale": {"type": "string"}},
    "required": ["same_product", "rationale"],
    "additionalProperties": False,
}
PRODUCT_CANDIDATES = 15


def render_product(p: dict) -> str:
    cands = "\n".join(f"- {c['moiety_id']}: {c['name']}" + (f" (also: {'; '.join(c['other_names'])})" if c["other_names"] else "")
                       + (f" | trial: {c['trial']}" if c["trial"] else "") for c in p["candidates"])
    return (f"FDA {p['appl_type']} {p['appl_no']} ({p['center']}), sponsor {p['sponsor']}\n"
            f"Brand names: {', '.join(p['brands']) or '-'}\nProper names / ingredients: {', '.join(p['ingredients']) or '-'}\n"
            f"Approved uses: {p['uses'] or '-'}\n\nCandidate trial entities:\n{cands}")


def validate_product(p: dict, out: dict) -> None:
    extra = set(out["same_product"]) - {c["moiety_id"] for c in p["candidates"]}
    if extra:
        raise ValueError(f"not candidates: {sorted(extra)}")


PRODUCT_TASK = llm.Task(name="fda_application_trial_entity", prompt_version="v1", schema_version="v1",
                        system=PRODUCT_SYSTEM, schema=PRODUCT_SCHEMA, render=render_product,
                        validate=validate_product, subject_type="fda_application", model="claude-opus-5-5",
                        effort="medium", max_tokens=2000)


def match_products(cur, apps: dict) -> list[tuple]:
    """Links (appl_no, moiety_id, decision) from applications none of whose
    entities appears in a trial to the trial entities that are the same product."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.neighbors import NearestNeighbors
    cur.execute("""SELECT m.moiety_id, m.name, m.code_names || m.aliases,
                          (SELECT c.brief_title FROM preclin.drug_moiety dm JOIN preclin.ctgov_study_drug sd USING (drug_id)
                           JOIN preclin.ctgov_study c USING (nct_id) WHERE dm.moiety_id = m.moiety_id LIMIT 1)
                   FROM preclin.moiety m
                   WHERE EXISTS (SELECT 1 FROM preclin.drug_moiety dm JOIN preclin.ctgov_study_drug sd USING (drug_id)
                                 WHERE dm.moiety_id = m.moiety_id)""")
    entities = cur.fetchall()
    in_trials = {e[0] for e in entities}
    cur.execute("SELECT appl_no, array_agg(moiety_id) FROM preclin.fda_application_moiety GROUP BY 1")
    linked = dict(cur.fetchall())
    todo = [a for a in apps if not set(linked.get(a, [])) & in_trials]
    if not todo:
        return []
    texts = [" ".join([name, *others]).lower() for _, name, others, _ in entities]
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 4), sublinear_tf=True)
    nn = NearestNeighbors(n_neighbors=PRODUCT_CANDIDATES, metric="cosine").fit(vec.fit_transform(texts))
    queries = [" ".join(apps[a]["brands"] + apps[a]["ingredients"]).lower() for a in todo]
    _, idx = nn.kneighbors(vec.transform(queries))
    cur.execute("""SELECT sl.appl_no, string_agg(DISTINCT u.indication_as_written, '; ')
                   FROM preclin.fda_submission_letter sl JOIN preclin.fda_approved_use u USING (letter_sha256)
                   WHERE sl.appl_no = ANY(%s) GROUP BY 1""", (todo,))
    uses = dict(cur.fetchall())
    items = {}
    for a, row in zip(todo, idx):
        items[a] = {**apps[a], "uses": (uses.get(a) or "")[:1500],
                    "candidates": [{"moiety_id": entities[i][0], "name": entities[i][1],
                                    "other_names": sorted(set(entities[i][2]))[:6], "trial": entities[i][3]}
                                   for i in row]}
    run_id = llm.run(PRODUCT_TASK, items)
    return [(a, mid, did) for a, did, out in llm.decisions(run_id) for mid in out["same_product"]]


def link(_args) -> None:
    from pipeline.drugs import entity_ids, moiety_key
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT substr(a, 4), array_agg(DISTINCT b), array_agg(DISTINCT g)
            FROM preclin.fda_label l, unnest(l.application_numbers) a,
                 unnest(l.brand_names) b, unnest(l.generic_names) g
            GROUP BY 1""")
        label_names = {appl: (brands, generics) for appl, brands, generics in cur.fetchall()}
        cur.execute("""
            SELECT a.appl_no, a.appl_type, a.center, coalesce(a.sponsor_name, ''),
                   coalesce(array_agg(DISTINCT p.drug_name) FILTER (WHERE p.drug_name IS NOT NULL), '{}'),
                   coalesce(array_agg(DISTINCT p.active_ingredient)
                            FILTER (WHERE p.active_ingredient IS NOT NULL), '{}')
            FROM preclin.fda_application a LEFT JOIN preclin.fda_product p USING (appl_no)
            GROUP BY a.appl_no, a.appl_type, a.center, a.sponsor_name""")
        items = {}
        centers = {}
        for appl_no, appl_type, center, sponsor, brands, ingredients in cur.fetchall():
            lb, lg = label_names.get(appl_no, ([], []))
            centers[appl_no] = center
            items[appl_no] = {"appl_no": appl_no, "appl_type": appl_type, "sponsor": sponsor,
                              "brands": sorted(set(brands) | set(lb)),
                              "ingredients": sorted(set(ingredients) | set(lg))}
    run_id = llm.run(INGREDIENT_TASK, items)
    links, names = [], {}
    for appl_no, decision_id, out in llm.decisions(run_id):
        for comp in out["components"]:
            key = moiety_key(comp["name"])
            if key:
                names.setdefault(key, comp["name"])
                links.append((appl_no, key, comp["biosimilar_of"], decision_id))
    with llm.connect() as conn, conn.cursor() as cur:
        ids = entity_ids(cur, names)
        cur.execute("DELETE FROM preclin.fda_application_moiety")
        execute_values(cur, """INSERT INTO preclin.fda_application_moiety
              (appl_no, moiety_id, biosimilar_of, llm_decision_id) VALUES %s ON CONFLICT DO NOTHING""",
                       [(appl, ids[k], bio, did) for appl, k, bio, did in links])
        products = match_products(cur, {a: {**it, "center": centers[a]} for a, it in items.items()})
        if products:
            execute_values(cur, """INSERT INTO preclin.fda_application_moiety (appl_no, moiety_id, llm_decision_id)
                                   VALUES %s ON CONFLICT DO NOTHING""", products)
        conn.commit()
    print(f"applications={len(items)} links={len(links)} moieties={len(names)} product matches={len(products)}")


def load_cber(_args) -> None:
    path = os.path.join(llm.REPO, ".cache", "cber", "letters_index.jsonl")
    records = [json.loads(line) for line in open(path)]
    sha = llm.sha256_file(path)
    apps, products, subs, letters, links = {}, set(), {}, {}, {}
    for r in records:
        appl = r["appl_no"]
        apps.setdefault(appl, r.get("sponsor"))
        products.add((appl, r.get("product_brand") or "", r.get("proper_name") or r.get("product_brand") or ""))
        key = (appl, r["submission_type"], str(r["submission_no"]))
        subs[key] = r["approval_date"]
        pdf = os.path.join(llm.REPO, ".cache", "cber", "letters", f"{r['sha256']}.pdf") if r.get("sha256") else ""
        text = pdf_text(pdf) if os.path.exists(pdf) else (r.get("text") or r.get("yearly_listing_text") or "")
        if not text.strip():
            continue
        doc_sha = r.get("sha256") or hashlib.sha256(text.encode()).hexdigest()
        letters[doc_sha] = (doc_sha, text.replace("\x00", ""), int(r.get("n_bytes") or len(text.encode())))
        links[key + (r["url"],)] = (*key, r["url"], r.get("doc_date") or None, doc_sha, r.get("error"))
    with llm.connect() as conn, conn.cursor() as cur:
        release = llm.register_release(cur, "fda_cber_approvals", records and max(r["approval_date"] for r in records),
                                       "https://www.fda.gov/vaccines-blood-biologics/development-approval-process-cber/"
                                       "biological-approvals-year", sha, {"n_records": len(records)})
        execute_values(cur, """INSERT INTO preclin.fda_application (appl_no, appl_type, center, sponsor_name,
                                 source_release_id) VALUES %s
            ON CONFLICT (appl_no) DO UPDATE SET center = 'CBER', sponsor_name = EXCLUDED.sponsor_name,
              source_release_id = EXCLUDED.source_release_id""",
                       [(a, "BLA", "CBER", sp, release) for a, sp in apps.items()])
        execute_values(cur, """INSERT INTO preclin.fda_product (appl_no, product_no, drug_name, active_ingredient)
            VALUES %s ON CONFLICT (appl_no, product_no) DO UPDATE SET drug_name = EXCLUDED.drug_name,
              active_ingredient = EXCLUDED.active_ingredient""",
                       [(a, f"cber{i}", brand, proper) for i, (a, brand, proper) in enumerate(sorted(products))])
        execute_values(cur, """INSERT INTO preclin.fda_submission (appl_no, submission_type, submission_no, status,
                                 status_date, submission_class) VALUES %s
            ON CONFLICT (appl_no, submission_type, submission_no) DO UPDATE SET status_date = EXCLUDED.status_date""",
                       [(*k, "AP", d, "CBER") for k, d in subs.items()])
        write_letters(cur, list(letters.values()), list(links.values()))
        conn.commit()
    print(f"CBER applications={len(apps)} submissions={len(subs)} documents={len(letters)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in [("fetch", fetch), ("load", load), ("extract", extract), ("link", link),
                     ("load-cber", load_cber)]:
        sub.add_parser(name).set_defaults(fn=fn)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
