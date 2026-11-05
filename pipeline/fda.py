"""FDA approval sources -> preclin.fda_* tables.

    python -m pipeline.fda fetch     # Drugs@FDA, openFDA labels, approval letters -> .cache/fda
    python -m pipeline.fda load      # cached files -> preclin.fda_application/_product/_submission/_letter/_label
    python -m pipeline.fda extract   # LLM: approved uses stated in each letter -> preclin.fda_approved_use
    python -m pipeline.fda link      # LLM: each application's principal active ingredients -> preclin.moiety;
                                     #   then each Phase 3 entity still unlinked -> its application (web search)
    python -m pipeline.fda load-cber # CBER approvals (.cache/cber/letters_index*.jsonl) -> preclin.fda_*
    python -m pipeline.fda unlisted  # applications link named that no FDA list carries -> their FDA letters

CBER-regulated biologics (vaccines, blood and plasma products, cell and gene
therapies) are not in Drugs@FDA; their original approvals and supplements come
from CBER's yearly approval pages and product approval-history pages. An
action listed without a retrievable letter keeps the listing text as its
document.

Letters cover every approved original NDA/BLA and every approved efficacy
supplement (Drugs@FDA submission class EFFICACY) from 2008-01-01 (LETTERS_FROM) through the
Drugs@FDA data date, so programs that entered a phase from 2008 on are dated
against the letter that approved them. An efficacy supplement Drugs@FDA posts
no letter for is read from the label posted for it, else from its review
(action_documents); `extract` reads those with their own prompt. CBER letters
start in 2015 (pipeline.cber).
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import zipfile
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

import requests
from psycopg2.extras import execute_values
from pypdf import PdfReader

from pipeline import llm
from pipeline.drugs import entity_ids, moiety_key

CACHE = os.path.join(llm.REPO, ".cache", "fda")
DRUGSFDA_URL = "https://www.fda.gov/media/89850/download"
OPENFDA_INDEX = "https://api.fda.gov/download.json"
LETTERS_FROM = "2008-01-01"  # earliest approval action whose letter is read
WINDOW = (LETTERS_FROM, "2026-12-31")
EFFICACY_CLASS = "2"
DOC_TYPES = {"1": "letter", "2": "label", "3": "review", "21": "review"}  # Drugs@FDA ApplicationDocsTypeID
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
    # The cached label files are one export: a new export replaces every file, and the index naming the
    # export is written only once all of its files are in place.
    index_path = os.path.join(CACHE, "openfda", "label_index.json")
    index = requests.get(OPENFDA_INDEX, timeout=60).json()["results"]["drug"]["label"]
    cached = json.load(open(index_path))["export_date"] if os.path.exists(index_path) else None
    for part in index["partitions"]:
        dest = os.path.join(CACHE, "openfda", os.path.basename(part["file"]))
        if cached != index["export_date"] or not os.path.exists(dest):
            with open(dest + ".part", "wb") as f:
                f.write(requests.get(part["file"], timeout=600).content)
            os.replace(dest + ".part", dest)
    json.dump(index, open(index_path, "w"))

    # Submissions in scope: approved ORIG submissions and efficacy-class supplements of NDA/BLA
    # applications inside WINDOW.
    apps = {r["ApplNo"] for r in read_tsv("Applications.txt") if r["ApplType"] in ("NDA", "BLA")}
    wanted = {(s["ApplNo"], s["SubmissionType"].strip(), s["SubmissionNo"]) for s in read_tsv("Submissions.txt")
              if s["SubmissionStatus"] == "AP" and WINDOW[0] <= s["SubmissionStatusDate"][:10] <= WINDOW[1]
              and s["ApplNo"] in apps
              and (s["SubmissionType"] == "ORIG" or s["SubmissionClassCodeID"] == EFFICACY_CLASS)}
    docs = action_documents(wanted, read_tsv("ApplicationDocs.txt"))
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
                   "doc_date": doc["ApplicationDocsDate"][:10], "doc_type": DOC_TYPES[doc["ApplicationDocsTypeID"]],
                   "error": err}
            if content:
                sha = hashlib.sha256(content).hexdigest()
                open(os.path.join(CACHE, "letters", f"{sha}.pdf"), "wb").write(content)
                rec.update(sha256=sha, n_bytes=len(content))
            out.write(json.dumps(rec) + "\n")
    print(f"letters fetched: {len(todo)}")


def action_documents(wanted: set[tuple], docs: list[dict[str, str]]) -> list[dict[str, str]]:
    """The documents that state what each wanted submission approved: its approval letters; for
    an efficacy supplement with no letter, the label PDFs posted for it, else its review PDFs."""
    by_sub: dict[tuple, dict[str, list]] = {}
    for d in docs:
        key = (d["ApplNo"], d["SubmissionType"].strip(), d["SubmissionNo"])
        kind = DOC_TYPES.get(d["ApplicationDocsTypeID"])
        if key in wanted and kind:
            by_sub.setdefault(key, {}).setdefault(kind, []).append(d)
    out = []
    for key, kinds in by_sub.items():
        if "letter" in kinds:
            out += kinds["letter"]
        elif key[1] == "SUPPL":
            pdfs = {k: [d for d in v if d["ApplicationDocsURL"].strip().split("#")[0].lower().endswith(".pdf")]
                    for k, v in kinds.items()}
            out += pdfs.get("label") or pdfs.get("review") or []
    return out


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
    """Document texts by sha256, then each submission's document links."""
    execute_values(cur, """INSERT INTO preclin.fda_letter (letter_sha256, letter_text, n_bytes)
        VALUES %s ON CONFLICT (letter_sha256) DO UPDATE SET letter_text = EXCLUDED.letter_text""", letters)
    execute_values(cur, """INSERT INTO preclin.fda_submission_letter
        (appl_no, submission_type, submission_no, url, doc_date, letter_sha256, fetch_error, doc_type) VALUES %s
        ON CONFLICT (appl_no, submission_type, submission_no, url) DO UPDATE SET
          letter_sha256 = EXCLUDED.letter_sha256, fetch_error = EXCLUDED.fetch_error,
          doc_type = EXCLUDED.doc_type""", links)


