"""Anthropic Messages runner that records every decision in
pv_evidence.llm_decision_run / pv_evidence.llm_decision.

A task supplies a system prompt, a JSON schema and one input payload per
subject. The runner reuses any validated decision from an earlier run of the
same task whose prompt version and input hash match, sends the rest to the
Messages API (directly for at most DIRECT_MAX items, otherwise as Message
Batches), validates each response against the schema, and stores raw output,
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
from dataclasses import dataclass
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
POLL_SECONDS = 60
WORKERS = 24  # concurrent Messages calls of a direct run
# Runs with at most this many new items call the Messages API directly
# instead of waiting in the batch queue (which can sit for hours).
DIRECT_MAX = int(os.environ.get("LLM_DIRECT_MAX", "100"))


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_commit() -> str | None:
    result = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=False)
    value = result.stdout.strip()
    return value if result.returncode == 0 and len(value) == 40 else None


KEEPALIVE = {"keepalives": 1, "keepalives_idle": 30, "keepalives_interval": 10, "keepalives_count": 3}


def connect():
    """A connection that notices a dead peer within about a minute instead of hanging."""
    return psycopg2.connect(os.environ["DATABASE_URL"], **KEEPALIVE)


def register_release(cur, name: str, version: str, url: str, sha: str, metadata: dict) -> int:
    cur.execute(
        """INSERT INTO preclin.evidence_source_release
             (source_name, source_version, source_url, content_sha256, metadata)
           VALUES (%s,%s,%s,%s,%s)
           ON CONFLICT (source_name, source_version, content_sha256) DO UPDATE SET metadata = EXCLUDED.metadata
           RETURNING source_release_id""",
        (name, version, url, sha, Json(metadata)))
    return cur.fetchone()[0]


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
    """subject_key -> (raw_response, parsed_output, provider_request_id, usage,
    llm_decision_id) of validated decisions from earlier runs of this task and
    prompt version: with reuse_by='input' the latest one per subject whose
    input hash equals the current payload's hash; with reuse_by='subject' the
    latest one per subject whatever its input."""
    keys = list(items)
    hashes = [sha256_text(canonical_json(items[k])) for k in keys]
    cur.execute(
        """
        SELECT DISTINCT ON (d.subject_key) d.subject_key, d.raw_response, d.parsed_output,
               d.provider_request_id, d.usage, d.llm_decision_id
        FROM unnest(%s::text[], %s::text[]) AS w(subject_key, input_sha256)
        JOIN pv_evidence.llm_decision d ON d.subject_key = w.subject_key
             AND (%s = 'subject' OR d.input_sha256 = w.input_sha256)
        JOIN pv_evidence.llm_decision_run r USING (decision_run_id)
        WHERE d.task = %s AND d.subject_type = %s AND r.prompt_version = %s
          AND r.output_schema_version = %s AND d.validation_status = 'validated'
        ORDER BY d.subject_key, d.created_at DESC
        """,
        (keys, hashes, reuse_by, task.name, task.subject_type, task.prompt_version, task.schema_version),
    )
    return {row[0]: row[1:] for row in cur.fetchall()}


def _row(run_id: uuid.UUID, task: Task, key: str, payload: dict[str, Any], raw: str,
         parsed: dict[str, Any] | None, request_id: str, usage: dict[str, Any],
         error: str | None = None, prior_id: int | None = None) -> tuple:
    """One llm_decision row; prior_id is the earlier decision a reused one copies."""
    canonical = parsed if parsed is not None else {"error": error}
    return (str(run_id), task.name, task.subject_type, key,
            sha256_text(canonical_json(payload)), raw, Json(canonical),
            sha256_text(raw), Json(canonical), sha256_text(canonical_json(canonical)),
            prior_id, "unchanged" if prior_id else "not_compared", Json(payload), request_id,
            Json({"model": task.model, "effort": task.effort, "max_tokens": task.max_tokens}),
            Json(usage), "invalid" if error else "validated", Json([error] if error else []))


def _insert(conn, rows: list[tuple]) -> None:
    """Insert decision rows, committing every 2,000."""
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


def run(task: Task, items: dict[str, dict[str, Any]], *, reuse_by: str = "input") -> uuid.UUID:
    """Decide every item (subject_key -> payload). Returns the run id; the
    run's decisions cover every key, reused or new. reuse_by='subject' keeps
    earlier decisions when only incidental payload details (e.g. the order of
    context rows) changed."""
    conn = connect()
    api = anthropic.Anthropic(max_retries=8)
    run_id = uuid.uuid4()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pv_evidence.llm_decision_run
              (decision_run_id, task, provider, model, prompt_version, output_schema_version,
               code_commit, parameters, status, started_at)
            VALUES (%s,%s,'anthropic',%s,%s,%s,%s,%s,'running',%s)
            """,
            (str(run_id), task.name, task.model, task.prompt_version, task.schema_version, git_commit(),
             Json({"system_prompt": task.system, "system_prompt_sha256": sha256_text(task.system),
                   "output_schema": task.schema,
                   "output_schema_sha256": sha256_text(canonical_json(task.schema)),
                   "effort": task.effort, "max_tokens": task.max_tokens, "n_items": len(items),
                   "reuse_by": reuse_by}),
             datetime.now(timezone.utc)),
        )
        reused = _reusable(cur, task, items, reuse_by)
        conn.commit()
    _insert(conn, [_row(run_id, task, key, items[key], raw, parsed, request_id, usage, prior_id=decision_id)
                   for key, (raw, parsed, request_id, usage, decision_id) in reused.items()])
    todo = [k for k in items if k not in reused]
    print(f"[{task.name}] run={run_id} items={len(items)} reused={len(reused)} new={len(todo)}", flush=True)
    if len(todo) <= DIRECT_MAX:
        _run_concurrent(api, conn, run_id, task, items, todo)
    else:
        _run_batches(api, conn, run_id, task, items, todo)
    with connect() as conn, conn.cursor() as cur:
        cur.execute("UPDATE pv_evidence.llm_decision_run SET status='completed', completed_at=%s "
                    "WHERE decision_run_id=%s", (datetime.now(timezone.utc), str(run_id)))
    return run_id


