"""Ingest rights-reviewed Europe PMC open-access JATS representations.

The command fetches only canonical works already marked open access and having
a PMCID. It validates the article identity and an explicit supported license
before persisting bytes. GCS upload is optional; without a configured bucket,
the exact UTF-8 XML remains in the immutable Neon source record version.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import Json


SOURCE_ID = "europe_pmc"
ADAPTER = "pv.ingest.europe_pmc_fulltext"
ADAPTER_VERSION = "1.0.0"
USER_AGENT = "predictive-validity-europe-pmc-fulltext/1.0"
API_TEMPLATE = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
EUROPE_PMC_COPYRIGHT = "https://europepmc.org/Copyright"


@dataclass(frozen=True)
class RightsDecision:
    license_name: str
    terms_url: str
    rights_tier: str
    statement: str
    rationale: str


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", value) else None


def fetch(url: str) -> bytes:
    for attempt in range(5):
        request = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "application/xml"}
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = response.read()
                content_type = response.headers.get_content_type()
            if content_type not in {"application/xml", "text/xml"}:
                raise RuntimeError(f"Unexpected Europe PMC content type: {content_type}")
            return raw
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 4:
                raise
            time.sleep(min(2**attempt, 30))
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise
            time.sleep(min(2**attempt, 30))
    raise AssertionError("unreachable")


def normalized_text(element: ET.Element) -> str:
    return " ".join(" ".join(element.itertext()).split())


def parse_and_decide(raw: bytes, expected_pmcid: str) -> tuple[dict[str, Any], RightsDecision]:
    root = ET.fromstring(raw)
    pmc_ids = {
        "PMC" + (element.text or "").strip().removeprefix("PMC")
        for element in root.findall(".//article-id")
        if element.attrib.get("pub-id-type") in {"pmc", "pmcid"}
        and (element.text or "").strip()
    }
    if expected_pmcid not in pmc_ids:
        raise RuntimeError(
            f"Full text identity mismatch: expected {expected_pmcid}, found {sorted(pmc_ids)}"
        )

    license_elements = root.findall(".//license")
    statements = [normalized_text(element) for element in license_elements]
    hrefs = [
        element.attrib.get("{http://www.w3.org/1999/xlink}href")
        or element.attrib.get("href")
        for element in license_elements
    ]
    combined = " ".join(statement for statement in statements if statement)
    normalized_hrefs = [href.rstrip("/").lower() for href in hrefs if href]

    cc_match = next(
        (href for href in normalized_hrefs if "creativecommons.org/licenses/" in href),
        None,
    )
    if cc_match:
        license_path = cc_match.split("creativecommons.org/licenses/", 1)[1]
        parts = license_path.split("/")
        code = parts[0]
        version = parts[1] if len(parts) > 1 else "unspecified"
        if code not in {"by", "by-sa", "by-nc", "by-nc-sa", "by-nd", "by-nc-nd"}:
            raise RuntimeError(f"Unsupported Creative Commons license: {cc_match}")
        tier = "open_noncommercial" if "nc" in code.split("-") else "open_redistributable"
        decision = RightsDecision(
            license_name=f"CC {code.upper()} {version}",
            terms_url=cc_match + "/",
            rights_tier=tier,
            statement=combined,
            rationale=(
                f"Article JATS explicitly declares CC {code.upper()} {version}; "
                "verbatim archival is permitted for noncommercial research."
            ),
        )
    elif "public domain" in combined.casefold() and "ehp" in combined.casefold():
        decision = RightsDecision(
            license_name="Environmental Health Perspectives public-domain notice",
            terms_url=EUROPE_PMC_COPYRIGHT,
            rights_tier="open_redistributable",
            statement=combined,
            rationale=(
                "Article JATS states that EHP publication lies in the public domain; "
                "archival retains the supplied attribution notice."
            ),
        )
    else:
        raise RuntimeError("No supported explicit archival license found in article JATS")

    metadata = {
        "pmcid": expected_pmcid,
        "article_type": root.attrib.get("article-type"),
        "license_name": decision.license_name,
        "license_url": decision.terms_url,
        "license_statement": decision.statement,
        "license_statement_sha256": sha256(decision.statement.encode()),
    }
    return metadata, decision


def load_candidates(
    conn: Any, work_ids: list[int], limit: int, only_missing: bool
) -> list[tuple[int, str, str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT sw.scholarly_work_id, sw.canonical_key, swi.identifier
            FROM pv_source.scholarly_work sw
            JOIN pv_source.scholarly_work_identifier swi
              ON swi.scholarly_work_id=sw.scholarly_work_id
             AND swi.namespace='PMCID'
            WHERE sw.is_open_access=true
              AND EXISTS (
                SELECT 1 FROM pv_evidence.document_relation_candidate candidate
                WHERE candidate.scholarly_work_id=sw.scholarly_work_id
              )
              AND (%s::bigint[] = '{}'::bigint[] OR sw.scholarly_work_id=ANY(%s))
              AND (
                NOT %s OR NOT EXISTS (
                  SELECT 1 FROM pv_source.representation representation
                  WHERE representation.scholarly_work_id=sw.scholarly_work_id
                    AND representation.representation_kind='full_text_jats'
                )
              )
            ORDER BY sw.scholarly_work_id
            LIMIT %s
            """,
            (work_ids, work_ids, only_missing, limit),
        )
        return [(row[0], row[1], row[2].upper()) for row in cur.fetchall()]