def load(_args) -> None:
    apps = {r["ApplNo"]: r for r in read_tsv("Applications.txt") if r["ApplType"] in ("NDA", "BLA")}
    zip_sha = llm.sha256_file(os.path.join(CACHE, "drugsfda.zip"))
    data_date = max(r["SubmissionStatusDate"][:10] for r in read_tsv("Submissions.txt"))
    label_index = json.load(open(os.path.join(CACHE, "openfda", "label_index.json")))
    label_files = sorted(glob.glob(os.path.join(CACHE, "openfda", "drug-label-*.json.zip")))
    label_sha = hashlib.sha256("".join(llm.sha256_file(p) for p in label_files).encode()).hexdigest()

    # Document texts are read (and OCRed) before the connection opens, which would otherwise sit idle.
    sizes, links = {}, {}
    for line in open(os.path.join(CACHE, "letters_index.jsonl")):
        r = json.loads(line)
        if r.get("sha256"):
            sizes[r["sha256"]] = r["n_bytes"]
        key = (r["appl_no"], r["submission_type"], r["submission_no"], r["url"])
        if r.get("sha256") or key not in links:  # a successful fetch supersedes a failed one
            links[key] = (*key, r.get("doc_date") or None, r.get("sha256"), r.get("error"),
                          r.get("doc_type", "letter"))
    links = list(links.values())
    with ProcessPoolExecutor() as pool:
        texts = pool.map(pdf_text, [os.path.join(CACHE, "letters", f"{sha}.pdf") for sha in sizes], chunksize=20)
        letters = [(sha, text, n) for (sha, n), text in zip(sizes.items(), texts)]

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


