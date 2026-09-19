"""Build evidence dossiers and rescore trial stoppage with OpenAI Responses.

The legacy ``classify_why_stopped.py`` task classifies a registry status string.
This task deliberately keeps four separate questions separate: whether the
study ran far enough to be evaluated, what the scientific readout showed, why
the study stopped, and what happened to the broader development program.

Preparing dossiers is free and reads only canonical documents already stored
in PostgreSQL. Direct scoring is paid and requires ``--confirm-paid``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any, Iterable

import psycopg2

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common import CallResult, PRICING, annotate, append_jsonl, extract_json_block, read_jsonl

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


DOSSIER_SCHEMA_VERSION = "trial_stoppage_dossier_v4"
SUPPORTED_DOSSIER_SCHEMA_VERSIONS = {
    "trial_stoppage_dossier_v1", "trial_stoppage_dossier_v2",
    "trial_stoppage_dossier_v3",
    DOSSIER_SCHEMA_VERSION,
}
RESULT_SCHEMA_VERSION = "trial_stoppage_rescore_v3"
PROMPT_VERSION = "trial_stoppage_multi_axis_v17"
DEFAULT_MODEL = "gpt-5.6-terra"
MODEL_MAX_TOKENS = 2200
DEFAULT_MAX_PUBLICATIONS = 20
DEFAULT_MAX_ABSTRACT_CHARS = 6000
DEFAULT_MAX_EXTERNAL_SOURCES = 20
DEFAULT_MAX_EXTERNAL_CHARS = 8000

STUDY_EXECUTION = {
    "withdrawn_before_enrollment",
    "stopped_before_primary_analysis",
    "primary_analysis_completed",
    "completed_as_planned",
    "unknown",
}
PRIMARY_ENDPOINT_ASSESSMENT = {
    "met",
    "missed",
    "mixed",
    "not_reported",
    "not_applicable",
    "unclear",
}
SCIENTIFIC_OUTCOME = {
    "efficacy_success",
    "confirmed_efficacy_failure",
    "probable_efficacy_failure",
    "safety_failure",
    "unfavorable_benefit_risk",
    "mixed_or_inconclusive",
    "not_efficacy_evaluable",
    "unknown",
}
TERMINATION_DRIVER = {
    "efficacy",
    "positive_efficacy_progression",
    "safety",
    "unfavorable_benefit_risk",
    "commercial_strategic",
    "competitive_landscape",
    "enrollment_operational",
    "manufacturing_supply",
    "pk_pd_formulation",
    "pandemic_external",
    "regulatory_administrative",
    "planned_or_not_applicable",
    "unknown",
}
PROGRAM_OUTCOME = {
    "continued",
    "discontinued",
    "followup_only_stopped",
    "unknown",
}
PROGRAM_OUTCOME_SCOPE = {
    "target_indication", "protocol_family", "asset_global", "unknown",
}
EUPHEMISM_ASSESSMENT = {
    "confirmed_efficacy_euphemism",
    "confirmed_not_efficacy",
    "suspected_efficacy_euphemism",
    "indeterminate",
    "not_applicable",
}
CONFIDENCE = {"high", "medium", "low"}
EVIDENCE_STRENGTH = {"direct", "strong_indirect", "weak", "insufficient"}


SYSTEM_PROMPT = """You adjudicate why a clinical trial stopped using only the supplied evidence packet.

Keep these axes independent:
1. Study execution: whether the study and its primary analysis were completed.
2. Scientific outcome: what the efficacy/safety evidence showed.
3. Termination driver: the proximate reason the registry study stopped.
4. Program outcome: whether development of the intervention/indication continued.

