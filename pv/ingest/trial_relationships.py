"""Promote explicit related-trial identifiers from archived trial records.

The first rule recognizes retrospective reuse of a named sponsor protocol. It
stores the literal sponsor-protocol identity without guessing an NCT mapping.
Later adapters can resolve that identity to another archived registry record.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from typing import Any

import psycopg2
from psycopg2.extras import Json


POPULATION_PATTERN = re.compile(
    r"Participants randomized in the (?P<name>.+?) study "
    r"\((?P<identifier>[^)]+)\)",
    re.IGNORECASE,
)


def normalized_protocol_identifier(value: str) -> str:
    value = value.replace("N°", "").replace("Nº", "")
    return re.sub(r"\s+", " ", value).strip()


def explicit_relationships(
    nct_id: str, source_record_version_id: int, payload: dict[str, Any]
) -> list[dict[str, Any]]:
    eligibility = ((payload.get("protocolSection") or {}).get("eligibilityModule") or {})
    population = eligibility.get("studyPopulation") or ""
    match = POPULATION_PATTERN.search(population)
    if not match:
        return []
    protocol_id = normalized_protocol_identifier(match.group("identifier"))
    study_name = match.group("name").strip()
    result = {
        "subject_nct_id": nct_id,
        "source_record_version_id": source_record_version_id,
        "object_namespace": "sponsor_protocol",
        "object_identifier": protocol_id,
        "object_display_name": study_name,
        "relationship_type": "reuses_data_from",
        "evidence": [
            {
                "source_path": "protocolSection.eligibilityModule.studyPopulation",
                "support_quote": match.group(0),
                "derivation_method": "source_explicit",
                "detail": {"parser_rule": "participants_randomized_in_named_study_v1"},
            }
        ],
    }
    criteria = eligibility.get("eligibilityCriteria") or ""
    protocol_numbers = re.findall(r"\d+", protocol_id)
    terminal_protocol_number = protocol_numbers[-1] if protocol_numbers else None
    for sentence in re.split(r"[\r\n]+", criteria):
        clean = sentence.lstrip("* ").strip()
        identifies_protocol = (
            terminal_protocol_number is not None
            and terminal_protocol_number in clean
            and ("PHRC" in clean.upper() or study_name.casefold() in clean.casefold())
        )
        if identifies_protocol and re.search(r"reuse of (?:its|their) data", clean, re.IGNORECASE):
            result["evidence"].append(
                {
                    "source_path": "protocolSection.eligibilityModule.eligibilityCriteria",
                    "support_quote": clean,
                    "derivation_method": "source_explicit",
                    "detail": {"parser_rule": "explicit_data_reuse_sentence_v1"},
                }
            )
    return [result]


def load_trials(conn: Any, nct_ids: list[str]) -> list[tuple[str, int, dict[str, Any]]]:
    params: list[Any] = []
    where = ""
    if nct_ids:
        where = "WHERE t.nct_id=ANY(%s)"
        params.append(nct_ids)
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT t.nct_id,t.latest_source_record_version_id,v.raw_payload
            FROM pv_core.trial t
            JOIN pv_source.source_record_version v
              ON v.source_record_version_id=t.latest_source_record_version_id
            {where}
            ORDER BY t.completion_date_lower_bound,t.nct_id
            """,
            params,
        )
        rows = cur.fetchall()
    if nct_ids and {row[0] for row in rows} != set(nct_ids):
        missing = sorted(set(nct_ids) - {row[0] for row in rows})
        raise SystemExit(f"Unknown trial IDs: {', '.join(missing)}")
    return rows


def promote(conn: Any, relationships: list[dict[str, Any]]) -> tuple[int, int]:
    stored = reused = 0
    with conn.cursor() as cur:
        for row in relationships:
            cur.execute(
                """
                INSERT INTO pv_core.trial_relationship
                  (subject_nct_id,object_namespace,object_identifier,
                   object_display_name,relationship_type)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT
                  (subject_nct_id,object_namespace,object_identifier,relationship_type)
                DO NOTHING
                RETURNING trial_relationship_id
                """,
                (
                    row["subject_nct_id"], row["object_namespace"],
                    row["object_identifier"], row["object_display_name"],
                    row["relationship_type"],
                ),
            )
            inserted = cur.fetchone()
            if inserted:
                relationship_id = inserted[0]
                stored += 1
            else:
                cur.execute(
                    """
                    SELECT trial_relationship_id FROM pv_core.trial_relationship
                    WHERE subject_nct_id=%s AND object_namespace=%s
                      AND object_identifier=%s AND relationship_type=%s
                    """,
                    (
                        row["subject_nct_id"], row["object_namespace"],
                        row["object_identifier"], row["relationship_type"],
                    ),
                )
                relationship_id = cur.fetchone()[0]
                reused += 1
            for evidence in row["evidence"]:
                cur.execute(
                    """
                    INSERT INTO pv_evidence.trial_relationship_evidence
                      (trial_relationship_id,source_record_version_id,source_path,
                       support_quote,derivation_method,detail)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        relationship_id, row["source_record_version_id"],
                        evidence["source_path"], evidence["support_quote"],
                        evidence["derivation_method"], Json(evidence["detail"]),
                    ),
                )
    conn.commit()
    return stored, reused


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--nct-id", action="append", default=[])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--commit", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        relationships: list[dict[str, Any]] = []
        for nct_id, version_id, payload in load_trials(conn, args.nct_id):
            relationships.extend(explicit_relationships(nct_id, version_id, payload))
        print(json.dumps(relationships, indent=2, ensure_ascii=False))
        if not args.commit:
            print(f"Dry run: relationships={len(relationships)}; Neon was not modified.")
            return
        stored, reused = promote(conn, relationships)
        print(f"Committed relationships={len(relationships)} stored={stored} reused={reused}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
