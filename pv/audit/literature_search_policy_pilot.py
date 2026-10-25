"""Count results for the proposed asset-indication and target-only policy.

This audit is read-only. It sends count-only Europe PMC requests for the
completion-date-selected 2015 pilot and does not create acquisition runs,
source records, scholarly works, or candidate links.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

from pv.ingest.target_phenotype_literature import (
    API_URL,
    database_connection,
    field_term,
    target_clause,
)
from pv.ingest.search_aliases import asset_search_aliases, target_search_aliases


DEFAULT_COHORT = "pv_2015_actual_completed_drug_biological_pilot5_v1"
POLICY_VERSION = "human_therapeutics_v2"
USER_AGENT = "predictive-validity-literature-policy-audit/1.0"


def unique_casefold(values: list[str | None]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        normalized = value.strip().casefold()
        if normalized and normalized not in seen:
            seen.add(normalized)
            output.append(value.strip())
    return output


def aliases(cur: Any, entity_id: Any, alias_kinds: tuple[str, ...]) -> list[str]:
    cur.execute(
        """SELECT alias_text FROM pv_core.entity_alias
           WHERE entity_id=%s AND is_ambiguous=false AND alias_kind=ANY(%s)
           ORDER BY alias_text""",
        (entity_id, list(alias_kinds)),
    )
    return [row[0] for row in cur.fetchall()]


def asset_indication_specs(conn: Any, cohort_id: str) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT cm.nct_id,a.entity_id,a.active_moiety_name,
                            p.entity_id,p.preferred_name
            FROM pv_core.trial_cohort_member cm
            JOIN pv_core.trial_asset_link tal
              ON tal.nct_id=cm.nct_id AND tal.resolution_status='resolved'
            JOIN pv_core.asset a ON a.entity_id=tal.asset_entity_id
            JOIN pv_core.trial_indication_link til
              ON til.nct_id=cm.nct_id
             AND til.indication_role IN ('treatment','prevention','diagnosis')
            JOIN pv_core.phenotype p ON p.entity_id=til.phenotype_entity_id
            JOIN pv_core.trial_development_scope tds
              ON tds.nct_id=cm.nct_id AND tds.policy_version=%s
             AND tds.scope_status='included'
            JOIN pv_core.asset_development_scope ads
              ON ads.asset_entity_id=a.entity_id
             AND ads.policy_version=tds.policy_version
             AND ads.scope_status='included'
            WHERE cm.cohort_id=%s AND cm.membership_status='included'
            ORDER BY cm.nct_id,a.active_moiety_name,p.preferred_name
            """,
            (POLICY_VERSION, cohort_id),
        )
        grouped: dict[tuple[Any, ...], list[tuple[Any, str]]] = defaultdict(list)
        for nct_id, asset_id, asset_name, phenotype_id, phenotype_name in cur.fetchall():
            grouped[(nct_id, asset_id, asset_name)].append((phenotype_id, phenotype_name))

        output = []
        for (nct_id, asset_id, asset_name), phenotypes in grouped.items():
            asset_aliases = asset_search_aliases(cur, asset_id, [asset_name])
            phenotype_aliases: list[str] = []
            phenotype_mesh_labels: list[str] = []
            for phenotype_id, phenotype_name in phenotypes:
                phenotype_aliases.extend(
                    aliases(
                        cur,
                        phenotype_id,
                        ("preferred_label", "query_label", "exact_synonym", "synonym"),
                    )
                    + [phenotype_name]
                )
                phenotype_mesh_labels.append(phenotype_name)
            phenotype_aliases = unique_casefold(phenotype_aliases)
            phenotype_terms = [field_term(value) for value in phenotype_aliases]
            phenotype_terms.extend(
                f'MESH:"{value.replace(chr(34), chr(92) + chr(34))}"'
                for value in unique_casefold(phenotype_mesh_labels)
            )
            output.append({
                "category": "asset_indication",
                "key": f"{nct_id}:{asset_name}",
                "nct_id": nct_id,
                "label": asset_name,
                "context": [name for _identifier, name in phenotypes],
                "asset_aliases": asset_aliases,
                "phenotype_aliases": phenotype_aliases,
                "query": f"{target_clause(asset_aliases)} AND ("
                         + " OR ".join(phenotype_terms) + ")",
            })
    return output


