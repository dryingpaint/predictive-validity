-- Preserve whether ClinicalTrials.gov completion dates are actual or estimated.

BEGIN;

ALTER TABLE pv_core.trial
  ADD COLUMN primary_completion_date_type TEXT CHECK (
    primary_completion_date_type IN ('ACTUAL','ESTIMATED')
  ),
  ADD COLUMN completion_date_type TEXT CHECK (
    completion_date_type IN ('ACTUAL','ESTIMATED')
  ),
  ADD COLUMN completion_date_precision TEXT CHECK (
    completion_date_precision IN ('day','month','year')
  ),
  ADD COLUMN completion_date_lower_bound DATE,
  ADD COLUMN completion_date_upper_bound DATE,
  ADD CONSTRAINT trial_completion_bounds_check CHECK (
    (completion_date_lower_bound IS NULL AND completion_date_upper_bound IS NULL)
    OR completion_date_lower_bound <= completion_date_upper_bound
  );

UPDATE pv_core.trial trial
SET primary_completion_date_type = NULLIF(
      version.raw_payload #>> '{protocolSection,statusModule,primaryCompletionDateStruct,type}',
      ''
    ),
    completion_date_type = NULLIF(
      version.raw_payload #>> '{protocolSection,statusModule,completionDateStruct,type}',
      ''
    ),
    completion_date_precision = CASE
      WHEN trial.completion_date_text ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN 'day'
      WHEN trial.completion_date_text ~ '^[0-9]{4}-[0-9]{2}$' THEN 'month'
      WHEN trial.completion_date_text ~ '^[0-9]{4}$' THEN 'year'
    END,
    completion_date_lower_bound = CASE
      WHEN trial.completion_date_text ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        THEN trial.completion_date_text::date
      WHEN trial.completion_date_text ~ '^[0-9]{4}-[0-9]{2}$'
        THEN to_date(trial.completion_date_text||'-01','YYYY-MM-DD')
      WHEN trial.completion_date_text ~ '^[0-9]{4}$'
        THEN to_date(trial.completion_date_text||'-01-01','YYYY-MM-DD')
    END,
    completion_date_upper_bound = CASE
      WHEN trial.completion_date_text ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        THEN trial.completion_date_text::date
      WHEN trial.completion_date_text ~ '^[0-9]{4}-[0-9]{2}$'
        THEN (to_date(trial.completion_date_text||'-01','YYYY-MM-DD')
              + INTERVAL '1 month - 1 day')::date
      WHEN trial.completion_date_text ~ '^[0-9]{4}$'
        THEN to_date(trial.completion_date_text||'-12-31','YYYY-MM-DD')
    END
FROM pv_source.source_record_version version
WHERE version.source_record_version_id=trial.latest_source_record_version_id;

COMMIT;
