#!/usr/bin/env python3
"""
Fallback modality classifier for drugs not covered by curated / public.therapies / ChEMBL.

Uses Claude Haiku over drug name (+ any hints). Batched, resumable.
Populates `preclin.drug_bio_class` with source='llm_haiku_4_5'.

Canonical modalities: small_molecule | antibody | adc | protein | peptide |
                       oligonucleotide | cell_therapy | gene_therapy | vaccine | mrna | other

Also emits:
  * modality_subtype (e.g. 'CAR-T', 'siRNA', 'AAV', 'bispecific mAb')
  * is_novel (True for novel NME / biologic / cell / gene / mRNA / vaccine; False for biosimilar / non-NME)
  * novelty_class (NME | biologic | vaccine | biosimilar | non_NME | unknown)
"""
from __future__ import annotations
import os, sys, json, time, subprocess, re
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2
import psycopg2.extras


MODALITIES = ["small_molecule", "antibody", "adc", "protein", "peptide",
              "oligonucleotide", "cell_therapy", "gene_therapy", "vaccine",
              "mrna", "other"]

BATCH = 40
CONCURRENCY = 12   # parallel API calls (Anthropic rate limit ~50 rpm for Haiku on standard tier)
MODEL = "claude-haiku-4-5"
MAX_RETRIES = 3

SYSTEM_PROMPT = (
    "You classify drug names into canonical drug-modality categories. For each drug name, output "
    "a JSON object with:\n"
    "  modality:   one of small_molecule | antibody | adc | protein | peptide | oligonucleotide "
    "| cell_therapy | gene_therapy | vaccine | mrna | other\n"
    "  modality_subtype: short label like 'mAb' | 'bispecific mAb' | 'CAR-T' | 'AAV gene therapy' "
    "| 'siRNA' | 'ASO' | 'small-molecule inhibitor' | 'peptide agonist' | ''\n"
    "  is_novel:   true for new NME/biologic/cell/gene/mRNA/vaccine; false for biosimilar or non-NME\n"
    "  novelty_class: NME | biologic | vaccine | biosimilar | non_NME | unknown\n"
    "  confidence: high | medium | low\n\n"
    "Modality signals from the name suffix:\n"
    "  -mab, -zumab, -tumab, -lumab, -olimab = antibody (novel biologic)\n"
    "  -imab, -bemab, -cemab = usually antibody biosimilar → is_novel=false, novelty_class=biosimilar\n"
    "  -tinib, -parib, -zomib, -sertib, -ciclib, -pib = small-molecule kinase/protease inhibitor\n"
    "  -stat, -sartan, -pril, -olol, -zole, -pine, -ide, -one = small_molecule\n"
    "  -tide, -reotide, -natide, -glutide, -lutide = peptide\n"
    "  -sen, -mersen, -rsen = antisense oligonucleotide\n"
    "  -siran, -sirna = siRNA\n"
    "  -tocel, -leucel, -bcel = cell therapy (often CAR-T)\n"
    "  -parvovec, -vec, -gene = gene therapy\n"
    "  contains 'vaccine' or 'BNT' or '-mRNA' = vaccine or mrna\n"
    "  '-inecel'/'-decel' with 'antibody drug conjugate' name = adc\n\n"
    "Rules:\n"
    "* If you can't determine modality confidently, default to 'small_molecule' with confidence='low'.\n"
    "* Combination drugs (e.g. 'X + Y') → classify by primary active ingredient.\n"
    "* Placebo / vehicle / diluent → modality='other', is_novel=false, novelty_class='unknown'.\n"
    "* Confidence should reflect how certain you are — low if you're guessing from name alone.\n\n"
    "Output ONLY a JSON array of objects, same order as input. No prose, no markdown fences."
)


def get_db_url() -> str:
    return ("postgresql://neondb_owner:npg_Snpr6yPT9sOE@ep-late-smoke-amionchh-pooler."
            "c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")


