-- The registry's brief summary of each study. Some sponsors give the reason a
-- trial stopped only here, with whyStopped left empty.

BEGIN;
SET LOCAL lock_timeout = '10s';
ALTER TABLE preclin.ctgov_study ADD COLUMN IF NOT EXISTS brief_summary text;
COMMIT;