def gcs_upload(
    raw: bytes, bucket: str, digest: str, rights_tier: str,
    extension: str = "xml", media_type: str = "application/xml",
) -> dict[str, Any]:
    object_name = f"{rights_tier}/europe_pmc/{digest[:2]}/{digest}.{extension}"
    uri = f"gs://{bucket}/{object_name}"
    describe = subprocess.run(
        ["gcloud", "storage", "objects", "describe", uri, "--format=json"],
        capture_output=True, text=True, check=False,
    )
    if describe.returncode != 0:
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as handle:
                handle.write(raw)
                temporary_path = handle.name
            upload = subprocess.run(
                [
                    "gcloud", "storage", "cp", "--if-generation-match=0",
                    f"--content-type={media_type}", temporary_path, uri,
                ],
                capture_output=True, text=True, check=False,
            )
            if upload.returncode != 0:
                raise RuntimeError(f"GCS upload failed for {uri}")
        finally:
            if temporary_path:
                Path(temporary_path).unlink(missing_ok=True)
        describe = subprocess.run(
            ["gcloud", "storage", "objects", "describe", uri, "--format=json"],
            capture_output=True, text=True, check=True,
        )
    payload = json.loads(describe.stdout)
    return {
        "bucket": bucket,
        "object_name": object_name,
        "generation": str(payload.get("generation") or ""),
        "crc32c": payload.get("crc32c") or payload.get("crc32cHash"),
    }


