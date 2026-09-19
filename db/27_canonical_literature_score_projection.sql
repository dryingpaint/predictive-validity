-- Select one declared target-literature scorer version per target/dimension.
--
-- Historical views used MAX(value_numeric) across every stored extraction.
-- That makes a rerun capable of changing the analytical feature according to
-- whichever version produced the largest score. Prefer v2_proper explicitly
-- and use the latest v1 row only for targets that were not covered by v2. A
-- future scorer version must be activated by a new migration.

BEGIN;

CREATE OR REPLACE VIEW preclin.v_target_literature_evidence_current AS
WITH ranked AS (
  SELECT es.*,
         ROW_NUMBER() OVER (
           PARTITION BY es.subject_id, es.dimension
           ORDER BY
             CASE es.source_version
               WHEN 'v2_proper' THEN 1
               WHEN 'v1' THEN 2
               ELSE 99
             END,
             es.extracted_at DESC,
             es.evidence_id DESC
         ) AS version_rank
  FROM preclin.evidence_score es
  WHERE es.subject_type = 'target'
    AND es.subject_id2 IS NULL
    AND es.source = 'pubmed_haiku'
    AND es.dimension IN (
      'line_b_lit', 'line_c_lit', 'line_d_lit', 'line_e_lit'
    )
    AND es.source_version IN ('v2_proper', 'v1')
)
SELECT evidence_id, subject_id AS target_id, dimension, category,
       value_numeric, source, source_version, confidence, citation_pmids,
       extracted_by, extracted_at
FROM ranked
WHERE version_rank = 1;

COMMENT ON VIEW preclin.v_target_literature_evidence_current IS
'Canonical target-literature projection: prefer v2_proper per target and dimension, fall back to the latest v1 row only when v2 is absent; a new scorer version requires an explicit migration.';

