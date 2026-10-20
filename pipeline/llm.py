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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import anthropic
import psycopg2
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from dotenv import load_dotenv
from psycopg2.extras import Json, execute_values

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(REPO, ".env"))

MODEL = "claude-opus-5"
BATCH_SIZE = 2000
# anthropic: Message Batches on the Anthropic API. openrouter: concurrent
# Messages calls through OpenRouter's Anthropic-compatible endpoint. agent:
# item chunks are written under .cache/agent/<task>/<run>/ for Claude Code
# workflow agents, and each <chunk>.out.jsonl they write is validated and
# stored as it appears.
PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic")
WORKERS = int(os.environ.get("LLM_WORKERS", "24"))
AGENT_CHUNK = int(os.environ.get("LLM_AGENT_CHUNK", "100"))
AGENT_MODEL = "claude-opus-5-5"  # the Claude Code session model the workflow agents run on
OPENROUTER_MODELS = {"claude-opus-5": "anthropic/claude-opus-5", "claude-opus-5-5": "anthropic/claude-opus-5.5",
                     "claude-sonnet-5": "anthropic/claude-sonnet-5"}


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


def client() -> anthropic.Anthropic:
    if PROVIDER == "openrouter":
        return anthropic.Anthropic(base_url="https://openrouter.ai/api", api_key=None,
                                   auth_token=os.environ["OPENROUTER_API_KEY"], max_retries=8)
    return anthropic.Anthropic(max_retries=8)


def provider_model(model: str) -> str:
    if PROVIDER == "openrouter":
        return OPENROUTER_MODELS[model]
    return AGENT_MODEL if PROVIDER == "agent" else model


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
            model=provider_model(self.model),
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


def _store_reused(conn, run_id: uuid.UUID, task: Task, items: dict[str, dict[str, Any]],
                  reused: dict[str, tuple]) -> None:
    """Copy earlier decisions into this run in bulk, committing every 2,000 rows."""
    rows = []
    for key, (_, _, raw, parsed, request_id, usage, decision_id) in reused.items():
        rows.append((str(run_id), task.name, task.subject_type, key,
                     sha256_text(canonical_json(items[key])), raw, Json(parsed),
                     sha256_text(raw), Json(parsed), sha256_text(canonical_json(parsed)),
                     decision_id, "unchanged", Json(items[key]), request_id,
                     Json({"model": task.model, "effort": task.effort, "max_tokens": task.max_tokens}),
                     Json(usage), "validated", Json([])))
    for start in range(0, len(rows), 2000):
        with conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO pv_evidence.llm_decision
                  (decision_run_id, task, subject_type, subject_key, input_sha256, raw_response,
                   parsed_output, output_sha256, canonical_decision, decision_sha256,
                   prior_decision_id, change_status, input_payload, provider_request_id,
                   model_parameters, usage, validation_status, validation_detail)
                VALUES %s""", rows[start:start + 2000])
        conn.commit()


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
    api = client()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pv_evidence.llm_decision_run
              (decision_run_id, task, provider, model, prompt_version, output_schema_version,
               code_commit, parameters, status, started_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'running',%s)
            """,
            (str(run_id), task.name, PROVIDER, provider_model(task.model), task.prompt_version,
             task.schema_version,
             git_commit(),
             Json({"system_prompt": task.system, "system_prompt_sha256": sha256_text(task.system),
                   "output_schema": task.schema,
                   "output_schema_sha256": sha256_text(canonical_json(task.schema)),
                   "effort": task.effort, "max_tokens": task.max_tokens, "n_items": len(items),
                   "reuse_by": reuse_by, **task.params}),
             datetime.now(timezone.utc)),
        )
        reused = _reusable(cur, task, items, reuse_by)
        conn.commit()
    _store_reused(conn, run_id, task, items, reused)
    todo = [k for k in items if k not in reused]
    print(f"[{task.name}] run={run_id} items={len(items)} reused={len(reused)} new={len(todo)}", flush=True)
    if PROVIDER == "openrouter":
        _run_concurrent(api, conn, run_id, task, items, todo)
    elif PROVIDER == "agent":
        _run_agents(conn, run_id, task, items, todo, poll_seconds)
    else:
        _run_batches(api, conn, run_id, task, items, todo, poll_seconds)

    with conn.cursor() as cur:
        cur.execute("UPDATE pv_evidence.llm_decision_run SET status='completed', completed_at=%s "
                    "WHERE decision_run_id=%s", (datetime.now(timezone.utc), str(run_id)))
    conn.commit()
    conn.close()
    return run_id


def _parse(task: Task, payload: dict[str, Any], msg) -> tuple[str, dict | None, str | None, dict]:
    """(raw text, parsed output, error, usage) for one Messages response."""
    usage = {"input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens,
             "cache_read_input_tokens": msg.usage.cache_read_input_tokens or 0}
    if getattr(msg.usage, "cost", None) is not None:  # OpenRouter reports the billed cost
        usage["cost_usd"] = msg.usage.cost
    raw = next((b.text for b in msg.content if b.type == "text"), "")
    if msg.stop_reason in ("refusal", "max_tokens"):
        return raw, None, msg.stop_reason, usage
    try:
        parsed = json.loads(raw)
        if task.validate:
            task.validate(payload, parsed)
        return raw, parsed, None, usage
    except Exception as exc:  # invalid JSON or failed semantic check
        return raw, None, f"{type(exc).__name__}: {exc}", usage


