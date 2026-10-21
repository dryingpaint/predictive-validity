-- How germline variation in a drug target acts on a program's disease
-- (pipeline.targets mechanism): the direction in which risk variants change the
-- gene product's function, whether protective variants are known, and the year
-- that mechanism was established. One row per (target gene, program disease) where
-- the gene has germline evidence for the disease or a subtype of it.

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE IF NOT EXISTS preclin.gene_disease_mechanism (
    ensembl_id        text NOT NULL,
    mondo_id          text NOT NULL,
    risk_mechanism    text NOT NULL,
    protective        text NOT NULL,
    established_year  integer,
    confidence        text NOT NULL,
    llm_decision_id   bigint NOT NULL REFERENCES pv_evidence.llm_decision,
    PRIMARY KEY (ensembl_id, mondo_id)
);
COMMIT;
