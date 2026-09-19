"""Extract source-grounded target context from archived ChEMBL mechanisms.

This is the second LLM stage.  Asset identity and complete ChEMBL mechanism
enumeration must already exist.  The model may structure only supplied source
text; deterministic validation rejects invented IDs, unsupported component
promotion, non-verbatim evidence, and normalized terms absent from the quote.
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
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import Json

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from pv.ingest.semantic_verifier import normalized


TASK = "chembl_mechanism_context_extraction"
PROMPT_VERSION = "pv_chembl_mechanism_context_v1"
REQUEST_SCHEMA_VERSION = "pv.chembl-mechanism-context-request/1.0"
OUTPUT_SCHEMA_VERSION = "pv.chembl-mechanism-context-response/1.0"
DEFAULT_MODEL = "gpt-5.6-terra"
DEFAULT_COHORT = "pv_2015_actual_completed_drug_biological_pilot5_v1"
MAX_OUTPUT_TOKENS = 5000
VERIFIER = "pv.ingest.chembl_mechanism_context_llm"
VERIFIER_VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parents[2]
RESPONSE_SCHEMA_PATH = ROOT / "docs/pv/schemas/chembl_mechanism_context_response.schema.json"

PRICING = {
    "gpt-5.6-terra": {"input": 2.0, "output": 12.0},
    "gpt-5.6-luna": {"input": 0.2, "output": 1.2},
}

SYSTEM_PROMPT = """You structure target specificity stated in already-retrieved ChEMBL records.

The asset and the complete ChEMBL mechanism set have already been resolved and enumerated. Do not use outside knowledge and do not add mechanisms, targets, identifiers, aliases, or gene assignments.

For every supplied mechanism:
- Copy source_mechanism_id, target_entity_id, canonical_target_name, and target_level exactly.
- Extract a target_context only when the mechanism source text explicitly narrows the canonical target, for example to a subfamily, binding site, domain, subunit, isoform, or mutation state.
- normalized_name must be a concise phrase occurring verbatim inside its cited quote, ignoring only case and punctuation normalization.
- source_path must name a supplied source item and quote must be an exact substring of that item.
- Component membership lists describe the composition of a family or complex. They do not prove that the asset acts on every component. Always return component_membership_is_target_evidence=false.
- Return a specific_gene_target only when the mechanism text itself explicitly names that supplied component gene. A family-level phrase such as "beta tubulin" does not identify one TUBB gene.
- Empty target_contexts and specific_gene_targets are valid and preferred to inference.
- Set review_required when source wording is internally inconsistent or cannot be represented without interpretation.

Example: "Binds to beta tubulin, vinca site" supports subfamily "beta tubulin" and binding_site "vinca site", but no specific gene target.

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


def response_text(body: dict[str, Any]) -> str:
    texts = [
        content["text"]
        for item in body.get("output") or []
        for content in item.get("content") or []
        if content.get("type") == "output_text" and content.get("text")
    ]
    if not texts:
        raise ValueError("OpenAI response contained no output_text")
    return "".join(texts)


def _mechanism_row(payload: dict[str, Any], mec_id: int) -> dict[str, Any]:
    matches = [row for row in payload.get("mechanisms") or [] if int(row.get("mec_id")) == mec_id]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one archived ChEMBL mechanism {mec_id}; found {len(matches)}")
    return matches[0]


def _source_item(path: str, value: Any, version_id: int) -> dict[str, Any] | None:
    if value is None or isinstance(value, (dict, list)):
        return None
    text = str(value).strip()
    return {"source_path": path, "text": text, "source_record_version_id": version_id} if text else None


