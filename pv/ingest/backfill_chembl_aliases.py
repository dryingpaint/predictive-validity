"""Backfill typed ChEMBL asset aliases from already archived raw records.

The command performs no network requests.  It is dry-run by default and is
idempotent because every inserted alias retains its source release and source
record version and uses the ledger's null-safe unique index.
"""
from __future__ import annotations

import argparse
import os
from collections import Counter
from typing import Any

import psycopg2
from psycopg2.extras import execute_values

from pv.ingest.search_aliases import classify_chembl_asset_alias
from pv.ingest.semantic_verifier import normalized


def rows_to_backfill(cur: Any) -> list[tuple[Any, int, int, dict[str, Any]]]:
    cur.execute(
        """
        SELECT DISTINCT ON (identifier.entity_id,record.source_record_id)
               identifier.entity_id,version.source_release_id,
               version.source_record_version_id,version.raw_payload
        FROM pv_core.entity_identifier identifier
        JOIN pv_source.source_record record
          ON record.source_system_id='chembl'
         AND record.native_record_id=identifier.identifier
        JOIN pv_source.source_record_version version
          ON version.source_record_id=record.source_record_id
        WHERE identifier.namespace='ChEMBL'
          AND record.record_type IN ('molecule_record','asset_record')
        ORDER BY identifier.entity_id,record.source_record_id,
                 version.retrieved_at DESC,version.source_record_version_id DESC
        """
    )
    return cur.fetchall()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    seen = Counter()
    values: list[tuple[Any, ...]] = []
    try:
        with conn.cursor() as cur:
            records = rows_to_backfill(cur)
            for entity_id, release_id, version_id, payload in records:
                for synonym in payload.get("molecule_synonyms") or []:
                    text = str(synonym.get("molecule_synonym") or "").strip()
                    if not text:
                        continue
                    kind, ambiguous, language = classify_chembl_asset_alias(synonym)
                    seen[kind] += 1
                    values.append(
                        (entity_id, text, normalized(text), kind, language,
                         release_id, version_id, ambiguous)
                    )
            execute_values(
                cur,
                """
                INSERT INTO pv_core.entity_alias
                  (entity_id,entity_type,alias_text,alias_normalized,alias_kind,
                   language,taxon_id,source_release_id,source_record_version_id,
                   is_ambiguous)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                values,
                template="(%s,'asset',%s,%s,%s,%s,NULL,%s,%s,%s)",
                page_size=10_000,
            )
            inserted_count = cur.rowcount
        if args.commit:
            conn.commit()
        else:
            conn.rollback()
    finally:
        conn.close()

    mode = "committed" if args.commit else "dry-run"
    print(f"{mode}: {len(records)} archived ChEMBL molecule records")
    print("classified: " + ", ".join(f"{key}={seen[key]}" for key in sorted(seen)))
    print(f"new typed rows: {inserted_count}")


if __name__ == "__main__":
    main()
