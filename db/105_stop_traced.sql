BEGIN;
SET LOCAL lock_timeout = '3s';
DELETE FROM preclin.stop;  -- derived rows; pipeline.stop_causes assemble writes them with traced
ALTER TABLE preclin.stop ADD COLUMN IF NOT EXISTS traced boolean NOT NULL;
COMMENT ON COLUMN preclin.stop.traced IS
    'The cause did not come straight from the registry: no usable reason was stated, or the efficacy attribution overturned the stated one.';
COMMIT;
