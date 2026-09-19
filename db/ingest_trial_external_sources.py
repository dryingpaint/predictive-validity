"""Repeatably ingest curated trial-specific evidence without fuzzy auto-linking."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import Json


NCT_RE = re.compile(r"^NCT\d{8}$")
EVIDENCE_RELATIONS = {
    "exact_nct", "unique_protocol", "parent_trial", "extension_trial",
    "sibling_indication", "program_only", "probable_composite",
}
SOURCE_TEXT_KINDS = {"exact_excerpt", "verified_paraphrase", "source_text"}
SUPPORT_TYPES = {
    "participant_results_present", "primary_endpoint_status",
    "safety_descriptive_only", "safety_failure", "efficacy_futility",
    "causal_stop", "study_execution", "program_continuation",
    "program_discontinuation", "followup_only_stop",
}
PROGRAM_SCOPES = {"target_indication", "protocol_family", "asset_global"}


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_jsonl(paths: list[Path]) -> Iterable[tuple[Path, int, dict]]:
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}: {exc}") from exc
                if not isinstance(value, dict):
                    raise ValueError(f"{path}:{line_number}: expected JSON object")
                yield path, line_number, value


def validated(row: dict, location: str) -> dict:
    nct_id = str(row.get("nct_id") or "").strip().upper()
    if not NCT_RE.fullmatch(nct_id):
        raise ValueError(f"{location}: invalid nct_id {nct_id!r}")
    required = (
        "source_type", "source_name", "external_id", "source_url", "title",
        "relationship", "retrieval_method", "attribution", "evidence_relation",
    )
    missing = [field for field in required if not str(row.get(field) or "").strip()]
    if missing:
        raise ValueError(f"{location}: missing fields {missing}")
    source_url = str(row["source_url"]).strip()
    if urlparse(source_url).scheme not in {"http", "https"}:
        raise ValueError(f"{location}: source_url must be HTTP(S)")
    evidence_relation = str(row["evidence_relation"]).strip()
    if evidence_relation not in EVIDENCE_RELATIONS:
        raise ValueError(f"{location}: invalid evidence_relation {evidence_relation!r}")
    support_fields = (
        "supports_scientific_outcome", "supports_termination_driver",
        "supports_program_outcome",
    )
    for field in support_fields:
        if not isinstance(row.get(field), bool):
            raise ValueError(f"{location}: {field} must be boolean")
    body_text = str(row.get("body_text") or row.get("excerpt_text") or "").strip()
    abstract_text = str(row.get("abstract_text") or "").strip() or None
    if not body_text and not abstract_text:
        raise ValueError(f"{location}: abstract_text or body_text is required")
    metadata = dict(row.get("metadata") or {})
    text_kind = str(metadata.get("text_kind") or "").strip()
    if text_kind not in SOURCE_TEXT_KINDS:
        raise ValueError(
            f"{location}: metadata.text_kind must be one of "
            f"{sorted(SOURCE_TEXT_KINDS)}"
        )
    if text_kind == "exact_excerpt" and not str(metadata.get("locator") or "").strip():
        raise ValueError(f"{location}: exact excerpts require metadata.locator")
    if (
        evidence_relation in {"parent_trial", "sibling_indication", "program_only"}
        and row["supports_scientific_outcome"]
    ):
        raise ValueError(
            f"{location}: {evidence_relation} evidence cannot support the "
            "target trial's scientific outcome"
        )
    support_types = metadata.get("support_types")
    if not isinstance(support_types, list) or not support_types:
        raise ValueError(f"{location}: metadata.support_types must be nonempty")
    invalid_support_types = sorted(set(support_types) - SUPPORT_TYPES)
    if invalid_support_types:
        raise ValueError(
            f"{location}: invalid metadata.support_types {invalid_support_types}"
        )
    if metadata.get("support_types_grounded_in_excerpt") is not True:
        raise ValueError(
            f"{location}: metadata.support_types_grounded_in_excerpt must be true"
        )
    if evidence_relation == "probable_composite":
        crosswalk_fields = metadata.get("crosswalk_fields")
        if not isinstance(crosswalk_fields, list) or len(crosswalk_fields) < 4:
            raise ValueError(
                f"{location}: probable_composite requires at least four "
                "metadata.crosswalk_fields"
            )
        if not str(metadata.get("linkage_basis") or "").strip():
            raise ValueError(
                f"{location}: probable_composite requires metadata.linkage_basis"
            )
        if metadata.get("competing_sibling_checked") is not True:
            raise ValueError(
                f"{location}: probable_composite requires a sibling check"
            )
        if metadata.get("no_competing_sibling") is not True:
            raise ValueError(
                f"{location}: probable_composite requires no_competing_sibling=true"
            )
    program_scope = metadata.get("program_scope")
    if row["supports_program_outcome"] and program_scope not in PROGRAM_SCOPES:
        raise ValueError(
            f"{location}: program-supporting evidence requires a valid "
            "metadata.program_scope"
        )
    if not row["supports_program_outcome"] and program_scope is not None:
        raise ValueError(
            f"{location}: metadata.program_scope requires program support"
        )
    metadata.update({field: row[field] for field in support_fields})
    metadata["evidence_relation"] = evidence_relation
    document_payload = {
        "source_type": str(row["source_type"]).strip(),
        "source_name": str(row["source_name"]).strip(),
        "external_id": str(row["external_id"]).strip(),
        "source_version": row.get("source_version"),
        "source_url": source_url,
        "title": str(row["title"]).strip(),
        "abstract_text": abstract_text,
        "body_text": body_text or None,
        "raw_content": row.get("raw_content"),
        "raw_content_text": row.get("raw_content_text"),
        "media_type": str(row.get("media_type") or "text/plain"),
        "language": row.get("language") or "en",
        "source_updated_at": row.get("source_updated_at"),
        "retrieval_method": str(row["retrieval_method"]).strip(),
        "attribution": str(row["attribution"]).strip(),
        "rights_notice": row.get("rights_notice"),
        "metadata": metadata,
    }
    return {
        "nct_id": nct_id,
        **document_payload,
        "content_sha256": sha256_text(canonical_json(document_payload)),
        "evidence_relation": evidence_relation,
        **{field: row[field] for field in support_fields},
        "relationship": str(row["relationship"]).strip(),
        "discovered_from": str(row.get("discovered_from") or "curated_external_source"),
        "link_metadata": {
            "evidence_relation": evidence_relation,
            **{field: row[field] for field in support_fields},
            **dict(row.get("link_metadata") or {}),
        },
    }


def ingest(cur, row: dict) -> int:
    cur.execute(
        """
        INSERT INTO preclin.source_document (
          source_type, source_name, external_id, source_version, source_url,
          title, abstract_text, body_text, raw_content, raw_content_text,
          media_type, language, content_sha256, source_updated_at,
          retrieval_method, attribution, rights_notice, metadata
        ) VALUES (
          %(source_type)s, %(source_name)s, %(external_id)s, %(source_version)s,
          %(source_url)s, %(title)s, %(abstract_text)s, %(body_text)s,
          %(raw_content)s, %(raw_content_text)s, %(media_type)s, %(language)s,
          %(content_sha256)s, %(source_updated_at)s, %(retrieval_method)s,
          %(attribution)s, %(rights_notice)s, %(metadata)s
        )
        ON CONFLICT (source_name, external_id, content_sha256)
        DO UPDATE SET last_seen_at=now()
        RETURNING source_document_id
        """,
        {
            **row,
            "raw_content": Json(row["raw_content"]),
            "metadata": Json(row["metadata"]),
        },
    )
    document_id = int(cur.fetchone()[0])
    cur.execute(
        """
        INSERT INTO preclin.source_document_subject (
          subject_type, subject_key, source_document_id, relationship,
          discovered_from, link_metadata
        ) VALUES ('trial', %s, %s, %s, %s, %s)
        ON CONFLICT (subject_type, subject_key, source_document_id, relationship)
        DO UPDATE SET link_metadata=EXCLUDED.link_metadata,
                      discovered_from=EXCLUDED.discovered_from
        """,
        (
            row["nct_id"], document_id, row["relationship"],
            row["discovered_from"], Json(row["link_metadata"]),
        ),
    )
    return document_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument(
        "--commit", action="store_true",
        help="Persist the transaction; omission performs a full database dry-run",
    )
    parser.add_argument(
        "--validated-out", type=Path,
        help="Atomically write the normalized, validated source rows after DB validation",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [
        validated(row, f"{path}:{line_number}")
        for path, line_number, row in read_jsonl(args.inputs)
    ]
    keys = [(row["nct_id"], row["source_name"], row["external_id"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate trial/source/external-id rows in input")
    connection = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cursor = connection.cursor()
        cursor.execute(
            """SELECT DISTINCT subject_key
               FROM preclin.source_document_subject
               WHERE subject_type='trial' AND subject_key=ANY(%s)
                 AND relationship='registry_record'""",
            (sorted({row["nct_id"] for row in rows}),),
        )
        known_nct_ids = {str(value) for value, in cursor.fetchall()}
        unknown_nct_ids = sorted({row["nct_id"] for row in rows} - known_nct_ids)
        if unknown_nct_ids:
            raise ValueError(
                "No canonical registry source for: " + ", ".join(unknown_nct_ids)
            )
        document_ids = [ingest(cursor, row) for row in rows]
        if args.commit:
            connection.commit()
        else:
            connection.rollback()
    finally:
        connection.close()
    if args.validated_out:
        args.validated_out.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.validated_out.with_suffix(args.validated_out.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        temporary.replace(args.validated_out)
    print(
        f"validated={len(rows)} documents={len(set(document_ids))} "
        f"committed={args.commit}"
    )


if __name__ == "__main__":
    main()
