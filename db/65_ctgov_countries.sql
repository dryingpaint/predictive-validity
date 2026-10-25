-- Countries with at least one site for each ClinicalTrials.gov study
-- (contactsLocationsModule), to separate US-registration-relevant programs.

BEGIN;
SET LOCAL lock_timeout = '90s';
ALTER TABLE preclin.ctgov_study ADD COLUMN IF NOT EXISTS countries text[];
COMMIT;
