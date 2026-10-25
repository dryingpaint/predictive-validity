-- trial_endpoint keeps the class of the governing primary outcome; how many primary
-- outcomes a trial registers is jsonb_array_length(ctgov_study.primary_outcomes).
-- gene_disease_mechanism dates its risk mechanism and its protective effect separately.

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.trial_endpoint DROP COLUMN IF EXISTS n_primaries;
COMMENT ON TABLE preclin.gene_disease_mechanism IS
    'How germline variation in a primary drug target acts on a program disease (pipeline.targets mechanism, drug-blind LLM)';
COMMENT ON COLUMN preclin.gene_disease_mechanism.risk_year IS
    'Year the risk mechanism was first shown for this gene in this disease; null when risk_mechanism is unknown or none';
COMMENT ON COLUMN preclin.gene_disease_mechanism.protective_year IS
    'Year the protective effect was first shown for this gene in this disease; null when protective is none_known';
COMMIT;
