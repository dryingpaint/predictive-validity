"""Project detailed ChEMBL mechanism context from archived mechanism sets.

This does not create narrower molecular targets.  Binding-site comments are
source qualifiers on the asset-to-target assertion and remain traceable to the
same immutable ChEMBL mechanism record.
"""
from __future__ import annotations

import argparse
import os

import psycopg2
from psycopg2.extras import Json

from pv.ingest.semantic_verifier import mechanism_support_quote


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    examined = updated = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT version.source_record_version_id,version.raw_payload
                FROM pv_source.source_record record
                JOIN pv_source.source_record_version version
                  ON version.source_record_id=record.source_record_id
                WHERE record.source_system_id='chembl'
                  AND record.record_type='mechanism_set'
                """
            )
            for version_id, payload in cur.fetchall():
                for mechanism in payload.get("mechanisms") or []:
                    examined += 1
                    locator = {
                        "mec_id": mechanism.get("mec_id"),
                        "target_chembl_id": mechanism.get("target_chembl_id"),
                        "molecule_chembl_id": mechanism.get("molecule_chembl_id"),
                        "mechanism_of_action": mechanism.get("mechanism_of_action"),
                        "binding_site_comment": mechanism.get("binding_site_comment"),
                        "action_type": mechanism.get("action_type"),
                        "direct_interaction": mechanism.get("direct_interaction"),
                    }
                    cur.execute(
                        """
                        UPDATE pv_evidence.asset_target_assertion
                        SET support_quote=%s,support_locator=%s
                        WHERE source_record_version_id=%s
                          AND source_native_id=%s
                          AND (support_quote IS DISTINCT FROM %s
                               OR support_locator IS DISTINCT FROM %s)
                        """,
                        (
                            mechanism_support_quote(mechanism), Json(locator), version_id,
                            f"ChEMBL mechanism:{mechanism['mec_id']}",
                            mechanism_support_quote(mechanism), Json(locator),
                        ),
                    )
                    updated += cur.rowcount
        if args.commit:
            conn.commit()
        else:
            conn.rollback()
    finally:
        conn.close()
    print(f"{'committed' if args.commit else 'dry-run'}: examined={examined}, updated={updated}")


if __name__ == "__main__":
    main()
