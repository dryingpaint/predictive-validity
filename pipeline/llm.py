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
import re
import subprocess
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import anthropic
import httpx2
import pandas as pd
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
WORKERS = int(os.environ.get("LLM_WORKERS", "24"))  # concurrent Messages calls of a direct run
STREAM_ATTEMPTS = 3  # the SDK retries opening a request, not a stream that drops partway
API_FAILURE_LIMIT = 0.2  # share of a direct run's calls failing at the API (e.g. credit exhausted) that stops it
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
CONNECT_ATTEMPTS = 6
# Batches a run submitted, recorded as they are created (batch id -> custom id -> [subject key, input
# sha256]) and dropped once collected, so a run that stops before collecting them is resumed by the
# next run of the same task with the same inputs instead of resubmitted.
BATCH_MANIFESTS = os.path.join(REPO, ".cache", "llm_batches")
API_ATTEMPTS = 10  # batch status and result calls through a network outage, waiting 30 s more each time


def connect():
    """A connection that notices a dead peer within about a minute instead of hanging,
    retried with backoff while the server cannot be reached."""
    for attempt in range(CONNECT_ATTEMPTS):
        try:
            return psycopg2.connect(os.environ["DATABASE_URL"], **KEEPALIVE)
        except psycopg2.OperationalError:
            if attempt == CONNECT_ATTEMPTS - 1:
                raise
            time.sleep(10 * (attempt + 1))


def register_release(cur, name: str, version: str, url: str, sha: str, metadata: dict) -> int:
    cur.execute(
        """INSERT INTO preclin.evidence_source_release
             (source_name, source_version, source_url, content_sha256, metadata)
           VALUES (%s,%s,%s,%s,%s)
           ON CONFLICT (source_name, source_version, content_sha256) DO UPDATE SET metadata = EXCLUDED.metadata
           RETURNING source_release_id""",
        (name, version, url, sha, Json(metadata)))
    return cur.fetchone()[0]


def record_method(cur, method_id: str, name: str, description: str, inputs: list[str], parameters: dict) -> str:
    """Record (or refresh) a method, id name@version, in preclin.analysis_method; returns the id."""
    cur.execute("""INSERT INTO preclin.analysis_method
                     (method_id, name, version, description, inputs, parameters, code_commit)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (method_id) DO UPDATE SET description = EXCLUDED.description,
                     inputs = EXCLUDED.inputs, parameters = EXCLUDED.parameters,
                     code_commit = EXCLUDED.code_commit, recorded_at = now()""",
                (method_id, name, method_id.split("@")[1], description, inputs, Json(parameters), git_commit()))
    return method_id


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
    # Server tools (web search, web fetch) the model may call; a task with tools runs direct calls
    # only, resumes paused turns up to MAX_CONTINUATIONS times, and records every URL it retrieved.
    tools: list[dict[str, Any]] | None = None

    def request_params(self, payload: dict[str, Any]) -> dict[str, Any]:
        extra = {"tools": self.tools} if self.tools else {}
        return dict(**extra,
            model=self.model,
            max_tokens=self.max_tokens,
            system=[{"type": "text", "text": self.system, "cache_control": {"type": "ephemeral"}}],
            output_config={"effort": self.effort,
                           "format": {"type": "json_schema", "schema": self.schema}},
            messages=[{"role": "user", "content": self.render(payload)}],
        )