def _parse(task: Task, payload: dict[str, Any], msg) -> tuple[str, dict | None, str | None, dict]:
    """(raw text, parsed output, error, usage) for one Messages response."""
    usage = {"input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens,
             "cache_read_input_tokens": msg.usage.cache_read_input_tokens or 0}
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
    pending = []  # rows not yet committed, replayed after a dropped connection
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for i, fut in enumerate(as_completed([pool.submit(call, k) for k in todo]), 1):
            key, request_id, raw, parsed, error, usage = fut.result()
            pending.append(_row(run_id, task, key, items[key], raw, parsed, request_id, usage, error))
            n_bad += error is not None
            n_ok += error is None
            if i % 25 == 0 or i == len(todo):  # short transactions: FK migrations on llm_decision need gaps
                for attempt in range(5):
                    try:
                        _insert(conn, pending)
                        pending = []
                        break
                    except psycopg2.OperationalError:
                        time.sleep(10 * (attempt + 1))
                        conn = connect()
                else:
                    raise RuntimeError("database unreachable")
            if i % 500 == 0 or i == len(todo):
                print(f"[{task.name}] {i}/{len(todo)} validated={n_ok} invalid={n_bad}", flush=True)


def _run_batches(api, conn, run_id: uuid.UUID, task: Task, items: dict[str, dict[str, Any]],
                 todo: list[str]) -> None:
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
        time.sleep(POLL_SECONDS)
        ended = [b for b in pending
                 if api.messages.batches.retrieve(b).processing_status == "ended"]
        for batch_id in ended:
            pending.remove(batch_id)
            rows, n_ok, n_bad = [], 0, 0
            for result in api.messages.batches.results(batch_id):
                key = custom_ids[result.custom_id]
                raw, parsed, error, usage = "", None, f"batch_{result.result.type}", {}
                if result.result.type == "succeeded":
                    raw, parsed, error, usage = _parse(task, items[key], result.result.message)
                rows.append(_row(run_id, task, key, items[key], raw, parsed,
                                 f"{batch_id}/{result.custom_id}", usage, error))
                n_bad += error is not None
                n_ok += error is None
            _insert(conn, rows)
            print(f"[{task.name}] batch {batch_id}: validated={n_ok} invalid={n_bad}", flush=True)


def decisions(run_id: uuid.UUID) -> list[tuple[str, int, dict[str, Any]]]:
    """(subject_key, llm_decision_id, parsed_output) for every validated decision of a run."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT subject_key, llm_decision_id, parsed_output FROM pv_evidence.llm_decision "
                    "WHERE decision_run_id = %s AND validation_status = 'validated' ORDER BY subject_key",
                    (str(run_id),))
        return cur.fetchall()
