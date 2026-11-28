-- Polygenicity (#147), migration 181: the population prevalence K of each profiled disease under each rule, one row per
-- disease per rule, so the sensitivities can be run and compared without touching the profile's registered columns.
-- Rules: registered (the gate of 2026-11-25, copied from the profile), own_first (the corrected rule of migration 178,
-- copied), v3 (announced on #147 on 2026-11-27 after an independent check of every code: own three-character ICD-10
-- codes and the phecodes reached through MONDO's ICD-9 cross-references first, then parents, Pan-UKB before GBD at
-- 1,000 cases, descendants pooled, chapter-level terms left without a K). Filled by `python -m pipeline.polygenicity k-rules`. Numbered 181: 179 and 180 were applied from another branch on 2026-11-27.
BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE preclin.disease_polygenicity_k (
    mondo_id text NOT NULL REFERENCES preclin.disease_polygenicity,
    rule text NOT NULL CHECK (rule IN ('registered', 'own_first', 'v3')),
    k numeric,
    k_source text CHECK (k_source IN ('gbd', 'panukb', 'none')),
    k_code text,
    k_via_parent boolean,
    h2_liab numeric,
    score numeric,
    ldsc_status text NOT NULL CHECK (ldsc_status IN ('ok', 'no_study', 'no_sumstats', 'not_european', 'no_case_control', 'no_effect',
        'run_failed', 'low_z', 'out_of_bounds', 'no_k', 'zero_loci', 'not_profiled', 'targeted_array')),
    category boolean NOT NULL DEFAULT false,
    built_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (mondo_id, rule)
);
COMMENT ON TABLE preclin.disease_polygenicity_k IS
    'The population prevalence K of each candidate disease of #147 under each rule for choosing it, with the liability-scale heritability, score and status that follow from the stored LDSC run; the registered rule is the primary, the others are sensitivities.';
COMMENT ON COLUMN preclin.disease_polygenicity_k.rule IS 'registered (gate of 2026-11-25), own_first (migration 178, the own-code-first ICD-10 rule) or v3 (phecodes through ICD-9, Pan-UKB before GBD, descendants pooled, categories excluded).';
COMMENT ON COLUMN preclin.disease_polygenicity_k.k IS 'The prevalence: the GBD rate per 100,000 over 100,000, or the Pan-UKB European case fraction of k_code (an ICD-10 three-character code or a phecode); null when the rule finds none.';
COMMENT ON COLUMN preclin.disease_polygenicity_k.k_source IS 'gbd, panukb or none.';
COMMENT ON COLUMN preclin.disease_polygenicity_k.k_code IS 'The Pan-UKB phenocode behind K when k_source is panukb: an ICD-10 three-character code (I48) or a phecode (401); null otherwise.';
COMMENT ON COLUMN preclin.disease_polygenicity_k.k_via_parent IS 'True when k_code is the three-character parent of one of the disease''s own ICD-10 codes (v3, own_first) or, for the registered rule, not one of the pooled codes.';
COMMENT ON COLUMN preclin.disease_polygenicity_k.h2_liab IS 'The stored run''s heritability on the liability scale at this K; null without a run or a K.';
COMMENT ON COLUMN preclin.disease_polygenicity_k.score IS 'loci / h2_liab, null unless ldsc_status is ok; the rule''s tertiles are re-cut over these in the report.';
COMMENT ON COLUMN preclin.disease_polygenicity_k.ldsc_status IS 'The profile status re-derived under this K from the stored run; the registered status where the run gave no estimate.';
COMMENT ON COLUMN preclin.disease_polygenicity_k.category IS 'v3 only: the term stands for a chapter (an own cross-reference spanning ten or more codes, or more than thirty descendant codes) and is given no K.';

COMMIT;