def _reusable(cur, task: Task, items: dict[str, dict[str, Any]], reuse_by: str) -> dict[str, tuple]:
    """subject_key -> (raw_response, parsed_output, provider_request_id, usage,
    llm_decision_id, model_parameters) of validated decisions from earlier runs
    of this task and prompt version: with reuse_by='input' the latest one per
    subject whose input hash equals the current payload's hash; with
    reuse_by='subject' the latest one per subject whatever its input. A decision
    that fails the task's validation against today's data is not reused."""
    keys = list(items)
    hashes = [sha256_text(canonical_json(items[k])) for k in keys]
    cur.execute(
        """
        SELECT DISTINCT ON (d.subject_key) d.subject_key, d.raw_response, d.parsed_output,
               d.provider_request_id, d.usage, d.llm_decision_id, d.model_parameters
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
    reused = {}
    for key, *row in cur.fetchall():
        try:
            if task.validate:
                task.validate(items[key], row[1])
        except Exception:  # valid when decided, not against today's data: decide again
            continue
        reused[key] = tuple(row)
    return reused


def _row(run_id: uuid.UUID, task: Task, key: str, payload: dict[str, Any], raw: str,
         parsed: dict[str, Any] | None, request_id: str, usage: dict[str, Any],
         error: str | None = None, prior_id: int | None = None, params: dict[str, Any] | None = None) -> tuple:
    """One llm_decision row; prior_id and params are the earlier decision a reused
    one copies and the model parameters it was made with."""
    canonical = parsed if parsed is not None else {"error": error}
    return (str(run_id), task.name, task.subject_type, key,
            sha256_text(canonical_json(payload)), raw, Json(canonical),
            sha256_text(raw), Json(canonical), sha256_text(canonical_json(canonical)),
            prior_id, "unchanged" if prior_id else "not_compared", Json(payload), request_id,
            Json(params or {"model": task.model, "effort": task.effort, "max_tokens": task.max_tokens}),
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


def _store(rows: list[tuple]) -> None:
    """Insert at most 2,000 decision rows (one transaction) on a fresh connection,
    replaying them while the database cannot be reached."""
    for attempt in range(CONNECT_ATTEMPTS):
        conn = connect()
        try:
            _insert(conn, rows)
            return
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            if attempt == CONNECT_ATTEMPTS - 1:
                raise
            time.sleep(10 * (attempt + 1))
        finally:
            conn.close()


def run(task: Task, items: dict[str, dict[str, Any]], *, reuse_by: str = "input") -> uuid.UUID:
    """Decide every item (subject_key -> payload). Returns the run id; the
    run's decisions cover every key, reused or new. reuse_by='subject' keeps
    earlier decisions when only incidental payload details (e.g. the order of
    context rows) changed. A run that stops on an error is marked failed."""
    api = anthropic.Anthropic(max_retries=8)
    run_id = uuid.uuid4()
    with connect() as conn, conn.cursor() as cur:
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
    status = "failed"
    try:
        with connect() as conn, conn.cursor() as cur:
            reused = _reusable(cur, task, items, reuse_by)
            _insert(conn, [_row(run_id, task, key, items[key], raw, parsed, request_id, usage,
                                prior_id=decision_id, params=params)
                           for key, (raw, parsed, request_id, usage, decision_id, params) in reused.items()])
        todo = [k for k in items if k not in reused]
        print(f"[{task.name}] run={run_id} items={len(items)} reused={len(reused)} new={len(todo)}", flush=True)
        if len(todo) <= DIRECT_MAX or task.tools:
            _run_concurrent(api, run_id, task, items, todo)
        else:
            _run_batches(api, run_id, task, items, todo)
        status = "completed"
    finally:
        with connect() as conn, conn.cursor() as cur:
            cur.execute("UPDATE pv_evidence.llm_decision_run SET status=%s, completed_at=%s "
                        "WHERE decision_run_id=%s", (status, datetime.now(timezone.utc), str(run_id)))
    return run_id


MAX_CONTINUATIONS = 4  # resumptions of a turn the server paused while running its tools


def latest_decisions(task: str, prompt_version: str, heldout: bool = False) -> pd.DataFrame:
    """The latest validated decision of each subject for a task version: key, llm_decision_id, parsed_output.
    heldout selects the subjects suffixed |heldout instead, with the suffix kept."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT ON (d.subject_key) d.subject_key, d.llm_decision_id, d.parsed_output
            FROM pv_evidence.llm_decision d JOIN pv_evidence.llm_decision_run r USING (decision_run_id)
            WHERE d.task = %s AND r.prompt_version = %s AND d.validation_status = 'validated'
              AND (d.subject_key LIKE '%%|heldout') = %s
            ORDER BY d.subject_key, d.created_at DESC""", (task, prompt_version, heldout))
        return pd.DataFrame(cur.fetchall(), columns=["key", "llm_decision_id", "parsed_output"])


def retrieved_urls(content) -> list[str]:
    """URLs that web search returned or web fetch read in a response, in order, without repeats."""
    urls = []
    for b in content:
        if b.type == "web_search_tool_result" and isinstance(b.content, list):
            urls += [r.url for r in b.content if getattr(r, "url", None)]
        elif b.type == "web_fetch_tool_result" and getattr(b.content, "url", None):
            urls.append(b.content.url)
    return list(dict.fromkeys(urls))


def norm_url(u: str) -> str:
    """A URL compared without scheme, www, fragment, trailing slash or case."""
    u = re.sub(r"^https?://(www\.)?", "", u.strip().lower())
    return u.split("#")[0].rstrip("/")


def _complete(api, task: Task, payload: dict[str, Any]):
    """One decision: the final message, every content block of the turn, and summed usage. A turn
    the server paused (stop_reason pause_turn) is resumed by sending it back unchanged."""
    params = task.request_params(payload)
    content, usage = [], {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
                          "web_search_requests": 0, "web_fetch_requests": 0}
    for _ in range(MAX_CONTINUATIONS + 1):
        with api.messages.stream(**params) as stream:  # streamed: no cap on max_tokens
            msg = stream.get_final_message()
        content += msg.content
        usage["input_tokens"] += msg.usage.input_tokens
        usage["output_tokens"] += msg.usage.output_tokens
        usage["cache_read_input_tokens"] += msg.usage.cache_read_input_tokens or 0
        server = getattr(msg.usage, "server_tool_use", None)
        if server:
            usage["web_search_requests"] += server.web_search_requests or 0
            usage["web_fetch_requests"] += getattr(server, "web_fetch_requests", 0) or 0
        if msg.stop_reason != "pause_turn":
            break
        params = {**params, "messages": [*params["messages"][:1], {"role": "assistant", "content": content}]}
    return msg, content, usage


def _parse(task: Task, payload: dict[str, Any], msg, content=None, usage=None
           ) -> tuple[str, dict | None, str | None, dict]:
    """(raw text, parsed output, error, usage) for one decision. The answer is the last text block;
    for a task with tools, parsed output also carries retrieved_urls, the URLs the turn retrieved."""
    content = msg.content if content is None else content
    usage = usage or {"input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens,
                      "cache_read_input_tokens": msg.usage.cache_read_input_tokens or 0}
    raw = next((b.text for b in reversed(content) if b.type == "text"), "")
    if msg.stop_reason in ("refusal", "max_tokens", "pause_turn"):
        return raw, None, msg.stop_reason, usage
    try:
        parsed = json.loads(raw)
        if task.tools:
            parsed["retrieved_urls"] = retrieved_urls(content)
        if task.validate:
            task.validate(payload, parsed)
        return raw, parsed, None, usage
    except Exception as exc:  # invalid JSON or failed semantic check
        return raw, None, f"{type(exc).__name__}: {exc}", usage


def _run_concurrent(api, run_id: uuid.UUID, task: Task, items: dict[str, dict[str, Any]], todo: list[str]) -> None:
    def call(key):
        for attempt in range(STREAM_ATTEMPTS):
            try:
                msg, content, usage = _complete(api, task, items[key])
                return key, msg.id, *_parse(task, items[key], msg, content, usage)
            except httpx2.TransportError as exc:
                if attempt == STREAM_ATTEMPTS - 1:
                    return key, "", "", None, f"{type(exc).__name__}: {exc}", {}
            except anthropic.APIError as exc:
                return key, "", "", None, f"{type(exc).__name__}: {exc}", {}

    n_ok = n_bad = n_api = 0
    pending = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for i, fut in enumerate(as_completed([pool.submit(call, k) for k in todo]), 1):
            key, request_id, raw, parsed, error, usage = fut.result()
            pending.append(_row(run_id, task, key, items[key], raw, parsed, request_id, usage, error))
            n_bad += error is not None
            n_ok += error is None
            n_api += not request_id  # no message came back
            if i >= 100 and n_api > API_FAILURE_LIMIT * i:  # a failing API, not failing items: stop, decide later
                pool.shutdown(wait=False, cancel_futures=True)
                raise RuntimeError(f"[{task.name}] {n_api} of {i} calls failed at the API; last: {error}")
            if i % 25 == 0 or i == len(todo):  # short transactions: FK migrations on llm_decision need gaps
                _store(pending)
                pending = []
            if i % 500 == 0 or i == len(todo):
                print(f"[{task.name}] {i}/{len(todo)} validated={n_ok} invalid={n_bad}", flush=True)


def _api(call, *args, **kwargs):
    """A batch API call, retried through connection failures the SDK's own retries do not outlast."""
    for attempt in range(API_ATTEMPTS):
        try:
            return call(*args, **kwargs)
        except (anthropic.APIConnectionError, httpx2.TransportError):
            if attempt == API_ATTEMPTS - 1:
                raise
            time.sleep(30 * (attempt + 1))


def _manifest_path(task: Task) -> str:
    return os.path.join(BATCH_MANIFESTS, f"{task.name}-{task.prompt_version}-{task.schema_version}.json")


def _read_manifest(task: Task) -> dict[str, dict[str, list[str]]]:
    path = _manifest_path(task)
    return json.load(open(path)) if os.path.exists(path) else {}


def _write_manifest(task: Task, manifest: dict[str, dict[str, list[str]]]) -> None:
    os.makedirs(BATCH_MANIFESTS, exist_ok=True)
    tmp = _manifest_path(task) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(manifest, f)
    os.replace(tmp, _manifest_path(task))


def _run_batches(api, run_id: uuid.UUID, task: Task, items: dict[str, dict[str, Any]], todo: list[str]) -> None:
    """Submit todo in batches and store each batch's decisions as it ends. Batches an earlier run of
    the task submitted for keys still in todo with the same input are collected, not resubmitted."""
    manifest = _read_manifest(task)
    shas = {k: sha256_text(canonical_json(items[k])) for k in todo}
    custom_ids, pending = {}, []
    for batch_id, cids in manifest.items():
        if all(shas.get(key) == sha for key, sha in cids.values()):
            custom_ids.update({(batch_id, cid): key for cid, (key, _) in cids.items()})
            pending.append(batch_id)
    resumed = set(custom_ids.values())
    if pending:
        print(f"[{task.name}] collecting {len(pending)} batches an earlier run submitted ({len(resumed)} requests)",
              flush=True)
    rest = [k for k in todo if k not in resumed]
    for start in range(0, len(rest), BATCH_SIZE):
        chunk = rest[start:start + BATCH_SIZE]
        requests = [Request(custom_id=f"r{start + i}",
                            params=MessageCreateParamsNonStreaming(**task.request_params(items[key])))
                    for i, key in enumerate(chunk)]
        batch = _api(api.messages.batches.create, requests=requests)
        manifest[batch.id] = {f"r{start + i}": [key, shas[key]] for i, key in enumerate(chunk)}
        _write_manifest(task, manifest)
        custom_ids.update({(batch.id, f"r{start + i}"): key for i, key in enumerate(chunk)})
        pending.append(batch.id)
        print(f"[{task.name}] submitted batch {batch.id} ({len(chunk)} requests)", flush=True)

    while pending:
        time.sleep(POLL_SECONDS)
        ended = [b for b in pending if _api(api.messages.batches.retrieve, b).processing_status == "ended"]
        for batch_id in ended:
            rows, n_ok, n_bad = [], 0, 0
            for result in _api(lambda b: list(api.messages.batches.results(b)), batch_id):
                key = custom_ids[(batch_id, result.custom_id)]
                raw, parsed, error, usage = "", None, f"batch_{result.result.type}", {}
                if result.result.type == "succeeded":
                    raw, parsed, error, usage = _parse(task, items[key], result.result.message)
                rows.append(_row(run_id, task, key, items[key], raw, parsed,
                                 f"{batch_id}/{result.custom_id}", usage, error))
                n_bad += error is not None
                n_ok += error is None
            _store(rows)
            pending.remove(batch_id)
            manifest.pop(batch_id, None)
            _write_manifest(task, manifest)
            print(f"[{task.name}] batch {batch_id}: validated={n_ok} invalid={n_bad}", flush=True)


def decisions(run_id: uuid.UUID) -> list[tuple[str, int, dict[str, Any]]]:
    """(subject_key, llm_decision_id, parsed_output) for every validated decision of a run."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT subject_key, llm_decision_id, parsed_output FROM pv_evidence.llm_decision "
                    "WHERE decision_run_id = %s AND validation_status = 'validated' ORDER BY subject_key",
                    (str(run_id),))
        return cur.fetchall()
