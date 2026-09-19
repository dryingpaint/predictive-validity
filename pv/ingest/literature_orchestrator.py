"""Plan, run, recover, and audit durable literature-retrieval work items."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json


DEFAULT_COHORT = "pv_2015_actual_completed_drug_biological_pilot5_v1"
POLICY_VERSION = "human_therapeutics_v2"
LITERATURE_POLICY_VERSION = "pv_literature_v2"
ACTIVE_WORK_KINDS = ("asset_indication", "effective_target")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def work_key(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def connect() -> Any:
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    return psycopg2.connect(os.environ["DATABASE_URL"])


def plan(cohort_id: str, commit: bool) -> dict[str, int]:
    """Plan only the two provider-query families in the active policy."""
    planned = {"asset_indication": 0, "effective_target": 0}
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT DISTINCT asset.entity_id,asset.active_moiety_name,
                              phenotype.entity_id,phenotype.preferred_name
               FROM pv_core.v_asset_indication_literature_scope scope
               JOIN pv_core.trial_cohort_member cm ON cm.nct_id=scope.nct_id
               JOIN pv_core.asset asset ON asset.entity_id=scope.asset_entity_id
               JOIN pv_core.phenotype phenotype
                 ON phenotype.entity_id=scope.phenotype_entity_id
               WHERE cm.cohort_id=%s AND cm.membership_status='included'
                 AND scope.policy_version=%s
               ORDER BY asset.active_moiety_name,phenotype.preferred_name""",
            (cohort_id, POLICY_VERSION),
        )
        asset_indication_rows = cur.fetchall()
        cur.execute(
            """SELECT DISTINCT assertion.asset_target_assertion_id,
                              target.entity_id,
                              coalesce(nullif(target.approved_symbol,''),target.approved_name),
                              context.asset_target_context_assertion_id,
                              context.context_type,context.context_name
               FROM pv_core.v_target_phenotype_literature_scope scope
               JOIN pv_core.trial_cohort_member cm ON cm.nct_id=scope.nct_id
               JOIN pv_evidence.asset_target_assertion assertion
                 ON assertion.asset_entity_id=scope.asset_entity_id
                AND assertion.target_entity_id=scope.target_entity_id
                AND assertion.role='therapeutic_primary'
               JOIN pv_core.target target ON target.entity_id=scope.target_entity_id
               LEFT JOIN pv_evidence.v_latest_asset_target_context context
                 ON context.asset_target_assertion_id=assertion.asset_target_assertion_id
                AND context.search_eligible=true
                AND context.verification_status='exact_source_span'
               WHERE cm.cohort_id=%s AND cm.membership_status='included'
                 AND scope.policy_version=%s
               ORDER BY assertion.asset_target_assertion_id,context.context_type,
                        context.context_name""",
            (cohort_id, POLICY_VERSION),
        )
        context_rows = cur.fetchall()

        for asset_id, asset, phenotype_id, phenotype in asset_indication_rows:
            identity = {
                "cohort_id": cohort_id, "policy_version": POLICY_VERSION,
                "literature_policy_version": LITERATURE_POLICY_VERSION,
                "work_kind": "asset_indication", "asset_entity_id": str(asset_id),
                "phenotype_entity_id": str(phenotype_id),
            }
            if commit:
                cur.execute(
                    """INSERT INTO pv_source.literature_work_item
                         (work_key,cohort_id,policy_version,work_kind,asset_entity_id,
                          phenotype_entity_id,arguments)
                       VALUES (%s,%s,%s,'asset_indication',%s,%s,%s)
                       ON CONFLICT (work_key) DO UPDATE SET
                         arguments=EXCLUDED.arguments,updated_at=now()
                       WHERE pv_source.literature_work_item.arguments
                         IS DISTINCT FROM EXCLUDED.arguments""",
                    (work_key(identity), cohort_id, POLICY_VERSION, str(asset_id),
                     str(phenotype_id), Json({
                         "literature_policy_version": LITERATURE_POLICY_VERSION,
                         "asset_id": str(asset_id), "asset": asset,
                         "phenotype_id": str(phenotype_id), "phenotype": phenotype,
                     })),
                )
                planned["asset_indication"] += cur.rowcount
            else:
                planned["asset_indication"] += 1

        grouped: dict[tuple[Any, str, int], list[tuple[int, str, str]]] = {}
        for assertion_id, target_id, target, context_id, context_type, context_name in context_rows:
            key = (target_id, target, assertion_id)
            grouped.setdefault(key, [])
            if context_id is not None:
                grouped[key].append((context_id, context_type, context_name))
        effective_subjects: dict[
            tuple[str, tuple[tuple[str, str], ...]], dict[str, Any]
        ] = {}
        for (target_id, target, _assertion_id), contexts in grouped.items():
            signature = tuple(sorted({
                (row[1], row[2].strip().casefold()) for row in contexts
            }))
            dedupe_key = (str(target_id), signature)
            subject = effective_subjects.setdefault(dedupe_key, {
                "target_id": str(target_id), "target": target,
                "context_ids": [], "contexts": [],
            })
            known_ids = set(subject["context_ids"])
            for context_id, context_type, context_name in contexts:
                if context_id not in known_ids:
                    subject["context_ids"].append(context_id)
                    subject["contexts"].append({
                        "id": context_id, "type": context_type, "name": context_name,
                    })
                    known_ids.add(context_id)
            subject["context_ids"].sort()
            subject["contexts"].sort(key=lambda row: (row["type"], row["name"], row["id"]))

        for (target_id, context_signature), arguments in sorted(effective_subjects.items()):
            identity = {
                "cohort_id": cohort_id, "policy_version": POLICY_VERSION,
                "literature_policy_version": LITERATURE_POLICY_VERSION,
                "work_kind": "effective_target", "target_entity_id": target_id,
                "context_ids": arguments["context_ids"],
            }
            arguments["literature_policy_version"] = LITERATURE_POLICY_VERSION
            if commit:
                cur.execute(
                    """INSERT INTO pv_source.literature_work_item
                         (work_key,cohort_id,policy_version,work_kind,target_entity_id,arguments)
                       VALUES (%s,%s,%s,'effective_target',%s,%s)
                       ON CONFLICT (work_key) DO UPDATE SET
                         arguments=EXCLUDED.arguments,updated_at=now()
                       WHERE pv_source.literature_work_item.arguments
                         IS DISTINCT FROM EXCLUDED.arguments""",
                    (work_key(identity), cohort_id, POLICY_VERSION, target_id,
                     Json(arguments)),
                )
                planned["effective_target"] += cur.rowcount
            else:
                planned["effective_target"] += 1
        if not commit:
            conn.rollback()
    return planned