USE_RULES = """- One entry per distinct disease/population combination approved.
- disease: the disease or condition in plain standard medical terms (e.g. "non-small cell lung cancer", "type 2 diabetes mellitus", "chronic plaque psoriasis"), without population qualifiers.
- qualifiers: the population restrictions stated (age group, line of therapy, prior treatment, biomarker/mutation, disease stage/severity, combination partner drugs, setting such as adjuvant/neoadjuvant/maintenance).
- change_type:
  new_indication = a disease/condition not previously on the label for this product;
  new_population = same disease, newly approved population (e.g. pediatric extension, new line of therapy, new biomarker subgroup, new stage/setting such as adjuvant);
  new_regimen = new dose, schedule, formulation-related use, or combination partner within an already-approved population;
  conversion_to_full = accelerated approval converted to regular approval / confirmatory data;
  efficacy_labeling = efficacy data added to labeling (e.g. new clinical study results, new endpoint) without a new population;
  original_approval = first approval of this application (ORIG submissions);
  other."""

LETTER_SYSTEM = f"""You read U.S. FDA approval letters (NDA/BLA original approvals and efficacy supplements) and record exactly what use was approved by THIS action.

Rules:
- Report only uses that this letter approves or changes. Do not list the drug's previously approved indications unless the letter re-states them as part of this action.
- If the letter only says the supplement "provides for revisions to the labeling" without naming a disease or population, set letter_states_use=false and leave approved_uses empty.
{USE_RULES}
- If uncertain whether the disease was already on the label, use your best judgment from the letter text and say so in notes."""

SUPPLEMENT_DOC_SYSTEM = f"""You read the labeling or review that the U.S. FDA posted for an efficacy supplement to an NDA/BLA that has no approval letter, and record exactly what use was approved by THIS supplement.

Rules:
- A label states every indication of the product, including those approved before this supplement. Report only uses this supplement added or changed. The Recent Major Changes list in the label's Highlights names the sections the supplement changed, each with a month and year; an Indications and Usage change dated at or just before the supplement's action date is this supplement's, and the indication it names in the Indications and Usage section is the use. A review states the indication the supplement proposed and whether it was approved.
- If the document does not show which use this supplement approved (no Indications and Usage change dated at the action date, a label without Recent Major Changes, or only dosage, safety or study-result changes), set letter_states_use=false (here: whether the document states the supplement's use) and leave approved_uses empty.
{USE_RULES}
- Say in notes which part of the document shows the use."""

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
    effort="medium", max_tokens=32000)


def render_supplement_doc(p: dict) -> str:
    subs = "; ".join(f"{s['appl_type']} {s['appl_no']} {s['submission_type']}-{s['submission_no']} "
                     f"approved {s['approval_date']}" for s in p["submissions"])
    return f"Efficacy supplement with no approval letter: {subs}\n\n{p['document'].capitalize()} text:\n{p['text']}"


SUPPLEMENT_DOC_TASK = llm.Task(
    name="fda_supplement_document_approved_uses", prompt_version="v1", schema_version="v1",
    system=SUPPLEMENT_DOC_SYSTEM, schema=LETTER_SCHEMA, render=render_supplement_doc, subject_type="fda_letter",
    effort="medium", max_tokens=32000)


