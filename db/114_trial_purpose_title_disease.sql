-- The disease a trial's title says it treats when its listed conditions are only complications of it.

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.trial_purpose ADD COLUMN title_disease text;
COMMENT ON COLUMN preclin.trial_purpose.title_disease IS
    'For indication_development: the disease the title says the trial treats when the listed conditions it develops the drug for are only complications or manifestations of it (e.g. COVID-19 for adult ARDS), as a standard disease name; null otherwise. pipeline.programs build counts the trial for this disease alone when the name equals a mapped condition string (lower-case alphanumerics).';
COMMIT;
