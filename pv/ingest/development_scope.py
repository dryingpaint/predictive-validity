"""Classify trials and assets under the versioned human-therapeutics policy.

All selected raw records remain in the database.  These materialized decisions
only decide whether downstream target/phenotype and preclinical literature
expansion may run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

import psycopg2
from psycopg2.extras import Json


POLICY_VERSION = "human_therapeutics_v2"
CLASSIFICATION_METHOD = "deterministic_v2"
HUMAN_TAXON_ID = 9606

# ATC groups explicitly denoting antibacterial products.  The target-taxon
# rule independently excludes other pathogen-directed anti-infectives.
ANTIBIOTIC_ATC_PREFIXES = (
    "A07AA",  # intestinal anti-infectives: antibiotics
    "D06A",   # antibiotics and chemotherapeutics for dermatological use
    "G01A",   # gynecological anti-infectives and antiseptics
    "J01",    # antibacterials for systemic use
    "R02AB",  # antibiotics for throat preparations
    "S01AA",  # ophthalmological anti-infectives
    "S02AA",  # otological anti-infectives
    "S03AA",  # ophthalmological/otological anti-infectives
)
NON_MOLECULAR_TRIAL_KINDS = {
    "behavioral", "device", "diagnostic", "exercise", "observational_exposure",
}


@dataclass(frozen=True)
class AssetDecision:
    status: str
    category: str
    reason: str
    basis: dict[str, Any]


def classify_asset(atc_codes: list[str], target_taxa: list[int | None]) -> AssetDecision:
    antibiotic_codes = sorted({
        code for code in atc_codes
        if any(code.upper().startswith(prefix) for prefix in ANTIBIOTIC_ATC_PREFIXES)
    })
    if antibiotic_codes:
        return AssetDecision(
            "excluded", "antibiotic", "antibiotic_atc_class",
            {"atc_codes": sorted(set(atc_codes)), "matched_antibiotic_codes": antibiotic_codes},
        )

    known_taxa = {taxon for taxon in target_taxa if taxon is not None}
    unknown_target_count = sum(taxon is None for taxon in target_taxa)
    basis = {
        "therapeutic_primary_target_taxa": sorted(known_taxa),
        "unknown_target_taxon_count": unknown_target_count,
    }
    non_human = known_taxa - {HUMAN_TAXON_ID}
    if non_human and HUMAN_TAXON_ID in known_taxa:
        return AssetDecision(
            "excluded", "mixed_human_non_human_target", "has_non_human_therapeutic_target", basis,
        )
    if non_human:
        return AssetDecision(
            "excluded", "non_human_target", "non_human_therapeutic_target", basis,
        )
    if known_taxa == {HUMAN_TAXON_ID} and unknown_target_count == 0:
        return AssetDecision(
            "included", "human_therapeutic", "verified_human_therapeutic_targets", basis,
        )
    return AssetDecision(
        "unresolved", "unknown_target_domain", "target_domain_not_fully_resolved", basis,
    )


def decision_hash(value: dict[str, Any]) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def latest_trial_decisions(cur: Any) -> list[tuple[str, str, Any]]:
    cur.execute(
        """SELECT DISTINCT ON (d.subject_key)
                  d.subject_key,d.parsed_output->>'trial_kind',d.llm_decision_id
           FROM pv_evidence.llm_decision d
           JOIN pv_core.trial t ON t.nct_id=d.subject_key
           WHERE d.task='trial_semantic_extraction'
             AND d.validation_status='validated'
           ORDER BY d.subject_key,d.created_at DESC,d.llm_decision_id DESC"""
    )
    return cur.fetchall()


def asset_inputs(cur: Any) -> list[tuple[Any, str, list[dict[str, Any]], list[dict[str, Any]]]]:
    cur.execute(
        """WITH latest_chembl AS (
             SELECT DISTINCT ON (record.source_record_id)
                    record.native_record_id,version.source_record_version_id,
                    version.raw_payload
             FROM pv_source.source_record record
             JOIN pv_source.source_record_version version
               ON version.source_record_id=record.source_record_id
             WHERE record.source_system_id='chembl'
               AND record.record_type='molecule_record'
             ORDER BY record.source_record_id,version.retrieved_at DESC,
                      version.source_record_version_id DESC
           )
           SELECT a.entity_id,a.active_moiety_name,
                  COALESCE((
                    SELECT jsonb_agg(DISTINCT jsonb_build_object(
                      'atc_code',atc_code,
                      'source_record_version_id',chembl.source_record_version_id
                    ))
                    FROM pv_core.entity_identifier identifier
                    JOIN latest_chembl chembl
                      ON chembl.native_record_id=identifier.identifier
                    CROSS JOIN LATERAL jsonb_array_elements_text(
                      COALESCE(chembl.raw_payload->'atc_classifications','[]'::jsonb)
                    ) atc(atc_code)
                    WHERE identifier.entity_id=a.entity_id
                      AND identifier.namespace='ChEMBL'
                  ),'[]'::jsonb) AS atc_evidence,
                  COALESCE((
                    SELECT jsonb_agg(DISTINCT jsonb_build_object(
                      'asset_target_assertion_id',assertion.asset_target_assertion_id,
                      'target_taxon_id',target.taxon_id,
                      'source_native_id',assertion.source_native_id,
                      'source_record_version_id',assertion.source_record_version_id
                    ))
                    FROM pv_evidence.asset_target_assertion assertion
                    JOIN pv_core.target target ON target.entity_id=assertion.target_entity_id
                    WHERE assertion.asset_entity_id=a.entity_id
                      AND assertion.role='therapeutic_primary'
                  ),'[]'::jsonb) AS target_evidence
           FROM pv_core.asset a
           ORDER BY a.active_moiety_name,a.entity_id"""
    )
    return cur.fetchall()


def classify(commit: bool) -> dict[str, Any]:
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    report: dict[str, Any] = {"policy_version": POLICY_VERSION, "assets": [], "trials": []}
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pv_core.development_scope_policy WHERE policy_version=%s",
                (POLICY_VERSION,),
            )
            if cur.fetchone() is None:
                raise SystemExit("Apply migration 38 before classifying development scope")

            asset_decisions: dict[Any, AssetDecision] = {}
            for asset_id, asset_name, atc_evidence, target_evidence in asset_inputs(cur):
                atc_codes = [item["atc_code"] for item in atc_evidence]
                target_taxa = [item["target_taxon_id"] for item in target_evidence]
                classified = classify_asset(atc_codes, target_taxa)
                decision = AssetDecision(
                    classified.status, classified.category, classified.reason,
                    {
                        **classified.basis,
                        "atc_evidence": atc_evidence,
                        "target_evidence": target_evidence,
                    },
                )
                asset_decisions[asset_id] = decision
                report["assets"].append({
                    "asset": asset_name, "status": decision.status,
                    "category": decision.category, "reason": decision.reason,
                    "basis": decision.basis,
                })
                if commit:
                    history = {
                        "status": decision.status, "category": decision.category,
                        "reason": decision.reason, "method": CLASSIFICATION_METHOD,
                        "basis": decision.basis,
                    }
                    cur.execute(
                        """INSERT INTO pv_core.asset_development_scope_history
                             (asset_entity_id,policy_version,decision_sha256,scope_status,
                              scope_category,reason_code,classification_method,decision_basis)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT DO NOTHING""",
                        (str(asset_id), POLICY_VERSION, decision_hash(history), decision.status,
                         decision.category, decision.reason, CLASSIFICATION_METHOD, Json(decision.basis)),
                    )
                    cur.execute(
                        """INSERT INTO pv_core.asset_development_scope
                             (asset_entity_id,policy_version,scope_status,scope_category,
                              reason_code,classification_method,decision_basis)
                           VALUES (%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (asset_entity_id,policy_version) DO UPDATE SET
                             policy_version=EXCLUDED.policy_version,
                             scope_status=EXCLUDED.scope_status,
                             scope_category=EXCLUDED.scope_category,
                             reason_code=EXCLUDED.reason_code,
                             classification_method=EXCLUDED.classification_method,
                             decision_basis=EXCLUDED.decision_basis,
                             classified_at=now()
                           WHERE (pv_core.asset_development_scope.policy_version,
                                  pv_core.asset_development_scope.scope_status,
                                  pv_core.asset_development_scope.scope_category,
                                  pv_core.asset_development_scope.reason_code,
                                  pv_core.asset_development_scope.classification_method,
                                  pv_core.asset_development_scope.decision_basis)
                             IS DISTINCT FROM
                                 (EXCLUDED.policy_version,EXCLUDED.scope_status,
                                  EXCLUDED.scope_category,EXCLUDED.reason_code,
                                  EXCLUDED.classification_method,EXCLUDED.decision_basis)""",
                        (str(asset_id), POLICY_VERSION, decision.status, decision.category,
                         decision.reason, CLASSIFICATION_METHOD, Json(decision.basis)),
                    )

            for nct_id, trial_kind, llm_decision_id in latest_trial_decisions(cur):
                cur.execute(
                    """SELECT DISTINCT asset_entity_id FROM pv_core.trial_asset_link
                       WHERE nct_id=%s AND resolution_status='resolved'""", (nct_id,),
                )
                linked_asset_ids = [row[0] for row in cur.fetchall()]
                linked = [asset_decisions[asset_id] for asset_id in linked_asset_ids]
                if trial_kind == "vaccine":
                    status, category, reason = "separate", "vaccine", "vaccine_separate_track"
                elif any(item.status == "excluded" for item in linked):
                    status, category, reason = (
                        "excluded", "non_human_target", "contains_excluded_asset"
                    )
                elif linked and all(item.status == "included" for item in linked):
                    status, category, reason = (
                        "included", "human_therapeutic",
                        ("verified_asset_overrides_coarse_trial_kind"
                         if trial_kind in NON_MOLECULAR_TRIAL_KINDS
                         else "all_resolved_assets_in_scope")
                    )
                elif trial_kind in NON_MOLECULAR_TRIAL_KINDS:
                    status, category, reason = (
                        "not_applicable", "non_molecular_intervention", "non_molecular_trial_kind"
                    )
                else:
                    status, category, reason = (
                        "unresolved", "unknown_target_domain", "no_fully_resolved_in_scope_asset"
                    )
                basis = {
                    "trial_kind": trial_kind,
                    "asset_statuses": sorted({item.status for item in linked}),
                    "asset_count": len(linked),
                }
                report["trials"].append({
                    "nct_id": nct_id, "trial_kind": trial_kind, "status": status,
                    "category": category, "reason": reason, "basis": basis,
                })
                if commit:
                    history = {
                        "status": status, "category": category, "reason": reason,
                        "method": CLASSIFICATION_METHOD, "llm_decision_id": llm_decision_id,
                        "basis": basis,
                    }
                    cur.execute(
                        """INSERT INTO pv_core.trial_development_scope_history
                             (nct_id,policy_version,decision_sha256,scope_status,scope_category,
                              reason_code,classification_method,llm_decision_id,decision_basis)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT DO NOTHING""",
                        (nct_id, POLICY_VERSION, decision_hash(history), status, category,
                         reason, CLASSIFICATION_METHOD, llm_decision_id, Json(basis)),
                    )
                    cur.execute(
                        """INSERT INTO pv_core.trial_development_scope
                             (nct_id,policy_version,scope_status,scope_category,reason_code,
                              classification_method,llm_decision_id,decision_basis)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (nct_id,policy_version) DO UPDATE SET
                             policy_version=EXCLUDED.policy_version,
                             scope_status=EXCLUDED.scope_status,
                             scope_category=EXCLUDED.scope_category,
                             reason_code=EXCLUDED.reason_code,
                             classification_method=EXCLUDED.classification_method,
                             llm_decision_id=EXCLUDED.llm_decision_id,
                             decision_basis=EXCLUDED.decision_basis,
                             classified_at=now()
                           WHERE (pv_core.trial_development_scope.policy_version,
                                  pv_core.trial_development_scope.scope_status,
                                  pv_core.trial_development_scope.scope_category,
                                  pv_core.trial_development_scope.reason_code,
                                  pv_core.trial_development_scope.classification_method,
                                  pv_core.trial_development_scope.llm_decision_id,
                                  pv_core.trial_development_scope.decision_basis)
                             IS DISTINCT FROM
                                 (EXCLUDED.policy_version,EXCLUDED.scope_status,
                                  EXCLUDED.scope_category,EXCLUDED.reason_code,
                                  EXCLUDED.classification_method,EXCLUDED.llm_decision_id,
                                  EXCLUDED.decision_basis)""",
                        (nct_id, POLICY_VERSION, status, category, reason,
                         CLASSIFICATION_METHOD, llm_decision_id, Json(basis)),
                    )
        if commit:
            conn.commit()
        else:
            conn.rollback()
    finally:
        conn.close()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--commit", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    print(json.dumps(classify(args.commit), indent=2, default=str))


if __name__ == "__main__":
    main()
