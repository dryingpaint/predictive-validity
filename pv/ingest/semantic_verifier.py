"""Verify LLM-proposed pilot assets and pharmacology against structured sources.

The LLM is a discovery aid, never the enumeration boundary.  For every exact
ChEMBL asset resolution this adapter follows the parent/form graph and archives
all mechanism rows before promoting canonical assets, targets, trial links, and
proposal-verification records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json

from pv.ingest.pilot_asset_targets import ASSET_NAMESPACE, TARGET_NAMESPACE
from pv.ingest.search_aliases import classify_chembl_asset_alias


LLM_RUN_ID = "e3e68b5a-5e4a-4b63-935f-84fe829dc972"
ADAPTER = "pv.ingest.semantic_verifier"
ADAPTER_VERSION = "1.1.0"
USER_AGENT = "predictive-validity-semantic-verifier/1.0"
CHEMBL_BASE = "https://www.ebi.ac.uk/chembl/api/data"

SOURCE_CONFIG = {
    "chembl": (
        "EMBL-EBI", "asset_and_mechanism", "https://www.ebi.ac.uk/chembl/",
        "https://www.ebi.ac.uk/about/terms-of-use/", "ChEMBL",
    ),
    "hgnc": (
        "HUGO Gene Nomenclature Committee", "target_identity",
        "https://www.genenames.org/", "https://www.genenames.org/about/license/", "HGNC",
    ),
    "uniprot": (
        "UniProt Consortium", "target_identity", "https://www.uniprot.org/",
        "https://www.uniprot.org/help/license", "UniProt",
    ),
    "pubchem": (
        "NCBI", "asset_identity", "https://pubchem.ncbi.nlm.nih.gov/",
        "https://www.ncbi.nlm.nih.gov/home/about/policies/", "PubChem",
    ),
    "ols4": (
        "EMBL-EBI", "ontology", "https://www.ebi.ac.uk/ols4/",
        "https://www.ebi.ac.uk/about/terms-of-use/", "Ontology Lookup Service",
    ),
    "clinicaltrials_gov": (
        "U.S. National Library of Medicine", "clinical_trials",
        "https://clinicaltrials.gov/", "https://clinicaltrials.gov/about-site/terms-conditions",
        "ClinicalTrials.gov",
    ),
}

ROLE_MAP = {
    "experimental_intervention": "registered_intervention",
    "active_comparator": "active_comparator",
    "inactive_comparator": "inactive_comparator",
    "background_therapy": "background_therapy",
    "historical_exposure": "historical_exposure",
}
ACTION_MAP = {
    "INHIBITOR": "inhibits", "AGONIST": "agonizes",
    "INVERSE AGONIST": "inverse_agonizes", "ANTAGONIST": "antagonizes",
    "BINDER": "binds", "DEGRADER": "degrades", "MODULATOR": "modulates",
}


def mechanism_support_quote(mechanism: dict[str, Any]) -> str:
    """Preserve ChEMBL's target-level mechanism and optional site qualifier."""
    parts = [
        mechanism.get("mechanism_of_action") or mechanism.get("action_type") or "",
        mechanism.get("binding_site_comment") or "",
    ]
    return " | ".join(dict.fromkeys(part.strip() for part in parts if part and part.strip()))


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def literal_key(value: str) -> str:
    """Case/space normalization that preserves stereochemical punctuation."""
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def git_commit() -> str | None:
    result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", value) else None


def fetch_json(url: str) -> tuple[bytes, dict[str, Any]]:
    for attempt in range(5):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = response.read()
            return raw, json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 4:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise
        time.sleep(min(2**attempt, 30))
    raise AssertionError("unreachable")