Rules:
- A registry status of COMPLETED means trial conduct ended as planned; it does not mean efficacy success.
- TERMINATED means recruitment/treatment/follow-up ended early; it does not by itself identify why.
- "Sponsor decision", "business decision", and similar wording are not efficacy failures without corroboration.
- A generic "sponsor decision" does not itself establish a commercial/strategic driver. Use unknown unless another supplied source establishes the cause. Reserve commercial_strategic for explicit business, financing, portfolio, resource-allocation, reprioritization, or corporate-strategy evidence.
- Treat an explicit "business decision," decision not to move a compound forward, change in drug-development plan, bankruptcy, company closure, or portfolio/resource decision as commercial_strategic even when the underlying business rationale is not disclosed. A bare "sponsor decision," "company decision," or "internal decision" remains unknown without more specific evidence.
- Conversely, a business-labelled stop can coexist with successful primary endpoints. In that case keep the scientific outcome and termination driver different.
- A p-value alone is insufficient when direction, estimand, superiority/noninferiority design, multiplicity, or hierarchy is unclear. Use the supplied endpoint descriptions and analysis comments.
- confirmed_efficacy_failure requires a missed prespecified endpoint, a futility finding, or an explicit lack-of-benefit statement.
- probable_efficacy_failure requires strong indirect evidence but incomplete direct results.
- Clinical efficacy failure requires clinical efficacy evidence. Failure to achieve adequate exposure, target engagement, pharmacodynamic activity, or a viable formulation belongs under pk_pd_formulation and does not by itself establish clinical efficacy failure; use not_efficacy_evaluable unless clinical efficacy was also assessed.
- Keep scientific outcome separate from termination causality. A missed endpoint may establish scientific failure, but it does not establish efficacy as the termination driver unless a source directly links the stopping decision to efficacy/futility or the temporal and documentary evidence make that causal link explicit. Otherwise retain the stated driver or use unknown, and describe possible concealment only in euphemism_assessment.
- Preserve chronology. Results analyzed after an early commercial or financing stop can establish a scientific outcome, but they do not retroactively change the proximate termination driver without evidence that the result caused the stop.
- Parent, sibling, extension, precursor, and program-level sources are not the target trial's own scientific result. They may establish the target's termination driver only when the source explicitly links that other result or program decision to the target stop. Use the source relationship and support flags supplied in the packet.
- `source_text_kind=exact_excerpt` contains source wording; `verified_paraphrase` is a curator summary and must not be quoted or treated as stronger than its stated support flags. Prefer exact source text when the sources conflict.
- Fields prefixed `curator_` document linkage and limitations for audit; they are not source wording and cannot independently establish an endpoint, safety finding, or stopping cause. Controlled support flags/types constrain permissible use but do not substitute for the evidence excerpt.
- Do not infer that unspecified "protocol-defined stopping criteria" were efficacy criteria merely because a reported endpoint was missed. The stopping criterion itself must be identified or directly linked to efficacy/futility.
- Use efficacy as the termination driver for negative efficacy/futility decisions. If a small study stops specifically because a positive signal justifies progression to a larger study, use positive_efficacy_progression instead.
- Use competitive_landscape only when named competing therapies or a changed treatment landscape is the stated cause; do not collapse it into commercial_strategic. The phrase "competing priorities" means portfolio/resource prioritization and is commercial_strategic unless the excerpt actually identifies competing therapies or a changed treatment landscape.
- Use pandemic_external when a pandemic or pandemic-era treatment environment caused the stop, even if the immediate mechanism was enrollment difficulty.
- Use manufacturing_supply for recalls, shortages, manufacturing failures, or unavailable product, even when the sponsor describes the recall as commercial.
- Product release potency, out-of-specification material, investigational-product chemistry work, assay-driven product-quality findings, recalls, and supply shortages are manufacturing_supply. Reserve pk_pd_formulation for in-human exposure, clearance, dose/exposure feasibility, target engagement, pharmacodynamic response, route, or formulation findings.
- A comparative clinical imaging, diagnostic-performance, or disease biomarker endpoint can support an efficacy/lack-of-effect conclusion. Do not reclassify it as PK/PD merely because it is not a mortality or symptom endpoint.
- Use safety when a human or nonclinical toxicology finding causally prompted the stop. A statement that there was no human safety signal does not erase a cited preclinical toxicology driver.
- Use planned_or_not_applicable when objectives/enrollment targets were met, a planned part was successfully concluded, or the study closed after collecting sufficient data. Use commercial_strategic for reprioritization/redesign only when closure was not simply successful completion or positive-signal progression.
- Protocol replacement or an explicit move to a later-phase protocol is planned_or_not_applicable and supports program continuation. positive_efficacy_progression requires an explicit statement that a favorable efficacy signal caused progression; do not infer it solely because an endpoint was met or a new study was redesigned.
- Do not infer whole-program discontinuation merely because one trial stopped.
- Classify program_outcome as continued only with direct evidence of subsequent development, such as an identified later trial or an explicit statement that development moved forward. An author's recommendation for further study is not evidence that the sponsor actually continued development.
- Use followup_only_stopped only when a source explicitly establishes that an extension, follow-up, or protocol-family component stopped while broader target-indication or asset development continued; cite a source typed followup_only_stop and state the applicable scope.
- Set program_outcome_scope to target_indication, protocol_family, or asset_global to state exactly what the program verdict covers. Use unknown when program_outcome is unknown. Continuation in another tumor type is asset-global evidence, not target-indication continuation.
- An actual primary-completion date does not prove the primary analysis was performed. Use primary_analysis_completed only when results or a publication show the primary analysis was actually completed. Use completed_as_planned only for a completed study or explicit completion of all planned conduct, not merely because a terminated study has an actual completion date.
- Euphemism definitions: confirmed_efficacy_euphemism requires direct evidence that generic/non-efficacy registry wording concealed an efficacy/futility stop; suspected_efficacy_euphemism requires strong but nonconclusive causal evidence; confirmed_not_efficacy requires direct evidence of a non-efficacy cause; indeterminate means generic wording with insufficient evidence; not_applicable means the registry already states the scientific cause plainly.
- When a publication or other direct source explicitly says that a trial recorded as "sponsor decision" stopped for futility or lack of efficacy, use confirmed_efficacy_euphemism, not merely suspected.
- confirmed_efficacy_euphemism is valid only when termination_driver is efficacy. When generic registry wording concealed a directly documented safety or unfavorable-benefit-risk stop, use confirmed_not_efficacy rather than an efficacy-euphemism label.
- Termination driver and euphemism assessment are independent. Explicit "business decision," development-plan, portfolio, or reprioritization wording can establish commercial_strategic as the stated proximate driver, but that wording alone does not prove efficacy was unrelated. Use indeterminate for euphemism_assessment unless a specific non-efficacy event or corroborating efficacy/safety evidence supports confirmed_not_efficacy.
- positive_efficacy_progression requires a positive efficacy conclusion and direct evidence that development continued. Use efficacy_success when a favorable endpoint/result is directly established; mixed_or_inconclusive is permissible when the source directly states that a favorable efficacy signal caused progression but does not supply complete results. If a study merely met its objective without documented progression, use planned_or_not_applicable; if progression is only intended or inferred from positive results, do not label positive_efficacy_progression.
- Cite only source_document_id values present in the packet. Prefer direct registry results and results publications over background discussion.
- Always cite registry_source_document_id because the registry supplies the conduct status and stated stopping reason.
- Return nonempty, separate source-document ID arrays for scientific_outcome, termination_driver, and program_outcome. Never return an empty axis array. Put a source in an axis array only when its support flag and support_types permit that exact inference. Parent/sibling/program evidence marked supports_scientific_outcome=false must never appear in scientific_outcome_source_document_ids.
- For unknown or not-efficacy-evaluable axes, put registry_source_document_id in the corresponding axis array. For an unknown program outcome, put registry_source_document_id in program_outcome_source_document_ids. For a non-unknown program outcome, cite at least one non-registry source explicitly supporting the exact program outcome and scope.
- Set primary_endpoint_assessment to met, missed, or mixed only when a scientific-outcome source is typed primary_endpoint_status, registry_results, or publication_results. A futility or insufficient-efficacy statement without an analyzed primary-endpoint result supports the scientific outcome but not necessarily a missed primary endpoint; use not_reported or unclear as appropriate.
- If two stopping causes are explicitly stated, choose the most proximate trial-level trigger as termination_driver and preserve the other supported causes in secondary_termination_drivers. Causes joined as coequal reasons by "and" in the same causal statement are equally direct unless the source specifies otherwise; apply the precedence rule rather than choosing whichever phrase appears last. For equally direct causes, use this reproducible precedence: safety or unfavorable benefit-risk; efficacy; manufacturing/supply or PK/PD/formulation; enrollment/operational or external/pandemic; regulatory/administrative; competitive landscape; commercial/strategic; planned/not-applicable.
- If sources conflict, preserve the conflict and lower confidence. Never invent missing facts.
"""


OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "study_execution", "primary_endpoint_assessment", "scientific_outcome",
        "termination_driver", "secondary_termination_drivers",
        "program_outcome", "program_outcome_scope", "euphemism_assessment",
        "evidence_strength", "confidence", "rationale", "conflicts",
        "cited_source_document_ids", "scientific_outcome_source_document_ids",
        "termination_driver_source_document_ids",
        "program_outcome_source_document_ids",
    ],
    "properties": {
        "study_execution": {"type": "string", "enum": sorted(STUDY_EXECUTION)},
        "primary_endpoint_assessment": {
            "type": "string", "enum": sorted(PRIMARY_ENDPOINT_ASSESSMENT)
        },
        "scientific_outcome": {"type": "string", "enum": sorted(SCIENTIFIC_OUTCOME)},
        "termination_driver": {"type": "string", "enum": sorted(TERMINATION_DRIVER)},
        "secondary_termination_drivers": {
            "type": "array",
            "items": {"type": "string", "enum": sorted(TERMINATION_DRIVER - {"unknown"})},
        },
        "program_outcome": {"type": "string", "enum": sorted(PROGRAM_OUTCOME)},
        "program_outcome_scope": {
            "type": "string", "enum": sorted(PROGRAM_OUTCOME_SCOPE)
        },
        "euphemism_assessment": {"type": "string", "enum": sorted(EUPHEMISM_ASSESSMENT)},
        "evidence_strength": {"type": "string", "enum": sorted(EVIDENCE_STRENGTH)},
        "confidence": {"type": "string", "enum": sorted(CONFIDENCE)},
        "rationale": {"type": "string"},
        "conflicts": {"type": "array", "items": {"type": "string"}},
        "cited_source_document_ids": {
            "type": "array", "items": {"type": "integer"}, "minItems": 1
        },
        "scientific_outcome_source_document_ids": {
            "type": "array", "items": {"type": "integer"}, "minItems": 1
        },
        "termination_driver_source_document_ids": {
            "type": "array", "items": {"type": "integer"}, "minItems": 1
        },
        "program_outcome_source_document_ids": {
            "type": "array", "items": {"type": "integer"}, "minItems": 1
        },
    },
}
OUTPUT_FORMAT = {
    "type": "json_schema",
    "name": "trial_stoppage_rescore",
    "strict": True,
    "schema": OUTPUT_SCHEMA,
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def date_value(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    return {key: value.get(key) for key in ("date", "type") if value.get(key) is not None}


def compact_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "groupIds", "paramType", "paramValue", "dispersionType", "dispersionValue",
        "ciNumSides", "ciPctValue", "ciLowerLimit", "ciUpperLimit", "pValue",
        "pValueComment", "statisticalMethod", "statisticalComment",
        "nonInferiorityType", "nonInferiorityComment", "estimateComment",
        "groupDescription",
    )
    return {key: analysis[key] for key in keys if analysis.get(key) not in (None, "", [])}


def compact_classes(classes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retain reported arm values without copying unrelated result modules."""
    result = []
    for outcome_class in classes:
        categories = []
        for category in outcome_class.get("categories") or []:
            measurements = []
            for measurement in category.get("measurements") or []:
                keys = ("groupId", "value", "spread", "lowerLimit", "upperLimit", "comment")
                measurements.append({key: measurement[key] for key in keys if measurement.get(key) not in (None, "")})
            categories.append({
                key: value
                for key, value in {"title": category.get("title"), "measurements": measurements}.items()
                if value not in (None, "", [])
            })
        result.append({
            key: value
            for key, value in {"title": outcome_class.get("title"), "categories": categories}.items()
            if value not in (None, "", [])
        })
    return result


def compact_reported_outcome(outcome: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "type", "title", "description", "timeFrame", "populationDescription",
        "reportingStatus", "paramType", "dispersionType", "unitOfMeasure",
    )
    result = {key: outcome[key] for key in fields if outcome.get(key) not in (None, "", [])}
    result["groups"] = [
        {key: group[key] for key in ("id", "title", "description") if group.get(key) not in (None, "")}
        for group in outcome.get("groups") or []
    ]
    result["measurements"] = compact_classes(outcome.get("classes") or [])
    result["analyses"] = [compact_analysis(item) for item in outcome.get("analyses") or []]
    return {key: value for key, value in result.items() if value not in (None, "", [])}


