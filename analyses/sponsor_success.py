"""Proper sponsor success rate — with drug-variant dedup + originator attribution.

Steps:
1. Deduplicate drugs via chembl_id (where available); else normalized_name.
   This collapses "talazoparib" + "TALZENNA capsule" + "Talazoparib soft gel capsule"
   into one canonical drug.
2. For each canonical drug, determine its ORIGINATOR sponsor:
   - If approved (has preclin.approval row): use the approval's canonical sponsor name.
   - Else: sponsor with most Phase 2+ trials on that drug (proxy for who invested most).
3. Per canonical sponsor:
   - denominator = canonical drugs they originated
   - numerator = originated drugs that were approved
4. Filter to sponsors with ≥15 originated drugs.
"""

import csv
import os
import re
import sys
from collections import defaultdict

import psycopg2
from psycopg2.extras import RealDictCursor

# Import canonicalization from v2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonicalize_sponsors import normalize_sponsor, ALIAS_GROUPS


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    # Step 1: build canonical drug map
    # canonical_drug_key = chembl_id if available, else normalized_name
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT drug_id, normalized_name, display_name, chembl_id,
                   is_placebo, is_combination
            FROM preclin.drug
        """)
        drugs = cur.fetchall()

    # Also flag placebo variants that slipped the is_placebo=TRUE filter
    def is_placebo_or_control(d):
        if d["is_placebo"]:
            return True
        low = (d["display_name"] or "").lower()
        return any(k in low for k in ["placebo", "vehicle", " saline", "sham "])

    canonical_key = {}  # drug_id → canonical_key
    key_to_display = {}  # canonical_key → representative display name

    for d in drugs:
        if is_placebo_or_control(d):
            canonical_key[d["drug_id"]] = None
            continue
        if d["chembl_id"] and d["chembl_id"].strip():
            key = f"CHEMBL:{d['chembl_id']}"
        else:
            # Normalized name — strip formulation/dose modifiers
            n = d["normalized_name"] or ""
            n = re.sub(r"\d+mg\d*", "", n)
            n = re.sub(r"(capsule|tablet|injection|softgel|solution|suspension|inhalation)", "", n)
            n = n.strip()
            key = f"NAME:{n}" if n else None
        canonical_key[d["drug_id"]] = key
        if key and key not in key_to_display:
            key_to_display[key] = d["display_name"] or d["normalized_name"]

    unique_canonical = set(v for v in canonical_key.values() if v)
    print(f"Total drug rows: {len(drugs)}")
    print(f"Unique canonical drugs (after chembl+placebo dedup): {len(unique_canonical)}")

    # Step 2: determine originator per canonical drug
    # 2a. For approved drugs: originator = approval's sponsor
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT DISTINCT a.drug_id, a.sponsor_name
            FROM preclin.approval a
            WHERE a.sponsor_name IS NOT NULL
        """)
        approval_sponsors = cur.fetchall()

    # canonical_key -> canonical sponsor name (from approval)
    approved_owner = {}  # canonical_key -> sponsor
    for r in approval_sponsors:
        ck = canonical_key.get(r["drug_id"])
        if not ck or ck in approved_owner:
            continue
        canonical = normalize_sponsor(r["sponsor_name"])
        # Skip "Unknown" — will fall back to trial-based attribution below
        if canonical == "Unknown" or not canonical or canonical.strip() == "":
            continue
        approved_owner[ck] = canonical

    # 2b. For non-approved drugs: modal Phase 2+ sponsor
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT p.drug_id, p.sponsor_name,
                   COUNT(*) FILTER (WHERE p.highest_phase >= 2) AS n_ph2plus_trials,
                   MAX(p.highest_phase) AS max_phase
            FROM preclin.program p
            WHERE p.sponsor_name IS NOT NULL
            GROUP BY p.drug_id, p.sponsor_name
        """)
        drug_sponsor_counts = cur.fetchall()

    # Group by canonical_key
    ck_sponsor_ph2 = defaultdict(lambda: defaultdict(int))  # ck -> sponsor -> ph2+ trial count
    for r in drug_sponsor_counts:
        ck = canonical_key.get(r["drug_id"])
        if not ck:
            continue
        canonical_sp = normalize_sponsor(r["sponsor_name"])
        ck_sponsor_ph2[ck][canonical_sp] += r["n_ph2plus_trials"] or 0

    # Determine originator for each canonical drug
    originator = {}  # ck -> canonical sponsor
    for ck in unique_canonical:
        if ck in approved_owner:
            originator[ck] = approved_owner[ck]
        else:
            # Modal Phase 2+ sponsor
            sponsors = ck_sponsor_ph2.get(ck, {})
            if sponsors:
                # Pick sponsor with most Phase 2+ trials
                best = max(sponsors.items(), key=lambda x: x[1])
                if best[1] > 0:
                    originator[ck] = best[0]

    print(f"Canonical drugs with attributed originator: {len(originator)}")

    # Step 3: is each canonical drug approved?
    ck_approved = set(approved_owner.keys())
    print(f"  approved canonical drugs: {len(ck_approved)}")

    # Step 4: aggregate per sponsor
    sponsor_stats = defaultdict(lambda: {"total": set(), "approved": set()})
    for ck, sponsor in originator.items():
        sponsor_stats[sponsor]["total"].add(ck)
        if ck in ck_approved:
            sponsor_stats[sponsor]["approved"].add(ck)

    rows = []
    for sponsor, d in sponsor_stats.items():
        n = len(d["total"])
        appr = len(d["approved"])
        rows.append({
            "sponsor": sponsor, "n": n, "appr": appr,
            "pct": 100 * appr / n if n else 0,
        })

    with open("/tmp/sponsor_success_proper.csv", "w") as f:
        w = csv.writer(f)
        w.writerow(["sponsor", "n_originated", "n_approved", "success_pct"])
        for r in sorted(rows, key=lambda x: -x["n"]):
            w.writerow([r["sponsor"], r["n"], r["appr"], round(r["pct"], 1)])

    # Sanity check big pharma
    print("\n=== Sanity check: big pharma expected 5-20% range ===")
    for check in ["Pfizer", "Roche / Genentech", "Novartis", "Bristol Myers Squibb",
                   "Eli Lilly", "Merck (MSD)", "GlaxoSmithKline (GSK)", "AstraZeneca",
                   "Sanofi", "AbbVie", "Johnson & Johnson (Janssen)", "Bayer",
                   "Takeda", "Gilead", "Novo Nordisk", "Amgen", "Regeneron"]:
        r = next((x for x in rows if x["sponsor"] == check), None)
        if r:
            print(f"  {check:<40} n={r['n']:>4}  appr={r['appr']:>3}  ({r['pct']:.1f}%)")

    # Filtered top 30
    filtered = sorted([r for r in rows if r["n"] >= 15], key=lambda x: -x["pct"])
    print(f"\n=== Top 30 filtered (≥15 originated drugs, qualifying: {len(filtered)}) ===")
    for r in filtered[:30]:
        print(f"  {r['sponsor']:<40} n={r['n']:>4}  appr={r['appr']:>3}  ({r['pct']:.1f}%)")
    conn.close()


if __name__ == "__main__":
    main()
