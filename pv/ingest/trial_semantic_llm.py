"""Extract pilot-trial assets, indications, targets, and mechanisms with an LLM.

The model performs semantic proposal first. Deterministic authority lookup and
relationship verification are intentionally separate downstream jobs. Every
request packet, raw response, parsed decision, model setting, and usage value is
stored so a rerun can be compared without overwriting the earlier run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


TASK = "trial_semantic_extraction"
PROMPT_VERSION = "pv_trial_semantic_llm_first_v2"
OUTPUT_SCHEMA_VERSION = "pv.trial-semantic-extraction-response/1.1"
DEFAULT_MODEL = "gpt-5.6-terra"
MAX_OUTPUT_TOKENS = 6000

PRICING = {
    "gpt-5.6-terra": {"input": 2.0, "output": 12.0},
    "gpt-5.6-luna": {"input": 0.2, "output": 1.2},
}

BASIS = ["explicit_trial", "inferred_from_trial_context", "model_prior"]
EVIDENCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["source_path", "quote"],
    "properties": {
        "source_path": {"type": "string", "minLength": 1},
        "quote": {"type": "string", "minLength": 1},
    },
}

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version", "nct_id", "trial_kind", "assets", "indications",
        "pharmacology", "warnings", "review_required",
    ],
    "properties": {
        "schema_version": {"type": "string", "const": OUTPUT_SCHEMA_VERSION},
        "nct_id": {"type": "string", "pattern": "^NCT[0-9]{8}$"},
        "trial_kind": {
            "type": "string",
            "enum": [
                "therapeutic_drug", "vaccine", "behavioral", "device",
                "diagnostic", "exercise", "observational_exposure", "other",
            ],
        },
        "assets": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "literal_name", "canonical_name_proposal", "components",
                    "role", "resolution", "basis", "evidence", "certainty",
                ],
                "properties": {
                    "literal_name": {"type": "string", "minLength": 1},
                    "canonical_name_proposal": {"type": ["string", "null"]},
                    "components": {
                        "type": "array", "items": {"type": "string", "minLength": 1},
                    },
                    "role": {
                        "type": "string",
                        "enum": [
                            "experimental_intervention", "active_comparator",
                            "inactive_comparator", "placebo", "background_therapy",
                            "historical_exposure", "assessment", "device", "behavior",
                            "exercise", "other",
                        ],
                    },
                    "resolution": {
                        "type": "string",
                        "enum": [
                            "active_asset", "regimen", "placebo",
                            "non_therapeutic", "unresolved",
                        ],
                    },
                    "basis": {"type": "string", "enum": BASIS},
                    "evidence": {"type": "array", "items": EVIDENCE_SCHEMA},
                    "certainty": {"type": "string", "enum": ["high", "medium", "low"]},
                },
            },
        },
        "indications": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "normalized_phrase", "role", "concepts", "modifiers",
                    "basis", "evidence", "certainty",
                ],
                "properties": {
                    "normalized_phrase": {"type": "string", "minLength": 1},
                    "role": {
                        "type": "string",
                        "enum": [
                            "treatment", "prevention", "diagnosis", "supportive_care",
                            "background_condition", "population_characteristic",
                            "healthy_volunteer", "unresolved",
                        ],
                    },
                    "concepts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["label", "concept_kind", "relationship"],
                            "properties": {
                                "label": {"type": "string", "minLength": 1},
                                "concept_kind": {
                                    "type": "string",
                                    "enum": [
                                        "disease", "symptom_or_phenotype", "infection",
                                        "injury", "behavioral_risk", "healthy_state", "other",
                                    ],
                                },
                                "relationship": {
                                    "type": "string",
                                    "enum": [
                                        "core_condition", "treated_condition",
                                        "background_disease", "population_context",
                                        "comorbidity", "other",
                                    ],
                                },
                            },
                        },
                    },
                    "modifiers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["type", "value"],
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": [
                                        "stage", "severity", "molecular_subtype",
                                        "anatomical_site", "age", "treatment_history",
                                        "temporal", "other",
                                    ],
                                },
                                "value": {"type": "string", "minLength": 1},
                            },
                        },
                    },
                    "basis": {"type": "string", "enum": BASIS},
                    "evidence": {"type": "array", "items": EVIDENCE_SCHEMA, "minItems": 1},
                    "certainty": {"type": "string", "enum": ["high", "medium", "low"]},
                },
            },
        },
        "pharmacology": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "asset_name", "claim_level", "object_name",
                    "object_symbol_proposal", "action", "role", "directness",
                    "basis", "evidence", "certainty",
                ],
                "properties": {
                    "asset_name": {"type": "string", "minLength": 1},
                    "claim_level": {
                        "type": "string",
                        "enum": [
                            "specific_molecular_target", "target_complex_or_family",
                            "biological_pathway_or_process",
                            "chemical_or_physiological_action", "unknown_mechanism",
                        ],
                    },
                    "object_name": {"type": "string", "minLength": 1},
                    "object_symbol_proposal": {"type": ["string", "null"]},
                    "action": {
                        "type": "string",
                        "enum": [
                            "binds", "inhibits", "antagonizes", "inverse_agonizes",
                            "agonizes", "degrades", "stabilizes", "replaces",
                            "silences", "edits", "scavenges", "chelates", "reduces",
                            "potentiates", "modulates", "immunizes_against", "unknown",
                        ],
                    },
                    "role": {
                        "type": "string",
                        "enum": [
                            "therapeutic_primary", "secondary", "off_target",
                            "delivery_target", "payload_target", "biomarker", "unknown",
                        ],
                    },
                    "directness": {
                        "type": "string",
                        "enum": ["direct", "claimed_direct", "indirect", "disputed", "unknown"],
                    },
                    "basis": {"type": "string", "enum": BASIS},
                    "evidence": {"type": "array", "items": EVIDENCE_SCHEMA},
                    "certainty": {"type": "string", "enum": ["high", "medium", "low"]},
                },
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
        "review_required": {"type": "boolean"},
    },
}

OUTPUT_FORMAT = {
    "type": "json_schema",
    "name": "pv_trial_semantic_extraction",
    "strict": True,
    "schema": OUTPUT_SCHEMA,
}

SYSTEM_PROMPT = """You interpret one ClinicalTrials.gov record for a reproducible biomedical evidence pipeline.