def load_packets(conn: Any, cohort_id: str, assets: list[str], limit: int) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT asset.entity_id,asset.active_moiety_name
            FROM pv_core.trial_cohort_member member
            JOIN pv_core.trial_asset_link link
              ON link.nct_id=member.nct_id AND link.resolution_status='resolved'
            JOIN pv_core.asset asset ON asset.entity_id=link.asset_entity_id
            JOIN pv_evidence.asset_target_assertion assertion
              ON assertion.asset_entity_id=asset.entity_id
            WHERE member.cohort_id=%s AND member.membership_status='included'
              AND (%s::text[] IS NULL OR lower(asset.active_moiety_name)=ANY(%s::text[]))
            ORDER BY asset.active_moiety_name,asset.entity_id
            """,
            (cohort_id, [value.casefold() for value in assets] if assets else None,
             [value.casefold() for value in assets] if assets else None),
        )
        asset_rows = cur.fetchall()
    if assets:
        found = {name.casefold() for _, name in asset_rows}
        missing = sorted(set(value.casefold() for value in assets) - found)
        if missing:
            raise SystemExit("Unknown or mechanism-free pilot assets: " + ", ".join(missing))
    if limit:
        asset_rows = asset_rows[:limit]

    packets: list[dict[str, Any]] = []
    for asset_id, asset_name in asset_rows:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT DISTINCT identifier FROM pv_core.entity_identifier
                   WHERE entity_id=%s AND namespace='ChEMBL' ORDER BY identifier""",
                (asset_id,),
            )
            chembl_ids = [row[0] for row in cur.fetchall()]
            cur.execute(
                """
                SELECT assertion.asset_target_assertion_id,assertion.source_record_version_id,
                       assertion.source_native_id,assertion.support_locator,
                       target.entity_id,target.approved_symbol,target.approved_name,
                       target.target_kind
                FROM pv_evidence.asset_target_assertion assertion
                JOIN pv_core.target target ON target.entity_id=assertion.target_entity_id
                WHERE assertion.asset_entity_id=%s
                  AND assertion.source_native_id LIKE 'ChEMBL mechanism:%%'
                ORDER BY assertion.source_native_id,assertion.asset_target_assertion_id
                """,
                (asset_id,),
            )
            assertions = cur.fetchall()
        mechanisms = []
        for assertion_id, mechanism_version_id, native_id, locator, target_id, symbol, target_name, target_kind in assertions:
            mec_id = int(locator["mec_id"])
            target_chembl_id = locator["target_chembl_id"]
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT raw_payload FROM pv_source.source_record_version WHERE source_record_version_id=%s",
                    (mechanism_version_id,),
                )
                mechanism_payload = cur.fetchone()[0]
                mechanism = _mechanism_row(mechanism_payload, mec_id)
                cur.execute(
                    """
                    SELECT version.source_record_version_id,version.raw_payload
                    FROM pv_source.source_record record
                    JOIN pv_source.source_record_version version USING (source_record_id)
                    WHERE record.source_system_id='chembl'
                      AND record.native_record_id=%s
                      AND record.record_type='target_record'
                    ORDER BY version.retrieved_at DESC,version.source_record_version_id DESC
                    LIMIT 1
                    """,
                    (target_chembl_id,),
                )
                target_version_id, target_payload = cur.fetchone()
                cur.execute(
                    """
                    SELECT DISTINCT ON (component_key)
                           component_target_entity_id,gene_symbol_literal,
                           component_name_literal,uniprot_accession_literal
                    FROM pv_core.target_component
                    WHERE group_target_entity_id=%s
                    ORDER BY component_key,source_record_version_id DESC
                    """,
                    (target_id,),
                )
                components = [
                    {
                        "target_entity_id": str(row[0]) if row[0] else None,
                        "gene_symbol": row[1], "protein_name": row[2],
                        "uniprot_accession": row[3],
                    }
                    for row in cur.fetchall()
                ]
            source_items = []
            for field in (
                "mechanism_of_action", "binding_site_name", "binding_site_comment",
                "action_type", "direct_interaction", "variant_sequence",
            ):
                item = _source_item(f"mechanisms[{mec_id}].{field}", mechanism.get(field), mechanism_version_id)
                if item:
                    source_items.append(item)
            for field in ("pref_name", "target_type", "organism"):
                item = _source_item(
                    f"targets[{target_chembl_id}].{field}", target_payload.get(field), target_version_id
                )
                if item:
                    source_items.append(item)
            for index, component in enumerate(components):
                for field in ("gene_symbol", "protein_name", "uniprot_accession"):
                    item = _source_item(
                        f"targets[{target_chembl_id}].components[{index}].{field}",
                        component[field], target_version_id,
                    )
                    if item:
                        source_items.append(item)
            mechanisms.append(
                {
                    "source_mechanism_id": native_id,
                    "mec_id": mec_id,
                    "asset_target_assertion_id": assertion_id,
                    "target_entity_id": str(target_id),
                    "canonical_target_name": symbol or target_name,
                    "target_level": target_kind,
                    "components": components,
                    "source_record_version_ids": sorted({mechanism_version_id, target_version_id}),
                    "source_items": source_items,
                }
            )
        packets.append(
            {
                "packet_version": REQUEST_SCHEMA_VERSION,
                "subject_key": str(asset_id),
                "asset": {
                    "entity_id": str(asset_id), "preferred_name": asset_name,
                    "chembl_ids": chembl_ids,
                },
                "mechanisms": mechanisms,
            }
        )
    return packets


