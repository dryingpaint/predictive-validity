-- Whether a MONDO disease term names one development indication or is a generic grouping term spanning several
-- (#185). A drug's disease that is an ontology ancestor of another of its diseases is folded into the narrower
-- programmes only when it is a grouping term; an indication keeps its own programme (rheumatoid arthritis, which
-- MONDO places above ankylosing spondylitis and psoriatic arthritis).

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE preclin.disease_term_scope (
    mondo_id        text PRIMARY KEY,
    scope           text NOT NULL CHECK (scope IN ('indication', 'grouping')),
    llm_decision_id bigint NOT NULL REFERENCES pv_evidence.llm_decision
);
COMMENT ON TABLE preclin.disease_term_scope IS
    'One row per MONDO disease term that is an ontology ancestor of another disease the same entity was tested in: whether it names one development indication or is a grouping term spanning several. Written by pipeline.programs scope; read by pipeline.programs build.';
COMMENT ON COLUMN preclin.disease_term_scope.scope IS
    'indication: a disease a sponsor develops a drug for and a regulator approves one for (rheumatoid arthritis, acute myeloid leukemia, colorectal cancer); its trials form their own programme. grouping: a term spanning several separate indications (cancer, lymphoma, leukemia, arthritis, solid tumour); its trials attach to the narrower programmes it contains.';
COMMENT ON COLUMN preclin.disease_term_scope.llm_decision_id IS 'The decision behind scope (task disease_term_scope).';
COMMIT;
