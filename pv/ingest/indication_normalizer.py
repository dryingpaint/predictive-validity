"""Normalize pilot indication concepts through exact, archived OLS4 lookups."""
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json

from pv.ingest.pilot_asset_targets import PHENOTYPE_NAMESPACE
from pv.ingest.semantic_verifier import Archive, LLM_RUN_ID, normalized


ADAPTER = "pv.ingest.indication_normalizer"
ADAPTER_VERSION = "1.1.0"
ROLE_MAP = {
    "treated_condition": None,
    "core_condition": None,
    "background_disease": "background_condition",
    "population_context": "population_characteristic",
    "comorbidity": "background_condition",
    "other": None,
}
ALLOWED_ROLES = {
    "treatment", "prevention", "diagnosis", "supportive_care",
    "background_condition", "population_characteristic", "healthy_volunteer",
}


def exact_ontology_match(archive: Archive, label: str, concept_kind: str) -> tuple[dict[str, Any], int] | None:
    params = {"q": label, "exact": "true", "rows": 100, "ontology": "mondo,hp,efo"}
    url = "https://www.ebi.ac.uk/ols4/api/search?" + urllib.parse.urlencode(params)
    payload, version_id = archive.retrieve(
        f"search:{normalized(label)}", label, url, f"search:{normalized(label)}", "ontology_search"
    )
    docs = (payload.get("response") or {}).get("docs") or []
    needle = normalized(label)
    exact = []
    for row in docs:
        source_terms = [row.get("label") or ""]
        source_terms.extend(row.get("exact_synonyms") or [])
        source_terms.extend(row.get("related_synonyms") or [])
        if needle in {normalized(term) for term in source_terms if term}:
            exact.append(row)
    # Imported terms are repeated by OLS. Prefer an identifier native to MONDO,
    # then HP, then EFO, independent of result order.
    namespace_order = ["MONDO", "HP", "EFO"] if concept_kind in {"disease", "infection", "injury"} else ["HP", "MONDO", "EFO"]
    for namespace in namespace_order:
        native = [row for row in exact if str(row.get("obo_id") or "").startswith(namespace + ":")]
        ids = {row.get("obo_id") for row in native}
        if len(ids) == 1:
            return native[0], version_id
    return None


def insert_alias(cur: Any, entity_id: uuid.UUID, text: str, kind: str,
                 release_id: int, version_id: int, ambiguous: bool = False) -> None:
    if not text:
        return
    cur.execute(
        """INSERT INTO pv_core.entity_alias
             (entity_id,entity_type,alias_text,alias_normalized,alias_kind,language,
              source_release_id,source_record_version_id,is_ambiguous)
           VALUES (%s,'phenotype',%s,%s,%s,'en',%s,%s,%s) ON CONFLICT DO NOTHING""",
        (str(entity_id), text, normalized(text), kind, release_id, version_id, ambiguous),
    )


