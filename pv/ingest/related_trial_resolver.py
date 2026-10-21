"""Resolve source-mentioned parent protocols to ClinicalTrials.gov records."""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import Json

from pv.ingest.semantic_verifier import Archive


ADAPTER = "pv.ingest.related_trial_resolver"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if not args.commit:
        raise SystemExit("Use --commit; the resolver is idempotent and archives every query.")
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    archive = Archive(conn, "clinicaltrials_gov", datetime.now(timezone.utc),
                      {"scope": "unresolved trial relationships"}, adapter=ADAPTER)
    counts = {"resolved": 0, "ambiguous": 0, "unresolved": 0}
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT trial_relationship_id,subject_nct_id,object_identifier
                   FROM pv_core.trial_relationship WHERE object_nct_id IS NULL
                   ORDER BY trial_relationship_id"""
            )
            relationships = cur.fetchall()
        for relationship_id, subject_nct_id, identifier in relationships:
            numeric = re.findall(r"[0-9]+", identifier)
            query_id = numeric[-1] if numeric else identifier
            params = {"query.id": query_id, "format": "json", "pageSize": 100, "countTotal": "true"}
            search_url = "https://clinicaltrials.gov/api/v2/studies?" + urllib.parse.urlencode(params)
            result, search_version = archive.retrieve(
                f"protocol-search:{query_id}", identifier, search_url,
                f"protocol-search:{query_id}", "related_trial_search"
            )
            candidates = []
            for study in result.get("studies") or []:
                identification = ((study.get("protocolSection") or {}).get("identificationModule") or {})
                org_id = (identification.get("orgStudyIdInfo") or {}).get("id")
                if org_id == query_id:
                    candidates.append(identification)
            if len(candidates) != 1:
                counts["ambiguous" if candidates else "unresolved"] += 1
                continue
            nct_id = candidates[0]["nctId"]
            detail_url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}?format=json"
            detail, detail_version = archive.retrieve(
                f"study:{nct_id}", nct_id, detail_url, nct_id, "supporting_trial_registry_record"
            )
            identification = ((detail.get("protocolSection") or {}).get("identificationModule") or {})
            exact_org_id = (identification.get("orgStudyIdInfo") or {}).get("id")
            if exact_org_id != query_id or identification.get("nctId") != nct_id:
                raise RuntimeError(f"ClinicalTrials.gov detail mismatch for {nct_id}")
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE pv_core.trial_relationship SET object_nct_id=%s,object_display_name=%s
                       WHERE trial_relationship_id=%s""",
                    (nct_id, identification.get("briefTitle"), relationship_id),
                )
                cur.execute(
                    """INSERT INTO pv_evidence.trial_relationship_evidence
                         (trial_relationship_id,source_record_version_id,source_path,support_quote,
                          derivation_method,detail)
                       VALUES (%s,%s,'protocolSection.identificationModule.orgStudyIdInfo.id',%s,
                               'deterministic_mapping',%s) ON CONFLICT DO NOTHING""",
                    (relationship_id, detail_version, exact_org_id,
                     Json({"resolved_nct_id": nct_id, "query_id": query_id,
                           "search_source_record_version_id": search_version,
                           "subject_nct_id": subject_nct_id})),
                )
            conn.commit()
            counts["resolved"] += 1
        archive.finish()
    except Exception as exc:
        conn.rollback()
        archive.fail(f"{type(exc).__name__}: {exc}")
        raise
    finally:
        conn.close()
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