-- Preserve the complete current target-wide schema and replace only the four
-- literature columns with the canonical projection above. Dependent views
-- (including v_program_evidence_wide) continue to use this view automatically.
CREATE OR REPLACE VIEW preclin.v_target_evidence_wide AS
WITH dgi AS (
  SELECT target_id, COUNT(*) AS n_dgidb_drugs
  FROM public.drug_gene_interactions
  GROUP BY target_id
), pdb AS (
  SELECT dt.target_id,
         MAX(tsf.n_pdb_structures) AS n_pdb_structures,
         BOOL_OR(tsf.has_structure) AS has_pdb_structure
  FROM preclin.target_structural_features tsf
  JOIN preclin.drug d ON d.primary_target_chembl = tsf.target_chembl_id
  JOIN preclin.drug_target dt ON dt.drug_id = d.drug_id AND dt.role = 'primary'
  GROUP BY dt.target_id
), ot_men AS (
  SELECT target_id, BOOL_OR(is_mendelian) AS ot_is_mendelian_any
  FROM public.target_evidence
  WHERE is_mendelian IS NOT NULL
  GROUP BY target_id
), nt AS (
  SELECT target_id,
         MAX(CASE tier WHEN 'T4' THEN 4 WHEN 'T3' THEN 3
                       WHEN 'T2' THEN 2 WHEN 'T1' THEN 1 ELSE 0 END)
           AS nelson_best_tier_num,
         MAX(tier) AS nelson_best_tier
  FROM preclin.nelson_tiers
  GROUP BY target_id
), lit AS (
  SELECT target_id,
         MAX(value_numeric) FILTER (WHERE dimension = 'line_b_lit') AS line_b_lit,
         MAX(value_numeric) FILTER (WHERE dimension = 'line_c_lit') AS line_c_lit,
         MAX(value_numeric) FILTER (WHERE dimension = 'line_d_lit') AS line_d_lit,
         MAX(value_numeric) FILTER (WHERE dimension = 'line_e_lit') AS line_e_lit
  FROM preclin.v_target_literature_evidence_current
  GROUP BY target_id
), ev AS (
  SELECT subject_id AS target_id,
         MAX(value_numeric) FILTER (WHERE dimension = 'impc_n_phenotypes') AS impc_n_phenotypes,
         MAX(value_numeric) FILTER (WHERE dimension = 'family_approved_count') AS family_approved_count,
         MAX(value_numeric) FILTER (WHERE dimension = 'gene_approved_count') AS gene_approved_count,
         MAX(value_numeric) FILTER (WHERE dimension = 'sc_tau_specificity') AS sc_tau_specificity,
         MAX(value_numeric) FILTER (WHERE dimension = 'sc_max_cell_value') AS sc_max_cell_value,
         MAX(value_text) FILTER (WHERE dimension = 'sc_max_cell_type') AS sc_max_cell_type,
         MAX(value_numeric) FILTER (WHERE dimension = 'sc_n_cell_types_expressed') AS sc_n_cell_types_expressed,
         MAX(value_numeric) FILTER (WHERE dimension = 'n_go_biological_process') AS n_go_biological_process,
         MAX(value_numeric) FILTER (WHERE dimension = 'n_go_molecular_function') AS n_go_molecular_function,
         MAX(value_numeric) FILTER (WHERE dimension = 'n_go_cellular_component') AS n_go_cellular_component,
         MAX(value_numeric) FILTER (WHERE dimension = 'n_reactome_pathways') AS n_reactome_pathways,
         MAX(value_numeric) FILTER (WHERE dimension = 'n_ppi_partners') AS n_ppi_partners,
         MAX(value_numeric) FILTER (WHERE dimension = 'n_hpo_phenotypes') AS n_hpo_phenotypes,
         MAX(value_numeric) FILTER (WHERE dimension = 'n_causal_diseases') AS n_causal_diseases,
         MAX(value_numeric) FILTER (WHERE dimension = 'n_suggestive_diseases') AS n_suggestive_diseases,
         MAX(value_numeric) FILTER (WHERE dimension = 'tau_specificity') AS tau_specificity,
         MAX(value_numeric) FILTER (WHERE dimension = 'max_tissue_tpm') AS max_tissue_tpm,
         MAX(value_text) FILTER (WHERE dimension = 'max_tissue_name') AS max_tissue_name,
         MAX(value_numeric) FILTER (WHERE dimension = 'n_high_tissues') AS n_high_tissues,
         MAX(value_numeric) FILTER (WHERE dimension = 'ot_rna_expression_max') AS ot_rna_expression_max,
         MAX(value_numeric) FILTER (WHERE dimension = 'ot_somatic_score_max') AS ot_somatic_score_max,
         MAX(value_numeric) FILTER (WHERE dimension = 'max_pchembl_target') AS max_pchembl_target,
         MAX(value_numeric) FILTER (WHERE dimension = 'has_predictive_biomarker') AS has_predictive_biomarker,
         MAX(value_numeric) FILTER (WHERE dimension = 'gwas_n_sig_pretrial') AS gwas_n_sig_pretrial
  FROM preclin.evidence_score
  WHERE subject_type = 'target'
    AND dimension NOT IN (
      'line_b_lit', 'line_c_lit', 'line_d_lit', 'line_e_lit'
    )
  GROUP BY subject_id
), gwas_agg AS (
  SELECT target_id, COUNT(*) AS gwas_n_sig
  FROM public.gwas_associations
  WHERE p_value_mlog >= 7.3
  GROUP BY target_id
), te_agg AS (
  SELECT target_id,
         MAX(overall_score) AS ot_overall_max,
         MAX(genetic_score) AS ot_genetic_max,
         MAX(literature_score) AS ot_literature_max,
         MAX(animal_model_score) AS ot_animal_model_max,
         MAX(known_drug_score) AS ot_known_drug_max
  FROM public.target_evidence
  GROUP BY target_id
)
SELECT t.id AS target_id,
       t.symbol,
       t.family AS target_family,
       t.tdl,
       t.tractability_sm,
       t.tractability_ab,
       t.tractability_protac,
       lit.line_b_lit,
       lit.line_c_lit,
       lit.line_d_lit,
       lit.line_e_lit,
       ev.impc_n_phenotypes,
       ev.family_approved_count,
       ev.gene_approved_count,
       ev.sc_tau_specificity,
       ev.sc_max_cell_value,
       ev.sc_max_cell_type,
       ev.sc_n_cell_types_expressed,
       ev.n_go_biological_process,
       ev.n_go_molecular_function,
       ev.n_go_cellular_component,
       ev.n_reactome_pathways,
       ev.n_ppi_partners,
       ev.n_hpo_phenotypes,
       ev.n_causal_diseases,
       ev.n_suggestive_diseases,
       ev.tau_specificity,
       ev.max_tissue_tpm,
       ev.max_tissue_name,
       ev.n_high_tissues,
       ev.ot_rna_expression_max,
       ev.ot_somatic_score_max,
       ev.max_pchembl_target,
       ev.has_predictive_biomarker,
       ev.gwas_n_sig_pretrial,
       dgi.n_dgidb_drugs,
       pdb.n_pdb_structures,
       pdb.has_pdb_structure,
       ot_men.ot_is_mendelian_any,
       nt.nelson_best_tier,
       nt.nelson_best_tier_num,
       gc.pli AS gnomad_pli,
       gc.loeuf AS gnomad_loeuf,
       gc.oe_lof_upper,
       ges.pan_essential AS depmap_pan_essential,
       ges.mean_effect AS depmap_mean_effect,
       ges.n_dependent_lineages AS depmap_n_dep_lineages,
       gwas_agg.gwas_n_sig,
       (SELECT MAX(cv.classification)
        FROM public.clingen_validity cv WHERE cv.target_id = t.id)
         AS clingen_max_classification,
       (SELECT COUNT(*)
        FROM public.clingen_validity cv
        WHERE cv.target_id = t.id
          AND cv.classification IN ('Definitive', 'Strong'))::integer
         AS clingen_n_strong,
       (SELECT COUNT(*) FROM public.mendelian_associations ma
        WHERE ma.target_id = t.id)::integer AS mendelian_n,
       (SELECT COUNT(*) FROM public.mendelian_associations ma
        WHERE ma.target_id = t.id
          AND ma.inheritance = 'autosomal_dominant')::integer
         AS mendelian_n_dominant,
       (SELECT COUNT(*) FROM public.mendelian_associations ma
        WHERE ma.target_id = t.id
          AND ma.inheritance = 'autosomal_recessive')::integer
         AS mendelian_n_recessive,
       te_agg.ot_overall_max,
       te_agg.ot_genetic_max,
       te_agg.ot_literature_max,
       te_agg.ot_animal_model_max,
       te_agg.ot_known_drug_max
FROM public.targets t
LEFT JOIN lit ON lit.target_id = t.id
LEFT JOIN ev ON ev.target_id = t.id
LEFT JOIN dgi ON dgi.target_id = t.id
LEFT JOIN pdb ON pdb.target_id = t.id
LEFT JOIN ot_men ON ot_men.target_id = t.id
LEFT JOIN nt ON nt.target_id = t.id
LEFT JOIN public.gene_constraint gc ON gc.target_id = t.id
LEFT JOIN public.gene_essentiality_summary ges ON ges.target_id = t.id
LEFT JOIN gwas_agg ON gwas_agg.target_id = t.id
LEFT JOIN te_agg ON te_agg.target_id = t.id;

COMMENT ON VIEW preclin.v_target_evidence_wide IS
'Every evidence dimension per target, wide-form. Literature Lines B-E use the explicit v2_proper projection with latest-v1 fallback rather than a maximum across scorer versions.';

COMMIT;
