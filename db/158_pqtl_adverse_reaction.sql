-- Two human evidence sources (2026-11-23): the direction protein genetics gives (a cis-pQTL of the target's plasma
-- protein colocalising with a disease GWAS signal) and the significant FAERS adverse reactions of approved drugs, both
-- from Open Targets 26.09, queried in place in BigQuery (the colocalisation table alone is 16 GB). Filled by
-- `python -m pipeline.opentargets pqtl` and `python -m pipeline.opentargets adverse`; read as facts pqtl and
-- adverse_reaction of preclin.evidence_subject_fact.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE preclin.pqtl_coloc (
    gwas_locus_id text NOT NULL,
    pqtl_locus_id text NOT NULL,
    disease_id text NOT NULL,
    ensembl_id text NOT NULL,
    gwas_study_id text NOT NULL,
    gwas_pmid text,
    gwas_year integer,
    pqtl_study_id text NOT NULL,
    pqtl_project text NOT NULL,
    pqtl_year integer NOT NULL,
    h4 double precision NOT NULL CHECK (h4 BETWEEN 0 AND 1),
    beta_ratio_sign double precision NOT NULL CHECK (beta_ratio_sign BETWEEN -1 AND 1 AND beta_ratio_sign <> 0),
    source_release_id bigint NOT NULL REFERENCES preclin.evidence_source_release(source_release_id),
    PRIMARY KEY (gwas_locus_id, pqtl_locus_id, disease_id)
);
CREATE INDEX pqtl_coloc_gene_idx ON preclin.pqtl_coloc (ensembl_id);
COMMENT ON TABLE preclin.pqtl_coloc IS
    'Each cis-pQTL credible set of a target''s plasma protein that colocalises (coloc H4 at least 0.8) with a GWAS credible set of a disease, once per disease the GWAS study is mapped to (Open Targets colocalisation_coloc, credible_set and study). Only targets of our entities (preclin.moiety_target).';
COMMENT ON COLUMN preclin.pqtl_coloc.gwas_locus_id IS 'The GWAS credible set (Open Targets studyLocusId).';
COMMENT ON COLUMN preclin.pqtl_coloc.pqtl_locus_id IS 'The pQTL credible set (Open Targets studyLocusId), cis to the protein''s gene.';
COMMENT ON COLUMN preclin.pqtl_coloc.disease_id IS 'An Open Targets disease the GWAS study is mapped to (preclin.ot_disease, which gives its MONDO terms).';
COMMENT ON COLUMN preclin.pqtl_coloc.ensembl_id IS 'The gene whose protein the pQTL study measured.';
COMMENT ON COLUMN preclin.pqtl_coloc.gwas_study_id IS 'The GWAS study (Open Targets studyId).';
COMMENT ON COLUMN preclin.pqtl_coloc.gwas_pmid IS 'The GWAS study''s publication (PubMed id); null for an unpublished release such as FinnGen''s.';
COMMENT ON COLUMN preclin.pqtl_coloc.gwas_year IS 'Year the GWAS study was published; null when Open Targets gives no publication date.';
COMMENT ON COLUMN preclin.pqtl_coloc.pqtl_study_id IS 'The pQTL study (Open Targets studyId): one protein in one project.';
COMMENT ON COLUMN preclin.pqtl_coloc.pqtl_project IS 'The pQTL project: Sun_2018 (INTERVAL, PMID 29875488) or UKB_PPP_EUR (UK Biobank Pharma Proteomics Project, PMID 37794186).';
COMMENT ON COLUMN preclin.pqtl_coloc.pqtl_year IS 'Year the pQTL project was published (Open Targets gives QTL studies no date).';
COMMENT ON COLUMN preclin.pqtl_coloc.h4 IS 'coloc posterior probability that the two signals share one causal variant.';
COMMENT ON COLUMN preclin.pqtl_coloc.beta_ratio_sign IS 'Mean sign of the GWAS effect over the pQTL effect across the colocalising variants: positive when the allele raising the protein raises disease risk.';
COMMENT ON COLUMN preclin.pqtl_coloc.source_release_id IS 'The Open Targets release queried (preclin.evidence_source_release).';

CREATE TABLE preclin.adverse_reaction (
    chembl_id text NOT NULL,
    meddra_code text NOT NULL,
    event text NOT NULL,
    reports integer NOT NULL CHECK (reports > 0),
    llr double precision NOT NULL,
    critval double precision NOT NULL,
    mondo_ids text[] NOT NULL,
    source_release_id bigint NOT NULL REFERENCES preclin.evidence_source_release(source_release_id),
    PRIMARY KEY (chembl_id, meddra_code)
);
COMMENT ON TABLE preclin.adverse_reaction IS
    'Each adverse reaction reported for a drug in FAERS significantly more often than for other drugs (Open Targets openfda_significant_adverse_drug_reactions: a likelihood-ratio test over every FAERS report to date, so undated). Only drugs that are one of our entities (preclin.chembl_moiety).';