def extract(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT l.letter_sha256, l.letter_text, sl.doc_type,
                   json_agg(json_build_object('appl_no', a.appl_no, 'appl_type', a.appl_type,
                            'submission_type', s.submission_type, 'submission_no', s.submission_no,
                            'approval_date', s.status_date) ORDER BY a.appl_no, s.submission_no)
            FROM preclin.fda_letter l
            JOIN preclin.fda_submission_letter sl USING (letter_sha256)
            JOIN preclin.fda_submission s USING (appl_no, submission_type, submission_no)
            JOIN preclin.fda_application a USING (appl_no)
            GROUP BY l.letter_sha256, l.letter_text, sl.doc_type""")
        letters, documents = {}, {}
        for sha, text, doc_type, subs in cur.fetchall():
            if doc_type == "letter":
                letters[sha] = {"text": text[:150000], "submissions": subs}
            else:
                documents[sha] = {"text": text[:150000], "document": doc_type, "submissions": subs}
    run_ids = [llm.run(LETTER_TASK, letters), llm.run(SUPPLEMENT_DOC_TASK, documents)]
    rows = [(sha, i, use["disease"], use["indication_as_written"], use["qualifiers"], use["change_type"],
             use["accelerated_approval"], decision_id)
            for run_id in run_ids for sha, decision_id, out in llm.decisions(run_id)
            for i, use in enumerate(out["approved_uses"])]
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.fda_approved_use")
        execute_values(cur, """INSERT INTO preclin.fda_approved_use
            (letter_sha256, ordinal, disease, indication_as_written, qualifiers, change_type,
             accelerated_approval, llm_decision_id) VALUES %s""", rows)
        conn.commit()
    print(f"runs={run_ids} letters={len(letters)} supplement documents={len(documents)} approved_uses={len(rows)}")


INGREDIENT_SYSTEM = """You resolve the active ingredients of an FDA-approved product to molecular entities.

Return every ingredient listed as active in the product. For each give its international nonproprietary name (INN) or USAN in lower case (e.g. "metformin", "insulin glargine", "trastuzumab deruxtecan", "axicabtagene ciloleucel"), with salts, counter-ions, esters used only as salt forms, hydrates, strengths and formulations stripped ("METFORMIN HYDROCHLORIDE" -> "metformin", "ATAZANAVIR SULFATE" -> "atazanavir", "SODIUM PICOSULFATE" -> "picosulfate"). Keep a prodrug or ester that has its own INN as that INN (e.g. "tenofovir alafenamide", "valacyclovir"). An inorganic salt that is itself the active ingredient keeps its name ("sodium bicarbonate", "magnesium oxide").

Give each ingredient a role:
- principal: an ingredient the product is given for, whose effect is the product's use (in a bowel preparation, its laxatives; in an electrolyte replacement or oral rehydration product, the electrolytes themselves).
- electrolyte_or_vehicle: an electrolyte, buffer, osmotic agent or diluent that the label lists as active only because it makes up the solution around a principal ingredient (the sodium, calcium and magnesium salts of a peritoneal dialysis solution built on icodextrin or dextrose; the electrolytes added to a polyethylene glycol bowel preparation).

For a biologic with a four-letter FDA suffix, use the core name without the suffix and say whether the product is a biosimilar or interchangeable biosimilar of an earlier reference product (biosimilar_of = the reference product's core name), or the originator (biosimilar_of = null). Mixtures without a single defined entity (e.g. allergenic extracts, plasma pools, multivitamins) use kind = mixture with the components you can name."""

INGREDIENT_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["single", "combination", "mixture"]},
        "components": {"type": "array", "items": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "biosimilar_of": {"type": ["string", "null"]},
                           "role": {"type": "string", "enum": ["principal", "electrolyte_or_vehicle"]}},
            "required": ["name", "biosimilar_of", "role"], "additionalProperties": False}},
    },
    "required": ["kind", "components"],
    "additionalProperties": False,
}


def render_ingredient(p: dict) -> str:
    return (f"{p['appl_type']} {p['appl_no']} (sponsor: {p['sponsor']})\nBrand names: {', '.join(p['brands'])}\n"
            f"Active ingredient field(s): {' | '.join(p['ingredients'])}")


def principals(out: dict) -> list[dict]:
    """The components an application links to: its principal ingredients, a biosimilar named by
    its reference product."""
    comps = [{**c, "name": c["biosimilar_of"] or c["name"]} for c in out["components"] if c["role"] == "principal"]
    return [c for c in comps if moiety_key(c["name"])]


