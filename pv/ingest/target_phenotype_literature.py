"""Discover and ingest source-linked target-to-phenotype literature candidates.

Search matches remain unreviewed candidates. This command does not infer a
target-phenotype assertion and does not call an LLM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json, execute_values

from pv.ingest.search_aliases import target_search_aliases


API_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
SOURCE_ID = "europe_pmc"
ADAPTER = "pv.ingest.target_phenotype_literature"
ADAPTER_VERSION = "1.0.0"
USER_AGENT = "predictive-validity-target-phenotype-literature/1.0"


def database_connection() -> Any:
    return psycopg2.connect(
        os.environ["DATABASE_URL"], keepalives=1, keepalives_idle=30,
        keepalives_interval=10, keepalives_count=5,
    )


def writable_connection(conn: Any) -> Any:
    """Reconnect after a long network-only discovery phase if Neon went idle."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return conn
    except psycopg2.Error:
        try:
            conn.close()
        except psycopg2.Error:
            pass
        return database_connection()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", value) else None


def fetch(url: str) -> tuple[bytes, dict[str, Any]]:
    for attempt in range(5):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = response.read()
            return raw, json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 4:
                raise
            time.sleep(min(2**attempt, 30))
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise
            time.sleep(min(2**attempt, 30))
    raise AssertionError("unreachable")


