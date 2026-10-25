"""Enrich missing pilot abstracts from archived PubMed XML batches."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json, execute_values

from pv.ingest.target_phenotype_literature import database_connection, writable_connection


SOURCE_ID = "pubmed"
ADAPTER = "pv.ingest.pubmed_abstracts"
ADAPTER_VERSION = "1.1.0"
USER_AGENT = "predictive-validity-pubmed-abstracts/1.0"


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_commit() -> str | None:
    result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", value) else None


def text(element: ET.Element | None) -> str | None:
    if element is None:
        return None
    value = " ".join("".join(element.itertext()).split())
    return value or None


def parse_articles(raw: bytes) -> dict[str, dict[str, str | None]]:
    root = ET.fromstring(raw)
    articles = {}
    for article in root.findall(".//PubmedArticle"):
        pmid = text(article.find(".//MedlineCitation/PMID"))
        if not pmid:
            continue
        parts = []
        for part in article.findall(".//Article/Abstract/AbstractText"):
            value = text(part)
            if not value:
                continue
            label = part.attrib.get("Label") or part.attrib.get("NlmCategory")
            parts.append(f"{label}: {value}" if label and not value.startswith(label + ":") else value)
        articles[pmid] = {
            "title": text(article.find(".//Article/ArticleTitle")),
            "abstract": "\n".join(parts) or None,
        }
    return articles


def fetch(pmids: list[str]) -> tuple[bytes, str]:
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml", "rettype": "abstract"}
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        raw = response.read()
    return raw, url


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    conn = database_connection()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT w.scholarly_work_id,i.identifier
               FROM pv_source.scholarly_work w
               JOIN pv_source.scholarly_work_identifier i USING(scholarly_work_id)
               WHERE i.namespace='PMID'
                 AND w.abstract_status='retrieval_pending'
                 AND (w.abstract_text IS NULL OR btrim(w.abstract_text)='')
               ORDER BY w.scholarly_work_id LIMIT %s""", (args.limit,),
        )
        candidates = cur.fetchall()
    print(f"missing_with_pmid={len(candidates)}")
    if not candidates:
        conn.close()
        return
    batches = [candidates[index:index + 200] for index in range(0, len(candidates), 200)]
    fetched = []
    for batch in batches:
        pmids = [row[1] for row in batch]
        raw, url = fetch(pmids)
        articles = parse_articles(raw)
        unexpected = set(articles) - set(pmids)
        if unexpected:
            raise RuntimeError(f"PubMed returned unexpected PMIDs: {sorted(unexpected)[:5]}")
        fetched.append((batch, raw, url, articles))
    if not args.commit:
        print(f"dry_run_batches={len(fetched)} abstracts={sum(bool(a.get('abstract')) for *_, rows in fetched for a in rows.values())}")
        conn.close()
        return

    conn = writable_connection(conn)
    retrieved_at = datetime.now(timezone.utc)
    run_id = uuid.uuid4()
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO pv_source.source_system
                 (source_system_id,provider,domain,base_url,terms_url,attribution)
               VALUES ('pubmed','NCBI','literature','https://pubmed.ncbi.nlm.nih.gov/',
                       'https://www.ncbi.nlm.nih.gov/home/about/policies/','PubMed')
               ON CONFLICT DO NOTHING"""
        )
        cur.execute(
            """INSERT INTO pv_source.source_release
                 (source_system_id,release_label,retrieved_at,metadata)
               VALUES ('pubmed',%s,%s,%s) RETURNING source_release_id""",
            (f"efetch-snapshot:{retrieved_at.isoformat()}", retrieved_at,
             Json({"snapshot_kind": "efetch_abstract"})),
        )
        release_id = cur.fetchone()[0]
        cur.execute(
            """INSERT INTO pv_source.acquisition_run
                 (acquisition_run_id,source_release_id,adapter,adapter_version,git_commit,
                  parameters,status,started_at,discovered_count,selected_count)
               VALUES (%s,%s,%s,%s,%s,%s,'running',%s,%s,%s)""",
            (str(run_id), release_id, ADAPTER, ADAPTER_VERSION, git_commit(),
             Json({"missing_abstracts_with_pmid": len(candidates), "batch_size": 200}),
             retrieved_at, len(candidates), len(candidates)),
        )
    conn.commit()
    stored = reused = enriched = 0
    try:
        for batch_index, (batch, raw, url, articles) in enumerate(fetched):
            conn = writable_connection(conn)
            pmids = [row[1] for row in batch]
            content_hash = sha256(raw)
            native_id = "efetch:" + hashlib.sha256(",".join(pmids).encode()).hexdigest()[:24]
            manifest = [{"pmid": pmid} for pmid in pmids]
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO pv_source.retrieval_query
                         (acquisition_run_id,query_kind,query_key,query_text,request_parameters,
                          expected_total,returned_total,result_manifest,manifest_sha256)
                       VALUES (%s,'pubmed_abstract_batch',%s,%s,%s,%s,%s,%s,%s)
                       RETURNING retrieval_query_id""",
                    (str(run_id), f"batch:{batch_index}", ",".join(pmids), Json({"url": url}),
                     len(pmids), len(articles), Json(manifest), sha256(json.dumps(manifest,sort_keys=True,separators=(",",":" )).encode())),
                )
                query_id = cur.fetchone()[0]
                cur.execute(
                    """INSERT INTO pv_source.source_record(source_system_id,native_record_id,record_type)
                       VALUES ('pubmed',%s,'pubmed_xml_batch') ON CONFLICT (source_system_id,native_record_id)
                       DO UPDATE SET record_type=EXCLUDED.record_type RETURNING source_record_id""", (native_id,),
                )
                record_id = cur.fetchone()[0]
                cur.execute(
                    """SELECT source_record_version_id FROM pv_source.source_record_version
                       WHERE source_record_id=%s AND content_sha256=%s""", (record_id, content_hash),
                )
                existing = cur.fetchone()
                if existing:
                    version_id = existing[0]
                    cur.execute("UPDATE pv_source.source_record_version SET last_seen_at=%s WHERE source_record_version_id=%s",
                                (retrieved_at, version_id))
                    reused += 1
                else:
                    cur.execute(
                        """INSERT INTO pv_source.source_record_version
                             (source_record_id,source_release_id,acquisition_run_id,source_url,media_type,
                              content_sha256,byte_size,raw_payload,raw_payload_text,retrieved_at,last_seen_at)
                           VALUES (%s,%s,%s,%s,'application/xml',%s,%s,%s,%s,%s,%s)
                           RETURNING source_record_version_id""",
                        (record_id, release_id, str(run_id), url, content_hash, len(raw),
                         Json({"pmids": pmids, "returned_pmids": sorted(articles)}),
                         raw.decode(), retrieved_at, retrieved_at),
                    )
                    version_id = cur.fetchone()[0]
                    stored += 1
                cur.execute(
                    """INSERT INTO pv_source.retrieval_disposition
                         (retrieval_query_id,source_record_id,source_record_version_id,result_ordinal,disposition)
                       VALUES (%s,%s,%s,0,%s)""",
                    (query_id, record_id, version_id, "selected_reused" if existing else "selected_stored"),
                )
                abstract_rows = []
                absent_work_ids = []
                work_record_rows = []
                for work_id, pmid in batch:
                    article = articles.get(pmid) or {}
                    abstract = article.get("abstract")
                    if abstract:
                        abstract_rows.append((work_id, abstract, article.get("title")))
                    else:
                        absent_work_ids.append(work_id)
                    work_record_rows.append((work_id, version_id, "abstract_metadata"))
                if abstract_rows:
                    execute_values(
                        cur,
                        """UPDATE pv_source.scholarly_work AS w
                           SET abstract_text=v.abstract_text,abstract_status='present',
                               title=COALESCE(w.title,v.title),updated_at=now()
                           FROM (VALUES %s) AS v(scholarly_work_id,abstract_text,title)
                           WHERE w.scholarly_work_id=v.scholarly_work_id""",
                        abstract_rows,
                    )
                    enriched += len(abstract_rows)
                if absent_work_ids:
                    cur.execute(
                        """UPDATE pv_source.scholarly_work
                           SET abstract_status='not_provided_by_retrieved_sources',updated_at=now()
                           WHERE scholarly_work_id=ANY(%s)""",
                        (absent_work_ids,),
                    )
                execute_values(
                    cur,
                    """INSERT INTO pv_source.scholarly_work_record
                         (scholarly_work_id,source_record_version_id,relationship)
                       VALUES %s ON CONFLICT DO NOTHING""",
                    work_record_rows,
                )
            conn.commit()
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE pv_source.acquisition_run SET status='completed',completed_at=now(),
                     stored_count=%s,reused_count=%s WHERE acquisition_run_id=%s""",
                (stored, reused, str(run_id)),
            )
        conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except psycopg2.Error:
            conn = database_connection()
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE pv_source.acquisition_run SET status='failed',completed_at=now(),failure_count=1,
                     error_summary=%s WHERE acquisition_run_id=%s""",
                (Json([{"error": f"{type(exc).__name__}: {exc}"[:1000]}]), str(run_id)),
            )
        conn.commit()
        raise
    finally:
        conn.close()
    print(f"run={run_id} batches_stored={stored} batches_reused={reused} abstracts_enriched={enriched}")


if __name__ == "__main__":
    main()
