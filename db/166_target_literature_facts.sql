-- The target-biology literature of issue #154 as evidence facts: every record the screen qualified for a gene and
-- disease, by kind (fact target_literature), and every cutoff a gene and disease was searched to
-- (target_literature_search), so the evidence lines score the literature kinds as of entry like every other fact.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE OR REPLACE VIEW preclin.evidence_subject_fact AS
 SELECT 'ot_tier'::text AS fact_key,
    t.ens AS ensembl_id,
    m.mondo_id,
    t.disease_id,
    NULL::integer AS moiety_id,
    k.tier AS value,
    NULL::double precision AS value_num,
    NULLIF(k.y, 9999) AS known_year,
    jsonb_build_object('source', t.source) AS detail,
    t.source,
    'ot_evidence'::text AS record_table,
    (((t.ens || ' '::text) || t.disease_id) || ' '::text) ||
        CASE
            WHEN t.source = 'mgi'::text THEN 'impc'::text
            ELSE t.source
        END AS record_key
   FROM preclin.ot_evidence_tiers t
     CROSS JOIN LATERAL ( VALUES ('any'::text,t.y_any), ('strong'::text,t.y_strong), ('mid'::text,t.y_mid), ('weak'::text,t.y_weak), ('lof_protect'::text,t.y_lof_protect), ('lof_risk'::text,t.y_lof_risk), ('gof_risk'::text,t.y_gof_risk), ('gof_protect'::text,t.y_gof_protect), ('up'::text,t.y_up)) k(tier, y)
     LEFT JOIN preclin.ot_disease d ON d.disease_id = t.disease_id
     LEFT JOIN LATERAL unnest(d.mondo_ids) m(mondo_id) ON true
  WHERE k.y IS NOT NULL
UNION ALL
 SELECT 'disease_mechanism'::text AS fact_key,
    g.ensembl_id,
    g.mondo_id,
    NULL::text AS disease_id,
    NULL::integer AS moiety_id,
    g.risk_mechanism AS value,
    NULL::double precision AS value_num,
    g.risk_year AS known_year,
    jsonb_build_object('protective', g.protective, 'protective_year', g.protective_year, 'confidence', g.confidence) AS detail,
    'llm'::text AS source,
    'gene_disease_mechanism'::text AS record_table,
    (g.ensembl_id || ' '::text) || g.mondo_id AS record_key
   FROM preclin.gene_disease_mechanism g
UNION ALL
 SELECT 'mouse_model'::text AS fact_key,
    r.ensembl_id,
    r.mondo_id,
    NULL::text AS disease_id,
    NULL::integer AS moiety_id,
    r.relation AS value,
    NULL::double precision AS value_num,
    min(e.evidence_year) AS known_year,
    jsonb_build_object('perturbation', r.perturbation, 'model_id', r.model_id) AS detail,
    'impc'::text AS source,
    'mouse_model_relation'::text AS record_table,
    (((r.ensembl_id || ' '::text) || r.mondo_id) || ' '::text) || r.model_id AS record_key
   FROM preclin.mouse_model_relation r
     JOIN preclin.ot_evidence e ON e.target_ensembl = r.ensembl_id AND e.datasource = 'impc'::text AND (e.detail ->> 'biologicalModelId'::text) = r.model_id
  GROUP BY r.ensembl_id, r.mondo_id, r.model_id, r.perturbation, r.relation
UNION ALL
 SELECT 'loeuf'::text AS fact_key,
    t.ensembl_id,
    NULL::text AS mondo_id,
    NULL::text AS disease_id,
    NULL::integer AS moiety_id,
    NULL::text AS value,
    min(g.loeuf) AS value_num,
    NULL::integer AS known_year,
    '{}'::jsonb AS detail,
    min(g.source) AS source,
    'gene_constraint'::text AS record_table,
    t.ensembl_id AS record_key
   FROM gene_constraint g
     JOIN targets t ON t.id = g.target_id
  WHERE t.ensembl_id IS NOT NULL AND g.loeuf IS NOT NULL
  GROUP BY t.ensembl_id