COMMENT ON COLUMN preclin.adverse_reaction.chembl_id IS 'The drug (ChEMBL parent molecule).';
COMMENT ON COLUMN preclin.adverse_reaction.meddra_code IS 'The reaction''s MedDRA preferred term code.';
COMMENT ON COLUMN preclin.adverse_reaction.event IS 'The reaction''s MedDRA preferred term.';
COMMENT ON COLUMN preclin.adverse_reaction.reports IS 'FAERS reports of the drug with the reaction.';
COMMENT ON COLUMN preclin.adverse_reaction.llr IS 'Log-likelihood ratio of the reaction for the drug.';
COMMENT ON COLUMN preclin.adverse_reaction.critval IS 'The drug''s critical value of the log-likelihood ratio (Monte Carlo, 0.95): llr above it is significant.';
COMMENT ON COLUMN preclin.adverse_reaction.mondo_ids IS 'MONDO diseases the reaction is: terms carrying the MedDRA code as a cross-reference, and terms whose label or synonym is the preferred term; empty for a reaction that is no disease in MONDO.';
COMMENT ON COLUMN preclin.adverse_reaction.source_release_id IS 'The Open Targets release queried (preclin.evidence_source_release).';

CREATE OR REPLACE VIEW preclin.evidence_subject_fact AS
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
FROM preclin.moiety_property p
UNION ALL
-- Each cis-pQTL of the gene's protein colocalising with a disease GWAS signal, once per MONDO term of the disease:
-- raises_risk when the allele raising the protein raises risk; dated by the later of the two studies (undated when
-- the GWAS has no publication date).
SELECT 'pqtl', p.ensembl_id, m.mondo_id, p.disease_id, NULL, CASE WHEN p.beta_ratio_sign > 0 THEN 'raises_risk'
       ELSE 'lowers_risk' END, p.h4, CASE WHEN p.gwas_year IS NOT NULL THEN greatest(p.gwas_year, p.pqtl_year) END,
       jsonb_build_object('pqtl_project', p.pqtl_project, 'gwas_study_id', p.gwas_study_id, 'gwas_pmid', p.gwas_pmid),
       'open_targets_colocalisation', 'pqtl_coloc', p.gwas_locus_id || ' ' || p.pqtl_locus_id || ' ' || p.disease_id
FROM preclin.pqtl_coloc p
JOIN preclin.ot_disease d ON d.disease_id = p.disease_id
CROSS JOIN LATERAL unnest(d.mondo_ids) m(mondo_id)
UNION ALL
-- Each significant FAERS adverse reaction of a drug that is a MONDO disease, once per term (undated: today's FAERS).
SELECT DISTINCT 'adverse_reaction', NULL, m.mondo_id, NULL, cm.moiety_id, a.event, a.llr, NULL::integer,
       jsonb_build_object('meddra_code', a.meddra_code, 'reports', a.reports, 'critval', a.critval),
       'openfda', 'adverse_reaction', a.chembl_id || ' ' || a.meddra_code
FROM preclin.adverse_reaction a
JOIN preclin.chembl_moiety cm ON cm.parent_chembl_id = a.chembl_id
CROSS JOIN LATERAL unnest(a.mondo_ids) m(mondo_id);

COMMENT ON COLUMN preclin.evidence_subject_fact.fact_key IS
    'The kind of fact: ot_tier (an Open Targets evidence tier of a target and disease), disease_mechanism, mouse_model, loeuf, mouse_phenotype, common_essential, screened_line, dependency, measurement, literature, molecule_property, pqtl (a colocalising cis-pQTL of the gene and a disease, value its direction), adverse_reaction (a significant FAERS reaction of a drug that is a disease).';
COMMENT ON COLUMN preclin.evidence_subject_fact.disease_id IS 'The Open Targets disease of an ot_tier or pqtl fact, which mondo_id maps it to.';
COMMENT ON COLUMN preclin.evidence_subject_fact.value IS 'The answer: the tier, mechanism, relation, phenotype, cell line, assay type, study kind, pQTL direction (raises_risk, lowers_risk) or adverse reaction (its MedDRA term).';
COMMENT ON COLUMN preclin.evidence_subject_fact.value_num IS 'A measured answer: LOEUF, pChEMBL potency, a pQTL''s coloc H4, or an adverse reaction''s log-likelihood ratio.';

COMMIT;