INGREDIENT_TASK = llm.Task(
    name="fda_application_moiety", prompt_version="v2", schema_version="v2",
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


def match_products(apps: dict, linked: dict[str, set[int]]) -> list[tuple]:
    """Links (appl_no, moiety_id, decision) from applications none of whose entities (linked: appl_no ->
    moiety_ids) appears in a trial to the trial entities that are the same product."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.neighbors import NearestNeighbors
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT m.moiety_id, m.name, m.code_names || m.aliases,
                          (SELECT c.brief_title FROM preclin.drug_moiety dm JOIN preclin.ctgov_study_drug sd USING (drug_id)
                           JOIN preclin.ctgov_study c USING (nct_id) WHERE dm.moiety_id = m.moiety_id
                           ORDER BY c.start_date DESC NULLS LAST, c.nct_id LIMIT 1)
                   FROM preclin.moiety m
                   WHERE EXISTS (SELECT 1 FROM preclin.drug_moiety dm JOIN preclin.ctgov_study_drug sd USING (drug_id)
                                 WHERE dm.moiety_id = m.moiety_id)""")
        entities = cur.fetchall()
        in_trials = {e[0] for e in entities}
        todo = [a for a in apps if not linked.get(a, set()) & in_trials]
        if not todo:
            return []
        cur.execute("""SELECT sl.appl_no, string_agg(DISTINCT u.indication_as_written, '; ')
                       FROM preclin.fda_submission_letter sl JOIN preclin.fda_approved_use u USING (letter_sha256)
                       WHERE sl.appl_no = ANY(%s) GROUP BY 1""", (todo,))
        uses = dict(cur.fetchall())
    texts = [" ".join([name, *others]).lower() for _, name, others, _ in entities]
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 4), sublinear_tf=True)
    nn = NearestNeighbors(n_neighbors=PRODUCT_CANDIDATES, metric="cosine").fit(vec.fit_transform(texts))
    queries = [" ".join(apps[a]["brands"] + apps[a]["ingredients"]).lower() for a in todo]
    _, idx = nn.kneighbors(vec.transform(queries))
    items = {}
    for a, row in zip(todo, idx):
        items[a] = {**apps[a], "uses": (uses.get(a) or "")[:1500],
                    "candidates": [{"moiety_id": entities[i][0], "name": entities[i][1],
                                    "other_names": sorted(set(entities[i][2]))[:6], "trial": entities[i][3]}
                                   for i in row]}
    run_id = llm.run(PRODUCT_TASK, items)
    return [(a, mid, did) for a, did, out in llm.decisions(run_id) for mid in out["same_product"]]


TRIAL_ENTITY_SYSTEM = """You find out whether a drug from clinical trials was approved by the U.S. FDA, under any name.

The entity was resolved from ClinicalTrials.gov intervention names, so its name may be a sponsor code, a descriptive name or a brand rather than the name on the FDA application. Search the web (Drugs@FDA, FDA approval letters and announcements, DailyMed, the Purple Book, company releases) for an approved NDA or BLA whose active ingredient is this same entity: the same active moiety in any salt or formulation, or the same biologic, vaccine, cell or gene therapy. A different molecule on the same target, a biosimilar of it, another strain composition, a successor product, a device, or a combination product of which this entity is only one part does not count. An approval for any disease counts. Search before answering, and use at most a handful of searches.

applications: each such NDA or BLA with appl_type, appl_no (the application number's digits only, e.g. 204153), brand and approval_year; empty when there is none. sources: URLs your searches returned that show each application. rationale: at most 60 words."""
TRIAL_ENTITY_SCHEMA = {
    "type": "object",
    "properties": {
        "applications": {"type": "array", "items": {
            "type": "object",
            "properties": {"appl_type": {"type": "string", "enum": ["NDA", "BLA"]}, "appl_no": {"type": "string"},
                           "brand": {"type": "string"}, "approval_year": {"type": ["integer", "null"]}},
            "required": ["appl_type", "appl_no", "brand", "approval_year"], "additionalProperties": False}},
        "sources": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": ["applications", "sources", "rationale"],
    "additionalProperties": False,
}


def render_trial_entity(p: dict) -> str:
    return (f"Entity: {p['name']}\nOther names and codes: {', '.join(p['other_names']) or '-'}\n"
            f"Modality: {p['modality']}\nSponsors: {', '.join(p['sponsors']) or '-'}\n"
            f"Diseases it reached Phase 3 in: {', '.join(p['diseases']) or '-'}\nA trial: {p['trial'] or '-'}")


def validate_trial_entity(p: dict, out: dict) -> None:
    bad = [a["appl_no"] for a in out["applications"] if not re.fullmatch(r"\d{5,6}", a["appl_no"])]
    if bad:
        raise ValueError(f"application numbers are not 5-6 digits: {bad}")
    if out["applications"] and not out["sources"]:
        raise ValueError("applications without a source")
    if not out.get("retrieved_urls"):
        raise ValueError("no search returned anything, so no answer either way")
    retrieved = {llm.norm_url(u) for u in out.get("retrieved_urls", [])}
    unknown = [u for u in out["sources"] if llm.norm_url(u) not in retrieved]
    if unknown:
        raise ValueError(f"cites sources it did not retrieve: {unknown[:3]}")


TRIAL_ENTITY_TASK = llm.Task(
    name="trial_entity_fda_application", prompt_version="v2", schema_version="v1", system=TRIAL_ENTITY_SYSTEM,
    schema=TRIAL_ENTITY_SCHEMA, render=render_trial_entity, validate=validate_trial_entity,
    subject_type="moiety", model="claude-sonnet-5", effort="medium", max_tokens=16000,
    tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 5},
           {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 2}])


