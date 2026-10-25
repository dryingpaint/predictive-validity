-- Drop the legacy layer: every relation no code in pipeline/, report/ or tests/ reads. These are the
-- earlier benchmark's tables and views (preclin.program, approval, evidence_score, classification,
-- llm_run, source_document and the rest), the genome-browser import in public except the three
-- tables the pipeline reads (targets, gene_constraint, publications), and the PV ingestion pilot
-- (pv_core, pv_source, and pv_evidence except llm_decision and llm_decision_run). The foreign keys
-- and link columns from preclin.drug and preclin.indication into the dropped public tables go too.
-- A Neon branch taken before this migration keeps the dropped data.

BEGIN;
SET LOCAL lock_timeout = '30s';
ALTER TABLE preclin.drug DROP CONSTRAINT IF EXISTS drug_therapy_id_fkey;
ALTER TABLE preclin.indication DROP CONSTRAINT IF EXISTS indication_disease_id_fkey;
ALTER TABLE preclin.drug DROP COLUMN IF EXISTS therapy_id;
ALTER TABLE preclin.indication DROP COLUMN IF EXISTS disease_id;
DROP SCHEMA IF EXISTS pv_core, pv_source CASCADE;
DROP MATERIALIZED VIEW IF EXISTS public.opportunities CASCADE;
DROP MATERIALIZED VIEW IF EXISTS public.opportunity_facet_rollup CASCADE;
DROP MATERIALIZED VIEW IF EXISTS public.opportunity_search CASCADE;
DROP VIEW IF EXISTS preclin.v_benchmark_calibration CASCADE;
DROP VIEW IF EXISTS preclin.v_benchmark_leaderboard CASCADE;
DROP VIEW IF EXISTS preclin.v_bio_enrichment_coverage CASCADE;
DROP VIEW IF EXISTS preclin.v_chembl_target_first_approval CASCADE;
DROP VIEW IF EXISTS preclin.v_classification_audit CASCADE;
DROP VIEW IF EXISTS preclin.v_dimension_coverage CASCADE;
DROP VIEW IF EXISTS preclin.v_drug_coverage CASCADE;
DROP VIEW IF EXISTS preclin.v_drug_target CASCADE;
DROP VIEW IF EXISTS preclin.v_drug_target_consensus CASCADE;
DROP VIEW IF EXISTS preclin.v_drug_target_consensus_live CASCADE;
DROP VIEW IF EXISTS preclin.v_drug_target_unambiguous CASCADE;
DROP VIEW IF EXISTS preclin.v_effect_sizes_2x2 CASCADE;
DROP VIEW IF EXISTS preclin.v_evidence_score_audit CASCADE;
DROP VIEW IF EXISTS preclin.v_failure_taxonomy CASCADE;
DROP VIEW IF EXISTS preclin.v_gwas_study_date_latest CASCADE;
DROP VIEW IF EXISTS preclin.v_outcome_summary CASCADE;
DROP VIEW IF EXISTS preclin.v_pathway_wrongness CASCADE;
DROP VIEW IF EXISTS preclin.v_program_clean CASCADE;
DROP VIEW IF EXISTS preclin.v_program_evidence_wide CASCADE;
DROP VIEW IF EXISTS preclin.v_relative_success_clean CASCADE;
DROP VIEW IF EXISTS preclin.v_sub_hypothesis CASCADE;
DROP VIEW IF EXISTS preclin.v_sub_hypothesis_enriched CASCADE;
DROP VIEW IF EXISTS preclin.v_target_evidence_wide CASCADE;
DROP VIEW IF EXISTS preclin.v_target_family_precedent_by_year CASCADE;
DROP VIEW IF EXISTS preclin.v_target_indication_program CASCADE;
DROP VIEW IF EXISTS preclin.v_target_indication_strict_outcome CASCADE;
DROP VIEW IF EXISTS preclin.v_target_literature_evidence_current CASCADE;
DROP VIEW IF EXISTS preclin.v_target_phenotype_evidence CASCADE;
DROP VIEW IF EXISTS preclin.v_ti_canonical CASCADE;
DROP VIEW IF EXISTS preclin.v_ti_within_stats CASCADE;
DROP VIEW IF EXISTS preclin.v_trial_features CASCADE;
DROP VIEW IF EXISTS preclin.v_trial_source_latest CASCADE;
DROP VIEW IF EXISTS public.therapy_by_target CASCADE;
DROP VIEW IF EXISTS public.trial_by_therapy CASCADE;
DROP VIEW IF EXISTS public.underexplored_targets CASCADE;
DROP VIEW IF EXISTS pv_evidence.v_active_asset_indication_literature_candidate CASCADE;
DROP VIEW IF EXISTS pv_evidence.v_active_effective_target_literature_candidate CASCADE;
DROP VIEW IF EXISTS pv_evidence.v_latest_asset_target_context CASCADE;
DROP VIEW IF EXISTS pv_evidence.v_legacy_clingen_target_phenotype CASCADE;
DROP VIEW IF EXISTS pv_evidence.v_legacy_gwas_target_phenotype CASCADE;
DROP VIEW IF EXISTS pv_evidence.v_legacy_hpo_target_phenotype CASCADE;
DROP VIEW IF EXISTS pv_evidence.v_legacy_mendelian_target_phenotype CASCADE;
DROP VIEW IF EXISTS pv_evidence.v_legacy_open_targets_target_phenotype CASCADE;
DROP VIEW IF EXISTS pv_evidence.v_llm_decision_change CASCADE;
DROP VIEW IF EXISTS pv_evidence.v_structured_target_context_evidence CASCADE;
DROP VIEW IF EXISTS pv_evidence.v_structured_target_phenotype_evidence CASCADE;
DROP VIEW IF EXISTS pv_evidence.v_target_indication_literature_candidate CASCADE;
DROP TABLE IF EXISTS preclin.approval CASCADE;
DROP TABLE IF EXISTS preclin.benchmark_prediction CASCADE;
DROP TABLE IF EXISTS preclin.benchmark_run CASCADE;
DROP TABLE IF EXISTS preclin.chembl_target_approval_event CASCADE;
DROP TABLE IF EXISTS preclin.chembl_target_approval_release CASCADE;
DROP TABLE IF EXISTS preclin.chembl_target_mapping CASCADE;
DROP TABLE IF EXISTS preclin.classification CASCADE;
DROP TABLE IF EXISTS preclin.disease_bridge CASCADE;
DROP TABLE IF EXISTS preclin.disease_name_alias CASCADE;
DROP TABLE IF EXISTS preclin.drug_bio_class CASCADE;
DROP TABLE IF EXISTS preclin.drug_target CASCADE;
DROP TABLE IF EXISTS preclin.drug_target_consensus_map CASCADE;
DROP TABLE IF EXISTS preclin.evidence_dimension CASCADE;
DROP TABLE IF EXISTS preclin.evidence_score CASCADE;
DROP TABLE IF EXISTS preclin.gwas_study_date CASCADE;
DROP TABLE IF EXISTS preclin.hpo_phenotypic_abnormality_term CASCADE;
DROP TABLE IF EXISTS preclin.indication_bio_class CASCADE;
DROP TABLE IF EXISTS preclin.ingest_log CASCADE;
DROP TABLE IF EXISTS preclin.llm_run CASCADE;
DROP TABLE IF EXISTS preclin.llm_run_evidence_score CASCADE;
DROP TABLE IF EXISTS preclin.llm_run_source CASCADE;
DROP TABLE IF EXISTS preclin.nelson_tiers CASCADE;
DROP TABLE IF EXISTS preclin.preclinical_ti CASCADE;
DROP TABLE IF EXISTS preclin.program CASCADE;
DROP TABLE IF EXISTS preclin.program_outcome CASCADE;
DROP TABLE IF EXISTS preclin.program_trial CASCADE;
DROP TABLE IF EXISTS preclin.source_document CASCADE;
DROP TABLE IF EXISTS preclin.source_document_subject CASCADE;
DROP TABLE IF EXISTS preclin.sponsor_ta_approval_rate CASCADE;
DROP TABLE IF EXISTS preclin.target_structural_features CASCADE;
DROP TABLE IF EXISTS public.adverse_events CASCADE;
DROP TABLE IF EXISTS public.approvals CASCADE;
DROP TABLE IF EXISTS public.biomarkers CASCADE;
DROP TABLE IF EXISTS public.cell_lines CASCADE;
DROP TABLE IF EXISTS public.clingen_validity CASCADE;
DROP TABLE IF EXISTS public.combination_components CASCADE;
DROP TABLE IF EXISTS public.deep_dive_cache CASCADE;
DROP TABLE IF EXISTS public.disease_evidence_stats CASCADE;
DROP TABLE IF EXISTS public.disease_novelty_stats CASCADE;
DROP TABLE IF EXISTS public.disease_pleiotropy CASCADE;
DROP TABLE IF EXISTS public.disease_sponsor_stats CASCADE;
DROP TABLE IF EXISTS public.disease_therapeutic_phenotypes CASCADE;
DROP TABLE IF EXISTS public.disease_tissue_context CASCADE;
DROP TABLE IF EXISTS public.disease_treatment_cache CASCADE;
DROP TABLE IF EXISTS public.disease_trial_stats CASCADE;
DROP TABLE IF EXISTS public.diseases CASCADE;
DROP TABLE IF EXISTS public.drug_gene_interactions CASCADE;
DROP TABLE IF EXISTS public.endpoints CASCADE;
DROP TABLE IF EXISTS public.evidence_publications CASCADE;
DROP TABLE IF EXISTS public.gene_essentiality CASCADE;
DROP TABLE IF EXISTS public.gene_essentiality_summary CASCADE;
DROP TABLE IF EXISTS public.gene_go CASCADE;
DROP TABLE IF EXISTS public.gene_phenotypes CASCADE;
DROP TABLE IF EXISTS public.go_terms CASCADE;
DROP TABLE IF EXISTS public.gwas_associations CASCADE;
DROP TABLE IF EXISTS public.linkage_log CASCADE;
DROP TABLE IF EXISTS public.llm_classification_cache CASCADE;
DROP TABLE IF EXISTS public.mendelian_associations CASCADE;
DROP TABLE IF EXISTS public.modality_classification_cache CASCADE;
DROP TABLE IF EXISTS public.mondo_edges CASCADE;
DROP TABLE IF EXISTS public.mondo_terms CASCADE;
DROP TABLE IF EXISTS public.mondo_xref CASCADE;
DROP TABLE IF EXISTS public.pathways CASCADE;
DROP TABLE IF EXISTS public.peptide_druggability_cache CASCADE;
DROP TABLE IF EXISTS public.phenotype_ranking_cache CASCADE;
DROP TABLE IF EXISTS public.phenotypes CASCADE;
DROP TABLE IF EXISTS public.protein_interactions CASCADE;
DROP TABLE IF EXISTS public.protein_structure CASCADE;
DROP TABLE IF EXISTS public.raw_ingestion_data CASCADE;
DROP TABLE IF EXISTS public.saved_queries CASCADE;
DROP TABLE IF EXISTS public.single_cell_expression CASCADE;
DROP TABLE IF EXISTS public.sponsors CASCADE;
DROP TABLE IF EXISTS public.target_evidence CASCADE;
DROP TABLE IF EXISTS public.target_pathways CASCADE;
DROP TABLE IF EXISTS public.target_pleiotropy CASCADE;
DROP TABLE IF EXISTS public.therapeutic_phenotypes CASCADE;
DROP TABLE IF EXISTS public.therapies CASCADE;
DROP TABLE IF EXISTS public.therapy_biomarkers CASCADE;
DROP TABLE IF EXISTS public.therapy_targets CASCADE;
DROP TABLE IF EXISTS public.tissue_expression CASCADE;
DROP TABLE IF EXISTS public.tissue_expression_summary CASCADE;
DROP TABLE IF EXISTS public.tissues CASCADE;
DROP TABLE IF EXISTS public.treatment_sponsors_global CASCADE;
DROP TABLE IF EXISTS public.treatment_stats_global CASCADE;
DROP TABLE IF EXISTS public.treatment_stats_json CASCADE;
DROP TABLE IF EXISTS public.trial_country_summary CASCADE;
DROP TABLE IF EXISTS public.trial_sponsor_summary CASCADE;
DROP TABLE IF EXISTS public.trial_summary_json CASCADE;
DROP TABLE IF EXISTS public.trial_therapies CASCADE;
DROP TABLE IF EXISTS public.trials CASCADE;
DROP TABLE IF EXISTS public.v1_discover_cache CASCADE;
DROP TABLE IF EXISTS pv_evidence.assertion CASCADE;
DROP TABLE IF EXISTS pv_evidence.asset_mechanism_assertion CASCADE;
DROP TABLE IF EXISTS pv_evidence.asset_target_assertion CASCADE;
DROP TABLE IF EXISTS pv_evidence.asset_target_context_assertion CASCADE;
DROP TABLE IF EXISTS pv_evidence.document_relation_candidate CASCADE;
DROP TABLE IF EXISTS pv_evidence.document_relation_candidate_observation CASCADE;
DROP TABLE IF EXISTS pv_evidence.llm_decision_comparison CASCADE;
DROP TABLE IF EXISTS pv_evidence.llm_decision_source CASCADE;
DROP TABLE IF EXISTS pv_evidence.llm_proposal_verification CASCADE;
DROP TABLE IF EXISTS pv_evidence.mechanism_phenotype_assertion CASCADE;
DROP TABLE IF EXISTS pv_evidence.preclinical_experiment CASCADE;
DROP TABLE IF EXISTS pv_evidence.preclinical_experiment_evidence CASCADE;
DROP TABLE IF EXISTS pv_evidence.target_phenotype_assertion CASCADE;
DROP TABLE IF EXISTS pv_evidence.trial_indication_evidence CASCADE;
DROP TABLE IF EXISTS pv_evidence.trial_relationship_evidence CASCADE;
DO $$
DECLARE
    missing text[];