UNION ALL
 SELECT 'mouse_phenotype'::text AS fact_key,
    p.target_ensembl AS ensembl_id,
    NULL::text AS mondo_id,
    NULL::text AS disease_id,
    NULL::integer AS moiety_id,
    p.phenotype_id AS value,
    NULL::double precision AS value_num,
    NULL::integer AS known_year,
    jsonb_build_object('class_ids', p.class_ids) AS detail,
    'open_targets'::text AS source,
    'ot_mouse_phenotype'::text AS record_table,
    (p.target_ensembl || ' '::text) || p.phenotype_id AS record_key
   FROM preclin.ot_mouse_phenotype p
UNION ALL
 SELECT 'common_essential'::text AS fact_key,
    h.ensembl_id,
    NULL::text AS mondo_id,
    NULL::text AS disease_id,
    NULL::integer AS moiety_id,
    'listed'::text AS value,
    NULL::double precision AS value_num,
    e.release_year AS known_year,
    '{}'::jsonb AS detail,
    'depmap'::text AS source,
    'depmap_common_essential'::text AS record_table,
    (e.release_year || ' '::text) || e.entrez_id AS record_key
   FROM preclin.depmap_common_essential e
     JOIN preclin.hgnc_gene h USING (entrez_id)
  WHERE h.ensembl_id IS NOT NULL
UNION ALL
 SELECT 'screened_line'::text AS fact_key,
    NULL::text AS ensembl_id,
    c.mondo_id,
    NULL::text AS disease_id,
    NULL::integer AS moiety_id,
    c.depmap_id AS value,
    NULL::double precision AS value_num,
    min(s.public_year) AS known_year,
    '{}'::jsonb AS detail,
    min(s.dataset) AS source,
    'cell_screen'::text AS record_table,
    c.depmap_id AS record_key
   FROM preclin.cell_line c
     JOIN preclin.cell_screen s USING (depmap_id)
  WHERE c.mondo_id IS NOT NULL
  GROUP BY c.depmap_id, c.mondo_id
UNION ALL
 SELECT 'dependency'::text AS fact_key,
    h.ensembl_id,
    NULL::text AS mondo_id,
    NULL::text AS disease_id,
    NULL::integer AS moiety_id,
    d.depmap_id AS value,
    NULL::double precision AS value_num,
    min(s.public_year) AS known_year,
    '{}'::jsonb AS detail,
    min(d.dataset) AS source,
    'cell_dependency'::text AS record_table,
    (d.depmap_id || ' '::text) || d.entrez_id AS record_key
   FROM preclin.cell_dependency d
     JOIN preclin.cell_screen s USING (depmap_id, dataset)
     JOIN preclin.hgnc_gene h ON h.entrez_id = d.entrez_id
  WHERE h.ensembl_id IS NOT NULL
  GROUP BY h.ensembl_id, d.depmap_id, d.entrez_id
UNION ALL
 SELECT DISTINCT 'measurement'::text AS fact_key,
    NULL::text AS ensembl_id,
    NULL::text AS mondo_id,
    NULL::text AS disease_id,
    cm.moiety_id,
    a.standard_type AS value,
    a.pchembl_value::double precision AS value_num,
    doc.year AS known_year,
    jsonb_build_object('target_chembl_id', a.target_chembl_id, 'symbols', t.symbols, 'target_type', t.target_type, 'functional', a.assay_type = 'F'::text, 'cell_based', a.bao_format = 'BAO_0000219'::text) AS detail,
    'chembl'::text AS source,
    'chembl_activity'::text AS record_table,
    a.activity_id::text AS record_key
   FROM preclin.chembl_moiety cm
     JOIN preclin.chembl_activity a USING (parent_chembl_id)
     JOIN preclin.chembl_target t USING (target_chembl_id)
     JOIN preclin.chembl_document doc USING (document_chembl_id)
  WHERE doc.year IS NOT NULL