def validate_output(packet: dict[str, Any], parsed: dict[str, Any]) -> None:
    if parsed.get("schema_version") != OUTPUT_SCHEMA_VERSION:
        raise ValueError("response schema_version mismatch")
    if parsed.get("subject_key") != packet["subject_key"]:
        raise ValueError("response subject_key mismatch")
    expected = {row["source_mechanism_id"]: row for row in packet["mechanisms"]}
    returned = parsed.get("mechanisms")
    if not isinstance(returned, list) or {row.get("source_mechanism_id") for row in returned} != set(expected):
        raise ValueError("response must contain exactly one row per supplied mechanism")
    for result in returned:
        source = expected[result["source_mechanism_id"]]
        for field in ("target_entity_id", "canonical_target_name", "target_level"):
            if result.get(field) != source[field]:
                raise ValueError(f"{result['source_mechanism_id']} changed {field}")
        if result.get("component_membership_is_target_evidence") is not False:
            raise ValueError("component membership cannot be promoted to target evidence")
        source_map = {row["source_path"]: row["text"] for row in source["source_items"]}
        mechanism_prefix = f"mechanisms[{source['mec_id']}]."
        for context in result.get("target_contexts") or []:
            path, quote = context["source_path"], context["quote"]
            if path not in source_map or quote not in source_map[path]:
                raise ValueError(f"unsupported target context evidence at {path}")
            if not path.startswith(mechanism_prefix):
                raise ValueError("target context must be asserted by the mechanism record")
            if normalized(context["normalized_name"]) not in normalized(quote):
                raise ValueError("normalized target context is absent from its source quote")
        component_by_id = {
            row["target_entity_id"]: row for row in source["components"] if row["target_entity_id"]
        }
        for gene in result.get("specific_gene_targets") or []:
            component = component_by_id.get(gene["target_entity_id"])
            if component is None or gene["symbol"] != component["gene_symbol"]:
                raise ValueError("specific gene target is not a supplied component candidate")
            path, quote = gene["source_path"], gene["quote"]
            if path not in source_map or quote not in source_map[path] or not path.startswith(mechanism_prefix):
                raise ValueError("specific gene target lacks direct mechanism-record support")
            if normalized(gene["symbol"]) not in normalized(quote):
                raise ValueError("specific gene symbol is absent from its mechanism quote")


