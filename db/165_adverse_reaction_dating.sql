-- FAERS side effects dated as of entry: each drug and reaction pair the side-effect fact can reach is counted in FAERS by
-- the year the FDA received its reports (openFDA), and dated by the first year the reports received by then met a
-- signal criterion. Filled by `python -m pipeline.opentargets adverse-dates`.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE preclin.faers_year_count (
    query_kind text NOT NULL CHECK (query_kind IN ('drug', 'reaction', 'pair', 'all')),
    subject_key text NOT NULL,
    moiety_id integer REFERENCES preclin.moiety(moiety_id),
    event text,
    year integer NOT NULL,
    reports integer NOT NULL CHECK ((year = 0) = (reports = 0)),
    source_release_id bigint NOT NULL REFERENCES preclin.evidence_source_release(source_release_id),
    PRIMARY KEY (query_kind, subject_key, year),
    CHECK ((moiety_id IS NOT NULL) = (query_kind IN ('drug', 'pair'))),
    CHECK ((event IS NOT NULL) = (query_kind IN ('reaction', 'pair')))
);
COMMENT ON TABLE preclin.faers_year_count IS
    'FAERS reports by the year the FDA received them (openFDA drug/event, receivedate), for one query: every report (all), the reports naming a drug (drug), naming a reaction (reaction), or both (pair). A drug is found by the UNIIs of its entity and their salts and forms (preclin.unii_parent), else by its name as a generic name. Years with no reports have no row; a query with no reports at all has one row of year 0 and 0 reports.';
COMMENT ON COLUMN preclin.faers_year_count.query_kind IS 'all, drug, reaction or pair: which reports were counted.';
COMMENT ON COLUMN preclin.faers_year_count.subject_key IS 'The query''s subject: empty for all, the moiety_id for drug, the reaction for reaction, moiety_id and reaction for pair.';
COMMENT ON COLUMN preclin.faers_year_count.moiety_id IS 'The drug of a drug or pair count.';
COMMENT ON COLUMN preclin.faers_year_count.event IS 'The reaction (MedDRA preferred term, as preclin.adverse_reaction names it) of a reaction or pair count.';
COMMENT ON COLUMN preclin.faers_year_count.year IS 'Year the FDA received the reports.';
COMMENT ON COLUMN preclin.faers_year_count.reports IS 'Reports received that year.';
COMMENT ON COLUMN preclin.faers_year_count.source_release_id IS 'The openFDA query run (preclin.evidence_source_release).';

CREATE TABLE preclin.faers_signal (
    moiety_id integer NOT NULL REFERENCES preclin.moiety(moiety_id),
    event text NOT NULL,
    signal_year integer,
    dated_through integer NOT NULL,
    reports integer,
    prr double precision,
    chi2 double precision,
    method_id text NOT NULL REFERENCES preclin.analysis_method(method_id),
    PRIMARY KEY (moiety_id, event)
);
COMMENT ON TABLE preclin.faers_signal IS
    'When a drug''s significant FAERS reaction (preclin.adverse_reaction) first became a signal: the first year whose cumulative reports, received by the end of it, met the method''s criterion (Evans 2001: at least 3 reports, proportional reporting ratio at least 2, chi-squared at least 4). Only pairs the side-effect fact can reach: a reaction that is the disease, or one at least 0.8 similar, of a stored evidence entry whose primary target the drug shares.';
COMMENT ON COLUMN preclin.faers_signal.moiety_id IS 'The drug (entity).';
COMMENT ON COLUMN preclin.faers_signal.event IS 'The reaction, as preclin.adverse_reaction names it.';
COMMENT ON COLUMN preclin.faers_signal.signal_year IS 'First year the criterion was met; null when it was not met by dated_through.';
COMMENT ON COLUMN preclin.faers_signal.dated_through IS 'Last year counted.';
COMMENT ON COLUMN preclin.faers_signal.reports IS 'Reports naming the drug and the reaction by the end of signal_year (by dated_through when there is no signal).';
COMMENT ON COLUMN preclin.faers_signal.prr IS 'Proportional reporting ratio at that point.';
COMMENT ON COLUMN preclin.faers_signal.chi2 IS 'Chi-squared (Yates) at that point.';
COMMENT ON COLUMN preclin.faers_signal.method_id IS 'The signal criterion (preclin.analysis_method).';

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
-- Each significant FAERS adverse reaction of a drug that is a MONDO disease, once per term, dated by the first year
-- its reports received by then met the signal criterion (preclin.faers_signal); undated when it was never dated.
SELECT DISTINCT 'adverse_reaction', NULL, m.mondo_id, NULL, cm.moiety_id, a.event, a.llr, s.signal_year,
       jsonb_build_object('reports', a.reports, 'critval', a.critval, 'dated_through', s.dated_through),
       'openfda', 'adverse_reaction', a.chembl_id || ' ' || a.event
FROM preclin.adverse_reaction a
JOIN preclin.chembl_moiety cm ON cm.parent_chembl_id = a.chembl_id
LEFT JOIN preclin.faers_signal s ON s.moiety_id = cm.moiety_id AND s.event = a.event
CROSS JOIN LATERAL unnest(a.mondo_ids) m(mondo_id);

COMMENT ON COLUMN preclin.evidence_subject_fact.known_year IS 'The year the fact became known; null when its source gives no date (undated facts count only on today''s data). An adverse_reaction fact is dated by preclin.faers_signal.signal_year.';

COMMIT;
