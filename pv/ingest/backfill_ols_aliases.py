"""Backfill phenotype synonyms from already archived OLS search responses.

Exact ontology synonyms become eligible retrieval aliases.  Related synonyms
are retained for provenance and review but marked ambiguous, so they cannot
silently broaden literature searches.
"""
from __future__ import annotations

import argparse
import os
from collections import Counter
from typing import Any

import psycopg2
from psycopg2.extras import execute_values

from pv.ingest.semantic_verifier import normalized


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    counts = Counter()
    values: list[tuple[Any, ...]] = []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (record.source_record_id)
                       version.source_release_id,version.source_record_version_id,
                       version.raw_payload
                FROM pv_source.source_record record
                JOIN pv_source.source_record_version version
                  ON version.source_record_id=record.source_record_id
                WHERE record.source_system_id='ols4'
                  AND record.record_type='ontology_search'
                ORDER BY record.source_record_id,version.retrieved_at DESC,
                         version.source_record_version_id DESC
                """
            )
            records = cur.fetchall()
            cur.execute(
                """
                SELECT identifier.identifier,identifier.entity_id
                FROM pv_core.entity_identifier identifier
                JOIN pv_core.phenotype phenotype ON phenotype.entity_id=identifier.entity_id
                """
            )
            entities = {identifier: entity_id for identifier, entity_id in cur.fetchall()}
            seen: set[tuple[Any, int, str, str]] = set()
            for release_id, version_id, payload in records:
                for doc in (payload.get("response") or {}).get("docs") or []:
                    entity_id = entities.get(doc.get("obo_id"))
                    if entity_id is None:
                        continue
                    for field, kind, ambiguous in (
                        ("exact_synonyms", "exact_synonym", False),
                        ("related_synonyms", "related_synonym", True),
                    ):
                        for text in doc.get(field) or []:
                            clean = str(text).strip()
                            if not clean:
                                continue
                            key = (entity_id, version_id, kind, clean)
                            if key in seen:
                                continue
                            seen.add(key)
                            counts[kind] += 1
                            values.append(
                                (entity_id, clean, normalized(clean), kind,
                                 release_id, version_id, ambiguous)
                            )
            if values:
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
                    template="(%s,'phenotype',%s,%s,%s,'en',NULL,%s,%s,%s)",
                    page_size=10_000,
                )
                inserted_count = cur.rowcount
            else:
                inserted_count = 0
        if args.commit:
            conn.commit()
        else:
            conn.rollback()
    finally:
        conn.close()

    mode = "committed" if args.commit else "dry-run"
    print(f"{mode}: {len(records)} archived OLS search records")
    print("classified: " + ", ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print(f"new typed rows: {inserted_count}")


if __name__ == "__main__":
    main()