def registry_evidence(record: dict[str, Any]) -> dict[str, Any]:
    protocol = record.get("protocolSection") or {}
    identification = protocol.get("identificationModule") or {}
    status = protocol.get("statusModule") or {}
    design = protocol.get("designModule") or {}
    sponsor = protocol.get("sponsorCollaboratorsModule") or {}
    conditions = protocol.get("conditionsModule") or {}
    interventions = (protocol.get("armsInterventionsModule") or {}).get("interventions") or []
    outcomes = protocol.get("outcomesModule") or {}
    results = record.get("resultsSection") or {}
    reported = (results.get("outcomeMeasuresModule") or {}).get("outcomeMeasures") or []
    primary_reported = [item for item in reported if str(item.get("type") or "").upper() == "PRIMARY"]
    adverse = results.get("adverseEventsModule") or {}
    return {
        "title": identification.get("officialTitle") or identification.get("briefTitle"),
        "brief_title": identification.get("briefTitle"),
        "overall_status": status.get("overallStatus"),
        "why_stopped": status.get("whyStopped"),
        "phases": design.get("phases") or [],
        "study_type": design.get("studyType"),
        "design": design.get("designInfo") or {},
        "enrollment": design.get("enrollmentInfo") or {},
        "dates": {
            "start": date_value(status.get("startDateStruct")),
            "primary_completion": date_value(status.get("primaryCompletionDateStruct")),
            "completion": date_value(status.get("completionDateStruct")),
            "results_first_post": date_value(status.get("resultsFirstPostDateStruct")),
            "last_update_post": date_value(status.get("lastUpdatePostDateStruct")),
        },
        "lead_sponsor": sponsor.get("leadSponsor") or {},
        "conditions": conditions.get("conditions") or [],
        "interventions": [
            {key: item[key] for key in ("type", "name", "description", "otherNames") if item.get(key) not in (None, "", [])}
            for item in interventions
        ],
        "protocol_primary_outcomes": outcomes.get("primaryOutcomes") or [],
        "has_results": bool(record.get("hasResults")),
        "reported_primary_outcomes": [compact_reported_outcome(item) for item in primary_reported],
        "reported_nonprimary_outcome_count": len(reported) - len(primary_reported),
        "adverse_event_summary": {
            "time_frame": adverse.get("timeFrame"),
            "groups": [
                {
                    key: group[key]
                    for key in (
                        "id", "title", "deathsNumAffected", "deathsNumAtRisk",
                        "seriousNumAffected", "seriousNumAtRisk", "otherNumAffected",
                        "otherNumAtRisk",
                    )
                    if group.get(key) is not None
                }
                for group in adverse.get("eventGroups") or []
            ],
        },
    }


def validation_selection(
    cur, per_category: int, seed: int
) -> list[dict[str, Any]]:
    """Select an evidence-profile-balanced sample within each legacy category."""
    cur.execute(
        """
        SELECT c.subject_key, c.category
        FROM preclin.classification c
        WHERE c.subject_type='trial'
          AND c.classifier_task='why_stopped'
          AND c.classifier_model='claude-sonnet'
          AND c.classifier_version='v1'
        ORDER BY c.category, c.subject_key
        """
    )
    legacy_rows = cur.fetchall()
    nct_ids = [str(row[0]) for row in legacy_rows]
    cur.execute(
        """
        SELECT DISTINCT ON (external_id)
               external_id,
               coalesce((raw_content->>'hasResults')::boolean, false),
               raw_content #>> '{protocolSection,statusModule,overallStatus}',
               raw_content #>> '{protocolSection,statusModule,whyStopped}',
               coalesce(raw_content #> '{protocolSection,designModule,phases}', '[]'::jsonb)
        FROM preclin.source_document
        WHERE source_name='clinicaltrials.gov' AND external_id=ANY(%s)
        ORDER BY external_id, retrieved_at DESC, source_document_id DESC
        """,
        (nct_ids,),
    )
    registry_by_nct = {
        str(nct_id): {
            "has_results": has_results,
            "overall_status": overall_status,
            "why_stopped": why_stopped,
            "phases": phases,
        }
        for nct_id, has_results, overall_status, why_stopped, phases in cur.fetchall()
    }
    cur.execute(
        """
        SELECT s.subject_key, count(DISTINCT s.source_document_id)
        FROM preclin.source_document_subject s
        WHERE s.subject_type='trial' AND s.subject_key=ANY(%s)
          AND s.relationship IN (
            'results_publication', 'background_publication',
            'nct_indexed_publication'
          )
        GROUP BY s.subject_key
        """,
        (nct_ids,),
    )
    publications_by_nct = {str(nct_id): int(count) for nct_id, count in cur.fetchall()}
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for nct_id, category in legacy_rows:
        registry = registry_by_nct.get(str(nct_id)) or {}
        publication_count = publications_by_nct.get(str(nct_id), 0)
        has_results = bool(registry.get("has_results"))
        has_publications = int(publication_count) > 0
        profile = (
            "results_and_publications" if has_results and has_publications
            else "results_only" if has_results
            else "publications_only" if has_publications
            else "registry_only"
        )
        by_category[str(category)].append({
            "nct_id": str(nct_id),
            "legacy_category": str(category),
            "evidence_profile": profile,
            "overall_status": registry.get("overall_status"),
            "why_stopped": registry.get("why_stopped"),
            "phases": registry.get("phases") or [],
            "has_results": has_results,
            "publication_count": int(publication_count),
        })

    def stable_order(row: dict[str, Any]) -> str:
        return sha256_text(f"{seed}:{row['nct_id']}")

    selected: list[dict[str, Any]] = []
    profiles = (
        "results_and_publications", "results_only",
        "publications_only", "registry_only",
    )
    for category in sorted(by_category):
        candidates = by_category[category]
        chosen: list[dict[str, Any]] = []
        chosen_ids: set[str] = set()
        for profile in profiles:
            eligible = sorted(
                (row for row in candidates if row["evidence_profile"] == profile),
                key=stable_order,
            )
            if eligible and len(chosen) < per_category:
                chosen.append(eligible[0])
                chosen_ids.add(eligible[0]["nct_id"])
        remaining = sorted(
            (row for row in candidates if row["nct_id"] not in chosen_ids),
            key=stable_order,
        )
        chosen.extend(remaining[: max(0, per_category - len(chosen))])
        selected.extend(chosen)
    return selected


def selected_nct_ids(cur, explicit: list[str], limit: int | None) -> list[str]:
    if explicit:
        values = sorted({value.strip().upper() for value in explicit if value.strip()})
    else:
        cur.execute(
            """SELECT DISTINCT subject_key
               FROM preclin.classification
               WHERE subject_type='trial' AND classifier_task='why_stopped'
               ORDER BY subject_key"""
        )
        values = [row[0] for row in cur.fetchall()]
    return values[:limit] if limit else values


