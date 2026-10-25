"""Normalize an exact registry drug and condition without an LLM decision."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json

from pv.ingest.development_scope import (
    POLICY_VERSION,
    AssetDecision,
    classify_asset,
    decision_hash,
)
from pv.ingest.indication_normalizer import exact_ontology_match, insert_alias as insert_phenotype_alias
from pv.ingest.pilot_asset_targets import PHENOTYPE_NAMESPACE
from pv.ingest.semantic_verifier import (
    ACTION_MAP,
    Archive,
    complete_mechanisms,
    exact_parent,
    mechanism_support_quote,
    normalized,
    promote_asset,
    promote_target,
)


ADAPTER = "pv.ingest.exact_trial_normalizer"
ADAPTER_VERSION = "1.0.0"
DEFAULT_COHORT = "pv_cftr_organoid_sentinel_v1"
MECHANISM_NAMESPACE = uuid.UUID("5367fa4b-a99e-45d7-bff5-378c137b3c95")


def insert_scope(
    cur: Any,
    nct_id: str,
    asset_id: Any,
    asset_name: str,
    molecule: dict[str, Any],
    target_rows: list[dict[str, Any]],
    mechanism_rows: list[dict[str, Any]],
) -> None:
    atc_codes = list(molecule.get("atc_classifications") or [])
    target_taxa = [row["taxon_id"] for row in target_rows]
    decision = classify_asset(atc_codes, target_taxa)
    # A source-backed, targetless pharmacology record is still an eligible
    # human therapeutic asset.  It must not be made to look target-directed
    # merely to pass the development-scope gate.
    if not target_rows and mechanism_rows:
        decision = AssetDecision(
            "included",
            "human_therapeutic",
            "source_backed_targetless_pharmacology",
            {
                **decision.basis,
                "mechanism_entity_ids": [
                    str(row["mechanism_id"]) for row in mechanism_rows
                ],
            },
        )
    basis = {
        **decision.basis,
        "atc_codes": atc_codes,
        "target_entity_ids": [str(row["target_id"]) for row in target_rows],
        "mechanism_entity_ids": [
            str(row["mechanism_id"]) for row in mechanism_rows
        ],
        "normalization_path": "exact_registry_literal_then_structured_sources",
    }
    method = "deterministic_exact_registry_v1"
    history = {
        "status": decision.status, "category": decision.category,
        "reason": decision.reason, "method": method, "basis": basis,
    }
    cur.execute(
        """INSERT INTO pv_core.asset_development_scope_history
             (asset_entity_id,policy_version,decision_sha256,scope_status,
              scope_category,reason_code,classification_method,decision_basis)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
        (str(asset_id), POLICY_VERSION, decision_hash(history), decision.status,
         decision.category, decision.reason, method, Json(basis)),
    )
    cur.execute(
        """INSERT INTO pv_core.asset_development_scope
             (asset_entity_id,policy_version,scope_status,scope_category,
              reason_code,classification_method,decision_basis)
           VALUES (%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (asset_entity_id,policy_version) DO UPDATE SET
             scope_status=EXCLUDED.scope_status,scope_category=EXCLUDED.scope_category,
             reason_code=EXCLUDED.reason_code,
             classification_method=EXCLUDED.classification_method,
             decision_basis=EXCLUDED.decision_basis,classified_at=now()
           WHERE (pv_core.asset_development_scope.scope_status,
                  pv_core.asset_development_scope.scope_category,
                  pv_core.asset_development_scope.reason_code,
                  pv_core.asset_development_scope.classification_method,
                  pv_core.asset_development_scope.decision_basis)
             IS DISTINCT FROM
                 (EXCLUDED.scope_status,EXCLUDED.scope_category,EXCLUDED.reason_code,
                  EXCLUDED.classification_method,EXCLUDED.decision_basis)""",
        (str(asset_id), POLICY_VERSION, decision.status, decision.category,
         decision.reason, method, Json(basis)),
    )
    if decision.status != "included":
        raise RuntimeError(
            f"Exact asset {asset_name} is not in development scope: {decision.status}/{decision.reason}"
        )
    trial_basis = {
        "trial_kind": "interventional_drug",
        "asset_statuses": [decision.status],
        "asset_count": 1,
        "normalization_path": "exact_registry_literal_then_structured_sources",
    }
    trial_history = {
        "status": "included", "category": "human_therapeutic",
        "reason": "all_exact_resolved_assets_in_scope", "method": method,
        "llm_decision_id": None, "basis": trial_basis,
    }
    cur.execute(
        """INSERT INTO pv_core.trial_development_scope_history
             (nct_id,policy_version,decision_sha256,scope_status,scope_category,
              reason_code,classification_method,llm_decision_id,decision_basis)
           VALUES (%s,%s,%s,'included','human_therapeutic',%s,%s,NULL,%s)
           ON CONFLICT DO NOTHING""",
        (nct_id, POLICY_VERSION, decision_hash(trial_history),
         "all_exact_resolved_assets_in_scope", method, Json(trial_basis)),
    )
    cur.execute(
        """INSERT INTO pv_core.trial_development_scope
             (nct_id,policy_version,scope_status,scope_category,reason_code,
              classification_method,llm_decision_id,decision_basis)
           VALUES (%s,%s,'included','human_therapeutic',%s,%s,NULL,%s)
           ON CONFLICT (nct_id,policy_version) DO UPDATE SET
             scope_status=EXCLUDED.scope_status,scope_category=EXCLUDED.scope_category,
             reason_code=EXCLUDED.reason_code,
             classification_method=EXCLUDED.classification_method,
             llm_decision_id=NULL,decision_basis=EXCLUDED.decision_basis,classified_at=now()
           WHERE (pv_core.trial_development_scope.scope_status,
                  pv_core.trial_development_scope.scope_category,
                  pv_core.trial_development_scope.reason_code,
                  pv_core.trial_development_scope.classification_method,
                  pv_core.trial_development_scope.decision_basis)
             IS DISTINCT FROM
                 (EXCLUDED.scope_status,EXCLUDED.scope_category,EXCLUDED.reason_code,
                  EXCLUDED.classification_method,EXCLUDED.decision_basis)""",
        (nct_id, POLICY_VERSION, "all_exact_resolved_assets_in_scope", method,
        Json(trial_basis)),
    )