def free_pdf_url(conn: Any, work_id: int) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT v.raw_payload
               FROM pv_source.scholarly_work_record wr
               JOIN pv_source.source_record_version v USING(source_record_version_id)
               WHERE wr.scholarly_work_id=%s AND wr.relationship='bibliographic_metadata'
               ORDER BY v.retrieved_at DESC""", (work_id,),
        )
        for (payload,) in cur.fetchall():
            urls = ((payload.get("fullTextUrlList") or {}).get("fullTextUrl") or [])
            pdfs = [row for row in urls if row.get("documentStyle") == "pdf"
                    and row.get("availabilityCode") == "F" and row.get("url")]
            if pdfs:
                pdfs.sort(key=lambda row: (row.get("site") != "Europe_PMC", row.get("url")))
                return pdfs[0]["url"]
    return None


def fetch_pdf(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/pdf"})
    with urllib.request.urlopen(request, timeout=180) as response:
        raw = response.read()
    if not raw.startswith(b"%PDF-"):
        raise RuntimeError("Free full-text URL did not return a PDF")
    return raw


def store_pdf(
    conn: Any, release_id: int, run_id: uuid.UUID, work_id: int, pmcid: str,
    pdf_url: str, raw: bytes, decision: RightsDecision, retrieved_at: datetime,
    gcs: dict[str, Any],
) -> bool:
    content_hash = sha256(raw)
    native_id = f"{pmcid}:pdf:{sha256(pdf_url.encode())[:20]}"
    metadata = {
        "pmcid": pmcid, "resolved_pdf_url": pdf_url,
        "license_name": decision.license_name, "license_url": decision.terms_url,
    }
    metadata_text = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO pv_source.object_blob
                 (storage_provider,bucket,object_name,object_generation,content_sha256,
                  crc32c,byte_size,media_type,rights_tier)
               VALUES ('gcs',%s,%s,%s,%s,%s,%s,'application/pdf',%s)
               ON CONFLICT (storage_provider,bucket,object_name,content_sha256)
               DO UPDATE SET object_generation=EXCLUDED.object_generation,crc32c=EXCLUDED.crc32c
               RETURNING object_blob_id""",
            (gcs["bucket"], gcs["object_name"], gcs["generation"], content_hash,
             gcs["crc32c"], len(raw), decision.rights_tier),
        )
        object_blob_id = cur.fetchone()[0]
        cur.execute(
            """INSERT INTO pv_source.source_record(source_system_id,native_record_id,record_type)
               VALUES (%s,%s,'full_text_pdf') ON CONFLICT (source_system_id,native_record_id)
               DO UPDATE SET record_type=EXCLUDED.record_type RETURNING source_record_id""",
            (SOURCE_ID, native_id),
        )
        record_id = cur.fetchone()[0]
        cur.execute(
            """SELECT source_record_version_id FROM pv_source.source_record_version
               WHERE source_record_id=%s AND content_sha256=%s""", (record_id, content_hash),
        )
        row = cur.fetchone()
        reused = bool(row)
        if row:
            version_id = row[0]
            cur.execute(
                """UPDATE pv_source.source_record_version SET last_seen_at=%s,
                     object_blob_id=COALESCE(object_blob_id,%s)
                   WHERE source_record_version_id=%s""", (retrieved_at, object_blob_id, version_id),
            )
        else:
            cur.execute(
                """INSERT INTO pv_source.source_record_version
                     (source_record_id,source_release_id,acquisition_run_id,provider_version,
                      source_url,media_type,content_sha256,byte_size,raw_payload,raw_payload_text,
                      object_blob_id,retrieved_at,last_seen_at)
                   VALUES (%s,%s,%s,%s,%s,'application/pdf',%s,%s,%s,%s,%s,%s,%s)
                   RETURNING source_record_version_id""",
                (record_id, release_id, str(run_id), pmcid, pdf_url, content_hash, len(raw),
                 Json(metadata), metadata_text, object_blob_id, retrieved_at, retrieved_at),
            )
            version_id = cur.fetchone()[0]
        license_id = ensure_license(cur, decision, retrieved_at)
        cur.execute(
            """INSERT INTO pv_source.rights_assertion
                 (source_record_version_id,license_id,decision,intended_use,rationale)
               SELECT %s,%s,'storage_permitted','noncommercial_research',%s
               WHERE NOT EXISTS (SELECT 1 FROM pv_source.rights_assertion
                                 WHERE source_record_version_id=%s AND decision='storage_permitted')
               RETURNING rights_assertion_id""",
            (version_id, license_id, decision.rationale, version_id),
        )
        rights_row = cur.fetchone()
        if rights_row:
            rights_id = rights_row[0]
        else:
            cur.execute(
                """SELECT rights_assertion_id FROM pv_source.rights_assertion
                   WHERE source_record_version_id=%s AND decision='storage_permitted'
                   ORDER BY rights_assertion_id LIMIT 1""", (version_id,),
            )
            rights_id = cur.fetchone()[0]
        cur.execute(
            """INSERT INTO pv_source.scholarly_work_record
                 (scholarly_work_id,source_record_version_id,relationship)
               VALUES (%s,%s,'full_text_pdf') ON CONFLICT DO NOTHING""", (work_id, version_id),
        )
        cur.execute(
            """INSERT INTO pv_source.representation
                 (scholarly_work_id,source_record_version_id,representation_kind,media_type,
                  rights_assertion_id,object_blob_id)
               VALUES (%s,%s,'full_text_pdf','application/pdf',%s,%s)
               ON CONFLICT (scholarly_work_id,source_record_version_id,representation_kind)
               DO UPDATE SET rights_assertion_id=EXCLUDED.rights_assertion_id,
                             object_blob_id=EXCLUDED.object_blob_id""",
            (work_id, version_id, rights_id, object_blob_id),
        )
    conn.commit()
    return reused


def start_run(conn: Any, retrieved_at: datetime, count: int, bucket: str | None) -> tuple[int, uuid.UUID]:
    run_id = uuid.uuid4()
    release_label = f"fulltext-api-snapshot:{retrieved_at.isoformat()}"
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pv_source.source_system
              (source_system_id,provider,domain,base_url,terms_url,attribution)
            VALUES
              ('europe_pmc','EMBL-EBI','literature','https://europepmc.org/',
               'https://www.ebi.ac.uk/about/terms-of-use/','Europe PMC')
            ON CONFLICT (source_system_id) DO NOTHING
            """
        )
        cur.execute(
            """
            INSERT INTO pv_source.source_release
              (source_system_id,release_label,retrieved_at,metadata)
            VALUES (%s,%s,%s,%s)
            RETURNING source_release_id
            """,
            (SOURCE_ID, release_label, retrieved_at, Json({"snapshot_kind": "full_text_api"})),
        )
        release_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO pv_source.acquisition_run
              (acquisition_run_id,source_release_id,adapter,adapter_version,
               git_commit,parameters,status,started_at,discovered_count,selected_count)
            VALUES (%s,%s,%s,%s,%s,%s,'running',%s,%s,%s)
            """,
            (
                str(run_id), release_id, ADAPTER, ADAPTER_VERSION, git_commit(),
                Json({"candidate_count": count, "gcs_bucket_configured": bool(bucket)}),
                retrieved_at, count, count,
            ),
        )
    conn.commit()
    return release_id, run_id