def get_api_key() -> str:
    r = subprocess.run(["grep", "^ANTHROPIC_API_KEY",
                        "/Users/melissadu/Documents/radical-numerics/omnii-biomysterybench/.env"],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip().split("=", 1)[1]


def classify(client, items: list[tuple[int, str, str | None]]) -> list[dict]:
    """items: (drug_id, normalized_name, chembl_id)"""
    payload = [{"i": idx, "name": n, "chembl_id": c or ""} for idx, (_, n, c) in enumerate(items)]
    user_msg = (f"Classify these {len(items)} drug names. Return a JSON array of {len(items)} "
                f"objects in the same order.\n\n{json.dumps(payload, ensure_ascii=False)}")
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.messages.create(
                model=MODEL, max_tokens=4000, system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            text = resp.content[0].text.strip()
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
            data = json.loads(text)
            if not isinstance(data, list) or len(data) != len(items):
                raise ValueError(f"array length mismatch {len(data)}/{len(items)}")
            return data
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                print(f"    batch failed: {e}", file=sys.stderr)
                return []
            time.sleep(1.5 * (attempt + 1))
    return []


def normalize_mod(m: str) -> str:
    m = (m or "").lower().strip().replace(" ", "_")
    mapping = {
        "small molecule": "small_molecule", "smallmolecule": "small_molecule",
        "mab": "antibody", "monoclonal_antibody": "antibody", "monoclonalantibody": "antibody",
        "antibody_drug_conjugate": "adc",
        "sirna": "oligonucleotide", "aso": "oligonucleotide", "antisense": "oligonucleotide",
        "cell": "cell_therapy", "gene": "gene_therapy",
    }
    m = mapping.get(m, m)
    return m if m in MODALITIES else "other"


def upsert_batch(cur, items: list, results: list[dict]) -> int:
    rows = []
    for (drug_id, _name, _cid), res in zip(items, results):
        mod = normalize_mod(res.get("modality", "other"))
        sub = (res.get("modality_subtype") or "")[:80]
        is_novel = res.get("is_novel")
        if isinstance(is_novel, str):
            is_novel = is_novel.lower() in ("true", "yes", "1")
        nov = (res.get("novelty_class") or "unknown")[:20]
        conf = (res.get("confidence") or "medium")[:8]
        rows.append((drug_id, mod, sub, is_novel, nov, "llm_haiku_4_5", conf))
    if not rows:
        return 0
    psycopg2.extras.execute_values(cur, """
        INSERT INTO preclin.drug_bio_class
          (drug_id, modality, modality_subtype, is_novel, novelty_class, source, confidence)
        VALUES %s
        ON CONFLICT (drug_id) DO NOTHING
    """, rows)
    return cur.rowcount


def main():
    from anthropic import Anthropic
    os.environ["ANTHROPIC_API_KEY"] = get_api_key()
    client = Anthropic()

    conn = psycopg2.connect(get_db_url())
    cur = conn.cursor()
    # Only classify drugs that have at least one trial in our program cohort (avoid classifying 30k
    # random ChEMBL entries; focus on drugs that actually appear in our clinical dataset).
    cur.execute("""
        SELECT DISTINCT d.drug_id, d.normalized_name, d.chembl_id
        FROM preclin.drug d
        JOIN preclin.program p ON p.drug_id = d.drug_id
        LEFT JOIN preclin.drug_bio_class dbc ON dbc.drug_id = d.drug_id
        WHERE dbc.drug_id IS NULL
        ORDER BY d.drug_id
    """)
    todo = cur.fetchall()
    print(f"Todo: {len(todo):,} in-cohort drugs to classify via LLM")
    if not todo:
        return

    # Parallel: submit CONCURRENCY batches at a time, upsert results as they land
    chunks = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    print(f"  {len(chunks):,} batches of {BATCH}, concurrency={CONCURRENCY}")
    classified = 0
    t0 = time.time()
    done_batches = 0

    def do_batch(chunk):
        return chunk, classify(client, chunk)

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futures = {ex.submit(do_batch, c): idx for idx, c in enumerate(chunks)}
        for fut in as_completed(futures):
            chunk, results = fut.result()
            if results:
                n = upsert_batch(cur, chunk, results)
                classified += n
                conn.commit()
            done_batches += 1
            if done_batches % 20 == 0 or done_batches == len(chunks):
                drugs_done = done_batches * BATCH
                rate = drugs_done / max(time.time() - t0, 0.1)
                eta_min = (len(todo) - drugs_done) / rate / 60 if rate > 0 else 0
                print(f"  progress: batch {done_batches:>4,}/{len(chunks):,}  "
                      f"drugs≈{drugs_done:>6,}/{len(todo):,}  classified={classified:,}  "
                      f"rate={rate:.1f}/s  eta={eta_min:.1f}min", flush=True)

    cur.execute("SELECT COUNT(*) FROM preclin.drug_bio_class")
    print(f"\nTotal drug classifications: {cur.fetchone()[0]:,}")
    cur.execute("""SELECT modality, COUNT(*) FROM preclin.drug_bio_class
                    GROUP BY modality ORDER BY 2 DESC""")
    for m, n in cur.fetchall():
        print(f"  {m:<20s}  {n:>6,}")
    conn.close()


if __name__ == "__main__":
    main()
