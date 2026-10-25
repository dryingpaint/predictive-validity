-- Each study's registered primary outcome measures (measure, description, time
-- frame), as ClinicalTrials.gov lists them; pipeline.outcomes endpoints classifies
-- the kind of endpoint they measure.

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.ctgov_study ADD COLUMN IF NOT EXISTS primary_outcomes jsonb;
COMMIT;