@dataclass
class Archive:
    conn: Any
    source_id: str
    retrieved_at: datetime
    parameters: dict[str, Any]
    adapter: str = ADAPTER
    adapter_version: str = ADAPTER_VERSION
    release_id: int = field(init=False)
    run_id: uuid.UUID = field(init=False)
    stored: int = 0
    reused: int = 0
    queries: int = 0
    cache: dict[str, tuple[dict[str, Any], int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        provider, domain, base_url, terms_url, attribution = SOURCE_CONFIG[self.source_id]
        self.run_id = uuid.uuid4()
        release_label = f"api-snapshot:{self.retrieved_at.isoformat()}"
        with self.conn.cursor() as cur:
            cur.execute(
                """INSERT INTO pv_source.source_system
                     (source_system_id,provider,domain,base_url,terms_url,attribution)
                   VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                (self.source_id, provider, domain, base_url, terms_url, attribution),
            )
            cur.execute(
                """INSERT INTO pv_source.source_release
                     (source_system_id,release_label,retrieved_at,metadata)
                   VALUES (%s,%s,%s,%s) RETURNING source_release_id""",
                (self.source_id, release_label, self.retrieved_at, Json({"snapshot_kind": "api_verification"})),
            )
            self.release_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO pv_source.acquisition_run
                     (acquisition_run_id,source_release_id,adapter,adapter_version,git_commit,
                      parameters,status,started_at,discovered_count,selected_count)
                   VALUES (%s,%s,%s,%s,%s,%s,'running',%s,0,0)""",
                (str(self.run_id), self.release_id, self.adapter, self.adapter_version,
                 git_commit(), Json(self.parameters), self.retrieved_at),
            )
        self.conn.commit()

    def retrieve(self, key: str, query: str, url: str, native_id: str,
                 record_type: str, provider_version: str | None = None) -> tuple[dict[str, Any], int]:
        if key in self.cache:
            return self.cache[key]
        raw, payload = fetch_json(url)
        content_hash = digest(raw)
        manifest = [{"native_id": native_id, "content_sha256": content_hash}]
        with self.conn.cursor() as cur:
            cur.execute(
                """INSERT INTO pv_source.retrieval_query
                     (acquisition_run_id,query_kind,query_key,query_text,request_parameters,
                      expected_total,returned_total,result_manifest,manifest_sha256)
                   VALUES (%s,'structured_verification',%s,%s,%s,1,1,%s,%s)
                   RETURNING retrieval_query_id""",
                (str(self.run_id), key, query, Json({"url": url}), Json(manifest), digest(canonical_json(manifest))),
            )
            query_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO pv_source.source_record(source_system_id,native_record_id,record_type)
                   VALUES (%s,%s,%s) ON CONFLICT (source_system_id,native_record_id)
                   DO UPDATE SET record_type=EXCLUDED.record_type RETURNING source_record_id""",
                (self.source_id, native_id, record_type),
            )
            record_id = cur.fetchone()[0]
            cur.execute(
                """SELECT source_record_version_id FROM pv_source.source_record_version
                   WHERE source_record_id=%s AND content_sha256=%s""", (record_id, content_hash),
            )
            existing = cur.fetchone()
            if existing:
                version_id = existing[0]
                cur.execute("UPDATE pv_source.source_record_version SET last_seen_at=%s WHERE source_record_version_id=%s",
                            (self.retrieved_at, version_id))
                disposition = "selected_reused"
                self.reused += 1
            else:
                cur.execute(
                    """INSERT INTO pv_source.source_record_version
                         (source_record_id,source_release_id,acquisition_run_id,provider_version,
                          source_url,media_type,content_sha256,byte_size,raw_payload,
                          raw_payload_text,retrieved_at,last_seen_at)
                       VALUES (%s,%s,%s,%s,%s,'application/json',%s,%s,%s,%s,%s,%s)
                       RETURNING source_record_version_id""",
                    (record_id, self.release_id, str(self.run_id), provider_version, url, content_hash,
                     len(raw), Json(payload), raw.decode(), self.retrieved_at, self.retrieved_at),
                )
                version_id = cur.fetchone()[0]
                disposition = "selected_stored"
                self.stored += 1
            cur.execute(
                """INSERT INTO pv_source.retrieval_disposition
                     (retrieval_query_id,source_record_id,source_record_version_id,result_ordinal,disposition)
                   VALUES (%s,%s,%s,0,%s)""", (query_id, record_id, version_id, disposition),
            )
            cur.execute(
                """INSERT INTO pv_source.rights_assertion
                     (source_record_version_id,decision,intended_use,rationale)
                   SELECT %s,'review_required','noncommercial_research',
                          'Public structured API record retained; representation-level terms review remains required.'
                   WHERE NOT EXISTS (SELECT 1 FROM pv_source.rights_assertion WHERE source_record_version_id=%s)""",
                (version_id, version_id),
            )
        self.queries += 1
        self.conn.commit()
        self.cache[key] = (payload, version_id)
        return self.cache[key]

    def finish(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """UPDATE pv_source.acquisition_run SET status='completed',completed_at=now(),
                     discovered_count=%s,selected_count=%s,stored_count=%s,reused_count=%s
                   WHERE acquisition_run_id=%s""",
                (self.queries, self.queries, self.stored, self.reused, str(self.run_id)),
            )
        self.conn.commit()

    def fail(self, message: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """UPDATE pv_source.acquisition_run SET status='failed',completed_at=now(),
                     discovered_count=%s,selected_count=%s,stored_count=%s,reused_count=%s,
                     failure_count=1,error_summary=%s
                   WHERE acquisition_run_id=%s AND status='running'""",
                (self.queries, self.queries, self.stored, self.reused,
                 Json([{"error": message[:1000]}]), str(self.run_id)),
            )
        self.conn.commit()


def exact_parent(archive: Archive, name: str) -> tuple[dict[str, Any], int] | None:
    url = CHEMBL_BASE + "/molecule/search.json?" + urllib.parse.urlencode({"q": name, "limit": 100})
    payload, version_id = archive.retrieve(f"molecule-search:{normalized(name)}", name, url,
                                           f"molecule-search:{normalized(name)}", "molecule_search")
    matches: dict[str, dict[str, Any]] = {}
    preferred_matches: dict[str, dict[str, Any]] = {}
    active_prefix_matches: dict[str, dict[str, Any]] = {}
    needle = normalized(name)
    for molecule in payload.get("molecules") or []:
        aliases = [molecule.get("pref_name") or ""]
        aliases += [row.get("molecule_synonym") or "" for row in molecule.get("molecule_synonyms") or []]
        aliases += [row.get("synonyms") or "" for row in molecule.get("molecule_synonyms") or []]
        parent = (molecule.get("molecule_hierarchy") or {}).get("parent_chembl_id") or molecule["molecule_chembl_id"]
        normalized_aliases = {normalized(alias) for alias in aliases if alias}
        if needle in normalized_aliases:
            matches[parent] = molecule
        preferred = normalized(molecule.get("pref_name") or "")
        if literal_key(molecule.get("pref_name") or "") == literal_key(name):
            preferred_matches[parent] = molecule
        if (preferred and needle.startswith(preferred + " ")
                and float(molecule.get("max_phase") or 0) >= 1):
            active_prefix_matches[parent] = molecule
    if len(preferred_matches) == 1:
        matches = preferred_matches
        method = "exact_preferred_name"
    elif len(matches) == 1:
        method = "unique_exact_alias"
    elif len(active_prefix_matches) == 1:
        matches = active_prefix_matches
        method = "unique_clinical_active_prefix"
    else:
        return None
    parent_id = next(iter(matches))
    detail_url = f"{CHEMBL_BASE}/molecule/{parent_id}.json"
    detail, detail_version = archive.retrieve(f"molecule:{parent_id}", parent_id, detail_url,
                                              parent_id, "molecule_record", "ChEMBL 37")
    detail = dict(detail)
    detail["_pv_resolution_method"] = method
    return detail, detail_version


def complete_mechanisms(archive: Archive, parent_id: str) -> list[tuple[dict[str, Any], int]]:
    forms_url = CHEMBL_BASE + "/molecule_form.json?" + urllib.parse.urlencode(
        {"parent_chembl_id__exact": parent_id, "limit": 1000}
    )
    forms, _ = archive.retrieve(f"forms:{parent_id}", parent_id, forms_url,
                                f"forms:{parent_id}", "molecule_form_set", "ChEMBL 37")
    form_rows = forms.get("molecule_forms") or []
    if len(form_rows) != int((forms.get("page_meta") or {}).get("total_count", -1)):
        raise RuntimeError(f"Incomplete ChEMBL form enumeration for {parent_id}")
    rows: dict[int, tuple[dict[str, Any], int]] = {}
    for form in form_rows:
        molecule_id = form["molecule_chembl_id"]
        url = CHEMBL_BASE + "/mechanism.json?" + urllib.parse.urlencode(
            {"molecule_chembl_id": molecule_id, "limit": 1000}
        )
        payload, version_id = archive.retrieve(f"mechanisms:{molecule_id}", molecule_id, url,
                                               f"mechanisms:{molecule_id}", "mechanism_set", "ChEMBL 37")
        mechanisms = payload.get("mechanisms") or []
        if len(mechanisms) != int((payload.get("page_meta") or {}).get("total_count", -1)):
            raise RuntimeError(f"Incomplete ChEMBL mechanism enumeration for {molecule_id}")
        for row in mechanisms:
            rows[int(row["mec_id"])] = (row, version_id)
    return [rows[key] for key in sorted(rows)]


def insert_alias(cur: Any, entity_id: uuid.UUID, entity_type: str, text: str, kind: str,
                 release_id: int, version_id: int, ambiguous: bool = False,
                 language: str = "en") -> None:
    if not text or not text.strip():
        return
    cur.execute(
        """INSERT INTO pv_core.entity_alias
             (entity_id,entity_type,alias_text,alias_normalized,alias_kind,language,taxon_id,
              source_release_id,source_record_version_id,is_ambiguous)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
        (str(entity_id), entity_type, text, normalized(text), kind, language,
         9606 if entity_type == "target" else None, release_id, version_id, ambiguous),
    )


def insert_identifier(cur: Any, entity_id: uuid.UUID, namespace: str, identifier: str,
                      release_id: int, preferred: bool = False) -> None:
    cur.execute(
        """INSERT INTO pv_core.entity_identifier
             (entity_id,namespace,identifier,source_release_id,is_preferred)
           VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
        (str(entity_id), namespace, identifier, release_id, preferred),
    )


def pubchem_identity(archive: Archive, molecule: dict[str, Any]) -> tuple[int, str, int] | None:
    structures = molecule.get("molecule_structures") or {}
    inchikey = structures.get("standard_inchi_key")
    if not inchikey:
        return None
    url = ("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/inchikey/" +
           urllib.parse.quote(inchikey) + "/property/Title,IUPACName,InChIKey/JSON")
    payload, version_id = archive.retrieve(
        f"inchikey:{inchikey}", inchikey, url, f"InChIKey:{inchikey}", "compound_identity_record"
    )
    rows = (payload.get("PropertyTable") or {}).get("Properties") or []
    if len(rows) != 1 or rows[0].get("InChIKey") != inchikey:
        return None
    return int(rows[0]["CID"]), rows[0].get("Title") or molecule.get("pref_name") or inchikey, version_id


def reconcile_asset_identity(conn: Any, canonical_id: uuid.UUID, duplicate_id: uuid.UUID) -> None:
    """Merge a former ChEMBL-only identity into its PubChem/InChIKey identity."""
    if canonical_id == duplicate_id:
        return
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pv_core.entity WHERE entity_id=%s", (str(duplicate_id),))
        if not cur.fetchone():
            return
        cur.execute(
            """INSERT INTO pv_core.entity_identifier(entity_id,namespace,identifier,source_release_id,is_preferred)
               SELECT %s,namespace,identifier,source_release_id,is_preferred
               FROM pv_core.entity_identifier WHERE entity_id=%s ON CONFLICT DO NOTHING""",
            (str(canonical_id), str(duplicate_id)),
        )
        cur.execute(
            """INSERT INTO pv_core.entity_alias
                 (entity_id,entity_type,alias_text,alias_normalized,alias_kind,language,taxon_id,
                  source_release_id,source_record_version_id,is_ambiguous)
               SELECT %s,entity_type,alias_text,alias_normalized,alias_kind,language,taxon_id,
                      source_release_id,source_record_version_id,is_ambiguous
               FROM pv_core.entity_alias WHERE entity_id=%s ON CONFLICT DO NOTHING""",
            (str(canonical_id), str(duplicate_id)),
        )
        cur.execute(
            """INSERT INTO pv_core.trial_asset_link
                 (nct_id,asset_entity_id,intervention_mention_id,link_role,source_record_version_id,
                  resolution_status,resolution_method,support_text,llm_decision_id)
               SELECT nct_id,%s,intervention_mention_id,link_role,source_record_version_id,
                      resolution_status,resolution_method,support_text,llm_decision_id
               FROM pv_core.trial_asset_link WHERE asset_entity_id=%s ON CONFLICT DO NOTHING""",
            (str(canonical_id), str(duplicate_id)),
        )
        cur.execute(
            """INSERT INTO pv_evidence.asset_target_assertion
                 (asset_entity_id,target_entity_id,action_literal,action_normalized,role,directness,
                  source_record_version_id,support_quote,assertion_date,source_native_id,
                  support_locator,relationship_origin)
               SELECT %s,target_entity_id,action_literal,action_normalized,role,directness,
                      source_record_version_id,support_quote,assertion_date,source_native_id,
                      support_locator,relationship_origin
               FROM pv_evidence.asset_target_assertion WHERE asset_entity_id=%s ON CONFLICT DO NOTHING""",
            (str(canonical_id), str(duplicate_id)),
        )
        cur.execute(
            """UPDATE pv_evidence.llm_proposal_verification SET verified_entity_id=%s
               WHERE verified_entity_id=%s""", (str(canonical_id), str(duplicate_id)),
        )
        cur.execute("DELETE FROM pv_core.trial_asset_link WHERE asset_entity_id=%s", (str(duplicate_id),))
        cur.execute("DELETE FROM pv_evidence.asset_target_assertion WHERE asset_entity_id=%s", (str(duplicate_id),))
        cur.execute("DELETE FROM pv_core.entity_alias WHERE entity_id=%s", (str(duplicate_id),))
        cur.execute("DELETE FROM pv_core.entity_identifier WHERE entity_id=%s", (str(duplicate_id),))
        cur.execute("DELETE FROM pv_core.asset WHERE entity_id=%s", (str(duplicate_id),))
        cur.execute("DELETE FROM pv_core.entity WHERE entity_id=%s", (str(duplicate_id),))
    conn.commit()


def promote_asset(conn: Any, chembl: Archive, pubchem: Archive,
                  molecule: dict[str, Any], version_id: int) -> uuid.UUID:
    chembl_id = molecule["molecule_chembl_id"]
    pubchem_row = pubchem_identity(pubchem, molecule)
    exact_inn_names = sorted({
        row.get("molecule_synonym") for row in molecule.get("molecule_synonyms") or []
        if row.get("syn_type") == "INN" and row.get("molecule_synonym")
    }, key=lambda value: (len(value), value.casefold()))
    regional_inn_names = sorted({
        row.get("molecule_synonym") for row in molecule.get("molecule_synonyms") or []
        if str(row.get("syn_type") or "").startswith("INN") and row.get("molecule_synonym")
    }, key=lambda value: (len(value), value.casefold()))
    inn_names = exact_inn_names or regional_inn_names
    if pubchem_row:
        cid, pubchem_title, pubchem_version = pubchem_row
        # Identity comes from PubChem/InChIKey; display preference is an INN
        # when ChEMBL supplies one, then the ChEMBL preferred name.
        preferred = (inn_names[0] if inn_names else molecule.get("pref_name") or pubchem_title).lower()
        asset_id = uuid.uuid5(ASSET_NAMESPACE, f"pubchem:{cid}")
    else:
        cid, pubchem_version = None, None
        preferred = (molecule.get("pref_name") or chembl_id).lower()
        asset_id = uuid.uuid5(ASSET_NAMESPACE, f"chembl:{chembl_id.lower()}")
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO pv_core.entity(entity_id,entity_type,preferred_name)
               VALUES (%s,'asset',%s) ON CONFLICT (entity_id) DO UPDATE SET preferred_name=EXCLUDED.preferred_name""",
            (str(asset_id), preferred),
        )
        cur.execute(
            """INSERT INTO pv_core.asset(entity_id,asset_kind,active_moiety_name)
               VALUES (%s,'small_molecule',%s) ON CONFLICT (entity_id)
               DO UPDATE SET active_moiety_name=EXCLUDED.active_moiety_name""",
            (str(asset_id), preferred),
        )
        insert_identifier(cur, asset_id, "ChEMBL", chembl_id, chembl.release_id, not pubchem_row)
        if cid is not None:
            insert_identifier(cur, asset_id, "PubChem CID", str(cid), pubchem.release_id, True)
            insert_alias(cur, asset_id, "asset", pubchem_title, "pubchem_title",
                         pubchem.release_id, pubchem_version)
        insert_alias(cur, asset_id, "asset", molecule.get("pref_name") or chembl_id,
                     "preferred", chembl.release_id, version_id)
        seen: set[str] = set()
        for synonym in molecule.get("molecule_synonyms") or []:
            text = synonym.get("molecule_synonym")
            if text and normalized(text) not in seen:
                kind, ambiguous, language = classify_chembl_asset_alias(synonym)
                insert_alias(
                    cur, asset_id, "asset", text, kind, chembl.release_id, version_id,
                    ambiguous, language,
                )
                seen.add(normalized(text))
    conn.commit()
    if pubchem_row:
        reconcile_asset_identity(conn, asset_id, uuid.uuid5(ASSET_NAMESPACE, f"chembl:{chembl_id.lower()}"))
    return asset_id


def promote_target(conn: Any, chembl: Archive, hgnc: Archive, uniprot: Archive,
                   chembl_id: str) -> tuple[uuid.UUID, dict[str, Any], int]:
    payload, chembl_version = chembl.retrieve(
        f"target:{chembl_id}", chembl_id, f"{CHEMBL_BASE}/target/{chembl_id}.json",
        chembl_id, "target_record", "ChEMBL 37",
    )
    components = payload.get("target_components") or []
    gene_symbols = []
    for component in components:
        gene_symbols += [s["component_synonym"] for s in component.get("target_component_synonyms") or []
                         if s.get("syn_type") == "GENE_SYMBOL"]
    human_single = payload.get("organism") == "Homo sapiens" and len(components) == 1 and gene_symbols
    hgnc_record = None
    hgnc_version = None
    uniprot_record = None
    uniprot_version = None
    if human_single:
        symbol = gene_symbols[0]
        url = f"https://rest.genenames.org/fetch/symbol/{urllib.parse.quote(symbol)}"
        response, hgnc_version = hgnc.retrieve(f"symbol:{symbol}", symbol, url, f"symbol:{symbol}", "gene_search")
        docs = (response.get("response") or {}).get("docs") or []
        if len(docs) == 1:
            hgnc_record = docs[0]
            accession = components[0].get("accession")
            if accession:
                uniprot_record, uniprot_version = uniprot.retrieve(
                    f"accession:{accession}", accession,
                    f"https://rest.uniprot.org/uniprotkb/{urllib.parse.quote(accession)}.json",
                    accession, "protein_identity_record",
                )
    if hgnc_record:
        hgnc_id = hgnc_record["hgnc_id"]
        target_id = uuid.uuid5(TARGET_NAMESPACE, f"hgnc:{hgnc_id.split(':')[-1].lower()}")
        symbol = hgnc_record["symbol"]
        name = hgnc_record["name"]
        kind = "protein"
        accession = components[0].get("accession")
    else:
        target_id = uuid.uuid5(TARGET_NAMESPACE, f"chembl-target:{chembl_id.lower()}")
        symbol = None
        name = payload.get("pref_name") or chembl_id
        kind_map = {"SINGLE PROTEIN": "protein", "PROTEIN FAMILY": "protein_family",
                    "PROTEIN COMPLEX": "protein_complex",
                    "PROTEIN COMPLEX GROUP": "protein_family",
                    "PROTEIN GROUP": "protein_family",
                    "NUCLEIC-ACID": "nucleic_acid"}
        kind = kind_map.get(payload.get("target_type"), "other")
        accession = components[0].get("accession") if len(components) == 1 else None
        hgnc_id = None
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO pv_core.entity(entity_id,entity_type,preferred_name)
               VALUES (%s,'target',%s) ON CONFLICT (entity_id) DO UPDATE SET preferred_name=EXCLUDED.preferred_name""",
            (str(target_id), symbol or name),
        )
        cur.execute(
            """INSERT INTO pv_core.target
                 (entity_id,hgnc_id,approved_symbol,approved_name,taxon_id,uniprot_accession,target_kind)
               VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (entity_id) DO UPDATE SET
                 hgnc_id=EXCLUDED.hgnc_id,approved_symbol=EXCLUDED.approved_symbol,
                 approved_name=EXCLUDED.approved_name,uniprot_accession=EXCLUDED.uniprot_accession,
                 target_kind=EXCLUDED.target_kind""",
            (str(target_id), hgnc_id, symbol, name, 9606 if payload.get("organism") == "Homo sapiens" else 0,
             accession, kind),
        )
        insert_identifier(cur, target_id, "ChEMBL Target", chembl_id, chembl.release_id, not hgnc_record)
        insert_alias(cur, target_id, "target", name, "chembl_preferred_name", chembl.release_id, chembl_version)
        if hgnc_record:
            insert_identifier(cur, target_id, "HGNC", hgnc_record["hgnc_id"], hgnc.release_id, True)
            insert_alias(cur, target_id, "target", symbol, "approved_symbol", hgnc.release_id, hgnc_version)
            insert_alias(cur, target_id, "target", name, "approved_name", hgnc.release_id, hgnc_version)
            for value in hgnc_record.get("alias_symbol") or []:
                insert_alias(cur, target_id, "target", value, "alias_symbol", hgnc.release_id, hgnc_version, True)
            for value in hgnc_record.get("prev_symbol") or []:
                insert_alias(cur, target_id, "target", value, "previous_symbol", hgnc.release_id, hgnc_version, True)
            if accession and uniprot_version:
                insert_identifier(cur, target_id, "UniProt", accession, uniprot.release_id, True)
                protein = (uniprot_record or {}).get("proteinDescription") or {}
                protein_name = ((((protein.get("recommendedName") or {}).get("fullName") or {}).get("value")))
                if protein_name:
                    insert_alias(cur, target_id, "target", protein_name, "protein_name",
                                 uniprot.release_id, uniprot_version)
        else:
            for component in components:
                component_symbols = [
                    item.get("component_synonym") for item in
                    component.get("target_component_synonyms") or []
                    if item.get("syn_type") == "GENE_SYMBOL" and item.get("component_synonym")
                ]
                resolved_component = None
                hgnc_ids = {
                    xref.get("xref_id") for xref in component.get("target_component_xrefs") or []
                    if xref.get("xref_src_db") == "HGNC" and xref.get("xref_id")
                }
                if len(component_symbols) == 1 and len(hgnc_ids) == 1:
                    component_hgnc = next(iter(hgnc_ids))
                    resolved_component = uuid.uuid5(
                        TARGET_NAMESPACE, f"hgnc:{component_hgnc.split(':')[-1].lower()}"
                    )
                    component_name = component.get("component_description") or component_symbols[0]
                    cur.execute(
                        """INSERT INTO pv_core.entity
                             (entity_id,entity_type,preferred_name,provisional)
                           VALUES (%s,'target',%s,true)
                           ON CONFLICT (entity_id) DO NOTHING""",
                        (str(resolved_component), component_symbols[0]),
                    )
                    cur.execute(
                        """INSERT INTO pv_core.target
                             (entity_id,hgnc_id,approved_symbol,approved_name,taxon_id,
                              uniprot_accession,target_kind)
                           VALUES (%s,%s,%s,%s,9606,%s,'protein')
                           ON CONFLICT (entity_id) DO UPDATE SET
                             hgnc_id=coalesce(pv_core.target.hgnc_id,EXCLUDED.hgnc_id),
                             approved_symbol=coalesce(pv_core.target.approved_symbol,EXCLUDED.approved_symbol),
                             uniprot_accession=coalesce(pv_core.target.uniprot_accession,
                                                        EXCLUDED.uniprot_accession)""",
                        (str(resolved_component), component_hgnc, component_symbols[0],
                         component_name, component.get("accession")),
                    )
                    insert_identifier(cur, resolved_component, "HGNC", component_hgnc,
                                      chembl.release_id, True)
                    if component.get("accession"):
                        insert_identifier(cur, resolved_component, "UniProt",
                                          component["accession"], chembl.release_id, True)
                    insert_alias(cur, resolved_component, "target", component_symbols[0],
                                 "component_gene_symbol", chembl.release_id, chembl_version)
                    insert_alias(cur, resolved_component, "target", component_name,
                                 "component_name", chembl.release_id, chembl_version)
                elif len(component_symbols) == 1:
                    cur.execute(
                        """SELECT entity_id FROM pv_core.target
                           WHERE taxon_id=9606 AND approved_symbol=%s""",
                        (component_symbols[0],),
                    )
                    resolved_row = cur.fetchone()
                    resolved_component = resolved_row[0] if resolved_row else None
                component_key = str(component.get("component_id") or component.get("accession")
                                    or component.get("component_description"))
                cur.execute(
                    """INSERT INTO pv_core.target_component
                         (group_target_entity_id,component_key,component_target_entity_id,
                          gene_symbol_literal,uniprot_accession_literal,component_name_literal,
                          relationship_literal,source_record_version_id)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (group_target_entity_id,component_key,source_record_version_id)
                       DO UPDATE SET component_target_entity_id=EXCLUDED.component_target_entity_id,
                         gene_symbol_literal=EXCLUDED.gene_symbol_literal,
                         uniprot_accession_literal=EXCLUDED.uniprot_accession_literal,
                         component_name_literal=EXCLUDED.component_name_literal,
                         relationship_literal=EXCLUDED.relationship_literal""",
                    (str(target_id), component_key,
                     str(resolved_component) if resolved_component else None,
                     component_symbols[0] if len(component_symbols) == 1 else None,
                     component.get("accession"), component.get("component_description"),
                     component.get("relationship"), chembl_version),
                )
                for synonym in component.get("target_component_synonyms") or []:
                    insert_alias(cur, target_id, "target", synonym.get("component_synonym") or "",
                                 synonym.get("syn_type", "component_synonym").lower(),
                                 chembl.release_id, chembl_version, True)
            cur.execute(
                """UPDATE pv_core.entity_alias SET is_ambiguous=true
                   WHERE entity_id=%s AND source_record_version_id=%s
                     AND alias_kind IN ('gene_symbol','gene_symbol_other','uniprot')""",
                (str(target_id), chembl_version),
            )
    conn.commit()
    return target_id, payload, chembl_version


def proposal_path(kind: str, index: int) -> str:
    return f"$.{kind}[{index}]"


def record_verification(cur: Any, decision_id: int, kind: str, path: str, status: str,
                        entity_id: uuid.UUID | None, source_version_id: int | None,
                        detail: dict[str, Any]) -> None:
    cur.execute(
        """INSERT INTO pv_evidence.llm_proposal_verification
             (llm_decision_id,proposal_kind,proposal_path,verification_status,verified_entity_id,
              verification_source_record_version_id,verifier,verifier_version,detail)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (llm_decision_id,proposal_kind,proposal_path,verifier,verifier_version)
           DO UPDATE SET verification_status=EXCLUDED.verification_status,
             verified_entity_id=EXCLUDED.verified_entity_id,
             verification_source_record_version_id=EXCLUDED.verification_source_record_version_id,
             detail=EXCLUDED.detail""",
        (decision_id, kind, path, status, str(entity_id) if entity_id else None, source_version_id,
         ADAPTER, ADAPTER_VERSION, Json(detail)),
    )


def find_mention(cur: Any, nct_id: str, evidence: list[dict[str, Any]]) -> int | None:
    paths = []
    for row in evidence:
        match = re.match(r"^(.*\.interventions\[[0-9]+\])(?:\..*)?$", row.get("source_path", ""))
        if match:
            paths.append(match.group(1))
    if not paths:
        return None
    cur.execute(
        """SELECT intervention_mention_id FROM pv_core.intervention_mention
           WHERE nct_id=%s AND source_path=ANY(%s) ORDER BY intervention_mention_id LIMIT 1""",
        (nct_id, paths),
    )
    row = cur.fetchone()
    return row[0] if row else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--decision-run-id", default=LLM_RUN_ID)
    parser.add_argument("--nct-id", action="append",
                        help="verify only this trial from the decision run; repeatable")
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    if not args.commit:
        raise SystemExit("This verifier currently requires --commit; all writes are idempotent projections/audit rows.")
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    retrieved_at = datetime.now(timezone.utc)
    archives = {name: Archive(conn, name, retrieved_at, {"decision_run_id": args.decision_run_id})
                for name in ("chembl", "hgnc", "uniprot", "pubchem")}
    chembl, hgnc, uniprot, pubchem = (archives["chembl"], archives["hgnc"],
                                     archives["uniprot"], archives["pubchem"])
    summary = {"resolved_assets": 0, "unresolved_assets": 0, "mechanisms": 0, "targets": set()}
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT task,status FROM pv_evidence.llm_decision_run
                   WHERE decision_run_id=%s""", (args.decision_run_id,),
            )
            run = cur.fetchone()
            if not run:
                raise RuntimeError(f"Unknown decision run: {args.decision_run_id}")
            if run != ("trial_semantic_extraction", "completed"):
                raise RuntimeError(
                    f"Decision run {args.decision_run_id} is not a completed "
                    f"trial_semantic_extraction run: task={run[0]} status={run[1]}"
                )
            decision_sql = """SELECT d.llm_decision_id,d.subject_key,d.parsed_output,t.study_type,
                          t.latest_source_record_version_id
                   FROM pv_evidence.llm_decision d JOIN pv_core.trial t ON t.nct_id=d.subject_key
                   WHERE d.decision_run_id=%s"""
            decision_params: list[Any] = [args.decision_run_id]
            if args.nct_id:
                decision_sql += " AND d.subject_key=ANY(%s)"
                decision_params.append(args.nct_id)
            decision_sql += " ORDER BY d.subject_key"
            cur.execute(decision_sql, decision_params)
            decisions = cur.fetchall()
        if not decisions:
            raise RuntimeError(f"Decision run {args.decision_run_id} contains no trial decisions")
        for decision_id, nct_id, output, study_type, trial_version_id in decisions:
            resolved: dict[str, tuple[uuid.UUID, dict[str, Any], int]] = {}
            for index, proposal in enumerate(output.get("assets") or []):
                canonical = proposal.get("canonical_name_proposal")
                components = proposal.get("components") or []
                chembl_applicable = (
                    proposal.get("role") in {
                        "experimental_intervention", "active_comparator",
                        "background_therapy", "historical_exposure",
                    }
                    and proposal.get("resolution") in {"active_asset", "regimen"}
                )
                candidates = ([canonical, *components] if chembl_applicable else [])
                candidates = list(dict.fromkeys(x for x in candidates if x))
                match = None
                matched_name = None
                for candidate in candidates:
                    match = exact_parent(chembl, candidate)
                    if match:
                        matched_name = candidate
                        break
                with conn.cursor() as cur:
                    if not match:
                        if (proposal.get("resolution") in {"non_therapeutic", "placebo"}
                                or proposal.get("role") in {"behavior", "inactive_comparator"}):
                            status = "not_applicable"
                            reason = "not_a_small_molecule_asset"
                        else:
                            status = "unresolved"
                            reason = ("requires_biologic_or_vaccine_authority" if output.get("trial_kind") == "vaccine"
                                      else "no_unique_exact_chembl_parent")
                        record_verification(cur, decision_id, "asset", proposal_path("assets", index), status,
                                            None, None, {"searched": candidates, "reason": reason})
                        if status == "unresolved":
                            summary["unresolved_assets"] += 1
                        conn.commit()
                        continue
                molecule, molecule_version = match
                asset_id = promote_asset(conn, chembl, pubchem, molecule, molecule_version)
                resolved[normalized(matched_name or canonical)] = (asset_id, molecule, molecule_version)
                for name in [canonical, proposal.get("literal_name"), *components]:
                    if name:
                        resolved[normalized(name)] = (asset_id, molecule, molecule_version)
                with conn.cursor() as cur:
                    mention_id = find_mention(cur, nct_id, proposal.get("evidence") or [])
                    role = ROLE_MAP.get(proposal.get("role"), "registered_intervention")
                    if study_type == "OBSERVATIONAL" and mention_id is None:
                        role = "historical_exposure"
                    support = (proposal.get("evidence") or [{}])[0].get("quote")
                    cur.execute(
                        """INSERT INTO pv_core.trial_asset_link
                             (nct_id,asset_entity_id,intervention_mention_id,link_role,
                              source_record_version_id,resolution_status,resolution_method,support_text,llm_decision_id)
                           VALUES (%s,%s,%s,%s,%s,'resolved','llm_proposal_then_chembl_deterministic_parent',%s,%s)
                           ON CONFLICT DO NOTHING""",
                        (nct_id, str(asset_id), mention_id, role, trial_version_id, support, decision_id),
                    )
                    if mention_id:
                        cur.execute(
                            """UPDATE pv_core.trial_asset_link SET
                                 resolution_method='llm_proposal_then_chembl_deterministic_parent',
                                 support_text=COALESCE(%s,support_text),llm_decision_id=%s
                               WHERE nct_id=%s AND asset_entity_id=%s AND intervention_mention_id=%s
                                 AND source_record_version_id=%s AND link_role=%s""",
                            (support, decision_id, nct_id, str(asset_id), mention_id,
                             trial_version_id, role),
                        )
                        cur.execute(
                            """DELETE FROM pv_core.trial_asset_link
                               WHERE nct_id=%s AND asset_entity_id=%s AND intervention_mention_id IS NULL
                                 AND source_record_version_id=%s AND llm_decision_id=%s
                                 AND link_role=%s""",
                            (nct_id, str(asset_id), trial_version_id, decision_id, role),
                        )
                    if mention_id and role in {"active_comparator", "inactive_comparator"}:
                        cur.execute(
                            """DELETE FROM pv_core.trial_asset_link
                               WHERE nct_id=%s AND asset_entity_id=%s AND intervention_mention_id=%s
                                 AND source_record_version_id=%s
                                 AND link_role='registered_intervention' AND llm_decision_id IS NULL""",
                            (nct_id, str(asset_id), mention_id, trial_version_id),
                        )
                    if mention_id:
                        cur.execute("UPDATE pv_core.intervention_mention SET normalization_status='resolved' WHERE intervention_mention_id=%s",
                                    (mention_id,))
                    record_verification(cur, decision_id, "asset", proposal_path("assets", index), "verified",
                                        asset_id, molecule_version,
                                        {"matched_name": matched_name,
                                         "chembl_parent": molecule["molecule_chembl_id"],
                                         "match_method": molecule.get("_pv_resolution_method")})
                conn.commit()
                summary["resolved_assets"] += 1

            enumerated: dict[uuid.UUID, list[dict[str, Any]]] = {}
            unique_assets = {str(row[0]): row for row in resolved.values()}.values()
            for asset_id, molecule, _ in unique_assets:
                for mechanism, mechanism_version in complete_mechanisms(chembl, molecule["molecule_chembl_id"]):
                    target_id, _, _ = promote_target(conn, chembl, hgnc, uniprot, mechanism["target_chembl_id"])
                    enumerated.setdefault(asset_id, []).append(mechanism)
                    summary["targets"].add(str(target_id))
                    with conn.cursor() as cur:
                        cur.execute(
                            """INSERT INTO pv_evidence.asset_target_assertion
                                 (asset_entity_id,target_entity_id,action_literal,action_normalized,role,directness,
                                  source_record_version_id,support_quote,source_native_id,support_locator,relationship_origin)
                               VALUES (%s,%s,%s,%s,'therapeutic_primary',%s,%s,%s,%s,%s,'structured_database')
                               ON CONFLICT DO NOTHING""",
                            (str(asset_id), str(target_id), mechanism.get("action_type") or "UNKNOWN",
                             ACTION_MAP.get(mechanism.get("action_type") or "", "unknown"),
                             "direct" if mechanism.get("direct_interaction") == 1 else "unknown",
                             mechanism_version, mechanism_support_quote(mechanism),
                             f"ChEMBL mechanism:{mechanism['mec_id']}",
                             Json({"mec_id": mechanism["mec_id"],
                                   "target_chembl_id": mechanism["target_chembl_id"],
                                   "molecule_chembl_id": mechanism["molecule_chembl_id"],
                                   "mechanism_of_action": mechanism.get("mechanism_of_action"),
                                   "binding_site_comment": mechanism.get("binding_site_comment"),
                                   "action_type": mechanism.get("action_type"),
                                   "direct_interaction": mechanism.get("direct_interaction")})),
                        )
                    conn.commit()
                    summary["mechanisms"] += 1

            for index, proposal in enumerate(output.get("pharmacology") or []):
                asset_row = resolved.get(normalized(proposal.get("asset_name") or ""))
                status, target_id, version_id = "unsupported", None, None
                matches: list[dict[str, Any]] = []
                if asset_row:
                    for mechanism in enumerated.get(asset_row[0], []):
                        target_chembl = mechanism.get("target_chembl_id")
                        with conn.cursor() as cur:
                            cur.execute(
                                """SELECT t.entity_id,t.approved_symbol,t.approved_name,a.source_record_version_id
                                   FROM pv_core.target t JOIN pv_evidence.asset_target_assertion a
                                     ON a.target_entity_id=t.entity_id
                                   WHERE a.asset_entity_id=%s AND a.source_native_id=%s LIMIT 1""",
                                (str(asset_row[0]), f"ChEMBL mechanism:{mechanism['mec_id']}"),
                            )
                            row = cur.fetchone()
                        proposed_names = {
                            normalized(value) for value in (
                                proposal.get("object_name"), proposal.get("object_symbol_proposal")
                            ) if value and normalized(value)
                        }
                        structured_names = {
                            normalized(value) for value in (
                                row[1] if row else None, row[2] if row else None,
                                mechanism.get("mechanism_of_action"),
                            ) if value and normalized(value)
                        }
                        if row and proposed_names & structured_names:
                            matches.append(mechanism)
                            target_id, version_id = row[0], row[3]
                    if matches:
                        status = "verified"
                    elif proposal.get("claim_level") == "target_complex_or_family" and enumerated.get(asset_row[0]):
                        status = "partially_verified"
                with conn.cursor() as cur:
                    record_verification(cur, decision_id, "pharmacology", proposal_path("pharmacology", index),
                                        status, target_id, version_id,
                                        {"structured_match_mec_ids": [m["mec_id"] for m in matches],
                                         "complete_structured_mec_ids": [m["mec_id"] for m in (enumerated.get(asset_row[0], []) if asset_row else [])]})
                conn.commit()
        for archive in archives.values():
            archive.finish()
    except Exception as exc:
        conn.rollback()
        for archive in archives.values():
            archive.fail(f"{type(exc).__name__}: {exc}")
        raise
    finally:
        conn.close()
    summary["targets"] = sorted(summary["targets"])
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
