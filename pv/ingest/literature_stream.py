"""Page-streamed Europe PMC retrieval shared by the active literature policy."""
from __future__ import annotations

import json
import urllib.parse
import uuid
from datetime import datetime
from typing import Any

from psycopg2.extras import Json

from pv.ingest.target_phenotype_literature import (
    API_URL,
    canonical_json,
    ensure_record_version,
    fetch,
    sha256,
    store_result_batch,
)


REQUEST_PARAMETERS = {
    "format": "json",
    "resultType": "core",
    "sort": "CITED desc",
    "synonym": False,
}


def count_query(query: str) -> int:
    """Return the provider hit count without inventorying the result set."""
    params = {
        "query": query,
        "format": "json",
        "resultType": "core",
        "pageSize": 1,
        "cursorMark": "*",
        "sort": "CITED desc",
        "synonym": "false",
    }
    _raw, payload = fetch(API_URL + "?" + urllib.parse.urlencode(params))
    return int(payload["hitCount"])


def _insert_query(
    conn: Any,
    run_id: uuid.UUID,
    query_spec: dict[str, str],
    target_id: Any | None,
    phenotype_id: Any | None,
    asset_id: Any | None,
    context_roles: dict[int, str],
) -> int:
    empty_manifest: list[dict[str, Any]] = []
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO pv_source.retrieval_query
                 (acquisition_run_id,query_kind,query_key,query_text,
                  request_parameters,expected_total,returned_total,
                  result_manifest,manifest_sha256,stream_status,next_cursor)
               VALUES (%s,%s,%s,%s,%s,NULL,0,%s,%s,'running','*')
               RETURNING retrieval_query_id""",
            (
                str(run_id), query_spec["query_kind"], query_spec["query_key"],
                query_spec["query"], Json(REQUEST_PARAMETERS),
                Json(empty_manifest), sha256(canonical_json(empty_manifest)),
            ),
        )
        query_id = cur.fetchone()[0]
        subjects = [
            (target_id, "target"),
            (phenotype_id, "phenotype"),
            (asset_id, "asset"),
        ]
        for entity_id, role in subjects:
            if entity_id is not None:
                cur.execute(
                    """INSERT INTO pv_source.retrieval_query_subject
                         (retrieval_query_id,entity_id,subject_role)
                       VALUES (%s,%s,%s)""",
                    (query_id, str(entity_id), role),
                )
        for context_id, role in sorted(context_roles.items()):
            cur.execute(
                """INSERT INTO pv_source.retrieval_query_target_context
                     (retrieval_query_id,asset_target_context_assertion_id,use_role)
                   VALUES (%s,%s,%s)""",
                (query_id, context_id, role),
            )
    conn.commit()
    return query_id


def stream_query(
    conn: Any,
    release_id: int,
    run_id: uuid.UUID,
    query_spec: dict[str, str],
    retrieved_at: datetime,
    *,
    target_id: Any | None = None,
    phenotype_id: Any | None = None,
    asset_id: Any | None = None,
    context_roles: dict[int, str] | None = None,
    limit: int = 0,
    page_size: int = 1000,
) -> dict[str, int | str]:
    """Fetch, archive, project, and commit one provider page at a time.

    A debug limit intentionally produces ``truncated`` rather than ``completed``
    state. Active-corpus views therefore cannot mistake a partial validation run
    for a complete inventory.
    """
    if limit < 0:
        raise ValueError("limit must be nonnegative")
    if not 1 <= page_size <= 1000:
        raise ValueError("page_size must be between 1 and 1000")
    context_roles = context_roles or {}
    query_id = _insert_query(
        conn, run_id, query_spec, target_id, phenotype_id, asset_id, context_roles
    )
    cursor = "*"
    page_index = 0
    returned = selected = stored = reused = 0
    expected: int | None = None
    page_manifest: list[dict[str, Any]] = []
    seen_provider_ids: set[tuple[str, str]] = set()
    query_hash = sha256(query_spec["query"].encode())[:20]

    try:
        while True:
            remaining = limit - selected if limit else page_size
            request_page_size = min(page_size, remaining) if limit else page_size
            if request_page_size <= 0:
                break
            params = {
                "query": query_spec["query"],
                "format": "json",
                "resultType": "core",
                "pageSize": request_page_size,
                "cursorMark": cursor,
                "sort": "CITED desc",
                "synonym": "false",
            }
            url = API_URL + "?" + urllib.parse.urlencode(params)
            raw, payload = fetch(url)
            hit_count = int(payload["hitCount"])
            if expected is None:
                expected = hit_count
            elif hit_count != expected:
                raise RuntimeError("Europe PMC hitCount changed during streamed pagination")
            page_results = (payload.get("resultList") or {}).get("result") or []
            output_cursor = payload.get("nextCursorMark")
            ranked_results: list[dict[str, Any]] = []
            for result in page_results:
                provider_key = (str(result.get("source")), str(result.get("id")))
                if provider_key in seen_provider_ids:
                    raise RuntimeError(f"Europe PMC repeated result {provider_key}")
                seen_provider_ids.add(provider_key)
                item = dict(result)
                item["_provider_rank"] = returned
                returned += 1
                ranked_results.append(item)

            with conn.cursor() as cur:
                native_id = f"query:{query_hash}:page:{page_index}"
                _record_id, page_version_id, _was_reused = ensure_record_version(
                    cur, release_id, run_id, native_id, "literature_search_page",
                    raw, payload, url, retrieved_at,
                )
                cur.execute(
                    """INSERT INTO pv_source.retrieval_query_page
                         (retrieval_query_id,page_index,source_record_version_id,
                          input_cursor,output_cursor,result_count)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (query_id, page_index, page_version_id, cursor, output_cursor,
                     len(ranked_results)),
                )
            conn.commit()

            for start in range(0, len(ranked_results), 200):
                with conn.cursor() as cur:
                    batch_stored, batch_reused = store_result_batch(
                        cur, release_id, run_id, query_id, target_id, phenotype_id,
                        asset_id, query_spec["query_kind"],
                        ranked_results[start:start + 200], retrieved_at,
                    )
                stored += batch_stored
                reused += batch_reused
                selected += len(ranked_results[start:start + 200])
                conn.commit()

            page_manifest.append({
                "page_index": page_index,
                "input_cursor": cursor,
                "output_cursor": output_cursor,
                "result_start": returned - len(ranked_results),
                "result_count": len(ranked_results),
                "payload_sha256": sha256(raw),
            })
            has_more = bool(output_cursor and ranked_results and returned < hit_count)
            truncated = bool(limit and selected >= limit and returned < hit_count)
            next_cursor = output_cursor if has_more and not truncated else None
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE pv_source.retrieval_query
                       SET expected_total=%s,returned_total=%s,result_manifest=%s,
                           manifest_sha256=%s,next_cursor=%s,pages_committed=%s,
                           results_committed=%s
                       WHERE retrieval_query_id=%s""",
                    (
                        hit_count, returned, Json(page_manifest),
                        sha256(canonical_json(page_manifest)), next_cursor,
                        page_index + 1, selected, query_id,
                    ),
                )
            conn.commit()
            if truncated or not has_more:
                break
            if output_cursor == cursor:
                raise RuntimeError("Europe PMC cursor did not advance")
            cursor = output_cursor
            page_index += 1

        if expected is None:
            raise RuntimeError("Europe PMC returned no inventory metadata")
        final_status = "truncated" if limit and returned < expected else "completed"
        if final_status == "completed" and returned != expected:
            raise RuntimeError(
                f"Europe PMC inventory mismatch: expected={expected} received={returned}"
            )
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE pv_source.retrieval_query
                   SET stream_status=%s,next_cursor=NULL,stream_completed_at=now()
                   WHERE retrieval_query_id=%s""",
                (final_status, query_id),
            )
        conn.commit()
        return {
            "query_id": query_id,
            "status": final_status,
            "discovered": expected,
            "returned": returned,
            "selected": selected,
            "stored": stored,
            "reused": reused,
            "pages": len(page_manifest),
        }
    except BaseException:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE pv_source.retrieval_query
                   SET stream_status='failed',next_cursor=%s,stream_completed_at=now()
                   WHERE retrieval_query_id=%s""",
                (cursor, query_id),
            )
        conn.commit()
        raise
