"""Retrieve complete asset-linked preclinical literature candidate sets."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json

from pv.ingest.target_phenotype_literature import (
    database_connection, discover, field_term, start_run, store_query,
    target_clause, writable_connection,
)
from pv.ingest.search_aliases import asset_search_aliases


ADAPTER = "pv.ingest.asset_preclinical_literature"
PRECLINICAL_CLAUSE = (
    '(TITLE_ABS:preclinical OR TITLE_ABS:"pre-clinical" OR TITLE_ABS:organoid '
    'OR TITLE_ABS:"patient-derived" OR TITLE_ABS:"patient derived" '
    'OR TITLE_ABS:"cell model" OR TITLE_ABS:"cell line" OR TITLE_ABS:"primary cells" '
    'OR TITLE_ABS:"in vitro" OR TITLE_ABS:"in vivo" OR TITLE_ABS:"animal model" '
    'OR TITLE_ABS:mouse OR TITLE_ABS:mice OR TITLE_ABS:rat OR TITLE_ABS:zebrafish '
    'OR TITLE_ABS:xenograft OR TITLE_ABS:PDX OR TITLE_ABS:assay '
    'OR TITLE_ABS:pharmacodynamic OR TITLE_ABS:biomarker)'
)


def build_wide_query(aliases: list[str]) -> dict[str, str]:
    asset = target_clause(aliases)
    return {
        "query_kind": "asset_preclinical_wide",
        "query_key_suffix": "asset_preclinical_wide",
        "query": f"{asset} AND {PRECLINICAL_CLAUSE}",
    }


def build_indication_query(aliases: list[str], phenotype_id: Any, phenotype: str) -> dict[str, str]:
    asset = target_clause(aliases)
    suffix = hashlib.sha256(str(phenotype_id).encode()).hexdigest()[:16]
    return {
        "query_kind": "asset_indication_preclinical",
        "query_key_suffix": f"asset_indication_preclinical:{suffix}",
        "query": f"{asset} AND ({field_term(phenotype)}) AND {PRECLINICAL_CLAUSE}",
    }


def load_assets(conn: Any, asset_filter: str | None = None) -> list[tuple[Any, str, list[tuple[Any, str]], list[str]]]:
    with conn.cursor() as cur:
        cur.execute(
            """WITH eligible AS (
                 SELECT DISTINCT tal.nct_id,tal.asset_entity_id
                 FROM pv_core.trial_asset_link tal
                 JOIN pv_core.trial_development_scope tds ON tds.nct_id=tal.nct_id
                  AND tds.policy_version='human_therapeutics_v2'
                  AND tds.scope_status='included'
                 JOIN pv_core.asset_development_scope ads ON ads.asset_entity_id=tal.asset_entity_id
                  AND ads.policy_version=tds.policy_version AND ads.scope_status='included'
                 WHERE tal.resolution_status='resolved'
               )
               SELECT DISTINCT a.entity_id,a.active_moiety_name,p.entity_id,p.preferred_name
               FROM eligible e JOIN pv_core.asset a ON a.entity_id=e.asset_entity_id
               LEFT JOIN pv_core.trial_indication_link til ON til.nct_id=e.nct_id
                AND til.indication_role IN ('treatment','prevention','diagnosis')
               LEFT JOIN pv_core.phenotype p ON p.entity_id=til.phenotype_entity_id
               WHERE 1=1
                 AND (%s IS NULL OR lower(a.active_moiety_name)=lower(%s))
               ORDER BY a.active_moiety_name,p.preferred_name NULLS LAST"""
            , (asset_filter, asset_filter)
        )
        source_rows = cur.fetchall()
        result = []
        grouped: dict[tuple[Any, str], list[tuple[Any, str]]] = {}
        for asset_id, asset_name, phenotype_id, phenotype_name in source_rows:
            if phenotype_id is not None:
                grouped.setdefault((asset_id, asset_name), []).append((phenotype_id, phenotype_name))
            else:
                grouped.setdefault((asset_id, asset_name), [])
        for (asset_id, asset_name), phenotypes in grouped.items():
            aliases = asset_search_aliases(cur, asset_id, [asset_name])
            result.append((asset_id, asset_name, list(dict.fromkeys(phenotypes)), aliases))
    return result


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
    run_ids = []
    totals = {"pairs": 0, "discovered": 0, "selected": 0, "stored": 0, "reused": 0}
    try:
        assets = load_assets(conn, args.asset)
        for asset_id, asset_name, phenotypes, aliases in assets:
            specs = [(None, build_wide_query(aliases))]
            specs.extend(
                (phenotype_id, build_indication_query(aliases, phenotype_id, phenotype_name))
                for phenotype_id, phenotype_name in phenotypes
            )
            discoveries = []
            for phenotype_id, spec in specs:
                results, pages, hits = discover(spec["query"])
                discoveries.append((phenotype_id, spec, results, pages, hits))
                print(f"{asset_name} {spec['query_kind']}: hits={hits}")
            if not args.commit:
                continue
            conn = writable_connection(conn)
            retrieved_at = datetime.now(timezone.utc)
            release_id, run_id = start_run(
                conn, retrieved_at,
                {"asset": asset_name,
                 "phenotypes": [{"id": str(pid), "name": name} for pid, name in phenotypes],
                 "aliases": aliases,
                 "limit_per_query": args.limit_per_query}, adapter=ADAPTER,
            )
            run_ids.append(run_id)
            selected_total = stored_total = reused_total = 0
            try:
                for phenotype_id, spec, results, pages, hits in discoveries:
                    selected, stored, reused = store_query(
                        conn, release_id, run_id, None, phenotype_id, asset_name,
                        spec, results, pages, hits, args.limit_per_query, retrieved_at,
                        asset_id=asset_id,
                    )
                    selected_total += selected
                    stored_total += stored
                    reused_total += reused
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE pv_source.acquisition_run SET status='completed',completed_at=now(),
                             discovered_count=%s,selected_count=%s,stored_count=%s,reused_count=%s
                           WHERE acquisition_run_id=%s""",
                        (sum(row[4] for row in discoveries), selected_total, stored_total,
                         reused_total, str(run_id)),
                    )
                conn.commit()
            except BaseException as exc:
                conn.rollback()
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE pv_source.acquisition_run SET status='failed',completed_at=now(),
                             failure_count=1,error_summary=%s WHERE acquisition_run_id=%s""",
                        (Json([{"error": f"{type(exc).__name__}: {exc}"[:1000]}]), str(run_id)),
                    )
                conn.commit()
                raise
            totals["pairs"] += 1
            totals["discovered"] += sum(row[4] for row in discoveries)
            totals["selected"] += selected_total
            totals["stored"] += stored_total
            totals["reused"] += reused_total
    finally:
        conn.close()
    if not args.commit:
        print("Dry run complete; Neon was not modified.")
    else:
        print(json.dumps(totals, indent=2))


if __name__ == "__main__":
    main()
