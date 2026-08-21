#!/usr/bin/env python3
"""
Classify each indication in `preclin.indication` into BIO 2021's 14 major disease areas + Other,
plus a short subarea name. Uses Claude Haiku, batched, concurrent, idempotent.
"""
from __future__ import annotations
import os, sys, json, time, subprocess, re
from typing import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2
import psycopg2.extras


BIO_AREAS = [
    "Allergy",
    "Autoimmune",
    "Cardiovascular",
    "Endocrine",
    "Gastroenterology",  # non-IBD
    "Hematology",
    "Infectious disease",
    "Metabolic",
    "Neurology",
    "Oncology",
    "Ophthalmology",
    "Psychiatry",
    "Respiratory",
    "Urology",
    "Other",  # dermatology, renal, ob/gyn, rheumatology non-autoimmune, ENT, orthopedics, etc.
]

BATCH = 30      # indications per Claude call
CONCURRENCY = 12
MODEL = "claude-haiku-4-5"
MAX_RETRIES = 3

SYSTEM_PROMPT = (
    "You are a clinical trials analyst classifying disease indications into fixed categories used "
    "by the BIO 2021 Clinical Development Success Rates report.\n\n"
    "For each indication, output JSON with these fields:\n"
    "  - bio_area: one of {areas}\n"
    "  - bio_subarea: a short (2-4 word) canonical name for the indication\n"
    "  - confidence: 'high' | 'medium' | 'low'\n\n"
    "Rules:\n"
    "* Oncology = any cancer. If the indication is a cancer, bio_area='Oncology'.\n"
    "* Hematology = blood disorders that are NOT cancers (hemophilia, anemia, sickle cell, "
    "  bleeding disorders). Blood cancers go to Oncology.\n"
    "* Neurology = neurological disease incl. Alzheimer's, Parkinson's, ALS, MS, migraine, "
    "  epilepsy, stroke. Psychiatry = mood, anxiety, schizophrenia, addiction, ADHD.\n"
    "* Metabolic = diabetes, obesity, lipid disorders, NAFLD. Endocrine = thyroid, growth, "
    "  reproductive endocrine.\n"
    "* Autoimmune = RA, lupus, IBD (Crohn's/UC), psoriasis, MS (dual-classify to Neurology), "
    "  Sjogren's. Allergy = allergic rhinitis, asthma (dual-classify to Respiratory), atopic "
    "  dermatitis, food allergy.\n"
    "* Gastroenterology (non-IBD) = GERD, IBS, hepatitis, NASH (dual-classify to Metabolic), "
    "  pancreatic disease. IBD → Autoimmune.\n"
    "* Infectious = viral, bacterial, fungal, parasitic. COVID-19 = Infectious.\n"
    "* When dual-classifiable, pick the PRIMARY area a sponsor would file under.\n"
    "* Rare-disease criterion is US <200K OR EU 1/2000. Common cancers are NOT rare.\n"
    "* Chronic-high-prev is chronic AND common (>1M US patients) AND not cancer.\n\n"
    "Output ONLY a JSON array, one object per input indication, in the same order. "
    "No prose, no markdown fences."
).format(areas=" | ".join(BIO_AREAS))


def get_db_url() -> str:
    return ("postgresql://neondb_owner:npg_Snpr6yPT9sOE@ep-late-smoke-amionchh-pooler."
            "c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")


