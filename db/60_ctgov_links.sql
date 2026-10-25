-- Links from each ClinicalTrials.gov study to the intervention names and
-- condition strings it lists (pipeline.programs register), and the role each
-- molecular entity plays in the study (pipeline.programs roles).

BEGIN;

CREATE TABLE IF NOT EXISTS preclin.ctgov_study_drug (
    nct_id            text NOT NULL REFERENCES preclin.ctgov_study,
    drug_id           integer NOT NULL REFERENCES preclin.drug,
    intervention_type text NOT NULL,
    arm_types         text[] NOT NULL,
    other_names       text[] NOT NULL,
    PRIMARY KEY (nct_id, drug_id)
);
CREATE INDEX IF NOT EXISTS ctgov_study_drug_drug_idx ON preclin.ctgov_study_drug (drug_id);

CREATE TABLE IF NOT EXISTS preclin.ctgov_study_indication (
    nct_id        text NOT NULL REFERENCES preclin.ctgov_study,
    indication_id integer NOT NULL REFERENCES preclin.indication,
    PRIMARY KEY (nct_id, indication_id)
);
CREATE INDEX IF NOT EXISTS ctgov_study_indication_ind_idx ON preclin.ctgov_study_indication (indication_id);

-- Role of each molecular entity in a study: what the study develops
-- (investigational), what every arm also receives (background), or what the
-- investigational agent is compared against (comparator).
CREATE TABLE IF NOT EXISTS preclin.ctgov_study_moiety (
    nct_id          text NOT NULL REFERENCES preclin.ctgov_study,
    moiety_id       integer NOT NULL REFERENCES preclin.moiety,
    role            text NOT NULL CHECK (role IN ('investigational', 'background', 'comparator')),
    method          text NOT NULL CHECK (method IN ('arm_types', 'llm')),
    llm_decision_id bigint REFERENCES pv_evidence.llm_decision,
    PRIMARY KEY (nct_id, moiety_id)
);
CREATE INDEX IF NOT EXISTS ctgov_study_moiety_moiety_idx ON preclin.ctgov_study_moiety (moiety_id, role);

COMMIT;