def escape_phrase(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def field_term(value: str) -> str:
    escaped = escape_phrase(value)
    # Hyphens are query syntax in Europe PMC. Quote research codes and other
    # hyphenated aliases so values such as MCI-186 and NSC-12 are treated as
    # literal phrases rather than parsed expressions.
    if re.fullmatch(r"[A-Za-z0-9_]+", value):
        return f"TITLE_ABS:{escaped}"
    return f'TITLE_ABS:"{escaped}"'


def target_clause(aliases: list[str]) -> str:
    return "(" + " OR ".join(field_term(alias) for alias in aliases) + ")"


def build_queries(aliases: list[str], phenotype_name: str) -> list[dict[str, str]]:
    target = target_clause(aliases)
    phenotype_markers = (
        "(TITLE_ABS:phenotype OR TITLE_ABS:disease OR TITLE_ABS:syndrome OR "
        "TITLE_ABS:disorder OR TITLE_ABS:trait OR TITLE_ABS:susceptibility OR "
        "TITLE_ABS:mutation OR TITLE_ABS:variant)"
    )
    phenotype = field_term(phenotype_name)
    return [
        {
            "query_kind": "target_wide_phenotype",
            "query_key_suffix": "target_wide_phenotype",
            "query": f"{target} AND {phenotype_markers}",
        },
        {
            "query_kind": "target_phenotype",
            "query_key_suffix": "target_phenotype",
            "query": f"{target} AND ({phenotype} OR MESH:{escape_phrase(phenotype_name)})",
        },
    ]


def discover(query: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    cursor = "*"
    rank = 0
    results: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    expected: int | None = None
    page_index = 0
    while True:
        params = {
            "query": query,
            "format": "json",
            "resultType": "core",
            "pageSize": 1000,
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
            raise RuntimeError("Europe PMC hitCount changed during pagination")
        page_results = (payload.get("resultList") or {}).get("result") or []
        output_cursor = payload.get("nextCursorMark")
        pages.append(
            {
                "page_index": page_index,
                "input_cursor": cursor,
                "output_cursor": output_cursor,
                "url": url,
                "raw": raw,
                "payload": payload,
                "result_count": len(page_results),
            }
        )
        for result in page_results:
            item = dict(result)
            item["_provider_rank"] = rank
            results.append(item)
            rank += 1
        if not output_cursor or not page_results or len(results) >= hit_count:
            break
        if output_cursor == cursor:
            raise RuntimeError("Europe PMC cursor did not advance")
        cursor = output_cursor
        page_index += 1
    if expected is None or len(results) != expected:
        raise RuntimeError(f"Europe PMC inventory mismatch: expected={expected} received={len(results)}")
    keys = [(str(item.get("source")), str(item.get("id"))) for item in results]
    if len(set(keys)) != len(keys):
        raise RuntimeError("Europe PMC returned duplicate source/id records")
    return results, pages, expected


def start_run(
    conn: Any, retrieved_at: datetime, parameters: dict[str, Any], adapter: str = ADAPTER,
    adapter_version: str = ADAPTER_VERSION,
) -> tuple[int, uuid.UUID]:
    run_id = uuid.uuid4()
    release_label = f"api-snapshot:{retrieved_at.isoformat()}"
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pv_source.source_system
              (source_system_id,provider,domain,base_url,terms_url,attribution)
            VALUES
              ('europe_pmc','EMBL-EBI','literature',
               'https://europepmc.org/',
               'https://www.ebi.ac.uk/about/terms-of-use/',
               'Europe PMC')
            ON CONFLICT (source_system_id) DO NOTHING
            """
        )
        cur.execute(
            """
            INSERT INTO pv_source.source_release
              (source_system_id,release_label,retrieved_at,metadata)
            VALUES ('europe_pmc',%s,%s,%s)
            RETURNING source_release_id
            """,
            (release_label, retrieved_at, Json({"snapshot_kind": "api_search"})),
        )
        release_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO pv_source.acquisition_run
              (acquisition_run_id,source_release_id,adapter,adapter_version,
               git_commit,parameters,status,started_at)
            VALUES (%s,%s,%s,%s,%s,%s,'running',%s)
            """,
            (
                str(run_id), release_id, adapter, adapter_version, git_commit(),
                Json(parameters), retrieved_at,
            ),
        )
    conn.commit()
    return release_id, run_id


def ensure_record_version(
    cur: Any,
    release_id: int,
    run_id: uuid.UUID,
    native_id: str,
    record_type: str,
    raw: bytes,
    payload: dict[str, Any],
    source_url: str,
    retrieved_at: datetime,
    provider_version: str | None = None,
) -> tuple[int, int, bool]:
    cur.execute(
        """
        INSERT INTO pv_source.source_record
          (source_system_id,native_record_id,record_type)
        VALUES (%s,%s,%s)
        ON CONFLICT (source_system_id,native_record_id)
        DO UPDATE SET record_type=EXCLUDED.record_type
        RETURNING source_record_id
        """,
        (SOURCE_ID, native_id, record_type),
    )
    record_id = cur.fetchone()[0]
    digest = sha256(raw)
    cur.execute(
        """SELECT source_record_version_id
           FROM pv_source.source_record_version
           WHERE source_record_id=%s AND content_sha256=%s""",
        (record_id, digest),
    )
    row = cur.fetchone()
    if row:
        version_id = row[0]
        cur.execute(
            """UPDATE pv_source.source_record_version SET last_seen_at=%s
               WHERE source_record_version_id=%s""",
            (retrieved_at, version_id),
        )
        return record_id, version_id, True
    cur.execute(
        """
        INSERT INTO pv_source.source_record_version
          (source_record_id,source_release_id,acquisition_run_id,
           provider_version,source_url,media_type,content_sha256,byte_size,
           raw_payload,raw_payload_text,retrieved_at,last_seen_at)
        VALUES (%s,%s,%s,%s,%s,'application/json',%s,%s,%s,%s,%s,%s)
        RETURNING source_record_version_id
        """,
        (
            record_id, release_id, str(run_id), provider_version, source_url,
            digest, len(raw), Json(payload), raw.decode(), retrieved_at, retrieved_at,
        ),
    )
    return record_id, cur.fetchone()[0], False


def parse_full_date(value: str | None) -> date | None:
    if not value:
        return None
    match = re.match(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})", value)
    if not match:
        return None
    return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))