def get_api_key() -> str:
    r = subprocess.run(["grep", "^ANTHROPIC_API_KEY",
                        "/Users/melissadu/Documents/radical-numerics/omnii-biomysterybench/.env"],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip().split("=", 1)[1]


def classify_batch(client, items: list[tuple[int, str, str | None]]) -> list[dict]:
    """items: list of (indication_id, display_name, existing_therapeutic_area)."""
    payload = [
        {"i": idx, "name": name, "current_ta_hint": ta or "unknown"}
        for idx, (_id, name, ta) in enumerate(items)
    ]
    user_msg = (
        f"Classify these {len(items)} indications. Return a JSON array of {len(items)} objects "
        f"in the same order.\n\n{json.dumps(payload, ensure_ascii=False)}"
    )
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.messages.create(
                model=MODEL, max_tokens=4000, system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            text = resp.content[0].text.strip()
            # strip potential fences
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
            data = json.loads(text)
            if not isinstance(data, list) or len(data) != len(items):
                raise ValueError(f"expected {len(items)}-element array, got {len(data) if isinstance(data, list) else type(data)}")
            return data
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                print(f"    batch failed after {MAX_RETRIES} retries: {e}", file=sys.stderr)
                return []
            time.sleep(1.5 * (attempt + 1))
    return []


def normalize_area(a: str) -> str:
    a = (a or "").strip()
    # Case-insensitive match to canonical
    for canon in BIO_AREAS:
        if a.lower() == canon.lower():
            return canon
    # Common variants
    variants = {
        "onco": "Oncology", "cancer": "Oncology", "tumor": "Oncology",
        "cns": "Neurology", "neuroscience": "Neurology",
        "psych": "Psychiatry", "mental": "Psychiatry",
        "cardio": "Cardiovascular", "cv": "Cardiovascular",
        "endo": "Endocrine",
        "gi": "Gastroenterology", "gastro": "Gastroenterology",
        "heme": "Hematology", "blood": "Hematology",
        "infect": "Infectious disease", "id": "Infectious disease",
        "metab": "Metabolic", "diabetes": "Metabolic",
        "ophth": "Ophthalmology", "eye": "Ophthalmology",
        "resp": "Respiratory", "pulm": "Respiratory",
        "uro": "Urology",
        "derm": "Other", "renal": "Other", "nephro": "Other",
        "ob/gyn": "Other", "musculo": "Other",
    }
    al = a.lower()
    for k, v in variants.items():
        if k in al:
            return v
    return "Other"


def upsert_batch(cur, items: list[tuple[int, str, str | None]], results: list[dict]) -> int:
    rows = []
    for (ind_id, name, _ta), res in zip(items, results):
        bio_area = normalize_area(res.get("bio_area", "Other"))
        subarea = (res.get("bio_subarea") or "")[:120]
        conf = (res.get("confidence") or "medium")[:8]
        rows.append((ind_id, bio_area, subarea, "llm_haiku_4_5", conf, name))
    if not rows:
        return 0
    psycopg2.extras.execute_values(cur, """
        INSERT INTO preclin.indication_bio_class
          (indication_id, bio_area, bio_subarea, source, confidence, rationale)
        VALUES %s
        ON CONFLICT (indication_id) DO NOTHING
    """, rows)
    return cur.rowcount


def main():
    from anthropic import Anthropic
    os.environ["ANTHROPIC_API_KEY"] = get_api_key()
    client = Anthropic()

    conn = psycopg2.connect(get_db_url())
    cur = conn.cursor()
    # todo list: all indications not yet classified
    cur.execute("""
        SELECT i.indication_id, i.display_name, i.therapeutic_area
        FROM preclin.indication i
        LEFT JOIN preclin.indication_bio_class ibc ON ibc.indication_id = i.indication_id
        WHERE ibc.indication_id IS NULL
        ORDER BY i.indication_id
    """)
    todo = cur.fetchall()
    print(f"Todo: {len(todo):,} indications to classify")
    if not todo:
        print("nothing to do")
        return

    chunks = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    print(f"  {len(chunks):,} batches of {BATCH}, concurrency={CONCURRENCY}")
    classified = 0
    t0 = time.time()
    done_batches = 0

    def do_batch(chunk):
        return chunk, classify_batch(client, chunk)

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futures = {ex.submit(do_batch, c): idx for idx, c in enumerate(chunks)}
        for fut in as_completed(futures):
            chunk, results = fut.result()
            if results:
                n = upsert_batch(cur, chunk, results)
                classified += n
                conn.commit()
            done_batches += 1
            if done_batches % 10 == 0 or done_batches == len(chunks):
                items_done = done_batches * BATCH
                rate = items_done / max(time.time() - t0, 0.1)
                eta_min = (len(todo) - items_done) / rate / 60 if rate > 0 else 0
                print(f"  batch {done_batches:>4,}/{len(chunks):,}  items≈{items_done:>5,}/{len(todo):,}  "
                      f"classified={classified:,}  rate={rate:.1f}/s  eta={eta_min:.1f}min", flush=True)

    cur.execute("SELECT COUNT(*) FROM preclin.indication_bio_class")
    total = cur.fetchone()[0]
    print(f"\nTotal classified: {total:,}")
    cur.execute("SELECT bio_area, COUNT(*) FROM preclin.indication_bio_class "
                "GROUP BY bio_area ORDER BY 2 DESC")
    print(f"{'bio_area':<20}  {'n':>6}")
    for area, n in cur.fetchall():
        print(f"  {area:<18}  {n:>6,}")

    conn.close()


if __name__ == "__main__":
    main()
