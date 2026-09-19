"""Audit a top-N Europe PMC relevance cutoff against the retained asset corpus.

This is a read-only audit.  It requests Europe PMC's default relevance order,
then compares the top N with every already-retained asset-mention candidate in
Neon.  The purpose-oriented text rules are audit probes, not ingestion rules.
They identify papers below the cutoff that deserve human review; they do not
assert that a paper is preclinical evidence.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from pv.ingest.asset_preclinical_literature import load_assets
from pv.ingest.target_phenotype_literature import (
    API_URL,
    canonical_work_key,
    database_connection,
    target_clause,
)


DEFAULT_ASSETS = (
    "azacitidine",
    "choriogonadotropin alfa",
    "pimavanserin",
    "rituximab",
    "salbutamol",
)
USER_AGENT = "predictive-validity-top-n-relevance-audit/1.0"

MODEL_PATTERNS = (
    r"\bpreclinical\b",
    r"\bin vitro\b",
    r"\bin vivo\b",
    r"\bex vivo\b",
    r"\borganoids?\b",
    r"\bpatient[- ]derived\b",
    r"\bxenografts?\b",
    r"\bmouse\b|\bmice\b|\bmurine\b",
    r"\brats?\b",
    r"\banimal models?\b",
    r"\bcell lines?\b|\bcell cultures?\b",
)
ENDPOINT_PATTERNS = (
    r"\bresponses?\b",
    r"\befficacy\b",
    r"\bsensitiv(?:e|ity)\b",
    r"\bresistan(?:t|ce)\b",
    r"\bpharmacodynamic\b",
    r"\bbiomarkers?\b",
    r"\bpredict(?:s|ed|ive|ion)?\b",
    r"\bendpoints?\b",
)
PHENOTYPE_STOPWORDS = {
    "acute", "disease", "disorder", "female", "large", "syndrome", "control",
}


def alias_pattern(alias: str) -> re.Pattern[str]:
    return re.compile(r"(?<![a-z0-9])" + re.escape(alias.lower()) + r"(?![a-z0-9])")


def count_aliases(text: str, aliases: Iterable[str]) -> int:
    lowered = text.lower()
    unique = {alias.strip().lower() for alias in aliases if alias.strip()}
    return sum(len(alias_pattern(alias).findall(lowered)) for alias in unique)


def pattern_hits(text: str, patterns: Iterable[str]) -> int:
    return sum(bool(re.search(pattern, text, re.IGNORECASE)) for pattern in patterns)


def phenotype_match(text: str, phenotype_names: Iterable[str]) -> bool:
    lowered = text.lower()
    for name in phenotype_names:
        name_lower = name.lower()
        if name_lower in lowered:
            return True
        tokens = {
            token for token in re.findall(r"[a-z0-9]+", name_lower)
            if len(token) >= 4 and token not in PHENOTYPE_STOPWORDS
        }
        if tokens and sum(token in lowered for token in tokens) >= min(2, len(tokens)):
            return True
    return False


def fetch_relevance_top(query: str, limit: int) -> tuple[list[dict[str, Any]], int, str]:
    params = {
        "query": query,
        "format": "json",
        "resultType": "core",
        "pageSize": limit,
        "cursorMark": "*",
        "synonym": "false",
        # Deliberately omit sort: Europe PMC's documented default is relevance.
    }
    url = API_URL + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.load(response)
    results = (payload.get("resultList") or {}).get("result") or []
    return results[:limit], int(payload["hitCount"]), url


def corpus_rows(conn: Any, asset_id: str) -> Iterable[dict[str, Any]]:
    cursor = conn.cursor(name=f"top_n_audit_{str(asset_id).replace('-', '')[:20]}")
    cursor.itersize = 2000
    cursor.execute(
        """
        SELECT w.scholarly_work_id,w.canonical_key,w.title,w.abstract_text,
               w.first_publication_date,w.publication_types,w.cited_by_count,
               bool_or(c.candidate_kind='asset_indication_preclinical') AS old_indication_probe,
               bool_or(c.candidate_kind='asset_preclinical_wide') AS old_wide_probe,
               min(o.provider_rank + 1) FILTER (
                 WHERE c.candidate_kind='asset_mention' AND q.query_kind='asset_mention'
               ) AS citation_rank
        FROM pv_evidence.document_relation_candidate c
        JOIN pv_source.scholarly_work w USING (scholarly_work_id)
        LEFT JOIN pv_evidence.document_relation_candidate_observation o
          USING (document_relation_candidate_id)
        LEFT JOIN pv_source.retrieval_query q USING (retrieval_query_id)
        WHERE c.asset_entity_id=%s
          AND c.candidate_kind IN (
            'asset_mention','asset_indication_preclinical','asset_preclinical_wide'
          )
        GROUP BY w.scholarly_work_id,w.canonical_key,w.title,w.abstract_text,
                 w.first_publication_date,w.publication_types,w.cited_by_count
        ORDER BY w.scholarly_work_id
        """,
        (asset_id,),
    )
    # psycopg2 server-side cursors do not populate ``description`` until the
    # first fetch.  Keep the projection explicit so the iterator stays
    # streaming even for broad assets.
    columns = (
        "scholarly_work_id", "canonical_key", "title", "abstract_text",
        "first_publication_date", "publication_types", "cited_by_count",
        "old_indication_probe", "old_wide_probe", "citation_rank",
    )
    try:
        for row in cursor:
            yield dict(zip(columns, row))
    finally:
        cursor.close()


def paper_features(
    row: dict[str, Any], aliases: list[str], phenotype_names: list[str], top_keys: set[str]
) -> dict[str, Any]:
    title = row.get("title") or ""
    abstract = row.get("abstract_text") or ""
    text = f"{title}\n{abstract}"
    title_mentions = count_aliases(title, aliases)
    abstract_mentions = count_aliases(abstract, aliases)
    model_hits = pattern_hits(text, MODEL_PATTERNS)
    endpoint_hits = pattern_hits(text, ENDPOINT_PATTERNS)
    indication = phenotype_match(text, phenotype_names) if phenotype_names else False
    in_top = row["canonical_key"] in top_keys
    strong_probe = bool(
        indication
        and (model_hits or endpoint_hits)
        and (title_mentions or abstract_mentions >= 3)
    )
    review_score = (
        5 * bool(title_mentions)
        + min(abstract_mentions, 5)
        + 4 * indication
        + 2 * bool(model_hits)
        + 2 * bool(endpoint_hits)
        + min(math.log10(1 + (row.get("cited_by_count") or 0)), 3)
    )
    return {
        **row,
        "in_relevance_top_n": in_top,
        "title_mentions": title_mentions,
        "abstract_mentions": abstract_mentions,
        "phenotype_match": indication,
        "model_pattern_groups": model_hits,
        "endpoint_pattern_groups": endpoint_hits,
        "strong_audit_probe": strong_probe,
        "review_score": round(review_score, 3),
    }


def audit_asset(
    conn: Any, asset: tuple[Any, str, Any, list[str]], top_n: int, scan_n: int
) -> dict[str, Any]:
    asset_id, asset_name, phenotypes, aliases = asset
    phenotype_names = [name for _phenotype_id, name in phenotypes]
    query = target_clause(aliases)
    scanned, hit_count, url = fetch_relevance_top(query, scan_n)
    top = scanned[:top_n]
    top_keys = {canonical_work_key(result) for result in top}
    scanned_ranks = {
        canonical_work_key(result): rank for rank, result in enumerate(scanned, 1)
    }
    counts: Counter[str] = Counter()
    below_candidates: list[dict[str, Any]] = []
    matched_top_keys: set[str] = set()
    for row in corpus_rows(conn, str(asset_id)):
        features = paper_features(row, aliases, phenotype_names, top_keys)
        if features["in_relevance_top_n"]:
            matched_top_keys.add(row["canonical_key"])
            counts["corpus_top_n"] += 1
            if features["strong_audit_probe"]:
                counts["strong_probe_top_n"] += 1
        else:
            counts["corpus_below_top_n"] += 1
            if features["old_indication_probe"]:
                counts["old_indication_probe_below_top_n"] += 1
            if features["strong_audit_probe"]:
                counts["strong_probe_below_top_n"] += 1
                below_candidates.append(features)
    below_candidates.sort(
        key=lambda row: (
            -row["review_score"],
            -(row.get("cited_by_count") or 0),
            row["scholarly_work_id"],
        )
    )
    top_summary = []
    top_years: Counter[int] = Counter()
    for rank, result in enumerate(top, 1):
        publication_date = result.get("firstPublicationDate") or ""
        match = re.match(r"^(\d{4})", publication_date)
        if match:
            top_years[int(match.group(1))] += 1
        top_summary.append({
            "rank": rank,
            "canonical_key": canonical_work_key(result),
            "title": result.get("title"),
            "pmid": result.get("pmid"),
            "pmcid": result.get("pmcid"),
            "doi": result.get("doi"),
            "cited_by_count": result.get("citedByCount"),
            "first_publication_date": publication_date or None,
        })
    return {
        "asset_id": str(asset_id),
        "asset": asset_name,
        "aliases": aliases,
        "phenotypes": phenotype_names,
        "query": query,
        "request_url": url,
        "sort": "Europe PMC default relevance (sort parameter omitted)",
        "provider_hit_count": hit_count,
        "requested_top_n": top_n,
        "returned_top_n": len(top),
        "top_n_found_in_retained_corpus": len(matched_top_keys),
        "top_n_publication_years": dict(sorted(top_years.items())),
        "counts": dict(counts),
        "top_results": top_summary,
        "highest_priority_below_cutoff": [
            {
                key: row.get(key) for key in (
                    "canonical_key", "title", "first_publication_date",
                    "publication_types", "cited_by_count",
                    "title_mentions", "abstract_mentions", "phenotype_match",
                    "model_pattern_groups", "endpoint_pattern_groups",
                    "old_indication_probe", "old_wide_probe", "citation_rank",
                    "review_score",
                )
            } | {"relevance_rank_if_scanned": scanned_ranks.get(row["canonical_key"])}
            for row in below_candidates[:25]
        ],
    }


def markdown_report(payload: dict[str, Any]) -> str:
    top_n = payload["top_n"]
    lines = [
        f"# Europe PMC top-{top_n} relevance cutoff audit",
        "",
        f"Retrieved: {payload['retrieved_at']}",
        "",
        "This is a read-only cutoff audit. Europe PMC's `sort` parameter was omitted, "
        "so the provider's default relevance order was used. The comparator is the "
        "complete asset-mention corpus already retained in Neon. Text rules are only "
        "review probes and are not evidence labels or ingestion filters.",
        "",
        "| Asset | Provider hits | Top publication-year span | Strong probes in top | Strong probes below | Old indication-query papers below |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for asset in payload["assets"]:
        counts = asset["counts"]
        years = list(asset["top_n_publication_years"])
        year_span = f"{min(years)}–{max(years)}" if years else "unknown"
        lines.append(
            f"| {asset['asset']} | {asset['provider_hit_count']:,} | {year_span} | "
            f"{counts.get('strong_probe_top_n', 0):,} | "
            f"{counts.get('strong_probe_below_top_n', 0):,} | "
            f"{counts.get('old_indication_probe_below_top_n', 0):,} |"
        )
    truncated_with_probes = [
        asset["asset"] for asset in payload["assets"]
        if asset["provider_hit_count"] > top_n
        and asset["counts"].get("strong_probe_below_top_n", 0) > 0
    ]
    no_truncation = [
        asset["asset"] for asset in payload["assets"]
        if asset["provider_hit_count"] <= top_n
    ]
    lines.extend(["", "## Cutoff result", ""])
    if truncated_with_probes:
        lines.append(
            "The hard provider-relevance cutoff is not cleared by this audit for "
            + ", ".join(truncated_with_probes)
            + ": the retained full corpus contains purpose-oriented review probes "
              "outside the cutoff. These require manual adjudication before the "
              "cutoff can be accepted or rejected."
        )
    if no_truncation:
        lines.append(
            "The cutoff does not truncate " + ", ".join(no_truncation)
            + " because the complete provider result set is at most 100."
        )
    for asset in payload["assets"]:
        lines.extend(["", f"## {asset['asset']}", ""])
        lines.append(
            f"Phenotype context: {', '.join(asset['phenotypes']) or '(none)'}. "
            f"Europe PMC reported {asset['provider_hit_count']:,} matches."
        )
        lines.extend(["", "Highest-priority audit probes below the cutoff:", ""])
        candidates = asset["highest_priority_below_cutoff"][:10]
        if not candidates:
            lines.append("No paper met the strong audit-probe rule below the cutoff.")
        for candidate in candidates:
            flags = (
                f"title mentions={candidate['title_mentions']}; "
                f"abstract mentions={candidate['abstract_mentions']}; "
                f"model groups={candidate['model_pattern_groups']}; "
                f"endpoint groups={candidate['endpoint_pattern_groups']}; "
                f"citations={candidate['cited_by_count'] or 0}; "
                f"citation rank={candidate['citation_rank'] or 'unavailable'}; "
                f"relevance rank within scan={candidate['relevance_rank_if_scanned'] or 'not in scan'}"
            )
            lines.append(
                f"- {candidate['title']}\n  `{candidate['canonical_key']}`; "
                f"published={candidate['first_publication_date'] or 'unknown'}; {flags}"
            )
    lines.extend([
        "",
        "## Interpretation limits",
        "",
        "The audit can show that a hard cutoff loses plausible papers. It cannot measure "
        "true recall because the retained corpus has not been exhaustively relevance-labeled. "
        "A final cutoff decision therefore needs manual review of the below-cutoff probes and "
        "a pinned-sentinel exception for known important papers.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--asset", action="append", dest="assets")
    parser.add_argument("--top-n", type=int, default=100)
    parser.add_argument(
        "--scan-n", type=int, default=1000,
        help="provider-ranked prefix used to locate below-cutoff audit probes",
    )
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    if args.top_n < 1 or args.top_n > 1000:
        raise SystemExit("--top-n must be between 1 and 1000")
    if args.scan_n < args.top_n or args.scan_n > 1000:
        raise SystemExit("--scan-n must be between --top-n and 1000")
    requested = set(args.assets or DEFAULT_ASSETS)
    conn = database_connection()
    try:
        available = {asset[1]: asset for asset in load_assets(conn, None)}
        missing = requested - available.keys()
        if missing:
            raise SystemExit(f"Unknown pilot assets: {', '.join(sorted(missing))}")
        reports = [
            audit_asset(conn, available[name], args.top_n, args.scan_n)
            for name in sorted(requested)
        ]
    finally:
        conn.close()
    payload = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "top_n": args.top_n,
        "scan_n": args.scan_n,
        "assets": reports,
    }
    rendered_json = json.dumps(payload, indent=2, default=str) + "\n"
    rendered_markdown = markdown_report(payload)
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
