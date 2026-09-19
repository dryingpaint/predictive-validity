"""Resolve source-backed assets and molecular targets for the ten-trial pilot.

This initial deterministic pass resolves salbutamol/albuterol through PubChem,
an FDA label, HGNC, and UniProt. It deliberately leaves unsupported or broad
mechanisms unresolved. No LLM is called.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json


USER_AGENT = "predictive-validity-asset-target-ingest/1.0"
ADAPTER_VERSION = "1.0.0"
ASSET_NAMESPACE = uuid.UUID("5ef25fa7-f44d-47f5-a474-07cd54fb7f79")
TARGET_NAMESPACE = uuid.UUID("8c03e58b-a014-483d-ab9f-f0e2b1471aa0")
PHENOTYPE_NAMESPACE = uuid.UUID("36998573-5099-4b02-99d0-5160d3c99ba5")


SOURCE_CONFIG = {
    "pubchem": {
        "provider": "NCBI",
        "domain": "asset_identity",
        "base_url": "https://pubchem.ncbi.nlm.nih.gov/",
        "terms_url": "https://www.ncbi.nlm.nih.gov/home/about/policies/",
        "attribution": "PubChem",
    },
    "openfda": {
        "provider": "U.S. Food and Drug Administration",
        "domain": "regulatory_label",
        "base_url": "https://api.fda.gov/",
        "terms_url": "https://open.fda.gov/terms/",
        "attribution": "openFDA",
    },
    "hgnc": {
        "provider": "HUGO Gene Nomenclature Committee",
        "domain": "target_identity",
        "base_url": "https://www.genenames.org/",
        "terms_url": "https://www.genenames.org/about/license/",
        "attribution": "HGNC",
    },
    "uniprot": {
        "provider": "UniProt Consortium",
        "domain": "target_identity",
        "base_url": "https://www.uniprot.org/",
        "terms_url": "https://www.uniprot.org/help/license",
        "attribution": "UniProt",
    },
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", value) else None


def fetch(url: str) -> tuple[bytes, dict[str, Any]]:
    for attempt in range(5):
        request = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                raw = response.read()
            return raw, json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 4:
                raise
            time.sleep(min(2**attempt, 30))
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise
            time.sleep(min(2**attempt, 30))
    raise AssertionError("unreachable")


def fetch_inputs() -> dict[str, dict[str, Any]]:
    pubchem_url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
        "salbutamol/synonyms/JSON"
    )
    pubchem_raw, pubchem = fetch(pubchem_url)
    compound = pubchem["InformationList"]["Information"][0]
    if compound["CID"] != 2083:
        raise RuntimeError(f"Unexpected PubChem CID for salbutamol: {compound['CID']}")
    synonyms = {value.casefold() for value in compound.get("Synonym", [])}
    if not {"salbutamol", "albuterol"}.issubset(synonyms):
        raise RuntimeError("PubChem did not return the required salbutamol/albuterol aliases")

    label_query = 'openfda.generic_name:"ALBUTEROL SULFATE"'
    search_url = "https://api.fda.gov/drug/label.json?" + urllib.parse.urlencode(
        {"search": label_query, "limit": 100}
    )
    _, search_result = fetch(search_url)
    labels = [item for item in search_result.get("results", []) if item.get("mechanism_of_action")]
    if not labels:
        raise RuntimeError("No albuterol label with mechanism_of_action was returned")
    selected = max(labels, key=lambda item: (item.get("effective_time") or "", item.get("set_id") or ""))
    set_id = selected["set_id"]
    label_url = "https://api.fda.gov/drug/label.json?" + urllib.parse.urlencode(
        {"search": f'set_id:"{set_id}"', "limit": 1}
    )
    label_raw, label_response = fetch(label_url)
    label = label_response["results"][0]
    mechanism_text = "\n".join(label.get("mechanism_of_action") or [])
    if not re.search(r"(?:beta|β)\s*2\s*-?adrenergic receptors?", mechanism_text, re.I):
        raise RuntimeError("Selected FDA label does not explicitly mention beta-2 adrenergic receptor")

    hgnc_url = "https://rest.genenames.org/fetch/symbol/ADRB2"
    hgnc_raw, hgnc = fetch(hgnc_url)
    hgnc_docs = hgnc["response"]["docs"]
    if len(hgnc_docs) != 1 or hgnc_docs[0]["hgnc_id"] != "HGNC:286":
        raise RuntimeError("HGNC did not uniquely resolve ADRB2 to HGNC:286")
    hgnc_record = hgnc_docs[0]
    uniprot_ids = hgnc_record.get("uniprot_ids") or []
    if "P07550" not in uniprot_ids:
        raise RuntimeError("HGNC ADRB2 record does not contain UniProt P07550")

    uniprot_url = "https://rest.uniprot.org/uniprotkb/P07550.json"
    uniprot_raw, uniprot = fetch(uniprot_url)
    genes = uniprot.get("genes") or []
    primary_gene = (((genes[0] if genes else {}).get("geneName") or {}).get("value"))
    if uniprot.get("primaryAccession") != "P07550" or primary_gene != "ADRB2":
        raise RuntimeError("UniProt P07550 did not resolve to ADRB2")

    return {
        "pubchem": {
            "raw": pubchem_raw, "payload": pubchem, "url": pubchem_url,
            "native_id": "CID:2083", "provider_version": None,
            "query": "salbutamol", "record_type": "compound_synonym_record",
        },
        "openfda": {
            "raw": label_raw, "payload": label_response, "url": label_url,
            "native_id": set_id, "provider_version": label.get("effective_time"),
            "query": label_query, "record_type": "regulatory_label",
            "selected_record": label, "mechanism_text": mechanism_text,
        },
        "hgnc": {
            "raw": hgnc_raw, "payload": hgnc, "url": hgnc_url,
            "native_id": "HGNC:286", "provider_version": hgnc_record.get("date_modified"),
            "query": "ADRB2", "record_type": "gene_identity_record",
            "selected_record": hgnc_record,
        },
        "uniprot": {
            "raw": uniprot_raw, "payload": uniprot, "url": uniprot_url,
            "native_id": "P07550",
            "provider_version": (uniprot.get("entryAudit") or {}).get("lastAnnotationUpdateDate"),
            "query": "P07550", "record_type": "protein_identity_record",
            "selected_record": uniprot,
        },
    }


def start_source_run(
    conn: Any, source_id: str, retrieved_at: datetime, parameters: dict[str, Any]
) -> tuple[int, uuid.UUID]:
    config = SOURCE_CONFIG[source_id]
    run_id = uuid.uuid4()
    release_label = f"api-snapshot:{retrieved_at.isoformat()}"
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pv_source.source_system
              (source_system_id, provider, domain, base_url, terms_url, attribution)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_system_id) DO NOTHING
            """,
            (
                source_id, config["provider"], config["domain"], config["base_url"],
                config["terms_url"], config["attribution"],
            ),
        )
        cur.execute(
            """
            INSERT INTO pv_source.source_release
              (source_system_id, release_label, retrieved_at, metadata)
            VALUES (%s, %s, %s, %s)
            RETURNING source_release_id
            """,
            (source_id, release_label, retrieved_at, Json({"snapshot_kind": "api_record"})),
        )
        release_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO pv_source.acquisition_run
              (acquisition_run_id, source_release_id, adapter, adapter_version,
               git_commit, parameters, status, started_at, discovered_count,
               selected_count)
            VALUES (%s, %s, %s, %s, %s, %s, 'running', %s, 1, 1)
            """,
            (
                str(run_id), release_id, "pv.ingest.pilot_asset_targets",
                ADAPTER_VERSION, git_commit(), Json(parameters), retrieved_at,
            ),
        )
    conn.commit()
    return release_id, run_id


def store_source_record(
    conn: Any,
    source_id: str,
    release_id: int,
    run_id: uuid.UUID,
    item: dict[str, Any],
    retrieved_at: datetime,
) -> tuple[int, int, bool]:
    raw = item["raw"]
    digest = sha256(raw)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pv_source.retrieval_query
              (acquisition_run_id, query_kind, query_key, query_text,
               request_parameters, expected_total, returned_total,
               result_manifest, manifest_sha256)
            VALUES (%s, 'record_fetch', 'record_fetch', %s, %s, 1, 1, %s, %s)
            RETURNING retrieval_query_id
            """,
            (
                str(run_id), item["query"], Json({"url": item["url"]}),
                Json([{"native_id": item["native_id"]}]),
                sha256(canonical_json([{"native_id": item["native_id"]}])),
            ),
        )
        query_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO pv_source.source_record
              (source_system_id, native_record_id, record_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (source_system_id, native_record_id)
            DO UPDATE SET record_type = EXCLUDED.record_type
            RETURNING source_record_id
            """,
            (source_id, item["native_id"], item["record_type"]),
        )
        record_id = cur.fetchone()[0]
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
                """UPDATE pv_source.source_record_version
                   SET last_seen_at=%s WHERE source_record_version_id=%s""",
                (retrieved_at, version_id),
            )
            reused = True
        else:
            cur.execute(
                """
                INSERT INTO pv_source.source_record_version
                  (source_record_id, source_release_id, acquisition_run_id,
                   provider_version, source_url, media_type, content_sha256,
                   byte_size, raw_payload, raw_payload_text, retrieved_at,
                   last_seen_at)
                VALUES (%s, %s, %s, %s, %s, 'application/json', %s, %s,
                        %s, %s, %s, %s)
                RETURNING source_record_version_id
                """,
                (
                    record_id, release_id, str(run_id), item["provider_version"],
                    item["url"], digest, len(raw), Json(item["payload"]),
                    raw.decode(), retrieved_at, retrieved_at,
                ),
            )
            version_id = cur.fetchone()[0]
            reused = False
        cur.execute(
            """
            INSERT INTO pv_source.retrieval_disposition
              (retrieval_query_id, source_record_id, source_record_version_id,
               result_ordinal, disposition)
            VALUES (%s, %s, %s, 0, %s)
            """,
            (query_id, record_id, version_id, "selected_reused" if reused else "selected_stored"),
        )
        cur.execute(
            """
            INSERT INTO pv_source.rights_assertion
              (source_record_version_id, decision, intended_use, rationale)
            SELECT %s, 'review_required', 'noncommercial_research',
                   'Public API record retained; representation-level terms review remains required.'
            WHERE NOT EXISTS (
              SELECT 1 FROM pv_source.rights_assertion
              WHERE source_record_version_id=%s
            )
            """,
            (version_id, version_id),
        )
        cur.execute(
            """
            UPDATE pv_source.acquisition_run
            SET status='completed', completed_at=now(),
                stored_count=%s, reused_count=%s
            WHERE acquisition_run_id=%s
            """,
            (int(not reused), int(reused), str(run_id)),
        )
    conn.commit()
    return release_id, version_id, reused


def insert_identifier(cur: Any, entity_id: uuid.UUID, namespace: str, value: str, release_id: int, preferred: bool = False) -> None:
    cur.execute(
        """
        INSERT INTO pv_core.entity_identifier
          (entity_id, namespace, identifier, source_release_id, is_preferred)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        """,
        (str(entity_id), namespace, value, release_id, preferred),
    )


def insert_alias(
    cur: Any, entity_id: uuid.UUID, entity_type: str, text: str,
    kind: str, release_id: int, version_id: int, ambiguous: bool = False,
) -> None:
    cur.execute(
        """
        INSERT INTO pv_core.entity_alias
          (entity_id, entity_type, alias_text, alias_normalized, alias_kind,
           language, source_release_id, source_record_version_id, is_ambiguous)
        SELECT %s, %s, %s, lower(regexp_replace(trim(%s), '\\s+', ' ', 'g')),
               %s, 'en', %s, %s, %s
        WHERE NOT EXISTS (
          SELECT 1 FROM pv_core.entity_alias
          WHERE entity_id=%s AND alias_text=%s AND alias_kind=%s
            AND source_release_id=%s
        )
        """,
        (
            str(entity_id), entity_type, text, text, kind, release_id, version_id,
            ambiguous, str(entity_id), text, kind, release_id,
        ),
    )


def promote(
    conn: Any,
    inputs: dict[str, dict[str, Any]],
    stored: dict[str, tuple[int, int, bool]],
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    asset_id = uuid.uuid5(ASSET_NAMESPACE, "pubchem:2083")
    target_id = uuid.uuid5(TARGET_NAMESPACE, "hgnc:286")
    phenotype_id = uuid.uuid5(PHENOTYPE_NAMESPACE, "mondo:0004979")
    hgnc = inputs["hgnc"]["selected_record"]
    uniprot = inputs["uniprot"]["selected_record"]
    label = inputs["openfda"]["selected_record"]
    mechanism_text = inputs["openfda"]["mechanism_text"]
    pubchem_release, pubchem_version, _ = stored["pubchem"]
    openfda_release, openfda_version, _ = stored["openfda"]
    hgnc_release, hgnc_version, _ = stored["hgnc"]
    uniprot_release, uniprot_version, _ = stored["uniprot"]

    protein = uniprot.get("proteinDescription") or {}
    recommended = protein.get("recommendedName") or {}
    protein_name = ((recommended.get("fullName") or {}).get("value"))

    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO pv_core.entity (entity_id,entity_type,preferred_name)
               VALUES (%s,'asset','salbutamol') ON CONFLICT DO NOTHING""",
            (str(asset_id),),
        )
        cur.execute(
            """INSERT INTO pv_core.asset (entity_id,asset_kind,active_moiety_name)
               VALUES (%s,'small_molecule','salbutamol') ON CONFLICT DO NOTHING""",
            (str(asset_id),),
        )
        insert_identifier(cur, asset_id, "PubChem CID", "2083", pubchem_release, True)
        insert_alias(cur, asset_id, "asset", "salbutamol", "preferred", pubchem_release, pubchem_version)
        insert_alias(cur, asset_id, "asset", "albuterol", "synonym", pubchem_release, pubchem_version)

        cur.execute(
            """INSERT INTO pv_core.entity (entity_id,entity_type,preferred_name)
               VALUES (%s,'target',%s) ON CONFLICT DO NOTHING""",
            (str(target_id), hgnc["symbol"]),
        )
        cur.execute(
            """
            INSERT INTO pv_core.target
              (entity_id,hgnc_id,approved_symbol,approved_name,taxon_id,uniprot_accession)
            VALUES (%s,%s,%s,%s,9606,'P07550')
            ON CONFLICT (entity_id) DO UPDATE SET
              approved_symbol=EXCLUDED.approved_symbol,
              approved_name=EXCLUDED.approved_name,
              uniprot_accession=EXCLUDED.uniprot_accession
            """,
            (str(target_id), hgnc["hgnc_id"], hgnc["symbol"], hgnc["name"]),
        )
        insert_identifier(cur, target_id, "HGNC", hgnc["hgnc_id"], hgnc_release, True)
        insert_identifier(cur, target_id, "UniProt", "P07550", uniprot_release, True)
        if hgnc.get("ensembl_gene_id"):
            insert_identifier(cur, target_id, "Ensembl", hgnc["ensembl_gene_id"], hgnc_release)
        if hgnc.get("entrez_id"):
            insert_identifier(cur, target_id, "NCBI Gene", str(hgnc["entrez_id"]), hgnc_release)
        insert_alias(cur, target_id, "target", hgnc["symbol"], "approved_symbol", hgnc_release, hgnc_version)
        insert_alias(cur, target_id, "target", hgnc["name"], "approved_name", hgnc_release, hgnc_version)
        for value in hgnc.get("prev_symbol") or []:
            insert_alias(cur, target_id, "target", value, "previous_symbol", hgnc_release, hgnc_version, True)
        for value in hgnc.get("alias_symbol") or []:
            insert_alias(cur, target_id, "target", value, "alias_symbol", hgnc_release, hgnc_version, True)
        if protein_name:
            insert_alias(cur, target_id, "target", protein_name, "protein_name", uniprot_release, uniprot_version)

        cur.execute(
            """INSERT INTO pv_core.entity (entity_id,entity_type,preferred_name)
               VALUES (%s,'phenotype','asthma') ON CONFLICT DO NOTHING""",
            (str(phenotype_id),),
        )
        cur.execute(
            """
            INSERT INTO pv_core.phenotype
              (entity_id,ontology_namespace,ontology_identifier,preferred_name,phenotype_kind)
            VALUES (%s,'MONDO','MONDO:0004979','asthma','disease')
            ON CONFLICT (entity_id) DO NOTHING
            """,
            (str(phenotype_id),),
        )

        cur.execute(
            """
            SELECT i.intervention_mention_id, i.nct_id,
                   i.source_record_version_id, i.literal_name
            FROM pv_core.intervention_mention i
            JOIN pv_core.trial t USING (nct_id)
            WHERE i.source_record_version_id=t.latest_source_record_version_id
              AND i.intervention_type='DRUG'
              AND lower(i.literal_name) LIKE '%%salbutamol%%'
            ORDER BY i.nct_id,i.source_path
            """
        )
        mentions = cur.fetchall()
        if not mentions:
            raise RuntimeError("No salbutamol intervention mentions found in pilot")
        for mention_id, nct_id, source_version_id, literal_name in mentions:
            cur.execute(
                """
                INSERT INTO pv_core.trial_asset_link
                  (nct_id,asset_entity_id,intervention_mention_id,link_role,
                   source_record_version_id,resolution_status,resolution_method,
                   support_text)
                VALUES (%s,%s,%s,'registered_intervention',%s,'resolved',
                        'pubchem_exact_synonym_after_component_token_match',%s)
                ON CONFLICT DO NOTHING
                """,
                (nct_id, str(asset_id), mention_id, source_version_id, literal_name),
            )
            cur.execute(
                """UPDATE pv_core.intervention_mention
                   SET normalization_status='resolved'
                   WHERE intervention_mention_id=%s""",
                (mention_id,),
            )

        effective = label.get("effective_time")
        assertion_date = None
        if effective and re.fullmatch(r"[0-9]{8}", effective):
            assertion_date = date(int(effective[:4]), int(effective[4:6]), int(effective[6:8]))
        cur.execute(
            """
            INSERT INTO pv_evidence.asset_target_assertion
              (asset_entity_id,target_entity_id,action_literal,
               action_normalized,role,directness,source_record_version_id,
               support_quote,assertion_date)
            VALUES (%s,%s,'preferential effect on and activation of beta-2 adrenergic receptors',
                    'agonizes','therapeutic_primary','claimed_direct',%s,%s,%s)
            ON CONFLICT DO NOTHING
            """,
            (str(asset_id), str(target_id), openfda_version, mechanism_text, assertion_date),
        )
    conn.commit()
    return asset_id, target_id, phenotype_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--commit", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    inputs = fetch_inputs()
    label = inputs["openfda"]["selected_record"]
    print("Resolved salbutamol/albuterol to PubChem CID 2083")
    print("Resolved beta-2 adrenergic receptor to HGNC:286 / ADRB2 / UniProt P07550")
    print(f"Selected FDA label set_id={label['set_id']} effective_time={label.get('effective_time')}")
    if not args.commit:
        print("Dry run complete; Neon was not modified.")
        return
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required with --commit")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    retrieved_at = datetime.now(timezone.utc)
    stored: dict[str, tuple[int, int, bool]] = {}
    try:
        for source_id, item in inputs.items():
            release_id, run_id = start_source_run(
                conn, source_id, retrieved_at,
                {"native_id": item["native_id"], "url": item["url"]},
            )
            stored[source_id] = store_source_record(
                conn, source_id, release_id, run_id, item, retrieved_at
            )
        asset_id, target_id, phenotype_id = promote(conn, inputs, stored)
    finally:
        conn.close()
    print(f"Promoted asset={asset_id} target={target_id} phenotype={phenotype_id}")
    print(
        "Source versions: " + ", ".join(
            f"{source}={'reused' if values[2] else 'stored'}"
            for source, values in stored.items()
        )
    )


if __name__ == "__main__":
    main()
