-- Evidence facts on their subject (the evidence layer of PR #159, 2026-11-22): one row per dated fact about a gene,
-- a gene and a disease, a cell line or a drug, each with its source and the key of the source rows behind it. The
-- report reads the evidence it scores only through this view (report.evidence_facts); a program's answer to each
-- fact of report.evidence_lines is a lookup over these rows for its targets and its disease as of the year before
-- entry. A view, not a table: it always matches the source tables it reads.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE VIEW preclin.evidence_subject_fact AS
-- Open Targets evidence: the first year of each tier per target, Open Targets disease and source
-- (preclin.ot_evidence_tiers), once per MONDO term the disease is (none for a trait that is not a disease).
SELECT 'ot_tier'::text AS fact_key, t.ens AS ensembl_id, m.mondo_id, t.disease_id, NULL::integer AS moiety_id,
       k.tier AS value, NULL::double precision AS value_num, NULLIF(k.y, 9999) AS known_year,
       jsonb_build_object('source', t.source) AS detail, t.source,
       'ot_evidence'::text AS record_table,
       t.ens || ' ' || t.disease_id || ' ' || CASE WHEN t.source = 'mgi' THEN 'impc' ELSE t.source END AS record_key
FROM preclin.ot_evidence_tiers t
CROSS JOIN LATERAL (VALUES ('any', t.y_any), ('strong', t.y_strong), ('mid', t.y_mid), ('weak', t.y_weak),
                           ('lof_protect', t.y_lof_protect), ('lof_risk', t.y_lof_risk), ('gof_risk', t.y_gof_risk),
                           ('gof_protect', t.y_gof_protect), ('up', t.y_up)) k(tier, y)
LEFT JOIN preclin.ot_disease d ON d.disease_id = t.disease_id
LEFT JOIN LATERAL unnest(d.mondo_ids) m(mondo_id) ON true
WHERE k.y IS NOT NULL
UNION ALL
-- The labelled mechanism of each gene and disease: how its risk variants act and, where some protect, how.
SELECT 'disease_mechanism', g.ensembl_id, g.mondo_id, NULL, NULL, g.risk_mechanism, NULL, g.risk_year,
       jsonb_build_object('protective', g.protective, 'protective_year', g.protective_year,
                          'confidence', g.confidence),
       'llm', 'gene_disease_mechanism', g.ensembl_id || ' ' || g.mondo_id
FROM preclin.gene_disease_mechanism g
UNION ALL
-- Each mouse model of a gene and how it relates to a disease, dated by its first IMPC data release.
SELECT 'mouse_model', r.ensembl_id, r.mondo_id, NULL, NULL, r.relation, NULL, min(e.evidence_year),
       jsonb_build_object('perturbation', r.perturbation, 'model_id', r.model_id),
       'impc', 'mouse_model_relation', r.ensembl_id || ' ' || r.mondo_id || ' ' || r.model_id
FROM preclin.mouse_model_relation r
JOIN preclin.ot_evidence e ON e.target_ensembl = r.ensembl_id AND e.datasource = 'impc'
                          AND e.detail->>'biologicalModelId' = r.model_id
GROUP BY r.ensembl_id, r.mondo_id, r.model_id, r.perturbation, r.relation
UNION ALL
-- Loss-of-function constraint of each gene: its lowest LOEUF (undated: the current gnomAD release).
SELECT 'loeuf', t.ensembl_id, NULL, NULL, NULL, NULL, min(g.loeuf), NULL, '{}'::jsonb, min(g.source),
       'gene_constraint', t.ensembl_id
FROM public.gene_constraint g JOIN public.targets t ON t.id = g.target_id
WHERE t.ensembl_id IS NOT NULL AND g.loeuf IS NOT NULL
GROUP BY t.ensembl_id
UNION ALL
-- Each mouse mutant phenotype of a gene, with its Mammalian Phenotype classes (undated: the current release).
SELECT 'mouse_phenotype', p.target_ensembl, NULL, NULL, NULL, p.phenotype_id, NULL, NULL,
       jsonb_build_object('class_ids', p.class_ids), 'open_targets', 'ot_mouse_phenotype',
       p.target_ensembl || ' ' || p.phenotype_id
FROM preclin.ot_mouse_phenotype p
UNION ALL
-- Each yearly DepMap list of common-essential genes, by the year of the release that listed the gene.
SELECT 'common_essential', h.ensembl_id, NULL, NULL, NULL, 'listed', NULL, e.release_year, '{}'::jsonb, 'depmap',
       'depmap_common_essential', e.release_year || ' ' || e.entrez_id
FROM preclin.depmap_common_essential e JOIN preclin.hgnc_gene h USING (entrez_id)
WHERE h.ensembl_id IS NOT NULL
UNION ALL
-- Each cancer cell line screened for dependencies, with its tumour type and its first public screen.
SELECT 'screened_line', NULL, c.mondo_id, NULL, NULL, c.depmap_id, NULL, min(s.public_year), '{}'::jsonb,
       min(s.dataset), 'cell_screen', c.depmap_id
FROM preclin.cell_line c JOIN preclin.cell_screen s USING (depmap_id)
WHERE c.mondo_id IS NOT NULL
GROUP BY c.depmap_id, c.mondo_id
UNION ALL
-- Each gene a screened cell line depends on, dated by the first public screen that showed it.
SELECT 'dependency', h.ensembl_id, NULL, NULL, NULL, d.depmap_id, NULL, min(s.public_year), '{}'::jsonb,
       min(d.dataset), 'cell_dependency', d.depmap_id || ' ' || d.entrez_id
FROM preclin.cell_dependency d JOIN preclin.cell_screen s USING (depmap_id, dataset)
JOIN preclin.hgnc_gene h ON h.entrez_id = d.entrez_id
WHERE h.ensembl_id IS NOT NULL
GROUP BY h.ensembl_id, d.depmap_id, d.entrez_id
UNION ALL
-- Each ChEMBL potency measurement of a drug's molecules, dated by the document that reported it.
SELECT DISTINCT 'measurement', NULL, NULL, NULL, cm.moiety_id, a.standard_type, a.pchembl_value::float, doc.year,
       jsonb_build_object('target_chembl_id', a.target_chembl_id, 'symbols', t.symbols, 'target_type', t.target_type,
                          'functional', a.assay_type = 'F', 'cell_based', a.bao_format = 'BAO_0000219'),
       'chembl', 'chembl_activity', a.activity_id::text
FROM preclin.chembl_moiety cm
JOIN preclin.chembl_activity a USING (parent_chembl_id)
JOIN preclin.chembl_target t USING (target_chembl_id)
JOIN preclin.chembl_document doc USING (document_chembl_id)
WHERE doc.year IS NOT NULL
UNION ALL
-- Each published study of a drug the literature screen qualified, by kind (for a disease model, once per MONDO
-- term of the modelled disease), dated by publication, with the searches that retrieved it (cutoff and source).
SELECT 'literature', NULL, q.mondo_id, NULL, s.moiety_id, q.kind, NULL,
       (SELECT p.year FROM public.publications p WHERE p.pmid = s.record_id
        UNION ALL SELECT r.year FROM preclin.literature_record r WHERE r.record_id = s.record_id LIMIT 1),
       jsonb_build_object('hits', h.hits), 'literature_screen', 'literature_screen',
       s.moiety_id || ' ' || s.record_id
FROM preclin.literature_screen s
CROSS JOIN LATERAL (SELECT 'animal_disease'::text AS kind, md.mondo_id
                    FROM unnest(s.modelled_diseases) md0(modelled_disease)
                    JOIN preclin.literature_model_disease md USING (modelled_disease)
                    WHERE s.animal_disease AND md.mondo_id IS NOT NULL
                    UNION ALL SELECT 'animal_healthy', NULL WHERE s.animal_healthy
                    UNION ALL SELECT 'human_engagement', NULL WHERE s.human_engagement) q
JOIN (SELECT hit.moiety_id, hit.record_id,
             jsonb_agg(DISTINCT jsonb_build_array(hit.cutoff_year, hit.source)) AS hits
      FROM preclin.literature_hit hit GROUP BY hit.moiety_id, hit.record_id) h
  ON h.moiety_id = s.moiety_id AND h.record_id = s.record_id
UNION ALL
-- Each drug's computed molecular properties (a structure does not change: undated).
SELECT 'molecule_property', NULL, NULL, NULL, p.moiety_id, NULL, NULL, NULL,
       jsonb_build_object('molecular_weight', p.molecular_weight, 'tpsa', p.tpsa, 'hbd', p.hbd,
                          'ro5_violations', p.ro5_violations),
       p.source, 'moiety_property', p.moiety_id::text
FROM preclin.moiety_property p;

COMMENT ON VIEW preclin.evidence_subject_fact IS
    'Every dated fact about a subject (a gene, a gene and a disease, a cell line or a drug) that the evidence lines are scored from, one row per fact, with its source and the key of the source rows behind it. A program''s answer to each fact of the evidence dataset is a lookup over these rows for its targets and its disease as of the year before entry (report.evidence_facts, report.evidence_lines). The precedent facts (approvals, failed trials, safety stops) are read from the program, trial and stop tables the cohorts are built from.';
COMMENT ON COLUMN preclin.evidence_subject_fact.fact_key IS
    'The kind of fact: ot_tier (an Open Targets evidence tier of a target and disease), disease_mechanism, mouse_model, loeuf, mouse_phenotype, common_essential, screened_line, dependency, measurement, literature, molecule_property.';
COMMENT ON COLUMN preclin.evidence_subject_fact.ensembl_id IS 'The gene the fact is about; null for a fact about a drug or a cell line.';
COMMENT ON COLUMN preclin.evidence_subject_fact.mondo_id IS 'The disease the fact is about (MONDO); null for a fact about no disease.';
COMMENT ON COLUMN preclin.evidence_subject_fact.disease_id IS 'The Open Targets disease of an ot_tier fact, which mondo_id maps it to.';
COMMENT ON COLUMN preclin.evidence_subject_fact.moiety_id IS 'The drug (entity) the fact is about; null for a fact about a gene.';
COMMENT ON COLUMN preclin.evidence_subject_fact.value IS 'The answer: the tier, mechanism, relation, phenotype, cell line, assay type or study kind.';
COMMENT ON COLUMN preclin.evidence_subject_fact.value_num IS 'A measured answer: LOEUF, or pChEMBL potency.';
COMMENT ON COLUMN preclin.evidence_subject_fact.known_year IS 'The year the fact became known; null when its source gives no date (undated facts count only on today''s data).';
COMMENT ON COLUMN preclin.evidence_subject_fact.detail IS 'Further attributes of the fact (for a literature fact, the [cutoff year, source] of each search that retrieved it).';
COMMENT ON COLUMN preclin.evidence_subject_fact.source IS 'Where the fact comes from: the evidence source, release dataset or labelling (open text).';
COMMENT ON COLUMN preclin.evidence_subject_fact.record_table IS 'The table holding the source rows behind the fact.';
COMMENT ON COLUMN preclin.evidence_subject_fact.record_key IS 'The key of those rows in record_table, space-separated (for ot_tier: target, Open Targets disease and data source).';

COMMIT;