UNION ALL
 SELECT 'literature'::text AS fact_key,
    NULL::text AS ensembl_id,
    q.mondo_id,
    NULL::text AS disease_id,
    s.moiety_id,
    q.kind AS value,
    NULL::double precision AS value_num,
    ( SELECT p.year
           FROM publications p
          WHERE p.pmid = s.record_id
        UNION ALL
         SELECT r.year
           FROM preclin.literature_record r
          WHERE r.record_id = s.record_id
 LIMIT 1) AS known_year,
    jsonb_build_object('hits', h.hits) AS detail,
    'literature_screen'::text AS source,
    'literature_screen'::text AS record_table,
    (s.moiety_id || ' '::text) || s.record_id AS record_key
   FROM preclin.literature_screen s
     CROSS JOIN LATERAL ( SELECT 'animal_disease'::text AS kind,
            md.mondo_id
           FROM unnest(s.modelled_diseases) md0(modelled_disease)
             JOIN preclin.literature_model_disease md USING (modelled_disease)
          WHERE s.animal_disease AND md.mondo_id IS NOT NULL
        UNION ALL
         SELECT 'animal_healthy'::text,
            NULL::text
          WHERE s.animal_healthy
        UNION ALL
         SELECT 'human_engagement'::text,
            NULL::text
          WHERE s.human_engagement) q
     JOIN ( SELECT hit.moiety_id,
            hit.record_id,
            jsonb_agg(DISTINCT jsonb_build_array(hit.cutoff_year, hit.source)) AS hits
           FROM preclin.literature_hit hit
          GROUP BY hit.moiety_id, hit.record_id) h ON h.moiety_id = s.moiety_id AND h.record_id = s.record_id
UNION ALL
 SELECT 'molecule_property'::text AS fact_key,
    NULL::text AS ensembl_id,
    NULL::text AS mondo_id,
    NULL::text AS disease_id,
    p.moiety_id,
    NULL::text AS value,
    NULL::double precision AS value_num,
    NULL::integer AS known_year,
    jsonb_build_object('molecular_weight', p.molecular_weight, 'tpsa', p.tpsa, 'hbd', p.hbd, 'ro5_violations', p.ro5_violations) AS detail,
    p.source,
    'moiety_property'::text AS record_table,
    p.moiety_id::text AS record_key
   FROM preclin.moiety_property p
UNION ALL
 SELECT 'pqtl'::text AS fact_key,
    p.ensembl_id,
    m.mondo_id,
    p.disease_id,
    NULL::integer AS moiety_id,
        CASE
            WHEN p.beta_ratio_sign > 0::double precision THEN 'raises_risk'::text
            ELSE 'lowers_risk'::text
        END AS value,
    p.h4 AS value_num,
        CASE
            WHEN p.gwas_year IS NOT NULL THEN GREATEST(p.gwas_year, p.pqtl_year)
            ELSE NULL::integer
        END AS known_year,
    jsonb_build_object('pqtl_project', p.pqtl_project, 'gwas_study_id', p.gwas_study_id, 'gwas_pmid', p.gwas_pmid) AS detail,
    'open_targets_colocalisation'::text AS source,
    'pqtl_coloc'::text AS record_table,
    (((p.gwas_locus_id || ' '::text) || p.pqtl_locus_id) || ' '::text) || p.disease_id AS record_key
   FROM preclin.pqtl_coloc p
     JOIN preclin.ot_disease d ON d.disease_id = p.disease_id
     CROSS JOIN LATERAL unnest(d.mondo_ids) m(mondo_id)
UNION ALL
 SELECT DISTINCT 'adverse_reaction'::text AS fact_key,
    NULL::text AS ensembl_id,
    m.mondo_id,
    NULL::text AS disease_id,
    cm.moiety_id,
    a.event AS value,
    a.llr AS value_num,
    s.signal_year AS known_year,
    jsonb_build_object('reports', a.reports, 'critval', a.critval, 'dated_through', s.dated_through) AS detail,
    'openfda'::text AS source,
    'adverse_reaction'::text AS record_table,
    (a.chembl_id || ' '::text) || a.event AS record_key
   FROM preclin.adverse_reaction a
     JOIN preclin.chembl_moiety cm ON cm.parent_chembl_id = a.chembl_id
     LEFT JOIN preclin.faers_signal s ON s.moiety_id = cm.moiety_id AND s.event = a.event
     CROSS JOIN LATERAL unnest(a.mondo_ids) m(mondo_id)
