#!/usr/bin/env python3
"""
Fill preclin.drug_bio_class with a canonical modality for every drug that has one.

Three sources in priority order:
  1. `preclin.drug.modality` — 544 drugs, curated from FDA approvals CSV
  2. `public.therapies.modality` — ~8k drugs, matched by chembl_id or normalized name
  3. ChEMBL molecule API — ~24k drugs with a chembl_id but no therapies match
                            (molecule_type field: Small molecule / Antibody / Oligonucleotide / etc.)

Everything else stays uncovered until the LLM fallback runs (`enrich_modality_llm.py`).
Idempotent — re-running skips drugs already in `drug_bio_class` with a non-llm source.
"""
from __future__ import annotations
import os, sys, time, subprocess
import psycopg2
import psycopg2.extras
import requests

MODALITY_CANON = {
    # ChEMBL molecule_type + public.therapies.modality → canonical
    "small molecule":         "small_molecule",
    "small_molecule":         "small_molecule",
    "antibody":               "antibody",
    "mab":                    "antibody",
    "bispecific_mab":         "antibody",
    "monoclonal antibody":    "antibody",
    "antibody drug conjugate":     "adc",
    "antibody_drug_conjugate":     "adc",
    "adc":                    "adc",
    "protein":                "protein",
    "protein_or_enzyme":      "protein",
    "enzyme":                 "protein",
    "peptide":                "peptide",
    "oligonucleotide":        "oligonucleotide",
    "oligonucleotide_aso":    "oligonucleotide",
    "oligonucleotide_siRNA".lower(): "oligonucleotide",
    "antisense":              "oligonucleotide",
    "sirna":                  "oligonucleotide",
    "vaccine":                "vaccine",
    "cell_therapy":           "cell_therapy",
    "other_cell_therapy":     "cell_therapy",
    "car_t":                  "cell_therapy",
    "til":                    "cell_therapy",
    "gene_therapy":           "gene_therapy",
    "aav_gene_therapy":       "gene_therapy",
    "ex_vivo_gene_therapy":   "gene_therapy",
    "mrna":                   "mrna",
    "oligosaccharide":        "small_molecule",   # closest fit
    "polymer":                "other",
    "mixture":                "other",
    "radioligand":            "small_molecule",
    "other":                  "other",
    "contrast_agent":         "small_molecule",
}


def canon(mod: str | None) -> str | None:
    if not mod:
        return None
    return MODALITY_CANON.get(mod.lower().strip(), "other")


def get_db_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    r = subprocess.run(["grep", "^DATABASE_URL", "/Users/melissadu/Documents/projects/capable/.env"],
                       capture_output=True, text=True, check=True)
    # override with predictive-validity DB
    return ("postgresql://neondb_owner:npg_Snpr6yPT9sOE@ep-late-smoke-amionchh-pooler."
            "c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")