def canonical_work_key(result: dict[str, Any]) -> str:
    if result.get("doi"):
        return "doi:" + str(result["doi"]).lower()
    if result.get("pmid"):
        return "pmid:" + str(result["pmid"])
    if result.get("pmcid"):
        return "pmcid:" + str(result["pmcid"]).upper()
    return f"europepmc:{result.get('source')}:{result.get('id')}"


def upsert_work(cur: Any, result: dict[str, Any], version_id: int) -> int:
    key = canonical_work_key(result)
    pub_types = result.get("pubTypeList") or {}
    if isinstance(pub_types, dict):
        pub_types = pub_types.get("pubType") or []
    if isinstance(pub_types, str):
        pub_types = [pub_types]
    cur.execute(
        """
        INSERT INTO pv_source.scholarly_work
          (canonical_key,title,abstract_text,journal_title,
           publication_date_text,first_publication_date,author_string,
           publication_types,is_open_access,is_retracted,cited_by_count,abstract_status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (canonical_key) DO UPDATE SET
          title=EXCLUDED.title,
          abstract_text=EXCLUDED.abstract_text,
          journal_title=EXCLUDED.journal_title,
          publication_date_text=EXCLUDED.publication_date_text,
          first_publication_date=EXCLUDED.first_publication_date,
          author_string=EXCLUDED.author_string,
          publication_types=EXCLUDED.publication_types,
          is_open_access=EXCLUDED.is_open_access,
          is_retracted=EXCLUDED.is_retracted,
          cited_by_count=EXCLUDED.cited_by_count,
          abstract_status=CASE WHEN EXCLUDED.abstract_status='present' THEN 'present'
                               ELSE pv_source.scholarly_work.abstract_status END,
          updated_at=now()
        RETURNING scholarly_work_id
        """,
        (
            key, result.get("title"), result.get("abstractText"),
            result.get("journalTitle"), result.get("firstPublicationDate") or result.get("journalInfo", {}).get("printPublicationDate"),
            parse_full_date(result.get("firstPublicationDate")), result.get("authorString"),
            pub_types, result.get("isOpenAccess") == "Y",
            result.get("isRetracted") == "Y", result.get("citedByCount"),
            "present" if result.get("abstractText") else "retrieval_pending",
        ),
    )
    work_id = cur.fetchone()[0]
    identifiers = [
        ("Europe PMC", f"{result.get('source')}:{result.get('id')}"),
        ("PMID", result.get("pmid")),
        ("PMCID", result.get("pmcid")),
        ("DOI", str(result.get("doi")).lower() if result.get("doi") else None),
    ]
    for namespace, identifier in identifiers:
        if not identifier:
            continue
        cur.execute(
            """
            INSERT INTO pv_source.scholarly_work_identifier
              (scholarly_work_id,namespace,identifier)
            VALUES (%s,%s,%s)
            ON CONFLICT DO NOTHING
            """,
            (work_id, namespace, identifier),
        )
    cur.execute(
        """
        INSERT INTO pv_source.scholarly_work_record
          (scholarly_work_id,source_record_version_id)
        VALUES (%s,%s)
        ON CONFLICT DO NOTHING
        """,
        (work_id, version_id),
    )
    return work_id


def source_url(result: dict[str, Any]) -> str:
    return f"https://europepmc.org/article/{result.get('source')}/{result.get('id')}"


def result_pub_types(result: dict[str, Any]) -> list[str]:
    values = result.get("pubTypeList") or {}
    if isinstance(values, dict):
        values = values.get("pubType") or []
    return [values] if isinstance(values, str) else values