def canonical_decision(parsed: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(json.dumps(parsed))
    value.pop("schema_version", None)
    for mechanism in value["mechanisms"]:
        mechanism["target_contexts"].sort(
            key=lambda row: (row["context_type"], row["normalized_name"].casefold(), row["source_path"])
        )
        mechanism["specific_gene_targets"].sort(key=lambda row: row["symbol"].casefold())
        mechanism["warnings"].sort(key=str.casefold)
    value["mechanisms"].sort(key=lambda row: row["source_mechanism_id"])
    value["warnings"].sort(key=str.casefold)
    return value


def call_one(client: Any, packet: dict[str, Any], model: str, output_format: dict[str, Any]) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            response = client.responses.create(
                model=model, instructions=SYSTEM_PROMPT, input=canonical_json(packet),
                max_output_tokens=MAX_OUTPUT_TOKENS, reasoning={"effort": "none"},
                text={"format": output_format}, store=False,
            )
            body = response.model_dump()
            raw = response_text(body)
            parsed = json.loads(raw)
            validate_output(packet, parsed)
            usage = body.get("usage") or {}
            return {
                "packet": packet, "raw": raw, "parsed": parsed,
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
            if attempt < 4:
                time.sleep(min(16, 2**attempt))
    assert last_error is not None
    raise last_error


def json_diff(before: Any, after: Any, path: str = "$") -> list[dict[str, Any]]:
    if type(before) is not type(after):
        return [{"path": path, "before": before, "after": after}]
    if isinstance(before, dict):
        output = []
        for key in sorted(set(before) | set(after)):
            child = f"{path}.{key}"
            if key not in before:
                output.append({"path": child, "before": None, "after": after[key]})
            elif key not in after:
                output.append({"path": child, "before": before[key], "after": None})
            else:
                output.extend(json_diff(before[key], after[key], child))
        return output
    if before != after:
        return [{"path": path, "before": before, "after": after}]
    return []


def resolve_prior_run(cur: Any, current_run: uuid.UUID, value: str | None) -> uuid.UUID | None:
    if value is None:
        return None
    if value != "latest":
        candidate = uuid.UUID(value)
        cur.execute("SELECT task,status FROM pv_evidence.llm_decision_run WHERE decision_run_id=%s", (str(candidate),))
        row = cur.fetchone()
        if row != (TASK, "completed"):
            raise SystemExit(f"Comparison run is not a completed {TASK!r} run")
        return candidate
    cur.execute(
        """SELECT decision_run_id FROM pv_evidence.llm_decision_run
           WHERE task=%s AND status='completed' AND decision_run_id<>%s
           ORDER BY started_at DESC,decision_run_id DESC LIMIT 1""",
        (TASK, str(current_run)),
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit(f"No earlier completed {TASK!r} run exists")
    return row[0]


def store_results(conn: Any, run_id: uuid.UUID, results: list[dict[str, Any]], model: str, compare_to: str | None) -> uuid.UUID | None:
    with conn.cursor() as cur:
        prior_run = resolve_prior_run(cur, run_id, compare_to)
        if prior_run:
            cur.execute(
                "UPDATE pv_evidence.llm_decision_run SET compare_to_run_id=%s WHERE decision_run_id=%s",
                (str(prior_run), str(run_id)),
            )
        for result in results:
            packet, parsed = result["packet"], result["parsed"]
            canonical = canonical_decision(parsed)
            prior_id = prior_hash = None
            if prior_run:
                cur.execute(
                    """SELECT llm_decision_id,decision_sha256 FROM pv_evidence.llm_decision
                       WHERE decision_run_id=%s AND task=%s AND subject_type='asset' AND subject_key=%s""",
                    (str(prior_run), TASK, packet["subject_key"]),
                )
                row = cur.fetchone()
                if row:
                    prior_id, prior_hash = row
            decision_hash = sha256_text(canonical_json(canonical))
            change_status = "not_compared" if not prior_run else "added" if not prior_id else "unchanged" if prior_hash == decision_hash else "changed"
            cur.execute(
                """
                INSERT INTO pv_evidence.llm_decision
                  (decision_run_id,task,subject_type,subject_key,input_sha256,raw_response,
                   parsed_output,output_sha256,canonical_decision,decision_sha256,
                   prior_decision_id,change_status,input_payload,provider_request_id,
                   model_parameters,usage,validation_status,validation_detail)
                VALUES (%s,%s,'asset',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        'validated','[]'::jsonb)
                RETURNING llm_decision_id
                """,
                (
                    str(run_id), TASK, packet["subject_key"], sha256_text(canonical_json(packet)),
                    result["raw"], Json(parsed), sha256_text(canonical_json(parsed)), Json(canonical),
                    decision_hash, prior_id, change_status, Json(packet), result["provider_request_id"],
                    Json({"reasoning_effort": "none", "max_output_tokens": MAX_OUTPUT_TOKENS,
                          "structured_outputs": True, "requested_model": model}), Json(result["usage"]),
                ),
            )
            decision_id = cur.fetchone()[0]
            versions = sorted({
                version_id for mechanism in packet["mechanisms"]
                for version_id in mechanism["source_record_version_ids"]
            })
            for ordinal, version_id in enumerate(versions):
                cur.execute(
                    """INSERT INTO pv_evidence.llm_decision_source
                         (llm_decision_id,source_record_version_id,ordinal)
                       VALUES (%s,%s,%s)""",
                    (decision_id, version_id, ordinal),
                )
            input_by_mechanism = {row["source_mechanism_id"]: row for row in packet["mechanisms"]}
            for mechanism in parsed["mechanisms"]:
                source = input_by_mechanism[mechanism["source_mechanism_id"]]
                source_versions = {row["source_path"]: row["source_record_version_id"] for row in source["source_items"]}
                for context in mechanism["target_contexts"]:
                    cur.execute(
                        """
                        INSERT INTO pv_evidence.asset_target_context_assertion
                          (asset_target_assertion_id,context_type,context_name,context_normalized,
                           source_record_version_id,source_path,support_quote,llm_decision_id,
                           verification_status,search_eligible,verifier,verifier_version)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'exact_source_span',true,%s,%s)
                        ON CONFLICT DO NOTHING
                        """,
                        (
                            source["asset_target_assertion_id"], context["context_type"],
                            context["normalized_name"], normalized(context["normalized_name"]),
                            source_versions[context["source_path"]], context["source_path"],
                            context["quote"], decision_id, VERIFIER, VERIFIER_VERSION,
                        ),
                    )
        conn.commit()
    return prior_run


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
            status = "added" if prior_id is None else "removed" if current_id is None else "unchanged" if current_hash == prior_hash else "changed"
            counts[status] += 1
            diff = json_diff(prior_value, current_value) if status == "changed" else []
            cur.execute(
                """
                INSERT INTO pv_evidence.llm_decision_comparison
                  (current_run_id,compare_to_run_id,task,subject_type,subject_key,
                   change_status,current_decision_id,prior_decision_id,field_diff)
                VALUES (%s,%s,%s,'asset',%s,%s,%s,%s,%s)
                """,
                (str(current), str(prior), TASK, key, status, current_id, prior_id, Json(diff)),
            )
        conn.commit()
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cohort-id", default=DEFAULT_COHORT)
    parser.add_argument("--asset", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--compare-decisions-to")
    parser.add_argument("--confirm-paid", action="store_true")
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or args.limit < 0:
        parser.error("--workers must be positive and --limit nonnegative")
    return args


def main() -> None:
    args = parse_args()
    if not args.confirm_paid:
        raise SystemExit("OpenAI Responses calls are paid; pass --confirm-paid")
    if not args.commit:
        raise SystemExit("This runner stores immutable decisions; pass --commit")
    if OpenAI is None or not os.environ.get("OPENAI_API_KEY") or not os.environ.get("DATABASE_URL"):
        raise SystemExit("openai, OPENAI_API_KEY, and DATABASE_URL are required")
    response_schema = json.loads(RESPONSE_SCHEMA_PATH.read_text())
    response_schema.pop("$schema", None)
    response_schema.pop("$id", None)
    response_schema.pop("title", None)
    output_format = {"type": "json_schema", "name": "pv_chembl_mechanism_context", "strict": True, "schema": response_schema}

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    run_id = uuid.uuid4()
    started_at = datetime.now(timezone.utc)
    try:
        packets = load_packets(conn, args.cohort_id, args.asset, args.limit)
        if not packets:
            raise SystemExit("No ChEMBL mechanism packets selected")
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pv_evidence.llm_decision_run
                  (decision_run_id,task,provider,model,prompt_version,output_schema_version,
                   code_commit,parameters,status,started_at)
                VALUES (%s,%s,'openai',%s,%s,%s,%s,%s,'running',%s)
                """,
                (
                    str(run_id), TASK, args.model, PROMPT_VERSION, OUTPUT_SCHEMA_VERSION,
                    git_commit(), Json({"cohort_id": args.cohort_id, "assets": args.asset,
                    "limit": args.limit, "workers": args.workers, "reasoning_effort": "none",
                    "max_output_tokens": MAX_OUTPUT_TOKENS, "system_prompt": SYSTEM_PROMPT,
                    "system_prompt_sha256": sha256_text(SYSTEM_PROMPT),
                    "output_schema": response_schema,
                    "output_schema_sha256": sha256_text(canonical_json(response_schema))}), started_at,
                ),
            )
            conn.commit()
        print(f"run_id={run_id} assets={len(packets)} model={args.model}", flush=True)
        client = OpenAI()
        results, errors = [], []
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            pending = {executor.submit(call_one, client, packet, args.model, output_format): packet for packet in packets}
            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    packet = pending.pop(future)
                    try:
                        results.append(future.result())
                        print(f"completed {packet['asset']['preferred_name']}", flush=True)
                    except Exception as exc:
                        error = f"{packet['asset']['preferred_name']}: {type(exc).__name__}: {exc}"
                        errors.append(error)
                        print(f"failed {error}", flush=True)
        if errors:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE pv_evidence.llm_decision_run SET status='failed',completed_at=%s,
                         parameters=parameters || %s::jsonb WHERE decision_run_id=%s""",
                    (datetime.now(timezone.utc), Json({"errors": errors}), str(run_id)),
                )
                conn.commit()
            raise SystemExit("; ".join(errors))
        prior_run = store_results(conn, run_id, sorted(results, key=lambda row: row["packet"]["asset"]["preferred_name"]), args.model, args.compare_decisions_to)
        input_tokens = sum(row["usage"]["input_tokens"] for row in results)
        output_tokens = sum(row["usage"]["output_tokens"] for row in results)
        price = PRICING.get(args.model)
        cost = input_tokens / 1_000_000 * price["input"] + output_tokens / 1_000_000 * price["output"] if price else None
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE pv_evidence.llm_decision_run SET status='completed',completed_at=%s,
                     model_snapshot=%s,parameters=parameters || %s::jsonb WHERE decision_run_id=%s""",
                (datetime.now(timezone.utc), ",".join(sorted({row["actual_model"] for row in results})),
                 Json({"input_tokens": input_tokens, "output_tokens": output_tokens,
                       "estimated_cost_usd": cost}), str(run_id)),
            )
            conn.commit()
        counts = store_comparison(conn, run_id, prior_run) if prior_run else None
        print(f"stored={len(results)} input_tokens={input_tokens} output_tokens={output_tokens} estimated_cost_usd={cost if cost is not None else 'unknown'}", flush=True)
        if prior_run:
            print(f"compare_to={prior_run} counts={canonical_json(counts)}", flush=True)
    except Exception as exc:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE pv_evidence.llm_decision_run
                   SET status='failed',completed_at=%s,
                       parameters=parameters || %s::jsonb
                   WHERE decision_run_id=%s AND status='running'""",
                (
                    datetime.now(timezone.utc),
                    Json({"persistence_error": f"{type(exc).__name__}: {exc}"}),
                    str(run_id),
                ),
            )
        conn.commit()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
