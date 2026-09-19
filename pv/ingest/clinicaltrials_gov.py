"""Discover and ingest a reproducible ClinicalTrials.gov completion-date cohort.

The command defaults to a dry run. Pass ``--commit`` to write the immutable raw
records and normalized trial/intervention projection to the PV schemas.

An "ended in a date range" cohort uses an ACTUAL Study Completion Date. It does
not use registration, first-posted, start, or primary-completion date. The
development cohort is restricted to interventional studies with at least one
registry intervention typed DRUG or BIOLOGICAL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
from calendar import monthrange
from datetime import date, datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json


API_BASE = "https://clinicaltrials.gov/api/v2/studies"
SOURCE_SYSTEM_ID = "clinicaltrials_gov"
ADAPTER = "pv.ingest.clinicaltrials_gov"
ADAPTER_VERSION = "1.3.0"
USER_AGENT = "predictive-validity-canonical-ingest/1.0"
NCT_RE = re.compile(r"^NCT[0-9]{8}$")


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def comparison_form(value: str) -> str:
    """Return a non-destructive comparison key; never use it as identity."""
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\u2018", "'").replace("\u2019", "'")
    value = value.replace("\u201c", '"').replace("\u201d", '"')
    value = value.replace("\u2013", "-").replace("\u2014", "-")
    return " ".join(value.casefold().split())


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return None
    return date.fromisoformat(value)


def partial_date_bounds(value: str | None) -> tuple[date, date, str] | None:
    """Return lower/upper bounds without fabricating precision."""
    if not value:
        return None
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        parsed = date.fromisoformat(value)
        return parsed, parsed, "day"
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}", value):
        year, month = map(int, value.split("-"))
        return date(year, month, 1), date(year, month, monthrange(year, month)[1]), "month"
    if re.fullmatch(r"[0-9]{4}", value):
        year = int(value)
        return date(year, 1, 1), date(year, 12, 31), "year"
    return None


def git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", value) else None


def request_bytes(url: str, attempts: int = 5) -> bytes:
    transient = {429, 500, 502, 503, 504}
    for attempt in range(attempts):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in transient or attempt + 1 == attempts:
                raise
            retry_after = exc.headers.get("Retry-After")
            try:
                wait = float(retry_after) if retry_after else 2**attempt
            except ValueError:
                wait = 2**attempt
            time.sleep(min(wait, 30))
        except (urllib.error.URLError, TimeoutError):
            if attempt + 1 == attempts:
                raise
            time.sleep(min(2**attempt, 30))
    raise AssertionError("unreachable")


def api_url(params: dict[str, Any]) -> str:
    return f"{API_BASE}?{urllib.parse.urlencode(params)}"


def query_expression(from_date: date, through_date: date) -> str:
    return (
        "AREA[CompletionDate]RANGE["
        f"{from_date.strftime('%m/%d/%Y')}, {through_date.strftime('%m/%d/%Y')}] "
        "AND AREA[CompletionDateType]ACTUAL "
        "AND AREA[StudyType]INTERVENTIONAL "
        "AND (AREA[InterventionType]DRUG OR AREA[InterventionType]BIOLOGICAL)"
    )


def discover_inventory(from_date: date, through_date: date) -> tuple[list[dict[str, str]], int, dict[str, Any]]:
    """Retrieve the complete ID/date inventory, then sort it deterministically."""
    expression = query_expression(from_date, through_date)
    common = {
        "query.term": expression,
        "pageSize": 1000,
        "countTotal": "true",
        "format": "json",
        "fields": "NCTId,CompletionDate,CompletionDateType",
        "sort": "CompletionDate:asc",
    }
    page_token: str | None = None
    expected_total: int | None = None
    rows: list[dict[str, str]] = []
    while True:
        params = dict(common)
        if page_token:
            params["pageToken"] = page_token
        payload = json.loads(request_bytes(api_url(params)))
        if expected_total is None:
            expected_total = int(payload["totalCount"])
        elif int(payload.get("totalCount", expected_total)) != expected_total:
            raise RuntimeError("ClinicalTrials.gov totalCount changed during discovery")
        for study in payload.get("studies", []):
            protocol = study.get("protocolSection") or {}
            nct_id = (protocol.get("identificationModule") or {}).get("nctId")
            completion = (
                (protocol.get("statusModule") or {}).get("completionDateStruct") or {}
            )
            completion_date = completion.get("date")
            completion_type = completion.get("type")
            if not nct_id or not completion_date or completion_type != "ACTUAL":
                raise RuntimeError(
                    "Discovery result lacks NCTId or an ACTUAL CompletionDate"
                )
            if not NCT_RE.fullmatch(nct_id):
                raise RuntimeError(f"Invalid NCT ID returned by source: {nct_id!r}")
            bounds = partial_date_bounds(completion_date)
            if bounds is None:
                raise RuntimeError(
                    f"Invalid completion date returned: {nct_id} {completion_date}"
                )
            lower, upper, precision = bounds
            rows.append({
                "nct_id": nct_id,
                "completion_date_text": completion_date,
                "completion_date_type": completion_type,
                "completion_date_precision": precision,
                "completion_date_lower_bound": lower.isoformat(),
                "completion_date_upper_bound": upper.isoformat(),
            })
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
    precision_order = {"day": 0, "month": 1, "year": 2}
    rows.sort(key=lambda row: (
        row["completion_date_lower_bound"],
        precision_order[row["completion_date_precision"]],
        row["nct_id"],
    ))
    if expected_total is None or len(rows) != expected_total:
        raise RuntimeError(
            f"Inventory mismatch: API reported {expected_total}, received {len(rows)}"
        )
    if len({row["nct_id"] for row in rows}) != len(rows):
        raise RuntimeError("ClinicalTrials.gov inventory contains duplicate NCT IDs")
    return rows, expected_total, common


def discover_selected(nct_ids: list[str]) -> tuple[list[dict[str, str]], int, dict[str, Any]]:
    """Build a deterministic inventory for explicitly selected registry IDs."""
    ordered_ids = sorted(dict.fromkeys(nct_ids))
    if not ordered_ids or any(not NCT_RE.fullmatch(value) for value in ordered_ids):
        raise SystemExit("Every --nct-id must match NCT followed by eight digits")
    rows: list[dict[str, str]] = []
    for nct_id in ordered_ids:
        _raw, payload, _url = fetch_study(nct_id)
        fields = status_fields(payload)
        if fields["study_type"] != "INTERVENTIONAL":
            raise RuntimeError(f"{nct_id} is not interventional")
        if fields["completion_date_type"] != "ACTUAL":
            raise RuntimeError(f"{nct_id} does not have an ACTUAL completion date")
        protocol = payload.get("protocolSection") or {}
        interventions = (protocol.get("armsInterventionsModule") or {}).get("interventions") or []
        if not any(row.get("type") in {"DRUG", "BIOLOGICAL"} for row in interventions):
            raise RuntimeError(f"{nct_id} has no DRUG or BIOLOGICAL intervention")
        bounds = partial_date_bounds(fields["completion_date_text"])
        if bounds is None:
            raise RuntimeError(f"{nct_id} has an invalid completion date")
        lower, upper, precision = bounds
        rows.append({
            "nct_id": nct_id,
            "completion_date_text": fields["completion_date_text"],
            "completion_date_type": fields["completion_date_type"],
            "completion_date_precision": precision,
            "completion_date_lower_bound": lower.isoformat(),
            "completion_date_upper_bound": upper.isoformat(),
        })
    rows.sort(key=lambda row: (row["completion_date_lower_bound"], row["nct_id"]))
    return rows, len(rows), {
        "mode": "explicit_nct_ids",
        "nct_ids": ordered_ids,
        "detail_endpoint": API_BASE + "/{nct_id}",
    }


def fetch_study(nct_id: str) -> tuple[bytes, dict[str, Any], str]:
    url = f"{API_BASE}/{urllib.parse.quote(nct_id)}?format=json"
    raw = request_bytes(url)
    payload = json.loads(raw)
    returned_id = (
        ((payload.get("protocolSection") or {}).get("identificationModule") or {}).get("nctId")
    )
    if returned_id != nct_id:
        raise RuntimeError(f"Requested {nct_id}, source returned {returned_id!r}")
    return raw, payload, url


def status_fields(payload: dict[str, Any]) -> dict[str, Any]:
    protocol = payload.get("protocolSection") or {}
    status = protocol.get("statusModule") or {}
    identification = protocol.get("identificationModule") or {}
    design = protocol.get("designModule") or {}
    sponsor = (protocol.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}
    conditions = (protocol.get("conditionsModule") or {}).get("conditions") or []

    def struct_date(name: str) -> date | None:
        return parse_iso_date((status.get(name) or {}).get("date"))

    def struct_date_text(name: str) -> str | None:
        return (status.get(name) or {}).get("date")

    completion_text = struct_date_text("completionDateStruct")
    completion_bounds = partial_date_bounds(completion_text)

    return {
        "nct_id": identification["nctId"],
        "brief_title": identification.get("briefTitle"),
        "official_title": identification.get("officialTitle"),
        "study_type": design.get("studyType"),
        "phases": design.get("phases") or [],
        "overall_status": status.get("overallStatus"),
        "lead_sponsor_name": sponsor.get("name"),
        "lead_sponsor_class": sponsor.get("class"),
        "first_submitted_date": parse_iso_date(status.get("studyFirstSubmitDate")),
        "first_posted_date": struct_date("studyFirstPostDateStruct"),
        "last_update_posted_date": struct_date("lastUpdatePostDateStruct"),
        "study_start_date_text": struct_date_text("startDateStruct"),
        "study_start_date": struct_date("startDateStruct"),
        "primary_completion_date_text": struct_date_text("primaryCompletionDateStruct"),
        "primary_completion_date": struct_date("primaryCompletionDateStruct"),
        "primary_completion_date_type": (status.get("primaryCompletionDateStruct") or {}).get("type"),
        "completion_date_text": struct_date_text("completionDateStruct"),
        "completion_date": struct_date("completionDateStruct"),
        "completion_date_type": (status.get("completionDateStruct") or {}).get("type"),
        "completion_date_precision": completion_bounds[2] if completion_bounds else None,
        "completion_date_lower_bound": completion_bounds[0] if completion_bounds else None,
        "completion_date_upper_bound": completion_bounds[1] if completion_bounds else None,
        "conditions": conditions,
        "has_results": bool(payload.get("hasResults")),
    }


def source_version_fields(payload: dict[str, Any]) -> tuple[str | None, date | None, date | None]:
    status = ((payload.get("protocolSection") or {}).get("statusModule") or {})
    first_posted = parse_iso_date((status.get("studyFirstPostDateStruct") or {}).get("date"))
    last_update = parse_iso_date((status.get("lastUpdatePostDateStruct") or {}).get("date"))
    return (last_update.isoformat() if last_update else None, first_posted, last_update)


def ensure_source_and_run(
    conn: Any,
    run_id: uuid.UUID,
    retrieved_at: datetime,
    parameters: dict[str, Any],
    discovered_count: int,
    selected_count: int,
) -> int:
    release_label = f"api-snapshot:{retrieved_at.isoformat()}"
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pv_source.source_system
              (source_system_id, provider, domain, base_url, terms_url, attribution)
            VALUES
              (%s, 'U.S. National Library of Medicine', 'clinical_trials',
               'https://clinicaltrials.gov/',
               'https://clinicaltrials.gov/about-site/terms-conditions',
               'ClinicalTrials.gov')
            ON CONFLICT (source_system_id) DO NOTHING
            """,
            (SOURCE_SYSTEM_ID,),
        )
        cur.execute(
            """
            INSERT INTO pv_source.source_release
              (source_system_id, release_label, retrieved_at, metadata)
            VALUES (%s, %s, %s, %s)
            RETURNING source_release_id
            """,
            (SOURCE_SYSTEM_ID, release_label, retrieved_at, Json({"snapshot_kind": "api_query"})),
        )
        release_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO pv_source.acquisition_run
              (acquisition_run_id, source_release_id, adapter, adapter_version,
               git_commit, parameters, status, started_at, discovered_count,
               selected_count)
            VALUES (%s, %s, %s, %s, %s, %s, 'running', %s, %s, %s)
            """,
            (
                str(run_id), release_id, ADAPTER, ADAPTER_VERSION, git_commit(),
                Json(parameters), retrieved_at, discovered_count, selected_count,
            ),
        )
    conn.commit()
    return release_id


def store_query(
    conn: Any,
    run_id: uuid.UUID,
    expression: str,
    request_parameters: dict[str, Any],
    inventory: list[dict[str, str]],
    expected_total: int,
) -> int:
    manifest_bytes = canonical_json(inventory)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pv_source.retrieval_query
              (acquisition_run_id, query_kind, query_key, query_text, request_parameters,
               expected_total, returned_total, result_manifest, manifest_sha256)
            VALUES (%s, 'trial_inventory', 'trial_inventory', %s, %s, %s, %s, %s, %s)
            RETURNING retrieval_query_id
            """,
            (
                str(run_id), expression, Json(request_parameters), expected_total,
                len(inventory), Json(inventory), sha256_bytes(manifest_bytes),
            ),
        )
        query_id = cur.fetchone()[0]
    conn.commit()
    return query_id