def target_specs(conn: Any, cohort_id: str) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT t.entity_id,t.approved_symbol,t.approved_name,t.target_kind
            FROM pv_core.trial_cohort_member cm
            JOIN pv_core.trial_asset_link tal
              ON tal.nct_id=cm.nct_id AND tal.resolution_status='resolved'
            JOIN pv_core.trial_development_scope tds
              ON tds.nct_id=cm.nct_id AND tds.policy_version=%s
             AND tds.scope_status='included'
            JOIN pv_core.asset_development_scope ads
              ON ads.asset_entity_id=tal.asset_entity_id
             AND ads.policy_version=tds.policy_version
             AND ads.scope_status='included'
            JOIN pv_evidence.asset_target_assertion ata
              ON ata.asset_entity_id=tal.asset_entity_id
             AND ata.role='therapeutic_primary'
            JOIN pv_core.target t ON t.entity_id=ata.target_entity_id
            WHERE cm.cohort_id=%s AND cm.membership_status='included'
              AND t.taxon_id=9606 AND t.target_kind<>'nucleic_acid'
            ORDER BY t.approved_symbol,t.approved_name
            """,
            (POLICY_VERSION, cohort_id),
        )
        output = []
        for target_id, symbol, name, target_kind in cur.fetchall():
            # Component membership is provenance for a family/complex record;
            # it is not evidence that the asset targets every component.  Keep
            # components visible for review but do not OR them into the query.
            cur.execute(
                """SELECT tc.gene_symbol_literal,tc.component_name_literal,
                          component.approved_symbol,component.approved_name
                   FROM pv_core.target_component tc
                   LEFT JOIN pv_core.target component
                     ON component.entity_id=tc.component_target_entity_id
                   WHERE tc.group_target_entity_id=%s
                   ORDER BY tc.component_key""",
                (target_id,),
            )
            components = [
                value for row in cur.fetchall() for value in row if value
            ]
            target_aliases = target_search_aliases(cur, target_id, [symbol, name])
            output.append({
                "category": "target_only",
                "key": symbol or name,
                "label": symbol or name,
                "context": target_kind,
                "target_aliases": target_aliases,
                "recorded_components": unique_casefold(components),
                "query": target_clause(target_aliases),
            })
    return output


def fetch_hit_count(spec: dict[str, Any]) -> dict[str, Any]:
    parameters = {
        "query": spec["query"],
        "format": "json",
        "resultType": "core",
        "pageSize": 1,
        "synonym": "false",
    }
    url = API_URL + "?" + urllib.parse.urlencode(parameters)
    error: Exception | None = None
    for attempt in range(5):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.load(response)
            if "hitCount" not in payload:
                raise RuntimeError(f"Europe PMC response has no hitCount: {payload}")
            return {**spec, "hit_count": int(payload["hitCount"]), "request_url": url}
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            error = exc
            if attempt == 4:
                break
            time.sleep(min(2**attempt, 16))
    assert error is not None
    raise error


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = [row["hit_count"] for row in rows]
    return {
        "queries": len(rows),
        "sum_of_query_hits": sum(counts),
        "minimum": min(counts) if counts else None,
        "median": median(counts) if counts else None,
        "mean": round(sum(counts) / len(counts), 1) if counts else None,
        "maximum": max(counts) if counts else None,
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Proposed literature-search policy: 2015 pilot hit counts",
        "",
        f"Retrieved: {payload['retrieved_at']}",
        "",
        "Count-only audit; Neon was not modified. Counts are summed provider hits, "
        "not deduplicated scholarly works. Target–indication is a later local projection "
        "of the target-only corpus and therefore is not a third provider query.",
    ]
    for category in ("asset_indication", "target_only"):
        rows = [row for row in payload["results"] if row["category"] == category]
        summary = payload["summaries"][category]
        lines.extend([
            "",
            f"## {category.replace('_', ' ').title()}",
            "",
            f"Queries: {summary['queries']}; summed hits: {summary['sum_of_query_hits']:,}; "
            f"median: {summary['median']:,}; range: {summary['minimum']:,}–{summary['maximum']:,}.",
            "",
            "| Query | Context | Hits |",
            "|---|---|---:|",
        ])
        for row in sorted(rows, key=lambda item: (-item["hit_count"], item["key"])):
            context = " / ".join(row["context"]) if isinstance(row["context"], list) else row["context"]
            lines.append(f"| {row['label']} | {context} | {row['hit_count']:,} |")
    lines.extend([
        "",
        "## Scope notes",
        "",
        "The healthy-volunteer drug–drug interaction trial has no treatment, prevention, "
        "or diagnostic indication and therefore produces no asset–indication queries. Its "
        "verified therapeutic-primary targets remain eligible for target-only discovery.",
        "",
        "The target-only counts use only stored, unambiguous aliases. Protein-family and "
        "complex component membership is reported as provenance but is not expanded into "
        "asserted target aliases. Broad nucleic-acid targets are excluded by policy.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cohort-id", default=DEFAULT_COHORT)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    conn = database_connection()
    try:
        specs = asset_indication_specs(conn, args.cohort_id) + target_specs(conn, args.cohort_id)
    finally:
        conn.close()
    started = time.monotonic()
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(fetch_hit_count, spec) for spec in specs]
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda row: (row["category"], row["key"]))
    payload = {
        "schema_version": "pv.literature-search-policy-pilot/1.0",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "cohort_id": args.cohort_id,
        "elapsed_seconds": round(time.monotonic() - started, 1),
        "results": results,
        "summaries": {
            category: summarize([row for row in results if row["category"] == category])
            for category in ("asset_indication", "target_only")
        },
    }
    rendered_json = json.dumps(payload, indent=2) + "\n"
    rendered_markdown = markdown(payload)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered_json)
    else:
        print(rendered_json)
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(rendered_markdown)


if __name__ == "__main__":
    main()