def upsert_batch(cur, rows: list[tuple]) -> None:
    """rows: (drug_id, modality, modality_subtype, is_novel, novelty_class, source, confidence)"""
    if not rows:
        return
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
        -- Only overwrite if new source has equal-or-higher priority
        WHERE preclin.drug_bio_class.source NOT IN ('curated_approvals','public_therapies','chembl_api')
    """, rows)


def novelty_from_modality(mod: str) -> tuple[bool | None, str]:
    """Best-effort novelty class from modality alone. Refined later via ChEMBL max_phase / approval status."""
    if mod in ("cell_therapy", "gene_therapy", "mrna", "oligonucleotide", "adc"):
        return True, "novel_biologic"
    if mod == "vaccine":
        return True, "vaccine"
    if mod in ("antibody", "protein", "peptide"):
        return True, "biologic"
    if mod == "small_molecule":
        return None, "unknown"  # can be NME or biosimilar; refined later
    return None, "unknown"


def step1_curated(cur) -> int:
    """Ingest `preclin.drug.modality` — 544 drugs, curated from approvals CSV."""
    cur.execute("SELECT drug_id, modality FROM preclin.drug WHERE modality IS NOT NULL")
    rows = []
    for drug_id, mod in cur.fetchall():
        m = canon(mod)
        if not m:
            continue
        novel, nov_class = novelty_from_modality(m)
        rows.append((drug_id, m, mod, novel, nov_class, "curated_approvals", "high"))
    upsert_batch(cur, rows)
    return len(rows)


def step2_public_therapies(cur) -> int:
    """Match drugs to public.therapies via chembl_id or normalized name."""
    cur.execute("""
        WITH matched AS (
          SELECT d.drug_id, th.modality, th.modality_subtype, th.novelty_class,
                 CASE WHEN th.chembl_id = d.chembl_id THEN 'chembl_id_match'
                      ELSE 'name_match' END AS match_kind
          FROM preclin.drug d
          JOIN public.therapies th
            ON (th.chembl_id = d.chembl_id AND d.chembl_id IS NOT NULL)
            OR LOWER(th.name) = LOWER(d.normalized_name)
        )
        SELECT DISTINCT ON (drug_id) drug_id, modality, modality_subtype, novelty_class, match_kind
        FROM matched ORDER BY drug_id,
          CASE match_kind WHEN 'chembl_id_match' THEN 1 ELSE 2 END
    """)
    rows = []
    for drug_id, mod, subtype, novelty, match_kind in cur.fetchall():
        m = canon(mod)
        if not m:
            continue
        novel, nov_default = novelty_from_modality(m)
        nov_class = novelty or nov_default
        rows.append((drug_id, m, subtype or mod, novel, nov_class, "public_therapies", "high"))
    upsert_batch(cur, rows)
    return len(rows)


def step3_chembl_api(cur) -> int:
    """Fetch molecule_type from ChEMBL API for drugs with chembl_id that haven't been classified yet."""
    cur.execute("""
        SELECT d.drug_id, d.chembl_id
        FROM preclin.drug d
        LEFT JOIN preclin.drug_bio_class dbc ON dbc.drug_id = d.drug_id
        WHERE d.chembl_id IS NOT NULL AND dbc.drug_id IS NULL
        ORDER BY d.drug_id
    """)
    todo = cur.fetchall()
    print(f"  ChEMBL API: {len(todo):,} drugs to fetch")
    if not todo:
        return 0
    BATCH = 50  # ChEMBL /molecule endpoint accepts semi-colon separated
    inserted = 0
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        ids = ";".join(c[1] for c in chunk if c[1])
        try:
            r = requests.get(
                f"https://www.ebi.ac.uk/chembl/api/data/molecule/set/{ids}.json",
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"    batch {i // BATCH} failed: {e}")
            time.sleep(2)
            continue
        # ChEMBL returns 'molecules' array
        mols = data.get("molecules") if isinstance(data, dict) else data
        by_chembl = {m["molecule_chembl_id"]: m for m in (mols or [])}
        rows = []
        for drug_id, chembl_id in chunk:
            m = by_chembl.get(chembl_id)
            if not m:
                continue
            mol_type = m.get("molecule_type") or ""
            max_phase = m.get("max_phase")
            mod = canon(mol_type)
            if not mod:
                continue
            novel, nov_class = novelty_from_modality(mod)
            # ChEMBL max_phase >= 4 = approved somewhere; use that as tiebreaker for is_novel
            rows.append((drug_id, mod, mol_type, novel, nov_class, "chembl_api", "medium"))
        upsert_batch(cur, rows)
        inserted += len(rows)
        if i % (BATCH * 10) == 0:
            print(f"    progress: {i + BATCH:>6,} / {len(todo):,}  (+{len(rows)} in this batch)")
        time.sleep(0.15)  # be polite to ChEMBL
    return inserted


def main():
    conn = psycopg2.connect(get_db_url())
    conn.autocommit = False
    cur = conn.cursor()

    print("Step 1: curated modality from preclin.drug (approvals CSV)")
    n1 = step1_curated(cur)
    conn.commit()
    print(f"  → {n1:,} rows")

    print("Step 2: modality from public.therapies (chembl_id or name match)")
    n2 = step2_public_therapies(cur)
    conn.commit()
    print(f"  → {n2:,} rows (may overlap step 1; only new drugs counted)")

    print("Step 3: modality from ChEMBL /molecule API")
    n3 = step3_chembl_api(cur)
    conn.commit()
    print(f"  → {n3:,} rows")

    cur.execute("SELECT * FROM preclin.v_bio_enrichment_coverage")
    total, class_ind, drugs, class_drug = cur.fetchone()
    print(f"\nCoverage: {class_drug:,} / {drugs:,} drugs classified ({100*class_drug/drugs:.1f}%)")

    cur.execute("""
        SELECT modality, source, COUNT(*)
        FROM preclin.drug_bio_class GROUP BY modality, source ORDER BY 3 DESC
    """)
    print("\nBy modality × source:")
    for mod, src, n in cur.fetchall():
        print(f"  {mod:<20s}  {src:<20s}  {n:>6,}")

    conn.close()


if __name__ == "__main__":
    main()