def store_result_batch(
    cur: Any, release_id: int, run_id: uuid.UUID, query_id: int,
    target_id: uuid.UUID | None, phenotype_id: uuid.UUID | None,
    asset_id: uuid.UUID | None, query_kind: str,
    items: list[dict[str, Any]], retrieved_at: datetime,
) -> tuple[int, int]:
    prepared = []
    for item in items:
        result = {key: value for key, value in item.items() if key != "_provider_rank"}
        raw = canonical_json(result)
        native_id = f"{result.get('source')}:{result.get('id')}"
        prepared.append({
            "item": item, "result": result, "raw": raw, "native_id": native_id,
            "hash": sha256(raw), "work_key": canonical_work_key(result),
        })

    execute_values(
        cur,
        """INSERT INTO pv_source.source_record(source_system_id,native_record_id,record_type)
           VALUES %s ON CONFLICT (source_system_id,native_record_id)
           DO UPDATE SET record_type=EXCLUDED.record_type""",
        [(SOURCE_ID, row["native_id"], "scholarly_metadata") for row in prepared],
    )
    native_ids = [row["native_id"] for row in prepared]
    cur.execute(
        """SELECT native_record_id,source_record_id FROM pv_source.source_record
           WHERE source_system_id=%s AND native_record_id=ANY(%s)""", (SOURCE_ID, native_ids),
    )
    record_ids = dict(cur.fetchall())
    cur.execute(
        """SELECT source_record_id,content_sha256 FROM pv_source.source_record_version
           WHERE source_record_id=ANY(%s)""", (list(record_ids.values()),),
    )
    existing = set(cur.fetchall())
    version_rows = []
    for row in prepared:
        result, raw = row["result"], row["raw"]
        version_rows.append((
            record_ids[row["native_id"]], release_id, str(run_id),
            result.get("firstPublicationDate") or result.get("pubYear"), source_url(result),
            row["hash"], len(raw), Json(result), raw.decode(), retrieved_at, retrieved_at,
        ))
    returned = execute_values(
        cur,
        """INSERT INTO pv_source.source_record_version
             (source_record_id,source_release_id,acquisition_run_id,provider_version,
              source_url,media_type,content_sha256,byte_size,raw_payload,raw_payload_text,
              retrieved_at,last_seen_at)
           VALUES %s ON CONFLICT (source_record_id,content_sha256)
           DO UPDATE SET last_seen_at=EXCLUDED.last_seen_at
           RETURNING source_record_id,content_sha256,source_record_version_id""",
        version_rows,
        template="(%s,%s,%s,%s,%s,'application/json',%s,%s,%s,%s,%s,%s)",
        fetch=True,
    )
    version_ids = {(record_id, content_hash): version_id for record_id, content_hash, version_id in returned}

    work_rows_by_key: dict[str, tuple[Any, ...]] = {}
    for row in prepared:
        result = row["result"]
        work_rows_by_key[row["work_key"]] = (
            row["work_key"], result.get("title"), result.get("abstractText"),
            result.get("journalTitle"),
            result.get("firstPublicationDate") or (result.get("journalInfo") or {}).get("printPublicationDate"),
            parse_full_date(result.get("firstPublicationDate")), result.get("authorString"),
            result_pub_types(result), result.get("isOpenAccess") == "Y",
            result.get("isRetracted") == "Y", result.get("citedByCount"),
            "present" if result.get("abstractText") else "retrieval_pending",
        )
    returned_works = execute_values(
        cur,
        """INSERT INTO pv_source.scholarly_work
             (canonical_key,title,abstract_text,journal_title,publication_date_text,
              first_publication_date,author_string,publication_types,is_open_access,
              is_retracted,cited_by_count,abstract_status)
           VALUES %s ON CONFLICT (canonical_key) DO UPDATE SET
             title=EXCLUDED.title,abstract_text=EXCLUDED.abstract_text,
             journal_title=EXCLUDED.journal_title,
             publication_date_text=EXCLUDED.publication_date_text,
             first_publication_date=EXCLUDED.first_publication_date,
             author_string=EXCLUDED.author_string,publication_types=EXCLUDED.publication_types,
             is_open_access=EXCLUDED.is_open_access,is_retracted=EXCLUDED.is_retracted,
             cited_by_count=EXCLUDED.cited_by_count,
             abstract_status=CASE WHEN EXCLUDED.abstract_status='present' THEN 'present'
                                  ELSE pv_source.scholarly_work.abstract_status END,
             updated_at=now()
           RETURNING canonical_key,scholarly_work_id""",
        list(work_rows_by_key.values()), fetch=True,
    )
    work_ids = dict(returned_works)

    identifier_rows = []
    work_record_rows = []
    disposition_rows = []
    candidate_rows_by_work: dict[int, tuple[Any, ...]] = {}
    provider_rank_by_work: dict[int, int] = {}
    phenotype_value = str(phenotype_id) if query_kind in {
        "target_phenotype", "asset_indication_preclinical",
        "target_indication_preclinical", "mechanism_phenotype",
        "asset_indication_v2",
    } else None
    for row in prepared:
        result = row["result"]
        record_id = record_ids[row["native_id"]]
        version_id = version_ids[(record_id, row["hash"])]
        work_id = work_ids[row["work_key"]]
        for namespace, identifier in (
            ("Europe PMC", f"{result.get('source')}:{result.get('id')}"),
            ("PMID", result.get("pmid")), ("PMCID", result.get("pmcid")),
            ("DOI", str(result.get("doi")).lower() if result.get("doi") else None),
        ):
            if identifier:
                identifier_rows.append((work_id, namespace, identifier))
        work_record_rows.append((work_id, version_id, "bibliographic_metadata"))
        disposition_rows.append((
            query_id, record_id, version_id, row["item"]["_provider_rank"],
            "selected_reused" if (record_id, row["hash"]) in existing else "selected_stored",
        ))
        candidate_rows_by_work[work_id] = (
            work_id, str(target_id) if target_id else None,
            phenotype_value, str(asset_id) if asset_id else None, query_kind,
        )
        provider_rank_by_work[work_id] = min(
            provider_rank_by_work.get(work_id, row["item"]["_provider_rank"]),
            row["item"]["_provider_rank"],
        )
    execute_values(
        cur,
        """INSERT INTO pv_source.scholarly_work_identifier
             (scholarly_work_id,namespace,identifier) VALUES %s ON CONFLICT DO NOTHING""",
        identifier_rows,
    )
    execute_values(
        cur,
        """INSERT INTO pv_source.scholarly_work_record
             (scholarly_work_id,source_record_version_id,relationship)
           VALUES %s ON CONFLICT DO NOTHING""", work_record_rows,
    )
    execute_values(
        cur,
        """INSERT INTO pv_source.retrieval_disposition
             (retrieval_query_id,source_record_id,source_record_version_id,result_ordinal,disposition)
           VALUES %s ON CONFLICT DO NOTHING""", disposition_rows,
    )
    returned_candidates = execute_values(
        cur,
        """INSERT INTO pv_evidence.document_relation_candidate
             (scholarly_work_id,target_entity_id,phenotype_entity_id,asset_entity_id,candidate_kind)
           VALUES %s ON CONFLICT (
             scholarly_work_id,target_entity_id,phenotype_entity_id,
             mechanism_entity_id,asset_entity_id,candidate_kind
           ) DO UPDATE SET scholarly_work_id=EXCLUDED.scholarly_work_id
           RETURNING scholarly_work_id,document_relation_candidate_id""",
        list(candidate_rows_by_work.values()), fetch=True,
    )
    candidate_ids = dict(returned_candidates)
    execute_values(
        cur,
        """INSERT INTO pv_evidence.document_relation_candidate_observation
             (retrieval_query_id,document_relation_candidate_id,provider_rank)
           VALUES %s ON CONFLICT DO NOTHING""",
        [(query_id, candidate_ids[work_id], rank)
         for work_id, rank in provider_rank_by_work.items()],
    )
    stored = sum((record_ids[row["native_id"]], row["hash"]) not in existing for row in prepared)
    return stored, len(prepared) - stored


