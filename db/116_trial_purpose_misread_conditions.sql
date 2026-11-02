-- Listed conditions whose mapped MONDO disease is not what the trial means by them.

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.trial_purpose ADD COLUMN misread_conditions jsonb NOT NULL DEFAULT '[]';
COMMENT ON COLUMN preclin.trial_purpose.misread_conditions IS
    'Listed conditions whose mapped MONDO disease the trial does not treat under them, read with its title (an abbreviation meaning another disease, as CRC for chronic refractory cough; or a disease named only as the population of a treated symptom), as [{condition, meaning}]. pipeline.programs build counts such a condition in this trial as the mapped condition string equal to its meaning (lower-case alphanumerics), or as a condition without a MONDO term when none is.';
COMMIT;
