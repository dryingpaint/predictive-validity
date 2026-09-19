"""Materialize the reviewed five-trial 2015 replacement pilot cohort."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from typing import Any

import psycopg2
from psycopg2.extras import Json


COHORT_ID = "pv_2015_actual_completed_drug_biological_pilot5_v1"
EXPECTED = [
    (0, "NCT00711230", "excluded", "vaccine", "Repeated DermaVir Immunizations"),
    (1, "NCT00911183", "included", "reviewed_therapeutic_candidate", "lymphoma"),
    (2, "NCT01272466", "excluded", "vaccine", "Vaccination With Peptides"),
    (3, "NCT01434342", "included", "reviewed_therapeutic_candidate", "Nicotine Replacement Patch"),
    (4, "NCT01507974", "excluded", "antibiotic", "Preventive Antibiotic Treatment"),
    (5, "NCT01882166", "included", "reviewed_therapeutic_candidate", "ovarian stimulation"),
    (6, "NCT02046239", "excluded", "non_therapeutic_registry_misclassification", "Suture vs Staples"),
    (7, "NCT02231931", "included", "reviewed_therapeutic_candidate", "Drug-drug Interaction"),
    (8, "NCT03998215", "excluded", "vaccine", "Diphtheria Vaccination"),
    (9, "NCT00082719", "included", "reviewed_therapeutic_candidate", "Interferon Alfa"),
]


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def materialize(commit: bool) -> dict[str, Any]:
    definition = {
        "registry": "ClinicalTrials.gov",
        "completion_from": "2015-01-01",
        "completion_through": "2015-12-31",
        "completion_date_type": "ACTUAL",
        "study_type": "INTERVENTIONAL",
        "intervention_types_any": ["DRUG", "BIOLOGICAL"],
        "candidate_order": ["completion_date_lower_bound", "completion_date_precision", "nct_id"],
        "candidate_limit": 10,
        "included_limit": 5,
        "scope_exclusions": ["vaccine", "antibiotic", "non_human_target", "non_therapeutic"],
        "selection_method": "source-grounded_manual_pilot_review_v1",
    }
    digest = hashlib.sha256(canonical(definition).encode()).hexdigest()
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT q.retrieval_query_id,q.result_manifest
                   FROM pv_source.retrieval_query q
                   JOIN pv_source.acquisition_run run USING(acquisition_run_id)
                   WHERE run.adapter='pv.ingest.clinicaltrials_gov'
                     AND run.status='completed'
                     AND run.parameters->>'from_date'='2015-01-01'
                     AND run.parameters->>'through_date'='2015-12-31'
                     AND (run.parameters->>'limit')::integer=10
                   ORDER BY run.completed_at DESC LIMIT 1"""
            )
            row = cur.fetchone()
            if row is None:
                raise SystemExit("No completed ten-candidate 2015 registry run found")
            query_id, manifest = row
            manifest_ids = [item["nct_id"] for item in manifest[:10]]
            expected_ids = [item[1] for item in EXPECTED]
            if manifest_ids != expected_ids:
                raise RuntimeError(f"Candidate manifest drift: {manifest_ids!r}")

            report = {"cohort_id": COHORT_ID, "definition_sha256": digest, "members": []}
            if commit:
                cur.execute(
                    """INSERT INTO pv_core.trial_cohort
                         (cohort_id,definition,definition_sha256,source_retrieval_query_id)
                       VALUES (%s,%s,%s,%s)
                       ON CONFLICT (cohort_id) DO UPDATE SET
                         source_retrieval_query_id=EXCLUDED.source_retrieval_query_id
                       WHERE pv_core.trial_cohort.definition_sha256=EXCLUDED.definition_sha256""",
                    (COHORT_ID, Json(definition), digest, query_id),
                )
            for ordinal, nct_id, status, reason, expected_text in EXPECTED:
                cur.execute(
                    """SELECT t.brief_title,
                              array_agg(i.literal_name ORDER BY i.source_path)
                                FILTER (WHERE i.literal_name IS NOT NULL)
                       FROM pv_core.trial t
                       LEFT JOIN pv_core.intervention_mention i ON i.nct_id=t.nct_id
                       WHERE t.nct_id=%s GROUP BY t.nct_id,t.brief_title""", (nct_id,),
                )
                trial = cur.fetchone()
                if trial is None:
                    raise RuntimeError(f"Missing candidate trial {nct_id}")
                title, interventions = trial
                searchable = " ".join([title or "", *(interventions or [])]).casefold()
                if expected_text.casefold() not in searchable:
                    raise RuntimeError(f"Expected support text missing for {nct_id}: {expected_text}")
                support = {
                    "brief_title": title,
                    "intervention_names": interventions or [],
                    "matched_text": expected_text,
                }
                report["members"].append({
                    "ordinal": ordinal, "nct_id": nct_id, "status": status,
                    "reason": reason, "support": support,
                })
                if commit:
                    cur.execute(
                        """INSERT INTO pv_core.trial_cohort_member
                             (cohort_id,nct_id,candidate_ordinal,membership_status,
                              reason_code,decision_method,support)
                           VALUES (%s,%s,%s,%s,%s,'source_grounded_manual_pilot_review_v1',%s)
                           ON CONFLICT (cohort_id,nct_id) DO UPDATE SET
                             candidate_ordinal=EXCLUDED.candidate_ordinal,
                             membership_status=EXCLUDED.membership_status,
                             reason_code=EXCLUDED.reason_code,
                             support=EXCLUDED.support
                           WHERE (pv_core.trial_cohort_member.candidate_ordinal,
                                  pv_core.trial_cohort_member.membership_status,
                                  pv_core.trial_cohort_member.reason_code,
                                  pv_core.trial_cohort_member.support)
                             IS DISTINCT FROM
                                 (EXCLUDED.candidate_ordinal,EXCLUDED.membership_status,
                                  EXCLUDED.reason_code,EXCLUDED.support)""",
                        (COHORT_ID, nct_id, ordinal, status, reason, Json(support)),
                    )
        if not commit:
            conn.rollback()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--commit", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    print(json.dumps(materialize(args.commit), indent=2))


if __name__ == "__main__":
    main()
