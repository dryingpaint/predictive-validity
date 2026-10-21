-- Human protein targets of each molecular entity (pipeline.targets resolve),
-- replacing preclin.drug_target / drug_target_consensus_map for analyses built
-- on preclin.dev_program. moiety.target_kind records entities acting on
-- pathogens or without a single molecular target.

BEGIN;
SET LOCAL lock_timeout = '90s';

CREATE TABLE IF NOT EXISTS preclin.moiety_target (
    moiety_id       integer NOT NULL REFERENCES preclin.moiety,
    target_id       integer NOT NULL REFERENCES public.targets,
    action          text NOT NULL,
    is_primary      boolean NOT NULL,
    llm_decision_id bigint NOT NULL REFERENCES pv_evidence.llm_decision,
    PRIMARY KEY (moiety_id, target_id)
);
CREATE INDEX IF NOT EXISTS moiety_target_target_idx ON preclin.moiety_target (target_id);

ALTER TABLE preclin.moiety
    ADD COLUMN IF NOT EXISTS target_kind text CHECK (target_kind IN
        ('human_protein', 'pathogen', 'no_single_target', 'unknown')),
    ADD COLUMN IF NOT EXISTS target_decision_id bigint REFERENCES pv_evidence.llm_decision;

COMMIT;
