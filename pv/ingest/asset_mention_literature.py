"""Retrieve every Europe PMC title/abstract mention of a normalized asset."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

from psycopg2.extras import Json

from pv.ingest.asset_preclinical_literature import load_assets
from pv.ingest.target_phenotype_literature import (
    database_connection,
    discover,
    start_run,
    store_query,
    target_clause,
    writable_connection,
)


ADAPTER = "pv.ingest.asset_mention_literature"
ADAPTER_VERSION = "1.0.0"
QUERY_VERSION = "asset_mentions_v1"


def build_query(aliases: list[str]) -> dict[str, str]:
    return {
        "query_kind": "asset_mention",
        "query_key_suffix": QUERY_VERSION,
        "query": target_clause(aliases),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit-per-query", type=int, default=0,
                        help="0 stores every result; positive values are for debugging only")
    parser.add_argument("--asset", help="optional canonical active-moiety name filter")
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if args.limit_per_query < 0:
        raise SystemExit("--limit-per-query must be nonnegative")
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")

    conn = database_connection()
    totals = {"assets": 0, "discovered": 0, "selected": 0, "stored": 0, "reused": 0}
    try:
        assets = load_assets(conn, args.asset)
        for asset_id, asset_name, _phenotypes, aliases in assets:
            spec = build_query(aliases)
            results, pages, hits = discover(spec["query"])
            print(f"{asset_name} asset_mention: hits={hits}")
            if not args.commit:
                continue

            conn = writable_connection(conn)
            retrieved_at = datetime.now(timezone.utc)
            release_id, run_id = start_run(
                conn,
                retrieved_at,
                {
                    "asset": asset_name,
                    "aliases": aliases,
                    "query_version": QUERY_VERSION,
                    "limit_per_query": args.limit_per_query,
                },
                adapter=ADAPTER,
                adapter_version=ADAPTER_VERSION,
            )
            try:
                selected, stored, reused = store_query(
                    conn, release_id, run_id, None, None, asset_name,
                    spec, results, pages, hits, args.limit_per_query, retrieved_at,
                    asset_id=asset_id,
                )
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE pv_source.acquisition_run
                           SET status='completed',completed_at=now(),discovered_count=%s,
                               selected_count=%s,stored_count=%s,reused_count=%s
                           WHERE acquisition_run_id=%s""",
                        (hits, selected, stored, reused, str(run_id)),
                    )
                conn.commit()
            except BaseException as exc:
                conn.rollback()
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE pv_source.acquisition_run
                           SET status='failed',completed_at=now(),failure_count=1,
                               error_summary=%s WHERE acquisition_run_id=%s""",
                        (Json([{"error": f"{type(exc).__name__}: {exc}"[:1000]}]), str(run_id)),
                    )
                conn.commit()
                raise
            totals["assets"] += 1
            totals["discovered"] += hits
            totals["selected"] += selected
            totals["stored"] += stored
            totals["reused"] += reused
    finally:
        conn.close()

    if not args.commit:
        print("Dry run complete; Neon was not modified.")
    else:
        print(json.dumps(totals, indent=2))


if __name__ == "__main__":
    main()