def trial_entity_items(cur, linked: set[int]) -> dict[str, dict]:
    """Every entity with a Phase 3 program that is not the sole ingredient of an FDA application (linked)."""
    cur.execute("""
        SELECT m.moiety_id, m.name, m.code_names || m.aliases, coalesce(m.modality, 'unknown'),
               array_agg(DISTINCT o.label) FILTER (WHERE p.highest_phase >= 3 AND o.label IS NOT NULL),
               (SELECT array_agg(DISTINCT s.lead_sponsor) FROM preclin.dev_program_trial dt
                JOIN preclin.dev_program p2 USING (program_id) JOIN preclin.ctgov_study s USING (nct_id)
                WHERE p2.moiety_id = m.moiety_id AND s.lead_sponsor IS NOT NULL),
               (SELECT s.brief_title FROM preclin.dev_program_trial dt JOIN preclin.dev_program p2 USING (program_id)
                JOIN preclin.ctgov_study s USING (nct_id) WHERE p2.moiety_id = m.moiety_id
                ORDER BY dt.phase DESC, s.start_date DESC NULLS LAST, s.nct_id LIMIT 1)
        FROM preclin.moiety m JOIN preclin.dev_program p USING (moiety_id)
        LEFT JOIN preclin.ontology_term o ON o.term_id = p.mondo_id
        GROUP BY m.moiety_id HAVING max(p.highest_phase) >= 3""")
    return {str(mid): {"name": name, "other_names": sorted(set(others))[:8], "modality": modality,
                       "diseases": sorted(diseases or [])[:6], "sponsors": sorted(sponsors or [])[:5], "trial": trial}
            for mid, name, others, modality, diseases, sponsors, trial in cur.fetchall() if mid not in linked}


def match_trial_entities(linked: set[int]) -> tuple[list[tuple], int]:
    """Links (appl_no, moiety_id, decision) from each entity with a Phase 3 program that is not the sole ingredient of
    an application (linked: the moiety_ids that are) to the applications the web shows are the same product, kept only where the
    application is in preclin.fda_application; and how many named applications are not there."""
    with llm.connect() as conn, conn.cursor() as cur:
        items = trial_entity_items(cur, linked)
        cur.execute("SELECT appl_no FROM preclin.fda_application")
        known = {a for (a,) in cur.fetchall()}
    run_id = llm.run(TRIAL_ENTITY_TASK, items)
    named = [(a["appl_no"].zfill(6), int(mid), did) for mid, did, out in llm.decisions(run_id)
             for a in out["applications"]]
    return [n for n in named if n[0] in known], sum(n[0] not in known for n in named)


def link(_args) -> None:
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
        for comp in principals(out):
            key = moiety_key(comp["name"])
            names.setdefault(key, comp["name"])
            links.append((appl_no, key, comp["biosimilar_of"], decision_id))
    with llm.connect() as conn, conn.cursor() as cur:
        ids = entity_ids(cur, names)  # an ingredient no entity carries yet becomes one
        conn.commit()
    rows = [(appl, ids[k], bio, did) for appl, k, bio, did in links]
    linked = defaultdict(set)
    for appl, mid, *_ in rows:
        linked[appl].add(mid)
    # The matching passes run LLM calls for minutes; no transaction is held open across them.
    products = match_products({a: {**it, "center": centers[a]} for a, it in items.items()}, linked)
    # Searched too: an entity linked only by a product match (which chooses among name-similar candidates and can
    # drop a product when they shift) or only as one ingredient of combinations (its own approval is not among them).
    trial_entities, unlisted = match_trial_entities({m for ms in linked.values() if len(ms) == 1 for m in ms})
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM preclin.fda_application_moiety")
        execute_values(cur, """INSERT INTO preclin.fda_application_moiety
              (appl_no, moiety_id, biosimilar_of, llm_decision_id) VALUES %s ON CONFLICT DO NOTHING""", rows)
        for found in (products, trial_entities):
            if found:
                execute_values(cur, """INSERT INTO preclin.fda_application_moiety (appl_no, moiety_id, llm_decision_id)
                                       VALUES %s ON CONFLICT DO NOTHING""", found)
        conn.commit()
    print(f"applications={len(items)} links={len(links)} moieties={len(names)} product matches={len(products)} "
          f"trial-entity matches={len(trial_entities)} (named applications not in preclin.fda_application: {unlisted})")


