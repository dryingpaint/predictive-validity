"""Bridge the existing public genetics/phenotype tables into canonical PV views.

The legacy rows stay in place.  This adapter inventories their current shape,
refuses silent drift, and idempotently resolves only targets that are already in
the trial-derived PV target universe plus all phenotype identifiers referenced by
the supported legacy evidence tables.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

import psycopg2
from psycopg2.extras import Json, execute_values

from pv.ingest.pilot_asset_targets import PHENOTYPE_NAMESPACE


ADAPTER = "pv.ingest.legacy_evidence_bridge"
ADAPTER_VERSION = "1.2.0"
RELEASE_LABEL = "legacy_release_unknown"
RELATIONS = {
    "public.targets": "SELECT count(*),min(id),max(id),max(updated_at) FROM public.targets",
    "public.phenotypes": "SELECT count(*),min(hpo_id),max(hpo_id) FROM public.phenotypes",
    "public.gene_phenotypes": "SELECT count(*),count(DISTINCT target_id),count(DISTINCT hpo_id) FROM public.gene_phenotypes",
    "public.gwas_associations": "SELECT count(*),min(id),max(id),max(study_year) FROM public.gwas_associations",
    "public.diseases": "SELECT count(*),min(id),max(id),max(updated_at) FROM public.diseases",
    "public.target_evidence": "SELECT count(*),min(id),max(id),max(updated_at) FROM public.target_evidence",
    "public.clingen_validity": "SELECT count(*),count(DISTINCT target_id),count(DISTINCT coalesce(disease_mondo,disease_name)) FROM public.clingen_validity",
    "public.mendelian_associations": "SELECT count(*),min(id),max(id),count(DISTINCT target_id) FROM public.mendelian_associations",
    "public.gene_constraint": "SELECT count(*),count(DISTINCT target_id),count(DISTINCT source) FROM public.gene_constraint",
    "public.tissue_expression": "SELECT count(*),count(DISTINCT target_id),count(DISTINCT source),count(DISTINCT tissue) FROM public.tissue_expression",
    "public.gene_go": "SELECT count(*),count(DISTINCT target_id),count(DISTINCT go_id) FROM public.gene_go",
    "public.target_pathways": "SELECT count(*),min(id),max(id),count(DISTINCT target_id) FROM public.target_pathways",
    "public.pathways": "SELECT count(*),min(id),max(id),count(DISTINCT reactome_id) FROM public.pathways",
    "public.gene_essentiality": "SELECT count(*),count(DISTINCT target_id),count(DISTINCT cell_line_id) FROM public.gene_essentiality",
    "public.cell_lines": "SELECT count(*),min(id),max(id),count(DISTINCT depmap_id) FROM public.cell_lines",
    "preclin.evidence_score": "SELECT count(*),min(evidence_id),max(evidence_id),count(*) FILTER (WHERE source='impc') FROM preclin.evidence_score",
}
SOURCE_SYSTEMS = {
    "legacy_postgres": ("Existing predictive-validity PostgreSQL", "legacy_database"),
    "hpo": ("Human Phenotype Ontology", "phenotype"),
    "gwas_catalog": ("NHGRI-EBI GWAS Catalog", "human_genetics"),
    "open_targets": ("Open Targets", "integrated_target_evidence"),
    "clingen": ("Clinical Genome Resource", "human_genetics"),
    "clinvar": ("NCBI ClinVar", "human_genetics"),
    "orphanet": ("Orphanet/Orphadata", "rare_disease"),
    "omim": ("OMIM", "rare_disease"),
    "gnomad": ("Genome Aggregation Database", "human_genetics"),
    "gtex": ("GTEx Project", "expression_and_regulation"),
    "hpa": ("Human Protein Atlas", "expression_and_regulation"),
    "gene_ontology": ("Gene Ontology Consortium", "mechanism_and_pathway"),
    "reactome": ("Reactome", "mechanism_and_pathway"),
    "depmap": ("Broad DepMap", "cell_models"),
    "impc": ("International Mouse Phenotyping Consortium", "model_organism"),
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", value) else None


def ontology_identifier(value: str | None) -> tuple[str, str] | None:
    if not value:
        return None
    text = value.strip()
    match = re.search(r"(?:^|[/#])((?:MONDO|EFO|HP|ORPHA|OMIM)[_:][0-9]+)$", text, re.I)
    if not match:
        match = re.fullmatch(r"((?:MONDO|EFO|HP|ORPHA|OMIM)[_:][0-9]+)", text, re.I)
    if not match:
        return None
    token = match.group(1).upper().replace("_", ":")
    namespace, identifier = token.split(":", 1)
    return namespace, f"{namespace}:{identifier}"


def normalized_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold().strip()).strip("_")


def ensure_sources(cur: Any, retrieved_at: datetime) -> dict[str, int]:
    releases: dict[str, int] = {}
    for source_id, (provider, domain) in SOURCE_SYSTEMS.items():
        cur.execute(
            """INSERT INTO pv_source.source_system(source_system_id,provider,domain)
               VALUES (%s,%s,%s) ON CONFLICT (source_system_id) DO NOTHING""",
            (source_id, provider, domain),
        )
        cur.execute(
            """INSERT INTO pv_source.source_release
                 (source_system_id,release_label,retrieved_at,metadata)
               VALUES (%s,%s,%s,%s)
               ON CONFLICT (source_system_id,release_label) DO UPDATE SET
                 metadata=pv_source.source_release.metadata
               RETURNING source_release_id""",
            (source_id, RELEASE_LABEL, retrieved_at,
             Json({"provenance_status": "legacy_release_unknown", "adapter": ADAPTER})),
        )
        releases[source_id] = cur.fetchone()[0]
    return releases


def relation_schema(cur: Any, schema: str, table: str) -> str:
    cur.execute(
        """SELECT column_name,data_type,is_nullable,coalesce(column_default,'')
           FROM information_schema.columns
           WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position""",
        (schema, table),
    )
    return hashlib.sha256(canonical(cur.fetchall()).encode()).hexdigest()


def snapshot_relations(cur: Any, release_id: int, captured_at: datetime) -> None:
    for relation, stats_sql in RELATIONS.items():
        schema, table = relation.split(".", 1)
        cur.execute(stats_sql)
        stats = list(cur.fetchone())
        row_count = int(stats[0])
        fingerprint = {"statistics": [str(value) if value is not None else None for value in stats]}
        schema_sha = relation_schema(cur, schema, table)
        cur.execute(
            """SELECT row_count,schema_sha256,content_fingerprint
               FROM pv_source.legacy_table_snapshot
               WHERE source_release_id=%s AND source_schema=%s AND source_table=%s""",
            (release_id, schema, table),
        )
        prior = cur.fetchone()
        if prior:
            if prior[0] != row_count or prior[1] != schema_sha or prior[2] != fingerprint:
                raise RuntimeError(
                    f"Legacy source drift for {schema}.{table}; preserve a new frozen export/release "
                    "before refreshing the canonical bridge"
                )
            continue
        cur.execute(
            """INSERT INTO pv_source.legacy_table_snapshot
                 (source_release_id,source_schema,source_table,captured_at,row_count,
                  schema_sha256,content_fingerprint,immutability_status,notes)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,'mutable_legacy_table',%s)""",
            (release_id, schema, table, captured_at, row_count, schema_sha, Json(fingerprint),
             "Legacy release is unknown. Row identity is retained in the source table; "
             "a future official pinned-release adapter must reconcile, not overwrite, it."),
        )


def stage_phenotypes(cur: Any, releases: dict[str, int], inputs: list[tuple[Any, ...]]) -> int:
    """Resolve and upsert phenotype records in set-based statements."""
    cur.execute(
        """SELECT ontology_namespace,ontology_identifier,entity_id
           FROM pv_core.phenotype"""
    )
    existing = {(row[0], row[1]): row[2] for row in cur.fetchall()}
    staged = []
    for source_system_id, native, label, kind, canonical_id, method in inputs:
        label = label or native
        namespace, identifier = canonical_id or (
            f"LEGACY_{source_system_id.upper()}", native
        )
        entity_id = existing.get((namespace, identifier))
        if entity_id is None:
            seed = identifier if canonical_id else f"{namespace}:{identifier}"
            entity_id = uuid.uuid5(PHENOTYPE_NAMESPACE, seed.casefold())
            existing[(namespace, identifier)] = entity_id
        staged.append((
            source_system_id, native, releases[source_system_id], str(entity_id),
            namespace, identifier, label, kind, method, canonical_id is None,
            normalized_label(label),
        ))
    cur.execute(
        """CREATE TEMP TABLE pv_phenotype_stage (
             source_system_id text,native_identifier text,source_release_id bigint,
             entity_id uuid,namespace text,identifier text,label text,kind text,
             method text,provisional boolean,alias_normalized text
           ) ON COMMIT DROP"""
    )
    execute_values(
        cur,
        """INSERT INTO pv_phenotype_stage
             (source_system_id,native_identifier,source_release_id,entity_id,
              namespace,identifier,label,kind,method,provisional,alias_normalized)
           VALUES %s""",
        staged,
        page_size=5000,
    )
    cur.execute(
        """INSERT INTO pv_core.entity(entity_id,entity_type,preferred_name,provisional)
           SELECT DISTINCT ON (entity_id) entity_id,'phenotype',label,provisional
           FROM pv_phenotype_stage ORDER BY entity_id,provisional,label
           ON CONFLICT (entity_id) DO NOTHING"""
    )
    cur.execute(
        """INSERT INTO pv_core.phenotype
             (entity_id,ontology_namespace,ontology_identifier,preferred_name,phenotype_kind)
           SELECT DISTINCT ON (entity_id) entity_id,namespace,identifier,label,kind
           FROM pv_phenotype_stage ORDER BY entity_id,provisional,label
           ON CONFLICT DO NOTHING"""
    )
    cur.execute(
        """INSERT INTO pv_core.entity_identifier
             (entity_id,namespace,identifier,source_release_id,is_preferred)
           SELECT DISTINCT entity_id,namespace,identifier,source_release_id,true
           FROM pv_phenotype_stage ON CONFLICT DO NOTHING"""
    )
    cur.execute(
        """INSERT INTO pv_core.entity_alias
             (entity_id,entity_type,alias_text,alias_normalized,alias_kind,language,
              source_release_id,is_ambiguous)
           SELECT DISTINCT s.entity_id,'phenotype',s.label,s.alias_normalized,
                  'legacy_source_label','en',s.source_release_id,false
           FROM pv_phenotype_stage s
           WHERE NOT EXISTS (
             SELECT 1 FROM pv_core.entity_alias a
             WHERE a.entity_id=s.entity_id AND a.alias_text=s.label
               AND a.alias_kind='legacy_source_label'
               AND a.source_release_id=s.source_release_id
           )"""
    )
    cur.execute(
        """INSERT INTO pv_core.legacy_phenotype_bridge
             (source_system_id,native_identifier,source_release_id,phenotype_entity_id,
              native_label,resolution_method)
           SELECT DISTINCT ON (source_system_id,native_identifier,source_release_id)
                  source_system_id,native_identifier,source_release_id,entity_id,label,method
           FROM pv_phenotype_stage
           ORDER BY source_system_id,native_identifier,source_release_id,label
           ON CONFLICT (source_system_id,native_identifier,source_release_id) DO UPDATE SET
             phenotype_entity_id=EXCLUDED.phenotype_entity_id,
             native_label=EXCLUDED.native_label,
             resolution_method=EXCLUDED.resolution_method
           WHERE (pv_core.legacy_phenotype_bridge.phenotype_entity_id,
                  pv_core.legacy_phenotype_bridge.native_label,
                  pv_core.legacy_phenotype_bridge.resolution_method)
             IS DISTINCT FROM
                 (EXCLUDED.phenotype_entity_id,EXCLUDED.native_label,EXCLUDED.resolution_method)"""
    )
    return len(staged)


def phenotype_rows(cur: Any) -> Iterable[tuple[str, str, str, str, tuple[str, str] | None, str]]:
    cur.execute(
        """SELECT DISTINCT gp.hpo_id,coalesce(p.name,gp.hpo_id)
           FROM public.gene_phenotypes gp
           LEFT JOIN public.phenotypes p ON p.hpo_id=gp.hpo_id
           ORDER BY gp.hpo_id"""
    )
    for native, label in cur.fetchall():
        yield "hpo", native, label, "human_phenotype", ontology_identifier(native), "hpo_identifier"

    cur.execute("SELECT id,name,mondo_id,efo_id FROM public.diseases ORDER BY id")
    for disease_id, label, mondo, efo in cur.fetchall():
        canonical_id = ontology_identifier(mondo) or ontology_identifier(efo)
        yield ("legacy_postgres", f"public.diseases:{disease_id}", label, "disease",
               canonical_id, "public_disease_ontology_id" if canonical_id else "public_disease_native_id")

    cur.execute(
        """SELECT coalesce(nullif(mapped_trait_uri,''),
                    'trait:' || lower(regexp_replace(btrim(trait),'[^[:alnum:]]+','_','g'))) AS native,
                  min(trait)
           FROM public.gwas_associations
           WHERE mapped_trait_uri IS NOT NULL OR trait IS NOT NULL
           GROUP BY 1 ORDER BY 1"""
    )
    for native, label in cur.fetchall():
        yield ("gwas_catalog", native, label, "trait", ontology_identifier(native),
               "mapped_trait_uri" if ontology_identifier(native) else "gwas_native_trait")

    cur.execute(
        """SELECT coalesce(nullif(disease_mondo,''),
                    'label:' || lower(regexp_replace(btrim(disease_name),'[^[:alnum:]]+','_','g'))) AS native,
                  min(disease_name)
           FROM public.clingen_validity GROUP BY 1 ORDER BY 1"""
    )
    for native, label in cur.fetchall():
        yield ("clingen", native, label, "disease", ontology_identifier(native),
               "clingen_mondo" if ontology_identifier(native) else "clingen_native_label")

    cur.execute(
        """SELECT lower(source),lower(source) || ':' || source_id,min(phenotype_name)
           FROM public.mendelian_associations
           GROUP BY lower(source),source_id ORDER BY 1,2"""
    )
    for source, native, label in cur.fetchall():
        system = "orphanet" if source in {"orpha", "orphanet"} else "omim" if source == "omim" else "legacy_postgres"
        canonical_id = ontology_identifier(native)
        yield system, native, label, "disease", canonical_id, "mendelian_source_identifier"


def bridge(commit: bool) -> dict[str, Any]:
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    captured_at = datetime.now(timezone.utc)
    run_id = uuid.uuid4()
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            releases = ensure_sources(cur, captured_at)
            snapshot_relations(cur, releases["legacy_postgres"], captured_at)
            cur.execute(
                """INSERT INTO pv_source.acquisition_run
                     (acquisition_run_id,source_release_id,adapter,adapter_version,git_commit,
                      parameters,status,started_at)
                   VALUES (%s,%s,%s,%s,%s,%s,'running',%s)""",
                (str(run_id), releases["legacy_postgres"], ADAPTER, ADAPTER_VERSION,
                 git_commit(), Json({"relations": sorted(RELATIONS), "projection_only": True}),
                 captured_at),
            )
            cur.execute(
                """DELETE FROM pv_core.legacy_target_bridge bridge
                   WHERE bridge.source_release_id=%s AND NOT EXISTS (
                     SELECT 1 FROM public.targets lt JOIN pv_core.target t
                       ON upper(lt.symbol)=upper(t.approved_symbol) AND t.taxon_id=9606
                     WHERE lt.id=bridge.public_target_id
                       AND t.entity_id=bridge.target_entity_id
                       AND lt.pathogen_type IS NULL
                   )""",
                (releases["legacy_postgres"],),
            )
            removed_target_bridges = cur.rowcount
            cur.execute(
                """INSERT INTO pv_core.legacy_target_bridge
                     (public_target_id,target_entity_id,resolution_method,source_release_id)
                   SELECT lt.id,t.entity_id,'exact_case_insensitive_approved_symbol',%s
                   FROM public.targets lt JOIN pv_core.target t
                     ON upper(lt.symbol)=upper(t.approved_symbol) AND t.taxon_id=9606
                   WHERE lt.pathogen_type IS NULL
                   ON CONFLICT (public_target_id) DO UPDATE SET
                     target_entity_id=EXCLUDED.target_entity_id,
                     resolution_method=EXCLUDED.resolution_method,
                     source_release_id=EXCLUDED.source_release_id
                   WHERE (pv_core.legacy_target_bridge.target_entity_id,
                          pv_core.legacy_target_bridge.resolution_method,
                          pv_core.legacy_target_bridge.source_release_id)
                     IS DISTINCT FROM
                         (EXCLUDED.target_entity_id,EXCLUDED.resolution_method,
                          EXCLUDED.source_release_id)""",
                (releases["legacy_postgres"],),
            )
            target_changes = cur.rowcount
            inputs = list(phenotype_rows(cur))
            phenotype_count = stage_phenotypes(cur, releases, inputs)
            cur.execute("SELECT count(*) FROM pv_core.legacy_target_bridge")
            target_total = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM pv_core.legacy_phenotype_bridge")
            phenotype_total = cur.fetchone()[0]
            cur.execute(
                """UPDATE pv_source.acquisition_run SET status='completed',completed_at=now(),
                     discovered_count=%s,selected_count=%s,stored_count=%s,reused_count=%s
                   WHERE acquisition_run_id=%s""",
                (phenotype_count, phenotype_count, target_changes,
                 max(0, phenotype_count - target_changes), str(run_id)),
            )
        if not commit:
            conn.rollback()
    return {
        "run_id": str(run_id), "committed": commit,
        "target_bridge_total": target_total,
        "phenotype_bridge_total": phenotype_total,
        "phenotype_inputs": phenotype_count,
        "removed_stale_target_bridges": removed_target_bridges,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--commit", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(bridge(args.commit), indent=2))


if __name__ == "__main__":
    main()