def verify(cur: Any, decision_id: int, path: str, status: str,
           entity_id: uuid.UUID | None, source_version_id: int | None,
           detail: dict[str, Any]) -> None:
    cur.execute(
        """INSERT INTO pv_evidence.llm_proposal_verification
             (llm_decision_id,proposal_kind,proposal_path,verification_status,verified_entity_id,
              verification_source_record_version_id,verifier,verifier_version,detail)
           VALUES (%s,'indication',%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (llm_decision_id,proposal_kind,proposal_path,verifier,verifier_version)
           DO UPDATE SET verification_status=EXCLUDED.verification_status,
             verified_entity_id=EXCLUDED.verified_entity_id,
             verification_source_record_version_id=EXCLUDED.verification_source_record_version_id,
             detail=EXCLUDED.detail""",
        (decision_id, path, status, str(entity_id) if entity_id else None, source_version_id,
         ADAPTER, ADAPTER_VERSION, Json(detail)),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--decision-run-id", default=LLM_RUN_ID)
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if not args.commit:
        raise SystemExit("Use --commit; writes are idempotent projections and append-only retrieval audit rows.")
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    archive = Archive(conn, "ols4", datetime.now(timezone.utc),
                      {"decision_run_id": args.decision_run_id}, adapter=ADAPTER)
    counts = {"resolved": 0, "unresolved": 0, "not_applicable": 0, "links": 0}
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT task,status FROM pv_evidence.llm_decision_run
                   WHERE decision_run_id=%s""", (args.decision_run_id,),
            )
            run = cur.fetchone()
            if not run:
                raise RuntimeError(f"Unknown decision run: {args.decision_run_id}")
            if run != ("trial_semantic_extraction", "completed"):
                raise RuntimeError(
                    f"Decision run {args.decision_run_id} is not a completed "
                    f"trial_semantic_extraction run: task={run[0]} status={run[1]}"
                )
            cur.execute(
                """SELECT d.llm_decision_id,d.subject_key,d.parsed_output,t.latest_source_record_version_id
                   FROM pv_evidence.llm_decision d JOIN pv_core.trial t ON t.nct_id=d.subject_key
                   WHERE d.decision_run_id=%s ORDER BY d.subject_key""", (args.decision_run_id,),
            )
            decisions = cur.fetchall()
        if not decisions:
            raise RuntimeError(f"Decision run {args.decision_run_id} contains no trial decisions")
        for decision_id, nct_id, output, trial_version_id in decisions:
            for indication_index, indication in enumerate(output.get("indications") or []):
                for concept_index, concept in enumerate(indication.get("concepts") or []):
                    path = f"$.indications[{indication_index}].concepts[{concept_index}]"
                    label = concept["label"]
                    kind = concept["concept_kind"]
                    if kind in {"healthy_state", "other"}:
                        with conn.cursor() as cur:
                            verify(cur, decision_id, path, "not_applicable", None, None,
                                   {"label": label, "reason": "not_a_disease_or_phenotype_ontology_projection"})
                        conn.commit()
                        counts["not_applicable"] += 1
                        continue
                    match = exact_ontology_match(archive, label, kind)
                    if not match:
                        with conn.cursor() as cur:
                            verify(cur, decision_id, path, "unresolved", None, None,
                                   {"label": label, "reason": "no_unique_exact_native_ontology_identifier"})
                        conn.commit()
                        counts["unresolved"] += 1
                        continue
                    row, ontology_version = match
                    obo_id = row["obo_id"]
                    namespace = obo_id.split(":", 1)[0]
                    phenotype_id = uuid.uuid5(PHENOTYPE_NAMESPACE, obo_id.casefold())
                    preferred = row.get("label") or label
                    role = ROLE_MAP.get(concept.get("relationship")) or indication.get("role")
                    if role not in ALLOWED_ROLES:
                        role = "population_characteristic"
                    with conn.cursor() as cur:
                        cur.execute(
                            """INSERT INTO pv_core.entity(entity_id,entity_type,preferred_name)
                               VALUES (%s,'phenotype',%s) ON CONFLICT (entity_id)
                               DO UPDATE SET preferred_name=EXCLUDED.preferred_name""",
                            (str(phenotype_id), preferred),
                        )
                        cur.execute(
                            """INSERT INTO pv_core.phenotype
                                 (entity_id,ontology_namespace,ontology_identifier,preferred_name,phenotype_kind)
                               VALUES (%s,%s,%s,%s,%s) ON CONFLICT (entity_id) DO UPDATE SET
                                 preferred_name=EXCLUDED.preferred_name,phenotype_kind=EXCLUDED.phenotype_kind""",
                            (str(phenotype_id), namespace, obo_id, preferred, kind),
                        )
                        cur.execute(
                            """INSERT INTO pv_core.entity_identifier
                                 (entity_id,namespace,identifier,source_release_id,is_preferred)
                               VALUES (%s,%s,%s,%s,true) ON CONFLICT DO NOTHING""",
                            (str(phenotype_id), namespace, obo_id, archive.release_id),
                        )
                        insert_alias(cur, phenotype_id, preferred, "preferred_label", archive.release_id, ontology_version)
                        if normalized(label) != normalized(preferred):
                            insert_alias(cur, phenotype_id, label, "query_label", archive.release_id, ontology_version)
                        for synonym in row.get("exact_synonyms") or []:
                            insert_alias(
                                cur, phenotype_id, synonym, "exact_synonym",
                                archive.release_id, ontology_version,
                            )
                        for synonym in row.get("related_synonyms") or []:
                            insert_alias(
                                cur, phenotype_id, synonym, "related_synonym",
                                archive.release_id, ontology_version, True,
                            )
                        cur.execute(
                            """INSERT INTO pv_core.trial_indication_link
                                 (nct_id,phenotype_entity_id,indication_role,source_record_version_id,
                                  resolution_method,llm_decision_id)
                               VALUES (%s,%s,%s,%s,'llm_concept_then_ols_exact_native_id',%s)
                               ON CONFLICT DO NOTHING RETURNING trial_indication_link_id""",
                            (nct_id, str(phenotype_id), role, trial_version_id, decision_id),
                        )
                        inserted = cur.fetchone()
                        if inserted:
                            link_id = inserted[0]
                        else:
                            cur.execute(
                                """SELECT trial_indication_link_id FROM pv_core.trial_indication_link
                                   WHERE nct_id=%s AND phenotype_entity_id=%s AND indication_role=%s
                                     AND source_record_version_id=%s""",
                                (nct_id, str(phenotype_id), role, trial_version_id),
                            )
                            link_id = cur.fetchone()[0]
                        for evidence in indication.get("evidence") or []:
                            source_path = evidence["source_path"]
                            evidence_role = "literal_condition" if ".conditionsModule.conditions[" in source_path else "title_or_summary"
                            if ".eligibilityModule." in source_path:
                                evidence_role = "eligibility_context"
                            cur.execute(
                                """INSERT INTO pv_evidence.trial_indication_evidence
                                     (trial_indication_link_id,source_path,support_quote,evidence_role,detail)
                                   VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                                (link_id, source_path, evidence["quote"], evidence_role,
                                 Json({"concept_path": path})),
                            )
                        cur.execute(
                            """INSERT INTO pv_evidence.trial_indication_evidence
                                 (trial_indication_link_id,source_path,support_quote,evidence_role,detail)
                               VALUES (%s,%s,%s,'ontology_mapping',%s) ON CONFLICT DO NOTHING""",
                            (link_id, f"OLS4:{obo_id}", preferred,
                             Json({"query_label": label, "ontology_identifier": obo_id})),
                        )
                        verify(cur, decision_id, path, "verified", phenotype_id, ontology_version,
                               {"query_label": label, "ontology_identifier": obo_id,
                                "preferred_label": preferred, "indication_role": role})
                    conn.commit()
                    counts["resolved"] += 1
                    counts["links"] += 1
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