CBER_INDEXES = {  # file in .cache/cber -> (release name, product_no prefix, whether it overrides an application
    # already loaded): 2015-2025 owns an application it lists; the other years only add the ones they alone list
    "letters_index.jsonl": ("fda_cber_approvals", "cber", True),  # pipeline.cber
    "letters_index_other.jsonl": ("fda_cber_approvals_other_years", "cbo", False),  # pipeline.cber.other_years
}


def load_cber(_args) -> None:
    """Load every CBER index present; each file is its own release, and its product numbers carry its own prefix
    so that loading one file never overwrites products another loaded."""
    for name, (release_name, prefix, owns) in CBER_INDEXES.items():
        path = os.path.join(llm.REPO, ".cache", "cber", name)
        if os.path.exists(path):
            load_cber_index(path, release_name, prefix, owns)


def load_cber_index(path: str, release_name: str, prefix: str, owns: bool) -> None:
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
        links[key + (r["url"],)] = (*key, r["url"], r.get("doc_date") or None, doc_sha, r.get("error"), "letter")
    with llm.connect() as conn, conn.cursor() as cur:
        release = llm.register_release(cur, release_name, records and max(r["approval_date"] for r in records),
                                       "https://www.fda.gov/vaccines-blood-biologics/development-approval-process-cber/"
                                       "biological-approvals-year", sha, {"n_records": len(records)})
        execute_values(cur, """INSERT INTO preclin.fda_application (appl_no, appl_type, center, sponsor_name,
                                 source_release_id) VALUES %s
            ON CONFLICT (appl_no) DO """ + ("""UPDATE SET center = 'CBER', sponsor_name = EXCLUDED.sponsor_name,
              source_release_id = EXCLUDED.source_release_id""" if owns else "NOTHING"),
                       [(a, "BLA", "CBER", sp, release) for a, sp in apps.items()])
        execute_values(cur, """INSERT INTO preclin.fda_product (appl_no, product_no, drug_name, active_ingredient)
            VALUES %s ON CONFLICT (appl_no, product_no) DO UPDATE SET drug_name = EXCLUDED.drug_name,
              active_ingredient = EXCLUDED.active_ingredient""",
                       [(a, f"{prefix}{i}", brand, proper) for i, (a, brand, proper) in enumerate(sorted(products))])
        execute_values(cur, """INSERT INTO preclin.fda_submission (appl_no, submission_type, submission_no, status,
                                 status_date, submission_class) VALUES %s
            ON CONFLICT (appl_no, submission_type, submission_no) DO UPDATE SET status_date = EXCLUDED.status_date""",
                       [(*k, "AP", d, "CBER") for k, d in subs.items()])
        write_letters(cur, list(letters.values()), list(links.values()))
        conn.commit()
    print(f"{os.path.basename(path)}: CBER applications={len(apps)} submissions={len(subs)} documents={len(letters)}")


UNLISTED_LETTER = "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/{year}/{appl}Orig1s000ltr.pdf"
SIGNED = re.compile(r"/s/\s*[A-Z][A-Z .,'-]+?\s+(\d{2})/(\d{2})/(\d{4})")  # a CDER letter's e-signature and its date


def signed_on(text: str) -> str | None:
    """The date of a CDER letter: its last electronic signature (the letterhead carries none)."""
    m = list(SIGNED.finditer(re.sub(r"\s+", " ", text)))
    return f"{m[-1].group(3)}-{m[-1].group(1)}-{m[-1].group(2)}" if m else None