def claim(conn: Any, cohort_id: str) -> tuple[Any, ...] | None:
    token = uuid.uuid4()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT literature_work_item_id,work_kind,arguments,attempt_count
               FROM pv_source.literature_work_item
               WHERE cohort_id=%s AND status IN ('pending','failed')
                 AND work_kind=ANY(%s)
               ORDER BY CASE status WHEN 'pending' THEN 0 ELSE 1 END,
                        literature_work_item_id
               FOR UPDATE SKIP LOCKED LIMIT 1""",
            (cohort_id, list(ACTIVE_WORK_KINDS)),
        )
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return None
        item_id, kind, arguments, attempts = row
        attempt_number = attempts + 1
        now = datetime.now(timezone.utc)
        cur.execute(
            """UPDATE pv_source.literature_work_item SET status='running',attempt_count=%s,
                 lease_token=%s,leased_at=%s,last_error=NULL,updated_at=%s
               WHERE literature_work_item_id=%s""",
            (attempt_number, str(token), now, now, item_id),
        )
        cur.execute(
            """INSERT INTO pv_source.literature_work_attempt
                 (literature_work_item_id,lease_token,attempt_number,status,started_at)
               VALUES (%s,%s,%s,'running',%s)""",
            (item_id, str(token), attempt_number, now),
        )
    conn.commit()
    return item_id, kind, arguments, token, attempt_number, now


def command(kind: str, arguments: dict[str, Any]) -> list[str]:
    if kind == "asset_indication":
        return [sys.executable, "-m", "pv.ingest.asset_indication_literature",
                "--asset-id", arguments["asset_id"],
                "--phenotype-id", arguments["phenotype_id"], "--commit"]
    if kind == "effective_target":
        return [sys.executable, "-m", "pv.ingest.effective_target_literature",
                "--target-id", arguments["target_id"],
                "--context-ids", ",".join(str(value) for value in arguments["context_ids"]),
                "--commit"]
    if kind == "target_phenotype":
        return [sys.executable, "-m", "pv.ingest.target_phenotype_literature",
                "--target-id", arguments["target_id"],
                "--phenotype", arguments["phenotype"], "--commit"]
    if kind == "asset_mention":
        return [sys.executable, "-m", "pv.ingest.asset_mention_literature",
                "--asset", arguments["asset"], "--commit"]
    return [sys.executable, "-m", "pv.ingest.asset_preclinical_literature",
            "--asset", arguments["asset"], "--commit"]


def acquisition_runs(cur: Any, kind: str, started_at: datetime) -> list[uuid.UUID]:
    adapter = {
        "asset_indication": "pv.ingest.asset_indication_literature",
        "effective_target": "pv.ingest.effective_target_literature",
        "target_phenotype": "pv.ingest.target_phenotype_literature",
        "asset_preclinical": "pv.ingest.asset_preclinical_literature",
        "asset_mention": "pv.ingest.asset_mention_literature",
    }[kind]
    cur.execute(
        """SELECT acquisition_run_id FROM pv_source.acquisition_run
           WHERE adapter=%s AND started_at >= %s ORDER BY started_at""",
        (adapter, started_at),
    )
    return [row[0] for row in cur.fetchall()]


def finish(conn: Any, claimed: tuple[Any, ...], result: subprocess.CompletedProcess[str]) -> None:
    item_id, kind, _arguments, token, _attempt_number, started_at = claimed
    status = "completed" if result.returncode == 0 else "failed"
    now = datetime.now(timezone.utc)
    stdout = result.stdout[-12000:]
    stderr = result.stderr[-12000:]
    error = None if result.returncode == 0 else f"exit_code={result.returncode}"
    with conn.cursor() as cur:
        runs = acquisition_runs(cur, kind, started_at)
        cur.execute(
            """UPDATE pv_source.literature_work_attempt
               SET status=%s,completed_at=%s,acquisition_run_ids=%s::uuid[],
                   stdout_tail=%s,stderr_tail=%s,error_summary=%s
               WHERE lease_token=%s""",
            (status, now, runs, stdout, stderr, error, str(token)),
        )
        cur.execute(
            """UPDATE pv_source.literature_work_item
               SET status=%s,lease_token=NULL,leased_at=NULL,
                   completed_at=CASE WHEN %s='completed' THEN %s ELSE completed_at END,
                   last_error=%s,updated_at=%s
               WHERE literature_work_item_id=%s AND lease_token=%s""",
            (status, status, now, error or None, now, item_id, str(token)),
        )
    conn.commit()


def execute_with_heartbeat(
    conn: Any, claimed: tuple[Any, ...], heartbeat_seconds: int = 30
) -> subprocess.CompletedProcess[str]:
    """Run one adapter while renewing its durable lease."""
    item_id, kind, arguments, token, _attempt_number, _started_at = claimed
    process = subprocess.Popen(
        command(kind, arguments), cwd=os.getcwd(), stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )
    while True:
        try:
            stdout, stderr = process.communicate(timeout=heartbeat_seconds)
            return subprocess.CompletedProcess(
                process.args, process.returncode, stdout=stdout, stderr=stderr
            )
        except subprocess.TimeoutExpired:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE pv_source.literature_work_item
                       SET leased_at=now(),updated_at=now()
                       WHERE literature_work_item_id=%s AND lease_token=%s
                         AND status='running'""",
                    (item_id, str(token)),
                )
            conn.commit()


