#!/usr/bin/env python3
"""
Populate `preclin.drug_bio_class` with canonical modality + novelty for every drug.

Source ladder (in priority order):
  1. `preclin.drug.modality`           — 544 drugs, curated from FDA approvals CSV
  2. `public.therapies.modality`       — ~4k drugs, matched via chembl_id or name
  3. ChEMBL /molecule API              — drugs with a chembl_id but no `public.therapies` match
  4. Claude Haiku 4.5                  — LLM fallback on drug name for everything remaining

Steps 1-3 are deterministic. Step 4 is the concurrent LLM batch job.
Idempotent — re-running skips drugs already classified by a higher-priority source.

Canonical modality set: small_molecule | antibody | adc | protein | peptide |
                        oligonucleotide | cell_therapy | gene_therapy | vaccine | mrna | other
"""
from __future__ import annotations
import os, sys, json, time, subprocess, re
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2
import psycopg2.extras
import requests

# ─── Canonical modality mapping (used by both deterministic + LLM paths) ───
MODALITIES = ["small_molecule", "antibody", "adc", "protein", "peptide",
              "oligonucleotide", "cell_therapy", "gene_therapy", "vaccine",
              "mrna", "other"]

MODALITY_CANON = {
    "small molecule": "small_molecule", "small_molecule": "small_molecule",
    "smallmolecule": "small_molecule",
    "antibody": "antibody", "mab": "antibody", "monoclonal antibody": "antibody",
    "monoclonal_antibody": "antibody", "bispecific_mab": "antibody",
    "antibody drug conjugate": "adc", "antibody_drug_conjugate": "adc", "adc": "adc",
    "protein": "protein", "protein_or_enzyme": "protein", "enzyme": "protein",
    "peptide": "peptide",
    "oligonucleotide": "oligonucleotide", "oligonucleotide_aso": "oligonucleotide",
    "oligonucleotide_sirna": "oligonucleotide", "antisense": "oligonucleotide",
    "sirna": "oligonucleotide", "aso": "oligonucleotide",
    "vaccine": "vaccine",
    "cell_therapy": "cell_therapy", "cell": "cell_therapy",
    "other_cell_therapy": "cell_therapy", "car_t": "cell_therapy", "til": "cell_therapy",
    "gene_therapy": "gene_therapy", "gene": "gene_therapy",
    "aav_gene_therapy": "gene_therapy", "ex_vivo_gene_therapy": "gene_therapy",
    "mrna": "mrna",
    "oligosaccharide": "small_molecule", "radioligand": "small_molecule",
    "contrast_agent": "small_molecule",
    "polymer": "other", "mixture": "other", "other": "other",
}


def canon(mod: str | None) -> str | None:
    if not mod:
        return None
    m = mod.lower().strip().replace(" ", "_")
    return MODALITY_CANON.get(m, "other" if m else None)


def novelty_from_modality(mod: str) -> tuple[bool | None, str]:
    if mod in ("cell_therapy", "gene_therapy", "mrna", "oligonucleotide", "adc"):
        return True, "novel_biologic"
    if mod == "vaccine":
        return True, "vaccine"
    if mod in ("antibody", "protein", "peptide"):
        return True, "biologic"
    if mod == "small_molecule":
        return None, "unknown"   # NME vs biosimilar/generic — refined by LLM
    return None, "unknown"


def get_db_url() -> str:
    return ("postgresql://neondb_owner:npg_Snpr6yPT9sOE@ep-late-smoke-amionchh-pooler."
            "c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")


