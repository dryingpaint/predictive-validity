-- Canonical bridge over the existing phenotype and genetics databases.
--
-- The public.* relations remain the raw legacy records.  These tables record
-- exactly which mutable legacy relation was observed and how its identifiers
-- resolve to PV entities.  The union view is the sole analysis-facing surface;
-- it does not imply that an Open Targets aggregate or a mapped GWAS gene is a
-- causal target--phenotype assertion.

BEGIN;

CREATE TABLE pv_source.legacy_table_snapshot (
  legacy_table_snapshot_id BIGSERIAL PRIMARY KEY,
  source_release_id        BIGINT NOT NULL REFERENCES pv_source.source_release(source_release_id),
  source_schema            TEXT NOT NULL,
  source_table             TEXT NOT NULL,
  captured_at              TIMESTAMPTZ NOT NULL,
  row_count                BIGINT NOT NULL CHECK (row_count >= 0),
  schema_sha256            TEXT NOT NULL CHECK (schema_sha256 ~ '^[0-9a-f]{64}$'),
  content_fingerprint      JSONB NOT NULL,
  immutability_status      TEXT NOT NULL CHECK (
    immutability_status IN ('mutable_legacy_table','frozen_export')
  ),
  notes                    TEXT NOT NULL,
  CHECK (jsonb_typeof(content_fingerprint) = 'object'),
  UNIQUE (source_release_id,source_schema,source_table)
);

CREATE TABLE pv_core.legacy_target_bridge (
  public_target_id       INTEGER PRIMARY KEY REFERENCES public.targets(id),
  target_entity_id       UUID NOT NULL REFERENCES pv_core.target(entity_id),
  resolution_method      TEXT NOT NULL,
  source_release_id      BIGINT NOT NULL REFERENCES pv_source.source_release(source_release_id),
  resolved_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(resolution_method) <> '')
);
CREATE INDEX pv_legacy_target_bridge_entity_idx
  ON pv_core.legacy_target_bridge(target_entity_id);

CREATE TABLE pv_core.legacy_phenotype_bridge (
  source_system_id       TEXT NOT NULL REFERENCES pv_source.source_system(source_system_id),
  native_identifier      TEXT NOT NULL,
  source_release_id      BIGINT NOT NULL REFERENCES pv_source.source_release(source_release_id),
  phenotype_entity_id    UUID NOT NULL REFERENCES pv_core.phenotype(entity_id),
  native_label           TEXT,
  resolution_method      TEXT NOT NULL,
  resolved_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(native_identifier) <> ''),
  CHECK (btrim(resolution_method) <> ''),
  PRIMARY KEY (source_system_id,native_identifier,source_release_id)
);
CREATE INDEX pv_legacy_phenotype_bridge_entity_idx
  ON pv_core.legacy_phenotype_bridge(phenotype_entity_id);

CREATE VIEW pv_evidence.v_legacy_hpo_target_phenotype AS
SELECT 'hpo:' || md5(concat_ws(E'\x1f',gp.target_id::text,gp.hpo_id,
                               coalesce(gp.disease_source_id,''),coalesce(gp.frequency,''))) AS evidence_id,
       tb.target_entity_id,
       pb.phenotype_entity_id,
       'hpo'::text AS source_system_id,
       'hpo'::text AS origin_source_system_id,
       'human_phenotype_annotation'::text AS evidence_category,
       'gene associated with disease-mediated HPO phenotype'::text AS relationship_literal,
       NULL::text AS direction,
       NULL::date AS assertion_date,
       'public.gene_phenotypes'::text AS source_relation,
       md5(concat_ws(E'\x1f',gp.target_id::text,gp.hpo_id,
                     coalesce(gp.disease_source_id,''),coalesce(gp.frequency,''))) AS source_row_key,
       jsonb_build_object('target_id',gp.target_id,'hpo_id',gp.hpo_id,
                          'disease_source_id',gp.disease_source_id) AS source_locator,
       jsonb_build_object('frequency',gp.frequency,
                          'disease_source_id',gp.disease_source_id) AS evidence_detail,
       false AS is_direct_causal_assertion