def upsert_source_version(
    cur: Any,
    release_id: int,
    run_id: uuid.UUID,
    raw: bytes,
    payload: dict[str, Any],
    source_url: str,
    retrieved_at: datetime,
) -> tuple[int, int, bool]:
    nct_id = status_fields(payload)["nct_id"]
    cur.execute(
        """
        INSERT INTO pv_source.source_record
          (source_system_id, native_record_id, record_type)
        VALUES (%s, %s, 'registry_record')
        ON CONFLICT (source_system_id, native_record_id)
        DO UPDATE SET native_record_id = EXCLUDED.native_record_id
        RETURNING source_record_id
        """,
        (SOURCE_SYSTEM_ID, nct_id),
    )
    record_id = cur.fetchone()[0]
    digest = sha256_bytes(raw)
    cur.execute(
        """
        SELECT source_record_version_id
        FROM pv_source.source_record_version
        WHERE source_record_id = %s AND content_sha256 = %s
        """,
        (record_id, digest),
    )
    existing = cur.fetchone()
    if existing:
        version_id = existing[0]
        cur.execute(
            """
            UPDATE pv_source.source_record_version
            SET last_seen_at = %s
            WHERE source_record_version_id = %s
            """,
            (retrieved_at, version_id),
        )
        return record_id, version_id, True

    provider_version, first_posted, last_update = source_version_fields(payload)
    cur.execute(
        """
        INSERT INTO pv_source.source_record_version
          (source_record_id, source_release_id, acquisition_run_id,
           provider_version, source_url, media_type, content_sha256, byte_size,
           raw_payload, raw_payload_text, publicly_available_at,
           source_updated_at, retrieved_at, last_seen_at)
        VALUES (%s, %s, %s, %s, %s, 'application/json', %s, %s, %s, %s,
                %s, %s, %s, %s)
        RETURNING source_record_version_id
        """,
        (
            record_id, release_id, str(run_id), provider_version, source_url,
            digest, len(raw), Json(payload), raw.decode("utf-8"), first_posted,
            last_update, retrieved_at, retrieved_at,
        ),
    )
    return record_id, cur.fetchone()[0], False