Perform semantic extraction before database normalization:
- Identify actual interventions, exposures, comparators, devices, behaviors, and exercise regimens. Start with items in `armsInterventionsModule.interventions`, then add a named drug, biologic, device, or exposure from the title, summaries, or arm descriptions when it defines a study group. A named drug may be a historical exposure even when the registry intervention list contains only assessments.
- Do not copy outcome measures, endpoints, questionnaires, rating scales, imaging procedures, laboratory assays, or biomarkers into `assets` merely because they occur elsewhere in the record. If such an assessment is itself listed in `armsInterventionsModule.interventions`, retain it as role `assessment` only to expose that registry classification.
- Propose a concise canonical asset/component name, but never invent a database identifier.
- Determine the indication semantically. Separate the treated, prevented, or diagnosed condition from background disease, population characteristics, symptoms, and modifiers. Preserve composite indications as multiple concepts instead of flattening them.
- For every active drug or vaccine, comprehensively propose its known therapeutic-primary specific molecular targets, target families, and distinct broader mechanisms. Do not stop at a broad pathway when central specific enzyme or receptor targets are known. Multi-target drugs and nucleic-acid-directed mechanisms must retain multiple claims rather than being collapsed to one convenient target. Do not manufacture a protein target for a broad or unknown mechanism.
- Do not assign molecular pharmacology to behavioral, exercise, diagnostic, or ordinary device interventions.
- `placebo` is reserved for an inert product explicitly described as placebo. Education, usual care, wait-list, sham procedures, no-device/no-cuff arms, and observation-only controls are active or inactive comparators as appropriate, never placebo unless the record explicitly says placebo.

Evidence and provenance rules:
- `explicit_trial` means the claim is stated in the supplied record and requires an exact supplied source-path/quote pair.
- `inferred_from_trial_context` means the interpretation follows from multiple supplied trial fields and requires exact supporting trial quotes.
- `model_prior` means biomedical knowledge not stated in the supplied trial. It may be proposed for later verification, but its evidence array must be empty.
- Quotes must be exact substrings at their source paths. Never cite a path not present in the packet.
- A target or mechanism proposed from model knowledge is only a candidate. Downstream code will verify both entity identity and the asset-to-target/mechanism relationship.
- Set `review_required` to true whenever any asset, indication, target, or mechanism is uncertain, based on model prior, or requires external relationship verification.
- Use standard biomedical names where possible. For a specific human protein target, provide its usual gene-symbol proposal when known. Do not provide ontology IDs.
- Return `unknown_mechanism` rather than guessing.