def store_query(
    conn: Any,
    release_id: int,
    run_id: uuid.UUID,
    target_id: uuid.UUID,
    phenotype_id: uuid.UUID | None,
    target_symbol: str,
    query_spec: dict[str, str],
    results: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    hit_count: int,
    limit: int,
    retrieved_at: datetime,
    asset_id: uuid.UUID | None = None,
) -> tuple[int, int, int]:
    manifest = [
        {
            "rank": item["_provider_rank"],
            "source": item.get("source"),
            "id": item.get("id"),
            "pmid": item.get("pmid"),
            "pmcid": item.get("pmcid"),
            "doi": item.get("doi"),
        }
        for item in results
    ]
    selected = results if limit == 0 else results[:limit]
    query_key = f"{target_symbol}:{query_spec['query_key_suffix']}"
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pv_source.retrieval_query
              (acquisition_run_id,query_kind,query_key,query_text,
               request_parameters,expected_total,returned_total,
               result_manifest,manifest_sha256)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING retrieval_query_id
            """,
            (
                str(run_id), query_spec["query_kind"], query_key,
                query_spec["query"],
                Json({"resultType": "core", "sort": "CITED desc", "synonym": False}),
                hit_count, len(results), Json(manifest), sha256(canonical_json(manifest)),
            ),
        )
        query_id = cur.fetchone()[0]
        if target_id is not None:
            cur.execute(
                """INSERT INTO pv_source.retrieval_query_subject
                     (retrieval_query_id,entity_id,subject_role)
                   VALUES (%s,%s,'target')""",
                (query_id, str(target_id)),
            )
        if asset_id is not None:
            cur.execute(
                """INSERT INTO pv_source.retrieval_query_subject
                     (retrieval_query_id,entity_id,subject_role)
                   VALUES (%s,%s,'asset')""", (query_id, str(asset_id)),
            )
        if query_spec["query_kind"] in {
            "target_phenotype", "asset_indication_preclinical",
            "target_indication_preclinical", "mechanism_phenotype",
        }:
            cur.execute(
                """INSERT INTO pv_source.retrieval_query_subject
                     (retrieval_query_id,entity_id,subject_role)
                   VALUES (%s,%s,'phenotype')""", (query_id, str(phenotype_id)),
            )

        for page in pages:
            query_hash = sha256(query_spec["query"].encode())[:20]
            native_id = f"query:{query_hash}:page:{page['page_index']}"
            _, page_version_id, _ = ensure_record_version(
                cur, release_id, run_id, native_id, "literature_search_page",
                page["raw"], page["payload"], page["url"], retrieved_at,
            )
            cur.execute(
                """
                INSERT INTO pv_source.retrieval_query_page
                  (retrieval_query_id,page_index,source_record_version_id,
                   input_cursor,output_cursor,result_count)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (
                    query_id, page["page_index"], page_version_id,
                    page["input_cursor"], page["output_cursor"], page["result_count"],
                ),
            )

        # The complete manifest and raw search pages are durable before the
        # potentially large canonical-work projection begins.  Small commits
        # prevent overlapping target searches from holding thousands of row
        # locks against the same DOI/PMID identities.
        conn.commit()

        stored = reused = 0
        for start in range(0, len(selected), 200):
            batch_stored, batch_reused = store_result_batch(
                cur, release_id, run_id, query_id, target_id, phenotype_id,
                asset_id, query_spec["query_kind"], selected[start:start + 200], retrieved_at,
            )
            stored += batch_stored
            reused += batch_reused
            conn.commit()
    conn.commit()
    return len(selected), stored, reused


