"""Retrieve free bibliographic candidates for unresolved trial stoppages."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable


EUROPE_PMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EUROPE_PMC_FULLTEXT_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
USER_AGENT = "predictive-validity-stoppage-source-retrieval/1.0"


def read_jsonl(path: Path) -> Iterable[dict]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc


def fetch_json(url: str, retries: int = 4) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt + 1 == retries:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def atomic_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def query_url(nct_id: str, page_size: int, cursor_mark: str = "*") -> str:
    return EUROPE_PMC_SEARCH_URL + "?" + urllib.parse.urlencode({
        "query": f'"{nct_id}"',
        "format": "json",
        "resultType": "core",
        "pageSize": str(page_size),
        "cursorMark": cursor_mark,
    })


def searchable(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def normalized_candidate(
    nct_id: str, item: dict, rank: int, query: str, trial: dict
) -> dict:
    title = item.get("title") or ""
    abstract = item.get("abstractText") or ""
    metadata_text = f"{title}\n{abstract}".upper()
    normalized_metadata = searchable(metadata_text)
    matched_interventions = []
    for intervention in trial.get("intervention_names") or []:
        normalized = searchable(str(intervention))
        if normalized and normalized != "placebo" and len(normalized) >= 4:
            if normalized in normalized_metadata:
                matched_interventions.append(intervention)
    title_has_trial_language = bool(re.search(
        r"\b(phase\s*[0-9ivx/]+|clinical trial|trial|first[- ]in[- ]human|results?)\b",
        title,
        re.IGNORECASE,
    ))
    exact_metadata = nct_id in metadata_text
    priority_score = (
        100 * int(exact_metadata)
        + 20 * int(bool(matched_interventions))
        + 10 * int(title_has_trial_language)
        + 2 * int(bool(abstract))
    )
    publication_types = item.get("pubTypeList") or {}
    if isinstance(publication_types, dict):
        publication_types = publication_types.get("pubType") or []
    if isinstance(publication_types, str):
        publication_types = [publication_types]
    identifiers = {
        "pmid": item.get("pmid"),
        "pmcid": item.get("pmcid"),
        "doi": item.get("doi"),
    }
    stable = next((f"{key}:{value}" for key, value in identifiers.items() if value), None)
    if stable is None:
        digest = hashlib.sha256(f"{title}|{item.get('firstPublicationDate')}".encode()).hexdigest()[:20]
        stable = f"epmc:{digest}"
    return {
        "candidate_id": stable,
        "nct_id": nct_id,
        "source_family": "europe_pmc",
        "query": query,
        "rank": rank,
        "pmid": item.get("pmid"),
        "pmcid": item.get("pmcid"),
        "doi": item.get("doi"),
        "title": title or None,
        "abstract": abstract or None,
        "journal": item.get("journalTitle"),
        "publication_date": item.get("firstPublicationDate") or item.get("firstIndexDate"),
        "publication_types": publication_types,
        "is_open_access": item.get("isOpenAccess") == "Y",
        "has_full_text": item.get("hasTextMinedTerms") == "Y" or bool(item.get("pmcid")),
        "exact_nct_in_title_or_abstract": exact_metadata,
        "matched_interventions": sorted(set(matched_interventions)),
        "title_has_trial_language": title_has_trial_language,
        "screening_priority_score": priority_score,
        "source_url": (
            f"https://europepmc.org/article/MED/{item['pmid']}" if item.get("pmid")
            else f"https://europepmc.org/article/PMC/{item['pmcid']}" if item.get("pmcid")
            else f"https://doi.org/{item['doi']}" if item.get("doi")
            else None
        ),
        "screening_status": "unscreened",
        "relationship": None,
        "result_bearing": None,
        "exclusion_reason": None,
    }


def search_europe_pmc(args: argparse.Namespace) -> None:
    backlog = list(read_jsonl(args.backlog))
    raw_dir = args.raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)
    candidates: list[dict] = []
    errors: list[dict] = []

    def retrieve_one(trial: dict) -> tuple[list[dict], dict | None]:
        nct_id = trial["nct_id"]
        raw_path = raw_dir / f"{nct_id}.json"
        query = f'"{nct_id}"'
        try:
            if raw_path.exists() and not args.refresh:
                payload = json.loads(raw_path.read_text(encoding="utf-8"))
            else:
                cursor_mark = "*"
                pages = []
                items = []
                hit_count = 0
                retrieval_complete = False
                for page_number in range(1, args.max_pages + 1):
                    page = fetch_json(query_url(nct_id, args.page_size, cursor_mark))
                    pages.append({
                        "page_number": page_number,
                        "cursor_mark": cursor_mark,
                        "result_count": len((page.get("resultList") or {}).get("result") or []),
                    })
                    page_items = (page.get("resultList") or {}).get("result") or []
                    items.extend(page_items)
                    hit_count = int(page.get("hitCount") or len(items))
                    next_cursor = page.get("nextCursorMark")
                    if not page_items or len(items) >= hit_count or not next_cursor or next_cursor == cursor_mark:
                        retrieval_complete = len(items) >= hit_count
                        break
                    cursor_mark = str(next_cursor)
                    time.sleep(args.request_interval)
                payload = {
                    "hitCount": hit_count,
                    "resultList": {"result": items},
                    "_retrieval": {
                        "pages": pages,
                        "pages_retrieved": len(pages),
                        "retrieval_complete": retrieval_complete,
                        "max_pages": args.max_pages,
                    },
                }
                atomic_write_json(raw_path, payload)
                time.sleep(args.request_interval)
            items = ((payload.get("resultList") or {}).get("result") or [])
            retrieval = payload.get("_retrieval") or {}
            hit_count = int(payload.get("hitCount") or len(items))
            retrieval_complete = bool(
                retrieval.get("retrieval_complete", len(items) >= hit_count)
            )
            rows = [
                normalized_candidate(nct_id, item, rank, query, trial)
                for rank, item in enumerate(items, start=1)
            ]
            for row in rows:
                row.update({
                    "search_hit_count": hit_count,
                    "pages_retrieved": int(retrieval.get("pages_retrieved") or 1),
                    "retrieval_complete": retrieval_complete,
                })
            return rows, None
        except (OSError, ValueError, urllib.error.URLError, TimeoutError) as exc:
            return [], {"nct_id": nct_id, "error_type": type(exc).__name__, "error": str(exc)}

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for index, (new_candidates, error) in enumerate(executor.map(retrieve_one, backlog), start=1):
            candidates.extend(new_candidates)
            if error is not None:
                errors.append(error)
            if index % 25 == 0 or index == len(backlog):
                print(
                    f"Europe PMC {index}/{len(backlog)}; candidates={len(candidates)}; "
                    f"errors={len(errors)}",
                    flush=True,
                )

    candidates.sort(key=lambda row: (row["nct_id"], row["rank"], row["candidate_id"]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in candidates:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(args.out)
    errors_path = args.out.with_name(f"{args.out.stem}.errors.jsonl")
    with errors_path.open("w", encoding="utf-8") as handle:
        for row in errors:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    summary = {
        "trials_queried": len(backlog),
        "trials_with_candidates": len({row["nct_id"] for row in candidates}),
        "candidate_count": len(candidates),
        "metadata_exact_nct_count": sum(row["exact_nct_in_title_or_abstract"] for row in candidates),
        "error_count": len(errors),
        "trials_with_truncated_retrieval": len({
            row["nct_id"] for row in candidates if not row.get("retrieval_complete")
        }),
        "source": "Europe PMC REST search API",
    }
    args.out.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


def fulltext_contexts(args: argparse.Namespace) -> None:
    selected = [
        row for row in read_jsonl(args.candidates)
        if row.get("pmcid") and int(row.get("screening_priority_score") or 0) >= args.min_score
    ]
    raw_dir = args.raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)

    def retrieve_one(row: dict) -> dict:
        nct_id = row["nct_id"]
        pmcid = row["pmcid"]
        raw_path = raw_dir / f"{pmcid}.xml"
        try:
            if raw_path.exists() and not args.refresh:
                body = raw_path.read_text(encoding="utf-8")
            else:
                request = urllib.request.Request(
                    EUROPE_PMC_FULLTEXT_URL.format(pmcid=urllib.parse.quote(pmcid)),
                    headers={"User-Agent": USER_AGENT},
                )
                with urllib.request.urlopen(request, timeout=60) as response:
                    body = response.read().decode("utf-8", errors="replace")
                temporary = raw_path.with_suffix(".xml.tmp")
                temporary.write_text(body, encoding="utf-8")
                temporary.replace(raw_path)
                time.sleep(args.request_interval)
            flattened = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))
            positions = [match.start() for match in re.finditer(re.escape(nct_id), flattened, re.I)]
            contexts = [
                flattened[max(0, position - args.context_chars): position + len(nct_id) + args.context_chars]
                for position in positions[: args.max_contexts]
            ]
            return {
                **row,
                "fulltext_exact_nct_match": bool(positions),
                "fulltext_nct_occurrences": len(positions),
                "fulltext_contexts": contexts,
                "fulltext_error": None,
            }
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            return {
                **row,
                "fulltext_exact_nct_match": False,
                "fulltext_nct_occurrences": 0,
                "fulltext_contexts": [],
                "fulltext_error": f"{type(exc).__name__}: {exc}",
            }

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        rows = list(executor.map(retrieve_one, selected))
    rows.sort(key=lambda row: (row["nct_id"], -row["screening_priority_score"], row["candidate_id"]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(args.out)
    summary = {
        "selected_candidates": len(rows),
        "exact_fulltext_matches": sum(row["fulltext_exact_nct_match"] for row in rows),
        "trials_with_exact_fulltext_match": len({
            row["nct_id"] for row in rows if row["fulltext_exact_nct_match"]
        }),
        "errors": sum(bool(row["fulltext_error"]) for row in rows),
        "min_score": args.min_score,
    }
    args.out.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    subparsers = parser.add_subparsers(dest="command", required=True)
    epmc = subparsers.add_parser("europe-pmc")
    epmc.add_argument("--backlog", type=Path, required=True)
    epmc.add_argument("--out", type=Path, required=True)
    epmc.add_argument("--raw-dir", type=Path, required=True)
    epmc.add_argument("--page-size", type=int, default=100)
    epmc.add_argument("--max-pages", type=int, default=100)
    epmc.add_argument("--request-interval", type=float, default=0.1)
    epmc.add_argument("--workers", type=int, default=4)
    epmc.add_argument("--refresh", action="store_true")
    contexts = subparsers.add_parser("fulltext-contexts")
    contexts.add_argument("--candidates", type=Path, required=True)
    contexts.add_argument("--out", type=Path, required=True)
    contexts.add_argument("--raw-dir", type=Path, required=True)
    contexts.add_argument("--min-score", type=int, default=30)
    contexts.add_argument("--context-chars", type=int, default=600)
    contexts.add_argument("--max-contexts", type=int, default=5)
    contexts.add_argument("--request-interval", type=float, default=0.1)
    contexts.add_argument("--workers", type=int, default=4)
    contexts.add_argument("--refresh", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "europe-pmc" and not 1 <= args.page_size <= 1000:
        parser.error("--page-size must be between 1 and 1000")
    if args.command == "europe-pmc" and args.request_interval < 0:
        parser.error("--request-interval cannot be negative")
    if args.command == "europe-pmc" and not 1 <= args.max_pages <= 1000:
        parser.error("--max-pages must be between 1 and 1000")
    if args.command == "europe-pmc" and not 1 <= args.workers <= 16:
        parser.error("--workers must be between 1 and 16")
    if args.command == "fulltext-contexts" and not 1 <= args.workers <= 16:
        parser.error("--workers must be between 1 and 16")
    return args


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)
    if args.command == "europe-pmc":
        search_europe_pmc(args)
    elif args.command == "fulltext-contexts":
        fulltext_contexts(args)


if __name__ == "__main__":
    main()