FROM public.gene_phenotypes gp
JOIN pv_core.legacy_target_bridge tb ON tb.public_target_id=gp.target_id
JOIN pv_core.legacy_phenotype_bridge pb
  ON pb.source_system_id='hpo' AND pb.native_identifier=gp.hpo_id;

CREATE VIEW pv_evidence.v_legacy_gwas_target_phenotype AS
SELECT 'gwas:' || g.id::text AS evidence_id,
       tb.target_entity_id,
       pb.phenotype_entity_id,
       'gwas_catalog'::text AS source_system_id,
       'gwas_catalog'::text AS origin_source_system_id,
       'common_variant_mapped_gene_association'::text AS evidence_category,
       'variant association mapped to gene'::text AS relationship_literal,
       CASE WHEN g.or_or_beta IS NULL THEN NULL ELSE 'reported_effect' END::text AS direction,
       make_date(g.study_year,1,1) AS assertion_date,
       'public.gwas_associations'::text AS source_relation,
       g.id::text AS source_row_key,
       jsonb_build_object('id',g.id,'study_accession',g.study_accession,
                          'rsid',g.rsid) AS source_locator,
       jsonb_build_object('trait',g.trait,'mapped_trait_uri',g.mapped_trait_uri,
                          'p_value',g.p_value,'p_value_mlog',g.p_value_mlog,
                          'or_or_beta',g.or_or_beta,'effect_allele',g.effect_allele,
                          'risk_allele_freq',g.risk_allele_freq,'ci_text',g.ci_text,
                          'context',g.context,'study_pmid',g.study_pmid,
                          'chromosome',g.chromosome,'position',g.position) AS evidence_detail,
       false AS is_direct_causal_assertion
FROM public.gwas_associations g
JOIN pv_core.legacy_target_bridge tb ON tb.public_target_id=g.target_id
JOIN pv_core.legacy_phenotype_bridge pb
  ON pb.source_system_id='gwas_catalog'
 AND pb.native_identifier=coalesce(nullif(g.mapped_trait_uri,''),
       'trait:' || lower(regexp_replace(btrim(g.trait),'[^[:alnum:]]+','_','g')));

CREATE VIEW pv_evidence.v_legacy_open_targets_target_phenotype AS
SELECT 'target_evidence:' || te.id::text AS evidence_id,
       tb.target_entity_id,
       pb.phenotype_entity_id,
       'legacy_postgres'::text AS source_system_id,
       CASE
         WHEN te.source IN ('open_targets','open_targets_api') THEN 'open_targets'
         WHEN te.source='clinvar' THEN 'clinvar'
         WHEN te.source='hpo_lift' THEN 'hpo'
         ELSE coalesce(te.source,'legacy_target_evidence')
       END::text AS origin_source_system_id,
       'integrated_target_disease_evidence'::text AS evidence_category,
       'aggregated target-disease evidence'::text AS relationship_literal,
       te.intervention_direction AS direction,
       te.created_at::date AS assertion_date,
       'public.target_evidence'::text AS source_relation,
       te.id::text AS source_row_key,
       jsonb_build_object('id',te.id,'target_id',te.target_id,
                          'disease_id',te.disease_id,'source',te.source) AS source_locator,
       jsonb_build_object('overall_score',te.overall_score,'genetic_score',te.genetic_score,
                          'somatic_score',te.somatic_score,'known_drug_score',te.known_drug_score,
                          'literature_score',te.literature_score,
                          'rna_expression_score',te.rna_expression_score,
                          'animal_model_score',te.animal_model_score,'l2g_score',te.l2g_score,
                          'confidence',te.confidence,'evidence_type',te.evidence_type,
                          'evidence_detail',te.evidence_detail,'key_pmids',te.key_pmids,
                          'variant_count',te.variant_count,'how_identified',te.how_identified,
                          'is_mendelian',te.is_mendelian,
                          'intervention_direction_source',te.intervention_direction_source,
                          'curator',te.curator,'curation_status',te.curation_status) AS evidence_detail,
       false AS is_direct_causal_assertion
FROM public.target_evidence te
JOIN pv_core.legacy_target_bridge tb ON tb.public_target_id=te.target_id
JOIN pv_core.legacy_phenotype_bridge pb
  ON pb.source_system_id='legacy_postgres'
 AND pb.native_identifier='public.diseases:' || te.disease_id::text;