def run(cohort_id: str, max_jobs: int) -> dict[str, int]:
    counts = {"completed": 0, "failed": 0}
    conn = connect()
    try:
        for _ in range(max_jobs):
            claimed = claim(conn, cohort_id)
            if not claimed:
                break
            result = execute_with_heartbeat(conn, claimed)
            finish(conn, claimed, result)
            counts["completed" if result.returncode == 0 else "failed"] += 1
    finally:
        conn.close()
    return counts


def recover(cohort_id: str, older_than_minutes: int, commit: bool) -> int:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT literature_work_item_id,lease_token FROM pv_source.literature_work_item
               WHERE cohort_id=%s AND status='running'
                 AND work_kind=ANY(%s)
                 AND leased_at < now()-(%s * interval '1 minute')
               FOR UPDATE""",
            (cohort_id, list(ACTIVE_WORK_KINDS), older_than_minutes),
        )
        rows = cur.fetchall()
        if commit:
            for item_id, token in rows:
                cur.execute(
                    """UPDATE pv_source.literature_work_attempt
                       SET status='interrupted',completed_at=now(),
                           error_summary='stale lease recovered'
                       WHERE lease_token=%s AND status='running'""", (str(token),),
                )
                cur.execute(
                    """UPDATE pv_source.literature_work_item SET status='pending',
                         lease_token=NULL,leased_at=NULL,last_error='stale lease recovered',
                         updated_at=now() WHERE literature_work_item_id=%s""", (item_id,),
                )
        else:
            conn.rollback()
    return len(rows)


def audit(cohort_id: str) -> dict[str, Any]:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT status,count(*) FROM pv_source.literature_work_item
               WHERE cohort_id=%s AND work_kind=ANY(%s)
               GROUP BY status ORDER BY status""",
            (cohort_id, list(ACTIVE_WORK_KINDS)),
        )
        statuses = dict(cur.fetchall())
        cur.execute(
            """SELECT count(*)-count(DISTINCT work_key)
               FROM pv_source.literature_work_item
               WHERE cohort_id=%s AND work_kind=ANY(%s)""",
            (cohort_id, list(ACTIVE_WORK_KINDS)),
        )
        duplicate_work = cur.fetchone()[0]
        cur.execute(
            """SELECT count(*) FROM (
                 SELECT scholarly_work_id,target_entity_id,phenotype_entity_id,
                        mechanism_entity_id,asset_entity_id,candidate_kind,count(*)
                 FROM pv_evidence.document_relation_candidate GROUP BY 1,2,3,4,5,6
                 HAVING count(*)>1
               ) d"""
        )
        duplicate_candidates = cur.fetchone()[0]
        cur.execute(
            """SELECT count(*) FROM pv_source.literature_work_item
               WHERE cohort_id=%s AND status='running'
                 AND work_kind=ANY(%s)
                 AND leased_at < now()-interval '60 minutes'""",
            (cohort_id, list(ACTIVE_WORK_KINDS)),
        )
        stale = cur.fetchone()[0]
        cur.execute(
            """SELECT stream_status,count(*)
               FROM pv_source.retrieval_query
               WHERE query_kind IN ('asset_indication_v2','effective_target_only_v1')
               GROUP BY stream_status ORDER BY stream_status"""
        )
        stream_statuses = dict(cur.fetchall())
    return {"literature_policy_version": LITERATURE_POLICY_VERSION,
            "statuses": statuses, "stream_statuses": stream_statuses,
            "duplicate_work_keys": duplicate_work,
            "duplicate_canonical_candidates": duplicate_candidates,
            "stale_running_leases": stale}


