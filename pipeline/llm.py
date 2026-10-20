"""Anthropic Message Batches runner that records every decision in
pv_evidence.llm_decision_run / pv_evidence.llm_decision.

A task supplies a system prompt, a JSON schema and one input payload per
subject. The runner reuses any validated decision from an earlier run of the
same task whose prompt version and input hash match, submits the rest as
batches, validates each response against the schema, and stores raw output,
parsed output and usage with the run's prompt, schema and code commit.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import anthropic
import psycopg2
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from dotenv import load_dotenv
from psycopg2.extras import Json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(REPO, ".env"))

MODEL = "claude-opus-5"
BATCH_SIZE = 2000


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def git_commit() -> str | None:
    result = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=False)
    value = result.stdout.strip()
    return value if result.returncode == 0 and len(value) == 40 else None


def connect():
    return psycopg2.connect(os.environ["DATABASE_URL"])


@dataclass
class Task:
    """One LLM classification task. `render` turns an input payload into the
    user message; `validate` raises on semantically invalid output."""

    name: str
    prompt_version: str
    schema_version: str
    system: str
    schema: dict[str, Any]
    render: Callable[[dict[str, Any]], str]
    subject_type: str
    validate: Callable[[dict[str, Any], dict[str, Any]], None] | None = None
    model: str = MODEL
    effort: str = "medium"
    max_tokens: int = 8000
    params: dict[str, Any] = field(default_factory=dict)

    def request_params(self, payload: dict[str, Any]) -> dict[str, Any]:
        return dict(
            model=self.model,
            max_tokens=self.max_tokens,
            system=[{"type": "text", "text": self.system, "cache_control": {"type": "ephemeral"}}],
            output_config={"effort": self.effort,
                           "format": {"type": "json_schema", "schema": self.schema}},
            messages=[{"role": "user", "content": self.render(payload)}],
        )


def _reusable(cur, task: Task, items: dict[str, dict[str, Any]], reuse_by: str) -> dict[str, tuple]:
    """Validated decisions from earlier runs of this task and prompt version:
    with reuse_by='input' only those whose input hash equals the current
    payload's hash; with reuse_by='subject' the latest one per subject."""
    hashes = {key: sha256_text(canonical_json(payload)) for key, payload in items.items()}
    cur.execute(
        """
        SELECT DISTINCT ON (d.subject_key) d.subject_key, d.input_sha256, d.raw_response,
               d.parsed_output, d.provider_request_id, d.usage, d.llm_decision_id
        FROM pv_evidence.llm_decision d
        JOIN pv_evidence.llm_decision_run r USING (decision_run_id)
        WHERE d.task = %s AND d.subject_type = %s AND r.prompt_version = %s
          AND r.output_schema_version = %s AND d.validation_status = 'validated'
          AND d.subject_key = ANY(%s)
        ORDER BY d.subject_key, d.created_at DESC
        """,
        (task.name, task.subject_type, task.prompt_version, task.schema_version, list(items)),
    )
    return {row[0]: row for row in cur.fetchall()
            if reuse_by == "subject" or hashes.get(row[0]) == row[1]}


