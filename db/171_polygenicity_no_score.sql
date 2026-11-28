-- Polygenicity and failure (issue #147), migration 171. Melissa's decision of 2026-11-24 (issuecomment-7149832720): a disease with
-- measurable heritability but no genome-wide significant locus joins the no-score group instead of scoring 0
-- (ldsc_status 'zero_loci'), and the profile records which Pan-UKB code supplied K and whether that code is the
-- three-character parent of the disease's own ICD-10 codes (she asked for the count of diseases that take K this way).
BEGIN;
SET LOCAL lock_timeout = '3s';

ALTER TABLE preclin.disease_polygenicity DROP CONSTRAINT disease_polygenicity_ldsc_status_check;
ALTER TABLE preclin.disease_polygenicity ADD CONSTRAINT disease_polygenicity_ldsc_status_check
    CHECK (ldsc_status IN ('ok', 'no_study', 'no_sumstats', 'not_european', 'no_case_control', 'no_effect', 'run_failed',
                           'low_z', 'out_of_bounds', 'no_k', 'zero_loci', 'not_profiled', 'targeted_array'));
ALTER TABLE preclin.disease_polygenicity ADD COLUMN k_code text;
ALTER TABLE preclin.disease_polygenicity ADD COLUMN k_via_parent boolean;
COMMENT ON COLUMN preclin.disease_polygenicity.k_code IS 'The Pan-UKB ICD-10 phenocode whose European case fraction supplied K (k_source panukb); null otherwise.';
COMMENT ON COLUMN preclin.disease_polygenicity.k_via_parent IS 'True when k_code is the three-character parent of a longer ICD-10 code of the disease rather than one of its own codes.';

COMMIT;
