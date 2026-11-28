-- Polygenicity (#147), migration 178: the corrected-K sensitivity (Melissa's decision of 2026-11-26, issuecomment-7207708610;
-- announced 2026-11-27, issuecomment-7235417538). The review of 2026-11-25 found that the registered profile took the
-- Pan-UKB prevalence from a descendant's ICD-10 code for 30 of the 64 scored diseases with a Pan-UKB K. The registered
-- columns stand as built; these seven hold K re-chosen own-code-first with ICD-10 ranges expanded, and the liability
-- heritability, score and status recomputed from the stored run under it (`python -m pipeline.polygenicity k-corrected`).
-- Numbered 178 because 173-177 landed on main on 2026-11-27.
BEGIN;
SET LOCAL lock_timeout = '3s';

ALTER TABLE preclin.disease_polygenicity
    ADD COLUMN k_corrected numeric,
    ADD COLUMN k_corrected_source text CHECK (k_corrected_source IN ('gbd', 'panukb', 'none')),
    ADD COLUMN k_corrected_code text,
    ADD COLUMN k_corrected_via_parent boolean,
    ADD COLUMN h2_liab_k_corrected numeric,
    ADD COLUMN score_k_corrected numeric,
    ADD COLUMN ldsc_status_k_corrected text CHECK (ldsc_status_k_corrected IN ('ok', 'no_study', 'no_sumstats', 'not_european',
        'no_case_control', 'no_effect', 'run_failed', 'low_z', 'out_of_bounds', 'no_k', 'zero_loci', 'not_profiled', 'targeted_array'));

COMMENT ON COLUMN preclin.disease_polygenicity.k_corrected IS
    'Corrected-K sensitivity: the population prevalence under the own-code-first rule (the GBD rate as for k, else the Pan-UKB European case fraction of the disease''s own ICD-10 code, ranges expanded, then its three-character parent, then a MONDO descendant''s code, then its parent); null when none.';
COMMENT ON COLUMN preclin.disease_polygenicity.k_corrected_source IS 'gbd, panukb or none: where k_corrected came from.';
COMMENT ON COLUMN preclin.disease_polygenicity.k_corrected_code IS 'The Pan-UKB ICD-10 phenocode behind k_corrected when its source is panukb; null otherwise.';
COMMENT ON COLUMN preclin.disease_polygenicity.k_corrected_via_parent IS 'True only when k_corrected_code is the three-character parent of one of the disease''s own ICD-10 codes (never for a descendant''s code).';
COMMENT ON COLUMN preclin.disease_polygenicity.h2_liab_k_corrected IS 'The stored run''s observed-scale heritability on the liability scale at k_corrected; null without a run or a K.';
COMMENT ON COLUMN preclin.disease_polygenicity.score_k_corrected IS 'loci / h2_liab_k_corrected, null unless ldsc_status_k_corrected is ok. The sensitivity re-cuts its tertiles over these; the registered tertiles stay the primary.';
COMMENT ON COLUMN preclin.disease_polygenicity.ldsc_status_k_corrected IS 'The profile status re-derived under k_corrected from the stored run (a disease that gains a K may become ok; one that loses its code becomes no_k); the registered status where the run gave no estimate.';

COMMIT;