def merge_document_link_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge every relationship attached to the same immutable document."""
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["source_document_id"])].append(row)
    relationship_rank = {
        "registry_record": 0, "results_and_termination": 1,
        "results_publication": 2, "trial_results": 3,
        "termination_evidence": 4, "background_publication": 5,
    }
    evidence_rank = {
        "exact_nct": 0, "unique_protocol": 1, "registry_linked": 2,
        "probable_composite": 3, "extension_trial": 4, "parent_trial": 5,
        "sibling_indication": 6, "program_only": 7,
    }
    merged_rows = []
    for document_id in sorted(grouped):
        linked = grouped[document_id]
        merged = dict(linked[0])
        relationships = sorted({str(item["relationship"]) for item in linked})
        metadata_values = [dict(item.get("link_metadata") or {}) for item in linked]
        evidence_relations = sorted({
            str(value["evidence_relation"])
            for value in metadata_values if value.get("evidence_relation")
        }, key=lambda value: (evidence_rank.get(value, 99), value))
        combined_metadata: dict[str, Any] = {
            "evidence_relations": evidence_relations,
            "relationship_metadata": [
                {
                    "relationship": item["relationship"],
                    "metadata": item.get("link_metadata") or {},
                }
                for item in linked
            ],
        }
        if evidence_relations:
            combined_metadata["evidence_relation"] = evidence_relations[0]
        for field in (
            "supports_scientific_outcome", "supports_termination_driver",
            "supports_program_outcome",
        ):
            combined_metadata[field] = any(bool(value.get(field)) for value in metadata_values)
        merged["relationship"] = min(
            relationships, key=lambda value: (relationship_rank.get(value, 99), value)
        )
        merged["relationships"] = relationships
        merged["link_metadata"] = combined_metadata
        merged_rows.append(merged)
    return merged_rows


def trial_documents(cur, nct_id: str) -> list[dict[str, Any]]:
    cur.execute(
        """
        WITH latest AS (
          SELECT DISTINCT ON (d.source_name, d.external_id)
                 d.source_document_id
          FROM preclin.source_document_subject s
          JOIN preclin.source_document d USING (source_document_id)
          WHERE s.subject_type='trial' AND s.subject_key=%s
          ORDER BY d.source_name, d.external_id,
                   d.retrieved_at DESC, d.source_document_id DESC
        )
        SELECT d.source_document_id, d.source_type, d.source_name, d.external_id,
               d.source_url, d.title, d.abstract_text, d.body_text, d.raw_content,
               d.content_sha256, d.metadata, s.relationship, s.link_metadata
        FROM latest l
        JOIN preclin.source_document d USING (source_document_id)
        JOIN preclin.source_document_subject s USING (source_document_id)
        WHERE s.subject_type='trial' AND s.subject_key=%s
        ORDER BY d.source_name, d.external_id, s.relationship
        """,
        (nct_id, nct_id),
    )
    columns = [item.name for item in cur.description]
    return merge_document_link_rows([
        dict(zip(columns, row)) for row in cur.fetchall()
    ])


def iter_trial_documents(conn, nct_ids: list[str]):
    """Stream latest canonical documents grouped by trial in one DB query."""
    if not nct_ids:
        return
    cur = conn.cursor(name="trial_stoppage_dossier_sources")
    cur.itersize = 100
    cur.execute(
        """
        WITH latest AS (
          SELECT DISTINCT ON (s.subject_key, d.source_name, d.external_id)
                 s.subject_key AS nct_id, d.source_document_id
          FROM preclin.source_document_subject s
          JOIN preclin.source_document d USING (source_document_id)
          WHERE s.subject_type='trial' AND s.subject_key=ANY(%s)
          ORDER BY s.subject_key, d.source_name, d.external_id,
                   d.retrieved_at DESC, d.source_document_id DESC
        )
        SELECT l.nct_id,
               d.source_document_id, d.source_type, d.source_name, d.external_id,
               d.source_url, d.title, d.abstract_text, d.body_text, d.raw_content,
               d.content_sha256, d.metadata, s.relationship, s.link_metadata
        FROM latest l
        JOIN preclin.source_document d USING (source_document_id)
        JOIN preclin.source_document_subject s USING (source_document_id)
        WHERE s.subject_type='trial' AND s.subject_key=l.nct_id
        ORDER BY l.nct_id, d.source_name, d.external_id, s.relationship
        """,
        (nct_ids,),
    )
    columns = (
        "source_document_id", "source_type", "source_name", "external_id",
        "source_url", "title", "abstract_text", "body_text", "raw_content",
        "content_sha256", "metadata", "relationship", "link_metadata",
    )
    current_nct: str | None = None
    documents: list[dict[str, Any]] = []
    for row in cur:
        nct_id = str(row[0])
        if current_nct is not None and nct_id != current_nct:
            yield current_nct, merge_document_link_rows(documents)
            documents = []
        current_nct = nct_id
        documents.append(dict(zip(columns, row[1:])))
    if current_nct is not None:
        yield current_nct, merge_document_link_rows(documents)
    cur.close()


def build_dossier(
    nct_id: str,
    documents: list[dict[str, Any]],
    max_publications: int = DEFAULT_MAX_PUBLICATIONS,
    max_abstract_chars: int = DEFAULT_MAX_ABSTRACT_CHARS,
    max_external_sources: int = DEFAULT_MAX_EXTERNAL_SOURCES,
    max_external_chars: int = DEFAULT_MAX_EXTERNAL_CHARS,
) -> dict[str, Any]:
    registry = [item for item in documents if item["source_name"] == "clinicaltrials.gov"]
    if len(registry) != 1 or not isinstance(registry[0].get("raw_content"), dict):
        raise ValueError(f"{nct_id}: expected one latest canonical ClinicalTrials.gov record")
    registry_doc = registry[0]
    registry_payload = registry_evidence(registry_doc["raw_content"])
    registry_excerpt = json.dumps(registry_payload, indent=2, sort_keys=True, ensure_ascii=False)

    publications = []
    source_inputs = [{
        "source_document_id": int(registry_doc["source_document_id"]),
        "source_name": "clinicaltrials.gov",
        "external_id": nct_id,
        "relationship": "registry_evidence_input",
        "ordinal": 0,
        "content_sha256": registry_doc["content_sha256"],
        "excerpt_text": registry_excerpt,
        "supports_scientific_outcome": bool(registry_payload.get("has_results")),
        "supports_termination_driver": True,
        "supports_program_outcome": False,
        "support_types": ["registry_results"] if registry_payload.get("has_results") else [],
    }]
    pub_docs = [item for item in documents if item["source_name"] == "pubmed"]
    pub_docs.sort(key=lambda item: (item["relationship"] != "results_publication", item["external_id"]))
    for ordinal, document in enumerate(pub_docs[:max_publications], start=1):
        abstract = str(document.get("abstract_text") or "")[:max_abstract_chars]
        excerpt = f"Title: {document.get('title') or ''}\nAbstract:\n{abstract}".strip()
        link_metadata = document.get("link_metadata") or {}
        document_metadata = document.get("metadata") or {}
        publication_scientific_support = (
            link_metadata.get("supports_scientific_outcome")
            if isinstance(link_metadata.get("supports_scientific_outcome"), bool)
            else document["relationship"] == "results_publication"
        )
        publication_termination_support = bool(
            link_metadata.get("supports_termination_driver")
        )
        publication_program_support = bool(link_metadata.get("supports_program_outcome"))
        publication_support_types = document_metadata.get("support_types") or (
            ["publication_results"]
            if document["relationship"] == "results_publication" else []
        )
        publication_evidence_relation = (
            link_metadata.get("evidence_relation") or "registry_linked"
        )
        publication_locator = document_metadata.get("locator") or "PubMed abstract"
        publications.append({
            "source_document_id": int(document["source_document_id"]),
            "pmid": str(document["external_id"]),
            "relationship": document["relationship"],
            "evidence_relation": publication_evidence_relation,
            "supports_scientific_outcome": publication_scientific_support,
            "supports_termination_driver": publication_termination_support,
            "supports_program_outcome": publication_program_support,
            "support_types": publication_support_types,
            "title": document.get("title"),
            "abstract": abstract,
            "url": document.get("source_url"),
        })
        source_inputs.append({
            "source_document_id": int(document["source_document_id"]),
            "source_name": "pubmed",
            "external_id": str(document["external_id"]),
            "relationship": "publication_abstract_input",
            "ordinal": ordinal,
            "content_sha256": document["content_sha256"],
            "excerpt_text": excerpt,
            "source_text_kind": document_metadata.get("text_kind") or "source_text",
            "source_locator": publication_locator,
            "evidence_relation": publication_evidence_relation,
            "supports_scientific_outcome": publication_scientific_support,
            "supports_termination_driver": publication_termination_support,
            "supports_program_outcome": publication_program_support,
            "support_types": publication_support_types,
        })
    external_sources = []
    external_docs = [
        item for item in documents
        if item["source_name"] not in {"clinicaltrials.gov", "pubmed"}
    ]
    external_docs.sort(key=lambda item: (
        item["relationship"] not in {
            "results_and_termination", "results_publication", "trial_results",
            "termination_evidence",
        },
        item["source_name"], item["external_id"],
    ))
    first_external_ordinal = len(publications) + 1
    for offset, document in enumerate(external_docs[:max_external_sources]):
        ordinal = first_external_ordinal + offset
        link_metadata = document.get("link_metadata") or {}
        document_metadata = document.get("metadata") or {}
        text = str(document.get("body_text") or document.get("abstract_text") or "")[:max_external_chars]
        excerpt = f"Title: {document.get('title') or ''}\nEvidence excerpt:\n{text}".strip()
        external_sources.append({
            "source_document_id": int(document["source_document_id"]),
            "source_name": document["source_name"],
            "source_type": document.get("source_type"),
            "external_id": str(document["external_id"]),
            "relationship": document["relationship"],
            "relationships": document.get("relationships") or [document["relationship"]],
            "evidence_relation": link_metadata.get("evidence_relation"),
            "supports_scientific_outcome": bool(link_metadata.get("supports_scientific_outcome")),
            "supports_termination_driver": bool(link_metadata.get("supports_termination_driver")),
            "supports_program_outcome": bool(link_metadata.get("supports_program_outcome")),
            "source_text_kind": document_metadata.get("text_kind") or "source_text",
            "source_locator": document_metadata.get("locator"),
            "support_types": document_metadata.get("support_types") or [],
            "program_scope": document_metadata.get("program_scope"),
            "curator_linkage_basis": document_metadata.get("linkage_basis"),
            "curator_source_limitations": document_metadata.get("limitations"),
            "curator_metadata_is_source_evidence": False,
            "title": document.get("title"),
            "excerpt": text,
            "url": document.get("source_url"),
        })
        source_inputs.append({
            "source_document_id": int(document["source_document_id"]),
            "source_name": document["source_name"],
            "external_id": str(document["external_id"]),
            "relationship": "external_evidence_input",
            "ordinal": ordinal,
            "content_sha256": document["content_sha256"],
            "excerpt_text": excerpt,
            "source_text_kind": document_metadata.get("text_kind") or "source_text",
            "source_locator": document_metadata.get("locator"),
            "evidence_relation": link_metadata.get("evidence_relation"),
            "supports_scientific_outcome": bool(link_metadata.get("supports_scientific_outcome")),
            "supports_termination_driver": bool(link_metadata.get("supports_termination_driver")),
            "supports_program_outcome": bool(link_metadata.get("supports_program_outcome")),
            "support_types": document_metadata.get("support_types") or [],
            "program_scope": document_metadata.get("program_scope"),
        })
    payload = {
        "schema_version": DOSSIER_SCHEMA_VERSION,
        "nct_id": nct_id,
        "registry": registry_payload,
        "publications": publications,
        "external_sources": external_sources,
        "source_inputs": source_inputs,
        "selection_summary": {
            "available_publications": len(pub_docs),
            "included_publications": len(publications),
            "max_publications": max_publications,
            "max_abstract_chars": max_abstract_chars,
            "available_external_sources": len(external_docs),
            "included_external_sources": len(external_sources),
            "max_external_sources": max_external_sources,
            "max_external_chars": max_external_chars,
        },
    }
    payload["dossier_sha256"] = sha256_text(canonical_json(payload))
    return payload


def prepare(args: argparse.Namespace) -> None:
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    selection: list[dict[str, Any]] = []
    extra_categories: dict[str, str] = {}
    if args.validation_per_category:
        selection = validation_selection(
            cur, args.validation_per_category, args.seed
        )
        sampled_ids = {row["nct_id"] for row in selection}
        extra_ids = sorted(
            {value.strip().upper() for value in args.nct_id if value.strip()}
            - sampled_ids
        )
        nct_ids = [row["nct_id"] for row in selection] + extra_ids
        selection_by_nct = {row["nct_id"]: row for row in selection}
        if extra_ids:
            cur.execute(
                """SELECT subject_key, category
                   FROM preclin.classification
                   WHERE subject_type='trial' AND classifier_task='why_stopped'
                     AND classifier_model='claude-sonnet'
                     AND classifier_version='v1' AND subject_key=ANY(%s)""",
                (extra_ids,),
            )
            extra_categories = {str(nct): str(cat) for nct, cat in cur.fetchall()}
    else:
        nct_ids = selected_nct_ids(cur, args.nct_id, args.limit)
        selection_by_nct = {}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    prepared = skipped = 0
    seen: set[str] = set()
    with args.out.open("w", encoding="utf-8") as handle:
        for nct_id, documents in iter_trial_documents(conn, nct_ids):
            seen.add(nct_id)
            try:
                dossier = build_dossier(
                    nct_id,
                    documents,
                    max_publications=args.max_publications,
                    max_abstract_chars=args.max_abstract_chars,
                    max_external_sources=args.max_external_sources,
                    max_external_chars=args.max_external_chars,
                )
                if nct_id in extra_categories:
                    registry = dossier["registry"]
                    publication_count = len(dossier["publications"])
                    has_results = bool(registry.get("has_results"))
                    profile = (
                        "results_and_publications" if has_results and publication_count
                        else "results_only" if has_results
                        else "publications_only" if publication_count
                        else "registry_only"
                    )
                    metadata = {
                        "nct_id": nct_id,
                        "legacy_category": extra_categories[nct_id],
                        "evidence_profile": profile,
                        "overall_status": registry.get("overall_status"),
                        "why_stopped": registry.get("why_stopped"),
                        "phases": registry.get("phases") or [],
                        "has_results": has_results,
                        "publication_count": publication_count,
                        "selection_reason": "prompt_size_outlier",
                    }
                    selection.append(metadata)
                    selection_by_nct[nct_id] = metadata
                if nct_id in selection_by_nct:
                    dossier["validation_selection"] = selection_by_nct[nct_id]
                    unhashed = dict(dossier)
                    unhashed.pop("dossier_sha256")
                    dossier["dossier_sha256"] = sha256_text(canonical_json(unhashed))
                handle.write(json.dumps(dossier, ensure_ascii=False) + "\n")
                prepared += 1
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                skipped += 1
            if (prepared + skipped) % 250 == 0:
                print(
                    f"  dossiers={prepared + skipped}/{len(nct_ids)} "
                    f"prepared={prepared} skipped={skipped}",
                    flush=True,
                )
    for nct_id in sorted(set(nct_ids) - seen):
        print(f"{nct_id}: no canonical source documents", file=sys.stderr)
        skipped += 1
    conn.close()
    if selection and args.selection_out:
        args.selection_out.parent.mkdir(parents=True, exist_ok=True)
        with args.selection_out.open("w", encoding="utf-8") as handle:
            for row in selection:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"prepared={prepared} skipped={skipped} out={args.out}")


def validate_dossier(dossier: dict[str, Any]) -> None:
    if dossier.get("schema_version") not in SUPPORTED_DOSSIER_SCHEMA_VERSIONS:
        raise ValueError("unsupported dossier schema")
    expected = dict(dossier)
    observed_hash = expected.pop("dossier_sha256", None)
    if observed_hash != sha256_text(canonical_json(expected)):
        raise ValueError(f"{dossier.get('nct_id')}: dossier hash mismatch")
    sources = dossier.get("source_inputs")
    if not isinstance(sources, list) or not sources:
        raise ValueError(f"{dossier.get('nct_id')}: no source inputs")
    if any(not isinstance(item.get("source_document_id"), int) for item in sources):
        raise ValueError(f"{dossier.get('nct_id')}: non-canonical source input")


def render_model_input(dossier: dict[str, Any]) -> str:
    validate_dossier(dossier)
    model_packet = {
        "nct_id": dossier["nct_id"],
        "registry_source_document_id": dossier["source_inputs"][0]["source_document_id"],
        "registry": dossier["registry"],
        "publications": dossier["publications"],
        "external_sources": dossier.get("external_sources") or [],
    }
    return (
        "Adjudicate this trial. Return the required JSON object.\n\n"
        + json.dumps(model_packet, indent=2, sort_keys=True, ensure_ascii=False)
    )


def validate_result(row: dict[str, Any], dossier: dict[str, Any]) -> dict[str, Any]:
    enum_fields = {
        "study_execution": STUDY_EXECUTION,
        "primary_endpoint_assessment": PRIMARY_ENDPOINT_ASSESSMENT,
        "scientific_outcome": SCIENTIFIC_OUTCOME,
        "termination_driver": TERMINATION_DRIVER,
        "program_outcome": PROGRAM_OUTCOME,
        "program_outcome_scope": PROGRAM_OUTCOME_SCOPE,
        "euphemism_assessment": EUPHEMISM_ASSESSMENT,
        "evidence_strength": EVIDENCE_STRENGTH,
        "confidence": CONFIDENCE,
    }
    for field, allowed in enum_fields.items():
        value = str(row.get(field) or "").lower()
        if value not in allowed:
            raise ValueError(f"invalid {field}: {value!r}")
        row[field] = value
    secondary_drivers = row.get("secondary_termination_drivers")
    if not isinstance(secondary_drivers, list) or any(
        str(value).lower() not in TERMINATION_DRIVER - {"unknown"}
        for value in secondary_drivers
    ):
        raise ValueError("invalid secondary_termination_drivers")
    row["secondary_termination_drivers"] = sorted({
        str(value).lower() for value in secondary_drivers
    })
    if row["termination_driver"] in row["secondary_termination_drivers"]:
        raise ValueError("primary termination_driver cannot also be secondary")
    if row["program_outcome"] == "unknown":
        if row["program_outcome_scope"] != "unknown":
            raise ValueError("unknown program_outcome requires unknown scope")
    elif row["program_outcome_scope"] == "unknown":
        raise ValueError("non-unknown program_outcome requires an explicit scope")
    if (
        row["euphemism_assessment"] == "confirmed_efficacy_euphemism"
        and row["termination_driver"] != "efficacy"
    ):
        raise ValueError(
            "confirmed_efficacy_euphemism requires efficacy as the "
            "termination_driver"
        )
    if row["termination_driver"] == "positive_efficacy_progression" and (
        row["scientific_outcome"] not in {
            "efficacy_success", "mixed_or_inconclusive"
        }
        or row["program_outcome"] != "continued"
    ):
        raise ValueError(
            "positive_efficacy_progression requires a positive scientific "
            "outcome and continued development"
        )
    if not isinstance(row.get("rationale"), str) or not row["rationale"].strip():
        raise ValueError("rationale is required")
    if not isinstance(row.get("conflicts"), list):
        raise ValueError("conflicts must be an array")
    cited = row.get("cited_source_document_ids")
    if not isinstance(cited, list) or any(not isinstance(value, int) for value in cited):
        raise ValueError("cited_source_document_ids must be integers")
    allowed_ids = {item["source_document_id"] for item in dossier["source_inputs"]}
    unsupported = set(cited) - allowed_ids
    if unsupported:
        raise ValueError(f"cited source ids absent from dossier: {sorted(unsupported)}")
    registry_ids = {
        item["source_document_id"]
        for item in dossier["source_inputs"]
        if item["source_name"] == "clinicaltrials.gov"
    }
    if len(registry_ids) != 1 or not registry_ids.issubset(set(cited)):
        raise ValueError("the canonical registry source_document_id must be cited")

    registry_id = next(iter(registry_ids))
    publication_by_id = {
        item["source_document_id"]: item
        for item in dossier.get("publications") or []
    }
    external_by_id = {
        item["source_document_id"]: item
        for item in dossier.get("external_sources") or []
    }
    axis_fields = {
        "scientific_outcome": "scientific_outcome_source_document_ids",
        "termination_driver": "termination_driver_source_document_ids",
        "program_outcome": "program_outcome_source_document_ids",
    }
    axis_sources: dict[str, list[int]] = {}
    for axis, field in axis_fields.items():
        values = row.get(field)
        if not isinstance(values, list) or not values or any(
            not isinstance(value, int) for value in values
        ):
            raise ValueError(f"{field} must be a nonempty integer array")
        values = sorted(set(values))
        if not set(values).issubset(set(cited)):
            raise ValueError(f"{field} must be a subset of cited sources")
        axis_sources[axis] = values
        row[field] = values

    registry_why_stopped = str(dossier["registry"].get("why_stopped") or "")

    def has_unnegated(pattern: str) -> bool:
        for match in re.finditer(pattern, registry_why_stopped, re.IGNORECASE):
            prefix = registry_why_stopped[max(0, match.start() - 60):match.start()]
            suffix = registry_why_stopped[match.end():match.end() + 90]
            prefix_negated = re.search(
                r"\b(?:not|no|without|unrelated(?:\s+to)?|not\s+based\s+on)\b.{0,45}$",
                prefix,
                re.IGNORECASE,
            )
            suffix_negated = re.search(
                r"^.{0,35}\b(?:was|were|is|are|considered|deemed|determined)?\s*"
                r"(?:not\s+(?:related|attributable)|unrelated|not\s+based)\b",
                suffix,
                re.IGNORECASE,
            )
            if not prefix_negated and not suffix_negated:
                return True
        return False

    registry_support_types: set[str] = set()
    if dossier["registry"].get("has_results"):
        registry_support_types.add("registry_results")
    if has_unnegated(
        r"futil\w*|lack(?:ing)?\s+(?:of\s+)?efficacy|ineffective|"
        r"did\s+not\s+meet|missed\s+(?:the\s+)?primary|unlikely\s+to\s+meet"
    ):
        registry_support_types.update({"efficacy_futility", "primary_endpoint_status"})
    if has_unnegated(
        r"safety\s+(?:concern|issue|signal)|toxicit\w*|adverse\s+event|fatalit\w*|death"
    ):
        registry_support_types.add("safety_failure")
    if has_unnegated(r"unfavourable\s+benefit.?risk|unfavorable\s+benefit.?risk"):
        registry_support_types.add("unfavorable_benefit_risk")

    required_registry_types = {
        "confirmed_efficacy_failure": {"efficacy_futility", "registry_results"},
        "probable_efficacy_failure": {"efficacy_futility", "registry_results"},
        "efficacy_success": {"registry_results"},
        "mixed_or_inconclusive": {"registry_results"},
        "safety_failure": {"safety_failure", "registry_results"},
        "unfavorable_benefit_risk": {
            "unfavorable_benefit_risk", "registry_results"
        },
    }.get(row["scientific_outcome"], set())

    def source_permits(axis: str, source_id: int) -> bool:
        if source_id == registry_id:
            if axis == "termination_driver":
                return True
            if axis == "program_outcome":
                return row["program_outcome"] == "unknown"
            return (
                row["scientific_outcome"] in {"unknown", "not_efficacy_evaluable"}
                or bool(registry_support_types & required_registry_types)
            )
        item = external_by_id.get(source_id)
        if item is not None:
            if axis == "scientific_outcome" and item.get("evidence_relation") in {
                "parent_trial", "extension_trial", "sibling_indication",
                "program_only",
            }:
                return False
            return bool(item.get(f"supports_{axis}"))
        publication = publication_by_id.get(source_id)
        if publication is None:
            return False
        flag = publication.get(f"supports_{axis}")
        if isinstance(flag, bool):
            return flag
        if axis == "scientific_outcome":
            return publication.get("relationship") == "results_publication"
        return False

    for axis, values in axis_sources.items():
        disallowed = [value for value in values if not source_permits(axis, value)]
        if disallowed:
            raise ValueError(
                f"{axis} cites sources whose support flags prohibit that axis: "
                f"{disallowed}"
            )

    def support_types_for(source_id: int) -> set[str]:
        if source_id == registry_id:
            return registry_support_types
        item = external_by_id.get(source_id)
        if item is not None:
            return {str(value) for value in item.get("support_types") or []}
        publication = publication_by_id.get(source_id)
        if publication is not None and publication.get("relationship") == "results_publication":
            return {"publication_results"}
        return set()

    scientific_support_types = set().union(*(
        support_types_for(value) for value in axis_sources["scientific_outcome"]
    ))
    broad_result_types = {"registry_results", "publication_results"}
    required_scientific_types = {
        "confirmed_efficacy_failure": {"primary_endpoint_status", "efficacy_futility"},
        "probable_efficacy_failure": {"primary_endpoint_status", "efficacy_futility"},
        "efficacy_success": {"participant_results_present", "primary_endpoint_status"},
        "mixed_or_inconclusive": {"participant_results_present", "primary_endpoint_status"},
        "safety_failure": {"safety_failure"},
        "unfavorable_benefit_risk": {"safety_failure"},
    }.get(row["scientific_outcome"])
    if required_scientific_types is not None and not (
        scientific_support_types & (required_scientific_types | broad_result_types)
    ):
        raise ValueError(
            f"{row['scientific_outcome']} lacks a source with the required "
            "scientific support type"
        )

    if row["program_outcome"] != "unknown":
        expected_program_type = {
            "continued": "program_continuation",
            "discontinued": "program_discontinuation",
            "followup_only_stopped": "followup_only_stop",
        }[row["program_outcome"]]
        program_items = [
            external_by_id[value]
            for value in axis_sources["program_outcome"]
            if value in external_by_id
        ]
        if not any(
            expected_program_type in set(item.get("support_types") or [])
            and item.get("program_scope") == row["program_outcome_scope"]
            for item in program_items
        ):
            raise ValueError(
                "program outcome lacks a matching support type and scope"
            )

    if row["primary_endpoint_assessment"] in {"met", "missed", "mixed"} and not any(
        support_types_for(value) & {
            "primary_endpoint_status", "registry_results", "publication_results"
        }
        for value in axis_sources["scientific_outcome"]
    ):
        raise ValueError("reported primary endpoint requires scientific-outcome evidence")

    substantive_source_ids = set().union(*axis_sources.values()) - {registry_id}
    if substantive_source_ids:
        text_kinds = {
            external_by_id[value].get("source_text_kind")
            for value in substantive_source_ids
            if value in external_by_id
        }
        if text_kinds == {"verified_paraphrase"} and (
            row["evidence_strength"] == "direct" or row["confidence"] == "high"
        ):
            raise ValueError(
                "paraphrase-only external evidence cannot yield direct/high adjudication"
            )
    row["cited_source_document_ids"] = sorted(set(cited))
    return row


def direct_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price = PRICING.get(model)
    if not price:
        return 0.0
    return input_tokens / 1_000_000 * price["input"] + output_tokens / 1_000_000 * price["output"]


def response_text(body: dict[str, Any]) -> str:
    parts = []
    for item in body.get("output") or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if content.get("type") == "output_text":
                parts.append(str(content.get("text") or ""))
    return "".join(parts)


def source_document_audit_rows(dossier: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "source_document_id": source["source_document_id"],
            "source_name": source["source_name"],
            "external_id": source["external_id"],
            "relationship": source["relationship"],
            "ordinal": source["ordinal"],
            "content_sha256": source["content_sha256"],
            "excerpt_text": source["excerpt_text"],
            "source_text_kind": source.get("source_text_kind"),
            "source_locator": source.get("source_locator"),
            "evidence_relation": source.get("evidence_relation"),
            "supports_scientific_outcome": source.get("supports_scientific_outcome"),
            "supports_termination_driver": source.get("supports_termination_driver"),
            "supports_program_outcome": source.get("supports_program_outcome"),
            "support_types": source.get("support_types") or [],
            "program_scope": source.get("program_scope"),
        }
        for source in dossier["source_inputs"]
    ]


def apply_conservative_repairs(
    row: dict[str, Any], dossier: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Repair only mechanical omissions or conservative evidence downgrades."""
    repaired = dict(row)
    repairs: list[dict[str, Any]] = []
    registry_id = dossier["source_inputs"][0]["source_document_id"]
    axis_specs = (
        ("scientific_outcome", "scientific_outcome_source_document_ids",
         {"unknown", "not_efficacy_evaluable"}),
        ("termination_driver", "termination_driver_source_document_ids", {"unknown"}),
        ("program_outcome", "program_outcome_source_document_ids", {"unknown"}),
    )
    for outcome_field, source_field, repairable_values in axis_specs:
        if repaired.get(outcome_field) in repairable_values and repaired.get(source_field) == []:
            repaired[source_field] = [registry_id]
            repairs.append({
                "field": source_field,
                "from": [],
                "to": [registry_id],
                "reason": "unknown-axis source arrays cite the canonical registry",
            })
            cited = repaired.get("cited_source_document_ids")
            if isinstance(cited, list) and registry_id not in cited:
                repaired["cited_source_document_ids"] = [*cited, registry_id]

    if repaired.get("primary_endpoint_assessment") in {"met", "missed", "mixed"}:
        source_ids = repaired.get("scientific_outcome_source_document_ids") or []
        support_types: set[str] = set()
        for source_id in source_ids:
            if source_id == registry_id and dossier["registry"].get("has_results"):
                support_types.add("registry_results")
            for publication in dossier.get("publications") or []:
                if publication.get("source_document_id") == source_id:
                    support_types.update(publication.get("support_types") or [])
            for source in dossier.get("external_sources") or []:
                if source.get("source_document_id") == source_id:
                    support_types.update(source.get("support_types") or [])
        if not support_types & {
            "primary_endpoint_status", "registry_results", "publication_results"
        }:
            previous = repaired["primary_endpoint_assessment"]
            repaired["primary_endpoint_assessment"] = "unclear"
            repairs.append({
                "field": "primary_endpoint_assessment",
                "from": previous,
                "to": "unclear",
                "reason": "no cited source is typed to establish primary-endpoint status",
            })

    secondary = repaired.get("secondary_termination_drivers")
    rationale = str(repaired.get("rationale") or "")
    if isinstance(secondary, list) and secondary and re.search(
        r"\b(?:coequal|equally direct)\b", rationale, re.IGNORECASE
    ):
        precedence = {
            value: rank
            for rank, group in enumerate((
                {"safety", "unfavorable_benefit_risk"},
                {"efficacy", "positive_efficacy_progression"},
                {"manufacturing_supply", "pk_pd_formulation"},
                {"enrollment_operational", "pandemic_external"},
                {"regulatory_administrative"},
                {"competitive_landscape"},
                {"commercial_strategic"},
                {"planned_or_not_applicable"},
            ))
            for value in group
        }
        all_drivers = [repaired.get("termination_driver"), *secondary]
        ordered = sorted(set(all_drivers), key=lambda value: (precedence.get(value, 99), value))
        if ordered and ordered[0] != repaired.get("termination_driver"):
            previous = repaired.get("termination_driver")
            repaired["termination_driver"] = ordered[0]
            repaired["secondary_termination_drivers"] = ordered[1:]
            repaired["rationale"] = (
                rationale.rstrip()
                + f" Deterministic precedence therefore records {ordered[0]} "
                f"as the primary driver and {previous} as secondary."
            )
            repairs.append({
                "field": "termination_driver",
                "from": previous,
                "to": ordered[0],
                "reason": "model described causes as coequal; deterministic precedence applied",
            })
    return repaired, repairs


