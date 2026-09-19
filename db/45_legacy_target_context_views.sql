-- Contextual target evidence that must not be misrepresented as a direct
-- target--phenotype causal assertion.

BEGIN;

CREATE VIEW pv_evidence.v_structured_target_context_evidence AS
SELECT 'constraint:' || gc.target_id::text AS evidence_id,
       tb.target_entity_id,
       CASE WHEN lower(coalesce(gc.source,'')) LIKE '%gnomad%' THEN 'gnomad'
            ELSE coalesce(gc.source,'legacy_postgres') END::text AS source_system_id,
       'population_constraint'::text AS evidence_category,
       'public.gene_constraint'::text AS source_relation,
       gc.target_id::text AS source_row_key,
       jsonb_build_object('target_id',gc.target_id,'source',gc.source) AS source_locator,
       jsonb_build_object('pli',gc.pli,'loeuf',gc.loeuf,
                          'oe_lof_upper',gc.oe_lof_upper,'oe_mis_upper',gc.oe_mis_upper,
                          'mis_z',gc.mis_z,'syn_z',gc.syn_z,
                          'constraint_flags',gc.constraint_flags) AS evidence_detail
FROM public.gene_constraint gc
JOIN pv_core.legacy_target_bridge tb ON tb.public_target_id=gc.target_id

UNION ALL
SELECT 'expression:' || md5(concat_ws(E'\x1f',te.target_id::text,te.source,te.tissue)) AS evidence_id,
       tb.target_entity_id,
       CASE WHEN lower(te.source) LIKE '%gtex%' THEN 'gtex'
            WHEN lower(te.source) LIKE '%hpa%' THEN 'hpa'
            ELSE te.source END::text AS source_system_id,
       'tissue_expression_context'::text AS evidence_category,
       'public.tissue_expression'::text AS source_relation,
       md5(concat_ws(E'\x1f',te.target_id::text,te.source,te.tissue)) AS source_row_key,
       jsonb_build_object('target_id',te.target_id,'source',te.source,'tissue',te.tissue) AS source_locator,
       jsonb_build_object('value',te.value) AS evidence_detail
FROM public.tissue_expression te
JOIN pv_core.legacy_target_bridge tb ON tb.public_target_id=te.target_id

UNION ALL
SELECT 'go:' || md5(concat_ws(E'\x1f',gg.target_id::text,gg.go_id,coalesce(gg.evidence_code,''))) AS evidence_id,
       tb.target_entity_id,
       'gene_ontology'::text AS source_system_id,
       'gene_ontology_annotation'::text AS evidence_category,
       'public.gene_go'::text AS source_relation,
       md5(concat_ws(E'\x1f',gg.target_id::text,gg.go_id,coalesce(gg.evidence_code,''))) AS source_row_key,
       jsonb_build_object('target_id',gg.target_id,'go_id',gg.go_id) AS source_locator,
       jsonb_build_object('evidence_code',gg.evidence_code) AS evidence_detail
FROM public.gene_go gg
JOIN pv_core.legacy_target_bridge tb ON tb.public_target_id=gg.target_id

UNION ALL
SELECT 'reactome:' || tp.id::text AS evidence_id,
       tb.target_entity_id,
       'reactome'::text AS source_system_id,
       'pathway_membership'::text AS evidence_category,
       'public.target_pathways'::text AS source_relation,
       tp.id::text AS source_row_key,
       jsonb_build_object('id',tp.id,'target_id',tp.target_id,'pathway_id',tp.pathway_id) AS source_locator,
       jsonb_build_object('reactome_id',p.reactome_id,'pathway_name',p.name,
                          'category',p.category,'gene_count',p.gene_count) AS evidence_detail
FROM public.target_pathways tp
JOIN public.pathways p ON p.id=tp.pathway_id
JOIN pv_core.legacy_target_bridge tb ON tb.public_target_id=tp.target_id

UNION ALL
SELECT 'depmap:' || md5(concat_ws(E'\x1f',ge.target_id::text,ge.cell_line_id::text)) AS evidence_id,
       tb.target_entity_id,
       'depmap'::text AS source_system_id,
       'cell_line_dependency'::text AS evidence_category,
       'public.gene_essentiality'::text AS source_relation,
       md5(concat_ws(E'\x1f',ge.target_id::text,ge.cell_line_id::text)) AS source_row_key,
       jsonb_build_object('target_id',ge.target_id,'cell_line_id',ge.cell_line_id,
                          'depmap_id',cl.depmap_id) AS source_locator,
       jsonb_build_object('gene_effect',ge.gene_effect,'cell_line_name',cl.name,
                          'primary_disease',cl.primary_disease,'lineage',cl.lineage,
                          'oncotree_lineage',cl.oncotree_lineage,
                          'oncotree_subtype',cl.oncotree_subtype,
                          'sex',cl.sex,'age',cl.age,'cell_line_source',cl.source) AS evidence_detail
FROM public.gene_essentiality ge
JOIN public.cell_lines cl ON cl.id=ge.cell_line_id
JOIN pv_core.legacy_target_bridge tb ON tb.public_target_id=ge.target_id

UNION ALL
SELECT 'impc_summary:' || es.evidence_id::text AS evidence_id,
       tb.target_entity_id,
       'impc'::text AS source_system_id,
       'aggregated_model_phenotype_summary'::text AS evidence_category,
       'preclin.evidence_score'::text AS source_relation,
       es.evidence_id::text AS source_row_key,
       jsonb_build_object('evidence_id',es.evidence_id,'subject_id',es.subject_id,
                          'dimension',es.dimension,'source_version',es.source_version) AS source_locator,
       jsonb_build_object('category',es.category,'value_numeric',es.value_numeric,
                          'value_text',es.value_text,'value_boolean',es.value_boolean,
                          'value_json',es.value_json,'confidence',es.confidence,
                          'citation_pmids',es.citation_pmids,
                          'citation_details',es.citation_details,
                          'extracted_at',es.extracted_at,'extracted_by',es.extracted_by,
                          'notes',es.notes,
                          'interpretation_boundary','aggregated legacy summary; not raw MP/procedure-level evidence') AS evidence_detail
FROM preclin.evidence_score es
JOIN pv_core.legacy_target_bridge tb ON tb.public_target_id=es.subject_id
WHERE es.subject_type='target' AND es.source='impc';

COMMIT;