CREATE VIEW pv_evidence.v_legacy_clingen_target_phenotype AS
SELECT 'clingen:' || md5(concat_ws(E'\x1f',cv.target_id::text,cv.disease_name,
                                   coalesce(cv.disease_mondo,''),cv.classification,
                                   coalesce(cv.mode_of_inheritance,''),
                                   coalesce(cv.classified_date,''))) AS evidence_id,
       tb.target_entity_id,
       pb.phenotype_entity_id,
       'clingen'::text AS source_system_id,
       'clingen'::text AS origin_source_system_id,
       'expert_gene_disease_validity'::text AS evidence_category,
       'ClinGen gene-disease validity classification'::text AS relationship_literal,
       NULL::text AS direction,
       NULL::date AS assertion_date,
       'public.clingen_validity'::text AS source_relation,
       md5(concat_ws(E'\x1f',cv.target_id::text,cv.disease_name,
                     coalesce(cv.disease_mondo,''),cv.classification,
                     coalesce(cv.mode_of_inheritance,''),
                     coalesce(cv.classified_date,''))) AS source_row_key,
       jsonb_build_object('target_id',cv.target_id,'disease_mondo',cv.disease_mondo,
                          'disease_name',cv.disease_name) AS source_locator,
       jsonb_build_object('classification',cv.classification,
                          'mode_of_inheritance',cv.mode_of_inheritance,
                          'sop_version',cv.sop_version,
                          'classified_date',cv.classified_date) AS evidence_detail,
       true AS is_direct_causal_assertion
FROM public.clingen_validity cv
JOIN pv_core.legacy_target_bridge tb ON tb.public_target_id=cv.target_id
JOIN pv_core.legacy_phenotype_bridge pb
  ON pb.source_system_id='clingen'
 AND pb.native_identifier=coalesce(nullif(cv.disease_mondo,''),
       'label:' || lower(regexp_replace(btrim(cv.disease_name),'[^[:alnum:]]+','_','g')));

CREATE VIEW pv_evidence.v_legacy_mendelian_target_phenotype AS
SELECT 'mendelian:' || ma.id::text AS evidence_id,
       tb.target_entity_id,
       pb.phenotype_entity_id,
       CASE WHEN lower(ma.source) IN ('orpha','orphanet') THEN 'orphanet'
            WHEN lower(ma.source)='omim' THEN 'omim'
            ELSE 'legacy_postgres' END::text AS source_system_id,
       lower(ma.source)::text AS origin_source_system_id,
       'mendelian_gene_disease_association'::text AS evidence_category,
       coalesce(ma.association_type,'Mendelian gene-disease association') AS relationship_literal,
       NULL::text AS direction,
       NULL::date AS assertion_date,
       'public.mendelian_associations'::text AS source_relation,
       ma.id::text AS source_row_key,
       jsonb_build_object('id',ma.id,'source',ma.source,'source_id',ma.source_id) AS source_locator,
       jsonb_build_object('phenotype_name',ma.phenotype_name,
                          'inheritance',ma.inheritance,
                          'association_type',ma.association_type) AS evidence_detail,
       true AS is_direct_causal_assertion
FROM public.mendelian_associations ma
JOIN pv_core.legacy_target_bridge tb ON tb.public_target_id=ma.target_id
JOIN pv_core.legacy_phenotype_bridge pb
  ON pb.source_system_id=CASE WHEN lower(ma.source) IN ('orpha','orphanet') THEN 'orphanet'
                              WHEN lower(ma.source)='omim' THEN 'omim'
                              ELSE 'legacy_postgres' END
 AND pb.native_identifier=lower(ma.source) || ':' || ma.source_id;

CREATE VIEW pv_evidence.v_structured_target_phenotype_evidence AS
SELECT * FROM pv_evidence.v_legacy_hpo_target_phenotype
UNION ALL SELECT * FROM pv_evidence.v_legacy_gwas_target_phenotype
UNION ALL SELECT * FROM pv_evidence.v_legacy_open_targets_target_phenotype
UNION ALL SELECT * FROM pv_evidence.v_legacy_clingen_target_phenotype
UNION ALL SELECT * FROM pv_evidence.v_legacy_mendelian_target_phenotype;

COMMIT;