def parse_model_result(result: CallResult, dossier: dict[str, Any]) -> dict[str, Any]:
    extracted = extract_json_block(result.text)
    repaired, repairs = apply_conservative_repairs(extracted, dossier)
    row = validate_result(repaired, dossier)
    cited_ids = set(row["cited_source_document_ids"])
    citation_pmids = [
        source["external_id"]
        for source in dossier["source_inputs"]
        if source["source_name"] == "pubmed" and source["source_document_id"] in cited_ids
    ]
    row.update({
        "schema_version": RESULT_SCHEMA_VERSION,
        "nct_id": dossier["nct_id"],
        "dossier_sha256": dossier["dossier_sha256"],
        "citation_pmids": citation_pmids,
        "source_selection": dossier["selection_summary"],
    })
    annotate(row, result, PROMPT_VERSION)
    if repairs:
        row["_deterministic_repairs"] = repairs
    row["_source_documents"] = source_document_audit_rows(dossier)
    return row


class ScoringValidationError(ValueError):
    def __init__(self, message: str, audit_row: dict[str, Any]):
        super().__init__(message)
        self.audit_row = audit_row


def get_client() -> Any:
    if OpenAI is None:
        raise RuntimeError("openai package is not installed")
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI()


def score_one(client: Any, dossier: dict[str, Any], model: str) -> dict[str, Any]:
    user_prompt = render_model_input(dossier)
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            response = client.responses.create(
                model=model,
                instructions=SYSTEM_PROMPT,
                input=user_prompt,
                max_output_tokens=MODEL_MAX_TOKENS,
                reasoning={"effort": "none"},
                text={"format": OUTPUT_FORMAT},
                store=False,
            )
            body = response.model_dump()
            usage = body.get("usage") or {}
            input_tokens = int(usage.get("input_tokens") or 0)
            output_tokens = int(usage.get("output_tokens") or 0)
            actual_model = str(body.get("model") or model)
            result = CallResult(
                text=response_text(body),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=direct_cost(actual_model, input_tokens, output_tokens),
                model=actual_model,
                provider_request_id=str(body.get("id") or ""),
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=MODEL_MAX_TOKENS,
                temperature=0.0,
                provider="openai",
            )
            try:
                row = parse_model_result(result, dossier)
            except ValueError as exc:
                audit_row: dict[str, Any] = {
                    "schema_version": RESULT_SCHEMA_VERSION,
                    "nct_id": dossier["nct_id"],
                    "dossier_sha256": dossier["dossier_sha256"],
                    "validation_error": str(exc),
                    "_source_documents": source_document_audit_rows(dossier),
                }
                annotate(audit_row, result, PROMPT_VERSION)
                audit_row["_model_parameters"].update({
                    "reasoning_effort": "none",
                    "structured_outputs": True,
                    "batch_api": False,
                })
                raise ScoringValidationError(str(exc), audit_row) from exc
            row["_model_parameters"].update({
                "reasoning_effort": "none", "structured_outputs": True, "batch_api": False
            })
            return row
        except ValueError:
            # Strict-output or semantic validation failures are deterministic
            # for the submitted evidence and should be reviewed, not retried
            # repeatedly as though they were transient transport failures.
            raise
        except Exception as exc:
            last_error = exc
            if attempt == 4:
                break
            time.sleep(min(20.0, 2.0 ** attempt))
    assert last_error is not None
    raise last_error