def unlisted_letter(appl: str, year: int) -> tuple[str, str] | None:
    """(url, text) of the original approval letter FDA hosts for an application, looked for in its approval
    year and the years either side; None when there is none."""
    os.makedirs(os.path.join(CACHE, "unlisted"), exist_ok=True)
    for y in (year, year + 1, year - 1):
        url = UNLISTED_LETTER.format(year=y, appl=appl)
        path = os.path.join(CACHE, "unlisted", f"{appl}_{y}.pdf")
        if not os.path.exists(path):
            r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200 or not r.content.startswith(b"%PDF"):
                continue
            with open(path, "wb") as f:
                f.write(r.content)
        return url, pdf_text(path)
    return None


def unlisted(_args) -> None:
    """Applications the trial-entity pass named that no FDA list carries (Drugs@FDA drops some withdrawn
    products, e.g. Belviq and Pepaxto): each is added from the original approval letter FDA still hosts,
    dated by the letter's e-signature, its product named by the brand and the proper name the letter gives."""
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT lpad(x->>'appl_no', 6, '0'), x->>'appl_type', x->>'brand',
                              (x->>'approval_year')::int
                       FROM pv_evidence.llm_decision d, jsonb_array_elements(d.parsed_output->'applications') x
                       WHERE d.task = %s AND d.validation_status = 'validated'
                         AND (x->>'approval_year')::int >= %s
                         AND NOT EXISTS (SELECT 1 FROM preclin.fda_application a
                                         WHERE a.appl_no = lpad(x->>'appl_no', 6, '0'))""",
                    (TRIAL_ENTITY_TASK.name, int(LETTERS_FROM[:4])))
        named = cur.fetchall()
    found = {}
    for appl, appl_type, brand, year in named:
        got = unlisted_letter(appl, year)
        if got and appl not in found:
            url, text = got
            proper = re.search(rf"{re.escape(brand)}\s*(?:\(|,)\s*([^)\n,]+)", text, re.I) if brand else None
            found[appl] = (appl_type, brand, proper.group(1).strip() if proper else brand, url, text,
                           signed_on(text))
    if not found:
        print(f"named={len(named)} letters found=0")
        return
    with llm.connect() as conn, conn.cursor() as cur:
        release = llm.register_release(cur, "fda_unlisted_letters", max(f[5] or "" for f in found.values()),
                                       UNLISTED_LETTER, llm.sha256_text("".join(sorted(found))),
                                       {"applications": sorted(found)})
        execute_values(cur, """INSERT INTO preclin.fda_application (appl_no, appl_type, center, sponsor_name,
                                 source_release_id) VALUES %s ON CONFLICT (appl_no) DO NOTHING""",
                       [(a, t, "CDER", None, release) for a, (t, *_) in found.items()])
        execute_values(cur, """INSERT INTO preclin.fda_product (appl_no, product_no, drug_name, active_ingredient)
                               VALUES %s ON CONFLICT (appl_no, product_no) DO NOTHING""",
                       [(a, "unlisted1", b, p) for a, (_, b, p, *_) in found.items()])
        execute_values(cur, """INSERT INTO preclin.fda_submission (appl_no, submission_type, submission_no, status,
                                 status_date, submission_class) VALUES %s ON CONFLICT DO NOTHING""",
                       [(a, "ORIG", "1", "AP", d, None) for a, (*_, d) in found.items() if d])
        docs = {a: hashlib.sha256(t.encode()).hexdigest() for a, (_, _, _, _, t, _) in found.items()}
        write_letters(cur, [(docs[a], t, len(t.encode())) for a, (_, _, _, _, t, _) in found.items()],
                      [(a, "ORIG", "1", u, d, docs[a], None, "letter") for a, (_, _, _, u, _, d) in found.items()])
        conn.commit()
    print(f"named={len(named)} letters found={len(found)}: {sorted(found)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in [("fetch", fetch), ("load", load), ("extract", extract), ("link", link),
                     ("load-cber", load_cber), ("unlisted", unlisted)]:
        sub.add_parser(name).set_defaults(fn=fn)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