def validate_resume(cohort_id: str, commit: bool) -> dict[str, Any]:
    """Simulate one interrupted lease and prove it returns to pending."""
    if not commit:
        return {"committed": False, "message": "pass --commit to record the simulated interrupted attempt"}
    conn = connect()
    try:
        claimed = claim(conn, cohort_id)
        if not claimed:
            raise RuntimeError("No pending or failed work item is available for resume validation")
        item_id, _kind, _arguments, token, attempt_number, _started = claimed
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE pv_source.literature_work_item
                   SET leased_at=now()-interval '2 hours' WHERE literature_work_item_id=%s""",
                (item_id,),
            )
            cur.execute(
                """UPDATE pv_source.literature_work_attempt
                   SET started_at=now()-interval '2 hours' WHERE lease_token=%s""",
                (str(token),),
            )
        conn.commit()
    finally:
        conn.close()
    recovered = recover(cohort_id, 60, True)
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT w.status,a.status,a.error_summary
               FROM pv_source.literature_work_item w
               JOIN pv_source.literature_work_attempt a USING(literature_work_item_id)
               WHERE w.literature_work_item_id=%s AND a.lease_token=%s""",
            (item_id, str(token)),
        )
        state = cur.fetchone()
    passed = recovered >= 1 and state == ("pending", "interrupted", "stale lease recovered")
    return {"committed": True, "passed": passed, "work_item_id": item_id,
            "attempt_number": attempt_number, "recovered_count": recovered,
            "final_state": state}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cohort-id", default=DEFAULT_COHORT)
    sub = parser.add_subparsers(dest="action", required=True)
    plan_parser = sub.add_parser("plan")
    plan_parser.add_argument("--commit", action="store_true")
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--max-jobs", type=int, default=1)
    recover_parser = sub.add_parser("recover-stale")
    recover_parser.add_argument("--older-than-minutes", type=int, default=60)
    recover_parser.add_argument("--commit", action="store_true")
    validate_parser = sub.add_parser("validate-resume")
    validate_parser.add_argument("--commit", action="store_true")
    sub.add_parser("audit")
    args = parser.parse_args()
    if args.action == "plan":
        result = plan(args.cohort_id, args.commit)
    elif args.action == "run":
        if args.max_jobs < 1:
            raise SystemExit("--max-jobs must be positive")
        result = run(args.cohort_id, args.max_jobs)
    elif args.action == "recover-stale":
        result = {"recovered": recover(args.cohort_id, args.older_than_minutes, args.commit)}
    elif args.action == "validate-resume":
        result = validate_resume(args.cohort_id, args.commit)
    else:
        result = audit(args.cohort_id)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
