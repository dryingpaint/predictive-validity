BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.stop ADD COLUMN IF NOT EXISTS subcause_support text
    CHECK (subcause_support IN ('stated', 'likely'));
COMMENT ON COLUMN preclin.stop.subcause_support IS 'For a safety, sponsor_decision, operational or positive_not_advanced subcause other than not_stated: stated where the stop''s text or a retrieved source gives it, likely where the search-based pass (stop_subcause_search) finds the sources make it likely without saying it. Null otherwise.';
COMMIT;