def _run_concurrent(api, conn, run_id: uuid.UUID, task: Task, items: dict[str, dict[str, Any]],
                    todo: list[str]) -> None:
    def call(key):
        try:
            msg = api.messages.create(**task.request_params(items[key]))
            return key, msg.id, *_parse(task, items[key], msg)
        except anthropic.APIError as exc:
            return key, "", "", None, f"{type(exc).__name__}: {exc}", {}

    n_ok = n_bad = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool, conn.cursor() as cur:
        for i, fut in enumerate(as_completed([pool.submit(call, k) for k in todo]), 1):
            key, request_id, raw, parsed, error, usage = fut.result()
            _store(cur, run_id, task, key, items[key], raw, parsed, request_id, usage, error, None)
            n_bad += error is not None
            n_ok += error is None
            if i % 25 == 0:  # short transactions: migrations adding FKs to llm_decision need gaps
                conn.commit()
            if i % 500 == 0 or i == len(todo):
                print(f"[{task.name}] {i}/{len(todo)} validated={n_ok} invalid={n_bad}", flush=True)
    conn.commit()


AGENT_INSTRUCTIONS = """Each line of the chunk file is one item: {"subject_key": ..., "user_message": ...}.
Decide every item independently, exactly as if the user_message had been sent to a model whose
system prompt is task.json's "system", and whose reply must be one JSON object valid against
task.json's "output_schema". Write one line per item to the .out.jsonl file:
{"subject_key": <same key>, "output": <the JSON object>}. After the last item write {"done": true}."""


def _run_agents(conn, run_id: uuid.UUID, task: Task, items: dict[str, dict[str, Any]], todo: list[str],
                poll_seconds: int) -> None:
    import jsonschema
    out_dir = os.path.join(REPO, ".cache", "agent", task.name, str(run_id))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "task.json"), "w") as f:
        json.dump({"task": task.name, "prompt_version": task.prompt_version, "system": task.system,
                   "output_schema": task.schema, "instructions": AGENT_INSTRUCTIONS}, f, indent=1)
    chunks = []
    for start in range(0, len(todo), AGENT_CHUNK):
        name = f"chunk_{start // AGENT_CHUNK:05d}"
        with open(os.path.join(out_dir, name + ".jsonl"), "w") as f:
            for key in todo[start:start + AGENT_CHUNK]:
                f.write(json.dumps({"subject_key": key, "user_message": task.render(items[key])}) + "\n")
        chunks.append(name)
    print(f"[{task.name}] wrote {len(chunks)} agent chunks to {out_dir}", flush=True)

    pending = set(chunks)
    while pending:
        for name in sorted(pending):
            path = os.path.join(out_dir, name + ".out.jsonl")
            if not os.path.exists(path):
                continue
            lines = [json.loads(l) for l in open(path) if l.strip()]
            if not lines or not lines[-1].get("done"):
                continue
            expected = [json.loads(l)["subject_key"] for l in open(os.path.join(out_dir, name + ".jsonl"))]
            got = {r["subject_key"]: r.get("output") for r in lines if "subject_key" in r}
            n_bad = 0
            with conn.cursor() as cur:
                for key in expected:
                    out, error = got.get(key), None
                    if out is None:
                        error = "agent_missing"
                    else:
                        try:
                            jsonschema.validate(out, task.schema)
                            if task.validate:
                                task.validate(items[key], out)
                        except Exception as exc:
                            error = f"{type(exc).__name__}: {str(exc)[:300]}"
                    raw = json.dumps(out) if out is not None else ""
                    _store(cur, run_id, task, key, items[key], raw, None if error else out,
                           f"agent:{name}", {}, error, None)
                    n_bad += error is not None
            conn.commit()
            pending.discard(name)
            print(f"[{task.name}] {name}: imported {len(expected)} invalid={n_bad} ({len(pending)} chunks left)",
                  flush=True)
        if pending:
            time.sleep(poll_seconds)


def _run_batches(api, conn, run_id: uuid.UUID, task: Task, items: dict[str, dict[str, Any]],
                 todo: list[str], poll_seconds: int) -> None:
    custom_ids, pending = {}, []
    for start in range(0, len(todo), BATCH_SIZE):
        chunk = todo[start:start + BATCH_SIZE]
        requests = []
        for i, key in enumerate(chunk):
            cid = f"r{start + i}"
            custom_ids[cid] = key
            requests.append(Request(custom_id=cid,
                                    params=MessageCreateParamsNonStreaming(**task.request_params(items[key]))))
        batch = api.messages.batches.create(requests=requests)
        pending.append(batch.id)
        print(f"[{task.name}] submitted batch {batch.id} ({len(chunk)} requests)", flush=True)

    while pending:
        time.sleep(poll_seconds)
        ended = [b for b in pending
                 if api.messages.batches.retrieve(b).processing_status == "ended"]
        for batch_id in ended:
            pending.remove(batch_id)
            _collect(api, conn, run_id, task, items, custom_ids, batch_id)


def _collect(api, conn, run_id: uuid.UUID, task: Task, items: dict[str, dict[str, Any]],
             custom_ids: dict[str, str], batch_id: str) -> None:
    """Validate and store every result of one ended batch."""
    n_ok = n_bad = 0
    with conn.cursor() as cur:
        for result in api.messages.batches.results(batch_id):
            key = custom_ids[result.custom_id]
            raw, parsed, error, usage = "", None, None, {}
            if result.result.type == "succeeded":
                raw, parsed, error, usage = _parse(task, items[key], result.result.message)
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