def load_subject(
    conn: Any, symbol: str | None, phenotype_name: str, target_id_arg: str | None = None
) -> tuple[uuid.UUID, uuid.UUID, list[str], str]:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT DISTINCT target.entity_id,phenotype.entity_id,target.approved_name
               FROM pv_core.v_target_phenotype_literature_scope scoped
               JOIN pv_core.target target ON target.entity_id=scoped.target_entity_id
               JOIN pv_core.phenotype phenotype ON phenotype.entity_id=scoped.phenotype_entity_id
               WHERE scoped.policy_version='human_therapeutics_v2'
                 AND (%s::uuid IS NULL OR target.entity_id=%s::uuid)
                 AND (%s IS NULL OR target.approved_symbol=%s)
                 AND lower(phenotype.preferred_name)=lower(%s)""",
            (target_id_arg, target_id_arg, symbol, symbol, phenotype_name),
        )
        matches = cur.fetchall()
        if len(matches) != 1:
            raise SystemExit(
                f"No unique in-scope human target/phenotype pair found for "
                f"{target_id_arg or symbol}/{phenotype_name}; classify development scope first"
            )
        target_id, phenotype_id, approved_name = matches[0]
        aliases = target_search_aliases(cur, target_id, [symbol, approved_name])
    if not aliases:
        raise SystemExit(f"No unambiguous search aliases found for {target_id_arg or symbol}")
    return target_id, phenotype_id, aliases, symbol or approved_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", default="ADRB2")
    parser.add_argument("--target-id", help="stable target UUID; takes precedence over --target")
    parser.add_argument("--phenotype", default="asthma")
    parser.add_argument(
        "--limit-per-query", type=int, default=0,
        help="0 stores all matches (default); a positive cap is only for explicit debugging",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--commit", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.limit_per_query < 0:
        raise SystemExit("--limit-per-query must be nonnegative")
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    conn = database_connection()
    run_id: uuid.UUID | None = None
    try:
        target_id, phenotype_id, aliases, target_label = load_subject(
            conn, None if args.target_id else args.target, args.phenotype, args.target_id
        )
        query_specs = build_queries(aliases, args.phenotype)
        discoveries = []
        for spec in query_specs:
            results, pages, hit_count = discover(spec["query"])
            discoveries.append((spec, results, pages, hit_count))
            print(
                f"{spec['query_kind']}: hits={hit_count} pages={len(pages)} "
                f"selected={hit_count if args.limit_per_query == 0 else min(hit_count, args.limit_per_query)}"
            )
            print(f"  query={spec['query']}")
        if not args.commit:
            print("Dry run complete; Neon was not modified.")
            return
        conn = writable_connection(conn)
        retrieved_at = datetime.now(timezone.utc)
        release_id, run_id = start_run(
            conn, retrieved_at,
            {
                "target": target_label,
                "phenotype": args.phenotype,
                "aliases": aliases,
                "limit_per_query": args.limit_per_query,
            },
        )
        total_selected = total_stored = total_reused = 0
        for spec, results, pages, hit_count in discoveries:
            selected, stored, reused = store_query(
                conn, release_id, run_id, target_id, phenotype_id,
                target_label, spec, results, pages, hit_count,
                args.limit_per_query, retrieved_at,
            )
            total_selected += selected
            total_stored += stored
            total_reused += reused
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pv_source.acquisition_run
                SET status='completed',completed_at=now(),
                    discovered_count=%s,selected_count=%s,
                    stored_count=%s,reused_count=%s
                WHERE acquisition_run_id=%s
                """,
                (
                    sum(item[3] for item in discoveries), total_selected,
                    total_stored, total_reused, str(run_id),
                ),
            )
        conn.commit()
    except BaseException as exc:
        conn.rollback()
        if run_id is not None:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE pv_source.acquisition_run
                       SET status='failed',completed_at=now(),failure_count=1,error_summary=%s
                       WHERE acquisition_run_id=%s AND status='running'""",
                    (Json([{"error": f"{type(exc).__name__}: {exc}"[:1000]}]), str(run_id)),
                )
            conn.commit()
        raise
    finally:
        conn.close()
    print(
        f"Run {run_id}: selected={total_selected} stored={total_stored} "
        f"reused={total_reused}"
    )


if __name__ == "__main__":
    main()