BEGIN
    SELECT array_agg(rel) INTO missing FROM unnest(ARRAY['preclin.chembl_mechanism',
        'preclin.chembl_molecule',
        'preclin.clinvar_accession_calibration',
        'preclin.ctgov_result_summary',
        'preclin.ctgov_study',
        'preclin.ctgov_study_drug',
        'preclin.ctgov_study_indication',
        'preclin.ctgov_study_moiety',
        'preclin.depmap_common_essential',
        'preclin.dev_program',
        'preclin.dev_program_approval',
        'preclin.dev_program_build',
        'preclin.dev_program_trial',
        'preclin.drug',
        'preclin.drug_moiety',
        'preclin.evidence_known_year',
        'preclin.evidence_source_release',
        'preclin.fda_application',
        'preclin.fda_application_moiety',
        'preclin.fda_approved_use',
        'preclin.fda_label',
        'preclin.fda_letter',
        'preclin.fda_product',
        'preclin.fda_submission',
        'preclin.fda_submission_letter',
        'preclin.gene_disease_mechanism',
        'preclin.hgnc_gene',
        'preclin.indication',
        'preclin.moiety',
        'preclin.moiety_target',
        'preclin.mondo_bio_area',
        'preclin.mouse_model_relation',
        'preclin.ontology_ancestor',
        'preclin.ontology_is_a',
        'preclin.ontology_term',
        'preclin.ontology_xref',
        'preclin.ot_association',
        'preclin.ot_disease',
        'preclin.ot_evidence',
        'preclin.ot_mouse_phenotype',
        'preclin.program_indication',
        'preclin.schema_migration',
        'preclin.trial_endpoint',
        'preclin.trial_outcome',
        'preclin.trial_publication',
        'preclin.trial_purpose',
        'preclin.unii_name',
        'preclin.unii_substance',
        'public.gene_constraint',
        'public.publications',
        'public.targets',
        'pv_evidence.llm_decision',
        'pv_evidence.llm_decision_run']) AS rel
    WHERE to_regclass(rel) IS NULL;
    IF missing IS NOT NULL THEN
        RAISE EXCEPTION 'tables the pipeline reads were dropped: %', missing;
    END IF;
END
$$;
COMMIT;