def completed_nct_ids(path: Path) -> set[str]:
    return {str(row.get("nct_id")) for row in read_jsonl(path) if row.get("nct_id")}


def score(args: argparse.Namespace) -> None:
    if not args.confirm_paid:
        raise SystemExit("direct Responses calls are paid; pass --confirm-paid")
    client = get_client()
    completed = completed_nct_ids(args.out)
    dossiers = [
        dossier for dossier in read_jsonl(args.dossiers)
        if str(dossier.get("nct_id") or "") not in completed
    ]
    succeeded = failed = 0
    cost = 0.0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        pending = {
            executor.submit(score_one, client, dossier, args.model): dossier
            for dossier in dossiers[: args.workers * 2]
        }
        next_index = len(pending)
        while pending:
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                dossier = pending.pop(future)
                nct_id = str(dossier.get("nct_id") or "")
                try:
                    row = future.result()
                    row["_dossier_file"] = args.dossiers.name
                    append_jsonl(args.out, row)
                    succeeded += 1
                    cost += float(row.get("_cost_usd") or 0.0)
                except Exception as exc:
                    error_row = {
                        "nct_id": nct_id,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                    if isinstance(exc, ScoringValidationError):
                        error_row.update(exc.audit_row)
                    append_jsonl(args.errors_out, error_row)
                    failed += 1
                if next_index < len(dossiers):
                    next_dossier = dossiers[next_index]
                    next_index += 1
                    pending[executor.submit(
                        score_one, client, next_dossier, args.model
                    )] = next_dossier
                print(
                    f"handled={succeeded + failed}/{len(dossiers)} ok={succeeded} "
                    f"failed={failed} cost=${cost:.4f}",
                    flush=True,
                )


def validate_file(args: argparse.Namespace) -> None:
    count = 0
    for dossier in read_jsonl(args.dossiers):
        validate_dossier(dossier)
        render_model_input(dossier)
        count += 1
    print(f"valid_dossiers={count} file={args.dossiers}")


def assemble_results(args: argparse.Namespace) -> None:
    """Validate, deduplicate, and atomically assemble a complete result file."""
    dossiers: dict[str, dict[str, Any]] = {}
    dossier_order: list[str] = []
    for dossier in read_jsonl(args.dossiers):
        validate_dossier(dossier)
        nct_id = str(dossier.get("nct_id") or "")
        if not nct_id or nct_id in dossiers:
            raise ValueError(f"invalid or duplicate dossier nct_id: {nct_id!r}")
        dossiers[nct_id] = dossier
        dossier_order.append(nct_id)

    selected: dict[str, dict[str, Any]] = {}
    invalid: list[str] = []
    rows_read = 0
    required_audit_fields = {
        "_run_id", "_provider", "_model", "_prompt_version",
        "_system_prompt", "_user_prompt", "_raw_response",
        "_source_documents",
    }
    result_inputs = [(result_path, False) for result_path in args.results]
    result_inputs.extend(
        (result_path, True) for result_path in args.replacement_result
    )
    replacements = 0
    for result_path, is_replacement in result_inputs:
        for row in read_jsonl(result_path):
            rows_read += 1
            nct_id = str(row.get("nct_id") or "")
            dossier = dossiers.get(nct_id)
            try:
                if dossier is None:
                    raise ValueError("no matching dossier")
                if row.get("dossier_sha256") != dossier["dossier_sha256"]:
                    raise ValueError("result and dossier hashes differ")
                missing_audit = sorted(
                    field for field in required_audit_fields
                    if row.get(field) in (None, "")
                )
                if missing_audit:
                    raise ValueError(
                        f"missing audit fields: {', '.join(missing_audit)}"
                    )
                validate_result(dict(row), dossier)
                if nct_id in selected and not is_replacement:
                    raise ValueError("more than one valid result for this trial")
            except Exception as exc:
                invalid.append(f"{result_path}:{nct_id or '<missing>'}: {exc}")
                continue
            if nct_id in selected:
                replacements += 1
            selected[nct_id] = row

    missing = [nct_id for nct_id in dossier_order if nct_id not in selected]
    if invalid:
        print(f"invalid_rows={len(invalid)}", file=sys.stderr)
        for message in invalid[:20]:
            print(message, file=sys.stderr)
        raise SystemExit(1)
    if missing:
        print(
            f"missing_valid_results={len(missing)} examples={missing[:20]}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if args.expected_count is not None and len(selected) != args.expected_count:
        raise ValueError(
            f"assembled count {len(selected)} != expected {args.expected_count}"
        )
    if args.out.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {args.out}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=args.out.parent, delete=False
    ) as handle:
        temporary_path = Path(handle.name)
        for nct_id in dossier_order:
            handle.write(json.dumps(selected[nct_id], ensure_ascii=False) + "\n")
    temporary_path.replace(args.out)
    print(
        f"assembled={len(selected)} rows_read={rows_read} "
        f"replacements={replacements} out={args.out}"
    )


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--out", type=Path, required=True)
    prepare_parser.add_argument("--nct-id", action="append", default=[])
    prepare_parser.add_argument("--limit", type=int)
    prepare_parser.add_argument(
        "--validation-per-category",
        type=int,
        help="select N evidence-profile-balanced trials per legacy Sonnet category",
    )
    prepare_parser.add_argument("--seed", type=int, default=20260902)
    prepare_parser.add_argument("--selection-out", type=Path)
    prepare_parser.add_argument("--max-publications", type=int, default=DEFAULT_MAX_PUBLICATIONS)
    prepare_parser.add_argument("--max-abstract-chars", type=int, default=DEFAULT_MAX_ABSTRACT_CHARS)
    prepare_parser.add_argument("--max-external-sources", type=int, default=DEFAULT_MAX_EXTERNAL_SOURCES)
    prepare_parser.add_argument("--max-external-chars", type=int, default=DEFAULT_MAX_EXTERNAL_CHARS)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--dossiers", type=Path, required=True)

    assemble_parser = subparsers.add_parser("assemble")
    assemble_parser.add_argument("--dossiers", type=Path, required=True)
    assemble_parser.add_argument("--results", type=Path, nargs="+", required=True)
    assemble_parser.add_argument(
        "--replacement-result", type=Path, action="append", default=[],
        help="validated result file applied after base results; duplicate NCTs replace base rows",
    )
    assemble_parser.add_argument("--out", type=Path, required=True)
    assemble_parser.add_argument("--expected-count", type=int)

    score_parser = subparsers.add_parser("score")
    score_parser.add_argument("--dossiers", type=Path, required=True)
    score_parser.add_argument("--out", type=Path, required=True)
    score_parser.add_argument("--errors-out", type=Path)
    score_parser.add_argument("--model", default=DEFAULT_MODEL)
    score_parser.add_argument("--workers", type=int, default=8)
    score_parser.add_argument("--confirm-paid", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "prepare":
        if args.limit is not None and args.limit <= 0:
            parser.error("--limit must be positive")
        if args.max_publications < 0 or args.max_abstract_chars <= 0:
            parser.error("publication limits must be non-negative/positive")
        if args.max_external_sources < 0 or args.max_external_chars <= 0:
            parser.error("external-source limits must be non-negative/positive")
        if args.validation_per_category is not None and args.validation_per_category <= 0:
            parser.error("--validation-per-category must be positive")
        if args.validation_per_category and args.limit:
            parser.error("validation sampling cannot be combined with --limit")
        if args.validation_per_category and args.selection_out is None:
            args.selection_out = args.out.with_name(f"{args.out.stem}.selection.jsonl")
    if args.command == "score" and args.errors_out is None:
        args.errors_out = args.out.with_name(f"{args.out.stem}.errors.jsonl")
    if args.command == "score" and args.workers <= 0:
        parser.error("--workers must be positive")
    return args


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)
    if args.command == "prepare":
        prepare(args)
    elif args.command == "validate":
        validate_file(args)
    elif args.command == "assemble":
        assemble_results(args)
    else:
        score(args)


if __name__ == "__main__":
    main()
