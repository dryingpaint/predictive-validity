-- How each mouse model that Open Targets links to a drug target and a program
-- disease relates to that disease (pipeline.targets mouse): whether the model
-- lowers or raises the gene's function, and whether its phenotypes resemble the
-- disease or its opposite. One row per (target gene, program disease, MGI model).

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE IF NOT EXISTS preclin.mouse_model_relation (
    ensembl_id        text NOT NULL,
    mondo_id          text NOT NULL,
    model_id          text NOT NULL,
    perturbation      text NOT NULL,
    relation          text NOT NULL,
    llm_decision_id   bigint NOT NULL REFERENCES pv_evidence.llm_decision,
    PRIMARY KEY (ensembl_id, mondo_id, model_id)
);
COMMIT;
