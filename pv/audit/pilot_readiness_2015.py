"""Export the completion-date-selected five-trial 2015 PV readiness report."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2


COHORT_ID = "pv_2015_actual_completed_drug_biological_pilot5_v1"
LLM_RUN_ID = "46c3debc-ec74-450b-b9d2-788712685a7d"
POLICY_VERSION = "human_therapeutics_v2"


def rows(cur: Any, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cur.execute(sql, params)
    names = [column.name for column in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


def scalar(cur: Any, sql: str, params: tuple[Any, ...] = ()) -> int:
    cur.execute(sql, params)
    return int(cur.fetchone()[0])


def build(conn: Any) -> dict[str, Any]:
    with conn.cursor() as cur:
        trials = rows(
            cur,
            """SELECT cm.candidate_ordinal,cm.membership_status,cm.reason_code,
                      t.nct_id,t.brief_title,t.completion_date_text,t.completion_date_type,
                      t.study_type,t.conditions,d.parsed_output->>'trial_kind' AS trial_kind,
                      scope.scope_status,scope.scope_category,scope.reason_code AS scope_reason
               FROM pv_core.trial_cohort_member cm
               JOIN pv_core.trial t ON t.nct_id=cm.nct_id
               LEFT JOIN pv_evidence.llm_decision d ON d.subject_key=t.nct_id
                AND d.decision_run_id=%s
               LEFT JOIN pv_core.trial_development_scope scope ON scope.nct_id=t.nct_id
                AND scope.policy_version=%s
               WHERE cm.cohort_id=%s ORDER BY cm.candidate_ordinal""",
            (LLM_RUN_ID, POLICY_VERSION, COHORT_ID),
        )
        for trial in trials:
            nct_id = trial["nct_id"]
            trial["assets"] = rows(
                cur,
                """SELECT DISTINCT a.active_moiety_name,tal.link_role,tal.resolution_method
                   FROM pv_core.trial_asset_link tal
                   JOIN pv_core.asset a ON a.entity_id=tal.asset_entity_id
                   WHERE tal.nct_id=%s ORDER BY a.active_moiety_name,tal.link_role""",
                (nct_id,),
            )
            trial["indications"] = rows(
                cur,
                """SELECT DISTINCT p.preferred_name,p.ontology_identifier,til.indication_role
                   FROM pv_core.trial_indication_link til
                   JOIN pv_core.phenotype p ON p.entity_id=til.phenotype_entity_id
                   WHERE til.nct_id=%s ORDER BY til.indication_role,p.preferred_name""",
                (nct_id,),
            )
            trial["targets"] = rows(
                cur,
                """SELECT DISTINCT a.active_moiety_name AS asset,
                          coalesce(nullif(t.approved_symbol,''),t.approved_name) AS target,
                          t.target_kind,ata.action_normalized
                   FROM pv_core.trial_asset_link tal
                   JOIN pv_core.asset a ON a.entity_id=tal.asset_entity_id
                   JOIN pv_evidence.asset_target_assertion ata ON ata.asset_entity_id=a.entity_id
                   JOIN pv_core.target t ON t.entity_id=ata.target_entity_id
                   WHERE tal.nct_id=%s ORDER BY asset,target""",
                (nct_id,),
            )
            trial["literature"] = rows(
                cur,
                """WITH entities AS (
                     SELECT tal.asset_entity_id AS asset_id,NULL::uuid AS target_id
                     FROM pv_core.trial_asset_link tal WHERE tal.nct_id=%s
                     UNION ALL
                     SELECT NULL::uuid,ata.target_entity_id
                     FROM pv_core.trial_asset_link tal
                     JOIN pv_evidence.asset_target_assertion ata
                       ON ata.asset_entity_id=tal.asset_entity_id
                     WHERE tal.nct_id=%s
                   )
                   SELECT c.candidate_kind,count(*) AS candidate_relations,
                          count(DISTINCT c.scholarly_work_id) AS unique_works,
                          count(DISTINCT c.scholarly_work_id) FILTER (
                            WHERE sw.abstract_status='present') AS works_with_abstract
                   FROM pv_evidence.document_relation_candidate c
                   JOIN pv_source.scholarly_work sw USING(scholarly_work_id)
                   WHERE EXISTS (SELECT 1 FROM entities e
                                 WHERE e.asset_id=c.asset_entity_id OR e.target_id=c.target_entity_id)
                   GROUP BY c.candidate_kind ORDER BY c.candidate_kind""",
                (nct_id, nct_id),
            )

        summary = {
            "candidate_trials": len(trials),
            "included_trials": sum(t["membership_status"] == "included" for t in trials),
            "excluded_trials": sum(t["membership_status"] == "excluded" for t in trials),
            "llm_decisions": scalar(cur, "SELECT count(*) FROM pv_evidence.llm_decision WHERE decision_run_id=%s", (LLM_RUN_ID,)),
            "included_trials_in_scope": scalar(cur, """SELECT count(*) FROM pv_core.trial_cohort_member cm JOIN pv_core.trial_development_scope s ON s.nct_id=cm.nct_id WHERE cm.cohort_id=%s AND cm.membership_status='included' AND s.policy_version=%s AND s.scope_status='included'""", (COHORT_ID, POLICY_VERSION)),
            "target_bridge_rows": scalar(cur, "SELECT count(*) FROM pv_core.legacy_target_bridge"),
            "phenotype_bridge_rows": scalar(cur, "SELECT count(*) FROM pv_core.legacy_phenotype_bridge"),
            "structured_target_phenotype_rows": scalar(cur, "SELECT count(*) FROM pv_evidence.v_structured_target_phenotype_evidence"),
            "structured_target_context_rows": scalar(cur, "SELECT count(*) FROM pv_evidence.v_structured_target_context_evidence"),
            "scholarly_works_global": scalar(cur, "SELECT count(*) FROM pv_source.scholarly_work"),
            "document_candidate_relations_global": scalar(cur, "SELECT count(*) FROM pv_evidence.document_relation_candidate"),
            "historical_pilot_asset_preclinical_relations": scalar(
                cur,
                """WITH cohort_assets AS (
                     SELECT DISTINCT tal.asset_entity_id
                     FROM pv_core.trial_cohort_member cm
                     JOIN pv_core.trial_asset_link tal USING(nct_id)
                     WHERE cm.cohort_id=%s AND cm.membership_status='included'
                   )
                   SELECT count(*)
                   FROM pv_evidence.document_relation_candidate c
                   JOIN cohort_assets ca ON ca.asset_entity_id=c.asset_entity_id
                   WHERE c.candidate_kind IN
                     ('asset_preclinical_wide','asset_indication_preclinical')""",
                (COHORT_ID,),
            ),
            "historical_pilot_asset_preclinical_unique_works": scalar(
                cur,
                """WITH cohort_assets AS (
                     SELECT DISTINCT tal.asset_entity_id
                     FROM pv_core.trial_cohort_member cm
                     JOIN pv_core.trial_asset_link tal USING(nct_id)
                     WHERE cm.cohort_id=%s AND cm.membership_status='included'
                   )
                   SELECT count(DISTINCT c.scholarly_work_id)
                   FROM pv_evidence.document_relation_candidate c
                   JOIN cohort_assets ca ON ca.asset_entity_id=c.asset_entity_id
                   WHERE c.candidate_kind IN
                     ('asset_preclinical_wide','asset_indication_preclinical')""",
                (COHORT_ID,),
            ),
            "pilot_asset_mention_relations": scalar(
                cur,
                """WITH cohort_assets AS (
                     SELECT DISTINCT tal.asset_entity_id
                     FROM pv_core.trial_cohort_member cm
                     JOIN pv_core.trial_asset_link tal USING(nct_id)
                     WHERE cm.cohort_id=%s AND cm.membership_status='included'
                   )
                   SELECT count(*)
                   FROM pv_evidence.document_relation_candidate c
                   JOIN cohort_assets ca ON ca.asset_entity_id=c.asset_entity_id
                   WHERE c.candidate_kind='asset_mention'""",
                (COHORT_ID,),
            ),
            "pilot_asset_mention_unique_works": scalar(
                cur,
                """WITH cohort_assets AS (
                     SELECT DISTINCT tal.asset_entity_id
                     FROM pv_core.trial_cohort_member cm
                     JOIN pv_core.trial_asset_link tal USING(nct_id)
                     WHERE cm.cohort_id=%s AND cm.membership_status='included'
                   )
                   SELECT count(DISTINCT c.scholarly_work_id)
                   FROM pv_evidence.document_relation_candidate c
                   JOIN cohort_assets ca ON ca.asset_entity_id=c.asset_entity_id
                   WHERE c.candidate_kind='asset_mention'""",
                (COHORT_ID,),
            ),
            "retained_jats": scalar(cur, "SELECT count(*) FROM pv_source.representation WHERE representation_kind='full_text_jats'"),
            "retained_pdfs": scalar(cur, "SELECT count(*) FROM pv_source.representation WHERE representation_kind='full_text_pdf'"),
            "gcs_objects": scalar(cur, "SELECT count(*) FROM pv_source.object_blob"),
            "preclinical_experiments_extracted": scalar(cur, "SELECT count(*) FROM pv_evidence.preclinical_experiment"),
        }
        latest_verification = """WITH latest AS (
          SELECT DISTINCT ON (v.llm_decision_id,v.proposal_kind,v.proposal_path,v.verifier)
                 v.verification_status
          FROM pv_evidence.llm_proposal_verification v
          JOIN pv_evidence.llm_decision d USING(llm_decision_id)
          WHERE d.decision_run_id=%s AND v.proposal_kind=%s
          ORDER BY v.llm_decision_id,v.proposal_kind,v.proposal_path,v.verifier,
                   v.created_at DESC,v.llm_proposal_verification_id DESC
        ) SELECT count(*) FROM latest WHERE verification_status IN ('unresolved','ambiguous','conflicting')"""
        unresolved_assets = scalar(cur, latest_verification, (LLM_RUN_ID, "asset"))
        unresolved_indications = scalar(
            cur, latest_verification, (LLM_RUN_ID, "indication")
        )
        incomplete_literature_items = scalar(
            cur,
            "SELECT count(*) FROM pv_source.literature_work_item "
            "WHERE cohort_id=%s AND status<>'completed'",
            (COHORT_ID,),
        )
        duplicate_work_keys = scalar(
            cur,
            "SELECT count(*)-count(DISTINCT work_key) "
            "FROM pv_source.literature_work_item WHERE cohort_id=%s",
            (COHORT_ID,),
        )
        duplicate_candidates = scalar(
            cur,
            """SELECT count(*) FROM (
                 SELECT scholarly_work_id,target_entity_id,phenotype_entity_id,
                        mechanism_entity_id,asset_entity_id,candidate_kind
                 FROM pv_evidence.document_relation_candidate
                 GROUP BY 1,2,3,4,5,6 HAVING count(*)>1
               ) d""",
        )
        missing_asset_mentions = scalar(
            cur,
            """WITH cohort_assets AS (
                 SELECT DISTINCT tal.asset_entity_id
                 FROM pv_core.trial_cohort_member cm
                 JOIN pv_core.trial_asset_link tal USING(nct_id)
                 WHERE cm.cohort_id=%s AND cm.membership_status='included'
               ), old_pairs AS (
                 SELECT DISTINCT c.asset_entity_id,c.scholarly_work_id
                 FROM pv_evidence.document_relation_candidate c
                 JOIN cohort_assets ca USING(asset_entity_id)
                 WHERE c.candidate_kind IN (
                   'asset_preclinical_wide','asset_indication_preclinical'
                 )
               ), new_pairs AS (
                 SELECT DISTINCT c.asset_entity_id,c.scholarly_work_id
                 FROM pv_evidence.document_relation_candidate c
                 JOIN cohort_assets ca USING(asset_entity_id)
                 WHERE c.candidate_kind='asset_mention'
               )
               SELECT count(*) FROM (
                 SELECT * FROM old_pairs EXCEPT SELECT * FROM new_pairs
               ) missing""",
            (COHORT_ID,),
        )
        pending_pmid_abstracts = scalar(
            cur,
            """SELECT count(*) FROM pv_source.scholarly_work w
               WHERE w.abstract_status='retrieval_pending' AND EXISTS (
                 SELECT 1 FROM pv_source.scholarly_work_identifier i
                 WHERE i.scholarly_work_id=w.scholarly_work_id
                   AND i.namespace='PMID'
               )""",
        )
        unfinished_runs = scalar(
            cur, "SELECT count(*) FROM pv_source.acquisition_run WHERE status='running'"
        )
        gates = [
            ("ten deterministic candidates retained", len(trials) == 10, len(trials)),
            ("five reviewed inclusions", summary["included_trials"] == 5, summary["included_trials"]),
            ("one LLM decision per inclusion", summary["llm_decisions"] == 5, summary["llm_decisions"]),
            ("all five inclusions in development scope", summary["included_trials_in_scope"] == 5, summary["included_trials_in_scope"]),
            ("no unresolved latest asset proposal", unresolved_assets == 0, unresolved_assets),
            ("no unresolved latest indication proposal", unresolved_indications == 0, unresolved_indications),
            ("literature queue complete", incomplete_literature_items == 0, incomplete_literature_items),
            ("no duplicate literature work keys", duplicate_work_keys == 0, duplicate_work_keys),
            ("no duplicate canonical document candidates", duplicate_candidates == 0, duplicate_candidates),
            ("asset mention corpus contains every historical preclinical pair", missing_asset_mentions == 0, missing_asset_mentions),
            ("no PMID-backed abstract remains pending", pending_pmid_abstracts == 0, pending_pmid_abstracts),
            ("no unfinished acquisition runs", unfinished_runs == 0, unfinished_runs),
        ]
    quality_gates = [
        {"gate": name, "status": "pass" if passed else "fail", "value": value}
        for name, passed, value in gates
    ]
    quality_gates.extend([
        {"gate": "GCS configured and populated", "status": "pass" if summary["gcs_objects"] else "warn", "value": summary["gcs_objects"]},
        {"gate": "narrative preclinical experiment extraction", "status": "warn", "value": summary["preclinical_experiments_extracted"], "note": "downstream enrichment over retained asset-specific documents"},
    ])
    return {
        "schema_version": "pv.pilot-readiness-2015/1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cohort_id": COHORT_ID,
        "llm_decision_run_id": LLM_RUN_ID,
        "policy_version": POLICY_VERSION,
        "summary": summary,
        "quality_gates": quality_gates,
        "trials": trials,
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PV 2015 five-trial pilot readiness", "",
        f"Generated: `{report['generated_at']}`", "",
        f"Cohort: `{report['cohort_id']}`", "",
        "## Summary", "", "| Item | Count |", "|---|---:|",
    ]
    for key, value in report["summary"].items():
        lines.append(f"| {key.replace('_',' ')} | {value} |")
    lines += ["", "## Quality gates", "", "| Gate | Status | Value |", "|---|---|---:|"]
    for gate in report["quality_gates"]:
        lines.append(f"| {gate['gate']} | {gate['status'].upper()} | {gate['value']} |")
    lines += ["", "## Trial review", ""]
    for trial in report["trials"]:
        lines += [f"### {trial['candidate_ordinal']}. {trial['nct_id']} — {trial['brief_title']}", "",
                  f"- Cohort: `{trial['membership_status']}` (`{trial['reason_code']}`)",
                  f"- Completion: `{trial['completion_date_text']}` (`{trial['completion_date_type']}`)"]
        if trial["membership_status"] == "included":
            lines.append(f"- Scope: `{trial['scope_status']}` / `{trial['scope_category']}`")
            lines.append("- Assets: " + ", ".join(a["active_moiety_name"] for a in trial["assets"]))
            indication_text = ", ".join(
                f"{p['preferred_name']} [{p['ontology_identifier']}; {p['indication_role']}]"
                for p in trial["indications"]
            )
            lines.append(
                "- Indications: "
                + (indication_text or "none (healthy-volunteer/non-disease study)")
            )
            target_text = ", ".join(
                f"{t['asset']} → {t['target']} ({t['action_normalized']})" for t in trial["targets"]
            )
            lines.append("- Targets: " + (target_text or "none verified"))
            literature_text = ", ".join(
                f"{x['candidate_kind']}={x['unique_works']} works" for x in trial["literature"]
            )
            lines.append("- Literature: " + (literature_text or "none retrieved"))
        lines.append("")
    lines += [
        "## Boundary", "",
        "Asset-mention retrieval is raw ingestion. A mention is not a preclinical claim. Document relevance classification and extraction of individual models, assays, endpoints, criteria, and positive/negative/null results are separate downstream enrichments over the frozen documents.", "",
        "A query hit remains a candidate relation, not a biological assertion. Legacy structured sources preserve their originating row and are not counted as independent evidence merely because Open Targets also aggregates them.", "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", default="data/pv/2015_pilot")
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        report = build(conn)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "pilot_readiness.json"
    md_path = output / "PILOT_REVIEW.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n")
    md_path.write_text(markdown(report))
    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()
