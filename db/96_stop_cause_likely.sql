-- The likely cause of a stop when no source states it: the model's best inference from context and
-- signals, kept apart from the evidence-backed cause in preclin.stop_cause.cause.

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.stop_cause ADD COLUMN IF NOT EXISTS likely_cause text;
ALTER TABLE preclin.stop_cause ADD COLUMN IF NOT EXISTS likely_basis text;
COMMENT ON COLUMN preclin.stop_cause.likely_cause IS
    'Best inference of the cause, from the same vocabulary as cause; equals cause where cause is known, and is the model''s reasoned guess from context and signals where cause is unknown. Null for registry rows.';
COMMENT ON COLUMN preclin.stop_cause.likely_basis IS 'What the likely cause rests on, in a sentence.';
COMMIT;
