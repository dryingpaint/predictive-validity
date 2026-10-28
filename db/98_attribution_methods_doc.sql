-- The efficacy-attribution methods live in report/methods_stops_and_engagement.md.

BEGIN;
SET LOCAL lock_timeout = '3s';
COMMENT ON TABLE preclin.efficacy_failure_attribution IS
    'Failure code of each program stopped for efficacy or exposure, from the three pillars (Morgan et al. 2012) read in the sources assembled for it. Methods: report/methods_stops_and_engagement.md.';
COMMENT ON COLUMN preclin.efficacy_failure_attribution.primary_code IS 'F1a, F1b, F2-F9 or U, as defined in report/methods_stops_and_engagement.md.';
COMMIT;