def get_api_key() -> str:
    r = subprocess.run(["grep", "^ANTHROPIC_API_KEY",
                        "/Users/melissadu/Documents/radical-numerics/omnii-biomysterybench/.env"],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip().split("=", 1)[1]


def upsert(cur, rows):
    """rows: (drug_id, modality, subtype, is_novel, novelty_class, source, confidence)"""
    if not rows:
        return 0
    psycopg2.extras.execute_values(cur, """
        INSERT INTO preclin.drug_bio_class
          (drug_id, modality, modality_subtype, is_novel, novelty_class, source, confidence)
        VALUES %s
        ON CONFLICT (drug_id) DO UPDATE SET
          modality = EXCLUDED.modality,
          modality_subtype = EXCLUDED.modality_subtype,
          is_novel = EXCLUDED.is_novel,
          novelty_class = EXCLUDED.novelty_class,
          source = EXCLUDED.source,
          confidence = EXCLUDED.confidence,
          extracted_at = now()
        -- only overwrite lower-priority sources
        WHERE preclin.drug_bio_class.source NOT IN
              ('curated_approvals','public_therapies','chembl_api')
    """, rows)
    return len(rows)


# ─── Step 1: curated approvals ─────────────────────────────────────────────
def step_curated(cur) -> int:
    cur.execute("SELECT drug_id, modality FROM preclin.drug WHERE modality IS NOT NULL")
    rows = []
    for did, mod in cur.fetchall():
        m = canon(mod)
        if not m:
            continue
        novel, nov = novelty_from_modality(m)
        rows.append((did, m, mod, novel, nov, "curated_approvals", "high"))
    return upsert(cur, rows)


# ─── Step 2: public.therapies ──────────────────────────────────────────────
def step_public_therapies(cur) -> int:
    cur.execute("""
      WITH matched AS (
        SELECT d.drug_id, th.modality, th.modality_subtype, th.novelty_class,
               CASE WHEN th.chembl_id = d.chembl_id THEN 'chembl' ELSE 'name' END AS how
        FROM preclin.drug d JOIN public.therapies th
          ON (th.chembl_id = d.chembl_id AND d.chembl_id IS NOT NULL)
          OR LOWER(th.name) = LOWER(d.normalized_name)
      )
      SELECT DISTINCT ON (drug_id) drug_id, modality, modality_subtype, novelty_class
      FROM matched ORDER BY drug_id, CASE how WHEN 'chembl' THEN 1 ELSE 2 END
    """)
    rows = []
    for did, mod, sub, nov in cur.fetchall():
        m = canon(mod)
        if not m:
            continue
        novel, nov_def = novelty_from_modality(m)
        rows.append((did, m, sub or mod, novel, nov or nov_def, "public_therapies", "high"))
    return upsert(cur, rows)


# ─── Step 3: ChEMBL /molecule API ──────────────────────────────────────────
def step_chembl_api(cur) -> int:
    cur.execute("""
      SELECT d.drug_id, d.chembl_id FROM preclin.drug d
      LEFT JOIN preclin.drug_bio_class dbc ON dbc.drug_id = d.drug_id
      WHERE d.chembl_id IS NOT NULL AND dbc.drug_id IS NULL
    """)
    todo = cur.fetchall()
    if not todo:
        return 0
    print(f"  ChEMBL: {len(todo):,} drugs to fetch")
    inserted = 0
    B = 50
    for i in range(0, len(todo), B):
        chunk = todo[i:i + B]
        ids = ";".join(c[1] for c in chunk if c[1])
        try:
            r = requests.get(
                f"https://www.ebi.ac.uk/chembl/api/data/molecule/set/{ids}.json", timeout=60)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"    batch {i//B} failed: {e}")
            time.sleep(2)
            continue
        mols = data.get("molecules") if isinstance(data, dict) else data
        by_id = {m["molecule_chembl_id"]: m for m in (mols or [])}
        rows = []
        for did, cid in chunk:
            m = by_id.get(cid)
            if not m:
                continue
            mod = canon(m.get("molecule_type") or "")
            if not mod:
                continue
            novel, nov = novelty_from_modality(mod)
            rows.append((did, mod, m.get("molecule_type"), novel, nov, "chembl_api", "medium"))
        inserted += upsert(cur, rows)
        time.sleep(0.2)
    return inserted


# ─── Step 4: Claude Haiku LLM classifier ───────────────────────────────────
BATCH = 40
CONCURRENCY = 12
MODEL = "claude-haiku-4-5"
MAX_RETRIES = 3

SYSTEM_PROMPT = (
    "You classify drug names into canonical drug modalities. For each drug name, output a JSON "
    "object with: modality (one of small_molecule | antibody | adc | protein | peptide | "
    "oligonucleotide | cell_therapy | gene_therapy | vaccine | mrna | other), modality_subtype "
    "(short like 'mAb' | 'bispecific mAb' | 'CAR-T' | 'AAV gene therapy' | 'siRNA' | 'ASO' | "
    "'small-molecule inhibitor' | 'peptide agonist'), is_novel (true for NME/novel biologic; "
    "false for biosimilar/non-NME), novelty_class (NME | biologic | vaccine | biosimilar | "
    "non_NME | unknown), confidence (high | medium | low).\n\n"
    "Suffix signals: -mab/-zumab/-tumab/-lumab/-olimab = antibody; -tinib/-parib/-zomib/-ciclib "
    "= small_molecule inhibitor; -tide/-natide/-glutide/-lutide = peptide; -sen/-mersen/-rsen "
    "= antisense; -siran/-sirna = siRNA; -tocel/-leucel/-bcel = cell_therapy; -parvovec/-vec "
    "= gene_therapy. 'vaccine'/'BNT'/'-mRNA' in name = vaccine or mrna.\n\n"
    "Rules:\n"
    "* Default modality='small_molecule' with confidence='low' if unclear.\n"
    "* Combinations 'X + Y' → classify by primary active ingredient.\n"
    "* Placebo / vehicle / diluent → modality='other', novelty_class='unknown'.\n\n"
    "Output ONLY a JSON array of objects, same order as input. No prose, no fences."
)