Indication-name rules:
- `normalized_phrase` is a concise singular biomedical noun phrase, not an explanation.
- Expand abbreviations only when unambiguous from the record.
- Put stage, severity, molecular subtype, anatomy, age, treatment history, and temporal qualifiers in `modifiers` while keeping them represented in the normalized phrase when clinically meaningful.
- Every indication requires at least one exact trial quote.

Return only the strict structured result."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", value) else None


def add_scalars(value: Any, path: str, rows: list[dict[str, str]]) -> None:
    if isinstance(value, dict):
        for key in sorted(value):
            child = f"{path}.{key}" if path else key
            add_scalars(value[key], child, rows)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            add_scalars(item, f"{path}[{index}]", rows)
    elif isinstance(value, (str, int, float, bool)) and str(value).strip():
        rows.append({"source_path": path, "text": str(value)})


def trial_packet(nct_id: str, source_version_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    protocol = payload.get("protocolSection") or {}
    derived = payload.get("derivedSection") or {}
    selected: dict[str, Any] = {}
    for module in (
        "identificationModule", "descriptionModule", "conditionsModule", "designModule",
        "armsInterventionsModule", "outcomesModule", "eligibilityModule",
    ):
        if module in protocol:
            selected[module] = protocol[module]
    if "conditionBrowseModule" in derived:
        selected["derivedConditionBrowseModule"] = derived["conditionBrowseModule"]
    source_items: list[dict[str, str]] = []
    for module, value in selected.items():
        prefix = (
            f"derivedSection.conditionBrowseModule" if module == "derivedConditionBrowseModule"
            else f"protocolSection.{module}"
        )
        add_scalars(value, prefix, source_items)
    return {
        "packet_version": "pv.trial-semantic-extraction-request/1.0",
        "nct_id": nct_id,
        "source_record_version_id": source_version_id,
        "source_items": source_items,
    }


def load_packets(conn: Any, nct_ids: list[str], limit: int) -> list[dict[str, Any]]:
    params: list[Any] = []
    where = ""
    if nct_ids:
        where = "WHERE t.nct_id = ANY(%s)"
        params.append(nct_ids)
    sql = f"""
        SELECT t.nct_id, t.latest_source_record_version_id, v.raw_payload
        FROM pv_core.trial t
        JOIN pv_source.source_record_version v
          ON v.source_record_version_id=t.latest_source_record_version_id
        {where}
        ORDER BY t.completion_date_lower_bound, t.nct_id
    """
    if limit:
        sql += " LIMIT %s"
        params.append(limit)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    if nct_ids and {row[0] for row in rows} != set(nct_ids):
        missing = sorted(set(nct_ids) - {row[0] for row in rows})
        raise SystemExit(f"Unknown trial IDs: {', '.join(missing)}")
    return [trial_packet(nct_id, version_id, payload) for nct_id, version_id, payload in rows]


def response_text(body: dict[str, Any]) -> str:
    texts: list[str] = []
    for item in body.get("output") or []:
        for content in item.get("content") or []:
            if content.get("type") == "output_text" and content.get("text"):
                texts.append(content["text"])
    if not texts:
        raise ValueError("OpenAI response contained no output_text")
    return "".join(texts)


def call_one(client: Any, packet: dict[str, Any], model: str) -> dict[str, Any]:
    user_input = canonical_json(packet)
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            response = client.responses.create(
                model=model,
                instructions=SYSTEM_PROMPT,
                input=user_input,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                reasoning={"effort": "none"},
                text={"format": OUTPUT_FORMAT},
                store=False,
            )
            body = response.model_dump()
            raw = response_text(body)
            parsed = json.loads(raw)
            validate_semantics(packet, parsed)
            usage = body.get("usage") or {}
            return {
                "packet": packet,
                "raw": raw,
                "parsed": parsed,
                "provider_request_id": str(body.get("id") or ""),
                "actual_model": str(body.get("model") or model),
                "usage": {
                    "input_tokens": int(usage.get("input_tokens") or 0),
                    "output_tokens": int(usage.get("output_tokens") or 0),
                    "total_tokens": int(usage.get("total_tokens") or 0),
                },
            }
        except Exception as exc:
            last_error = exc
            if attempt == 4:
                break
            time.sleep(min(16, 2**attempt))
    assert last_error is not None
    raise last_error


def validate_semantics(packet: dict[str, Any], parsed: dict[str, Any]) -> None:
    if parsed.get("schema_version") != OUTPUT_SCHEMA_VERSION:
        raise ValueError("response schema_version mismatch")
    if parsed.get("nct_id") != packet["nct_id"]:
        raise ValueError("response nct_id mismatch")
    source_map = {row["source_path"]: row["text"] for row in packet["source_items"]}
    for section in ("assets", "indications", "pharmacology"):
        if not isinstance(parsed.get(section), list):
            raise ValueError(f"{section} must be an array")
        for item in parsed[section]:
            evidence = item.get("evidence")
            if not isinstance(evidence, list):
                raise ValueError(f"{section} evidence must be an array")
            if item.get("basis") == "model_prior" and evidence:
                raise ValueError(f"model_prior {section} item cannot cite trial evidence")
            if section == "indications" and not evidence:
                raise ValueError("every indication must cite trial evidence")
            for support in evidence:
                path = support.get("source_path")
                quote = support.get("quote")
                if path not in source_map:
                    raise ValueError(f"unknown evidence source_path: {path}")
                if not quote or quote not in source_map[path]:
                    raise ValueError(f"evidence quote not found at {path}")


def canonical_decision(parsed: dict[str, Any]) -> dict[str, Any]:
    def sorted_rows(name: str, keys: tuple[str, ...]) -> list[dict[str, Any]]:
        rows = json.loads(json.dumps(parsed[name]))
        for row in rows:
            if isinstance(row.get("evidence"), list):
                row["evidence"].sort(key=lambda x: (x["source_path"], x["quote"]))
            if isinstance(row.get("components"), list):
                row["components"].sort(key=str.casefold)
            if isinstance(row.get("concepts"), list):
                row["concepts"].sort(
                    key=lambda x: (x["label"].casefold(), x["relationship"], x["concept_kind"])
                )
            if isinstance(row.get("modifiers"), list):
                row["modifiers"].sort(key=lambda x: (x["type"], x["value"].casefold()))
        return sorted(rows, key=lambda x: tuple(str(x.get(key) or "").casefold() for key in keys))

    return {
        "trial_kind": parsed["trial_kind"],
        "assets": sorted_rows("assets", ("canonical_name_proposal", "literal_name", "role")),
        "indications": sorted_rows("indications", ("normalized_phrase", "role")),
        "pharmacology": sorted_rows("pharmacology", ("asset_name", "claim_level", "object_name")),
        "review_required": parsed["review_required"],
    }


def resolve_prior_run(cur: Any, current_run: uuid.UUID, value: str | None) -> uuid.UUID | None:
    if value is None:
        return None
    if value != "latest":
        return uuid.UUID(value)
    cur.execute(
        """
        SELECT decision_run_id FROM pv_evidence.llm_decision_run
        WHERE task=%s AND status='completed' AND decision_run_id<>%s
        ORDER BY started_at DESC, decision_run_id DESC LIMIT 1
        """,
        (TASK, str(current_run)),
    )
    row = cur.fetchone()
    if row is None:
        raise SystemExit(f"No earlier completed {TASK!r} run exists")
    return row[0]


def store_results(
    conn: Any,
    run_id: uuid.UUID,
    results: list[dict[str, Any]],
    model: str,
    compare_to: str | None,
) -> uuid.UUID | None:
    with conn.cursor() as cur:
        prior_run = resolve_prior_run(cur, run_id, compare_to)
        if prior_run is not None:
            cur.execute(
                "UPDATE pv_evidence.llm_decision_run SET compare_to_run_id=%s WHERE decision_run_id=%s",
                (str(prior_run), str(run_id)),
            )
        for result in results:
            packet = result["packet"]
            parsed = result["parsed"]
            canonical = canonical_decision(parsed)
            prior_id = prior_hash = None
            if prior_run is not None:
                cur.execute(
                    """
                    SELECT llm_decision_id,decision_sha256
                    FROM pv_evidence.llm_decision
                    WHERE decision_run_id=%s AND task=%s
                      AND subject_type='trial' AND subject_key=%s
                    """,
                    (str(prior_run), TASK, packet["nct_id"]),
                )
                row = cur.fetchone()
                if row:
                    prior_id, prior_hash = row
            decision_hash = sha256_text(canonical_json(canonical))
            change_status = (
                "not_compared" if prior_run is None else
                "added" if prior_id is None else
                "unchanged" if prior_hash == decision_hash else "changed"
            )
            cur.execute(
                """
                INSERT INTO pv_evidence.llm_decision
                  (decision_run_id,task,subject_type,subject_key,input_sha256,
                   raw_response,parsed_output,output_sha256,canonical_decision,
                   decision_sha256,prior_decision_id,change_status,input_payload,
                   provider_request_id,model_parameters,usage,validation_status,
                   validation_detail)
                VALUES (%s,%s,'trial',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        'validated','[]'::jsonb)
                RETURNING llm_decision_id
                """,
                (
                    str(run_id), TASK, packet["nct_id"],
                    sha256_text(canonical_json(packet)), result["raw"], Json(parsed),
                    sha256_text(canonical_json(parsed)), Json(canonical), decision_hash,
                    prior_id, change_status, Json(packet), result["provider_request_id"],
                    Json({"reasoning_effort": "none", "max_output_tokens": MAX_OUTPUT_TOKENS,
                          "structured_outputs": True, "requested_model": model}),
                    Json(result["usage"]),
                ),
            )
            decision_id = cur.fetchone()[0]
            # Link the exact ClinicalTrials.gov source version used by the packet.
            cur.execute(
                """
                INSERT INTO pv_evidence.llm_decision_source
                  (llm_decision_id,source_record_version_id,ordinal,excerpt_text,excerpt_sha256)
                VALUES (%s,%s,0,NULL,NULL)
                """,
                (decision_id, packet["source_record_version_id"]),
            )
        conn.commit()
    return prior_run


def json_diff(before: Any, after: Any, path: str = "$") -> list[dict[str, Any]]:
    if type(before) is not type(after):
        return [{"path": path, "before": before, "after": after}]
    if isinstance(before, dict):
        result: list[dict[str, Any]] = []
        for key in sorted(set(before) | set(after)):
            child = f"{path}.{key}"
            if key not in before:
                result.append({"path": child, "before": None, "after": after[key]})
            elif key not in after:
                result.append({"path": child, "before": before[key], "after": None})
            else:
                result.extend(json_diff(before[key], after[key], child))
        return result
    if before != after:
        return [{"path": path, "before": before, "after": after}]
    return []


def store_comparison(conn: Any, current: uuid.UUID, prior: uuid.UUID) -> dict[str, int]:
    counts = {key: 0 for key in ("added", "removed", "changed", "unchanged")}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(c.subject_key,p.subject_key),c.llm_decision_id,p.llm_decision_id,
                   c.decision_sha256,p.decision_sha256,c.canonical_decision,p.canonical_decision
            FROM (SELECT * FROM pv_evidence.llm_decision WHERE decision_run_id=%s) c
            FULL OUTER JOIN (SELECT * FROM pv_evidence.llm_decision WHERE decision_run_id=%s) p
              ON c.task=p.task AND c.subject_type=p.subject_type AND c.subject_key=p.subject_key
            ORDER BY 1
            """,
            (str(current), str(prior)),
        )
        for key, current_id, prior_id, current_hash, prior_hash, current_value, prior_value in cur.fetchall():
            status = (
                "added" if prior_id is None else "removed" if current_id is None else
                "unchanged" if current_hash == prior_hash else "changed"
            )
            counts[status] += 1
            diff = json_diff(prior_value, current_value) if status == "changed" else []
            cur.execute(
                """
                INSERT INTO pv_evidence.llm_decision_comparison
                  (current_run_id,compare_to_run_id,task,subject_type,subject_key,
                   change_status,current_decision_id,prior_decision_id,field_diff)
                VALUES (%s,%s,%s,'trial',%s,%s,%s,%s,%s)
                """,
                (str(current), str(prior), TASK, key, status, current_id, prior_id, Json(diff)),
            )
        conn.commit()
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--nct-id", action="append", default=[])
    parser.add_argument("--limit", type=int, default=10, help="0 processes all stored trials")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--compare-decisions-to", help="earlier run UUID or 'latest'")
    parser.add_argument("--confirm-paid", action="store_true")
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if args.workers <= 0:
        parser.error("--workers must be positive")
    return args


def main() -> None:
    args = parse_args()
    if not args.confirm_paid:
        raise SystemExit("OpenAI Responses calls are paid; pass --confirm-paid")
    if not args.commit:
        raise SystemExit("This runner stores immutable decisions; pass --commit")
    if OpenAI is None:
        raise SystemExit("openai package is not installed")
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required")
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    run_id = uuid.uuid4()
    started_at = datetime.now(timezone.utc)
    try:
        packets = load_packets(conn, args.nct_id, args.limit)
        if not packets:
            raise SystemExit("No trial packets selected")
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pv_evidence.llm_decision_run
                  (decision_run_id,task,provider,model,prompt_version,
                   output_schema_version,code_commit,parameters,status,started_at)
                VALUES (%s,%s,'openai',%s,%s,%s,%s,%s,'running',%s)
                """,
                (
                    str(run_id), TASK, args.model, PROMPT_VERSION,
                    OUTPUT_SCHEMA_VERSION, git_commit(),
                    Json({"workers": args.workers, "limit": args.limit,
                          "nct_ids": args.nct_id, "reasoning_effort": "none",
                          "max_output_tokens": MAX_OUTPUT_TOKENS,
                          "system_prompt": SYSTEM_PROMPT,
                          "system_prompt_sha256": sha256_text(SYSTEM_PROMPT),
                          "output_schema": OUTPUT_SCHEMA,
                          "output_schema_sha256": sha256_text(canonical_json(OUTPUT_SCHEMA))}),
                    started_at,
                ),
            )
            conn.commit()

        print(f"run_id={run_id} trials={len(packets)} model={args.model}", flush=True)
        client = OpenAI()
        results: list[dict[str, Any]] = []
        errors: list[str] = []
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            pending = {executor.submit(call_one, client, packet, args.model): packet for packet in packets}
            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    packet = pending.pop(future)
                    try:
                        result = future.result()
                        results.append(result)
                        print(f"completed {packet['nct_id']}", flush=True)
                    except Exception as exc:
                        errors.append(f"{packet['nct_id']}: {type(exc).__name__}: {exc}")
                        print(f"failed {errors[-1]}", flush=True)
        if errors:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE pv_evidence.llm_decision_run
                       SET status='failed',completed_at=%s,
                           parameters=parameters || %s::jsonb
                       WHERE decision_run_id=%s""",
                    (datetime.now(timezone.utc), Json({"errors": errors}), str(run_id)),
                )
                conn.commit()
            raise SystemExit("; ".join(errors))

        prior_run = store_results(conn, run_id, sorted(results, key=lambda x: x["packet"]["nct_id"]), args.model, args.compare_decisions_to)
        total_input = sum(row["usage"]["input_tokens"] for row in results)
        total_output = sum(row["usage"]["output_tokens"] for row in results)
        actual_models = sorted({row["actual_model"] for row in results})
        price = PRICING.get(args.model)
        estimated_cost = (
            total_input / 1_000_000 * price["input"] + total_output / 1_000_000 * price["output"]
            if price else None
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pv_evidence.llm_decision_run
                SET status='completed',completed_at=%s,
                    model_snapshot=%s,
                    parameters=parameters || %s::jsonb
                WHERE decision_run_id=%s
                """,
                (
                    datetime.now(timezone.utc), ",".join(actual_models),
                    Json({"input_tokens": total_input, "output_tokens": total_output,
                          "estimated_cost_usd": estimated_cost}), str(run_id),
                ),
            )
            conn.commit()
        counts = store_comparison(conn, run_id, prior_run) if prior_run else None
        print(
            f"stored={len(results)} input_tokens={total_input} output_tokens={total_output} "
            f"estimated_cost_usd={estimated_cost if estimated_cost is not None else 'unknown'}",
            flush=True,
        )
        if prior_run:
            print(f"compare_to={prior_run} counts={canonical_json(counts)}", flush=True)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
