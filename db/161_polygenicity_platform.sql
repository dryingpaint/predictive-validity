-- Polygenicity (#147), follow-up to 160: the genotyping platform's SNP count per Catalog study, so that a study on a
-- targeted array (Immunochip, Metabochip: about 130,000 to 200,000 SNPs) is not chosen for LDSC, whose regression
-- needs genome-wide coverage; and the matching disease status.

BEGIN;
SET LOCAL lock_timeout = '3s';

ALTER TABLE preclin.gwas_catalog_study ADD COLUMN platform_snps int;
COMMENT ON COLUMN preclin.gwas_catalog_study.platform_snps IS
    'SNPs passing QC as the Catalog gives them in the platform text ("Illumina [~2,500,000] (imputed)"), the largest bracketed count; null when not stated.';

ALTER TABLE preclin.disease_polygenicity DROP CONSTRAINT disease_polygenicity_ldsc_status_check;
ALTER TABLE preclin.disease_polygenicity ADD CONSTRAINT disease_polygenicity_ldsc_status_check
    CHECK (ldsc_status IN ('ok', 'no_study', 'no_sumstats', 'not_european', 'no_case_control', 'targeted_array',
        'no_effect', 'run_failed', 'low_z', 'out_of_bounds', 'no_k', 'not_profiled'));
COMMENT ON COLUMN preclin.disease_polygenicity.ldsc_status IS
    'ok when an estimate exists (h2_z >= 4, 0 < h2_liab <= 1, a genome-wide platform); otherwise why not, the first reason in the order no_study, no_sumstats, no_case_control, not_european, targeted_array, no_effect, run_failed, low_z, no_k, out_of_bounds; not_profiled marks a disease the unit gained after the build.';

COMMIT;