UNION ALL
-- Each record the target-literature screen (#154) qualified for a gene and disease, by kind, from each record's latest
-- screen version, dated by publication, with the searches that retrieved it (cutoff and source). Descriptive: the
-- kinds failed #154's registered gate; their coverage and precision are in report/audits/target_literature.md.
SELECT 'target_literature', s.ensembl_id, s.mondo_id, NULL, NULL, k.kind, NULL,
       coalesce((SELECT p.year FROM public.publications p WHERE p.pmid = s.record_id),
                (SELECT r.year FROM preclin.literature_record r WHERE r.record_id = s.record_id),
                (SELECT min(o.year) FROM preclin.target_disease_source o
                 WHERE o.record_id IN (s.record_id, 'PMID:' || s.record_id))),
       jsonb_build_object('agent_is_program_drug', s.agent_is_program_drug, 'screen_version', s.screen_version,
                          'hits', h.hits),
       'target_literature_screen', 'target_literature_screen', s.ensembl_id || ' ' || s.mondo_id || ' ' || s.record_id
FROM (SELECT DISTINCT ON (ensembl_id, mondo_id, record_id) * FROM preclin.target_literature_screen
      ORDER BY ensembl_id, mondo_id, record_id, screen_version DESC) s
CROSS JOIN LATERAL (VALUES ('human_cell_perturbation', s.human_cell_perturbation),
                           ('cell_line_perturbation', s.cell_line_perturbation),
                           ('diseased_tissue_protein', s.diseased_tissue_protein),
                           ('animal_model_pharmacology', s.animal_model_pharmacology),
                           ('mouse_genetic_disease_model', s.mouse_genetic_disease_model),
                           ('observational_biomarker', s.observational_biomarker),
                           ('clinical_observation', s.clinical_observation)) k(kind, shown)
JOIN (SELECT hit.ensembl_id, hit.mondo_id, hit.record_id,
             jsonb_agg(DISTINCT jsonb_build_array(hit.cutoff_year, hit.source)) AS hits
      FROM preclin.target_literature_hit hit GROUP BY 1, 2, 3) h
  ON (h.ensembl_id, h.mondo_id, h.record_id) = (s.ensembl_id, s.mondo_id, s.record_id)
WHERE s.original_data AND s.disease_match = 'same_or_subtype' AND k.shown
UNION ALL
-- Each cutoff a gene and disease's target literature was searched to (#154): PubMed and Europe PMC both stored, so its
-- retrieval up to that year was searched and screened; the year is the cutoff.
SELECT 'target_literature_search', s.ensembl_id, s.mondo_id, NULL, NULL, 'searched', NULL, s.cutoff_year,
       NULL::jsonb, 'target_literature_search', 'target_literature_search',
       s.ensembl_id || ' ' || s.mondo_id || ' ' || s.cutoff_year
FROM preclin.target_literature_search s
WHERE s.source IN ('pubmed', 'europepmc')
GROUP BY s.ensembl_id, s.mondo_id, s.cutoff_year
HAVING count(DISTINCT s.source) = 2;

COMMENT ON COLUMN preclin.evidence_subject_fact.fact_key IS
    'The kind of fact: ot_tier (an Open Targets evidence tier of a target and disease), disease_mechanism, mouse_model, loeuf, mouse_phenotype, common_essential, screened_line, dependency, measurement, literature (a drug''s published study), molecule_property, pqtl (a colocalising cis-pQTL of the gene and a disease, value its direction), adverse_reaction (a significant FAERS reaction of a drug that is a disease), target_literature (a published study of a gene in a disease, value its kind; #154, descriptive), target_literature_search (a cutoff a gene and disease''s target literature was searched to).';
COMMENT ON COLUMN preclin.evidence_subject_fact.value IS 'The answer: the tier, mechanism, relation, phenotype, cell line, assay type, study kind, pQTL direction (raises_risk, lowers_risk), adverse reaction (its MedDRA term), target-literature kind, or searched.';
COMMENT ON COLUMN preclin.evidence_subject_fact.detail IS 'Further attributes of the fact (for a literature or target_literature fact, the [cutoff year, source] of each search that retrieved it; for target_literature also agent_is_program_drug and the screen_version read).';

COMMIT;
