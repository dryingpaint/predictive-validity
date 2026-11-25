-- The adjudication of #154's confirmed set gains versions: a re-reading under a tightened rubric (v2) is added beside
-- the first (v1) rather than replacing it, and readers take each record's latest version.

BEGIN;
SET LOCAL lock_timeout = '3s';

ALTER TABLE preclin.target_literature_adjudication ADD COLUMN adjudication_version text NOT NULL DEFAULT 'v1';
ALTER TABLE preclin.target_literature_adjudication DROP CONSTRAINT target_literature_adjudication_pkey;
ALTER TABLE preclin.target_literature_adjudication ADD PRIMARY KEY (ensembl_id, mondo_id, record_id, adjudication_version);
COMMENT ON COLUMN preclin.target_literature_adjudication.adjudication_version IS
    'The adjudication rubric''s prompt_version: v1, the first reading of every candidate; v2, a re-reading of the v1 YES calls of five kinds under a rubric tightened after a second-model spot check (report/audits/target_literature.md). Readers take each record''s latest version.';

COMMIT;