def _store(cur, run_id: uuid.UUID, task: Task, key: str, payload: dict[str, Any], raw: str,
           parsed: dict[str, Any] | None, request_id: str, usage: dict[str, Any],
           error: str | None, prior_id: int | None) -> None:
    canonical = parsed if parsed is not None else {"error": error}
    cur.execute(
        """
        INSERT INTO pv_evidence.llm_decision
          (decision_run_id, task, subject_type, subject_key, input_sha256, raw_response,
           parsed_output, output_sha256, canonical_decision, decision_sha256,
           prior_decision_id, change_status, input_payload, provider_request_id,
           model_parameters, usage, validation_status, validation_detail)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (str(run_id), task.name, task.subject_type, key,
         sha256_text(canonical_json(payload)), raw, Json(canonical),
         sha256_text(raw), Json(canonical), sha256_text(canonical_json(canonical)),
         prior_id, "unchanged" if prior_id else "not_compared", Json(payload), request_id,
         Json({"model": task.model, "effort": task.effort, "max_tokens": task.max_tokens}),
         Json(usage), "invalid" if error else "validated",
         Json([error] if error else [])),
    )


def run(task: Task, items: dict[str, dict[str, Any]], *, poll_seconds: int = 60,
        reuse_by: str = "input") -> uuid.UUID:
    """Decide every item (subject_key -> payload). Returns the run id; the
    run's decisions cover every key, reused or new. reuse_by='subject' keeps
    earlier decisions when only incidental payload details (e.g. the order of
    context rows) changed."""
    conn = connect()
    run_id = uuid.uuid4()
    client = anthropic.Anthropic()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pv_evidence.llm_decision_run
              (decision_run_id, task, provider, model, prompt_version, output_schema_version,
               code_commit, parameters, status, started_at)
            VALUES (%s,%s,'anthropic',%s,%s,%s,%s,%s,'running',%s)
            """,
            (str(run_id), task.name, task.model, task.prompt_version, task.schema_version,
             git_commit(),
             Json({"system_prompt": task.system, "system_prompt_sha256": sha256_text(task.system),
                   "output_schema": task.schema,
                   "output_schema_sha256": sha256_text(canonical_json(task.schema)),
                   "effort": task.effort, "max_tokens": task.max_tokens, "n_items": len(items),
                   "reuse_by": reuse_by, **task.params}),
             datetime.now(timezone.utc)),
        )
        reused = _reusable(cur, task, items, reuse_by)
        for key, row in reused.items():
            _, _, raw, parsed, request_id, usage, decision_id = row
            _store(cur, run_id, task, key, items[key], raw, parsed, request_id, usage, None, decision_id)
        conn.commit()
    todo = [k for k in items if k not in reused]
    print(f"[{task.name}] run={run_id} items={len(items)} reused={len(reused)} new={len(todo)}", flush=True)

    custom_ids, pending = {}, []
    for start in range(0, len(todo), BATCH_SIZE):
        chunk = todo[start:start + BATCH_SIZE]
        requests = []
        for i, key in enumerate(chunk):
            cid = f"r{start + i}"
            custom_ids[cid] = key
            requests.append(Request(custom_id=cid,
                                    params=MessageCreateParamsNonStreaming(**task.request_params(items[key]))))
        batch = client.messages.batches.create(requests=requests)
        pending.append(batch.id)
        print(f"[{task.name}] submitted batch {batch.id} ({len(chunk)} requests)", flush=True)

    while pending:
        time.sleep(poll_seconds)
        ended = [b for b in pending
                 if client.messages.batches.retrieve(b).processing_status == "ended"]
        for batch_id in ended:
            pending.remove(batch_id)
            _collect(client, conn, run_id, task, items, custom_ids, batch_id)

    with conn.cursor() as cur:
        cur.execute("UPDATE pv_evidence.llm_decision_run SET status='completed', completed_at=%s "
                    "WHERE decision_run_id=%s", (datetime.now(timezone.utc), str(run_id)))
    conn.commit()
    conn.close()
    return run_id


def _collect(client, conn, run_id: uuid.UUID, task: Task, items: dict[str, dict[str, Any]],
             custom_ids: dict[str, str], batch_id: str) -> None:
    """Validate and store every result of one ended batch."""
    n_ok = n_bad = 0
    with conn.cursor() as cur:
        for result in client.messages.batches.results(batch_id):
            key = custom_ids[result.custom_id]
            raw, parsed, error, usage = "", None, None, {}
            if result.result.type == "succeeded":
                msg = result.result.message
                usage = {"input_tokens": msg.usage.input_tokens,
                         "output_tokens": msg.usage.output_tokens,
                         "cache_read_input_tokens": msg.usage.cache_read_input_tokens or 0}
                raw = next((b.text for b in msg.content if b.type == "text"), "")
                if msg.stop_reason in ("refusal", "max_tokens"):
                    error = msg.stop_reason
                else:
                    try:
                        parsed = json.loads(raw)
                        if task.validate:
                            task.validate(items[key], parsed)
                    except Exception as exc:  # invalid JSON or failed semantic check
                        parsed, error = None, f"{type(exc).__name__}: {exc}"
            else:
                error = f"batch_{result.result.type}"
            _store(cur, run_id, task, key, items[key], raw, parsed,
                   f"{batch_id}/{result.custom_id}", usage, error, None)
            n_bad += error is not None
            n_ok += error is None
    conn.commit()
    print(f"[{task.name}] batch {batch_id}: validated={n_ok} invalid={n_bad}", flush=True)


def decisions(run_id: uuid.UUID | str) -> dict[str, dict[str, Any]]:
    """subject_key -> parsed output for every validated decision of a run."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT subject_key, parsed_output FROM pv_evidence.llm_decision "
                    "WHERE decision_run_id=%s AND validation_status='validated'", (str(run_id),))
        return dict(cur.fetchall())
