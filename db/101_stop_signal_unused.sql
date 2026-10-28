-- Signals no step reads: the model's bundle and the reports use stopped_on, drug_continued_elsewhere,
-- drug_approved_anywhere, sponsor_active_after and target_peers_stopped only.

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.stop_signal
    DROP COLUMN IF EXISTS trials_terminated,
    DROP COLUMN IF EXISTS trials_completed,
    DROP COLUMN IF EXISTS has_results,
    DROP COLUMN IF EXISTS has_publication;
COMMIT;
