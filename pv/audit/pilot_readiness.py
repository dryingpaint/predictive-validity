"""Export a human-readable and JSON audit of the ten-trial PV pilot."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2


LLM_RUN_ID = "e3e68b5a-5e4a-4b63-935f-84fe829dc972"


def rows(cur: Any, query: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cur.execute(query, parameters)
    names = [item.name for item in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


def scalar(cur: Any, query: str, parameters: tuple[Any, ...] = ()) -> int:
    cur.execute(query, parameters)
    return int(cur.fetchone()[0])


def build(conn: Any) -> dict[str, Any]:
    with conn.cursor() as cur:
        trials = rows(
            cur,
            """SELECT t.nct_id,t.brief_title,t.first_posted_date,
                      t.completion_date_text,t.completion_date_type,
                      t.study_type,t.conditions,
                      d.parsed_output->>'trial_kind' AS semantic_trial_kind,
                      (d.parsed_output->>'review_required')::boolean AS llm_review_required,
                      scope.scope_status,scope.scope_category,scope.reason_code AS scope_reason,
                      scope.policy_version AS scope_policy_version
               FROM pv_core.trial t
               JOIN pv_evidence.llm_decision d ON d.subject_key=t.nct_id
                AND d.decision_run_id=%s
               LEFT JOIN pv_core.trial_development_scope scope ON scope.nct_id=t.nct_id
               ORDER BY t.first_posted_date,t.nct_id""", (LLM_RUN_ID,),
        )
        for trial in trials:
            nct_id = trial["nct_id"]
            trial["first_posted_date"] = trial["first_posted_date"].isoformat()
            trial["assets"] = rows(
                cur,
                """SELECT a.active_moiety_name AS name,tal.link_role,tal.resolution_method,
                          array_agg(DISTINCT i.namespace||':'||i.identifier ORDER BY i.namespace||':'||i.identifier) AS identifiers
                   FROM pv_core.trial_asset_link tal JOIN pv_core.asset a ON a.entity_id=tal.asset_entity_id
                   LEFT JOIN pv_core.entity_identifier i ON i.entity_id=a.entity_id
                   WHERE tal.nct_id=%s GROUP BY a.entity_id,a.active_moiety_name,tal.link_role,tal.resolution_method
                   ORDER BY a.active_moiety_name,tal.link_role""", (nct_id,),
            )
            trial["indications"] = rows(
                cur,
                """SELECT p.preferred_name AS name,p.ontology_identifier AS identifier,
                          til.indication_role,til.resolution_method
                   FROM pv_core.trial_indication_link til
                   JOIN pv_core.phenotype p ON p.entity_id=til.phenotype_entity_id
                   WHERE til.nct_id=%s ORDER BY til.indication_role,p.preferred_name""", (nct_id,),
            )
            trial["structured_pharmacology"] = rows(
                cur,
                """SELECT DISTINCT a.active_moiety_name AS asset,
                          COALESCE(t.approved_symbol,t.approved_name) AS object,
                          t.target_kind,ata.action_normalized,ata.source_native_id
                   FROM pv_core.trial_asset_link tal
                   JOIN pv_core.asset a ON a.entity_id=tal.asset_entity_id
                   JOIN pv_evidence.asset_target_assertion ata ON ata.asset_entity_id=a.entity_id
                   JOIN pv_core.target t ON t.entity_id=ata.target_entity_id
                   WHERE tal.nct_id=%s AND ata.relationship_origin='structured_database'
                   ORDER BY asset,object,ata.action_normalized,ata.source_native_id""", (nct_id,),
            )
            trial["proposal_review"] = rows(
                cur,
                """SELECT v.proposal_kind,v.proposal_path,v.verification_status,v.detail
                   FROM pv_evidence.llm_proposal_verification v
                   JOIN pv_evidence.llm_decision d USING(llm_decision_id)
                   WHERE d.decision_run_id=%s AND d.subject_key=%s
                     AND v.verification_status NOT IN ('verified','not_applicable')
                   ORDER BY v.proposal_kind,v.proposal_path""", (LLM_RUN_ID, nct_id),
            )
            trial["literature"] = rows(
                cur,
                """WITH relevant_entities AS (
                     SELECT tal.asset_entity_id AS asset_id,NULL::uuid AS target_id
                     FROM pv_core.trial_asset_link tal WHERE tal.nct_id=%s
                     UNION ALL
                     SELECT NULL::uuid,ata.target_entity_id
                     FROM pv_core.trial_asset_link tal
                     JOIN pv_evidence.asset_target_assertion ata ON ata.asset_entity_id=tal.asset_entity_id
                     WHERE tal.nct_id=%s
                   )
                   SELECT c.candidate_kind,count(*) AS candidate_relations,
                          count(DISTINCT c.scholarly_work_id) AS unique_works,
                          count(DISTINCT c.scholarly_work_id) FILTER (
                            WHERE w.abstract_status='present') AS works_with_abstract,
                          count(DISTINCT r.scholarly_work_id) AS works_with_retained_fulltext
                   FROM pv_evidence.document_relation_candidate c
                   JOIN pv_source.scholarly_work w USING(scholarly_work_id)
                   LEFT JOIN pv_source.representation r ON r.scholarly_work_id=c.scholarly_work_id
                   WHERE EXISTS (
                     SELECT 1 FROM relevant_entities e
                     WHERE e.asset_id=c.asset_entity_id OR e.target_id=c.target_entity_id
                   )
                   GROUP BY c.candidate_kind ORDER BY c.candidate_kind""", (nct_id, nct_id),
            )

        summary = {
            "focal_trials": len(trials),
            "canonical_assets": scalar(cur, "SELECT count(*) FROM pv_core.asset"),
            "canonical_targets": scalar(cur, "SELECT count(*) FROM pv_core.target"),
            "normalized_trial_indication_links": scalar(cur, "SELECT count(*) FROM pv_core.trial_indication_link"),
            "structured_asset_target_rows": scalar(cur, "SELECT count(*) FROM pv_evidence.asset_target_assertion WHERE relationship_origin='structured_database'"),
            "scholarly_works": scalar(cur, "SELECT count(*) FROM pv_source.scholarly_work"),
            "works_with_abstract": scalar(cur, "SELECT count(*) FROM pv_source.scholarly_work WHERE abstract_status='present'"),
            "works_without_provider_abstract": scalar(cur, "SELECT count(*) FROM pv_source.scholarly_work WHERE abstract_status='not_provided_by_retrieved_sources'"),
            "works_abstract_pending": scalar(cur, "SELECT count(*) FROM pv_source.scholarly_work WHERE abstract_status='retrieval_pending'"),
            "document_candidate_relations": scalar(cur, "SELECT count(*) FROM pv_evidence.document_relation_candidate"),
            "target_literature_candidate_relations": scalar(cur, "SELECT count(*) FROM pv_evidence.document_relation_candidate WHERE candidate_kind LIKE 'target%%'"),
            "asset_preclinical_candidate_relations": scalar(cur, "SELECT count(*) FROM pv_evidence.document_relation_candidate WHERE candidate_kind LIKE 'asset%%'"),
            "retained_jats": scalar(cur, "SELECT count(*) FROM pv_source.representation WHERE representation_kind='full_text_jats'"),
            "retained_pdfs": scalar(cur, "SELECT count(*) FROM pv_source.representation WHERE representation_kind='full_text_pdf'"),
            "gcs_objects": scalar(cur, "SELECT count(*) FROM pv_source.object_blob"),
            "preclinical_experiments_extracted": scalar(cur, "SELECT count(*) FROM pv_evidence.preclinical_experiment"),
            "unfinished_acquisition_runs": scalar(cur, "SELECT count(*) FROM pv_source.acquisition_run WHERE status='running'"),
            "main_track_trials": scalar(cur, "SELECT count(*) FROM pv_core.trial_development_scope WHERE scope_status='included'"),
            "separate_vaccine_trials": scalar(cur, "SELECT count(*) FROM pv_core.trial_development_scope WHERE scope_status='separate' AND scope_category='vaccine'"),
            "excluded_non_human_trials": scalar(cur, "SELECT count(*) FROM pv_core.trial_development_scope WHERE scope_status='excluded' AND scope_category='non_human_target'"),
            "non_molecular_trials": scalar(cur, "SELECT count(*) FROM pv_core.trial_development_scope WHERE scope_status='not_applicable'"),
            "unresolved_scope_trials": scalar(cur, "SELECT count(*) FROM pv_core.trial_development_scope WHERE scope_status='unresolved'"),
        }
        gates = [
            {"gate": "ten legacy focal trials", "status": "pass" if len(trials) == 10 else "fail", "value": len(trials)},
            {"gate": "one LLM decision per focal trial", "status": "pass" if scalar(cur, "SELECT count(*) FROM pv_evidence.llm_decision WHERE decision_run_id=%s", (LLM_RUN_ID,)) == 10 else "fail", "value": 10},
            {"gate": "no unfinished acquisition runs", "status": "pass" if summary["unfinished_acquisition_runs"] == 0 else "fail", "value": summary["unfinished_acquisition_runs"]},
            {"gate": "related PIMPARK trial resolved", "status": "pass" if scalar(cur, "SELECT count(*) FROM pv_core.trial_relationship WHERE subject_nct_id='NCT06754553' AND object_nct_id='NCT03947216'") == 1 else "fail", "value": "NCT03947216"},
            {"gate": "uncapped target literature retained", "status": "pass" if summary["target_literature_candidate_relations"] > 8000 else "fail", "value": summary["target_literature_candidate_relations"]},
            {"gate": "asset preclinical candidates retained", "status": "pass" if summary["asset_preclinical_candidate_relations"] > 5000 else "fail", "value": summary["asset_preclinical_candidate_relations"]},
            {"gate": "repeat HTR2A search created no new versions", "status": "pass" if scalar(cur, """SELECT count(*) FROM (SELECT stored_count,reused_count FROM pv_source.acquisition_run WHERE adapter='pv.ingest.target_phenotype_literature' AND parameters->>'target'='HTR2A' AND status='completed' ORDER BY started_at DESC LIMIT 1) x WHERE stored_count=0 AND reused_count=906""") == 1 else "fail", "value": "stored=0 reused=906"},
            {"gate": "repeat pimavanserin preclinical search created no new versions", "status": "pass" if scalar(cur, """SELECT count(*) FROM (SELECT stored_count,reused_count FROM pv_source.acquisition_run WHERE adapter='pv.ingest.asset_preclinical_literature' AND parameters->>'asset'='pimavanserin' AND status='completed' ORDER BY started_at DESC LIMIT 1) x WHERE stored_count=0 AND reused_count=73""") == 1 else "fail", "value": "stored=0 reused=73"},
            {"gate": "licensed full-text path exercised", "status": "pass" if summary["retained_jats"] > 0 else "fail", "value": summary["retained_jats"]},
            {"gate": "GCS configured and populated", "status": "pass" if summary["gcs_objects"] > 0 else "warn", "value": summary["gcs_objects"]},
            {"gate": "PDF path populated", "status": "pass" if summary["retained_pdfs"] > 0 else "warn", "value": summary["retained_pdfs"]},
            {"gate": "narrative preclinical extraction", "status": "warn", "value": summary["preclinical_experiments_extracted"], "note": "explicitly deferred enrichment; candidate corpus is retained"},
            {"gate": "vaccines routed to separate track", "status": "pass" if summary["separate_vaccine_trials"] == 1 else "fail", "value": summary["separate_vaccine_trials"]},
            {"gate": "non-human targets admitted to main track", "status": "pass" if scalar(cur, "SELECT count(*) FROM pv_core.v_target_phenotype_literature_scope scoped JOIN pv_core.target target ON target.entity_id=scoped.target_entity_id WHERE target.taxon_id IS DISTINCT FROM 9606") == 0 else "fail", "value": 0},
            {"gate": "all legacy pilot trials have scope decisions", "status": "pass" if scalar(cur, "SELECT count(*) FROM pv_evidence.llm_decision d LEFT JOIN pv_core.trial_development_scope scope ON scope.nct_id=d.subject_key WHERE d.decision_run_id=%s AND scope.nct_id IS NULL", (LLM_RUN_ID,)) == 0 else "fail", "value": scalar(cur, "SELECT count(*) FROM pv_evidence.llm_decision d LEFT JOIN pv_core.trial_development_scope scope ON scope.nct_id=d.subject_key WHERE d.decision_run_id=%s AND scope.nct_id IS NULL", (LLM_RUN_ID,))},
        ]
    return {
        "schema_version": "pv.pilot-readiness/1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "registry": "ClinicalTrials.gov",
            "pilot_selection": "legacy_first_posted_2025_deterministic_first_10",
            "current_collection_definition": "actual_completion_date_interventional_drug_or_biological_2015_through_2025",
            "llm_decision_run_id": LLM_RUN_ID,
        },
        "summary": summary, "quality_gates": gates, "trials": trials,
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# PV legacy ten-trial pilot review", "",
        f"Generated: `{report['generated_at']}`", "",
        "This report preserves the original first-posted-2025 pilot. It is now a legacy formatting checkpoint and is not the cohort definition for expansion. The current definition uses INTERVENTIONAL DRUG/BIOLOGICAL studies with an ACTUAL Study Completion Date from 2015 through 2025; a replacement pilot must be run before full ingestion.", "",
        "## Collection summary", "",
        "| Item | Count |", "|---|---:|",
    ]
    for key, value in summary.items():
        lines.append(f"| {key.replace('_', ' ')} | {value} |")
    lines += ["", "## Quality gates", "", "| Gate | Status | Value |", "|---|---|---:|"]
    for gate in report["quality_gates"]:
        lines.append(f"| {gate['gate']} | {gate['status'].upper()} | {gate['value']} |")
    lines += ["", "## Trial-level format", ""]
    for trial in report["trials"]:
        lines += [f"### {trial['nct_id']} — {trial['brief_title']}", "",
                  f"- Registry/semantic type: `{trial['study_type']}` / `{trial['semantic_trial_kind']}`",
                  f"- Registry dates: first posted `{trial['first_posted_date']}`; completion `{trial['completion_date_text'] or 'missing'}` ({trial['completion_date_type'] or 'unknown'})",
                  f"- Development scope: `{trial['scope_status']}` / `{trial['scope_category']}` ({trial['scope_reason']}; policy `{trial['scope_policy_version']}`)",
                  f"- Literal registry conditions: {', '.join(trial['conditions']) or 'none'}"]
        if trial["assets"]:
            lines.append("- Canonical assets: " + "; ".join(
                f"{a['name']} ({a['link_role']}; {', '.join(a['identifiers'] or [])})" for a in trial["assets"]
            ))
        else:
            lines.append("- Canonical assets: none (non-drug or unresolved)")
        if trial["indications"]:
            lines.append("- Normalized indications: " + "; ".join(
                f"{i['name']} [{i['identifier']}, {i['indication_role']}]" for i in trial["indications"]
            ))
        else:
            lines.append("- Normalized indications: none promoted")
        if trial["structured_pharmacology"]:
            lines.append("- Complete structured pharmacology: " + "; ".join(
                f"{p['asset']} {p['action_normalized']} {p['object']} ({p['source_native_id']})"
                for p in trial["structured_pharmacology"]
            ))
        if trial["literature"]:
            lines.append("- Raw literature candidates: " + "; ".join(
                f"{item['candidate_kind']}={item['unique_works']} works/{item['works_with_abstract']} abstracts/{item['works_with_retained_fulltext']} retained full texts"
                for item in trial["literature"]
            ))
        if trial["proposal_review"]:
            lines.append("- Review queue: " + "; ".join(
                f"{item['proposal_kind']} {item['proposal_path']}={item['verification_status']}"
                for item in trial["proposal_review"]
            ))
        lines.append("")
    lines += [
        "## Interpretation", "",
        "A literature query hit is a raw candidate, not a target–phenotype assertion and not a passed preclinical test. "
        "The later extraction layer must cite exact model, assay, endpoint, result, and reported criterion passages. "
        "Missing source abstracts remain explicit rather than being fabricated.", "",
        "Development scope never deletes raw records. Policy `human_therapeutics_v1` permits literature expansion only for verified human-biology therapeutics, excludes antibiotics and non-human therapeutic targets, routes vaccines to a separate track, and holds unknown target domains unresolved.", "",
        "GCS/PDF rows remain empty when `PV_GCS_BUCKET` is not configured. The ingestion code uploads only after an explicit rights decision and stores immutable `gs://` object coordinates, not signed URLs.", "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", default="data/pv")
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        report = build(conn)
    finally:
        conn.close()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "pilot_readiness.json"
    markdown_path = output_dir / "PILOT_REVIEW.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n")
    markdown_path.write_text(markdown(report))
    print(json_path)
    print(markdown_path)


if __name__ == "__main__":
    main()