def _classify(client, items):
    payload = [{"i": i, "name": n, "chembl_id": c or ""}
               for i, (_, n, c) in enumerate(items)]
    user = (f"Classify these {len(items)} drug names. Return JSON array of "
            f"{len(items)} in the same order.\n\n{json.dumps(payload, ensure_ascii=False)}")
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.messages.create(
                model=MODEL, max_tokens=4000, system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user}],
            )
            text = resp.content[0].text.strip()
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
            data = json.loads(text)
            if not isinstance(data, list) or len(data) != len(items):
                raise ValueError(f"len {len(data)}/{len(items)}")
            return data
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                print(f"    batch failed: {e}", file=sys.stderr)
                return []
            time.sleep(1.5 * (attempt + 1))
    return []


def step_llm(cur) -> int:
    from anthropic import Anthropic
    os.environ["ANTHROPIC_API_KEY"] = get_api_key()
    client = Anthropic()

    cur.execute("""
      SELECT DISTINCT d.drug_id, d.normalized_name, d.chembl_id
      FROM preclin.drug d JOIN preclin.program p ON p.drug_id = d.drug_id
      LEFT JOIN preclin.drug_bio_class dbc ON dbc.drug_id = d.drug_id
      WHERE dbc.drug_id IS NULL
    """)
    todo = cur.fetchall()
    if not todo:
        return 0
    chunks = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    print(f"  LLM: {len(todo):,} drugs in {len(chunks):,} batches, concurrency={CONCURRENCY}")
    t0 = time.time()
    done = classified = 0

    def process(chunk):
        return chunk, _classify(client, chunk)

    conn = cur.connection
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futs = {ex.submit(process, c): i for i, c in enumerate(chunks)}
        for fut in as_completed(futs):
            chunk, results = fut.result()
            if results:
                rows = []
                for (did, _n, _c), res in zip(chunk, results):
                    mod = canon(res.get("modality", "other")) or "other"
                    sub = (res.get("modality_subtype") or "")[:80]
                    is_novel = res.get("is_novel")
                    if isinstance(is_novel, str):
                        is_novel = is_novel.lower() in ("true", "yes", "1")
                    nov = (res.get("novelty_class") or "unknown")[:20]
                    conf = (res.get("confidence") or "medium")[:8]
                    rows.append((did, mod, sub, is_novel, nov, "llm_haiku_4_5", conf))
                classified += upsert(cur, rows)
                conn.commit()
            done += 1
            if done % 20 == 0 or done == len(chunks):
                rate = (done * BATCH) / max(time.time() - t0, 0.1)
                eta = (len(todo) - done * BATCH) / rate / 60 if rate > 0 else 0
                print(f"    batch {done:>4,}/{len(chunks):,}  "
                      f"drugs≈{min(done*BATCH,len(todo)):>6,}  rate={rate:.1f}/s  eta={eta:.1f}min",
                      flush=True)
    return classified


def main():
    conn = psycopg2.connect(get_db_url())
    conn.autocommit = False
    cur = conn.cursor()

    print("(1) curated approvals")
    print(f"  → {step_curated(cur):,} rows"); conn.commit()

    print("(2) public.therapies")
    print(f"  → {step_public_therapies(cur):,} rows"); conn.commit()

    print("(3) ChEMBL /molecule API")
    print(f"  → {step_chembl_api(cur):,} rows"); conn.commit()

    print("(4) Claude Haiku fallback")
    print(f"  → {step_llm(cur):,} rows"); conn.commit()

    cur.execute("""SELECT modality, COUNT(*) FROM preclin.drug_bio_class
                    GROUP BY modality ORDER BY 2 DESC""")
    print("\nFinal modality distribution:")
    for m, n in cur.fetchall():
        print(f"  {m:<20s}  {n:>6,}")
    conn.close()


if __name__ == "__main__":
    main()