def promote_targetless_mechanism(
    conn: Any,
    asset_id: Any,
    mechanism: dict[str, Any],
    mechanism_version: int,
) -> uuid.UUID:
    """Project a ChEMBL mechanism row that deliberately has no target."""
    literal = str(mechanism.get("mechanism_of_action") or "Unknown").strip()
    if literal.casefold() == "unknown":
        preferred = "therapeutic mechanism unknown"
        mechanism_kind = "unknown"
        action_normalized = "unknown"
    else:
        preferred = literal
        mechanism_kind = "chemical_action"
        action_normalized = normalized(literal)
    mechanism_id = uuid.uuid5(MECHANISM_NAMESPACE, normalized(preferred))
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO pv_core.entity(entity_id,entity_type,preferred_name)
               VALUES (%s,'mechanism',%s)
               ON CONFLICT (entity_id) DO UPDATE SET
                 preferred_name=EXCLUDED.preferred_name""",
            (str(mechanism_id), preferred),
        )
        cur.execute(
            """INSERT INTO pv_core.mechanism
                 (entity_id,mechanism_kind,vocabulary_namespace,vocabulary_identifier)
               VALUES (%s,%s,'ChEMBL mechanism',%s)
               ON CONFLICT (entity_id) DO UPDATE SET
                 mechanism_kind=EXCLUDED.mechanism_kind,
                 vocabulary_namespace=EXCLUDED.vocabulary_namespace,
                 vocabulary_identifier=EXCLUDED.vocabulary_identifier""",
            (str(mechanism_id), mechanism_kind, str(mechanism["mec_id"])),
        )
        cur.execute(
            """INSERT INTO pv_evidence.asset_mechanism_assertion
                 (asset_entity_id,mechanism_entity_id,action_literal,
                  action_normalized,source_record_version_id,support_quote)
               VALUES (%s,%s,%s,%s,%s,%s)
               ON CONFLICT DO NOTHING""",
            (
                str(asset_id), str(mechanism_id), literal, action_normalized,
                mechanism_version, mechanism_support_quote(mechanism),
            ),
        )
    conn.commit()
    return mechanism_id


def insert_cohort(cur: Any, nct_id: str, cohort_id: str) -> None:
    purpose = (
        "trace_known_organoid_review_through_active_literature_policy"
        if cohort_id == DEFAULT_COHORT
        else "trace_exact_trial_through_active_literature_policy"
    )
    definition = {
        "cohort_kind": "sentinel_trial",
        "nct_ids": [nct_id],
        "purpose": purpose,
        "development_scope_policy": POLICY_VERSION,
    }
    raw = json.dumps(definition, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    cur.execute(
        """SELECT query.retrieval_query_id
           FROM pv_source.retrieval_query query
           JOIN pv_source.acquisition_run run USING (acquisition_run_id)
           WHERE run.adapter='pv.ingest.clinicaltrials_gov'
             AND run.parameters->'nct_ids' ? %s
             AND run.status='completed'
           ORDER BY run.started_at DESC LIMIT 1""",
        (nct_id,),
    )
    row = cur.fetchone()
    source_query_id = row[0] if row else None
    cur.execute(
        """INSERT INTO pv_core.trial_cohort
             (cohort_id,definition,definition_sha256,source_retrieval_query_id)
           VALUES (%s,%s,%s,%s) ON CONFLICT (cohort_id) DO NOTHING""",
        (cohort_id, Json(definition), digest, source_query_id),
    )
    cur.execute(
        """SELECT definition_sha256 FROM pv_core.trial_cohort WHERE cohort_id=%s""",
        (cohort_id,),
    )
    if cur.fetchone()[0].strip() != digest:
        raise RuntimeError(f"Cohort {cohort_id} already has a different definition")
    cur.execute(
        """INSERT INTO pv_core.trial_cohort_member
             (cohort_id,nct_id,candidate_ordinal,membership_status,reason_code,
              decision_method,support)
           VALUES (%s,%s,0,'included','explicit_sentinel_trial',
                   'deterministic_exact_registry_v1',%s)
           ON CONFLICT (cohort_id,nct_id) DO NOTHING""",
        (cohort_id, nct_id, Json({"nct_id": nct_id})),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--nct-id", required=True)
    parser.add_argument("--intervention", required=True)
    parser.add_argument("--condition", required=True)
    parser.add_argument(
        "--condition-concept",
        help="exact ontology label when the registry literal is not itself an ontology label",
    )
    parser.add_argument("--cohort-id", default=DEFAULT_COHORT)
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if not args.commit:
        raise SystemExit("Use --commit; all projections are source-backed and idempotent")
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    retrieved_at = datetime.now(timezone.utc)
    archives = {
        name: Archive(
            conn, name, retrieved_at,
            {"nct_id": args.nct_id, "intervention": args.intervention,
             "condition": args.condition,
             "condition_concept": args.condition_concept},
            adapter=ADAPTER, adapter_version=ADAPTER_VERSION,
        )
        for name in ("chembl", "hgnc", "uniprot", "pubchem", "ols4")
    }
    chembl, hgnc, uniprot, pubchem, ols = (
        archives["chembl"], archives["hgnc"], archives["uniprot"],
        archives["pubchem"], archives["ols4"],
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT mention.intervention_mention_id,mention.literal_name,
                          trial.latest_source_record_version_id
                   FROM pv_core.intervention_mention mention
                   JOIN pv_core.trial trial USING (nct_id)
                   WHERE mention.nct_id=%s AND mention.intervention_type IN ('DRUG','BIOLOGICAL')
                     AND lower(mention.literal_name)=lower(%s)""",
                (args.nct_id, args.intervention),
            )
            mentions = cur.fetchall()
            if len(mentions) != 1:
                raise RuntimeError("Intervention literal is not unique in the selected trial")
            mention_id, literal_name, trial_version_id = mentions[0]
            cur.execute(
                """SELECT condition_mention_id,source_path,literal_name
                   FROM pv_core.condition_mention
                   WHERE nct_id=%s AND lower(literal_name)=lower(%s)""",
                (args.nct_id, args.condition),
            )
            conditions = cur.fetchall()
            if len(conditions) != 1:
                raise RuntimeError("Condition literal is not unique in the selected trial")
            condition_mention_id, condition_path, condition_literal = conditions[0]

        match = exact_parent(chembl, literal_name)
        if match is None:
            raise RuntimeError(f"No unique exact ChEMBL parent for {literal_name}")
        molecule, molecule_version = match
        asset_id = promote_asset(conn, chembl, pubchem, molecule, molecule_version)
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO pv_core.trial_asset_link
                     (nct_id,asset_entity_id,intervention_mention_id,link_role,
                      source_record_version_id,resolution_status,resolution_method,support_text)
                   VALUES (%s,%s,%s,'registered_intervention',%s,'resolved',
                           'exact_registry_literal_then_chembl_parent',%s)
                   ON CONFLICT DO NOTHING""",
                (args.nct_id, str(asset_id), mention_id, trial_version_id, literal_name),
            )
            cur.execute(
                """UPDATE pv_core.intervention_mention SET normalization_status='resolved'
                   WHERE intervention_mention_id=%s""",
                (mention_id,),
            )
        conn.commit()

        target_rows: list[dict[str, Any]] = []
        mechanism_rows: list[dict[str, Any]] = []
        for mechanism, mechanism_version in complete_mechanisms(
            chembl, molecule["molecule_chembl_id"]
        ):
            if not mechanism.get("target_chembl_id"):
                mechanism_id = promote_targetless_mechanism(
                    conn, asset_id, mechanism, mechanism_version
                )
                mechanism_rows.append({"mechanism_id": mechanism_id})
                continue
            target_id, target_payload, _target_version = promote_target(
                conn, chembl, hgnc, uniprot, mechanism["target_chembl_id"]
            )
            target_rows.append({
                "target_id": target_id,
                "taxon_id": 9606 if target_payload.get("organism") == "Homo sapiens" else 0,
            })
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO pv_evidence.asset_target_assertion
                         (asset_entity_id,target_entity_id,action_literal,action_normalized,
                          role,directness,source_record_version_id,support_quote,
                          source_native_id,support_locator,relationship_origin)
                       VALUES (%s,%s,%s,%s,'therapeutic_primary',%s,%s,%s,%s,%s,
                               'structured_database')
                       ON CONFLICT DO NOTHING""",
                    (
                        str(asset_id), str(target_id),
                        mechanism.get("action_type") or "UNKNOWN",
                        ACTION_MAP.get(mechanism.get("action_type") or "", "unknown"),
                        "direct" if mechanism.get("direct_interaction") == 1 else "unknown",
                        mechanism_version, mechanism_support_quote(mechanism),
                        f"ChEMBL mechanism:{mechanism['mec_id']}",
                        Json({
                            "mec_id": mechanism["mec_id"],
                            "target_chembl_id": mechanism["target_chembl_id"],
                            "molecule_chembl_id": mechanism["molecule_chembl_id"],
                            "mechanism_of_action": mechanism.get("mechanism_of_action"),
                            "action_type": mechanism.get("action_type"),
                        }),
                    ),
                )
            conn.commit()

        condition_concept = args.condition_concept or condition_literal
        ontology_match = exact_ontology_match(ols, condition_concept, "disease")
        if ontology_match is None:
            raise RuntimeError(f"No unique exact ontology match for {condition_concept}")
        ontology_row, ontology_version = ontology_match
        obo_id = ontology_row["obo_id"]
        namespace = obo_id.split(":", 1)[0]
        phenotype_id = uuid.uuid5(PHENOTYPE_NAMESPACE, obo_id.casefold())
        preferred = ontology_row.get("label") or condition_literal
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO pv_core.entity(entity_id,entity_type,preferred_name)
                   VALUES (%s,'phenotype',%s) ON CONFLICT (entity_id) DO UPDATE SET
                     preferred_name=EXCLUDED.preferred_name""",
                (str(phenotype_id), preferred),
            )
            cur.execute(
                """INSERT INTO pv_core.phenotype
                     (entity_id,ontology_namespace,ontology_identifier,preferred_name,phenotype_kind)
                   VALUES (%s,%s,%s,%s,'disease') ON CONFLICT (entity_id) DO UPDATE SET
                     preferred_name=EXCLUDED.preferred_name""",
                (str(phenotype_id), namespace, obo_id, preferred),
            )
            cur.execute(
                """INSERT INTO pv_core.entity_identifier
                     (entity_id,namespace,identifier,source_release_id,is_preferred)
                   VALUES (%s,%s,%s,%s,true) ON CONFLICT DO NOTHING""",
                (str(phenotype_id), namespace, obo_id, ols.release_id),
            )
            insert_phenotype_alias(
                cur, phenotype_id, preferred, "preferred_label", ols.release_id,
                ontology_version,
            )
            if normalized(condition_literal) != normalized(preferred):
                insert_phenotype_alias(
                    cur, phenotype_id, condition_literal, "query_label", ols.release_id,
                    ontology_version,
                )
            for synonym in ontology_row.get("exact_synonyms") or []:
                insert_phenotype_alias(
                    cur, phenotype_id, synonym, "exact_synonym", ols.release_id,
                    ontology_version,
                )
            cur.execute(
                """INSERT INTO pv_core.trial_indication_link
                     (nct_id,phenotype_entity_id,condition_mention_id,indication_role,
                      source_record_version_id,resolution_method)
                   VALUES (%s,%s,%s,'treatment',%s,
                           'exact_registry_condition_then_ols_native_id')
                   ON CONFLICT DO NOTHING RETURNING trial_indication_link_id""",
                (args.nct_id, str(phenotype_id), condition_mention_id, trial_version_id),
            )
            inserted = cur.fetchone()
            if inserted:
                indication_link_id = inserted[0]
            else:
                cur.execute(
                    """SELECT trial_indication_link_id FROM pv_core.trial_indication_link
                       WHERE nct_id=%s AND phenotype_entity_id=%s
                         AND indication_role='treatment' AND source_record_version_id=%s""",
                    (args.nct_id, str(phenotype_id), trial_version_id),
                )
                indication_link_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO pv_evidence.trial_indication_evidence
                     (trial_indication_link_id,source_path,support_quote,evidence_role,detail)
                   VALUES (%s,%s,%s,'literal_condition',%s) ON CONFLICT DO NOTHING""",
                (indication_link_id, condition_path, condition_literal,
                 Json({"normalization": "exact_registry_condition"})),
            )
            cur.execute(
                """INSERT INTO pv_evidence.trial_indication_evidence
                     (trial_indication_link_id,source_path,support_quote,evidence_role,detail)
                   VALUES (%s,%s,%s,'ontology_mapping',%s) ON CONFLICT DO NOTHING""",
                (indication_link_id, f"OLS4:{obo_id}", preferred,
                 Json({"ontology_identifier": obo_id})),
            )
            insert_scope(
                cur, args.nct_id, asset_id, molecule.get("pref_name") or literal_name,
                molecule, target_rows, mechanism_rows,
            )
            insert_cohort(cur, args.nct_id, args.cohort_id)
        conn.commit()
        for archive in archives.values():
            archive.finish()
        print(json.dumps({
            "nct_id": args.nct_id,
            "asset_id": str(asset_id),
            "asset": molecule.get("pref_name"),
            "target_ids": [str(row["target_id"]) for row in target_rows],
            "mechanism_ids": [
                str(row["mechanism_id"]) for row in mechanism_rows
            ],
            "phenotype_id": str(phenotype_id),
            "phenotype": preferred,
            "cohort_id": args.cohort_id,
        }, indent=2))
    except BaseException as exc:
        conn.rollback()
        for archive in archives.values():
            archive.fail(f"{type(exc).__name__}: {exc}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
