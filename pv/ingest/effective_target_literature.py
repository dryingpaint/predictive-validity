"""Stream the active-policy effective-target-only Europe PMC corpus."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from psycopg2.extras import Json

from pv.ingest.literature_stream import count_query, stream_query
from pv.ingest.search_aliases import target_search_aliases
from pv.ingest.target_phenotype_literature import (
    database_connection,
    start_run,
    target_clause,
)


ADAPTER = "pv.ingest.effective_target_literature"
ADAPTER_VERSION = "2.0.0"
POLICY_VERSION = "pv_literature_v2"
QUERY_KIND = "effective_target_only_v1"
STANDALONE_CONTEXT_TYPES = {"subfamily", "isoform"}


def load_subject(
    conn: Any, target_id_arg: str, context_ids: list[int]
) -> tuple[Any, str, list[str], list[dict[str, Any]]]:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT DISTINCT target.entity_id,
                     coalesce(nullif(target.approved_symbol,''),target.approved_name),
                     target.approved_name
               FROM pv_core.v_target_phenotype_literature_scope scope
               JOIN pv_core.target target ON target.entity_id=scope.target_entity_id
               WHERE scope.policy_version='human_therapeutics_v2'
                 AND target.entity_id=%s::uuid""",
            (target_id_arg,),
        )
        targets = cur.fetchall()
        if len(targets) != 1:
            raise SystemExit("No unique in-scope human target found")
        target_id, target_label, approved_name = targets[0]
        aliases = target_search_aliases(
            cur, target_id, [target_label, approved_name]
        )
        contexts: list[dict[str, Any]] = []
        if context_ids:
            cur.execute(
                """SELECT context.asset_target_context_assertion_id,
                          context.context_type,context.context_name
                   FROM pv_evidence.v_latest_asset_target_context context
                   JOIN pv_evidence.asset_target_assertion assertion
                     USING (asset_target_assertion_id)
                   WHERE assertion.target_entity_id=%s
                     AND context.asset_target_context_assertion_id=ANY(%s)
                     AND context.search_eligible=true
                     AND context.verification_status='exact_source_span'
                   ORDER BY context.context_type,context.context_name,
                            context.asset_target_context_assertion_id""",
                (str(target_id), context_ids),
            )
            contexts = [
                {"id": row[0], "type": row[1], "name": row[2]}
                for row in cur.fetchall()
            ]
            if {row["id"] for row in contexts} != set(context_ids):
                raise SystemExit("One or more context IDs are not current verified contexts for this target")
    if not aliases:
        raise SystemExit("Target has no safe deterministic search aliases")
    return target_id, target_label, aliases, contexts


def build_query(
    target_id: Any,
    target_aliases: list[str],
    contexts: list[dict[str, Any]],
) -> tuple[dict[str, str], dict[int, str], str]:
    standalone = [
        context for context in contexts
        if context["type"] in STANDALONE_CONTEXT_TYPES
    ]
    if standalone:
        search_contexts = standalone
        query = target_clause(list(dict.fromkeys(row["name"] for row in standalone)))
        strategy = "verified_standalone_context_replaces_broad_parent"
    elif contexts:
        search_contexts = contexts
        query = (
            f"{target_clause(target_aliases)} AND "
            f"{target_clause(list(dict.fromkeys(row['name'] for row in contexts)))}"
        )
        strategy = "verified_context_qualifies_parent"
    else:
        search_contexts = []
        query = target_clause(target_aliases)
        strategy = "canonical_target_aliases"

    search_ids = {row["id"] for row in search_contexts}
    context_roles = {
        row["id"]: "search_term" if row["id"] in search_ids else "provenance_only"
        for row in contexts
    }
    identity_payload = {
        "target_id": str(target_id),
        "search_contexts": sorted({
            (row["type"], row["name"].strip().casefold())
            for row in search_contexts
        }),
        "strategy": strategy,
        "policy": POLICY_VERSION,
    }
    identity = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:20]
    return ({
        "query_kind": QUERY_KIND,
        "query_key": f"effective-target:{identity}",
        "query": query,
    }, context_roles, strategy)


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
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--context-ids", default="",
                        help="comma-separated current verified context assertion IDs")
    parser.add_argument("--limit", type=int, default=0,
                        help="debug only; capped runs are marked truncated and inactive")
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    if args.limit < 0:
        raise SystemExit("--limit must be nonnegative")
    try:
        context_ids = [int(value) for value in args.context_ids.split(",") if value]
    except ValueError as exc:
        raise SystemExit("--context-ids must be comma-separated integers") from exc

    conn = database_connection()
    run_id = None
    try:
        target_id, target_label, aliases, contexts = load_subject(
            conn, args.target_id, context_ids
        )
        spec, context_roles, strategy = build_query(target_id, aliases, contexts)
        if not args.commit:
            print(json.dumps({
                "policy": POLICY_VERSION,
                "query_kind": QUERY_KIND,
                "target": target_label,
                "strategy": strategy,
                "contexts": contexts,
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
                "target_id": str(target_id),
                "target": target_label,
                "target_aliases": aliases,
                "contexts": contexts,
                "query_strategy": strategy,
                "limit": args.limit,
                "page_size": args.page_size,
            },
            adapter=ADAPTER,
            adapter_version=ADAPTER_VERSION,
        )
        result = stream_query(
            conn, release_id, run_id, spec, retrieved_at,
            target_id=target_id, context_roles=context_roles,
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