def ensure_license(cur: Any, decision: RightsDecision, retrieved_at: datetime) -> int:
    cur.execute(
        """
        SELECT license_id FROM pv_source.license
        WHERE source_system_id=%s AND license_name=%s AND terms_url=%s
        ORDER BY license_id LIMIT 1
        """,
        (SOURCE_ID, decision.license_name, decision.terms_url),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        """
        INSERT INTO pv_source.license
          (source_system_id,license_name,terms_url,terms_retrieved_at,notes)
        VALUES (%s,%s,%s,%s,%s)
        RETURNING license_id
        """,
        (SOURCE_ID, decision.license_name, decision.terms_url, retrieved_at, decision.statement),
    )
    return cur.fetchone()[0]


def store_one(
    conn: Any, release_id: int, run_id: uuid.UUID, work_id: int,
    pmcid: str, raw: bytes, metadata: dict[str, Any], decision: RightsDecision,
    retrieved_at: datetime, gcs: dict[str, Any] | None,
) -> bool:
    digest = sha256(raw)
    native_id = f"{pmcid}:fullTextXML"
    url = API_TEMPLATE.format(pmcid=pmcid)
    with conn.cursor() as cur:
        object_blob_id = None
        if gcs:
            cur.execute(
                """
                INSERT INTO pv_source.object_blob
                  (storage_provider,bucket,object_name,object_generation,
                   content_sha256,crc32c,byte_size,media_type,rights_tier)
                VALUES ('gcs',%s,%s,%s,%s,%s,%s,'application/xml',%s)
                ON CONFLICT (storage_provider,bucket,object_name,content_sha256)
                DO UPDATE SET object_generation=EXCLUDED.object_generation,
                              crc32c=EXCLUDED.crc32c
                RETURNING object_blob_id
                """,
                (
                    gcs["bucket"], gcs["object_name"], gcs["generation"], digest,
                    gcs["crc32c"], len(raw), decision.rights_tier,
                ),
            )
            object_blob_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO pv_source.source_record
              (source_system_id,native_record_id,record_type)
            VALUES (%s,%s,'full_text_jats')
            ON CONFLICT (source_system_id,native_record_id)
            DO UPDATE SET record_type=EXCLUDED.record_type
            RETURNING source_record_id
            """,
            (SOURCE_ID, native_id),
        )
        record_id = cur.fetchone()[0]
        cur.execute(
            """
            SELECT source_record_version_id,object_blob_id
            FROM pv_source.source_record_version
            WHERE source_record_id=%s AND content_sha256=%s
            """,
            (record_id, digest),
        )
        row = cur.fetchone()
        reused = row is not None
        if row:
            version_id = row[0]
            cur.execute(
                """
                UPDATE pv_source.source_record_version
                SET last_seen_at=%s,
                    object_blob_id=COALESCE(object_blob_id,%s)
                WHERE source_record_version_id=%s
                """,
                (retrieved_at, object_blob_id, version_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO pv_source.source_record_version
                  (source_record_id,source_release_id,acquisition_run_id,
                   provider_version,source_url,media_type,content_sha256,byte_size,
                   raw_payload,raw_payload_text,object_blob_id,retrieved_at,last_seen_at)
                VALUES (%s,%s,%s,%s,%s,'application/xml',%s,%s,%s,%s,%s,%s,%s)
                RETURNING source_record_version_id
                """,
                (
                    record_id, release_id, str(run_id), pmcid, url, digest, len(raw),
                    Json(metadata), raw.decode("utf-8"), object_blob_id,
                    retrieved_at, retrieved_at,
                ),
            )
            version_id = cur.fetchone()[0]

        license_id = ensure_license(cur, decision, retrieved_at)
        cur.execute(
            """
            SELECT rights_assertion_id FROM pv_source.rights_assertion
            WHERE source_record_version_id=%s AND decision='storage_permitted'
            ORDER BY rights_assertion_id LIMIT 1
            """,
            (version_id,),
        )
        rights_row = cur.fetchone()
        if rights_row:
            rights_id = rights_row[0]
        else:
            cur.execute(
                """
                INSERT INTO pv_source.rights_assertion
                  (source_record_version_id,license_id,decision,intended_use,rationale)
                VALUES (%s,%s,'storage_permitted','noncommercial_research',%s)
                RETURNING rights_assertion_id
                """,
                (version_id, license_id, decision.rationale),
            )
            rights_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO pv_source.scholarly_work_record
              (scholarly_work_id,source_record_version_id,relationship)
            VALUES (%s,%s,'full_text_jats')
            ON CONFLICT DO NOTHING
            """,
            (work_id, version_id),
        )
        cur.execute(
            """
            INSERT INTO pv_source.representation
              (scholarly_work_id,source_record_version_id,representation_kind,
               media_type,rights_assertion_id,object_blob_id)
            VALUES (%s,%s,'full_text_jats','application/xml',%s,%s)
            ON CONFLICT (scholarly_work_id,source_record_version_id,representation_kind)
            DO UPDATE SET rights_assertion_id=EXCLUDED.rights_assertion_id,
                          object_blob_id=COALESCE(
                            pv_source.representation.object_blob_id,
                            EXCLUDED.object_blob_id
                          )
            """,
            (work_id, version_id, rights_id, object_blob_id),
        )
    conn.commit()
    return reused


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--work-id", type=int, action="append", default=[])
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--gcs-bucket", default=os.environ.get("PV_GCS_BUCKET"))
    parser.add_argument("--include-existing", action="store_true",
                        help="refetch works that already have a retained JATS representation")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--commit", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be positive")
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        candidates = load_candidates(conn, args.work_id, args.limit, not args.include_existing)
        if not args.commit:
            print(f"Eligible missing OA full texts: {len(candidates)}")
            print("Dry run complete; Neon and GCS were not modified.")
            return

        retrieved_at = datetime.now(timezone.utc)
        release_id, run_id = start_run(conn, retrieved_at, len(candidates), args.gcs_bucket)
        stored = reused = 0
        pdf_stored = pdf_reused = pdf_attempted = 0
        failures: list[dict[str, str]] = []
        for work_id, canonical_key, pmcid in candidates:
            try:
                raw = fetch(API_TEMPLATE.format(pmcid=pmcid))
                metadata, decision = parse_and_decide(raw, pmcid)
                gcs = (
                    gcs_upload(raw, args.gcs_bucket, sha256(raw), decision.rights_tier)
                    if args.gcs_bucket else None
                )
                was_reused = store_one(
                    conn, release_id, run_id, work_id, pmcid, raw, metadata,
                    decision, retrieved_at, gcs,
                )
                stored += int(not was_reused)
                reused += int(was_reused)
                print(
                    f"{work_id} {pmcid} bytes={len(raw)} sha256={sha256(raw)} "
                    f"license={decision.license_name} rights={decision.rights_tier}"
                )
                if args.gcs_bucket:
                    pdf_url = free_pdf_url(conn, work_id)
                    if pdf_url:
                        pdf_attempted += 1
                        try:
                            pdf_raw = fetch_pdf(pdf_url)
                            pdf_gcs = gcs_upload(
                                pdf_raw, args.gcs_bucket, sha256(pdf_raw), decision.rights_tier,
                                extension="pdf", media_type="application/pdf",
                            )
                            was_pdf_reused = store_pdf(
                                conn, release_id, run_id, work_id, pmcid, pdf_url,
                                pdf_raw, decision, retrieved_at, pdf_gcs,
                            )
                            pdf_stored += int(not was_pdf_reused)
                            pdf_reused += int(was_pdf_reused)
                        except Exception as exc:
                            conn.rollback()
                            failures.append({"work": canonical_key, "pmcid": pmcid,
                                             "representation": "pdf", "url": pdf_url,
                                             "error": f"{type(exc).__name__}: {exc}"[:1000]})
            except Exception as exc:
                conn.rollback()
                failures.append({"work": canonical_key, "pmcid": pmcid,
                                 "error": f"{type(exc).__name__}: {exc}"[:1000]})
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pv_source.acquisition_run
                SET status='completed',completed_at=now(),stored_count=%s,reused_count=%s,
                    failure_count=%s,error_summary=%s
                WHERE acquisition_run_id=%s
                """,
                (stored, reused, len(failures), Json(failures), str(run_id)),
            )
        conn.commit()
        print(
            f"Run {run_id}: selected={len(candidates)} stored={stored} reused={reused} "
            f"failed={len(failures)} jats_gcs={stored + reused if args.gcs_bucket else 0} "
            f"pdf_attempted={pdf_attempted} pdf_stored={pdf_stored} pdf_reused={pdf_reused}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
