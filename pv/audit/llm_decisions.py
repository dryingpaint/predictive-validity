"""Compare canonical decisions from two stored LLM enrichment runs."""
from __future__ import annotations

import argparse
import json
import os
import uuid
from collections import Counter
from typing import Any

import psycopg2


def json_diff(before: Any, after: Any, path: str = "$") -> list[dict[str, Any]]:
    """Return deterministic, decision-focused JSON differences."""
    if type(before) is not type(after):
        return [{"path": path, "before": before, "after": after}]
    if isinstance(before, dict):
        changes: list[dict[str, Any]] = []
        for key in sorted(set(before) | set(after)):
            child = f"{path}.{key}"
            if key not in before:
                changes.append({"path": child, "before": None, "after": after[key]})
            elif key not in after:
                changes.append({"path": child, "before": before[key], "after": None})
            else:
                changes.extend(json_diff(before[key], after[key], child))
        return changes
    if isinstance(before, list):
        if before == after:
            return []
        return [{"path": path, "before": before, "after": after}]
    if before != after:
        return [{"path": path, "before": before, "after": after}]
    return []


def run_metadata(cur: Any, run_id: uuid.UUID) -> tuple[str, str]:
    cur.execute(
        """
        SELECT task, status
        FROM pv_evidence.llm_decision_run
        WHERE decision_run_id = %s
        """,
        (str(run_id),),
    )
    row = cur.fetchone()
    if row is None:
        raise SystemExit(f"Unknown decision run: {run_id}")
    return row[0], row[1]


def resolve_comparison_run(cur: Any, current_run: uuid.UUID, value: str) -> uuid.UUID:
    current_task, _ = run_metadata(cur, current_run)
    if value != "latest":
        try:
            candidate = uuid.UUID(value)
        except ValueError as exc:
            raise SystemExit("--compare-decisions-to must be 'latest' or a UUID") from exc
        comparison_task, _ = run_metadata(cur, candidate)
        if comparison_task != current_task:
            raise SystemExit(
                f"Run task mismatch: current={current_task!r}, comparison={comparison_task!r}"
            )
        return candidate
    cur.execute(
        """
        SELECT prior.decision_run_id
        FROM pv_evidence.llm_decision_run current
        JOIN pv_evidence.llm_decision_run prior
          ON prior.task = current.task
         AND prior.decision_run_id <> current.decision_run_id
         AND prior.status = 'completed'
         AND prior.started_at < current.started_at
        WHERE current.decision_run_id = %s
        ORDER BY prior.started_at DESC, prior.decision_run_id DESC
        LIMIT 1
        """,
        (str(current_run),),
    )
    row = cur.fetchone()
    if row is None:
        raise SystemExit(f"No earlier completed run exists for task {current_task!r}")
    return row[0]


def compare(cur: Any, current_run: uuid.UUID, prior_run: uuid.UUID) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT COALESCE(current.task, prior.task) AS task,
               COALESCE(current.subject_type, prior.subject_type) AS subject_type,
               COALESCE(current.subject_key, prior.subject_key) AS subject_key,
               current.llm_decision_id,
               prior.llm_decision_id,
               current.decision_sha256,
               prior.decision_sha256,
               current.canonical_decision,
               prior.canonical_decision
        FROM (
          SELECT * FROM pv_evidence.llm_decision WHERE decision_run_id = %s
        ) current
        FULL OUTER JOIN (
          SELECT * FROM pv_evidence.llm_decision WHERE decision_run_id = %s
        ) prior
          ON current.task = prior.task
         AND current.subject_type = prior.subject_type
         AND current.subject_key = prior.subject_key
        ORDER BY 1, 2, 3
        """,
        (str(current_run), str(prior_run)),
    )
    results = []
    for row in cur.fetchall():
        (
            task, subject_type, subject_key, current_id, prior_id,
            current_hash, prior_hash, current_value, prior_value,
        ) = row
        if prior_id is None:
            status = "added"
        elif current_id is None:
            status = "removed"
        elif current_hash == prior_hash:
            status = "unchanged"
        else:
            status = "changed"
        results.append(
            {
                "task": task,
                "subject_type": subject_type,
                "subject_key": subject_key,
                "change_status": status,
                "current_decision_id": current_id,
                "prior_decision_id": prior_id,
                "field_diff": (
                    json_diff(prior_value, current_value) if status == "changed" else []
                ),
            }
        )
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=uuid.UUID)
    parser.add_argument(
        "--compare-decisions-to",
        required=True,
        help="Earlier decision-run UUID, or 'latest'",
    )
    parser.add_argument("--show-unchanged", action="store_true")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            prior_run = resolve_comparison_run(
                cur, args.run, args.compare_decisions_to
            )
            results = compare(cur, args.run, prior_run)
    finally:
        conn.close()

    counts = Counter(row["change_status"] for row in results)
    payload = {
        "current_run_id": str(args.run),
        "compare_to_run_id": str(prior_run),
        "counts": {
            status: counts.get(status, 0)
            for status in ("added", "removed", "changed", "unchanged")
        },
        "decisions": [
            row for row in results
            if args.show_unchanged or row["change_status"] != "unchanged"
        ],
    }
    if args.json:
        print(json.dumps(payload, sort_keys=True, indent=2, default=str))
        return
    print(f"current={args.run} compare_to={prior_run}")
    print(" ".join(f"{key}={value}" for key, value in payload["counts"].items()))
    for row in payload["decisions"]:
        print(
            f"{row['change_status']:9} {row['task']} "
            f"{row['subject_type']}:{row['subject_key']}"
        )
        for change in row["field_diff"]:
            print(f"  {change['path']}: {change['before']!r} -> {change['after']!r}")


if __name__ == "__main__":
    main()
