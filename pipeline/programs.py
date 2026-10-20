"""Development programs built from the ClinicalTrials.gov snapshot.

    python -m pipeline.programs register   # trial -> intervention names / conditions (preclin.ctgov_study_*)
    python -m pipeline.programs roles      # role of each molecular entity in each trial

A trial is in scope when it lists Early Phase 1, Phase 1, 2 or 3 (any sponsor,
any date). Intervention names (DRUG, BIOLOGICAL, GENETIC, COMBINATION_PRODUCT)
and condition strings are registered in preclin.drug and preclin.indication,
keyed like every earlier row (lower-case alphanumerics), so pipeline.drugs and
pipeline.indications resolve them.
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict

from psycopg2.extras import execute_values

from pipeline import llm

IN_SCOPE_PHASES = ["EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3"]
DRUG_TYPES = {"DRUG", "BIOLOGICAL", "GENETIC", "COMBINATION_PRODUCT"}
COMPARATOR_ARMS = {"ACTIVE_COMPARATOR", "PLACEBO_COMPARATOR", "SHAM_COMPARATOR", "NO_INTERVENTION"}


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower().strip())


def in_scope_studies(cur):
    cur.execute("""SELECT nct_id, interventions, arm_groups, conditions FROM preclin.ctgov_study
                   WHERE phases && %s::text[]""", (IN_SCOPE_PHASES,))
    return cur.fetchall()


def register(_args) -> None:
    with llm.connect() as conn, conn.cursor() as cur:
        studies = in_scope_studies(cur)
        drug_names, drug_syns = defaultdict(Counter), defaultdict(set)
        cond_names = defaultdict(Counter)
        study_drugs = {}
        study_conds = set()
        for nct, interventions, arms, conditions in studies:
            arm_type = {a.get("label"): a.get("type") or "UNKNOWN" for a in arms}
            for iv in interventions:
                if iv.get("type") not in DRUG_TYPES or not norm(iv.get("name")):
                    continue
                key = norm(iv["name"])
                drug_names[key][iv["name"].strip()] += 1
                drug_syns[key].update(o.strip() for o in iv.get("otherNames") or [] if o.strip())
                types = sorted({arm_type.get(l, "UNKNOWN") for l in iv.get("armGroupLabels") or []})
                prev = study_drugs.get((nct, key))
                study_drugs[(nct, key)] = (iv["type"], sorted(set(types) | set(prev[1] if prev else [])),
                                           sorted(drug_syns[key])[:10])
            for c in conditions:
                if norm(c):
                    cond_names[norm(c)][c.strip()] += 1
                    study_conds.add((nct, norm(c)))

        execute_values(cur, """INSERT INTO preclin.drug (normalized_name, display_name, synonyms, resolved_via)
            VALUES %s ON CONFLICT (normalized_name) DO NOTHING""",
                       [(k, v.most_common(1)[0][0], sorted(drug_syns[k])[:10], "ctgov_snapshot")
                        for k, v in drug_names.items()], page_size=5000)
        execute_values(cur, """INSERT INTO preclin.indication (normalized_name, display_name, ct_gov_conditions)
            VALUES %s ON CONFLICT (normalized_name) DO NOTHING""",
                       [(k, v.most_common(1)[0][0], sorted(v)) for k, v in cond_names.items()], page_size=5000)
        cur.execute("SELECT normalized_name, drug_id FROM preclin.drug")
        drug_id = dict(cur.fetchall())
        cur.execute("SELECT normalized_name, indication_id FROM preclin.indication")
        ind_id = dict(cur.fetchall())
        cur.execute("DELETE FROM preclin.ctgov_study_drug")
        execute_values(cur, """INSERT INTO preclin.ctgov_study_drug
            (nct_id, drug_id, intervention_type, arm_types, other_names) VALUES %s""",
                       [(nct, drug_id[k], t, arms, syns) for (nct, k), (t, arms, syns) in study_drugs.items()],
                       page_size=10000)
        cur.execute("DELETE FROM preclin.ctgov_study_indication")
        execute_values(cur, "INSERT INTO preclin.ctgov_study_indication (nct_id, indication_id) VALUES %s",
                       [(nct, ind_id[k]) for nct, k in study_conds], page_size=10000)
        conn.commit()
    print(f"in-scope studies={len(studies)} drug names={len(drug_names)} conditions={len(cond_names)} "
          f"study-drug links={len(study_drugs)} study-condition links={len(study_conds)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("register").set_defaults(fn=register)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
