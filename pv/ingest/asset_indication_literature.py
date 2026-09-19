"""Stream the active-policy asset-plus-indication Europe PMC corpus."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from psycopg2.extras import Json

from pv.ingest.literature_stream import count_query, stream_query
from pv.ingest.search_aliases import asset_search_aliases
from pv.ingest.target_phenotype_literature import (
    database_connection,
    escape_phrase,
    field_term,
    start_run,
    target_clause,
)


ADAPTER = "pv.ingest.asset_indication_literature"
ADAPTER_VERSION = "2.0.0"
POLICY_VERSION = "pv_literature_v2"
QUERY_KIND = "asset_indication_v2"


def phenotype_search_aliases(cur: Any, phenotype_id: Any, preferred_name: str) -> list[str]:
    cur.execute(
        """SELECT alias_text
           FROM pv_core.entity_alias
           WHERE entity_id=%s AND entity_type='phenotype'
             AND alias_kind IN (
               'preferred_label','exact_synonym','related_synonym','query_label'
             )
             AND is_ambiguous=false
           ORDER BY alias_kind,alias_text""",
        (phenotype_id,),
    )
    values = [preferred_name] + [row[0] for row in cur.fetchall()]
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = str(value or "").strip()
        normalized = clean.casefold()
        if clean and normalized not in seen:
            seen.add(normalized)
            output.append(clean)
    return output


def load_subject(conn: Any, asset_id: str, phenotype_id: str) -> tuple[Any, str, list[str], Any, str, list[str]]:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT DISTINCT asset.entity_id,asset.active_moiety_name,
                              phenotype.entity_id,phenotype.preferred_name
               FROM pv_core.v_asset_indication_literature_scope scope
               JOIN pv_core.asset asset ON asset.entity_id=scope.asset_entity_id
               JOIN pv_core.phenotype phenotype
                 ON phenotype.entity_id=scope.phenotype_entity_id
               WHERE scope.policy_version='human_therapeutics_v2'
                 AND scope.asset_entity_id=%s::uuid
                 AND scope.phenotype_entity_id=%s::uuid""",
            (asset_id, phenotype_id),
        )
        rows = cur.fetchall()
        if len(rows) != 1:
            raise SystemExit("No unique in-scope asset/indication pair found")
        resolved_asset_id, asset_name, resolved_phenotype_id, phenotype_name = rows[0]
        asset_aliases = asset_search_aliases(cur, resolved_asset_id, [asset_name])
        phenotype_aliases = phenotype_search_aliases(
            cur, resolved_phenotype_id, phenotype_name
        )
    if not asset_aliases or not phenotype_aliases:
        raise SystemExit("The pair has no safe deterministic search aliases")
    return (
        resolved_asset_id, asset_name, asset_aliases,
        resolved_phenotype_id, phenotype_name, phenotype_aliases,
    )


def build_query(
    asset_id: Any,
    phenotype_id: Any,
    asset_aliases: list[str],
    phenotype_aliases: list[str],
    phenotype_name: str,
) -> dict[str, str]:
    phenotype_terms = [field_term(alias) for alias in phenotype_aliases]
    phenotype_terms.append(f'MESH:"{escape_phrase(phenotype_name)}"')
    phenotype_clause = "(" + " OR ".join(phenotype_terms) + ")"
    query = f"{target_clause(asset_aliases)} AND {phenotype_clause}"
    identity = hashlib.sha256(
        f"{asset_id}:{phenotype_id}:{POLICY_VERSION}".encode()
    ).hexdigest()[:20]
    return {
        "query_kind": QUERY_KIND,
        "query_key": f"asset-indication:{identity}",
        "query": query,
    }


def mark_run_failed(conn: Any, run_id: Any, exc: BaseException) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE pv_source.acquisition_run
               SET status='failed',completed_at=now(),failure_count=1,error_summary=%s
               WHERE acquisition_run_id=%s""",
            (Json([{"error": f"{type(exc).__name__}: {exc}"[:1000]}]), str(run_id)),
        )
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--phenotype-id", required=True)
    parser.add_argument("--limit", type=int, default=0,
                        help="debug only; capped runs are marked truncated and inactive")
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    if args.limit < 0:
        raise SystemExit("--limit must be nonnegative")

    conn = database_connection()
    run_id = None
    try:
        (asset_id, asset_name, asset_aliases, phenotype_id, phenotype_name,
         phenotype_aliases) = load_subject(conn, args.asset_id, args.phenotype_id)
        spec = build_query(
            asset_id, phenotype_id, asset_aliases, phenotype_aliases, phenotype_name
        )
        if not args.commit:
            print(json.dumps({
                "policy": POLICY_VERSION,
                "query_kind": QUERY_KIND,
                "asset": asset_name,
                "indication": phenotype_name,
                "hits": count_query(spec["query"]),
                "query": spec["query"],
            }, indent=2))
            return

        retrieved_at = datetime.now(timezone.utc)
        release_id, run_id = start_run(
            conn,
            retrieved_at,
            {
                "literature_policy_version": POLICY_VERSION,
                "asset_id": str(asset_id),
                "asset": asset_name,
                "asset_aliases": asset_aliases,
                "phenotype_id": str(phenotype_id),
                "phenotype": phenotype_name,
                "phenotype_aliases": phenotype_aliases,
                "limit": args.limit,
                "page_size": args.page_size,
            },
            adapter=ADAPTER,
            adapter_version=ADAPTER_VERSION,
        )
        result = stream_query(
            conn, release_id, run_id, spec, retrieved_at,
            asset_id=asset_id, phenotype_id=phenotype_id,
            limit=args.limit, page_size=args.page_size,
        )
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE pv_source.acquisition_run
                   SET status='completed',completed_at=now(),discovered_count=%s,
                       selected_count=%s,stored_count=%s,reused_count=%s
                   WHERE acquisition_run_id=%s""",
                (
                    result["discovered"], result["selected"], result["stored"],
                    result["reused"], str(run_id),
                ),
            )
        conn.commit()
        print(json.dumps(result, indent=2))
    except BaseException as exc:
        conn.rollback()
        if run_id is not None:
            mark_run_failed(conn, run_id, exc)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
