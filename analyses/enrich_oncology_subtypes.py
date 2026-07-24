#!/usr/bin/env python3
"""
Classify oncology indications into BIO's three sub-buckets:
  - solid            (solid tumors — lung, breast, colorectal, prostate, pancreatic, glioma, sarcoma, etc.)
  - hematologic      (blood cancers — AML, ALL, CML, CLL, MM, NHL, HL, MDS, etc.)
  - immuno_oncology  (IO-focused: checkpoint inhibitors, adoptive cell therapy, cancer vaccines, IO combos)

Reads oncology-classified indications from `preclin.indication_bio_class` where oncology_subtype
IS NULL and populates the column via Claude Haiku (batched, concurrent).
"""
from __future__ import annotations
import os, sys, json, time, subprocess, re
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2
import psycopg2.extras

BATCH = 30
CONCURRENCY = 12
MODEL = "claude-haiku-4-5"
MAX_RETRIES = 3

SYSTEM = (
    "You classify oncology indications into ONE of three BIO categories:\n"
    "  - solid: solid-tumor cancers (NSCLC, breast, colorectal, prostate, pancreatic, "
    "melanoma, ovarian, gastric, HCC, glioma/GBM, sarcoma, etc.)\n"
    "  - hematologic: blood cancers (AML, ALL, CML, CLL, MM, NHL, HL, MDS, MPN, DLBCL, etc.)\n"
    "  - immuno_oncology: broad IO-development targeting solid OR heme, when the indication "
    "language implies checkpoint inhibitor / adoptive cell / bispecific engager / cancer vaccine "
    "or a general 'advanced solid tumors' IO expansion. If the indication names a specific tumor "
    "type (e.g. 'NSCLC' or 'AML'), classify as solid or hematologic respectively.\n\n"
    "Rules:\n"
    "* Multiple myeloma, myeloma → hematologic\n"
    "* Lymphoma (any) → hematologic\n"
    "* Leukemia (AML/ALL/CML/CLL) → hematologic\n"
    "* MDS, MPN, myelofibrosis → hematologic\n"
    "* Anything with 'solid tumor', 'metastatic', named organ → solid\n"
    "* 'Advanced malignancies' / 'refractory solid tumors' / 'basket trial' → solid (default)\n"
    "* Cancer vaccine, oncolytic virus, TCR/CAR-T against solid → immuno_oncology\n"
    "* If unclear, pick solid (dominant category)\n\n"
    "Return JSON array of {oncology_subtype, confidence} in input order. No prose, no fences."
)


def get_db_url() -> str:
    return ("postgresql://neondb_owner:npg_Snpr6yPT9sOE@ep-late-smoke-amionchh-pooler."
            "c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")


def get_key() -> str:
    r = subprocess.run(["grep", "^ANTHROPIC_API_KEY",
                        "/Users/melissadu/Documents/radical-numerics/omnii-biomysterybench/.env"],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip().split("=", 1)[1]


def classify(client, items):
    payload = [{"i": idx, "name": name, "subarea": sub or ""}
               for idx, (_, name, sub) in enumerate(items)]
    user = (f"Classify these {len(items)} oncology indications. Return a JSON array of "
            f"{len(items)} objects in the same order.\n\n{json.dumps(payload, ensure_ascii=False)}")
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.messages.create(
                model=MODEL, max_tokens=3000, system=SYSTEM,
                messages=[{"role": "user", "content": user}],
            )
            text = resp.content[0].text.strip()
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
            data = json.loads(text)
            if not isinstance(data, list) or len(data) != len(items):
                raise ValueError(f"len mismatch {len(data)}/{len(items)}")
            return data
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                print(f"    batch failed: {e}", file=sys.stderr)
                return []
            time.sleep(1.5 * (attempt + 1))
    return []


def normalize(v):
    v = (v or "").lower().strip().replace(" ", "_")
    if v in ("solid", "solid_tumor", "solid_tumors"):
        return "solid"
    if v in ("hematologic", "hematological", "heme", "hem"):
        return "hematologic"
    if v in ("immuno_oncology", "io", "immunooncology", "immuno-oncology"):
        return "immuno_oncology"
    return "solid"  # safe default


def upsert(cur, items, results):
    rows = []
    for (ind_id, _n, _s), res in zip(items, results):
        rows.append((normalize(res.get("oncology_subtype", "")), ind_id))
    psycopg2.extras.execute_batch(cur,
        "UPDATE preclin.indication_bio_class SET oncology_subtype=%s WHERE indication_id=%s",
        rows, page_size=200)
    return len(rows)


def main():
    from anthropic import Anthropic
    os.environ["ANTHROPIC_API_KEY"] = get_key()
    client = Anthropic()
    conn = psycopg2.connect(get_db_url())
    cur = conn.cursor()

    cur.execute("""
        SELECT ibc.indication_id, i.display_name, ibc.bio_subarea
        FROM preclin.indication_bio_class ibc
        JOIN preclin.indication i USING(indication_id)
        WHERE ibc.bio_area = 'Oncology' AND ibc.oncology_subtype IS NULL
        ORDER BY ibc.indication_id
    """)
    todo = cur.fetchall()
    print(f"Todo: {len(todo):,} oncology indications to sub-classify")
    if not todo:
        return

    chunks = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    print(f"  {len(chunks):,} batches × {BATCH} @ concurrency={CONCURRENCY}")
    t0 = time.time()
    done = 0

    def do_batch(chunk):
        return chunk, classify(client, chunk)

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futs = {ex.submit(do_batch, c): idx for idx, c in enumerate(chunks)}
        for fut in as_completed(futs):
            chunk, results = fut.result()
            if results:
                upsert(cur, chunk, results)
                conn.commit()
            done += 1
            if done % 10 == 0 or done == len(chunks):
                pct = 100 * done / len(chunks)
                rate = (done * BATCH) / max(time.time() - t0, 0.1)
                print(f"  batch {done}/{len(chunks)}  ({pct:.0f}%)  rate={rate:.1f}/s", flush=True)

    cur.execute("""
        SELECT oncology_subtype, COUNT(*) FROM preclin.indication_bio_class
        WHERE bio_area = 'Oncology' GROUP BY oncology_subtype ORDER BY 2 DESC
    """)
    print("\nOncology subtype distribution:")
    for st, n in cur.fetchall():
        print(f"  {st or '(unclassified)':<20} {n:>6,}")
    conn.close()


if __name__ == "__main__":
    main()
