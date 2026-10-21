-- Molecular entities in each FDA application (pipeline.fda link): the LLM
-- resolves Drugs@FDA active-ingredient strings and label names to the same
-- nonproprietary-name keys as preclin.moiety, flagging biosimilars.

BEGIN;

CREATE TABLE IF NOT EXISTS preclin.fda_application_moiety (
    appl_no         text NOT NULL REFERENCES preclin.fda_application,
    moiety_id       integer NOT NULL REFERENCES preclin.moiety,
    biosimilar_of   text,
    llm_decision_id bigint NOT NULL REFERENCES pv_evidence.llm_decision,
    PRIMARY KEY (appl_no, moiety_id)
);
CREATE INDEX IF NOT EXISTS fda_application_moiety_moiety_idx ON preclin.fda_application_moiety (moiety_id);

COMMIT;