def upsert_trial_projection(cur: Any, version_id: int, payload: dict[str, Any]) -> None:
    fields = status_fields(payload)
    if fields["completion_date_text"] is None:
        raise RuntimeError(f"{fields['nct_id']} has no completion date")
    cur.execute(
        """
        INSERT INTO pv_core.trial
          (nct_id, brief_title, official_title, study_type, phases,
           overall_status, lead_sponsor_name, lead_sponsor_class,
           first_submitted_date, first_posted_date, last_update_posted_date,
           study_start_date_text, study_start_date,
           primary_completion_date_text, primary_completion_date,
           primary_completion_date_type,
           completion_date_text, completion_date, completion_date_type,
           completion_date_precision,completion_date_lower_bound,
           completion_date_upper_bound,
           conditions, has_results, latest_source_record_version_id)
        VALUES
          (%(nct_id)s, %(brief_title)s, %(official_title)s, %(study_type)s,
           %(phases)s, %(overall_status)s, %(lead_sponsor_name)s,
           %(lead_sponsor_class)s, %(first_submitted_date)s,
           %(first_posted_date)s, %(last_update_posted_date)s,
           %(study_start_date_text)s, %(study_start_date)s,
           %(primary_completion_date_text)s, %(primary_completion_date)s,
           %(primary_completion_date_type)s,
           %(completion_date_text)s, %(completion_date)s,
           %(completion_date_type)s,
           %(completion_date_precision)s,%(completion_date_lower_bound)s,
           %(completion_date_upper_bound)s,
           %(conditions)s, %(has_results)s, %(version_id)s)
        ON CONFLICT (nct_id) DO UPDATE SET
          brief_title = EXCLUDED.brief_title,
          official_title = EXCLUDED.official_title,
          study_type = EXCLUDED.study_type,
          phases = EXCLUDED.phases,
          overall_status = EXCLUDED.overall_status,
          lead_sponsor_name = EXCLUDED.lead_sponsor_name,
          lead_sponsor_class = EXCLUDED.lead_sponsor_class,
          first_submitted_date = EXCLUDED.first_submitted_date,
          first_posted_date = EXCLUDED.first_posted_date,
          last_update_posted_date = EXCLUDED.last_update_posted_date,
          study_start_date_text = EXCLUDED.study_start_date_text,
          study_start_date = EXCLUDED.study_start_date,
          primary_completion_date_text = EXCLUDED.primary_completion_date_text,
          primary_completion_date = EXCLUDED.primary_completion_date,
          primary_completion_date_type = EXCLUDED.primary_completion_date_type,
          completion_date_text = EXCLUDED.completion_date_text,
          completion_date = EXCLUDED.completion_date,
          completion_date_type = EXCLUDED.completion_date_type,
          completion_date_precision = EXCLUDED.completion_date_precision,
          completion_date_lower_bound = EXCLUDED.completion_date_lower_bound,
          completion_date_upper_bound = EXCLUDED.completion_date_upper_bound,
          conditions = EXCLUDED.conditions,
          has_results = EXCLUDED.has_results,
          latest_source_record_version_id = EXCLUDED.latest_source_record_version_id,
          updated_at = now()
        """,
        {**fields, "version_id": version_id},
    )
    nct_id = fields["nct_id"]
    cur.execute(
        """
        INSERT INTO pv_core.trial_record_link (nct_id, source_record_version_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
        """,
        (nct_id, version_id),
    )

    protocol = payload.get("protocolSection") or {}
    module = protocol.get("armsInterventionsModule") or {}
    arm_ids: dict[str, int] = {}
    for index, arm in enumerate(module.get("armGroups") or []):
        path = f"protocolSection.armsInterventionsModule.armGroups[{index}]"
        cur.execute(
            """
            INSERT INTO pv_core.trial_arm
              (nct_id, source_record_version_id, source_path, label, arm_type, description)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_record_version_id, source_path)
            DO UPDATE SET label = EXCLUDED.label
            RETURNING trial_arm_id
            """,
            (nct_id, version_id, path, arm["label"], arm.get("type"), arm.get("description")),
        )
        arm_ids[arm["label"]] = cur.fetchone()[0]

    for index, intervention in enumerate(module.get("interventions") or []):
        path = f"protocolSection.armsInterventionsModule.interventions[{index}]"
        literal_name = intervention["name"]
        cur.execute(
            """
            INSERT INTO pv_core.intervention_mention
              (nct_id, source_record_version_id, source_path, literal_name,
               comparison_name, intervention_type, description, other_names)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_record_version_id, source_path)
            DO UPDATE SET literal_name = EXCLUDED.literal_name
            RETURNING intervention_mention_id
            """,
            (
                nct_id, version_id, path, literal_name, comparison_form(literal_name),
                intervention.get("type"), intervention.get("description"),
                intervention.get("otherNames") or [],
            ),
        )
        intervention_id = cur.fetchone()[0]
        for label in intervention.get("armGroupLabels") or []:
            arm_id = arm_ids.get(label)
            if arm_id is not None:
                cur.execute(
                    """
                    INSERT INTO pv_core.arm_intervention
                      (trial_arm_id, intervention_mention_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (arm_id, intervention_id),
                )

    conditions = (protocol.get("conditionsModule") or {}).get("conditions") or []
    for index, condition in enumerate(conditions):
        path = f"protocolSection.conditionsModule.conditions[{index}]"
        cur.execute(
            """
            INSERT INTO pv_core.condition_mention
              (nct_id, source_record_version_id, source_path, literal_name,
               comparison_name)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (source_record_version_id, source_path)
            DO UPDATE SET literal_name = EXCLUDED.literal_name
            """,
            (nct_id, version_id, path, condition, comparison_form(condition)),
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-date", type=date.fromisoformat)
    parser.add_argument("--through-date", type=date.fromisoformat)
    parser.add_argument(
        "--nct-id", action="append",
        help="ingest an explicit eligible NCT ID instead of discovering a date range; repeatable",
    )
    parser.add_argument("--limit", type=int, default=10, help="0 selects the complete inventory")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--commit", action="store_true", help="write to Neon")
    mode.add_argument("--dry-run", action="store_true", help="discover and fetch without writing (default)")
    parser.add_argument(
        "--expect-no-new-versions",
        action="store_true",
        help="fail if a committed rerun observes any changed/new source payload",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.nct_id and (args.from_date or args.through_date):
        raise SystemExit("Use either --nct-id or --from-date/--through-date, not both")
    if not args.nct_id and (args.from_date is None or args.through_date is None):
        raise SystemExit("Provide --nct-id or both --from-date and --through-date")
    if not args.nct_id and args.from_date > args.through_date:
        raise SystemExit("--from-date must be on or before --through-date")
    if args.limit < 0:
        raise SystemExit("--limit must be nonnegative")

    if args.nct_id:
        inventory, expected_total, request_parameters = discover_selected(args.nct_id)
        expression = " OR ".join(f"AREA[NCTId]{value}" for value in sorted(set(args.nct_id)))
    else:
        inventory, expected_total, request_parameters = discover_inventory(
            args.from_date, args.through_date
        )
        expression = query_expression(args.from_date, args.through_date)
    selected = inventory if args.limit == 0 else inventory[: args.limit]
    print(
        f"Discovered {len(inventory)} records; selected {len(selected)} by "
        "(actual_completion_date, nct_id)"
    )
    for row in selected:
        print(
            f"  {row['completion_date_text']} ({row['completion_date_precision']}) "
            f"{row['nct_id']}"
        )

    if not args.commit:
        for row in selected:
            raw, payload, _ = fetch_study(row["nct_id"])
            fields = status_fields(payload)
            if fields["completion_date_text"] != row["completion_date_text"]:
                raise RuntimeError(f"Discovery/detail date mismatch for {row['nct_id']}")
            if fields["completion_date_type"] != "ACTUAL":
                raise RuntimeError(f"Discovery/detail completion type mismatch for {row['nct_id']}")
            print(f"  fetched {row['nct_id']} bytes={len(raw)} sha256={sha256_bytes(raw)}")
        print("Dry run complete; Neon was not modified.")
        return

    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required with --commit")
    retrieved_at = datetime.now(timezone.utc)
    run_id = uuid.uuid4()
    parameters = {
        "from_date": args.from_date.isoformat() if args.from_date else None,
        "through_date": args.through_date.isoformat() if args.through_date else None,
        "nct_ids": sorted(set(args.nct_id or [])),
        "selection_mode": "explicit_nct_ids" if args.nct_id else "completion_date_range",
        "limit": args.limit,
        "cohort_date_field": "completion_date",
        "completion_date_type": "ACTUAL",
        "study_type": "INTERVENTIONAL",
        "intervention_types_any": ["DRUG", "BIOLOGICAL"],
        "selection_order": ["completion_date", "nct_id"],
        "raw_storage": "neon_raw_payload_text",
        "gcs_archive": None,
    }
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    stored = reused = failures = 0
    errors: list[dict[str, str]] = []
    try:
        release_id = ensure_source_and_run(
            conn, run_id, retrieved_at, parameters, len(inventory), len(selected)
        )
        query_id = store_query(
            conn, run_id, expression, request_parameters, inventory, expected_total
        )
        for ordinal, row in enumerate(selected):
            nct_id = row["nct_id"]
            try:
                raw, payload, source_url = fetch_study(nct_id)
                fields = status_fields(payload)
                if fields["completion_date_text"] != row["completion_date_text"]:
                    raise RuntimeError("discovery/detail completion date mismatch")
                if fields["completion_date_type"] != "ACTUAL":
                    raise RuntimeError("discovery/detail completion type mismatch")
                with conn.cursor() as cur:
                    record_id, version_id, was_reused = upsert_source_version(
                        cur, release_id, run_id, raw, payload, source_url,
                        datetime.now(timezone.utc),
                    )
                    upsert_trial_projection(cur, version_id, payload)
                    cur.execute(
                        """
                        INSERT INTO pv_source.retrieval_disposition
                          (retrieval_query_id, source_record_id,
                           source_record_version_id, result_ordinal, disposition)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            query_id, record_id, version_id, ordinal,
                            "selected_reused" if was_reused else "selected_stored",
                        ),
                    )
                conn.commit()
                reused += int(was_reused)
                stored += int(not was_reused)
                print(
                    f"  {'reused' if was_reused else 'stored'} {nct_id} "
                    f"bytes={len(raw)} sha256={sha256_bytes(raw)}"
                )
            except Exception as exc:  # retain the failed run and continue the pilot
                conn.rollback()
                failures += 1
                errors.append({"nct_id": nct_id, "error_type": type(exc).__name__, "message": str(exc)})
                print(f"  failed {nct_id}: {type(exc).__name__}: {exc}", file=sys.stderr)
        final_status = "completed" if failures == 0 else "failed"
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pv_source.acquisition_run
                SET status = %s, completed_at = now(), stored_count = %s,
                    reused_count = %s, failure_count = %s, error_summary = %s
                WHERE acquisition_run_id = %s
                """,
                (final_status, stored, reused, failures, Json(errors), str(run_id)),
            )
        conn.commit()
    finally:
        conn.close()
    print(
        f"Run {run_id}: status={'completed' if failures == 0 else 'failed'} "
        f"stored={stored} reused={reused} failures={failures}"
    )
    if failures:
        raise SystemExit(1)
    if args.expect_no_new_versions and stored:
        raise SystemExit(
            f"Idempotency check failed: {stored} source payload(s) were new or changed"
        )


if __name__ == "__main__":
    main()
